import os
import subprocess
import pytest
import tempfile
import zipfile
from pathlib import Path

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
# Tests für neue Output-Logik
# ------------------------

def test_output_flag_and_file_download(tmp_path):
    """Client: Prüft [OUTPUT_DONE] und Herunterladen neuer Dateien"""
    # Testscript erzeugen
    main_py = tmp_path / "main.py"
    main_py.write_text("""
with open('generated.txt', 'w') as f:
    f.write('hello output')
print('done main')
""")

    # Task ausführen
    code, output = run_cmd(["octo", "run", str(main_py)], timeout=30)
    assert code == 0
    assert "done main" in output

    # Prüfen, ob neue Datei heruntergeladen wurde
    generated_file = tmp_path / "generated.txt"
    assert generated_file.exists(), "generated.txt wurde nicht heruntergeladen"
    assert generated_file.read_text() == "hello output"

def test_nested_folder_download(tmp_path):
    """Client: Prüft, dass Dateien in Unterordner korrekt heruntergeladen werden"""
    # Testscript erzeugen
    main_py = tmp_path / "main_nested.py"
    main_py.write_text("""
import os
os.makedirs('subdir', exist_ok=True)
with open('subdir/nested.txt', 'w') as f:
    f.write('nested output')
print('done nested')
""")

    # Task ausführen
    code, output = run_cmd(["octo", "run", str(main_py)], timeout=30)
    assert code == 0
    assert "done nested" in output

    nested_file = tmp_path / "subdir" / "nested.txt"
    assert nested_file.exists(), "nested.txt wurde nicht heruntergeladen"
    assert nested_file.read_text() == "nested output"

def test_multiple_files_download(tmp_path):
    """Client: Prüft, dass mehrere neue Dateien korrekt heruntergeladen werden"""
    main_py = tmp_path / "main_multi.py"
    main_py.write_text("""
for i in range(3):
    with open(f'file_{i}.txt', 'w') as f:
        f.write(f'content {i}')
print('done multiple')
""")
    code, output = run_cmd(["octo", "run", str(main_py)], timeout=30)
    assert code == 0
    assert "done multiple" in output

    for i in range(3):
        fpath = tmp_path / f"file_{i}.txt"
        assert fpath.exists()
        assert fpath.read_text() == f"content {i}"

def test_pycache_excluded(tmp_path):
    """Client: Prüft, dass __pycache__-Dateien nicht heruntergeladen werden"""
    main_py = tmp_path / "main_cache.py"
    main_py.write_text("""
import os
os.makedirs('__pycache__', exist_ok=True)
with open('__pycache__/cached.pyc', 'w') as f:
    f.write('bytecode')
print('done cache')
""")

    code, output = run_cmd(["octo", "run", str(main_py)], timeout=30)
    assert code == 0
    assert "done cache" in output

    cached_file = tmp_path / "__pycache__" / "cached.pyc"
    assert not cached_file.exists(), "__pycache__ sollte nicht heruntergeladen werden"


def test_venv_excluded(tmp_path):
    """Client: Prüft, dass venv-Ordner nicht heruntergeladen wird"""
    main_py = tmp_path / "main_venv.py"
    main_py.write_text("""
import os
os.makedirs('venv', exist_ok=True)
with open('venv/fake.py', 'w') as f:
    f.write('fake venv')
print('done venv')
""")

    code, output = run_cmd(["octo", "run", str(main_py)], timeout=30)
    assert code == 0
    assert "done venv" in output

    fake_file = tmp_path / "venv" / "fake.py"
    assert not fake_file.exists(), "venv sollte nicht heruntergeladen werden"

def test_deeply_nested_folder_download(tmp_path):
    """Client: Prüft, dass tief verschachtelte Ordner korrekt heruntergeladen werden"""
    main_py = tmp_path / "main_deep.py"
    main_py.write_text("""
import os
os.makedirs('a/b/c', exist_ok=True)
with open('a/b/c/deep.txt', 'w') as f:
    f.write('deep content')
print('done deep')
""")

    code, output = run_cmd(["octo", "run", str(main_py)], timeout=30)
    assert code == 0
    assert "done deep" in output

    deep_file = tmp_path / "a" / "b" / "c" / "deep.txt"
    assert deep_file.exists(), "deep.txt wurde nicht heruntergeladen"
    assert deep_file.read_text() == "deep content"
