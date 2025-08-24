# server.py
# -----------------------------------------------------------------------------
# Octo Server:
# - /submit nimmt multipart/form-data (token, entry, archive-ZIP) entgegen
# - legt Task in Queue
# - /get_task (POST, JSON {token}) liefert Task + absolute archive_url
# - /download/<task_id> gibt ZIP aus tasks/ zurück
# - /submit_output/<task_id> nimmt Runner-Logs an
# - /stream/<task_id> streamt Logs zum Client
# - CLI: token_add, token_list, token_remove, server
# -----------------------------------------------------------------------------

from flask import Flask, request, jsonify, Response, stream_with_context, send_file
import uuid, queue, time, json, os, typer

app = Flask(__name__)
task_queue = queue.Queue()
task_output = {}  # task_id → {"lines": [...], "done": bool}

# Pfade
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TASK_DIR = os.path.join(BASE_DIR, "tasks")
os.makedirs(TASK_DIR, exist_ok=True)

CONFIG_PATH = os.path.expanduser("~/.remotecompute/serverconfig.json")
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

cli = typer.Typer(help="Octo Server CLI")

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
            config = json.load(f)
    else:
        config = {"valid_tokens": []}
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    config.setdefault("valid_tokens", [])
    return config

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

# ---------------------------
# Flask Endpoints
# ---------------------------

@app.route("/submit", methods=["POST"])
def submit():
    """Nimmt ein ZIP-Archiv vom Client an und legt einen neuen Task in die Queue."""
    token = request.form.get("token")
    entry_file = request.form.get("entry")
    config = load_config()
    if token not in config["valid_tokens"]:
        return jsonify({"error": "Unauthorized"}), 403

    file = request.files.get("archive")
    if not file or not entry_file:
        return jsonify({"error": "archive and entry required"}), 400

    # Task anlegen
    task_id = str(uuid.uuid4())
    zip_path = os.path.join(TASK_DIR, f"{task_id}.zip")
    file.save(zip_path)

    # Output-Container anlegen
    task_output[task_id] = {"lines": [], "done": False}

    # Task in Queue legen (Runner holt ihn ab)
    task_queue.put({"id": task_id, "entry": entry_file})
    print(f"📥 Task {task_id} gespeichert unter {zip_path}")

    return jsonify({"task_id": task_id})

@app.route("/get_task", methods=["POST"])
def get_task():
    """Runner fragt einen neuen Task ab."""
    data = request.json or {}
    token = data.get("token")
    config = load_config()
    if token not in config["valid_tokens"]:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        task = task_queue.get_nowait()
        print("📝 get_task liefert:", task)  # DEBUG
        return jsonify({
            "id": task["id"],
            "entry": task["entry"],
            "archive": f"{request.host_url}download/{task['id']}"
        })
    except queue.Empty:
        return jsonify({"task": None})

@app.route("/download/<task_id>")
def download(task_id):
    """Runner lädt das ZIP zum Task herunter."""
    path = os.path.join(TASK_DIR, f"{task_id}.zip")
    if not os.path.exists(path):
        return jsonify({"error": f"File not found for task {task_id}"}), 404
    return send_file(os.path.abspath(path), as_attachment=True)

@app.route("/submit_output/<task_id>", methods=["POST"])
def submit_output(task_id):
    """Runner sendet Output-Zeilen zurück."""
    line = (request.json or {}).get("line")

    if task_id not in task_output:
        return jsonify({"error": "Unknown task_id"}), 404

    if line == "[TASK_DONE]":
        task_output[task_id]["done"] = True
    elif line:
        task_output[task_id]["lines"].append(line)
    return "", 204

@app.route("/stream/<task_id>")
def stream(task_id):
    """Streamt den Output an den Client (Plaintext-Zeilen)."""
    @stream_with_context
    def generate():
        seen = 0
        while True:
            data = task_output.get(task_id)
            if not data:
                break
            lines = data["lines"]
            done = data["done"]
            while seen < len(lines):
                yield f"{lines[seen]}\n"
                seen += 1
            if done:
                break
            time.sleep(0.3)
    return Response(generate(), mimetype="text/plain")

# ---------------------------
# Typer CLI
# ---------------------------

@cli.command()
def server(host: str = "0.0.0.0", port: int = 5000):
    """Startet den Octo-Server."""
    typer.echo(ascii_art)
    typer.echo(f"🚀 Starting Octo Server on http://{host}:{port}")
    app.run(host=host, port=port)

@cli.command()
def token_add(token: str):
    """Fügt ein Token hinzu."""
    config = load_config()
    if token not in config["valid_tokens"]:
        config["valid_tokens"].append(token)
        save_config(config)
        typer.echo(f"✅ Token added: {token}")
    else:
        typer.echo("ℹ️ Token already exists")

@cli.command()
def token_list():
    """Listet alle Tokens."""
    config = load_config()
    tokens = config.get("valid_tokens", [])
    if tokens:
        typer.echo("🔐 Valid Tokens:")
        for t in tokens:
            typer.echo(f"- {t}")
    else:
        typer.echo("ℹ️ No tokens configured.")

@cli.command()
def token_remove(token: str):
    """Entfernt ein Token."""
    config = load_config()
    if token in config.get("valid_tokens", []):
        config["valid_tokens"].remove(token)
        save_config(config)
        typer.echo(f"✅ Token removed: {token}")
    else:
        typer.echo(f"❌ Token not found: {token}")

if __name__ == "__main__":
    cli()
