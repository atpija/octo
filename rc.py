import typer, requests, os, json

app = typer.Typer()
CONFIG_PATH = os.path.expanduser("~/.remotecompute/config.json")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

@app.command()
def login(token: str, server: str):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"token": token, "server": server}, f)
    typer.echo("✅ Konfiguration gespeichert.")

@app.command()
def run(script: str):
    cfg = load_config()
    with open(script, "r") as f:
        code = f.read()

    res = requests.post(f"{cfg['server']}/submit", json={
        "token": cfg["token"],
        "code": code
    })

    if res.ok:
        task_id = res.json()["task_id"]
        typer.echo(f"🚀 Task eingereicht: {task_id}\n📡 Warte auf Live-Ausgabe...\n")

        with requests.get(f"{cfg['server']}/stream/{task_id}", stream=True) as r:
            for line in r.iter_lines():
                if line:
                    print(line.decode())
    else:
        typer.echo("❌ Fehler beim Absenden:")
        print(res.text)

if __name__ == "__main__":
    app()
