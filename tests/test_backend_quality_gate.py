from pathlib import Path

from scripts.backend_quality_gate import run_checks


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _base_project(root: Path, coverage: int = 100) -> None:
    _write(root / "pytest.ini", f"[pytest]\naddopts = --cov=. --cov-fail-under={coverage}\n")
    _write(root / "services" / "__init__.py", "")
    _write(root / "services" / "alpha.py", "def ok() -> int:\n    return 1\n")
    _write(root / "services" / "beta.py", "def ok() -> int:\n    return 2\n")


def test_backend_quality_gate_accepts_clean_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _base_project(tmp_path)

    assert tuple(filter(None, run_checks(tmp_path))) == ()


def test_backend_quality_gate_reports_file_length(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _base_project(tmp_path)
    _write(tmp_path / "services" / "long.py", "\n".join(("x = 1",) * 101))

    violations = "\n".join(filter(None, run_checks(tmp_path)))

    assert "file too long: services/long.py" in violations


def test_backend_quality_gate_honors_file_baseline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _base_project(tmp_path)
    _write(tmp_path / "services" / "long.py", "\n".join(("x = 1",) * 101))
    _write(tmp_path / "scripts" / "backend_quality_baseline.txt", "file:services/long.py\n")

    assert tuple(filter(None, run_checks(tmp_path))) == ()


def test_backend_quality_gate_reports_complex_function(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _base_project(tmp_path)
    code = "def risky(a, b, c, d, e):\n"
    code += "    if a:\n        pass\n"
    code += "    if b:\n        pass\n"
    code += "    if c:\n        pass\n"
    code += "    if d:\n        pass\n"
    code += "    if e:\n        pass\n"
    _write(tmp_path / "services" / "complex.py", code)

    violations = "\n".join(filter(None, run_checks(tmp_path)))

    assert "function too complex: services/complex.py:1 risky=6" in violations


def test_backend_quality_gate_reports_module_size(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _base_project(tmp_path)
    _write(tmp_path / "api" / "routes" / "single.py", "def ok() -> int:\n    return 1\n")

    violations = "\n".join(filter(None, run_checks(tmp_path)))

    assert "module size violation: api/routes has 1 files" in violations


def test_backend_quality_gate_reports_coverage_floor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _base_project(tmp_path, coverage=75)

    violations = "\n".join(filter(None, run_checks(tmp_path)))

    assert "coverage floor too low: pytest.ini has 75, expected 100" in violations
