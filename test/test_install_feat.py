import os
import subprocess
import pytest
from pathlib import Path

SERVER_URL = os.environ.get("SERVER_URL", "http://host.docker.internal:5001")
TOKEN = os.environ.get("DAILY_TOKEN", "demo-token2")

def run_cmd(cmd, timeout=30):
    """Hilfsfunktion: CLI-Befehl ausführen"""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        outs, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, _ = proc.communicate()
    return proc.returncode, outs

@pytest.fixture(autouse=True)
def ensure_login():
    """Vor jedem Test neu einloggen"""
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, f"Login failed: {output}"
    yield


# -------------------------------------------------------
# Neue Tests für auto_install
# -------------------------------------------------------

def test_config_install_flag():
    """Config: docker image setzen mit --install"""
    code, output = run_cmd(["octo", "config", "--docker", "python:3.11", "--install"])
    assert code == 0
    assert "auto_install" in output or "🐳" in output

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    assert "auto_install" in output
    assert "true" in output.lower()


def test_config_noinstall_flag():
    """Config: docker image setzen mit --noinstall"""
    code, output = run_cmd(["octo", "config", "--docker", "python:3.11", "--noinstall"])
    assert code == 0

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    assert "auto_install" in output
    assert "false" in output.lower()


def test_run_with_requirements(tmp_path):
    """Script mit requirements.txt wird automatisch installiert"""
    # Config: docker image + auto_install aktivieren
    run_cmd(["octo", "config", "--docker", "python:3.11", "--install"])

    # requirements.txt (z.B. requests)
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.31.0\n")

    main = tmp_path / "main.py"
    main.write_text("import requests; print('requests_version:', requests.__version__)")

    code, output = run_cmd(["octo", "run", str(main)], timeout=120)
    assert code == 0
    assert "requests_version:" in output
    assert "2.31.0" in output


def test_run_without_auto_install(tmp_path):
    """Script mit requirements.txt schlägt fehl, wenn auto_install = False"""
    # Config zurücksetzen auf noinstall
    run_cmd(["octo", "config", "--docker", "python:3.11", "--noinstall"])

    req = tmp_path / "requirements.txt"
    req.write_text("pandas\n")

    main = tmp_path / "main.py"
    main.write_text("import pandas; print('should fail')")

    code, output = run_cmd(["octo", "run", str(main)], timeout=60)
    # Pandas wird nicht installiert → sollte Fehler sein
    assert code != 0
    assert "ModuleNotFoundError" in output or "ImportError" in output


if __name__ == "__main__":
    import sys
    
    # Default pytest args mit besserer Ausgabe
    args = [
        "-v",              # verbose
        "-s",              # show print statements
        "--tb=short",      # shorter traceback format
        "--color=yes",     # colored output
        __file__,
    ]
    
    sys.exit(pytest.main(args))