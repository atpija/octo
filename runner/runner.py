import time, requests, tempfile, os, typer, zipfile, subprocess, shutil, json

cli = typer.Typer(help="Octo Runner CLI")
CONFIG_PATH = os.path.expanduser("~/.remotecompute/serverconfig.json")

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
            task = res.json()
            if task.get("id") and task.get("archive"):
                # Archive-URL zusammensetzen
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

# ---------------------------
# Runner Loop
# ---------------------------

@cli.command()
def runner(token: str = typer.Option(..., help="Authentication token"),
           server: str = typer.Option("http://127.0.0.1:5000", help="Server URL")):
    typer.echo(ascii_art)
    save_token(token, server)
    typer.echo(f"🚀 Runner connected to {server} with token {token}")

    while True:
        task = poll_task(server, token)
        if task:
            task_id = task["id"]
            archive_file = task["archive_file"]
            entry_file = task.get("entry", "main.py")

            print(f"⚡ Running Task {task_id}")

            try:
                # ZIP entpacken
                workdir = tempfile.mkdtemp()
                with zipfile.ZipFile(archive_file, "r") as zf:
                    zf.extractall(workdir)

                print("📦 Archive extracted to:", workdir)
                print("📂 Files inside workdir:")
                for root, dirs, files in os.walk(workdir):
                    for f in files:
                        rel_path = os.path.relpath(os.path.join(root, f), workdir)
                        print("   ", rel_path)

                main_path = os.path.join(workdir, entry_file)
                print("👉 Looking for entry file:", main_path)

                if not os.path.exists(main_path):
                    msg = f"[RUNNER ERROR] Startfile {entry_file} not found in {workdir}"
                    send_output(server, task_id, msg)
                    send_output(server, task_id, "[TASK_FAILED]")
                    continue

                # Docker ausführen
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{workdir}:/workspace",
                    "--user", f"{os.getuid()}:{os.getgid()}",
                    "-e", "PYTHONDONTWRITEBYTECODE=1",
                    "python:3.11-slim",
                    "python", "-u", f"/workspace/{entry_file}"
                ]
                print("🐳 Running docker command:", docker_cmd)

                proc = subprocess.Popen(
                    docker_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                for line in iter(proc.stdout.readline, ''):
                    line = line.strip()
                    if line:
                        send_output(server, task_id, line)

                proc.stdout.close()
                proc.wait()

                if proc.returncode == 0:
                    send_output(server, task_id, "[TASK_DONE]")
                    print("✅ Task done")
                else:
                    send_output(server, task_id, f"[RUNNER ERROR] Process exited with {proc.returncode}")
                    send_output(server, task_id, "[TASK_FAILED]")
                    print(f"❌ Process exited with {proc.returncode}")

            except Exception as e:
                send_output(server, task_id, f"[RUNNER ERROR] {e}")
                send_output(server, task_id, "[TASK_FAILED]")
                print(f"❌ Exception: {e}")
            finally:
                if os.path.exists(workdir):
                    shutil.rmtree(workdir)
                if os.path.exists(archive_file):
                    os.remove(archive_file)
        else:
            time.sleep(2)

if __name__ == "__main__":
    cli()