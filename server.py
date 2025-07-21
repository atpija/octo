# server.py
from flask import Flask, request, jsonify
import subprocess
import tempfile

app = Flask(__name__)
API_TOKEN = "test123"  # einfacher Token für lokale Auth

@app.route("/execute", methods=["POST"])
def execute():
    data = request.json
    token = data.get("token")
    code = data.get("code")

    if token != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            f.flush()
            result = subprocess.run(["python3", f.name], capture_output=True, timeout=10)

        return jsonify({
            "output": result.stdout.decode(),
            "error": result.stderr.decode()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
