#!/usr/bin/env python3
"""Validate Cursor setup for the City-GO repository."""

from dataclasses import dataclass
from pathlib import Path
import argparse
import sys


ROOT = Path(__file__).resolve().parents[1]

CORE_RULE = ROOT / ".cursor" / "rules" / "00-city-go-core.mdc"
TOKEN_RULE = ROOT / ".cursor" / "rules" / "10-token-economy.mdc"
CURSORIGNORE = ROOT / ".cursorignore"


@dataclass
class Check:
    name: str
    passed: bool


def read_text(path: Path) -> str:
    """Read a text file safely."""
    return path.read_text(encoding="utf-8")


def normalized_lines(text: str) -> set[str]:
    """Return meaningful trimmed lines, excluding empty lines and comments."""
    return {
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def check(name: str, passed: bool) -> Check:
    """Create a Check object."""
    return Check(name=name, passed=passed)


def main() -> int:
    """Run all Cursor setup checks."""
    parser = argparse.ArgumentParser(description="Validate Cursor setup for the City-GO repository.")
    parser.add_argument("--quiet", action="store_true", help="Print only the final summary")
    args = parser.parse_args()

    results: list[Check] = []

    def add_check(name: str, passed: bool):
        c = check(name, passed)
        results.append(c)
        if not args.quiet:
            status = "OK" if c.passed else "FAIL"
            print(f"{status}: {c.name}")

    add_check(f"{CORE_RULE.relative_to(ROOT)} exists", CORE_RULE.exists())
    if CORE_RULE.exists():
        core_text = read_text(CORE_RULE)
        add_check("core rule contains 'alwaysApply: true'", "alwaysApply: true" in core_text)
        add_check("core rule contains '## Token economy'", "## Token economy" in core_text)

    add_check(f"{TOKEN_RULE.relative_to(ROOT)} exists", TOKEN_RULE.exists())
    if TOKEN_RULE.exists():
        token_text = read_text(TOKEN_RULE)
        add_check("token economy rule contains 'alwaysApply: false'", "alwaysApply: false" in token_text)

    add_check(f"{CURSORIGNORE.relative_to(ROOT)} exists", CURSORIGNORE.exists())
    if CURSORIGNORE.exists():
        cursorignore_text = read_text(CURSORIGNORE)
        cursorignore_lines = normalized_lines(cursorignore_text)

        add_check(".cursorignore contains exact line '.env'", ".env" in cursorignore_lines)
        add_check(".cursorignore contains exact line '.env.*'", ".env.*" in cursorignore_lines)
        add_check(".cursorignore contains exact line '!.env.example'", "!.env.example" in cursorignore_lines)
        add_check(".cursorignore contains exact line '*.bak'", "*.bak" in cursorignore_lines)

        add_check(".cursorignore does not contain wrong exact line '.env.'", ".env." not in cursorignore_lines)
        add_check(".cursorignore does not contain wrong exact line '.bak'", ".bak" not in cursorignore_lines)

    if all(c.passed for c in results):
        print("\nCursor setup validation passed.")
        return 0

    print("\nCursor setup validation failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
