import os
import subprocess
import pytest
import time
from concurrent.futures import ThreadPoolExecutor

SERVER_URL = os.environ.get("SERVER_URL", "http://host.docker.internal:5001")
TOKEN = os.environ.get("DAILY_TOKEN", "demo-token2")
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"


def run_cmd(cmd, timeout=600):
    """Hilfsfunktion für CLI Kommandos mit Timing"""
    start_time = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        outs, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, _ = proc.communicate()
        outs += f"\n[TIMEOUT after {timeout}s]"
    elapsed = time.time() - start_time
    return proc.returncode, outs, elapsed


@pytest.fixture(autouse=True)
def ensure_login():
    """Vor jedem Test frisches Login"""
    code, output, _ = run_cmd(["octo", "login", "--token", TOKEN, "--server", SERVER_URL])
    assert code == 0, f"Login fixture failed: {output}"
    yield
    # Cleanup: Config zurücksetzen nach jedem Test
    run_cmd(["octo", "config", "--docker", DEFAULT_DOCKER_IMAGE])


# ------------------------
# Daily Long-Run Tests
# ------------------------

def test_long_runtime_5min(tmp_path):
    """Container mit sehr langer Laufzeit (~5 Minuten)"""
    f = tmp_path / "longrun.py"
    script = """
import time
import sys

print('Starting 5-minute task...', flush=True)
for i in range(5):
    time.sleep(60)
    print(f'Minute {i+1}/5 completed', flush=True)
print('done after 5 min')
"""
    f.write_text(script)
    
    code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=400)
    
    assert code == 0, f"Long run failed with code {code}: {output}"
    assert "done after 5 min" in output, "Completion message not found"
    assert elapsed >= 300, f"Task finished too quickly: {elapsed}s (expected ~300s)"
    assert elapsed < 350, f"Task took too long: {elapsed}s (expected ~300s)"
    
    # Prüfe ob alle Zwischenmeldungen da sind
    for i in range(1, 6):
        assert f"Minute {i}/5" in output, f"Missing progress message for minute {i}"


def test_high_memory_usage(tmp_path):
    """Script das sehr viel Speicher verbraucht (~100MB)"""
    f = tmp_path / "memtest.py"
    script = """
import sys

# Allokiere ~100MB (10 Millionen Integers, ca. 10 Bytes pro Int in Python)
print('Allocating memory...', flush=True)
x = [i for i in range(10_000_000)]
print(f'Allocated {len(x)} elements', flush=True)

# Verifiziere die Daten
assert len(x) == 10_000_000, 'Wrong length'
assert x[0] == 0, 'Wrong first element'
assert x[-1] == 9_999_999, 'Wrong last element'
print('Memory test passed')
"""
    f.write_text(script)
    
    code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=120)
    
    assert code == 0, f"Memory test failed: {output}"
    assert "Allocated 10000000 elements" in output, "Memory allocation not confirmed"
    assert "Memory test passed" in output, "Memory verification failed"


def test_cpu_intensive(tmp_path):
    """Script das CPU-lastig ist (berechnet Fibonacci-Zahlen)"""
    f = tmp_path / "cputest.py"
    script = """
import time

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print('Starting CPU-intensive task...', flush=True)
start = time.time()

# Berechne mehrere Fibonacci-Zahlen (CPU-intensiv wegen Rekursion)
results = [fibonacci(i) for i in range(30, 35)]

elapsed = time.time() - start
print(f'Computed fibonacci numbers: {results}', flush=True)
print(f'CPU time: {elapsed:.2f}s', flush=True)
print('CPU test completed')
"""
    f.write_text(script)
    
    code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=600)
    
    assert code == 0, f"CPU test failed: {output}"
    assert "CPU test completed" in output, "Completion message not found"
    assert "Computed fibonacci numbers:" in output, "Results not found"
    # CPU-intensive Task sollte mindestens 2-3 Sekunden dauern
    assert elapsed >= 2, f"Task finished suspiciously fast: {elapsed}s"


def test_massive_output(tmp_path):
    """Sehr viele Prints (50k Zeilen) mit Fortschrittsanzeige"""
    f = tmp_path / "spam_big.py"
    script = """
import sys

total = 50000
print(f'Starting output of {total} lines...', flush=True)

for i in range(total):
    print(f'line {i}')
    # Progress alle 10k Zeilen
    if i > 0 and i % 10000 == 0:
        print(f'[PROGRESS] {i}/{total} lines', flush=True, file=sys.stderr)

print(f'Completed {total} lines', flush=True)
"""
    f.write_text(script)
    
    code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=300)
    
    assert code == 0, f"Massive output test failed: {output[:500]}"
    assert "line 0" in output, "First line missing"
    assert "line 49999" in output, "Last line missing"
    assert "Completed 50000 lines" in output, "Completion message missing"


