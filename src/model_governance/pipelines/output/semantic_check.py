"""Semantic-based safety check pipeline for output validation."""

from typing import Protocol, runtime_checkable

from model_governance.pipelines.base import OutputPipeline, PipelineResult
from model_governance.validators.topics import TopicGuard, TopicGuardResult


@runtime_checkable
class SemanticChecker(Protocol):
    """Protocol for semantic safety checkers.

    Semantic checkers use embeddings and similarity measures
    to detect harmful content.
    """

    async def check(self, content: str, context: dict) -> tuple[bool, list[str]]:
        """Check content for safety using semantic analysis.

        Args:
            content: The content to check.
            context: Additional context for the check.

        Returns:
            A tuple of (is_safe, list_of_issues).
        """
        ...


class PatternBasedSemanticChecker:
    """Pattern-based semantic checker implementation.

    This is a simple implementation that uses pattern matching.
    A production system would use embeddings from zai-sdk.
    """

    def __init__(self, guards: list[TopicGuard] | None = None) -> None:
        """Initialize the semantic checker.

        Args:
            guards: List of topic guards to use.
        """
        from model_governance.validators.topics import SelfHarmGuard, HateSpeechGuard, ThreatsGuard

        self._guards = guards or [
            SelfHarmGuard(),
            HateSpeechGuard(),
            ThreatsGuard(),
        ]

    async def check(self, content: str, context: dict | None = None) -> tuple[bool, list[str]]:
        """Check content using semantic guards.

        Args:
            content: The content to check.
            context: Additional context.

        Returns:
            Tuple of (is_safe, list_of_issues).
        """
        issues: list[str] = []
        context = context or {}

        for guard in self._guards:
            result = await guard.check(content, context)
            if not result.is_safe:
                issues.append(f"{guard.name}: {result.reason}")

        return len(issues) == 0, issues


class SemanticCheckPipeline(OutputPipeline):
    """Semantic-based safety check pipeline.

    Uses semantic analysis to detect harmful content in model outputs.
    """

    def __init__(
        self,
        checker: SemanticChecker | None = None,
        threshold: float = 0.8,
    ) -> None:
        """Initialize the semantic check pipeline.

        Args:
            checker: Optional semantic checker. Uses default if not provided.
            threshold: Similarity threshold for blocking.
        """
        super().__init__()
        self._checker = checker or PatternBasedSemanticChecker()
        self._threshold = threshold

    async def process(self, input_data: str) -> PipelineResult:
        """Process output through semantic safety check.

        Args:
            input_data: The output to check.

        Returns:
            PipelineResult with safety check results.
        """
        is_safe, issues = await self._checker.check(input_data, {})

        if not is_safe:
            return PipelineResult(
                success=False,
                errors=issues,
                blocked=True,
                block_reason=f"Semantic safety check failed: {'; '.join(issues)}",
                metadata={"method": "semantic", "threshold": self._threshold},
            )

        return await self._next_process(input_data)
