"""Policy registry and evaluator for managing and evaluating governance policies."""

from collections import defaultdict
from typing import Any

from model_governance.core.modes import EnforcementMode
from model_governance.policies.base import Policy, PolicyAction, PolicyDecision, PolicyResult


class PolicyRegistry:
    """Registry for managing governance policies.

    The registry handles policy registration, retrieval, and organization
    into chains. It does NOT handle evaluation - that's done by PolicyEvaluator.
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
        # Also remove from chains and metadata
        self._metadata.pop(name, None)
        for chain_name in list(self._chains.keys()):
            self._chains[chain_name] = [p for p in self._chains[chain_name] if p != name]
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

    def get_metadata(self, name: str) -> dict[str, Any]:
        """Get metadata for a policy.

        Args:
            name: The name of the policy.

        Returns:
            Metadata dictionary for the policy.
        """
        return self._metadata.get(name, {})

    def clear(self) -> None:
        """Clear all registered policies and chains."""
        self._policies.clear()
        self._chains.clear()
        self._metadata.clear()


class PolicyEvaluator:
    """Evaluator for policy chains.

    The evaluator handles the execution of policy chains and makes
    decisions based on enforcement modes. It works with a PolicyRegistry
    to access registered policies and chains.
    """

    def __init__(self, registry: PolicyRegistry) -> None:
        """Initialize the policy evaluator.

        Args:
            registry: The policy registry to use for evaluation.
        """
        self._registry = registry

    async def evaluate_chain(
        self,
        chain_name: str,
        content: str,
        context: dict | None = None,
        mode: EnforcementMode = EnforcementMode.BLOCK,
    ) -> list[PolicyResult]:
        """Evaluate all policies in a chain.

        Evaluation stops early if a high-confidence violation is found
        (only in BLOCK mode).

        Args:
            chain_name: Name of the policy chain to evaluate.
            content: The content to evaluate.
            context: Optional context for evaluation.
            mode: The enforcement mode to use.

        Returns:
            List of PolicyResult objects from evaluated policies.
        """
        context = context or {}
        chain = self._registry.get_chain(chain_name)
        if not chain:
            return []

        results: list[PolicyResult] = []

        for policy_name in chain:
            policy = self._registry.get(policy_name)
            if policy is None:
                continue

            result = await policy.evaluate(content, context)
            result.policy_name = policy_name
            result.mode = mode.value
            results.append(result)

            # Early exit for block mode on high-confidence violations
            if mode == EnforcementMode.BLOCK and result.is_block():
                break

        return results

    async def make_decision(
        self,
        chain_name: str,
        content: str,
        context: dict | None = None,
        mode: EnforcementMode = EnforcementMode.BLOCK,
    ) -> PolicyDecision:
        """Make a policy decision by evaluating a chain.

        Args:
            chain_name: Name of the policy chain to evaluate.
            content: The content to evaluate.
            context: Optional context for evaluation.
            mode: The enforcement mode to use.

        Returns:
            PolicyDecision with the final action to take.
        """
        results = await self.evaluate_chain(chain_name, content, context, mode)

        for result in results:
            if mode == EnforcementMode.BLOCK:
                if result.is_block():
                    return PolicyDecision(
                        action=PolicyAction.BLOCK,
                        reason=result.reason,
                        policy_name=result.policy_name,
                    )
            elif mode == EnforcementMode.DETECT:
                if not result.allowed:
                    return PolicyDecision(
                        action=PolicyAction.WARN,
                        reason=f"[DETECTED] {result.reason}",
                        policy_name=result.policy_name,
                    )
            elif mode == EnforcementMode.MODIFY:
                if not result.allowed:
                    # Apply modifications
                    policy = self._registry.get(result.policy_name)
                    if policy and hasattr(policy, "modify_content"):
                        modified = policy.modify_content(content)
                        return PolicyDecision(
                            action=PolicyAction.MODIFY,
                            reason=f"[MODIFIED] {result.reason}",
                            modified_content=modified,
                            policy_name=result.policy_name,
                        )

        return PolicyDecision(action=PolicyAction.ALLOW, reason="All policies passed")
