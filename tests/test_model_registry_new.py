from __future__ import annotations

import subprocess
import sys


def test_models_package_configures_sqlalchemy_mappers_in_fresh_process():
    result = subprocess.run(
        [sys.executable, "-c", "import models; from sqlalchemy.orm import configure_mappers; configure_mappers()"],
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
