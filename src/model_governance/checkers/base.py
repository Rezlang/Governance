"""Base classes and result types for content checkers."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckerResult:
    """Standard result for content checker evaluations.

    Checkers perform content analysis (e.g., semantic similarity, LLM evaluation)
    and return consistent results across different implementations.

    Attributes:
        is_safe: Whether the content passed the safety check.
        issues: List of issues found (empty if safe).
        confidence: Overall confidence score (0.0 to 1.0).
        metadata: Additional metadata about the check.
        checker_name: Name of the checker that produced this result.
    """

    is_safe: bool
    issues: list[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    checker_name: str | None = None

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def add_issue(self, issue: str) -> None:
        """Add an issue to the result.

        Args:
            issue: The issue description to add.
        """
        self.issues.append(issue)
        if self.is_safe:
            self.is_safe = False

    @classmethod
    def safe(cls, confidence: float = 1.0, metadata: dict[str, Any] | None = None) -> "CheckerResult":
        """Create a safe result.

        Args:
            confidence: Confidence score for the safe result.
            metadata: Optional metadata.

        Returns:
            A CheckerResult indicating the content is safe.
        """
        return cls(is_safe=True, issues=[], confidence=confidence, metadata=metadata or {})

    @classmethod
    def unsafe(
        cls,
        issues: list[str] | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> "CheckerResult":
        """Create an unsafe result.

        Args:
            issues: List of issues found.
            confidence: Confidence score for the unsafe result.
            metadata: Optional metadata.

        Returns:
            A CheckerResult indicating the content is unsafe.
        """
        return cls(is_safe=False, issues=issues or [], confidence=confidence, metadata=metadata or {})
