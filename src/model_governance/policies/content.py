"""Content-specific policies for HTML and JSON blocking."""

import json
import re
from typing import Any

from model_governance.policies.base import Policy, PolicyResult


class HTMLBlockingPolicy(Policy):
    """Policy to block HTML content in outputs.

    Helps prevent XSS and other HTML injection attacks.
    """

    def __init__(self, priority: int = 100, block_all: bool = True, allowed_tags: set[str] | None = None) -> None:
        """Initialize the HTML blocking policy.

        Args:
            priority: Policy priority.
            block_all: If True, block all HTML. If False, only allow allowed_tags.
            allowed_tags: Set of HTML tags to allow (if block_all is False).
        """
        self._priority = priority
        self._block_all = block_all
        self._allowed_tags = allowed_tags or set()

        self._html_pattern = re.compile(r"<[^>]+>")
        self._tag_pattern = re.compile(r"<(\w+)")

    @property
    def name(self) -> str:
        """Policy name."""
        return "html_blocking"

    @property
    def priority(self) -> int:
        """Policy priority."""
        return self._priority

    async def evaluate(self, content: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate content for HTML.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        if not self._html_pattern.search(content):
            return PolicyResult(allowed=True, reason="No HTML detected")

        if self._block_all:
            return PolicyResult(
                allowed=False, reason="HTML content is not allowed", confidence=1.0
            )

        tags_found = self._tag_pattern.findall(content)
        disallowed_tags = [tag for tag in tags_found if tag.lower() not in self._allowed_tags]

        if disallowed_tags:
            return PolicyResult(
                allowed=False,
                reason=f"HTML contains disallowed tags: {', '.join(set(disallowed_tags))}",
                confidence=1.0,
            )

        return PolicyResult(allowed=True, reason="HTML contains only allowed tags")

    def modify_content(self, content: str) -> str:
        """Remove HTML tags from content.

        Args:
            content: The content to modify.

        Returns:
            Content with HTML tags removed.
        """
        # Remove all HTML tags
        cleaned = self._html_pattern.sub("", content)
        return cleaned.strip()


class JSONBlockingPolicy(Policy):
    """Policy to block JSON content in outputs.

    Useful when structured output is not desired or to prevent
    data leakage through JSON format.
    """

    def __init__(self, priority: int = 90) -> None:
        """Initialize the JSON blocking policy.

        Args:
            priority: Policy priority.
        """
        self._priority = priority

    @property
    def name(self) -> str:
        """Policy name."""
        return "json_blocking"

    @property
    def priority(self) -> int:
        """Policy priority."""
        return self._priority

    async def evaluate(self, content: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate content for JSON.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        content_stripped = content.strip()

        if not content_stripped.startswith(("{", "[")):
            return PolicyResult(allowed=True, reason="No JSON detected")

        try:
            json.loads(content_stripped)
            return PolicyResult(
                allowed=False, reason="JSON content is not allowed", confidence=1.0
            )
        except json.JSONDecodeError:
            return PolicyResult(allowed=True, reason="Not valid JSON")

    def modify_content(self, content: str) -> str:
        """Escape JSON braces to prevent them from being recognized.

        Args:
            content: The content to modify.

        Returns:
            Content with JSON braces escaped.
        """
        return content.replace("{", "{{").replace("}", "}}")


class CodeBlockPolicy(Policy):
    """Policy to block or allow code blocks in content.

    Can be used to prevent code injection or to enforce
    specific code language restrictions.
    """

    def __init__(
        self,
        priority: int = 80,
        block_all: bool = False,
        allowed_languages: set[str] | None = None,
        blocked_languages: set[str] | None = None,
    ) -> None:
        """Initialize the code block policy.

        Args:
            priority: Policy priority.
            block_all: If True, block all code blocks.
            allowed_languages: Set of allowed code languages (e.g., {'python', 'javascript'}).
            blocked_languages: Set of blocked code languages.
        """
        self._priority = priority
        self._block_all = block_all
        self._allowed_languages = {lang.lower() for lang in (allowed_languages or set())}
        self._blocked_languages = {lang.lower() for lang in (blocked_languages or set())}

        self._code_block_pattern = re.compile(r"```(\w*)\n([\s\S]*?)```")

    @property
    def name(self) -> str:
        """Policy name."""
        return "code_block"

    @property
    def priority(self) -> int:
        """Policy priority."""
        return self._priority

    async def evaluate(self, content: str, context: dict[str, Any]) -> PolicyResult:
        """Evaluate content for code blocks.

        Args:
            content: The content to evaluate.
            context: Additional context for evaluation.

        Returns:
            PolicyResult with the evaluation outcome.
        """
        matches = self._code_block_pattern.findall(content)

        if not matches:
            return PolicyResult(allowed=True, reason="No code blocks detected")

        if self._block_all:
            return PolicyResult(
                allowed=False, reason="Code blocks are not allowed", confidence=1.0
            )

        for lang, _ in matches:
            lang_lower = lang.lower()

            if lang_lower in self._blocked_languages:
                return PolicyResult(
                    allowed=False,
                    reason=f"Code blocks in language '{lang}' are not allowed",
                    confidence=1.0,
                )

            if self._allowed_languages and lang_lower and lang_lower not in self._allowed_languages:
                return PolicyResult(
                    allowed=False,
                    reason=f"Only code blocks in {', '.join(self._allowed_languages)} are allowed",
                    confidence=1.0,
                )

        return PolicyResult(allowed=True, reason="Code blocks comply with policy")

    def modify_content(self, content: str) -> str:
        """Remove code blocks from content.

        Args:
            content: The content to modify.

        Returns:
            Content with code blocks removed.
        """
        # Remove code blocks
        cleaned = self._code_block_pattern.sub("[CODE REMOVED]", content)
        return cleaned
