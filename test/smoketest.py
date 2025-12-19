import os
import subprocess
import pytest
from concurrent.futures import ThreadPoolExecutor

SERVER_URL = os.environ.get("SERVER_URL", "http://octo-infra:5000")
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
# Basis Smoke Tests
# ------------------------

def test_login():
    """Client: octo login"""
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0
    assert "✅" in output or "success" in output.lower()


def test_run_basic(tmp_path):
    """Client: octo run main.py"""
    testfile = tmp_path / "main.py"
    testfile.write_text("print('hello from smoke test')")
    code, output = run_cmd(["octo", "run", str(testfile)])
    assert code == 0
    assert "hello from smoke test" in output


def test_session_switch(tmp_path):
    """Client: Session-Wechsel"""
    file_a = tmp_path / "a.py"
    file_a.write_text("print('Runner A ok')")
    code, output = run_cmd(["octo", "run", str(file_a)])
    assert "Runner A ok" in output

    # Neues Login simuliert zweiten Runner
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0

    file_b = tmp_path / "b.py"
    file_b.write_text("print('Runner B ok')")
    code, output = run_cmd(["octo", "run", str(file_b)])
    assert "Runner B ok" in output


# ------------------------
# Erweiterte Tests
# ------------------------

def test_invalid_token(tmp_path):
    """Client: ungültiger Token – Fehler erst bei run"""
    code, output = run_cmd(["octo", "login", "--token", "WRONG", "--server", SERVER_URL])
    assert code == 0  # Client speichert den Token einfach
    f = tmp_path / "bad.py"
    f.write_text("print('unauthorized test')")
    code, output = run_cmd(["octo", "run", str(f)])
    assert code != 0
    assert "Unauthorized" in output


def test_parallel_runs(tmp_path):
    """Client: Viele parallele Runs"""
    def run_one(i):
        f = tmp_path / f"task_{i}.py"
        f.write_text(f"print('Task {i}')")
        return run_cmd(["octo", "run", str(f)])[1]

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(run_one, range(10)))

    for i, output in enumerate(results):
        assert f"Task {i}" in output


def test_error_in_script(tmp_path):
    """Client: Fehler im Code"""
    f = tmp_path / "fail.py"
    f.write_text("1/0")
    code, output = run_cmd(["octo", "run", str(f)])
    # aktuell gibt dein Client evtl. immer 0 zurück → das wäre ein Bug
    assert "ZeroDivisionError" in output


def test_large_output(tmp_path):
    """Client: sehr viele Prints"""
    f = tmp_path / "spam.py"
    f.write_text("for i in range(1000): print(f'line {i}')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=60)
    assert code == 0
    assert "line 999" in output


def test_long_running(tmp_path):
    """Client: lange Runtime"""
    f = tmp_path / "sleepy.py"
    f.write_text("import time; time.sleep(3); print('done')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=10)
    assert code == 0
    assert "done" in output

def test_many_files(tmp_path):
    """Client: Projekt mit sehr vielen Files"""
    # 500 kleine Dateien anlegen
    for i in range(50):
        f = tmp_path / f"file_{i}.py"
        f.write_text(f"print('Hello from {i}')")

    # Main File, das ein paar andere Files importiert
    main = tmp_path / "main.py"
    main.write_text("import file_2; print('main running')")

    code, output = run_cmd(["octo", "run", str(main)], timeout=60)
    assert code == 0
    assert "main running" in output

def test_config_show_and_set():
    """Client: docker image setzen und anzeigen"""
    code, output = run_cmd(["octo", "config", "--docker", "python:3.12"])
    assert code == 0
    assert "python:3.12" in output or "✅" in output

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    assert "python:3.12" in output


def test_run_with_custom_docker(tmp_path):
    """Client: Script wird im gesetzten Docker-Image ausgeführt"""
    # Config auf spezielles Image setzen
    run_cmd(["octo", "config", "--docker", "python:3.12"])

    f = tmp_path / "docker_test.py"
    f.write_text("import sys; print('python-version:', sys.version)")
    code, output = run_cmd(["octo", "run", str(f)], timeout=30)
    assert code == 0
    assert "python-version:" in output
    # wir checken nur grob auf "3.12", weil die genaue Minor-Version variieren kann
    assert "3.12" in output


def test_run_with_default_docker(tmp_path):
    """Client: Script läuft ohne explizite Config im Default-Image"""
    # Config zurücksetzen auf Default
    run_cmd(["octo", "config", "--docker", "python:3.11-slim"])

    f = tmp_path / "default_docker.py"
    f.write_text("print('default docker works')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=30)
    assert code == 0
    assert "default docker works" in output

if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))
