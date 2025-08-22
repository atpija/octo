import time, json, requests, subprocess, tempfile, os, typer

cli = typer.Typer(help="Octo Runner CLI")

CONFIG_PATH = os.path.expanduser("~/.remotecompute/serverconfig.json")

ascii_art = r"""
                __       
  ____   _____ / /_ ____ 
 / __ \ / ___// __// __ \
/ /_/ // /__ / /_ / /_/ /
\____/ \___/ \__/ \____/
"""

def load_config():
    """Lädt bestehende Config, falls vorhanden."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"valid_tokens": [], "server": "http://127.0.0.1:5000"}

def save_token(token, server):
    """Speichert einen neuen Token optional in der Config, ohne alte zu löschen."""
    cfg = load_config()
    if token not in cfg.get("valid_tokens", []):
        cfg.setdefault("valid_tokens", []).append(token)
    cfg["server"] = server
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def poll_task(server, token):
    try:
        res = requests.post(f"{server}/get_task", json={"token": token})
        if res.ok:
            task = res.json()
            if task.get("id") and task.get("code"):
                return task
    except Exception as e:
        print(f"❌ Error while calling Tasks: {e}")
    return None

def send_output(server, task_id, line):
    try:
        requests.post(f"{server}/submit_output/{task_id}", json={"line": line})
    except Exception as e:
        print(f"❌ Error while sending output: {e}")

@cli.command()
def runner(
    token: str = typer.Option(..., help="Authentication token"),  # zwingend
    server: str = typer.Option("http://127.0.0.1:5000", help="Server URL")
):
    """
    Starte den Octo Runner mit Token.
    """
    typer.echo(ascii_art)
    save_token(token, server)

    typer.echo(f"🚀 Runner connected to {server} with token {token}")

    while True:
        task = poll_task(server, token)

        if task:
            task_id = task["id"]
            code = task["code"]

            print(f"⚡ Running Task {task_id}")

            try:
                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
                    f.write(code)
                    f.flush()

                    proc = subprocess.Popen(
                        ["python3", "-u", f.name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )

                    for line in proc.stdout:
                        send_output(server, task_id, line.strip())

                    proc.stdout.close()
                    proc.wait()
                    send_output(server, task_id, "[TASK_DONE]")
                    print("✅ Task done")
            except Exception as e:
                send_output(server, task_id, f"[RUNNER ERROR] {e}")
        else:
            time.sleep(2)

if __name__ == "__main__":
    cli()
