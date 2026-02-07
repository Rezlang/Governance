"""Trust level classifications and policies for the governance system."""

from enum import IntEnum
from typing import Protocol, runtime_checkable


class TrustLevel(IntEnum):
    """Trust level classifications for content and sources.

    Trust levels are hierarchical - higher values indicate greater trust.
    This hierarchy enables access control based on trust thresholds.
    """

    UNTRUSTED = 0
    """Content from unknown or potentially malicious sources."""

    LOW = 1
    """Content with limited trust, requires scrutiny."""

    MEDIUM = 2
    """Content from moderately trusted sources."""

    HIGH = 3
    """Content from highly trusted sources."""

    CRITICAL = 4
    """Content from the system itself or fully trusted sources."""

    @classmethod
    def get_default(cls) -> "TrustLevel":
        """Get the default trust level for unknown sources.

        Returns:
            The default trust level (LOW).
        """
        return cls.LOW

    def can_access(self, required_level: "TrustLevel") -> bool:
        """Check if this level can access resources requiring required_level.

        Args:
            required_level: The minimum trust level required.

        Returns:
            True if this level meets or exceeds the required level.
        """
        return self.value >= required_level.value

    def requires_review(self) -> bool:
        """Whether content at this level requires manual review.

        Returns:
            True if content at this level requires review.
        """
        return self.value <= TrustLevel.LOW

    def is_blocked_by_default(self) -> bool:
        """Whether content at this level should be blocked by default.

        Returns:
            True if content should be blocked without explicit approval.
        """
        return self.value <= TrustLevel.UNTRUSTED


@runtime_checkable
class TrustPolicy(Protocol):
    """Protocol for trust-based policies.

    Trust policies determine whether content at a given trust level
    should be allowed, blocked, or require additional review.
    """

    async def is_allowed(self, level: TrustLevel, context: dict) -> tuple[bool, str]:
        """Check if content at the given trust level is allowed.

        Args:
            level: The trust level to check.
            context: Additional context for the decision.

        Returns:
            A tuple of (is_allowed, reason).
        """
        ...


def parse_trust_level(value: str | int | TrustLevel) -> TrustLevel:
    """Parse a trust level from various input types.

    Args:
        value: The value to parse (string, int, or TrustLevel).

    Returns:
        The parsed TrustLevel.

    Raises:
        ValueError: If the value cannot be parsed.
    """
    if isinstance(value, TrustLevel):
        return value
    if isinstance(value, int):
        try:
            return TrustLevel(value)
        except ValueError:
            raise ValueError(f"Invalid trust level int: {value}")
    if isinstance(value, str):
        try:
            return TrustLevel[value.upper()]
        except KeyError:
            try:
                return TrustLevel(int(value))
            except (ValueError, KeyError):
                raise ValueError(f"Invalid trust level string: {value}")
    raise ValueError(f"Cannot parse trust level from: {value}")
