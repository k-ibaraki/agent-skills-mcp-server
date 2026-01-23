#!/usr/bin/env python3
"""Run tests with pytest."""

import subprocess
import sys


def main() -> int:
    """Run pytest with provided arguments."""
    args = sys.argv[1:]  # Pass through all arguments to pytest

    print("🧪 Running tests...")
    print()

    result = subprocess.run(
        ["uv", "run", "pytest", *args],
        check=False,
    )

    if result.returncode != 0:
        print()
        print("❌ Tests failed!")
        return 1

    print()
    print("✅ All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
