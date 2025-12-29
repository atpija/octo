import os
import subprocess
import pytest
from pathlib import Path

SERVER_URL = os.environ.get("SERVER_URL", "http://host.docker.internal:5001")
TOKEN = os.environ.get("DAILY_TOKEN", "demo-token")


def run_cmd(cmd, timeout=30):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        outs, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, _ = proc.communicate()
    return proc.returncode, outs


@pytest.fixture(autouse=True)
def ensure_login():
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, f"Login failed: {output}"
    yield


# ------------------------
# Output & Download Tests
# ------------------------

def run_and_assert(tmp_path, script_content, expected_files):
    main = tmp_path / "main.py"
    main.write_text(script_content)

    code, output = run_cmd(["octo", "run", str(main)])
    assert code == 0, f"Run failed: {output}"

    for rel, content in expected_files.items():
        f = tmp_path / rel
        assert f.exists(), f"{rel} not downloaded"
        if content is not None:
            assert f.read_text() == content


def test_single_file_download(tmp_path):
    run_and_assert(
        tmp_path,
        "open('generated.txt','w').write('hello')",
        {"generated.txt": "hello"},
    )


def test_nested_folder_download(tmp_path):
    run_and_assert(
        tmp_path,
        "import os; os.makedirs('a/b', exist_ok=True); open('a/b/x.txt','w').write('x')",
        {"a/b/x.txt": "x"},
    )


def test_multiple_files_download(tmp_path):
    run_and_assert(
        tmp_path,
        "open('a.txt','w').write('a'); open('b.txt','w').write('b')",
        {"a.txt": "a", "b.txt": "b"},
    )


def test_excluded_folders(tmp_path):
    main = tmp_path / "main.py"
    main.write_text("""
import os
os.makedirs('__pycache__', exist_ok=True)
os.makedirs('venv', exist_ok=True)
open('__pycache__/x.pyc','w').write('x')
open('venv/y.py','w').write('y')
print('done')
""")

    code, output = run_cmd(["octo", "run", str(main)])
    assert code == 0

    assert not (tmp_path / "__pycache__").exists()
    assert not (tmp_path / "venv").exists()


def test_deeply_nested_download(tmp_path):
    run_and_assert(
        tmp_path,
        "import os; os.makedirs('x/y/z', exist_ok=True); open('x/y/z/d.txt','w').write('deep')",
        {"x/y/z/d.txt": "deep"},
    )
