from flask import Flask, request, jsonify, Response, stream_with_context
import uuid
import queue
import time
import json
import os
import typer

CONFIG_PATH = "~/.remotecompute/serverconfig.json"
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

ascii_art = r"""
                __       
  ____   _____ / /_ ____ 
 / __ \ / ___// __// __ \
/ /_/ // /__ / /_ / /_/ /
\____/ \___/ \__/ \____/ 
"""

typer.echo(ascii_art)

# Falls Datei nicht existiert oder leer ist: Token abfragen und Datei schreiben
if not os.path.exists(CONFIG_PATH) or os.stat(CONFIG_PATH).st_size == 0:
    token = input("🔐 Bitte Token für diesen Server eingeben: ").strip()
    config = {"valid_tokens": [token]}
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✅ Token gespeichert unter {CONFIG_PATH}")
else:
    # Datei existiert, lade Konfiguration
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Prüfe, ob gültige Tokens vorhanden sind
    if "valid_tokens" not in config:
        config["valid_tokens"] = []

    # Token abfragen, falls gewünscht
    new_token = input("➕ Optional: Weiteren Token hinzufügen? (leer lassen zum Überspringen): ").strip()
    if new_token:
        if new_token not in config["valid_tokens"]:
            config["valid_tokens"].append(new_token)
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)
            print("✅ Neuer Token hinzugefügt.")
        else:
            print("ℹ️ Token bereits vorhanden.")

VALID_TOKENS = config["valid_tokens"]

app = Flask(__name__)
task_queue = queue.Queue()
task_output = {}  # task_id → {"lines": [...], "done": bool}

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    if data.get("token") not in VALID_TOKENS:
        return jsonify({"error": "Unauthorized"}), 403

    task_id = str(uuid.uuid4())
    task = {"id": task_id, "code": data["code"]}
    task_output[task_id] = {"lines": [], "done": False}
    task_queue.put(task)
    return jsonify({"task_id": task_id})

@app.route("/get_task", methods=["POST"])
def get_task():
    data = request.json
    if data.get("token") not in VALID_TOKENS:
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
