import os
import subprocess
import pytest
import time
from concurrent.futures import ThreadPoolExecutor

SERVER_URL = os.environ.get("SERVER_URL", "http://172.30.170.213:5001")
TOKEN = os.environ.get("DAILY_TOKEN", "demo-token2")


def run_cmd(cmd, timeout=600):
    """Hilfsfunktion für CLI Kommandos"""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        outs, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, _ = proc.communicate()
    return proc.returncode, outs


@pytest.fixture(autouse=True)
def ensure_login():
    """Vor jedem Test frisches Login"""
    code, output = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, f"Login fixture failed: {output}"
    yield


# ------------------------
# Daily Long-Run Tests
# ------------------------

def test_long_runtime_5min(tmp_path):
    """Container mit sehr langer Laufzeit (~5 Minuten)"""
    f = tmp_path / "longrun.py"
    f.write_text("import time; time.sleep(300); print('done after 5 min')")
    code, output = run_cmd(["octo", "run", str(f)], timeout=400)
    assert code == 0
    assert "done after 5 min" in output


def test_high_memory_usage(tmp_path):
    """Script das sehr viel Speicher verbraucht"""
    f = tmp_path / "memtest.py"
    f.write_text("x = [0]*10_000_000; print('allocated', len(x))")
    code, output = run_cmd(["octo", "run", str(f)], timeout=120)
    assert code == 0
    assert "allocated" in output


def test_cpu_intensive(tmp_path):
    """Script das CPU-lastig ist"""
    f = tmp_path / "cputest.py"
    f.write_text("s=0\nfor i in range(10**8): s+=i\nprint('sum', s)")
    code, output = run_cmd(["octo", "run", str(f)], timeout=600)
    assert code == 0
    assert "sum" in output


#def test_massive_output(tmp_path):
#    """Sehr viele Prints (100k Zeilen)"""
#    f = tmp_path / "spam_big.py"
#    f.write_text("for i in range(100000): print(f'line {i}')")
#    code, output = run_cmd(["octo", "run", str(f)], timeout=300)
#    assert code == 0
#    assert "line 99999" in output


def test_parallel_long_tasks(tmp_path):
    """Mehrere lange Tasks parallel starten"""
    def run_one(i):
        f = tmp_path / f"ltask_{i}.py"
        f.write_text("import time; time.sleep(20); print('parallel done')")
        return run_cmd(["octo", "run", str(f)], timeout=60)[1]

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_one, range(3)))

    for output in results:
        assert "parallel done" in output


def test_custom_docker_long_run(tmp_path):
    """Docker-Image-Wechsel bei langem Task"""
    run_cmd(["octo", "config", "--docker", "python:3.12"])
    f = tmp_path / "longdocker.py"
    f.write_text("import sys, time; time.sleep(30); print('image', sys.version)")
    code, output = run_cmd(["octo", "run", str(f)], timeout=90)
    assert code == 0
    assert "image" in output
    assert "3.12" in output


def test_task_failure_exit_code(tmp_path):
    """Script beendet sich absichtlich mit Fehler"""
    f = tmp_path / "fail_exit.py"
    f.write_text("import sys; print('exiting'); sys.exit(1)")
    code, output = run_cmd(["octo", "run", str(f)], timeout=60)
    assert code != 0
    assert "exiting" in output


def test_two_runners_conflict(tmp_path):
    """Zwei Runner arbeiten gleichzeitig mit gleichem Server"""
    # Start 2 Scripts die parallel laufen
    def run_one(i):
        f = tmp_path / f"conflict_{i}.py"
        f.write_text(f"print('conflict task {i}')")
        return run_cmd(["octo", "run", str(f)], timeout=60)[1]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run_one, range(2)))

    assert "conflict task 0" in results[0] or results[1]
    assert "conflict task 1" in results[0] or results[1]

if __name__ == "__main__":
    import pytest
    import sys

    # Default pytest args
    args = [
        "-v",
        __file__,
    ]

    sys.exit(pytest.main(args))
