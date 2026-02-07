"""LLM-based safety check pipeline for output validation."""

from typing import Protocol, runtime_checkable

from model_governance.pipelines.base import OutputPipeline, PipelineResult


@runtime_checkable
class LLMChecker(Protocol):
    """Protocol for LLM-based safety checkers.

    LLM checkers use an LLM to analyze content for safety issues.
    """

    async def check(self, content: str, context: dict) -> tuple[bool, str, float]:
        """Check content for safety using LLM analysis.

        Args:
            content: The content to check.
            context: Additional context for the check.

        Returns:
            A tuple of (is_safe, reason, confidence).
        """
        ...


class MockLLMChecker:
    """Mock LLM checker for testing.

    A production implementation would use the zai-sdk moderations API.
    """

    def __init__(self) -> None:
        """Initialize the mock LLM checker."""
        self._harmful_patterns = [
            "self harm",
            "suicide",
            "hate speech",
            "kill",
            "threat",
            "violence",
        ]

    async def check(self, content: str, context: dict) -> tuple[bool, str, float]:
        """Check content using pattern-based LLM simulation.

        Args:
            content: The content to check.
            context: Additional context.

        Returns:
            Tuple of (is_safe, reason, confidence).
        """
        content_lower = content.lower()

        for pattern in self._harmful_patterns:
            if pattern in content_lower:
                return False, f"LLM detected harmful content: {pattern}", 0.85

        return True, "LLM check passed: no harmful content detected", 1.0


class LLMCheckPipeline(OutputPipeline):
    """LLM-based safety check pipeline.

    Uses an LLM to analyze content for safety issues.
    """

    def __init__(
        self,
        checker: LLMChecker | None = None,
        threshold: float = 0.7,
    ) -> None:
        """Initialize the LLM check pipeline.

        Args:
            checker: Optional LLM checker. Uses default if not provided.
            threshold: Confidence threshold for blocking.
        """
        super().__init__()
        self._checker = checker or MockLLMChecker()
        self._threshold = threshold

    async def process(self, input_data: str) -> PipelineResult:
        """Process output through LLM safety check.

        Args:
            input_data: The output to check.

        Returns:
            PipelineResult with safety check results.
        """
        is_safe, reason, confidence = await self._checker.check(input_data, {})

        if not is_safe and confidence >= self._threshold:
            return PipelineResult(
                success=False,
                errors=[reason],
                blocked=True,
                block_reason=reason,
                metadata={"method": "llm", "confidence": confidence, "threshold": self._threshold},
            )

        return await self._next_process(input_data)
