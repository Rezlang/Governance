"""Trust-based policies for access control and content filtering."""

from model_governance.trust.levels import TrustLevel


class TrustBasedPolicy:
    """Base class for trust-based policies.

    These policies enforce rules based on trust levels,
    such as requiring minimum trust levels or blocking
    content below certain thresholds.
    """

    def __init__(self, required_level: TrustLevel) -> None:
        """Initialize the policy.

        Args:
            required_level: The minimum trust level required.
        """
        self.required_level = required_level

    async def is_allowed(self, level: TrustLevel, context: dict) -> tuple[bool, str]:
        """Check if trust level is sufficient.

        Args:
            level: The trust level to check.
            context: Additional context for the decision.

        Returns:
            A tuple of (is_allowed, reason).
        """
        if not level.can_access(self.required_level):
            return (
                False,
                f"Requires {self.required_level.name} trust level, got {level.name}",
            )
        return True, "OK"


class BlockLowTrustPolicy(TrustBasedPolicy):
    """Blocks content below MEDIUM trust level.

    This policy is useful for requiring that content has at least
    been vetted to some degree before being processed.
    """

    def __init__(self) -> None:
        """Initialize the policy to block below MEDIUM trust."""
        super().__init__(TrustLevel.MEDIUM)


class RequireAuthPolicy(TrustBasedPolicy):
    """Requires HIGH trust level (authenticated)."""

    def __init__(self) -> None:
        """Initialize the policy to require HIGH trust."""
        super().__init__(TrustLevel.HIGH)


class RequireCriticalTrustPolicy(TrustBasedPolicy):
    """Requires CRITICAL trust level (system only)."""

    def __init__(self) -> None:
        """Initialize the policy to require CRITICAL trust."""
        super().__init__(TrustLevel.CRITICAL)


class BlockUntrustedPolicy(TrustBasedPolicy):
    """Blocks UNTRUSTED content only.

    This is a permissive policy that only blocks content explicitly
    marked as untrusted.
    """

    def __init__(self) -> None:
        """Initialize the policy to block only UNTRUSTED."""
        super().__init__(TrustLevel.LOW)


class TrustPolicyWithOptions:
    """Trust policy with configurable options for different trust levels."""

    def __init__(
        self,
        block_below: TrustLevel = TrustLevel.MEDIUM,
        review_below: TrustLevel = TrustLevel.MEDIUM,
        warn_below: TrustLevel = TrustLevel.HIGH,
    ) -> None:
        """Initialize the policy with configurable thresholds.

        Args:
            block_below: Block content below this level.
            review_below: Flag content below this level for review.
            warn_below: Show warnings for content below this level.
        """
        self.block_below = block_below
        self.review_below = review_below
        self.warn_below = warn_below

    async def evaluate(self, level: TrustLevel, context: dict) -> tuple[str, str]:
        """Evaluate trust level against configured thresholds.

        Args:
            level: The trust level to evaluate.
            context: Additional context for the decision.

        Returns:
            A tuple of (action, reason) where action is one of:
            "block", "review", "warn", "allow".
        """
        if level < self.block_below:
            return "block", f"Trust level {level.name} below block threshold {self.block_below.name}"
        if level < self.review_below:
            return "review", f"Trust level {level.name} requires review"
        if level < self.warn_below:
            return "warn", f"Trust level {level.name} below warning threshold"
        return "allow", "Trust level acceptable"
