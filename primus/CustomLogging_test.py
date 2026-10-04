import logging
import subprocess
import sys

import pytest


pytestmark = pytest.mark.unit


def test_import_succeeds_without_aws_logging_dependencies():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['watchtower'] = None; sys.modules['boto3'] = None; "
            "import primus.CustomLogging",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_setup_logging_configures_only_the_primus_logger(monkeypatch):
    from primus import CustomLogging

    root_logger = logging.getLogger()
    original_root_handlers = list(root_logger.handlers)
    monkeypatch.setenv("DEBUG", "1")

    try:
        CustomLogging.setup_logging()

        primus_logger = logging.getLogger("primus")
        assert primus_logger.handlers
        assert primus_logger.propagate is False
        assert root_logger.handlers == original_root_handlers
        assert all(
            handler.__class__.__module__ != "watchtower"
            for handler in primus_logger.handlers
        )
    finally:
        root_logger.handlers[:] = original_root_handlers
