# client.py
# -----------------------------------------------------------------------------
# Octo Client:
# - login: Token + Server speichern
# - run: packt Projekt (Ordner des Entry-Files) in ZIP und schickt es an den Server
# - config --docker: setzt Docker Image
# - config --show: zeigt aktuelle Config
# - config --gpu/--ram/--cpu/--shm-size: setzt Ressourcenoptionen
# -----------------------------------------------------------------------------

import typer, requests, os, json, zipfile, tempfile, sys, io
from pathlib import Path

app = typer.Typer(help="Octo Client CLI")

# --- Version ---
def version_callback(value: bool):
    if value:
        typer.echo("octo 0.2.1")
        raise typer.Exit()

@app.callback()
def main(version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True)):
    pass

CONFIG_PATH = os.path.expanduser("~/.remotecompute/config.json")
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

# Sicherstellen, dass stdout/stderr UTF-8 ist (für Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')


# ---------------------------
# Hilfsfunktionen
# ---------------------------

def load_config():
    """Loads saved Config (Token + Server + Docker-Image)."""
    if not os.path.exists(CONFIG_PATH):
        raise typer.BadParameter("No Config found. Please use `octo login` first.")
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def zip_project(entry_path: str) -> tuple[str, str, str]:
    """
    Packt den gesamten Ordner des Entry-Files in ein temporäres ZIP.
    Schließt Ordner 'venv/', '__pycache__', 'site-packages', '*.dist-info' und versteckte Dateien aus.
    Gibt (zip_path, entry_file_relpfad, project_dir) zurück.
    """
    entry_abs = os.path.abspath(entry_path)
    if not os.path.isfile(entry_abs):
        raise typer.BadParameter(f"Entry-File existiert nicht: {entry_abs}")

    project_dir = os.path.dirname(entry_abs)
    entry_rel = os.path.relpath(entry_abs, project_dir)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_dir):
            # Verzeichnisse filtern
            dirs[:] = [
                d for d in dirs
                if not (
                    d.lower() == "venv"
                    or d == "__pycache__"
                    or d == "site-packages"
                    or d.endswith(".dist-info")
                    or d.startswith(".")
                )
            ]
            for file in files:
                if file.startswith("."):
                    continue
                if file.endswith(".pyc"):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                zf.write(file_path, rel_path)
    return tmp.name, entry_rel, project_dir

# ---------------------------
# Typer CLI Commands
# ---------------------------

@app.command()
def login(token: str = typer.Option(..., help="Auth-Token vom Server"),
          server: str = typer.Option(..., help="Server-URL, z.B. http://127.0.0.1:5000")):
    """saves Config (Token + Server)."""
    cfg = {"token": token, "server": server, "docker_image": "python:3.11"}
    save_config(cfg)
    typer.secho(f"{typer.style('[OK]', fg='green')} Configuration saved.")

@app.command()
def run(path: str = typer.Argument(..., help="specify your main file (main.py/main.c etc.)")):
    """
    Sets up a Task on your Server:
    - ZIP with your whole project (excluding venv/)
    - passes entry + docker_image
    - streams Live-Output
    - downloads new/changed files from Runner into workspace
    """
    cfg = load_config()
    archive, entry_rel, project_dir = zip_project(path)

    # --- Task auf Server senden ---
    with open(archive, "rb") as f:
        res = requests.post(
            f"{cfg['server']}/submit",
            data={
                "token": cfg["token"],
                "entry": entry_rel,
                "docker_image": cfg.get("docker_image", "python:3.11"),
                "auto_install": json.dumps(cfg.get("auto_install", False)),
                "gpu": cfg.get("gpu"),
                "ram": cfg.get("ram"),
                "cpu": cfg.get("cpu"),
                "shm_size": cfg.get("shm_size"),
            },
            files={"archive": f},
            timeout=60
        )

    os.remove(archive)

    if not res.ok:
        typer.secho(f"{typer.style('[ERROR]', fg='red')} Error while submitting:")
        typer.secho(res.text, fg='red')
        sys.exit(1)

    task_id = res.json()["task_id"]
    typer.secho(f"{typer.style('[SUBMIT]', fg='cyan')} Task submitted: {task_id}")
    typer.secho(f"{typer.style('[WAIT]', fg='yellow')} Waiting for Live-Output...\n")

    # --- Live-Output streamen ---
    task_done = False
    output_done = False

    with requests.get(f"{cfg['server']}/stream/{task_id}", stream=True) as r:
        for line in r.iter_lines():
            if not line:
                continue
            msg = line.decode().strip()

            if msg == "[TASK_FAILED]":
                typer.secho(f"{typer.style('[ERROR]', fg='red')} Task failed")
                sys.exit(1)

            elif msg == "[OUTPUT_DONE]":
                typer.secho(f"{typer.style('[INFO]', fg='blue')} Output ZIP uploaded by Runner, downloading...")
                try:
                    out_res = requests.get(f"{cfg['server']}/download_output/{task_id}", stream=True)
                    if out_res.status_code == 200:
                        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
                        for chunk in out_res.iter_content(chunk_size=8192):
                            tmp_zip.write(chunk)
                        tmp_zip.close()

                        # Entpacken ins Projektverzeichnis, Unterordner erstellen falls nötig
                        with zipfile.ZipFile(tmp_zip.name, "r") as zf:
                            typer.secho(f"{typer.style('[LIST]', fg='blue')} Output ZIP contains:")
                            for f in zf.namelist():
                                typer.secho(f"{typer.style('-', fg='blue')} {f}")
                                target_path = os.path.join(project_dir, f)
                                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                with open(target_path, "wb") as out_f:
                                    out_f.write(zf.read(f))
                        os.remove(tmp_zip.name)
                        typer.secho(f"{typer.style('[OK]', fg='green')} New/changed files downloaded from Runner.")
                        output_done = True
                    else:
                        typer.secho(f"{typer.style('[INFO]', fg='yellow')} No output ZIP found from Runner.")
                except Exception as e:
                    typer.secho(f"{typer.style('[ERROR]', fg='red')} Error downloading output ZIP: {e}")

            elif msg == "[TASK_DONE]":
                typer.secho(f"{typer.style('[OK]', fg='green')} Task finished successfully")
                task_done = True

            else:
                print(msg)
            sys.stdout.flush()

            if task_done and output_done:
                break

