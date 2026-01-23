#!/usr/bin/env python3
"""Auto-fix code quality issues (lint + format)."""

import subprocess
import sys


def main() -> int:
    """Run ruff check with --fix and format."""
    print("🔧 Auto-fixing code quality issues...")
    print()

    # Run lint fix
    print("📋 Running ruff lint --fix...")
    result_lint = subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", "src/", "tests/"],
        check=False,
    )

    # Run format
    print()
    print("🎨 Running ruff format...")
    result_format = subprocess.run(
        ["uv", "run", "ruff", "format", "src/", "tests/"],
        check=False,
    )

    # Return non-zero if any operation failed
    if result_lint.returncode != 0 or result_format.returncode != 0:
        print()
        print("❌ Some issues could not be auto-fixed!")
        print("💡 Please fix remaining issues manually")
        return 1

    print()
    print("✅ Code quality issues fixed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
