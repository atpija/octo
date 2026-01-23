# runner.py (corrected version)

import time, requests, tempfile, os, typer, zipfile, subprocess, shutil, json, platform

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
# File Type Configuration
# ---------------------------

FILE_TYPE_CONFIG = {
    '.py': {
        'default_image': 'python:3.11-slim',
        'package_file': 'requirements.txt',
        'install_cmd': 'pip install -r /workspace/requirements.txt',
    },
    '.js': {
        'default_image': 'node:latest',
        'package_file': 'package.json',
        'install_cmd': 'npm install',
    },
    '.ts': {
        'default_image': 'node:latest',
        'package_file': 'package.json',
        'install_cmd': 'npm install',
    },
    '.rb': {
        'default_image': 'ruby:latest',
        'package_file': 'Gemfile',
        'install_cmd': 'bundle install',
    },
    '.go': {
        'default_image': 'golang:latest',
        'package_file': 'go.mod',
        'install_cmd': 'go mod download',
    },
    '.rs': {
        'default_image': 'rust:latest',
        'package_file': 'Cargo.toml',
        'install_cmd': 'cargo build',
    },
    '.java': {
        'default_image': 'openjdk:latest',
        'package_file': None,
        'install_cmd': None,
    },
    '.c': {
        'default_image': 'gcc:latest',
        'package_file': None,
        'install_cmd': None,
    },
    '.cpp': {
        'default_image': 'gcc:latest',
        'package_file': None,
        'install_cmd': None,
    },
    '.sh': {
        'default_image': 'alpine:latest',
        'package_file': None,
        'install_cmd': None,
    },
    '.ps1': {
        'default_image': 'mcr.microsoft.com/powershell:latest',
        'package_file': None,
        'install_cmd': None,
    },
}

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
        typer.secho(f"{typer.style('[ERROR]', fg='red')} Error while polling task: {e}")
    return None

def send_output(server, task_id, line):
    """Sendet Output-Zeile zurück an den Server."""
    try:
        requests.post(f"{server}/submit_output/{task_id}", json={"line": line})
    except Exception as e:
        typer.secho(f"{typer.style('[ERROR]', fg='red')} Error while sending output: {e}")

def zip_new_files(workdir, orig_files):
    exclude_dirs = {"venv", ".local", "__pycache__", "node_modules", "target", ".git"}
    exclude_ext = {".pyc", ".pyo", ".o", ".so", ".dll"}

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workdir):
            # bestimmte Verzeichnisse ignorieren
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for f in files:
                if any(f.endswith(ext) for ext in exclude_ext):
                    continue

                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, workdir)

                # nur neue/geänderte Files packen
                if rel_path not in orig_files:
                    zf.write(abs_path, rel_path)
    return tmp.name

def build_execution_command(entry_file, workdir, auto_install, file_ext, file_config):
    """Builds the execution command based on file type."""
    
    # Check if package manager file exists
    package_file_path = None
    if file_config.get('package_file'):
        package_file_path = os.path.join(workdir, file_config['package_file'])
    
    # Build install command if auto_install is enabled
    install_cmd = ""
    if auto_install and package_file_path and os.path.exists(package_file_path) and file_config.get('install_cmd'):
        install_cmd = f"{file_config['install_cmd']} && "
    
    # Build execution command based on file type
    if file_ext == '.py':
        exec_cmd = f"python -u /workspace/{entry_file}"
    
    elif file_ext == '.sh':
        exec_cmd = f"chmod +x /workspace/{entry_file} && sh /workspace/{entry_file}"
    
    elif file_ext == '.ps1':
        exec_cmd = f"pwsh /workspace/{entry_file}"
    
    elif file_ext == '.c':
        exec_cmd = f"gcc /workspace/{entry_file} -o /workspace/a.out && chmod +x /workspace/a.out && /workspace/a.out"
    
    elif file_ext in ['.cpp', '.cc', '.cxx']:
        exec_cmd = f"g++ /workspace/{entry_file} -o /workspace/a.out && chmod +x /workspace/a.out && /workspace/a.out"
    
    elif file_ext == '.js':
        exec_cmd = f"node /workspace/{entry_file}"
    
    elif file_ext == '.ts':
        # For TypeScript, we need ts-node or compile first
        if auto_install:
            exec_cmd = f"npx ts-node /workspace/{entry_file}"
        else:
            exec_cmd = f"tsc /workspace/{entry_file} && node /workspace/{os.path.splitext(entry_file)[0]}.js"
    
    elif file_ext == '.rb':
        exec_cmd = f"ruby /workspace/{entry_file}"
    
    elif file_ext == '.go':
        exec_cmd = f"go run /workspace/{entry_file}"
    
    elif file_ext == '.java':
        class_name = os.path.splitext(os.path.basename(entry_file))[0]
        exec_cmd = f"javac /workspace/{entry_file} && java -cp /workspace {class_name}"
    
    elif file_ext == '.rs':
        if os.path.exists(os.path.join(workdir, 'Cargo.toml')):
            # Rust project with Cargo
            exec_cmd = "cargo run"
        else:
            # Single Rust file
            exec_cmd = f"rustc /workspace/{entry_file} -o /workspace/output && chmod +x /workspace/output && /workspace/output"
    
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    # Combine install and exec commands
    full_cmd = f"{install_cmd}{exec_cmd}"
    
    return ["sh", "-c", full_cmd]

