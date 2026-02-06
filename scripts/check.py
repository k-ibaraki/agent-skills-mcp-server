#!/usr/bin/env python3
"""Run code quality checks (lint + format check + tests)."""

import subprocess
import sys


def main() -> int:
    """Run ruff check, format check, and tests."""
    print("🔍 Running code quality checks and tests...")
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

    # Run tests
    print()
    print("🧪 Running tests...")
    result_test = subprocess.run(
        ["uv", "run", "pytest", "-m", "unit", "-q"],
        check=False,
    )

    # Return non-zero if any check failed
    if result_lint.returncode != 0 or result_format.returncode != 0 or result_test.returncode != 0:
        print()
        print("❌ Checks failed!")
        if result_lint.returncode != 0 or result_format.returncode != 0:
            print("💡 Run 'uv run fix' to auto-fix lint/format issues")
        if result_test.returncode != 0:
            print("💡 Run 'uv run test' to see detailed test output")
        return 1

    print()
    print("✅ All checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
