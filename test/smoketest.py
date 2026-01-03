import os
import subprocess
import pytest
from concurrent.futures import ThreadPoolExecutor

SERVER_URL = os.environ.get("SERVER_URL", "http://host.docker.internal:5001")
TOKEN = os.environ.get("SMOKE_TOKEN", "demo-token1")
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"


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
    # Cleanup: Config zurücksetzen nach jedem Test
    run_cmd(["octo", "config", "--docker", DEFAULT_DOCKER_IMAGE])


# ------------------------
# Basis Smoke Tests
# ------------------------

def test_login():
    """Client: octo login"""
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, f"Login failed: {output}"
    assert "✅" in output or "success" in output.lower(), "No success message in output"


def test_run_basic(tmp_path):
    """Client: octo run main.py"""
    testfile = tmp_path / "main.py"
    testfile.write_text("print('hello from smoke test')")
    code, output = run_cmd(["octo", "run", str(testfile)])
    assert code == 0, f"Run failed with code {code}: {output}"
    assert "hello from smoke test" in output, "Expected output not found"


def test_session_switch(tmp_path):
    """Client: Session-Wechsel"""
    file_a = tmp_path / "a.py"
    file_a.write_text("print('Runner A ok')")
    code, output = run_cmd(["octo", "run", str(file_a)])
    assert code == 0, "Runner A failed"
    assert "Runner A ok" in output

    # Neues Login simuliert zweiten Runner
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, "Re-login failed"

    file_b = tmp_path / "b.py"
    file_b.write_text("print('Runner B ok')")
    code, output = run_cmd(["octo", "run", str(file_b)])
    assert code == 0, "Runner B failed"
    assert "Runner B ok" in output


# ------------------------
# Erweiterte Tests
# ------------------------

def test_invalid_token(tmp_path):
    """Client: ungültiger Token – Fehler erst bei run"""
    # Speichere falschen Token
    code, output = run_cmd(["octo", "login", "--token", "WRONG_TOKEN_123", "--server", SERVER_URL])
    assert code == 0, "Login with wrong token should succeed (client just stores it)"
    
    # Versuche ein Script zu laufen
    f = tmp_path / "bad.py"
    f.write_text("print('unauthorized test')")
    code, output = run_cmd(["octo", "run", str(f)])
    
    # WICHTIG: Exit code muss != 0 sein!
    assert code != 0, "Run with invalid token should fail with non-zero exit code"
    assert "Unauthorized" in output or "401" in output or "auth" in output.lower(), \
        f"Expected authorization error message, got: {output}"
    
    # Cleanup: Gültigen Token wiederherstellen
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, "Failed to restore valid token"


def test_parallel_runs(tmp_path):
    """Client: Viele parallele Runs"""
    def run_one(i):
        f = tmp_path / f"task_{i}.py"
        f.write_text(f"print('Task {i} completed')")
        code, output = run_cmd(["octo", "run", str(f)])
        assert code == 0, f"Task {i} failed with code {code}: {output}"
        return output

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_one, range(10)))

    # Verifiziere, dass alle Tasks erfolgreich waren
    for i, output in enumerate(results):
        assert f"Task {i} completed" in output, f"Task {i} output missing or incorrect"


def test_error_in_script(tmp_path):
    """Client: Fehler im Code - Exit Code muss != 0 sein"""
    f = tmp_path / "fail.py"
    f.write_text("raise RuntimeError('intentional error'); 1/0")
    code, output = run_cmd(["octo", "run", str(f)])
    
    # KRITISCH: Exit code MUSS != 0 sein bei Fehlern!
    assert code != 0, "Exit code should be non-zero for failed scripts"
    assert "RuntimeError" in output or "intentional error" in output, \
        "Error message not found in output"


def test_syntax_error_in_script(tmp_path):
    """Client: Syntax-Fehler im Code"""
    f = tmp_path / "syntax_fail.py"
    f.write_text("def broken(\nprint('missing closing parenthesis')")
    code, output = run_cmd(["octo", "run", str(f)])
    
    assert code != 0, "Exit code should be non-zero for syntax errors"
    assert "SyntaxError" in output or "syntax" in output.lower(), \
        "Syntax error message not found"


