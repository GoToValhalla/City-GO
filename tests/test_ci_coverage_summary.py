from __future__ import annotations

import json
from pathlib import Path

from scripts import ci_coverage_summary


def test_backend_admin_coverage_metric(tmp_path: Path) -> None:
    coverage_xml = tmp_path / 'coverage.xml'
    coverage_xml.write_text(
        '<coverage><packages><package><classes>'
        '<class filename="routers/admin_import_jobs.py"><lines><line hits="1"/><line hits="0"/></lines></class>'
        '<class filename="services/admin_city_import_job_service.py"><lines><line hits="1"/><line hits="1"/></lines></class>'
        '<class filename="core/settings.py"><lines><line hits="0"/></lines></class>'
        '</classes></package></packages></coverage>',
        encoding='utf-8',
    )
    result = ci_coverage_summary.main([
        '--suite', 'backend',
        '--format', 'cobertura',
        '--input', str(coverage_xml),
        '--output', str(tmp_path / 'coverage.txt'),
        '--json-output', str(tmp_path / 'coverage.json'),
        '--fail-under', 'backend_admin=90',
    ])

    payload = json.loads((tmp_path / 'coverage.json').read_text(encoding='utf-8'))
    admin = next(group for group in payload['groups'] if group['name'] == 'backend_admin')
    assert result == 1
    assert admin['pct'] == 75.0
    assert admin['enforced'] is True


def test_frontend_admin_coverage_metric(tmp_path: Path) -> None:
    summary_json = tmp_path / 'coverage-summary.json'
    summary_json.write_text(
        json.dumps({
            'total': {'lines': {'total': 10, 'covered': 9, 'pct': 90}},
            '/repo/frontend/src/pages/admin/AdminImportJobsPage.tsx': {'lines': {'total': 4, 'covered': 4, 'pct': 100}},
            '/repo/frontend/src/App.tsx': {'lines': {'total': 6, 'covered': 5, 'pct': 83.33}},
        }),
        encoding='utf-8',
    )
    result = ci_coverage_summary.main([
        '--suite', 'frontend',
        '--format', 'vitest-json-summary',
        '--input', str(summary_json),
        '--output', str(tmp_path / 'coverage.txt'),
        '--json-output', str(tmp_path / 'coverage.json'),
        '--fail-under', 'frontend_admin=90',
    ])

    payload = json.loads((tmp_path / 'coverage.json').read_text(encoding='utf-8'))
    admin = next(group for group in payload['groups'] if group['name'] == 'frontend_admin')
    assert result == 0
    assert admin['pct'] == 100.0
    assert admin['passed'] is True
