"""Policy registry for managing and chaining policies."""

from collections import defaultdict
from typing import Any

from model_governance.policies.base import Policy, PolicyAction, PolicyDecision, PolicyResult


class PolicyRegistry:
    """Registry for managing and organizing governance policies.

    The registry allows policies to be registered, retrieved, and
    organized into chains for sequential evaluation.
    """

    def __init__(self) -> None:
        """Initialize an empty policy registry."""
        self._policies: dict[str, Policy] = {}
        self._chains: dict[str, list[str]] = defaultdict(list)
        self._metadata: dict[str, dict[str, Any]] = defaultdict(dict)

    def register(self, policy: Policy, metadata: dict[str, Any] | None = None) -> None:
        """Register a policy.

        Args:
            policy: The policy to register.
            metadata: Optional metadata for the policy.

        Raises:
            ValueError: If a policy with the same name is already registered.
        """
        if policy.name in self._policies:
            raise ValueError(f"Policy '{policy.name}' is already registered")
        self._policies[policy.name] = policy
        if metadata:
            self._metadata[policy.name] = metadata

    def unregister(self, name: str) -> Policy | None:
        """Unregister a policy by name.

        Args:
            name: The name of the policy to unregister.

        Returns:
            The unregistered policy, or None if not found.
        """
        return self._policies.pop(name, None)

    def get(self, name: str) -> Policy | None:
        """Get a policy by name.

        Args:
            name: The name of the policy to retrieve.

        Returns:
            The policy if found, None otherwise.
        """
        return self._policies.get(name)

    def list_policies(self) -> list[str]:
        """List all registered policy names.

        Returns:
            List of policy names.
        """
        return list(self._policies.keys())

    def create_chain(self, chain_name: str, policy_names: list[str]) -> None:
        """Create a chain of policies for sequential evaluation.

        Policies are ordered by priority (highest first) within the chain.

        Args:
            chain_name: Name for the policy chain.
            policy_names: List of policy names to include in the chain.

        Raises:
            ValueError: If any policy name is not registered.
        """
        missing = [name for name in policy_names if name not in self._policies]
        if missing:
            raise ValueError(f"Policies not registered: {missing}")

        policies = [self._policies[name] for name in policy_names]
        policies.sort(key=lambda p: p.priority, reverse=True)
        self._chains[chain_name] = [p.name for p in policies]

    def get_chain(self, chain_name: str) -> list[str] | None:
        """Get a policy chain by name.

        Args:
            chain_name: The name of the chain.

        Returns:
            List of policy names in the chain, or None if not found.
        """
        return self._chains.get(chain_name)

    async def evaluate_chain(
        self, chain_name: str, content: str, context: dict | None = None
    ) -> list[PolicyResult]:
        """Evaluate all policies in a chain.

        Evaluation stops early if a high-confidence violation is found.

        Args:
            chain_name: Name of the policy chain to evaluate.
            content: The content to evaluate.
            context: Optional context for evaluation.

        Returns:
            List of PolicyResult objects from evaluated policies.
        """
        context = context or {}
        chain = self._chains.get(chain_name, [])
        results: list[PolicyResult] = []

        for policy_name in chain:
            policy = self._policies.get(policy_name)
            if policy is None:
                continue

            result = await policy.evaluate(content, context)
            result.policy_name = policy_name
            results.append(result)

            if result.is_block():
                break

        return results

    async def make_decision(
        self, chain_name: str, content: str, context: dict | None = None
    ) -> PolicyDecision:
        """Make a policy decision by evaluating a chain.

        Args:
            chain_name: Name of the policy chain to evaluate.
            content: The content to evaluate.
            context: Optional context for evaluation.

        Returns:
            PolicyDecision with the final action to take.
        """
        results = await self.evaluate_chain(chain_name, content, context)

        for result in results:
            if result.is_block():
                return PolicyDecision(
                    action=PolicyAction.BLOCK, reason=result.reason, policy_name=result.policy_name
                )
            if result.is_warn():
                return PolicyDecision(
                    action=PolicyAction.WARN, reason=result.reason, policy_name=result.policy_name
                )

        return PolicyDecision(action=PolicyAction.ALLOW, reason="All policies passed")

    def clear(self) -> None:
        """Clear all registered policies and chains."""
        self._policies.clear()
        self._chains.clear()
        self._metadata.clear()
