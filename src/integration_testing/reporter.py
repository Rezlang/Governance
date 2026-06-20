"""Render test results to the console (and optionally JSON)."""

import json
import sys
from typing import TextIO

from integration_testing.results import TestResult

_RULE = "=" * 78
_SUB = "-" * 78


def report(
    results: list[TestResult],
    *,
    verbose: bool = False,
    stream: TextIO | None = None,
) -> int:
    """Print a summary plus full transcripts for failing tests.

    For every failing test the complete agent transcript and the raw SDK message
    stream are printed, so the cause of a missed activation is always visible.
    With ``verbose=True`` the transcript is printed for passing tests too.

    Returns a process exit code: 0 if all tests passed, 1 otherwise.
    """
    out = stream or sys.stdout
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(_RULE, file=out)
    print("Integration test results", file=out)
    print(_RULE, file=out)
    for result in results:
        line = result.summary()
        if result.cost_usd is not None:
            line += f"  cost=${result.cost_usd:.4f}"
        if result.num_turns is not None:
            line += f"  turns={result.num_turns}"
        print(line, file=out)

    for result in results:
        show_detail = not result.passed or verbose
        if not show_detail:
            continue
        _print_detail(result, out, full=not result.passed)

    print(_RULE, file=out)
    print(f"Total: {len(results)}  passed: {len(passed)}  failed: {len(failed)}", file=out)
    print(_RULE, file=out)
    return 0 if not failed else 1


def _print_detail(result: TestResult, out: TextIO, *, full: bool) -> None:
    print("", file=out)
    print(_SUB, file=out)
    print(result.summary(), file=out)
    print(f"prompt: {result.prompt}", file=out)
    if result.error:
        print(f"error: {result.error}", file=out)

    for check in result.checks:
        print(f"  [{check.status()}] {check.kind}: {check.expected}", file=out)
        if check.reason:
            print(f"           -> {check.reason}", file=out)

    print(
        f"  observed activations: {result.recorded_tool_uses or '(none)'}",
        file=out,
    )

    if full:
        print("", file=out)
        print("  --- transcript ---", file=out)
        for line in result.transcript.splitlines():
            print(f"  {line}", file=out)
        print("", file=out)
        print("  --- raw SDK messages ---", file=out)
        for raw in result.raw_messages:
            print(f"  {raw}", file=out)


def report_json(results: list[TestResult], stream: TextIO | None = None) -> int:
    """Emit results as JSON. Returns 0 if all passed, else 1."""
    out = stream or sys.stdout
    payload = {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": [r.to_dict() for r in results],
    }
    json.dump(payload, out, indent=2)
    out.write("\n")
    return 0 if all(r.passed for r in results) else 1
