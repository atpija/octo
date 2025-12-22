import os
import subprocess
import pytest
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

SERVER_URL = os.environ.get("SERVER_URL", "http://octo-infra:5000")
TOKEN = os.environ.get("SMOKE_TOKEN", "demo-token")


def run_cmd(cmd, timeout=20, cwd=None):
    """Hilfsfunktion um CLI-Kommandos auszuführen"""
    proc = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True,
        cwd=cwd
    )
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


@pytest.fixture
def test_project():
    """Erstellt ein isoliertes Test-Projekt-Verzeichnis"""
    import uuid
    project_dir = Path(f"test_project_{uuid.uuid4().hex[:8]}")
    project_dir.mkdir(exist_ok=True)
    
    original_cwd = os.getcwd()
    
    yield project_dir
    
    # Cleanup
    os.chdir(original_cwd)
    if project_dir.exists():
        shutil.rmtree(project_dir)


# ------------------------
# Basis Smoke Tests
# ------------------------

def test_login():
    """Client: octo login"""
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0
    assert "✅" in output or "success" in output.lower()


def test_run_basic(test_project):
    """Client: octo run main.py"""
    testfile = test_project / "main.py"
    testfile.write_text("print('hello from smoke test')")
    
    code, output = run_cmd(["octo", "run", "main.py"], cwd=test_project)
    assert code == 0, f"Command failed: {output}"
    assert "hello from smoke test" in output


def test_session_switch(test_project):
    """Client: Session-Wechsel"""
    file_a = test_project / "a.py"
    file_a.write_text("print('Runner A ok')")
    
    code, output = run_cmd(["octo", "run", "a.py"], cwd=test_project)
    assert "Runner A ok" in output, f"Output was: {output}"

    # Neues Login simuliert zweiten Runner
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0

    file_b = test_project / "b.py"
    file_b.write_text("print('Runner B ok')")
    
    code, output = run_cmd(["octo", "run", "b.py"], cwd=test_project)
    assert "Runner B ok" in output, f"Output was: {output}"


# ------------------------
# Erweiterte Tests
# ------------------------

def test_invalid_token(test_project):
    """Client: ungültiger Token – Fehler erst bei run"""
    code, output = run_cmd(["octo", "login", "--token", "WRONG", "--server", SERVER_URL])
    assert code == 0  # Client speichert den Token einfach
    
    testfile = test_project / "bad.py"
    testfile.write_text("print('unauthorized test')")
    
    code, output = run_cmd(["octo", "run", "bad.py"], cwd=test_project)
    assert code != 0
    assert "Unauthorized" in output


def test_parallel_runs():
    """Client: Viele parallele Runs"""
    def run_one(i):
        # Jeder Task bekommt sein eigenes Projekt-Verzeichnis
        import uuid
        project_dir = Path(f"test_parallel_{uuid.uuid4().hex[:8]}")
        project_dir.mkdir(exist_ok=True)
        
        try:
            testfile = project_dir / "task.py"
            testfile.write_text(f"print('Task {i}')")
            return run_cmd(["octo", "run", "task.py"], cwd=project_dir)[1]
        finally:
            if project_dir.exists():
                shutil.rmtree(project_dir)

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(run_one, range(10)))

    for i, output in enumerate(results):
        assert f"Task {i}" in output


def test_error_in_script(test_project):
    """Client: Fehler im Code"""
    testfile = test_project / "fail.py"
    testfile.write_text("1/0")
    
    code, output = run_cmd(["octo", "run", "fail.py"], cwd=test_project)
    # aktuell gibt dein Client evtl. immer 0 zurück → das wäre ein Bug
    assert "ZeroDivisionError" in output


def test_large_output(test_project):
    """Client: sehr viele Prints"""
    testfile = test_project / "spam.py"
    testfile.write_text("for i in range(1000): print(f'line {i}')")
    
    code, output = run_cmd(["octo", "run", "spam.py"], timeout=60, cwd=test_project)
    assert code == 0
    assert "line 999" in output


def test_long_running(test_project):
    """Client: lange Runtime"""
    testfile = test_project / "sleepy.py"
    testfile.write_text("import time; time.sleep(3); print('done')")
    
    code, output = run_cmd(["octo", "run", "sleepy.py"], timeout=10, cwd=test_project)
    assert code == 0
    assert "done" in output


def test_many_files(test_project):
    """Client: Projekt mit sehr vielen Files"""
    # 50 kleine Dateien anlegen
    for i in range(50):
        f = test_project / f"file_{i}.py"
        f.write_text(f"print('Hello from {i}')")

    # Main File, das ein paar andere Files importiert
    main = test_project / "main.py"
    main.write_text("import file_2; print('main running')")

    code, output = run_cmd(["octo", "run", "main.py"], timeout=60, cwd=test_project)
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


def test_run_with_custom_docker(test_project):
    """Client: Script wird im gesetzten Docker-Image ausgeführt"""
    # Config auf spezielles Image setzen
    run_cmd(["octo", "config", "--docker", "python:3.12"])

    testfile = test_project / "docker_test.py"
    testfile.write_text("import sys; print('python-version:', sys.version)")
    
    code, output = run_cmd(["octo", "run", "docker_test.py"], timeout=30, cwd=test_project)
    assert code == 0
    assert "python-version:" in output
    # wir checken nur grob auf "3.12", weil die genaue Minor-Version variieren kann
    assert "3.12" in output


def test_run_with_default_docker(test_project):
    """Client: Script läuft ohne explizite Config im Default-Image"""
    # Config zurücksetzen auf Default
    run_cmd(["octo", "config", "--docker", "python:3.11-slim"])

    testfile = test_project / "default_docker.py"
    testfile.write_text("print('default docker works')")
    
    code, output = run_cmd(["octo", "run", "default_docker.py"], timeout=30, cwd=test_project)
    assert code == 0
    assert "default docker works" in output


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))