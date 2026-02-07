"""Base policy classes and result types for the governance system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto


@dataclass
class PolicyResult:
    """Standard result for policy evaluations.

    Attributes:
        allowed: Whether the content is allowed by this policy.
        reason: Human-readable explanation of the decision.
        confidence: Confidence score for the decision (0.0 to 1.0).
        metadata: Additional metadata about the evaluation.
        policy_name: Name of the policy that produced this result.
    """

    allowed: bool
    reason: str
    confidence: float = 1.0
    metadata: dict[str, object] = field(default_factory=dict)
    policy_name: str | None = None

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def is_block(self) -> bool:
        """Check if this result indicates content should be blocked."""
        return not self.allowed and self.confidence >= 0.7

    def is_warn(self) -> bool:
        """Check if this result indicates a warning."""
        return not self.allowed and self.confidence < 0.7


class Policy(ABC):
    """Abstract base class for all governance policies.

    Policies evaluate content against specific rules and return
    a decision on whether the content should be allowed.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique policy name for registration and identification."""

        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Higher priority policies run first in chains.

        Priority should be a positive integer. Higher values indicate
        higher priority.
        """

        pass

    @abstractmethod
    async def evaluate(self, content: str, context: dict) -> PolicyResult:
        """Evaluate content against this policy.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        pass

    def allows(self, result: PolicyResult) -> bool:
        """Check if a policy result allows the content.

        Args:
            result: The policy result to check.

        Returns:
            True if the content is allowed.
        """
        return result.allowed

    def blocks(self, result: PolicyResult) -> bool:
        """Check if a policy result blocks the content.

        Args:
            result: The policy result to check.

        Returns:
            True if the content should be blocked.
        """
        return result.is_block()


class PolicyAction(Enum):
    """Actions that can be taken when a policy is violated."""

    BLOCK = auto()
    """Completely block the content."""

    WARN = auto()
    """Allow the content but log a warning."""

    MODIFY = auto()
    """Modify the content before allowing."""

    REQUIRE_REVIEW = auto()
    """Flag for manual review before allowing."""

    ALLOW = auto()
    """Allow the content without restrictions."""


@dataclass
class PolicyDecision:
    """Decision made by evaluating a policy.

    Attributes:
        action: The action to take.
        reason: Explanation for the decision.
        modified_content: The modified content if action is MODIFY.
        policy_name: Name of the policy that made the decision.
    """

    action: PolicyAction
    reason: str
    modified_content: str | None = None
    policy_name: str | None = None
