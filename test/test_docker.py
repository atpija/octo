import os
import subprocess
import pytest

SERVER_URL = os.environ.get("SERVER_URL", "http://host.docker.internal:5001")
TOKEN = os.environ.get("DAILY_TOKEN", "demo-token3")
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"


def run_cmd(cmd, timeout=20):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        outs, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, _ = proc.communicate()
    return proc.returncode, outs


@pytest.fixture(autouse=True)
def ensure_login_and_cleanup():
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, f"Login failed: {output}"
    yield
    # Cleanup nach jedem Test
    run_cmd(["octo", "config", "--docker", DEFAULT_DOCKER_IMAGE])


# ------------------------
# Config Tests
# ------------------------

def test_config_set_and_show():
    code, _ = run_cmd(["octo", "config", "--docker", DEFAULT_DOCKER_IMAGE])
    assert code == 0

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    assert DEFAULT_DOCKER_IMAGE in output


def test_config_resource_limits():
    settings = [
        (["octo", "config", "--gpu", "all"], "gpu"),
        (["octo", "config", "--ram", "4g"], "ram"),
        (["octo", "config", "--cpu", "2"], "cpu"),
        (["octo", "config", "--shm-size", "1g"], "shm"),
    ]

    for cmd, name in settings:
        code, output = run_cmd(cmd)
        assert code == 0, f"Setting {name} failed: {output}"

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    for key in ["gpu", "ram", "cpu", "shm"]:
        assert key in output.lower()


def test_config_install_toggle():
    code, _ = run_cmd(["octo", "config", "--install"])
    assert code == 0

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    assert "install" in output.lower()

    code, _ = run_cmd(["octo", "config", "--noinstall"])
    assert code == 0

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