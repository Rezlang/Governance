"""Content blocking policies for pattern-based filtering."""

import re
from typing import Any

from model_governance.core.patterns import SecurityPatterns
from model_governance.policies.base import Policy, PolicyResult


class ContentBlockingPolicy(Policy):
    """Policy that blocks content based on pattern matching.

    Patterns can be simple strings or regular expressions.
    """

    def __init__(
        self,
        name: str,
        patterns: list[str] | str,
        priority: int = 100,
        case_sensitive: bool = False,
        use_regex: bool = False,
        block_message: str | None = None,
    ) -> None:
        """Initialize the content blocking policy.

        Args:
            name: Unique policy name.
            patterns: Pattern(s) to block. Can be a list or single pattern.
            priority: Policy priority (higher runs first).
            case_sensitive: Whether matching is case sensitive.
            use_regex: Whether to treat patterns as regular expressions.
            block_message: Custom message for blocked content.
        """
        self._name = name
        self._priority = priority
        self._case_sensitive = case_sensitive
        self._use_regex = use_regex
        self._block_message = block_message or f"Blocked by {name}"

        if isinstance(patterns, str):
            patterns = [patterns]

        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            self._patterns = [re.compile(p, flags) for p in patterns]
        else:
            self._patterns = patterns

    @property
    def name(self) -> str:
        """Policy name."""
        return self._name

    @property
    def priority(self) -> int:
        """Policy priority."""
        return self._priority

    async def evaluate(self, content: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate content against blocking patterns.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        check_content = content if self._case_sensitive else content.lower()

        if self._use_regex:
            for pattern in self._patterns:
                if pattern.search(content):
                    return PolicyResult(
                        allowed=False,
                        reason=f"{self._block_message}: matched pattern '{pattern.pattern}'",
                        confidence=1.0,
                    )
        else:
            for pattern in self._patterns:
                check_pattern = pattern if self._case_sensitive else pattern.lower()
                if check_pattern in check_content:
                    return PolicyResult(
                        allowed=False,
                        reason=f"{self._block_message}: matched pattern '{pattern}'",
                        confidence=1.0,
                    )

        return PolicyResult(allowed=True, reason="No blocked patterns found")

    def modify_content(self, content: str) -> str:
        """Remove blocked patterns from content.

        Args:
            content: The content to modify.

        Returns:
            Content with blocked patterns removed or replaced.
        """
        modified = content
        if self._use_regex:
            for pattern in self._patterns:
                # Remove matched patterns
                modified = pattern.sub("[REMOVED]", modified)
        else:
            for pattern in self._patterns:
                # Case-insensitive replacement
                if not self._case_sensitive:
                    pattern_lower = pattern.lower()
                    # Find all occurrences and replace them
                    while pattern_lower in modified.lower():
                        idx = modified.lower().find(pattern_lower)
                        if idx != -1:
                            modified = modified[:idx] + "[REMOVED]" + modified[idx + len(pattern):]
                else:
                    modified = modified.replace(pattern, "[REMOVED]")
        return modified


class PromptInjectionPolicy(ContentBlockingPolicy):
    """Policy to detect and block prompt injection attempts."""

    def __init__(self, priority: int = 100, patterns: list[str] | None = None) -> None:
        """Initialize the prompt injection policy.

        Args:
            priority: Policy priority.
            patterns: Custom patterns to use, or defaults if not provided.
        """
        default_patterns = SecurityPatterns.get_injection_patterns()
        super().__init__(
            name="prompt_injection",
            patterns=patterns or default_patterns,
            priority=priority,
            case_sensitive=False,
        )


class MaliciousCodePolicy(ContentBlockingPolicy):
    """Policy to detect potentially malicious code patterns."""

    def __init__(self, priority: int = 90, patterns: list[str] | None = None) -> None:
        """Initialize the malicious code policy.

        Args:
            priority: Policy priority.
            patterns: Custom patterns to use, or defaults if not provided.
        """
        default_patterns = SecurityPatterns.get_code_execution_patterns()
        super().__init__(
            name="malicious_code",
            patterns=patterns or default_patterns,
            priority=priority,
            case_sensitive=False,
        )