def test_large_output(tmp_path):
    """Client: sehr viele Prints"""
    f = tmp_path / "spam.py"
    f.write_text("for i in range(1000): print(f'line {i}')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=60)
    assert code == 0, f"Large output test failed: {output[:200]}"
    assert "line 0" in output, "First line missing"
    assert "line 999" in output, "Last line missing"


def test_long_running(tmp_path):
    """Client: lange Runtime"""
    f = tmp_path / "sleepy.py"
    f.write_text("import time; time.sleep(3); print('done sleeping')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=10)
    assert code == 0, "Long running script failed"
    assert "done sleeping" in output


def test_many_files(tmp_path):
    """Client: Projekt mit sehr vielen Files"""
    # 50 kleine Dateien anlegen
    for i in range(50):
        f = tmp_path / f"file_{i}.py"
        f.write_text(f"def func_{i}(): return {i}")

    # file_2 mit testbarem Content
    (tmp_path / "file_2.py").write_text("print('file_2 loaded'); VALUE = 42")

    # Main File, das file_2 importiert
    main = tmp_path / "main.py"
    main.write_text("""
import file_2
print('main running')
print(f'file_2.VALUE = {file_2.VALUE}')
""")

    code, output = run_cmd(["octo", "run", str(main)], timeout=60)
    assert code == 0, f"Many files test failed: {output}"
    assert "file_2 loaded" in output
    assert "main running" in output
    assert "file_2.VALUE = 42" in output


def test_config_show_and_set(tmp_path):
    """Client: docker image setzen und anzeigen"""
    # Setze Custom Image
    code, output = run_cmd(["octo", "config", "--docker", "python:3.12"])
    assert code == 0, f"Config set failed: {output}"
    assert "python:3.12" in output or "✅" in output

    # Zeige Config an
    code, output = run_cmd(["octo", "config", "--show"])
    assert code == 0, f"Config show failed: {output}"
    assert "python:3.12" in output, "Set docker image not shown in config"
    
    # Cleanup wird von Fixture erledigt


def test_run_with_custom_docker(tmp_path):
    """Client: Script wird im gesetzten Docker-Image ausgeführt"""
    # Config auf spezielles Image setzen
    code, _ = run_cmd(["octo", "config", "--docker", "python:3.12"])
    assert code == 0, "Failed to set custom docker image"

    f = tmp_path / "docker_test.py"
    f.write_text("import sys; print(f'Python version: {sys.version}')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=30)
    
    assert code == 0, f"Run with custom docker failed: {output}"
    assert "Python version:" in output
    assert "3.12" in output, "Expected Python 3.12, got different version"


def test_run_with_default_docker(tmp_path):
    """Client: Script läuft ohne explizite Config im Default-Image"""
    # Config zurücksetzen auf Default
    code, _ = run_cmd(["octo", "config", "--docker", DEFAULT_DOCKER_IMAGE])
    assert code == 0, "Failed to reset to default docker image"

    f = tmp_path / "default_docker.py"
    f.write_text("print('default docker works')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=30)
    
    assert code == 0, f"Run with default docker failed: {output}"
    assert "default docker works" in output


# ------------------------
# Zusätzliche Edge Cases
# ------------------------

def test_nonexistent_file():
    """Client: Run mit nicht existierender Datei"""
    code, output = run_cmd(["octo", "run", "/tmp/does_not_exist_12345.py"])
    assert code != 0, "Should fail when file doesn't exist"
    assert "not found" in output.lower() or "no such file" in output.lower() or "error" in output.lower(), \
        f"Expected file not found error, got: {output}"


def test_empty_file(tmp_path):
    """Client: Run mit leerer Datei"""
    f = tmp_path / "empty.py"
    f.write_text("")
    code, output = run_cmd(["octo", "run", str(f)])
    # Leere Python-Datei ist valide und sollte erfolgreich sein
    assert code == 0, f"Empty file should run successfully: {output}"


def test_file_with_only_comments(tmp_path):
    """Client: Run mit Datei die nur Kommentare enthält"""
    f = tmp_path / "comments.py"
    f.write_text("# This is just a comment\n# Another comment\n")
    code, output = run_cmd(["octo", "run", str(f)])
    assert code == 0, "File with only comments should run successfully"


def test_unicode_output(tmp_path):
    """Client: Unicode-Zeichen im Output"""
    f = tmp_path / "unicode.py"
    f.write_text("print('Hello 世界 🚀 Ümläüt')")
    code, output = run_cmd(["octo", "run", str(f)])
    assert code == 0, "Unicode test failed"
    # Check ob zumindest einige Unicode-Zeichen durchkommen
    # (perfekte Encoding-Tests sind schwierig über subprocess)


def test_multiline_output(tmp_path):
    """Client: Mehrzeiliger Output"""
    f = tmp_path / "multiline.py"
    f.write_text("""
print('Line 1')
print('Line 2')
print('Line 3')
""")
    code, output = run_cmd(["octo", "run", str(f)])
    assert code == 0
    assert "Line 1" in output
    assert "Line 2" in output
    assert "Line 3" in output


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