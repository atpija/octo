# client.py
# -----------------------------------------------------------------------------
# Octo Client:
# - `octo login --token ... --server ...` speichert Token + Server
# - `octo run path/to/script.py` packt den gesamten Projektordner in ein ZIP,
#   und sendet ZIP + Entry-File-Name an den Server.
# - Streamt Live-Output zurück (Realtime Logs).
# -----------------------------------------------------------------------------

import typer, requests, os, json, zipfile, tempfile, sys

app = typer.Typer()
CONFIG_PATH = os.path.expanduser("~/.remotecompute/config.json")

# ---------------------------
# Hilfsfunktionen
# ---------------------------

def load_config():
    """Lädt gespeicherte Konfiguration (Token + Server)."""
    if not os.path.exists(CONFIG_PATH):
        raise typer.BadParameter("Keine Config gefunden. Bitte zuerst `octo login` ausführen.")
    with open(CONFIG_PATH) as f:
        return json.load(f)

def zip_project(entry_path: str) -> tuple[str, str]:
    """
    Packt den gesamten Ordner des Entry-Files in ein temporäres ZIP.
    Gibt (zip_path, entry_file_relpfad) zurück.
    - entry_file_relpfad ist der relative Pfad zum Projektwurzel, z.B. 'sub/test.py'
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
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                zf.write(file_path, rel_path)
    return tmp.name, entry_rel

# ---------------------------
# Typer CLI Commands
# ---------------------------

@app.command()
def login(token: str = typer.Option(..., help="Auth-Token vom Server"),
          server: str = typer.Option(..., help="Server-URL, z.B. http://127.0.0.1:5000")):
    """Speichert Token + Server-Adresse."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"token": token, "server": server}, f)
    typer.echo("✅ Configuration saved.")

@app.command()
def run(path: str = typer.Argument(..., help="Pfad zum Start-Script (Entry-File)")):
    """
    Reicht einen Task beim Server ein:
    - ZIP mit komplettem Projektordner
    - Entry-File-Relative Pfad
    - Token per Form-Feld
    Streamt anschließend Live-Output.
    """
    cfg = load_config()
    archive, entry_rel = zip_project(path)

    with open(archive, "rb") as f:
        res = requests.post(
            f"{cfg['server']}/submit",
            data={"token": cfg["token"], "entry": entry_rel},
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
                    break
                else:
                    print(msg)
                sys.stdout.flush()
    else:
        typer.echo("❌ Error while submitting:")
        print(res.text)

if __name__ == "__main__":
    app()
