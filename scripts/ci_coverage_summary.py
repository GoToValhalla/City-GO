#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def norm(path: str) -> str:
    return path.replace('\\', '/').lstrip('./')


def parse_limit(items: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for item in items:
        name, value = item.split('=', 1)
        result[name.strip()] = float(value.strip())
    return result


def read_cobertura(path: Path) -> list[tuple[str, int, int]]:
    root = ET.parse(path).getroot()
    files: list[tuple[str, int, int]] = []
    for node in root.findall('.//class'):
        filename = norm(node.attrib.get('filename') or node.attrib.get('name') or '')
        lines = node.findall('./lines/line')
        total = len(lines)
        covered = sum(1 for line in lines if int(line.attrib.get('hits', '0') or 0) > 0)
        if filename and total:
            files.append((filename, covered, total))
    return files


def read_vitest_summary(path: Path) -> list[tuple[str, int, int]]:
    data = json.loads(path.read_text(encoding='utf-8'))
    files: list[tuple[str, int, int]] = []
    for filename, metrics in data.items():
        if filename == 'total':
            continue
        lines = metrics.get('lines') or {}
        total = int(lines.get('total') or 0)
        covered = int(lines.get('covered') or 0)
        if total:
            files.append((norm(filename), covered, total))
    return files


def has(path: str, needle: str) -> bool:
    value = '/' + norm(path)
    return value.startswith('/' + needle) or ('/' + needle) in value


def select_group(suite: str, group: str, files: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    if group.endswith('_overall'):
        return files
    if suite == 'backend' and group == 'backend_admin':
        return [item for item in files if has(item[0], 'routers/admin') or has(item[0], 'services/admin') or has(item[0], 'schemas/admin')]
    if suite == 'backend' and group == 'backend_platform':
        return [item for item in files if any(has(item[0], prefix) for prefix in ('core/', 'routers/', 'services/', 'models/', 'schemas/'))]
    if suite == 'frontend' and group == 'frontend_admin':
        return [item for item in files if has(item[0], 'src/pages/admin/') or has(item[0], 'src/components/admin/')]
    if suite == 'frontend' and group == 'frontend_ui':
        return [item for item in files if has(item[0], 'src/')]
    return []


def pct(covered: int, total: int) -> float:
    return covered / total * 100 if total else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=('backend', 'frontend'), required=True)
    parser.add_argument('--format', choices=('cobertura', 'vitest-json-summary'), required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--json-output', type=Path, required=True)
    parser.add_argument('--target', action='append', default=[])
    parser.add_argument('--fail-under', action='append', default=[])
    args = parser.parse_args(argv)

    targets = parse_limit(args.target)
    enforced = parse_limit(args.fail_under)
    default_target = targets.get('default', 90.0)
    files = read_cobertura(args.input) if args.format == 'cobertura' else read_vitest_summary(args.input)
    group_names = ['backend_platform', 'backend_admin', 'backend_overall'] if args.suite == 'backend' else ['frontend_ui', 'frontend_admin', 'frontend_overall']

    rows = []
    failed = False
    for name in group_names:
        selected = select_group(args.suite, name, files)
        covered = sum(item[1] for item in selected)
        total = sum(item[2] for item in selected)
        target = targets.get(name, default_target)
        fail_under = enforced.get(name, target)
        value = pct(covered, total)
        is_enforced = name in enforced
        passed = total > 0 and value >= fail_under
        failed = failed or (is_enforced and not passed)
        rows.append({'name': name, 'covered': covered, 'total': total, 'pct': round(value, 2), 'target': target, 'fail_under': fail_under, 'enforced': is_enforced, 'passed': passed})

    icon = '❌' if failed else '✅'
    lines = [f'{icon} City Go {args.suite} coverage', f"Прогон: #{os.getenv('GITHUB_RUN_NUMBER', 'unknown')} · commit {os.getenv('GITHUB_SHA', 'unknown')[:7]}", '', 'Метрики покрытия строк:']
    for row in rows:
        mark = '✅' if row['passed'] else ('❌' if row['enforced'] else '⚠️')
        mode = f"baseline {row['fail_under']:.1f}% enforced" if row['enforced'] else 'tracked'
        lines.append(f"- {mark} {row['name'].replace('_', ' ')}: {row['pct']:.1f}% ({row['covered']}/{row['total']}) · target {row['target']:.1f}% · {mode}")
    if failed:
        lines += ['', 'Что делать: открыть coverage artifact, найти непокрытые строки и добавить атомарные unit/API/UI тесты под эти ветки.']
    message = '\n'.join(lines) + '\n'

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(message, encoding='utf-8')
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps({'suite': args.suite, 'groups': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if os.getenv('GITHUB_STEP_SUMMARY'):
        Path(os.environ['GITHUB_STEP_SUMMARY']).open('a', encoding='utf-8').write('\n```text\n' + message + '```\n')
    print(message)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