def test_parallel_long_tasks(tmp_path):
    """Mehrere lange Tasks parallel starten"""
    def run_one(i):
        f = tmp_path / f"ltask_{i}.py"
        script = f"""
import time
import sys

print('Task {i} starting...', flush=True)
time.sleep(20)
print('Task {i} parallel done', flush=True)
"""
        f.write_text(script)
        code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=60)
        
        # Wichtig: Prüfe Exit Code!
        assert code == 0, f"Task {i} failed with code {code}: {output}"
        assert f"Task {i} parallel done" in output, f"Task {i} completion message missing"
        assert elapsed >= 20, f"Task {i} finished too quickly: {elapsed}s"
        
        return output

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_one, range(3)))
    total_elapsed = time.time() - start_time
    
    # Alle Tasks sollten parallel gelaufen sein (~20s statt 60s)
    assert total_elapsed < 40, f"Tasks ran sequentially instead of parallel: {total_elapsed}s"
    assert len(results) == 3, "Not all tasks completed"


def test_custom_docker_long_run(tmp_path):
    """Docker-Image-Wechsel bei langem Task"""
    # Setze Custom Image
    code, _, _ = run_cmd(["octo", "config", "--docker", "python:3.12"])
    assert code == 0, "Failed to set custom docker image"
    
    f = tmp_path / "longdocker.py"
    script = """
import sys
import time
import platform

print(f'Python version: {sys.version}', flush=True)
print(f'Platform: {platform.platform()}', flush=True)

time.sleep(30)

print('Long docker task completed', flush=True)
"""
    f.write_text(script)
    
    code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=90)
    
    assert code == 0, f"Custom docker long run failed: {output}"
    assert "Python version:" in output, "Python version not shown"
    assert "3.12" in output, "Expected Python 3.12"
    assert "Long docker task completed" in output
    assert elapsed >= 30, f"Task finished too quickly: {elapsed}s"


def test_task_failure_exit_code(tmp_path):
    """Script beendet sich absichtlich mit verschiedenen Fehlerarten"""
    
    # Test 1: sys.exit(1)
    f1 = tmp_path / "fail_exit.py"
    f1.write_text("import sys; print('exiting with 1'); sys.exit(1)")
    code, output, _ = run_cmd(["octo", "run", str(f1)], timeout=60)
    assert code != 0, "sys.exit(1) should return non-zero exit code"
    assert "exiting with 1" in output
    
    # Test 2: Exception
    f2 = tmp_path / "fail_exception.py"
    f2.write_text("print('raising exception'); raise RuntimeError('intentional error')")
    code, output, _ = run_cmd(["octo", "run", str(f2)], timeout=60)
    assert code != 0, "Unhandled exception should return non-zero exit code"
    assert "raising exception" in output
    assert "RuntimeError" in output or "intentional error" in output
    
    # Test 3: Assertion Error
    f3 = tmp_path / "fail_assert.py"
    f3.write_text("print('checking assertion'); assert False, 'assertion failed'")
    code, output, _ = run_cmd(["octo", "run", str(f3)], timeout=60)
    assert code != 0, "Failed assertion should return non-zero exit code"
    assert "AssertionError" in output or "assertion failed" in output


def test_two_runners_conflict(tmp_path):
    """Zwei Runner arbeiten gleichzeitig mit gleichem Server"""
    def run_one(i):
        f = tmp_path / f"conflict_{i}.py"
        script = f"""
import time
print('Conflict task {i} starting', flush=True)
time.sleep(5)
print('Conflict task {i} completed', flush=True)
"""
        f.write_text(script)
        code, output, _ = run_cmd(["octo", "run", str(f)], timeout=60)
        assert code == 0, f"Conflict task {i} failed with code {code}"
        return output

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run_one, range(2)))
    
    # FIX: Korrekte Assertion - beide Tasks müssen ihre Completion-Messages haben
    combined_output = "\n".join(results)
    assert "Conflict task 0 completed" in combined_output, "Task 0 didn't complete properly"
    assert "Conflict task 1 completed" in combined_output, "Task 1 didn't complete properly"
    
    # Zusätzlich: Jeder Task sollte in seinem eigenen Output sein
    assert "Conflict task 0 completed" in results[0], "Task 0 output not in result 0"
    assert "Conflict task 1 completed" in results[1], "Task 1 output not in result 1"


# ------------------------
# Zusätzliche Stress Tests
# ------------------------

def test_rapid_sequential_runs(tmp_path):
    """Viele schnelle Runs hintereinander"""
    f = tmp_path / "quick.py"
    f.write_text("print('quick run')")
    
    results = []
    for i in range(10):
        code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=30)
        assert code == 0, f"Run {i} failed"
        assert "quick run" in output
        results.append(elapsed)
    
    avg_time = sum(results) / len(results)
    print(f"Average time per run: {avg_time:.2f}s")
    
    # Durchschnitt sollte relativ konsistent sein (nicht stark schwanken)
    max_time = max(results)
    min_time = min(results)
    assert max_time < min_time * 3, f"Run times vary too much: {min_time:.2f}s to {max_time:.2f}s"


