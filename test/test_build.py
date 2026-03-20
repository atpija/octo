import os
import subprocess
import pytest
from concurrent.futures import ThreadPoolExecutor

SERVER_URL = os.environ.get("SERVER_URL", "http://host.docker.internal:5001")
TOKEN = os.environ.get("SMOKE_TOKEN", "demo-token1")
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"


def run_cmd(cmd, timeout=60):
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
    run_cmd(["octo", "config", "--noinstall"])


# --------------------------------
# octo build Tests
# --------------------------------

def test_build_basic(tmp_path):
    """Build: einfaches Dockerfile bauen"""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.11-slim\nRUN echo 'build ok'")
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", "octo-test-basic:latest"])
    assert code == 0, f"Build failed: {output}"
    assert "[OK]" in output, "No success message in output"


def test_build_with_custom_tag(tmp_path):
    """Build: Image mit custom Tag"""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM alpine:latest\nRUN echo 'custom tag ok'")
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", "octo-test-custom:v1.0"])
    assert code == 0, f"Build with custom tag failed: {output}"
    assert "[OK]" in output


def test_build_invalid_dockerfile(tmp_path):
    """Build: ungültiges Dockerfile – muss fehlschlagen"""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM nonexistent-image-xyz-12345:latest\nRUN echo 'should fail'")
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", "octo-test-invalid:latest"])
    assert code != 0, "Build with invalid base image should fail"
    assert "ERROR" in output or "error" in output.lower(), \
        f"Expected error message, got: {output}"


def test_build_nonexistent_dockerfile():
    """Build: Dockerfile existiert nicht"""
    code, output = run_cmd(["octo", "build", "/tmp/does_not_exist.Dockerfile", "--tag", "octo-test-missing:latest"])
    assert code != 0, "Should fail when Dockerfile doesn't exist"
    assert "not found" in output.lower() or "error" in output.lower(), \
        f"Expected file not found error, got: {output}"


def test_build_multistep_dockerfile(tmp_path):
    """Build: Dockerfile mit mehreren Schritten"""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM python:3.11-slim\n"
        "RUN apt-get update && apt-get install -y curl\n"
        "RUN python -c \"print('multi-step build ok')\"\n"
        "CMD [\"python\", \"-c\", \"print('ready')\"]\n"
    )
    code, output = run_cmd(
        ["octo", "build", str(dockerfile), "--tag", "octo-test-multistep:latest"],
        timeout=120
    )
    assert code == 0, f"Multi-step build failed: {output}"
    assert "[OK]" in output


def test_build_invalid_syntax_dockerfile(tmp_path):
    """Build: Dockerfile mit Syntaxfehler"""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("THISISNOTVALID\nRUN echo 'broken'")
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", "octo-test-syntax:latest"])
    assert code != 0, "Dockerfile with syntax error should fail"


def test_parallel_builds(tmp_path):
    """Build: Mehrere Builds parallel"""
    def build_one(i):
        dockerfile = tmp_path / f"Dockerfile_{i}"
        dockerfile.write_text(f"FROM alpine:latest\nRUN echo 'build {i} ok'")
        code, output = run_cmd(
            ["octo", "build", str(dockerfile), "--tag", f"octo-test-parallel-{i}:latest"],
            timeout=120
        )
        assert code == 0, f"Parallel build {i} failed: {output}"
        return output

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(build_one, range(5)))

    assert len(results) == 5, "Not all parallel builds completed"


# --------------------------------
# install Tests
# --------------------------------

def test_install_basic(tmp_path):
    """install: requirements.txt wird installiert"""
    (tmp_path / "requirements.txt").write_text("httpx\n")
    (tmp_path / "main.py").write_text("import httpx; print(f'httpx ok: {httpx.__version__}')")

    run_cmd(["octo", "config", "--install"])
    code, output = run_cmd(["octo", "run", str(tmp_path / "main.py")], timeout=60)
    assert code == 0, f"install basic failed: {output}"
    assert "httpx ok:" in output, "httpx was not installed or imported"


