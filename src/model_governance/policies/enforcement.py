"""Enforcement mechanisms for policy violations."""

from dataclasses import dataclass

from model_governance.policies.base import PolicyAction, PolicyResult


@dataclass
class EnforcementDecision:
    """Decision made by an enforcement mechanism.

    Attributes:
        action: The enforcement action to take.
        reason: Explanation for the decision.
        modified_content: Content after modification (if applicable).
        confidence: Confidence in the decision (0.0 to 1.0).
        metadata: Additional metadata about the decision.
    """

    action: PolicyAction
    reason: str
    modified_content: str | None = None
    confidence: float = 1.0
    metadata: dict[str, object] | None = None


class EnforcementMechanism:
    """Base class for enforcement mechanisms.

    Enforcement mechanisms decide what action to take when a policy
    is violated.
    """

    async def enforce(
        self, policy_result: PolicyResult, content: str, context: dict
    ) -> EnforcementDecision:
        """Enforce a policy decision.

        Args:
            policy_result: The result from policy evaluation.
            content: The content being evaluated.
            context: Additional context for enforcement.

        Returns:
            EnforcementDecision with the action to take.
        """
        raise NotImplementedError


class BlockingEnforcer(EnforcementMechanism):
    """Simple blocking enforcer.

    Blocks content when policy confidence is above threshold,
    otherwise warns.
    """

    def __init__(self, block_threshold: float = 0.7) -> None:
        """Initialize the blocking enforcer.

        Args:
            block_threshold: Confidence level above which to block.
        """
        self.block_threshold = block_threshold

    async def enforce(
        self, policy_result: PolicyResult, content: str, context: dict
    ) -> EnforcementDecision:
        """Enforce the policy decision.

        Args:
            policy_result: The result from policy evaluation.
            content: The content being evaluated.
            context: Additional context for enforcement.

        Returns:
            EnforcementDecision with the appropriate action.
        """
        if not policy_result.allowed:
            if policy_result.confidence >= self.block_threshold:
                return EnforcementDecision(
                    action=PolicyAction.BLOCK, reason=policy_result.reason, confidence=policy_result.confidence
                )
            return EnforcementDecision(
                action=PolicyAction.WARN, reason=policy_result.reason, confidence=policy_result.confidence
            )

        return EnforcementDecision(action=PolicyAction.ALLOW, reason="Allowed")


class StrictEnforcer(EnforcementMechanism):
    """Strict enforcer that blocks all policy violations."""

    async def enforce(
        self, policy_result: PolicyResult, content: str, context: dict
    ) -> EnforcementDecision:
        """Enforce the policy decision strictly.

        Args:
            policy_result: The result from policy evaluation.
            content: The content being evaluated.
            context: Additional context for enforcement.

        Returns:
            EnforcementDecision with BLOCK action for any violation.
        """
        if not policy_result.allowed:
            return EnforcementDecision(
                action=PolicyAction.BLOCK, reason=policy_result.reason, confidence=policy_result.confidence
            )

        return EnforcementDecision(action=PolicyAction.ALLOW, reason="Allowed")


class ReviewEnforcer(EnforcementMechanism):
    """Enforcer that flags content for review instead of blocking."""

    def __init__(self, block_threshold: float = 0.9) -> None:
        """Initialize the review enforcer.

        Args:
            block_threshold: Confidence level above which to block instead of review.
        """
        self.block_threshold = block_threshold

    async def enforce(
        self, policy_result: PolicyResult, content: str, context: dict
    ) -> EnforcementDecision:
        """Enforce the policy decision with review preference.

        Args:
            policy_result: The result from policy evaluation.
            content: The content being evaluated.
            context: Additional context for enforcement.

        Returns:
            EnforcementDecision with REVIEW action for most violations.
        """
        if not policy_result.allowed:
            if policy_result.confidence >= self.block_threshold:
                return EnforcementDecision(
                    action=PolicyAction.BLOCK, reason=policy_result.reason, confidence=policy_result.confidence
                )
            return EnforcementDecision(
                action=PolicyAction.REQUIRE_REVIEW, reason=policy_result.reason, confidence=policy_result.confidence
            )

        return EnforcementDecision(action=PolicyAction.ALLOW, reason="Allowed")


