# runner.py (angepasst, .venv entfernt, korrektes Zurückzippen + OUTPUT_DONE)

import time, requests, tempfile, os, typer, zipfile, subprocess, shutil, json, platform, sys, io

cli = typer.Typer(help="Octo Runner CLI")
CONFIG_PATH = os.path.expanduser("~/.remotecompute/serverconfig.json")

# Sicherstellen, dass stdout/stderr UTF-8 ist (für Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

ascii_art = r"""
                __       
  ____   _____ / /_ ____ 
 / __ \ / ___// __// __ \
/ /_/ // /__ / /_ / /_/ /
\____/ \___/ \__/ \____/
"""

# ---------------------------
# Config Handling
# ---------------------------

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"valid_tokens": [], "server": "http://127.0.0.1:5000"}

def save_token(token, server):
    cfg = load_config()
    if token not in cfg.get("valid_tokens", []):
        cfg.setdefault("valid_tokens", []).append(token)
    cfg["server"] = server
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ---------------------------
# Task Handling
# ---------------------------

def poll_task(server, token):
    """Fragt einen Task ab und lädt das ZIP herunter."""
    try:
        res = requests.post(f"{server}/get_task", json={"token": token})
        if res.ok:
            data = res.json()
            task = data.get("task")
            if task and task.get("id") and task.get("archive"):
                archive_url = task["archive"]
                if archive_url.startswith("/"):
                    archive_url = server.rstrip("/") + archive_url

                resp = requests.get(archive_url)
                if resp.ok:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
                    tmp.write(resp.content)
                    tmp.close()
                    task["archive_file"] = tmp.name
                    return task
    except Exception as e:
        print(f"❌ Error while polling task: {e}")
    return None

def send_output(server, task_id, line):
    """Sendet Output-Zeile zurück an den Server."""
    try:
        requests.post(f"{server}/submit_output/{task_id}", json={"line": line})
    except Exception as e:
        print(f"❌ Error while sending output: {e}")

def zip_new_files(workdir, orig_files):
    exclude_dirs = {"venv", ".local", "__pycache__"}
    exclude_ext = {".pyc", ".pyo"}

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workdir):
            # bestimmte Verzeichnisse ignorieren
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for f in files:
                if any(f.endswith(ext) for ext in exclude_ext):
                    continue  # Skip unnötige Files

                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, workdir)

                # nur neue/geänderte Files packen
                if rel_path not in orig_files:
                    zf.write(abs_path, rel_path)
    return tmp.name

# ---------------------------
# Runner Loop
# ---------------------------

@cli.command()
def runner(token: str = typer.Option(..., help="Authentication token")):
    typer.echo(ascii_art)

    cfg = load_config()
    server = cfg.get("server", "http://127.0.0.1:5000")

    save_token(token, server)
    typer.echo(f"🚀 Runner connected to {server} with token {token}")

    while True:
        task = poll_task(server, token)
        if task:
            task_id = task["id"]
            archive_file = task["archive_file"]
            entry_file = task.get("entry", "main.py")
            docker_image = task.get("docker_image", "python:3.11-slim")
            auto_install = task.get("auto_install", False)

            gpu = task.get("gpu")
            ram = task.get("ram")
            cpu = task.get("cpu")
            shm_size = task.get("shm_size")

            print(f"⚡ Running Task {task_id} using image {docker_image}")

            try:
                # ZIP entpacken
                workdir = tempfile.mkdtemp()
                with zipfile.ZipFile(archive_file, "r") as zf:
                    zf.extractall(workdir)

                print("📦 Archive extracted to:", workdir)
                main_path = os.path.join(workdir, entry_file)

                if not os.path.exists(main_path):
                    send_output(server, task_id, f"[RUNNER ERROR] Startfile {entry_file} not found")
                    send_output(server, task_id, "[TASK_FAILED]")
                    continue

                requirements_path = os.path.join(workdir, "requirements.txt")

                # --- Originaldateien merken ---
                orig_files = []
                for root, dirs, files in os.walk(workdir):
                    dirs[:] = [d for d in dirs if d.lower() != "venv"]
                    for f in files:
                        rel_path = os.path.relpath(os.path.join(root, f), workdir)
                        orig_files.append(rel_path)

                # Docker ausführen
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{workdir}:/workspace",
                    "-w", "/workspace",
                    "-e", "PYTHONUTF8=1",
                    "-e", "PYTHONDONTWRITEBYTECODE=1",
                    "-e", "PYTHONUSERBASE=/workspace/.local",
                ]
                if platform.system() != "Windows":
                    uid = os.getuid()
                    gid = os.getgid()
                    docker_cmd += ["--user", f"{uid}:{gid}"]
                if cpu: docker_cmd += ["--cpus", str(cpu)]
                if ram: docker_cmd += ["--memory", str(ram)]
                if shm_size: docker_cmd += ["--shm-size", str(shm_size)]
                if gpu: docker_cmd += ["--gpus", str(gpu)]

                docker_cmd.append(docker_image)

                if auto_install and os.path.exists(requirements_path):
                    docker_cmd += [
                        "sh", "-c",
                        f"pip install -r /workspace/requirements.txt && python -u /workspace/{entry_file}"
                    ]
                else:
                    docker_cmd += ["python", "-u", f"/workspace/{entry_file}"]

                proc = subprocess.Popen(
                    docker_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8"
                )
                for line in proc.stdout:
                    send_output(server, task_id, line.rstrip())
                proc.wait()

                # --- Neue/geänderte Dateien zippen und an Server schicken ---
                output_zip = zip_new_files(workdir, orig_files)
                with open(output_zip, "rb") as f:
                    try:
                        requests.post(f"{server}/submit_output_zip/{task_id}", files={"archive": f})
                        # --- Flag an Client senden ---
                        send_output(server, task_id, "[OUTPUT_DONE]")
                    except Exception as e:
                        print(f"❌ Error sending output zip: {e}")
                os.remove(output_zip)

                if proc.returncode == 0:
                    send_output(server, task_id, "[TASK_DONE]")
                else:
                    send_output(server, task_id, "[TASK_FAILED]")

            except Exception as e:
                send_output(server, task_id, f"[RUNNER ERROR] {e}")
                send_output(server, task_id, "[TASK_FAILED]")
            finally:
                if os.path.exists(archive_file):
                    os.remove(archive_file)
                if os.path.exists(workdir):
                    shutil.rmtree(workdir)
        else:
            time.sleep(2)

if __name__ == "__main__":
    cli()
