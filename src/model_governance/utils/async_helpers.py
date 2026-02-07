"""Async helper functions for pipeline execution and error handling."""

import asyncio
from typing import Any, TypeVar

from model_governance.pipelines.base import InputPipeline, PipelineResult

T = TypeVar("T")


async def run_parallel_pipelines(
    *pipelines: InputPipeline, input_data: str
) -> list[PipelineResult]:
    """Run multiple pipelines in parallel.

    Args:
        *pipelines: Variable number of pipelines to run.
        input_data: Input data to pass to all pipelines.

    Returns:
        List of PipelineResult objects from each pipeline.

    Example:
        ```python
        results = await run_parallel_pipelines(
            user_pipeline,
            tool_pipeline,
            input_data="Hello"
        )
        ```
    """
    tasks = [pipeline.process(input_data) for pipeline in pipelines]

    results: list[PipelineResult] = []
    for task in asyncio.as_completed(tasks):
        result = await task
        results.append(result)

    return results


async def run_with_timeout(coro: Any, timeout: float, default: Any = None) -> Any:
    """Run a coroutine with a timeout, returning default on timeout.

    Args:
        coro: The coroutine to run.
        timeout: Timeout in seconds.
        default: Default value to return on timeout.

    Returns:
        Result of the coroutine or default value on timeout.

    Example:
        ```python
        result = await run_with_timeout(
            slow_check(content),
            timeout=5.0,
            default={"safe": True, "reason": "Timeout - allowing"}
        )
        ```
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default


async def retry_with_backoff(
    func: Any,
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Any:
    """Retry a function with exponential backoff.

    Args:
        func: The async function to retry.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries.
        max_delay: Maximum delay between retries.
        backoff_factor: Multiplier for delay after each retry.

    Returns:
        Result of the function call.

    Raises:
        Exception: The last exception if all retries fail.

    Example:
        ```python
        result = await retry_with_backoff(
            api_client.check_content(content),
            max_retries=5
        )
        ```
    """
    last_exception = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            if attempt < max_retries:
                await asyncio.sleep(min(delay, max_delay))
                delay *= backoff_factor

    raise last_exception


async def gather_with_errors(*coros: Any, return_exceptions: bool = False) -> list[Any]:
    """Gather coroutines with optional error handling.

    Args:
        *coros: Variable number of coroutines to run.
        return_exceptions: If True, return exceptions instead of raising.

    Returns:
        List of results or exceptions.

    Example:
        ```python
        results = await gather_with_errors(
            check1(content),
            check2(content),
            return_exceptions=True
        )
        ```
    """
    return await asyncio.gather(*coros, return_exceptions=return_exceptions)


async def run_sequential(*coros: Any) -> list[Any]:
    """Run coroutines sequentially, stopping on first error.

    Args:
        *coros: Variable number of coroutines to run in sequence.

    Returns:
        List of results from all completed coroutines.

    Raises:
        Exception: The first exception encountered.

    Example:
        ```python
        results = await run_sequential(
            validate_input(content),
            check_policies(content),
            process_output(content)
        )
        ```
    """
    results: list[Any] = []

    for coro in coros:
        result = await coro
        results.append(result)

    return results


async def run_first_successful(*coros: Any) -> Any:
    """Run coroutines and return the first successful result.

    Args:
        *coros: Variable number of coroutines to run.

    Returns:
        Result of the first successful coroutine.

    Raises:
        Exception: If all coroutines fail.

    Example:
        ```python
        result = await run_first_successful(
            primary_check(content),
            fallback_check(content),
            last_resort_check(content)
        )
        ```
    """
    exceptions: list[Exception] = []

    for coro in coros:
        try:
            return await coro
        except Exception as e:
            exceptions.append(e)

    if exceptions:
        raise exceptions[-1]

    raise RuntimeError("No coroutines provided")


class AsyncSemaphore:
    """Context manager for limiting concurrent async operations."""

    def __init__(self, limit: int) -> None:
        """Initialize the semaphore.

        Args:
            limit: Maximum number of concurrent operations.
        """
        self._semaphore = asyncio.Semaphore(limit)

    async def __aenter__(self) -> "AsyncSemaphore":
        """Enter the context."""
        await self._semaphore.acquire()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit the context."""
        self._semaphore.release()


async def run_with_semaphore(limit: int, *coros: Any) -> list[Any]:
    """Run coroutines with a semaphore limiting concurrency.

    Args:
        limit: Maximum concurrent operations.
        *coros: Variable number of coroutines to run.

    Returns:
        List of results.

    Example:
        ```python
        results = await run_with_semaphore(
            5,  # Max 5 concurrent
            *[check_item(item) for item in items]
        )
        ```
    """
    async def bounded(coro: Any) -> Any:
        async with AsyncSemaphore(limit):
            return await coro

    return await gather_with_errors(*(bounded(c) for c in coros))