def test_install_multiple_packages(tmp_path):
    """install: mehrere Pakete aus requirements.txt"""
    (tmp_path / "requirements.txt").write_text("httpx\nrich\n")
    (tmp_path / "main.py").write_text(
        "import httpx, rich; print(f'httpx={httpx.__version__} packages ok')"
    )

    run_cmd(["octo", "config", "--install"])
    code, output = run_cmd(["octo", "run", str(tmp_path / "main.py")], timeout=60)
    assert code == 0, f"multi-package install failed: {output}"
    assert "httpx=" in output
    assert "rich=" in output


def test_install_pinned_version(tmp_path):
    """install: pinned Paketversion aus requirements.txt"""
    (tmp_path / "requirements.txt").write_text("httpx==0.27.0\n")
    (tmp_path / "main.py").write_text("import httpx; print(f'version={httpx.__version__}')")

    run_cmd(["octo", "config", "--install"])
    code, output = run_cmd(["octo", "run", str(tmp_path / "main.py")], timeout=60)
    assert code == 0, f"pinned version failed: {output}"
    assert "0.27.0" in output, "Expected pinned version 0.27.0"


def test_install_invalid_package(tmp_path):
    """install: ungültiges Paket – muss fehlschlagen"""
    (tmp_path / "requirements.txt").write_text("this-package-does-not-exist-xyz-99999\n")
    (tmp_path / "main.py").write_text("print('should not reach here')")

    run_cmd(["octo", "config", "--install"])
    code, output = run_cmd(["octo", "run", str(tmp_path / "main.py")], timeout=60)
    assert code != 0, "Should fail with invalid package"
    assert "error" in output.lower() or "not found" in output.lower(), \
        f"Expected install error, got: {output}"


def test_noinstall_ignores_requirements(tmp_path):
    """install: --noinstall ignoriert requirements.txt"""
    (tmp_path / "requirements.txt").write_text("httpx\n")
    (tmp_path / "main.py").write_text("print('no install ok')")

    run_cmd(["octo", "config", "--noinstall"])
    code, output = run_cmd(["octo", "run", str(tmp_path / "main.py")], timeout=30)
    assert code == 0, f"noinstall run failed: {output}"
    assert "no install ok" in output


def test_install_no_requirements_file(tmp_path):
    """install: --install aber kein requirements.txt vorhanden – sollte trotzdem laufen"""
    (tmp_path / "main.py").write_text("print('no requirements ok')")

    run_cmd(["octo", "config", "--install"])
    code, output = run_cmd(["octo", "run", str(tmp_path / "main.py")], timeout=30)
    assert code == 0, f"Run without requirements.txt failed: {output}"
    assert "no requirements ok" in output


# --------------------------------
# Build + Run kombiniert
# --------------------------------

def test_build_and_run_python_package(tmp_path):
    """Build+Run: Image mit vorinstalliertem Paket bauen, dann nutzen"""
    image_tag = "octo-test-preinstalled:latest"

    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM python:3.11-slim\n"
        "RUN pip install httpx\n"
    )
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", image_tag], timeout=120)
    assert code == 0, f"Build phase failed: {output}"

    run_cmd(["octo", "config", "--docker", image_tag])
    run_cmd(["octo", "config", "--noinstall"])

    script = tmp_path / "main.py"
    script.write_text("import httpx; print(f'httpx from image: {httpx.__version__}')")
    code, output = run_cmd(["octo", "run", str(script)], timeout=60)
    assert code == 0, f"Run with preinstalled package failed: {output}"
    assert "httpx from image:" in output


def test_build_and_run_system_dependency(tmp_path):
    """Build+Run: Image mit System-Dependency (curl) bauen und nutzen"""
    image_tag = "octo-test-curl:latest"

    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM python:3.11-slim\n"
        "RUN apt-get update && apt-get install -y curl\n"
    )
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", image_tag], timeout=120)
    assert code == 0, f"Build with system dep failed: {output}"

    run_cmd(["octo", "config", "--docker", image_tag])

    script = tmp_path / "main.py"
    script.write_text(
        "import subprocess\n"
        "r = subprocess.run(['curl', '--version'], capture_output=True, text=True)\n"
        "print('curl available' if r.returncode == 0 else 'curl missing')\n"
    )
    code, output = run_cmd(["octo", "run", str(script)], timeout=60)
    assert code == 0, f"Run with curl failed: {output}"
    assert "curl available" in output


