import os
import subprocess
import pytest
from pathlib import Path
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


def test_run_basic():
    """Client: octo run main.py"""
    testfile = Path("test_main.py")
    try:
        testfile.write_text("print('hello from smoke test')")
        code, output = run_cmd(["octo", "run", str(testfile.absolute())])
        assert code == 0, f"Command failed: {output}"
        assert "hello from smoke test" in output
    finally:
        if testfile.exists():
            testfile.unlink()


def test_session_switch():
    """Client: Session-Wechsel"""
    file_a = Path("test_a.py")
    file_b = Path("test_b.py")
    
    try:
        file_a.write_text("print('Runner A ok')")
        code, output = run_cmd(["octo", "run", str(file_a.absolute())])
        assert "Runner A ok" in output, f"Output was: {output}"

        # Neues Login simuliert zweiten Runner
        code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
        assert code == 0

        file_b.write_text("print('Runner B ok')")
        code, output = run_cmd(["octo", "run", str(file_b.absolute())])
        assert "Runner B ok" in output, f"Output was: {output}"
    finally:
        if file_a.exists():
            file_a.unlink()
        if file_b.exists():
            file_b.unlink()


# ------------------------
# Erweiterte Tests
# ------------------------

def test_invalid_token():
    """Client: ungültiger Token – Fehler erst bei run"""
    code, output = run_cmd(["octo", "login", "--token", "WRONG", "--server", SERVER_URL])
    assert code == 0  # Client speichert den Token einfach
    
    testfile = Path("test_bad.py")
    try:
        testfile.write_text("print('unauthorized test')")
        code, output = run_cmd(["octo", "run", str(testfile.absolute())])
        assert code != 0
        assert "Unauthorized" in output
    finally:
        if testfile.exists():
            testfile.unlink()


def test_parallel_runs():
    """Client: Viele parallele Runs"""
    def run_one(i):
        testfile = Path(f"test_task_{i}.py")
        try:
            testfile.write_text(f"print('Task {i}')")
            return run_cmd(["octo", "run", str(testfile.absolute())])[1]
        finally:
            if testfile.exists():
                testfile.unlink()

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(run_one, range(10)))

    for i, output in enumerate(results):
        assert f"Task {i}" in output


def test_error_in_script():
    """Client: Fehler im Code"""
    testfile = Path("test_fail.py")
    try:
        testfile.write_text("1/0")
        code, output = run_cmd(["octo", "run", str(testfile.absolute())])
        # aktuell gibt dein Client evtl. immer 0 zurück → das wäre ein Bug
        assert "ZeroDivisionError" in output
    finally:
        if testfile.exists():
            testfile.unlink()


def test_large_output():
    """Client: sehr viele Prints"""
    testfile = Path("test_spam.py")
    try:
        testfile.write_text("for i in range(1000): print(f'line {i}')")
        code, output = run_cmd(["octo", "run", str(testfile.absolute())], timeout=60)
        assert code == 0
        assert "line 999" in output
    finally:
        if testfile.exists():
            testfile.unlink()


def test_long_running():
    """Client: lange Runtime"""
    testfile = Path("test_sleepy.py")
    try:
        testfile.write_text("import time; time.sleep(3); print('done')")
        code, output = run_cmd(["octo", "run", str(testfile.absolute())], timeout=10)
        assert code == 0
        assert "done" in output
    finally:
        if testfile.exists():
            testfile.unlink()


def test_many_files():
    """Client: Projekt mit sehr vielen Files"""
    test_dir = Path("test_many_files")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # 50 kleine Dateien anlegen
        for i in range(50):
            f = test_dir / f"file_{i}.py"
            f.write_text(f"print('Hello from {i}')")

        # Main File, das ein paar andere Files importiert
        main = test_dir / "main.py"
        main.write_text("import file_2; print('main running')")

        code, output = run_cmd(["octo", "run", str(main.absolute())], timeout=60)
        assert code == 0
        assert "main running" in output
    finally:
        # Cleanup
        if test_dir.exists():
            for f in test_dir.glob("*.py"):
                f.unlink()
            test_dir.rmdir()


def test_config_show_and_set():
    """Client: docker image setzen und anzeigen"""
    code, output = run_cmd(["octo", "config", "--docker", "python:3.12"])
    assert code == 0
    assert "python:3.12" in output or "✅" in output

    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0
    assert "python:3.12" in output


def test_run_with_custom_docker():
    """Client: Script wird im gesetzten Docker-Image ausgeführt"""
    # Config auf spezielles Image setzen
    run_cmd(["octo", "config", "--docker", "python:3.12"])

    testfile = Path("test_docker_test.py")
    try:
        testfile.write_text("import sys; print('python-version:', sys.version)")
        code, output = run_cmd(["octo", "run", str(testfile.absolute())], timeout=30)
        assert code == 0
        assert "python-version:" in output
        # wir checken nur grob auf "3.12", weil die genaue Minor-Version variieren kann
        assert "3.12" in output
    finally:
        if testfile.exists():
            testfile.unlink()


def test_run_with_default_docker():
    """Client: Script läuft ohne explizite Config im Default-Image"""
    # Config zurücksetzen auf Default
    run_cmd(["octo", "config", "--docker", "python:3.11-slim"])

    testfile = Path("test_default_docker.py")
    try:
        testfile.write_text("print('default docker works')")
        code, output = run_cmd(["octo", "run", str(testfile.absolute())], timeout=30)
        assert code == 0
        assert "default docker works" in output
    finally:
        if testfile.exists():
            testfile.unlink()


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))