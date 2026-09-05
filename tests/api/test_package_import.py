"""Verify imports outside pytest's configured source paths."""

import os
import subprocess
import sys
from pathlib import Path


def test_run_grade_route_imports_from_api_directory():
    api_directory = Path(__file__).resolve().parents[2] / "apps" / "api"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", "from routes.run_grade import router"],
        cwd=api_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
