# client.py
# -----------------------------------------------------------------------------
# Octo Client:
# - login: Token + Server speichern
# - run: packt Projekt (Ordner des Entry-Files) in ZIP und schickt es an den Server
# - config --docker: setzt Docker Image
# - config --show: zeigt aktuelle Config
# -----------------------------------------------------------------------------

import typer, requests, os, json, zipfile, tempfile, sys
from pathlib import Path

app = typer.Typer(help="Octo Client CLI")

CONFIG_PATH = os.path.expanduser("~/.remotecompute/config.json")
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

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
    Gibt (zip_path, entry_file_relpfad, project_dir) zurück.
    """
    entry_abs = os.path.abspath(entry_path)
    if not os.path.isfile(entry_abs):
        raise typer.BadParameter(f"Entry-File existiert nicht: {entry_abs}")

    project_dir = os.path.dirname(entry_abs)
    entry_rel = os.path.relpath(entry_abs, project_dir)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file.startswith("."):  # versteckte Dateien ignorieren
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
    typer.echo("✅ Configuration saved.")

@app.command()
def run(path: str = typer.Argument(..., help="specify your main file (main.py/main.c etc.)")):
    """
    Sets up a Task on your Server:
    - ZIP with your whole project
    - passes entry + docker_image
    - streams Live-Output
    """
    cfg = load_config()
    archive, entry_rel, project_dir = zip_project(path)

    with open(archive, "rb") as f:
        res = requests.post(
            f"{cfg['server']}/submit",
            data={
                "token": cfg["token"],
                "entry": entry_rel,
                "docker_image": cfg.get("docker_image", "python:3.11"),
            },
            files={"archive": f},
            timeout=60
        )

    if res.ok:
        task_id = res.json()["task_id"]
        typer.echo(f"🚀 Task submitted: {task_id}\n📡 Waiting for Live-Output...\n")

        # Live-Output streamen
        with requests.get(f"{cfg['server']}/stream/{task_id}", stream=True) as r:
            for line in r.iter_lines():
                if not line:
                    continue
                msg = line.decode().strip()

                if msg == "[TASK_DONE]":
                    print("✅ Task finished successfully")
                    break
                elif msg == "[TASK_FAILED]":
                    print("❌ Task failed")
                    sys.exit(1)
                    break
                else:
                    print(msg)
                sys.stdout.flush()
    else:
        typer.echo("❌ Error while submitting:")
        print(res.text)
        sys.exit(1)

@app.command()
def config(docker: str = typer.Option(None, "--docker", help="Set Docker Image"),
           show: bool = typer.Option(False, "--show", help="Show current config")):
    """Docker-Image setzen oder Config anzeigen."""
    cfg = load_config()
    if docker:
        cfg["docker_image"] = docker
        save_config(cfg)
        typer.echo(f"🐳 Docker-Image gesetzt: {docker}")
    elif show:
        typer.echo("⚙️ Aktuelle Config:")
        typer.echo(json.dumps(cfg, indent=2))
    else:
        typer.echo("ℹ️ Optionen: --docker IMAGE | --show")

if __name__ == "__main__":
    app()