def test_build_and_run_custom_python_version(tmp_path):
    """Build+Run: spezifische Python-Version im Image"""
    image_tag = "octo-test-py312:latest"

    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12-slim\n")
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", image_tag], timeout=120)
    assert code == 0, f"Build Python 3.12 image failed: {output}"

    run_cmd(["octo", "config", "--docker", image_tag])

    script = tmp_path / "main.py"
    script.write_text("import sys; print(f'python={sys.version_info.major}.{sys.version_info.minor}')")
    code, output = run_cmd(["octo", "run", str(script)], timeout=60)
    assert code == 0, f"Run with Python 3.12 failed: {output}"
    assert "python=3.12" in output


def test_build_and_run_env_variable(tmp_path):
    """Build+Run: ENV Variable im Dockerfile setzen und im Script lesen"""
    image_tag = "octo-test-env:latest"

    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM python:3.11-slim\n"
        "ENV MY_VAR=hello_from_dockerfile\n"
    )
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", image_tag], timeout=120)
    assert code == 0, f"Build with ENV failed: {output}"

    run_cmd(["octo", "config", "--docker", image_tag])

    script = tmp_path / "main.py"
    script.write_text("import os; print(f'env={os.environ.get(\"MY_VAR\", \"not set\")}')")
    code, output = run_cmd(["octo", "run", str(script)], timeout=60)
    assert code == 0, f"Run with ENV var failed: {output}"
    assert "env=hello_from_dockerfile" in output


def test_build_run_output_files(tmp_path):
    """Build+Run: Script schreibt Output-Datei, Runner liefert sie zurück"""
    image_tag = "octo-test-output:latest"

    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.11-slim\n")
    code, output = run_cmd(["octo", "build", str(dockerfile), "--tag", image_tag], timeout=120)
    assert code == 0, f"Build for output test failed: {output}"

    run_cmd(["octo", "config", "--docker", image_tag])

    script = tmp_path / "main.py"
    script.write_text(
        "with open('result.txt', 'w') as f:\n"
        "    f.write('output file ok')\n"
        "print('file written')\n"
    )
    code, output = run_cmd(["octo", "run", str(script)], timeout=60)
    assert code == 0, f"Run with output file failed: {output}"
    assert "file written" in output

    result_file = tmp_path / "result.txt"
    assert result_file.exists(), "result.txt was not returned by Runner"
    assert result_file.read_text() == "output file ok"


def test_build_failed_run_still_works(tmp_path):
    """Build+Run: fehlgeschlagener Build blockiert keine weiteren Runs"""
    bad_dockerfile = tmp_path / "Dockerfile"
    bad_dockerfile.write_text("FROM nonexistent-xyz:latest")
    run_cmd(["octo", "build", str(bad_dockerfile), "--tag", "octo-test-shouldfail:latest"])

    run_cmd(["octo", "config", "--docker", DEFAULT_DOCKER_IMAGE])
    script = tmp_path / "main.py"
    script.write_text("print('still works after failed build')")
    code, output = run_cmd(["octo", "run", str(script)], timeout=60)
    assert code == 0, f"Run after failed build failed: {output}"
    assert "still works after failed build" in output


if __name__ == "__main__":
    import sys
    from pathlib import Path

    report_dir = Path("test-reports")
    report_dir.mkdir(exist_ok=True)

    test_name = Path(__file__).stem

    args = [
        "-v",
        "-s",
        "--tb=short",
        "--color=yes",
        f"--junitxml={report_dir}/junit-{test_name}.xml",
        f"--html={report_dir}/report-{test_name}.html",
        "--self-contained-html",
        __file__,
    ]

    sys.exit(pytest.main(args))