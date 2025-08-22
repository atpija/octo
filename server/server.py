from flask import Flask, request, jsonify, Response, stream_with_context
import uuid
import queue
import time
import json
import os
import typer
import threading

app = Flask(__name__)
task_queue = queue.Queue()
task_output = {}  # task_id → {"lines": [...], "done": bool}

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

def add_token(token: str):
    config = load_config()
    if token not in config["valid_tokens"]:
        config["valid_tokens"].append(token)
        save_config(config)
        typer.echo(f"✅ Token added: {token}")
    else:
        typer.echo(f"ℹ️ Token already exists: {token}")

def remove_token(token: str):
    config = load_config()
    if token in config["valid_tokens"]:
        config["valid_tokens"].remove(token)
        save_config(config)
        typer.echo(f"✅ Token removed: {token}")
    else:
        typer.echo(f"❌ Token not found: {token}")

def list_tokens():
    config = load_config()
    if config["valid_tokens"]:
        typer.echo("🔐 Valid Tokens:")
        for t in config["valid_tokens"]:
            typer.echo(f"- {t}")
    else:
        typer.echo("ℹ️ No tokens configured.")

# ---------------------------
# Flask Endpoints
# ---------------------------

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    token = data.get("token")
    config = load_config()
    if token not in config["valid_tokens"]:
        return jsonify({"error": "Unauthorized"}), 403

    task_id = str(uuid.uuid4())
    task = {"id": task_id, "code": data["code"]}
    task_output[task_id] = {"lines": [], "done": False}
    task_queue.put(task)
    return jsonify({"task_id": task_id})

@app.route("/get_task", methods=["POST"])
def get_task():
    data = request.json
    token = data.get("token")
    config = load_config()
    if token not in config["valid_tokens"]:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        task = task_queue.get_nowait()
        return jsonify(task)
    except queue.Empty:
        return jsonify({"task": None})

@app.route("/submit_output/<task_id>", methods=["POST"])
def submit_output(task_id):
    line = request.json.get("line")

    if task_id not in task_output:
        return jsonify({"error": "Unknown task_id"}), 404

    if line == "[TASK_DONE]":
        task_output[task_id]["done"] = True
    else:
        task_output[task_id]["lines"].append(line)

    return "", 204

@app.route("/stream/<task_id>")
def stream(task_id):
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

            time.sleep(0.5)

    return Response(generate(), mimetype="text/plain")

# ---------------------------
# Typer CLI Commands
# ---------------------------

@cli.command()
def server(host: str = "0.0.0.0", port: int = 5000):
    """
    Starte den Octo-Server.
    """
    typer.echo(ascii_art)
    config = load_config()
    typer.echo(f"🚀 Starting Octo Server on http://{host}:{port}")
    app.run(host=host, port=port)

@cli.command()
def token_add(token: str):
    """Füge einen neuen Token hinzu."""
    add_token(token)

@cli.command()
def token_remove(token: str):
    """Entferne einen Token."""
    remove_token(token)

@cli.command()
def token_list():
    """Liste alle gültigen Tokens auf."""
    list_tokens()

if __name__ == "__main__":
    cli()
