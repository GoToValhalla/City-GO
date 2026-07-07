"""Regression: core.router_setup must import without a circular-import failure.

services/import_pipeline/__init__.py used to eagerly import runner, which pulled in
admin_city_import_runner -> run_due_import_jobs -> import_city_osm_v2 while
import_city_osm_v2 itself was still mid-import (it imports
services.import_pipeline.schema_compat, triggering the package __init__).

Must run in a fresh interpreter: once conftest has already imported the app,
every module in the cycle is already in sys.modules and the bug can't reproduce.
"""

import subprocess
import sys


def test_router_setup_imports_without_circular_import():
    script = (
        "import importlib\n"
        "for name in ("
        "'services.admin_platform_quality', "
        "'routers.admin_platform', "
        "'routers.place_verification', "
        "'core.router_setup', "
        "'services.import_pipeline.schema_compat', "
        "'data.scripts.import_city_osm_v2'"
        "):\n"
        "    importlib.import_module(name)\n"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
