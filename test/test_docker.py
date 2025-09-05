import os
import subprocess
import pytest

SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:5000")
TOKEN = os.environ.get("SMOKE_TOKEN", "demo-token")


def run_cmd(cmd, timeout=20):
    """Hilfsfunktion um CLI-Kommandos auszuführen"""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        outs, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, _ = proc.communicate()
    return proc.returncode, outs


@pytest.fixture(autouse=True)
def ensure_login():
    """Vor jedem Test neu einloggen mit gültigem Token"""
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, f"Login fixture failed: {output}"
    yield


# ------------------------
# Config Tests
# ------------------------

def test_config_set_and_show():
    """Config: Docker-Image setzen und anzeigen"""
    code, output = run_cmd(["octo", "config", "--docker", "python:3.11-slim"])
    assert code == 0
    assert "🐳 Docker-Image set:" in output

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    assert "python:3.11-slim" in output


def test_config_gpu_ram_cpu_shm():
    """Config: GPU / RAM / CPU / SHM-Size setzen und prüfen"""
    code, output = run_cmd(["octo", "config", "--gpu", "all"])
    assert code == 0
    assert "🎮 GPU set:" in output

    code, output = run_cmd(["octo", "config", "--ram", "4g"])
    assert code == 0
    assert "🧠 RAM set:" in output

    code, output = run_cmd(["octo", "config", "--cpu", "2"])
    assert code == 0
    assert "⚙️ CPU set:" in output

    code, output = run_cmd(["octo", "config", "--shm-size", "1g"])
    assert code == 0
    assert "📂 Shared Memory set:" in output

    # alle anzeigen
    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    for check in ["gpu", "ram", "cpu", "shm_size"]:
        assert check in output.lower()


def test_config_install_toggle():
    """Config: Auto-Install an- und ausschalten"""
    code, output = run_cmd(["octo", "config", "--install"])
    assert code == 0
    assert "📦 Auto-Install active" in output

    code, output = run_cmd(["octo", "config", "--noinstall"])
    assert code == 0
    assert "🚫 Auto-Install deactive" in output