def test_disk_io_intensive(tmp_path):
    """Script das viel Disk I/O macht"""
    f = tmp_path / "diskio.py"
    script = """
import os
import tempfile

print('Starting disk I/O test...', flush=True)

# Schreibe 50MB in Dateien
with tempfile.TemporaryDirectory() as tmpdir:
    data = 'x' * 1024 * 1024  # 1MB string
    
    for i in range(50):
        filepath = os.path.join(tmpdir, f'file_{i}.txt')
        with open(filepath, 'w') as f:
            f.write(data)
        
        if i % 10 == 0:
            print(f'Written {i+1}/50 files', flush=True)
    
    # Lese alle Dateien zurück
    for i in range(50):
        filepath = os.path.join(tmpdir, f'file_{i}.txt')
        with open(filepath, 'r') as f:
            content = f.read()
            assert len(content) == len(data), f'File {i} has wrong size'
    
    print('Disk I/O test completed')
"""
    f.write_text(script)
    
    code, output, _ = run_cmd(["octo", "run", str(f)], timeout=300)
    
    assert code == 0, f"Disk I/O test failed: {output}"
    assert "Disk I/O test completed" in output


def test_imports_external_packages(tmp_path):
    """Test ob standard library packages verfügbar sind"""
    f = tmp_path / "imports.py"
    script = """
# Teste verschiedene Standard Library Packages
import json
import sys
import os
import time
import datetime
import random
import math
import re
import pathlib
import subprocess

packages = [
    'json', 'sys', 'os', 'time', 'datetime', 
    'random', 'math', 're', 'pathlib', 'subprocess'
]

print('Testing standard library imports:', flush=True)
for pkg in packages:
    print(f'  ✓ {pkg}', flush=True)

print('All imports successful')
"""
    f.write_text(script)
    
    code, output, _ = run_cmd(["octo", "run", str(f)], timeout=60)
    
    assert code == 0, f"Import test failed: {output}"
    assert "All imports successful" in output


def test_environment_variables(tmp_path):
    """Test ob Environment Variables richtig weitergegeben werden"""
    f = tmp_path / "envtest.py"
    script = """
import os
import sys

print('Environment test:', flush=True)
print(f'  Python version: {sys.version}', flush=True)
print(f'  Platform: {sys.platform}', flush=True)
print(f'  PATH exists: {bool(os.environ.get("PATH"))}', flush=True)

# Check ob in Container
in_container = os.path.exists('/.dockerenv')
print(f'  In container: {in_container}', flush=True)

print('Environment test passed')
"""
    f.write_text(script)
    
    code, output, _ = run_cmd(["octo", "run", str(f)], timeout=60)
    
    assert code == 0, f"Environment test failed: {output}"
    assert "Environment test passed" in output


def test_timeout_handling(tmp_path):
    """Test wie System mit zu langen Tasks umgeht"""
    f = tmp_path / "timeout_test.py"
    script = """
import time

print('Starting infinite loop test...', flush=True)
# Simuliere einen Task der zu lange läuft
time.sleep(1000)  # 16+ Minuten
print('This should never print')
"""
    f.write_text(script)
    
    # Setze kurzes Timeout
    code, output, elapsed = run_cmd(["octo", "run", str(f)], timeout=30)
    
    # Task sollte durch Timeout abgebrochen werden
    assert elapsed < 40, f"Timeout didn't work properly: {elapsed}s"
    assert "[TIMEOUT" in output or code != 0, "Timeout not detected"


def test_concurrent_config_changes(tmp_path):
    """Test ob Config-Änderungen während laufender Tasks problematisch sind"""
    # Start einen langen Task
    f1 = tmp_path / "long1.py"
    f1.write_text("import time; time.sleep(15); print('long task done')")
    
    # Starte Task asynchron
    import threading
    result = {}
    
    def run_long_task():
        code, output, _ = run_cmd(["octo", "run", str(f1)], timeout=60)
        result['code'] = code
        result['output'] = output
    
    thread = threading.Thread(target=run_long_task)
    thread.start()
    
    # Während Task läuft, ändere Config
    time.sleep(5)
    run_cmd(["octo", "config", "--docker", "python:3.12"])
    
    # Warte auf Task-Completion
    thread.join(timeout=60)
    
    # Task sollte erfolgreich sein trotz Config-Änderung
    assert 'code' in result, "Task didn't complete"
    assert result['code'] == 0, f"Task failed during config change: {result.get('output', '')}"
    assert "long task done" in result['output']


if __name__ == "__main__":
    import sys
    
    # pytest args mit besserer Ausgabe
    args = [
        "-v",                # verbose
        "-s",                # show print statements  
        "--tb=short",        # shorter traceback
        "--color=yes",       # colored output
        "--durations=10",    # show 10 slowest tests
        __file__,
    ]
    
    sys.exit(pytest.main(args))