class CompositeEnforcer(EnforcementMechanism):
    """Enforcer that combines multiple enforcement strategies.

    Uses different enforcers based on context or policy type.
    """

    def __init__(self, default_enforcer: EnforcementMechanism | None = None) -> None:
        """Initialize the composite enforcer.

        Args:
            default_enforcer: Default enforcer to use if no specific one matches.
        """
        self._default_enforcer = default_enforcer or BlockingEnforcer()
        self._enforcers: dict[str, EnforcementMechanism] = {}

    def register_enforcer(self, policy_name: str, enforcer: EnforcementMechanism) -> None:
        """Register an enforcer for a specific policy.

        Args:
            policy_name: The policy name to use this enforcer for.
            enforcer: The enforcer to use for the policy.
        """
        self._enforcers[policy_name] = enforcer

    async def enforce(
        self, policy_result: PolicyResult, content: str, context: dict
    ) -> EnforcementDecision:
        """Enforce using the appropriate enforcer.

        Args:
            policy_result: The result from policy evaluation.
            content: The content being evaluated.
            context: Additional context for enforcement.

        Returns:
            EnforcementDecision from the appropriate enforcer.
        """
        policy_name = policy_result.policy_name
        enforcer = self._enforcers.get(policy_name, self._default_enforcer)
        return await enforcer.enforce(policy_result, content, context)


class DetectEnforcer(EnforcementMechanism):
    """Enforcer that detects violations but allows content.

    In detect mode, violations are logged as warnings but the content
    is allowed to pass through.
    """

    async def enforce(
        self, policy_result: PolicyResult, content: str, context: dict
    ) -> EnforcementDecision:
        """Enforce the policy decision with detect mode.

        Args:
            policy_result: The result from policy evaluation.
            content: The content being evaluated.
            context: Additional context for enforcement.

        Returns:
            EnforcementDecision with WARN action for violations (allows content).
        """
        if not policy_result.allowed:
            return EnforcementDecision(
                action=PolicyAction.WARN,
                reason=f"[DETECTED] {policy_result.reason}",
                confidence=policy_result.confidence,
                metadata={"detection": True},
            )

        return EnforcementDecision(action=PolicyAction.ALLOW, reason="Allowed")


class ModifyEnforcer(EnforcementMechanism):
    """Enforcer that modifies content instead of blocking.

    In modify mode, problematic parts of the content are removed or
    sanitized while allowing the rest to pass through.
    """

    def __init__(self, replacement_char: str = "***") -> None:
        """Initialize the modify enforcer.

        Args:
            replacement_char: Character(s) to replace problematic content with.
        """
        self._replacement_char = replacement_char

    async def enforce(
        self, policy_result: PolicyResult, content: str, context: dict
    ) -> EnforcementDecision:
        """Enforce the policy decision with modify mode.

        Args:
            policy_result: The result from policy evaluation.
            content: The content being evaluated.
            context: Additional context for enforcement.

        Returns:
            EnforcementDecision with MODIFY action for violations.
        """
        if not policy_result.allowed:
            modified_content = self._modify_content(content, policy_result)
            return EnforcementDecision(
                action=PolicyAction.MODIFY,
                reason=f"[MODIFIED] {policy_result.reason}",
                modified_content=modified_content,
                confidence=policy_result.confidence,
                metadata={"modified": True},
            )

        return EnforcementDecision(action=PolicyAction.ALLOW, reason="Allowed")

    def _modify_content(self, content: str, policy_result: PolicyResult) -> str:
        """Modify content based on policy violation.

        Args:
            content: The content to modify.
            policy_result: The policy result with violation details.

        Returns:
            Modified content.
        """
        # Get the matched pattern from metadata
        pattern = policy_result.metadata.get("matched_pattern", "")
        if pattern:
            # Replace the matched pattern with placeholder
            modified = content.replace(pattern, self._replacement_char)
            return modified

        # If no specific pattern, return original
        return content

