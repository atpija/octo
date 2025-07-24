import time
import requests
import subprocess
import tempfile

SERVER = "http://127.0.0.1:5000"
TOKEN = "test123"

def poll_task():
    try:
        res = requests.post(f"{SERVER}/get_task", json={"token": TOKEN})
        if res.ok:
            task = res.json()
            if task.get("id") and task.get("code"):
                return task
    except Exception as e:
        print(f"[!] Fehler beim Abrufen des Tasks: {e}")
    return None

def send_output(task_id, line):
    try:
        requests.post(f"{SERVER}/submit_output/{task_id}", json={"line": line})
    except Exception as e:
        print(f"[!] Fehler beim Senden der Ausgabe: {e}")

while True:
    task = poll_task()

    if task:
        task_id = task["id"]
        code = task["code"]

        print(f"🚀 Führe Task {task_id} aus...")

        try:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                f.write(code)
                f.flush()

                # Starte Python-Prozess
                proc = subprocess.Popen(
                    ["python3", "-u", f.name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in proc.stdout:
                    send_output(task_id, line.strip())

                proc.stdout.close()
                proc.wait()
                requests.post(f"{SERVER}/submit_output/{task_id}", json={"line": "[TASK_DONE]"})
                print("Task done")
        except Exception as e:
            send_output(task_id, f"[RUNNER ERROR] {e}")
    else:
        time.sleep(2)

