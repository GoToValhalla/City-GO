from __future__ import annotations

from pathlib import Path

from scripts.build_total_autotest_report import build_report


def test_total_report_marks_missing_failed_frontend_job(monkeypatch, tmp_path: Path) -> None:
    messages = tmp_path / "downloaded" / "backend-test-artifacts" / "artifacts" / "messages"
    messages.mkdir(parents=True)
    (messages / "backend.txt").write_text("✅ Backend ok", encoding="utf-8")
    monkeypatch.setenv("BACKEND_JOB_RESULT", "success")
    monkeypatch.setenv("FRONTEND_JOB_RESULT", "failure")
    monkeypatch.setenv("GITHUB_SHA", "abcdef123456")
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "1")

    report = build_report(tmp_path / "downloaded")

    assert report.startswith("❌ CITY GO · CI")
    assert "Frontend job FAILED" in report
    assert "frontend.txt" in report


def test_total_report_stays_green_when_required_jobs_success(monkeypatch, tmp_path: Path) -> None:
    messages = tmp_path / "downloaded" / "backend-test-artifacts" / "artifacts" / "messages"
    messages.mkdir(parents=True)
    (messages / "backend.txt").write_text("✅ Backend ok", encoding="utf-8")
    frontend_messages = tmp_path / "downloaded" / "frontend-test-artifacts" / "artifacts" / "messages"
    frontend_messages.mkdir(parents=True)
    (frontend_messages / "frontend.txt").write_text("✅ Frontend ok", encoding="utf-8")
    monkeypatch.setenv("BACKEND_JOB_RESULT", "success")
    monkeypatch.setenv("FRONTEND_JOB_RESULT", "success")

    report = build_report(tmp_path / "downloaded")

    assert report.startswith("✅ CITY GO · CI")
    assert "Frontend job FAILED" not in report
