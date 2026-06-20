"""Run tests: build the prompt, drive a session, evaluate expectations."""

from integration_testing.matchers import find_matches, name_matches
from integration_testing.models import SessionConfig, TestCase, TestSuite
from integration_testing.recorder import RecordedToolUse, SessionRecorder
from integration_testing.results import ActivationCheck, TestResult
from integration_testing.session import run_session


def _build_prompt(test: TestCase) -> str:
    """Derive the session prompt for an activation or chain test."""
    if test.type == "activation":
        assert test.prompt is not None  # guaranteed by model validation
        return test.prompt

    assert test.trigger is not None  # guaranteed by model validation
    trigger = test.trigger
    if trigger.mode == "manual" and trigger.seed:
        directive = (
            f"Before doing anything else, use the `{trigger.seed}` {trigger.seed_kind}. "
            f"Then continue with the request below.\n\n"
        )
        return directive + trigger.prompt
    return trigger.prompt


def _evaluate(test: TestCase, recorder: SessionRecorder) -> tuple[list[ActivationCheck], bool]:
    """Compare recorded tool/skill uses against the test's expectations."""
    uses: list[RecordedToolUse] = recorder.tool_uses
    checks: list[ActivationCheck] = []

    # For chain tests, confirm the seed A actually activated.
    if test.type == "chain" and test.trigger and test.trigger.seed:
        seed = test.trigger.seed
        hit = any(name_matches(seed, use) for use in uses)
        checks.append(
            ActivationCheck(
                kind="seed",
                expected=seed,
                satisfied=hit,
                reason="" if hit else f"seed '{seed}' was never activated",
            )
        )

    # Required (and optional) activations.
    for expectation in test.expect_activated:
        matched = find_matches(expectation, uses)
        enough = len(matched) >= expectation.min_count
        satisfied = enough or expectation.optional
        if enough:
            reason = f"matched {len(matched)} invocation(s)"
        elif expectation.optional:
            reason = "not activated (optional)"
        else:
            reason = f"expected >= {expectation.min_count}, found {len(matched)}"
        checks.append(
            ActivationCheck(
                kind="activated",
                expected=expectation.describe(),
                satisfied=satisfied,
                reason=reason,
            )
        )

    # Forbidden activations.
    for name in test.expect_not_activated:
        offenders = [use.label() for use in uses if name_matches(name, use)]
        satisfied = not offenders
        checks.append(
            ActivationCheck(
                kind="not_activated",
                expected=name,
                satisfied=satisfied,
                reason="" if satisfied else f"unexpectedly activated: {', '.join(offenders)}",
            )
        )

    passed = recorder.error is None and all(check.satisfied for check in checks)
    return checks, passed


async def run_test(test: TestCase, defaults: SessionConfig | None = None) -> TestResult:
    """Run a single test and return its result."""
    config = (defaults or SessionConfig()).merge(test.session)
    prompt = _build_prompt(test)
    recorder = await run_session(prompt, config, timeout=test.timeout)
    checks, passed = _evaluate(test, recorder)

    return TestResult(
        name=test.name,
        type=test.type,
        kind=test.kind,
        passed=passed,
        checks=checks,
        recorded_tool_uses=[use.label() for use in recorder.tool_uses],
        transcript=recorder.transcript,
        raw_messages=recorder.raw_messages,
        error=recorder.error,
        duration_ms=recorder.duration_ms,
        cost_usd=recorder.cost_usd,
        num_turns=recorder.num_turns,
        prompt=prompt,
    )


async def run_suite(suite: TestSuite) -> list[TestResult]:
    """Run every test in a suite sequentially (sessions are stateful and stateless across tests)."""
    results: list[TestResult] = []
    for test in suite.tests:
        results.append(await run_test(test, suite.defaults))
    return results


async def run_suites(suites: list[TestSuite]) -> list[TestResult]:
    """Run multiple suites, concatenating their results."""
    results: list[TestResult] = []
    for suite in suites:
        results.extend(await run_suite(suite))
    return results
