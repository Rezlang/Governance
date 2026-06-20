"""Result types produced by running tests."""

from dataclasses import dataclass, field
from typing import Any, Literal

CheckKind = Literal["seed", "activated", "not_activated"]


@dataclass
class ActivationCheck:
    """The outcome of a single expectation within a test."""

    kind: CheckKind
    expected: str
    satisfied: bool
    reason: str = ""

    def status(self) -> str:
        return "ok" if self.satisfied else "FAILED"


@dataclass
class TestResult:
    """The aggregate outcome of running one :class:`~integration_testing.models.TestCase`."""

    name: str
    type: str
    kind: str
    passed: bool
    checks: list[ActivationCheck] = field(default_factory=list)
    recorded_tool_uses: list[str] = field(default_factory=list)
    transcript: str = ""
    raw_messages: list[str] = field(default_factory=list)
    error: str | None = None
    duration_ms: float | None = None
    cost_usd: float | None = None
    num_turns: int | None = None
    prompt: str = ""

    def summary(self) -> str:
        """One-line status string."""
        marker = "PASS" if self.passed else "FAIL"
        return f"[{marker}] {self.name} ({self.type}/{self.kind})"

    def to_dict(self) -> dict[str, Any]:
        """Serializable representation (used by the JSON reporter)."""
        return {
            "name": self.name,
            "type": self.type,
            "kind": self.kind,
            "passed": self.passed,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "cost_usd": self.cost_usd,
            "num_turns": self.num_turns,
            "prompt": self.prompt,
            "recorded_tool_uses": self.recorded_tool_uses,
            "checks": [
                {
                    "kind": c.kind,
                    "expected": c.expected,
                    "satisfied": c.satisfied,
                    "reason": c.reason,
                }
                for c in self.checks
            ],
        }
