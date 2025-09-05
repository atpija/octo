# server.py
# (um Ressourcenoptionen erweitert)
# -----------------------------------------------------------------------------

from flask import Flask, request, jsonify, Response, stream_with_context, send_file
import uuid, queue, time, json, os, typer

app = Flask(__name__)
task_queue = queue.Queue()
task_output = {}

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
# Config
# ---------------------------

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"valid_tokens": []}

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ---------------------------
# Flask Endpoints
# ---------------------------

@app.route("/submit", methods=["POST"])
def submit():
    token = request.form.get("token")
    entry_file = request.form.get("entry")
    docker_image = request.form.get("docker_image")
    auto_install = request.form.get("auto_install") == "true"

    gpu = request.form.get("gpu")
    ram = request.form.get("ram")
    cpu = request.form.get("cpu")
    shm_size = request.form.get("shm_size")

    cfg = load_config()
    if token not in cfg["valid_tokens"]:
        return jsonify({"error": "Unauthorized"}), 403

    file = request.files.get("archive")
    if not file or not entry_file:
        return jsonify({"error": "archive and entry required"}), 400

    task_id = str(uuid.uuid4())
    zip_path = os.path.join(TASK_DIR, f"{task_id}.zip")
    file.save(zip_path)

    task_output[task_id] = {"lines": [], "done": False}

    task = {
        "id": task_id,
        "entry": entry_file,
        "docker_image": docker_image,
        "auto_install": auto_install,
        "gpu": gpu,
        "ram": ram,
        "cpu": cpu,
        "shm_size": shm_size,
    }
    task_queue.put(task)

    return jsonify({"task_id": task_id})

@app.route("/get_task", methods=["POST"])
def get_task():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    cfg = load_config()
    if token not in cfg["valid_tokens"]:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        task = task_queue.get_nowait()
        return jsonify({
            "task": {
                "id": task["id"],
                "entry": task["entry"],
                "docker_image": task.get("docker_image"),
                "auto_install": task.get("auto_install", False),
                "gpu": task.get("gpu"),
                "ram": task.get("ram"),
                "cpu": task.get("cpu"),
                "shm_size": task.get("shm_size"),
                "archive": f"/download/{task['id']}"
            }
        })
    except queue.Empty:
        return jsonify({"task": None})

@app.route("/download/<task_id>")
def download(task_id):
    path = os.path.join(TASK_DIR, f"{task_id}.zip")
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(os.path.abspath(path), as_attachment=True)

@app.route("/submit_output/<task_id>", methods=["POST"])
def submit_output(task_id):
    data = request.get_json(silent=True) or {}
    line = data.get("line")
    if task_id not in task_output:
        return jsonify({"error": "Unknown task"}), 404
    if line == "[TASK_DONE]":
        task_output[task_id]["done"] = True
    elif line:
        task_output[task_id]["lines"].append(line)
    return "", 204

@app.route("/stream/<task_id>")
def stream(task_id):
    @stream_with_context
    def generate():
        seen = 0
        while True:
            data = task_output.get(task_id)
            if not data: break
            lines = data["lines"]
            done = data["done"]
            while seen < len(lines):
                yield f"{lines[seen]}\n"
                seen += 1
            if done: break
            time.sleep(0.3)
    return Response(generate(), mimetype="text/plain")

# ---------------------------
# Typer CLI
# ---------------------------

@cli.command()
def server(host: str = "0.0.0.0", port: int = 5000):
    typer.echo(ascii_art)
    typer.echo("🚀 Starting Octo Server...")
    app.run(host=host, port=port)

@cli.command()
def token_add(token: str):
    cfg = load_config()
    if token not in cfg["valid_tokens"]:
        cfg["valid_tokens"].append(token)
        save_config(cfg)
        typer.echo(f"✅ Token added: {token}")
    else:
        typer.echo("ℹ️ Token already exists")

@cli.command()
def token_list():
    cfg = load_config()
    tokens = cfg.get("valid_tokens", [])
    if tokens:
        typer.echo("🔐 Valid Tokens:")
        for t in tokens: typer.echo(f"- {t}")
    else:
        typer.echo("ℹ️ No tokens configured.")

@cli.command()
def token_remove(token: str):
    cfg = load_config()
    if token in cfg.get("valid_tokens", []):
        cfg["valid_tokens"].remove(token)
        save_config(cfg)
        typer.echo(f"✅ Token removed: {token}")
    else:
        typer.echo(f"❌ Token not found: {token}")

if __name__ == "__main__":
    cli()
