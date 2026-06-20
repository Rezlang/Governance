"""Matching logic for activation and chain expectations."""

from fnmatch import fnmatch
from typing import Any

from integration_testing.models import ExpectedActivation, MatchMode
from integration_testing.recorder import RecordedToolUse


def strip_mcp_prefix(name: str) -> str:
    """Reduce 'mcp__server__tool' to 'tool'; leave other names unchanged."""
    if name.startswith("mcp__"):
        parts = name.split("__")
        if len(parts) >= 3:
            return "__".join(parts[2:])
    return name


def _candidates(use: RecordedToolUse) -> set[str]:
    """All names an expectation may legitimately match against for one invocation."""
    names = {use.name, strip_mcp_prefix(use.name)}
    if use.skill_name:
        names.add(use.skill_name)
    return {n for n in names if n}


def _resolve_mode(expected: str, mode: MatchMode) -> MatchMode:
    if mode != "auto":
        return mode
    if "*" in expected or "?" in expected or "[" in expected:
        return "glob"
    if expected.startswith("mcp__"):
        return "exact"
    return "loose"


def name_matches(expected: str, use: RecordedToolUse, mode: MatchMode = "auto") -> bool:
    """Return True if ``expected`` matches the recorded invocation under ``mode``."""
    resolved = _resolve_mode(expected, mode)
    if resolved == "glob":
        return any(fnmatch(candidate, expected) for candidate in _candidates(use))
    if resolved == "exact":
        return expected == use.name
    # loose: compare against every candidate name
    return expected in _candidates(use)


def args_match(expected_args: dict[str, Any], recorded_input: dict[str, Any]) -> bool:
    """Return True if every expected argument is present and matches.

    String expectations support glob patterns; other types compare by equality.
    Only the keys listed in ``expected_args`` are checked (subset match).
    """
    for key, expected in expected_args.items():
        if key not in recorded_input:
            return False
        actual = recorded_input[key]
        if isinstance(expected, str) and isinstance(actual, str):
            if any(ch in expected for ch in "*?["):
                if not fnmatch(actual, expected):
                    return False
            elif actual != expected:
                return False
        elif actual != expected:
            return False
    return True


def find_matches(
    expectation: ExpectedActivation, uses: list[RecordedToolUse]
) -> list[RecordedToolUse]:
    """All recorded invocations satisfying both the name and argument constraints."""
    return [
        use
        for use in uses
        if name_matches(expectation.name, use, expectation.match)
        and args_match(expectation.arguments, use.input)
    ]
