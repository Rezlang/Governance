"""Composite output pipeline combining multiple safety checks."""

import asyncio
from typing import Protocol, runtime_checkable

from model_governance.pipelines.base import OutputPipeline, PipelineResult
from model_governance.pipelines.output.llm_check import LLMChecker
from model_governance.pipelines.output.semantic_check import SemanticChecker


@runtime_checkable
class SafetyChecker(Protocol):
    """Protocol for any safety checker."""

    async def check(self, content: str, context: dict) -> tuple[bool, str, float]:
        """Check content for safety.

        Returns:
            Tuple of (is_safe, reason, confidence).
        """
        ...


class CompositeOutputPipeline(OutputPipeline):
    """Composite output pipeline combining multiple safety checks.

    Can run semantic and LLM checks in parallel or sequentially,
    with configurable blocking logic.
    """

    def __init__(
        self,
        semantic_checker: SemanticChecker | None = None,
        llm_checker: LLMChecker | None = None,
        enable_parallel: bool = True,
        block_on_any: bool = True,
        combined_threshold: float = 0.7,
    ) -> None:
        """Initialize the composite output pipeline.

        Args:
            semantic_checker: Optional semantic checker.
            llm_checker: Optional LLM checker.
            enable_parallel: Whether to run checks in parallel.
            block_on_any: If True, block if any check fails.
                          If False, block only if all checks fail.
            combined_threshold: Combined confidence threshold for blocking.
        """
        super().__init__()
        self._semantic_checker = semantic_checker
        self._llm_checker = llm_checker
        self._enable_parallel = enable_parallel
        self._block_on_any = block_on_any
        self._combined_threshold = combined_threshold

    async def _run_semantic_check(self, content: str) -> tuple[bool, list[str], float]:
        """Run semantic check.

        Args:
            content: The content to check.

        Returns:
            Tuple of (is_safe, issues, confidence).
        """
        if self._semantic_checker is None:
            return True, [], 1.0

        is_safe, issues = await self._semantic_checker.check(content, {})
        confidence = 0.0 if not is_safe else 1.0
        return is_safe, issues, confidence

    async def _run_llm_check(self, content: str) -> tuple[bool, str, float]:
        """Run LLM check.

        Args:
            content: The content to check.

        Returns:
            Tuple of (is_safe, reason, confidence).
        """
        if self._llm_checker is None:
            return True, "LLM check not enabled", 1.0

        return await self._llm_checker.check(content, {})

    async def process(self, input_data: str) -> PipelineResult:
        """Process output through all safety checks.

        Args:
            input_data: The output to check.

        Returns:
            PipelineResult with aggregated safety check results.
        """
        all_errors: list[str] = []
        all_metadata: dict[str, object] = {}

        if self._enable_parallel and self._semantic_checker and self._llm_checker:
            semantic_result, llm_result = await asyncio.gather(
                self._run_semantic_check(input_data),
                self._run_llm_check(input_data),
            )

            semantic_safe, semantic_issues, semantic_conf = semantic_result
            llm_safe, llm_reason, llm_conf = llm_result

            all_metadata["semantic"] = {"safe": semantic_safe, "confidence": semantic_conf}
            all_metadata["llm"] = {"safe": llm_safe, "confidence": llm_conf}

            if not semantic_safe:
                all_errors.extend(semantic_issues)

            if not llm_safe:
                all_errors.append(llm_reason)

            should_block = self._should_block(semantic_safe, llm_safe, semantic_conf, llm_conf)

            if should_block and all_errors:
                return PipelineResult(
                    success=False,
                    errors=all_errors,
                    blocked=True,
                    block_reason=f"Safety check failed: {'; '.join(all_errors[:3])}",
                    metadata=all_metadata,
                )

        else:
            if self._semantic_checker:
                is_safe, issues, conf = await self._run_semantic_check(input_data)
                all_metadata["semantic"] = {"safe": is_safe, "confidence": conf}

                if not is_safe:
                    all_errors.extend(issues)
                    if self._block_on_any:
                        return PipelineResult(
                            success=False,
                            errors=issues,
                            blocked=True,
                            block_reason=f"Semantic check failed: {issues[0]}",
                            metadata=all_metadata,
                        )

            if self._llm_checker:
                is_safe, reason, conf = await self._run_llm_check(input_data)
                all_metadata["llm"] = {"safe": is_safe, "confidence": conf}

                if not is_safe:
                    all_errors.append(reason)
                    if self._block_on_any:
                        return PipelineResult(
                            success=False,
                            errors=[reason],
                            blocked=True,
                            block_reason=reason,
                            metadata=all_metadata,
                        )

        return await self._next_process(input_data)

    def _should_block(
        self, semantic_safe: bool, llm_safe: bool, semantic_conf: float, llm_conf: float
    ) -> bool:
        """Determine if content should be blocked.

        Args:
            semantic_safe: Whether semantic check passed.
            llm_safe: Whether LLM check passed.
            semantic_conf: Semantic check confidence.
            llm_conf: LLM check confidence.

        Returns:
            True if content should be blocked.
        """
        if self._block_on_any:
            return not semantic_safe or not llm_safe
        else:
            avg_confidence = (semantic_conf + llm_conf) / 2
            return avg_confidence < self._combined_threshold