@app.command()
def config(
    docker: str = typer.Option(None, "--docker", help="Set Docker Image"),
    install: bool = typer.Option(None, "--install/--noinstall", help="Auto-install requirements.txt"),
    gpu: str = typer.Option(None, "--gpu", help="Set GPU option, e.g. 'all' or 'device=0'"),
    ram: str = typer.Option(None, "--ram", help="Set RAM limit, e.g. '8g'"),
    cpu: str = typer.Option(None, "--cpu", help="Set CPU limit, e.g. '4'"),
    shm_size: str = typer.Option(None, "--shm-size", help="Set shared memory size, e.g. '2g'"),
    show: bool = typer.Option(False, "--show", help="Show current config")
):
    """set Docker-Image, resources, toggle Auto-Install or show Config."""
    cfg = load_config()
    changed = False

    if docker:
        cfg["docker_image"] = docker
        typer.secho(f"{typer.style('[CONFIG]', fg='cyan')} Docker-Image set: {docker}")
        changed = True
    if install is not None:
        cfg["auto_install"] = install
        msg = "Auto-Install active" if install else "Auto-Install deactive"
        color = "green" if install else "yellow"
        typer.secho(f"{typer.style('[CONFIG]', fg=color)} {msg}")
        changed = True
    if gpu is not None:
        cfg["gpu"] = gpu
        typer.secho(f"{typer.style('[CONFIG]', fg='cyan')} GPU set: {gpu}")
        changed = True
    if ram is not None:
        cfg["ram"] = ram
        typer.secho(f"{typer.style('[CONFIG]', fg='cyan')} RAM set: {ram}")
        changed = True
    if cpu is not None:
        cfg["cpu"] = cpu
        typer.secho(f"{typer.style('[CONFIG]', fg='cyan')} CPU set: {cpu}")
        changed = True
    if shm_size is not None:
        cfg["shm_size"] = shm_size
        typer.secho(f"{typer.style('[CONFIG]', fg='cyan')} Shared Memory set: {shm_size}")
        changed = True

    if changed:
        save_config(cfg)

    if show:
        typer.secho(f"{typer.style('[CONFIG]', fg='cyan')} Active Config:")
        typer.secho(json.dumps(cfg, indent=2), fg='blue')

    if not (docker or install is not None or gpu or ram or cpu or shm_size or show):
        typer.secho(f"{typer.style('[INFO]', fg='yellow')} Options: --docker IMAGE | --install/--noinstall | --gpu OPT | --ram OPT | --cpu OPT | --shm-size OPT | --show")

@app.command()
def build(
    dockerfile: str = typer.Argument(..., help="Path to Dockerfile"),
    tag: str = typer.Option(..., "--tag", "-t", help="Image name:tag, e.g. myimage:latest")
):
    """Builds a Docker image on the Runner from a Dockerfile."""
    cfg = load_config()
    
    dockerfile_abs = os.path.abspath(dockerfile)
    if not os.path.isfile(dockerfile_abs):
        typer.secho(f"{typer.style('[ERROR]', fg='red')} Dockerfile not found: {dockerfile_abs}")
        sys.exit(1)

    typer.secho(f"{typer.style('[BUILD]', fg='cyan')} Sending Dockerfile to server...")

    with open(dockerfile_abs, "rb") as f:
        res = requests.post(
            f"{cfg['server']}/build",
            data={"token": cfg["token"], "tag": tag},
            files={"dockerfile": f},
            timeout=60
        )

    if not res.ok:
        typer.secho(f"{typer.style('[ERROR]', fg='red')} {res.text}")
        sys.exit(1)

    task_id = res.json()["task_id"]
    typer.secho(f"{typer.style('[WAIT]', fg='yellow')} Building image '{tag}'...\n")

    with requests.get(f"{cfg['server']}/stream/{task_id}", stream=True) as r:
        for line in r.iter_lines():
            if not line:
                continue
            msg = line.decode().strip()
            if msg == "[TASK_DONE]":
                typer.secho(f"{typer.style('[OK]', fg='green')} Image '{tag}' built successfully")
                break
            elif msg == "[TASK_FAILED]":
                typer.secho(f"{typer.style('[ERROR]', fg='red')} Build failed")
                sys.exit(1)
            else:
                print(msg)
            sys.stdout.flush()

if __name__ == "__main__":
    app()
