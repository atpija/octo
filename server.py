from flask import Flask, request, jsonify, Response, stream_with_context
import uuid
import queue
import time
import json
import os

# Lade Konfiguration aus ~/.remotecompute/config.json
CONFIG_PATH = os.path.expanduser("~/.remotecompute/config.json")

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError("❌ config.json nicht gefunden. Bitte zuerst mit 'rc login' konfigurieren.")

with open(CONFIG_PATH) as f:
    config = json.load(f)

API_TOKEN = config["token"]  # Kein Fallback mehr – muss vorhanden sein

app = Flask(__name__)

task_queue = queue.Queue()
task_output = {}  # task_id → {"lines": [...], "done": bool}

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    if data.get("token") != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    task_id = str(uuid.uuid4())
    task = {"id": task_id, "code": data["code"]}
    task_output[task_id] = {"lines": [], "done": False}
    task_queue.put(task)
    return jsonify({"task_id": task_id})

@app.route("/get_task", methods=["POST"])
def get_task():
    data = request.json
    if data.get("token") != API_TOKEN:
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
