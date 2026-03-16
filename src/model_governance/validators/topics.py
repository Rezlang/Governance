"""Topic guards for harmful content detection."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from model_governance.core.patterns import SecurityPatterns


@dataclass
class TopicGuardResult:
    """Result from a topic guard check.

    Attributes:
        is_safe: Whether the content is safe regarding this topic.
        confidence: Confidence score (0.0 to 1.0).
        reason: Human-readable explanation.
        detected_phrases: List of phrases that triggered the guard.
        method: Which detection method was used ('semantic', 'llm', 'pattern').
    """

    is_safe: bool
    confidence: float
    reason: str
    detected_phrases: list[str] | None = None
    method: str = "pattern"


class TopicGuard(ABC):
    """Base class for topic-based guards.

    Topic guards detect content related to specific harmful topics
    such as self-harm, hate speech, threats, etc.
    """

    def __init__(
        self,
        name: str,
        patterns: list[str] | None = None,
        threshold: float = 0.7,
    ) -> None:
        """Initialize the topic guard.

        Args:
            name: Name of the guard (e.g., 'self_harm').
            patterns: List of trigger phrases/patterns for this topic.
            threshold: Confidence threshold for blocking.
        """
        self.name = name
        self._patterns = patterns or []
        self._threshold = threshold

    @abstractmethod
    async def check(self, content: str, context: dict[str, Any] | None = None) -> TopicGuardResult:
        """Check content for this topic.

        Args:
            content: The content to check.
            context: Optional additional context.

        Returns:
            TopicGuardResult with the check outcome.
        """
        pass

    def _check_patterns(self, content: str) -> tuple[bool, list[str]]:
        """Check for pattern matches in content.

        Args:
            content: The content to check.

        Returns:
            Tuple of (has_match, matched_phrases).
        """
        content_lower = content.lower()
        matched = []

        for pattern in self._patterns:
            if pattern.lower() in content_lower:
                matched.append(pattern)

        return len(matched) > 0, matched


class SelfHarmGuard(TopicGuard):
    """Guard for self-harm related content."""

    def __init__(self, threshold: float = 0.7, patterns: list[str] | None = None) -> None:
        """Initialize the self-harm guard.

        Args:
            threshold: Confidence threshold for blocking.
            patterns: Custom patterns, or defaults if not provided.
        """
        default_patterns = SecurityPatterns.get_self_harm_patterns()
        super().__init__(name="self_harm", patterns=patterns or default_patterns, threshold=threshold)

    async def check(self, content: str, context: dict[str, Any] | None = None) -> TopicGuardResult:
        """Check content for self-harm related content.

        Args:
            content: The content to check.
            context: Optional additional context.

        Returns:
            TopicGuardResult with the check outcome.
        """
        has_match, matched = self._check_patterns(content)

        if has_match:
            return TopicGuardResult(
                is_safe=False,
                confidence=0.9,
                reason=f"Self-harm related content detected: {', '.join(matched[:3])}",
                detected_phrases=matched,
                method="pattern",
            )

        return TopicGuardResult(
            is_safe=True,
            confidence=1.0,
            reason="No self-harm content detected",
            method="pattern",
        )


class HateSpeechGuard(TopicGuard):
    """Guard for hate speech content."""

    def __init__(self, threshold: float = 0.7, patterns: list[str] | None = None) -> None:
        """Initialize the hate speech guard.

        Args:
            threshold: Confidence threshold for blocking.
            patterns: Custom patterns, or defaults if not provided.
        """
        default_patterns = SecurityPatterns.get_hate_speech_patterns()
        super().__init__(name="hate_speech", patterns=patterns or default_patterns, threshold=threshold)

    async def check(self, content: str, context: dict[str, Any] | None = None) -> TopicGuardResult:
        """Check content for hate speech.

        Args:
            content: The content to check.
            context: Optional additional context.

        Returns:
            TopicGuardResult with the check outcome.
        """
        has_match, matched = self._check_patterns(content)

        if has_match:
            return TopicGuardResult(
                is_safe=False,
                confidence=0.85,
                reason=f"Hate speech indicators detected: {', '.join(matched[:3])}",
                detected_phrases=matched,
                method="pattern",
            )

        return TopicGuardResult(
            is_safe=True,
            confidence=1.0,
            reason="No hate speech detected",
            method="pattern",
        )


class ThreatsGuard(TopicGuard):
    """Guard for threats and violent content."""

    def __init__(self, threshold: float = 0.7, patterns: list[str] | None = None) -> None:
        """Initialize the threats guard.

        Args:
            threshold: Confidence threshold for blocking.
            patterns: Custom patterns, or defaults if not provided.
        """
        default_patterns = SecurityPatterns.get_threats_patterns()
        super().__init__(name="threats", patterns=patterns or default_patterns, threshold=threshold)

    async def check(self, content: str, context: dict[str, Any] | None = None) -> TopicGuardResult:
        """Check content for threats and violent content.

        Args:
            content: The content to check.
            context: Optional additional context.

        Returns:
            TopicGuardResult with the check outcome.
        """
        has_match, matched = self._check_patterns(content)

        if has_match:
            return TopicGuardResult(
                is_safe=False,
                confidence=0.9,
                reason=f"Threat or violence indicators detected: {', '.join(matched[:3])}",
                detected_phrases=matched,
                method="pattern",
            )

        return TopicGuardResult(
            is_safe=True,
            confidence=1.0,
            reason="No threats detected",
            method="pattern",
        )


class SexualContentGuard(TopicGuard):
    """Guard for sexually explicit content."""

    def __init__(self, threshold: float = 0.7, patterns: list[str] | None = None) -> None:
        """Initialize the sexual content guard.

        Args:
            threshold: Confidence threshold for blocking.
            patterns: Custom patterns, or defaults if not provided.
        """
        default_patterns = SecurityPatterns.get_sexual_content_patterns()
        super().__init__(
            name="sexual_content", patterns=patterns or default_patterns, threshold=threshold
        )

    async def check(self, content: str, context: dict[str, Any] | None = None) -> TopicGuardResult:
        """Check content for sexual content.

        Args:
            content: The content to check.
            context: Optional additional context.

        Returns:
            TopicGuardResult with the check outcome.
        """
        has_match, matched = self._check_patterns(content)

        if has_match:
            return TopicGuardResult(
                is_safe=False,
                confidence=0.8,
                reason=f"Sexual content indicators detected: {', '.join(matched[:3])}",
                detected_phrases=matched,
                method="pattern",
            )

        return TopicGuardResult(
            is_safe=True,
            confidence=1.0,
            reason="No sexual content detected",
            method="pattern",
        )
