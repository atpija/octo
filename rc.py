# rc.py
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

    res = requests.post(f"{cfg['server']}/execute", json={
        "token": cfg["token"],
        "code": code
    })

    if res.ok:
        data = res.json()
        typer.echo("📤 Ausgabe:")
        print(data["output"])
        if data["error"]:
            typer.echo("⚠️ Fehler:")
            print(data["error"])
    else:
        typer.echo("❌ Fehler:")
        print(res.text)

if __name__ == "__main__":
    app()
