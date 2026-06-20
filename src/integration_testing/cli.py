"""Command-line entry point: ``python -m integration_testing PATH [PATH...]``."""

import argparse
import asyncio
import sys

from integration_testing.loader import load_suites
from integration_testing.reporter import report, report_json
from integration_testing.runner import run_suites


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="integration_testing",
        description=(
            "Run MCP tool / skill activation and chain tests against a real Claude "
            "agent session (via the Claude Agent SDK, using your local Claude credentials)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Test YAML files or directories (searched for *.test.yaml).",
    )
    parser.add_argument(
        "-k",
        "--filter",
        default=None,
        help="Only run tests whose name contains this substring.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print transcripts for passing tests too.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the text report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    suites = load_suites(args.paths)
    if args.filter:
        for suite in suites:
            suite.tests = [t for t in suite.tests if args.filter in t.name]
    suites = [s for s in suites if s.tests]

    if not suites:
        print("No matching tests found.", file=sys.stderr)
        return 2

    results = asyncio.run(run_suites(suites))

    if args.json:
        return report_json(results)
    return report(results, verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