# ---------------------------
# Runner Loop
# ---------------------------

@cli.command()
def runner(
    token: str = typer.Option(..., help="Authentication token"),
    server: str = typer.Option(None, help="Server URL")  # Neuer Parameter
):
    typer.echo(ascii_art)

    cfg = load_config()
    
    if server is None:
        server = cfg.get("server", "http://127.0.0.1:5000")

    save_token(token, server)
    typer.echo(f"🚀 Runner connected to {server} with token {token}")

    while True:
        task = poll_task(server, token)
        if task:
            task_id = task["id"]
            archive_file = task["archive_file"]
            entry_file = task.get("entry", "main.py")
            auto_install = task.get("auto_install", False)

            gpu = task.get("gpu")
            ram = task.get("ram")
            cpu = task.get("cpu")
            shm_size = task.get("shm_size")

            # Detect file type
            file_ext = os.path.splitext(entry_file)[1].lower()
            
            if file_ext not in FILE_TYPE_CONFIG:
                typer.secho(f"{typer.style('[ERROR]', fg='red')} Unsupported file type: {file_ext}")
                send_output(server, task_id, f"[RUNNER ERROR] Unsupported file type: {file_ext}")
                send_output(server, task_id, "[TASK_FAILED]")
                continue
            
            file_config = FILE_TYPE_CONFIG[file_ext]
            
            # Determine Docker image (task can override default)
            docker_image = task.get("docker_image") or file_config['default_image']

            typer.secho(f"{typer.style('[RUN]', fg='cyan')} Running Task {task_id} ({file_ext} file) using image {docker_image}")

            try:
                # ZIP entpacken
                workdir = tempfile.mkdtemp()
                with zipfile.ZipFile(archive_file, "r") as zf:
                    zf.extractall(workdir)

                typer.secho(f"{typer.style('[INFO]', fg='blue')} Archive extracted to: {workdir}")
                main_path = os.path.join(workdir, entry_file)

                if not os.path.exists(main_path):
                    send_output(server, task_id, f"[RUNNER ERROR] Startfile {entry_file} not found")
                    send_output(server, task_id, "[TASK_FAILED]")
                    continue

                # --- Originaldateien merken ---
                orig_files = []
                for root, dirs, files in os.walk(workdir):
                    dirs[:] = [d for d in dirs if d not in {"venv", "node_modules", "target", ".git"}]
                    for f in files:
                        rel_path = os.path.relpath(os.path.join(root, f), workdir)
                        orig_files.append(rel_path)

                # Docker base command
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

                # Build execution command
                exec_cmd = build_execution_command(entry_file, workdir, auto_install, file_ext, file_config)
                docker_cmd.extend(exec_cmd)

                typer.secho(f"{typer.style('[DOCKER]', fg='cyan')} Running: {' '.join(docker_cmd)}")

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
                        send_output(server, task_id, "[OUTPUT_DONE]")
                    except Exception as e:
                        typer.secho(f"{typer.style('[ERROR]', fg='red')} Error sending output zip: {e}")
                os.remove(output_zip)

                if proc.returncode == 0:
                    send_output(server, task_id, "[TASK_DONE]")
                    typer.secho(f"{typer.style('[OK]', fg='green')} Task done")
                else:
                    send_output(server, task_id, f"[RUNNER ERROR] Process exited with {proc.returncode}")
                    send_output(server, task_id, "[TASK_FAILED]")
                    typer.secho(f"{typer.style('[ERROR]', fg='red')} Process exited with {proc.returncode}")

            except Exception as e:
                send_output(server, task_id, f"[RUNNER ERROR] {e}")
                send_output(server, task_id, "[TASK_FAILED]")
                typer.secho(f"{typer.style('[ERROR]', fg='red')} Exception: {e}")
            finally:
                if os.path.exists(archive_file):
                    os.remove(archive_file)
                if os.path.exists(workdir):
                    shutil.rmtree(workdir)
        else:
            time.sleep(2)

if __name__ == "__main__":
    cli()