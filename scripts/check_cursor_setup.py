#!/usr/bin/env python3
"""Validate Cursor setup for the City-GO repository."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

CORE_RULE = ROOT / ".cursor" / "rules" / "00-city-go-core.mdc"
TOKEN_RULE = ROOT / ".cursor" / "rules" / "10-token-economy.mdc"
CURSORIGNORE = ROOT / ".cursorignore"


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


def check(name: str, passed: bool) -> bool:
    """Print one check result and return its boolean state."""
    status = "OK" if passed else "FAIL"
    print(f"{status}: {name}")
    return passed


def main() -> int:
    """Run all Cursor setup checks."""
    results: list[bool] = []

    results.append(check(f"{CORE_RULE.relative_to(ROOT)} exists", CORE_RULE.exists()))
    if CORE_RULE.exists():
        core_text = read_text(CORE_RULE)
        results.append(check("core rule contains 'alwaysApply: true'", "alwaysApply: true" in core_text))
        results.append(check("core rule contains '## Token economy'", "## Token economy" in core_text))

    results.append(check(f"{TOKEN_RULE.relative_to(ROOT)} exists", TOKEN_RULE.exists()))
    if TOKEN_RULE.exists():
        token_text = read_text(TOKEN_RULE)
        results.append(check("token economy rule contains 'alwaysApply: false'", "alwaysApply: false" in token_text))

    results.append(check(f"{CURSORIGNORE.relative_to(ROOT)} exists", CURSORIGNORE.exists()))
    if CURSORIGNORE.exists():
        cursorignore_text = read_text(CURSORIGNORE)
        cursorignore_lines = normalized_lines(cursorignore_text)

        results.append(check(".cursorignore contains exact line '.env'", ".env" in cursorignore_lines))
        results.append(check(".cursorignore contains exact line '.env.*'", ".env.*" in cursorignore_lines))
        results.append(check(".cursorignore contains exact line '!.env.example'", "!.env.example" in cursorignore_lines))
        results.append(check(".cursorignore contains exact line '*.bak'", "*.bak" in cursorignore_lines))

        results.append(check(".cursorignore does not contain wrong exact line '.env.'", ".env." not in cursorignore_lines))
        results.append(check(".cursorignore does not contain wrong exact line '.bak'", ".bak" not in cursorignore_lines))

    if all(results):
        print("\nCursor setup validation passed.")
        return 0

    print("\nCursor setup validation failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
