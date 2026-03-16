#!/usr/bin/env python3
"""Run unit and integration tests with output logging."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def run_tests(
    output_file: str = "test_output.txt",
    verbosity: int = 1,
) -> int:
    """Run pytest and save output to file.

    Args:
        output_file: File to write test output to.
        verbosity: Verbosity level (0=low, 1=medium, 2=high).

    Returns:
        Exit code from pytest.
    """
    # Set verbosity environment variable for conftest.py
    os.environ["TEST_VERBOSITY"] = str(verbosity)

    with open(output_file, "w") as f:
        # Write header
        f.write("=" * 80 + "\n")
        f.write("MODEL GOVERNANCE TEST OUTPUT\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Verbosity: {verbosity} (0=low, 1=medium, 2=high)\n")
        f.write("=" * 80 + "\n\n")

        # Run pytest and capture output
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/",
                "-v",
                "--tb=short",
                f"--color=no",
                "-s",  # Don't capture stdout (show print statements)
            ],
            cwd=Path(__file__).parent,
            stdout=f,
            stderr=subprocess.STDOUT,
            env=os.environ,
        )

        # Write footer
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Exit code: {result.returncode}\n")
        f.write("=" * 80 + "\n")

    # Also print to console
    with open(output_file, "r") as f:
        print(f.read())

    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run model governance tests")
    parser.add_argument(
        "output_file",
        nargs="?",
        default="test_output.txt",
        help="File to write test output to (default: test_output.txt)",
    )
    parser.add_argument(
        "-V",
        "--verbosity",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="Verbosity level: 0=low (minimal), 1=medium (standard), 2=high (detailed)",
    )

    args = parser.parse_args()
    sys.exit(run_tests(args.output_file, args.verbosity))
