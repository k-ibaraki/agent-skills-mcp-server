#!/usr/bin/env python3
"""Run code quality checks (lint + format check)."""

import subprocess
import sys


def main() -> int:
    """Run ruff check and format check."""
    print("🔍 Running code quality checks...")
    print()

    # Run lint check
    print("📋 Running ruff lint check...")
    result_lint = subprocess.run(
        ["uv", "run", "ruff", "check", "src/", "tests/"],
        check=False,
    )

    # Run format check
    print()
    print("🎨 Running ruff format check...")
    result_format = subprocess.run(
        ["uv", "run", "ruff", "format", "--check", "src/", "tests/"],
        check=False,
    )

    # Return non-zero if any check failed
    if result_lint.returncode != 0 or result_format.returncode != 0:
        print()
        print("❌ Code quality checks failed!")
        print("💡 Run 'uv run python scripts/fix.py' to auto-fix issues")
        return 1

    print()
    print("✅ All code quality checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
