from pathlib import Path


def test_portable_command_worker_container_artifact_uses_the_package_runtime() -> None:
    dockerfile = (
        Path(__file__).parents[2] / "primus" / "command_worker" / "Dockerfile"
    ).read_text(encoding="utf-8")

    assert "python:3.12-slim" in dockerfile
    assert "poetry install --only main --extras command-service-runtime" in dockerfile
    assert "apt-get install --yes --no-install-recommends build-essential" in dockerfile
    assert "PIP_DEFAULT_TIMEOUT=120" in dockerfile
    assert "PIP_RETRIES=5" in dockerfile
    assert 'python -m pip install --upgrade "cython<4" "numpy<3"' in dockerfile
    assert "--extras scoring" not in dockerfile
    assert "--extras evaluation" not in dockerfile
    assert "POETRY_VIRTUALENVS_CREATE=false" in dockerfile
    assert "from primus.command_worker.executors.primus_cli import create_executor" in dockerfile
    assert "python -m primus.command_worker.smoke" in dockerfile
    assert 'ENTRYPOINT ["primus-command-worker"]' in dockerfile
    assert "COMMAND_WORKER_EXECUTOR_FACTORY" in dockerfile
