"""Decorator utilities for policy application and trust management."""

import asyncio
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from model_governance.pipelines.base import PipelineResult
from model_governance.policies.registry import PolicyRegistry
from model_governance.trust.levels import TrustLevel

P = ParamSpec("P")
R = TypeVar("R")


def apply_policies(registry: PolicyRegistry, chain_name: str):
    """Decorator to apply policy chain to async function.

    Args:
        registry: The policy registry to use.
        chain_name: Name of the policy chain to apply.

    Returns:
        Decorator function.

    Example:
        ```python
        registry = PolicyRegistry()
        registry.create_chain("input_validation", ["injection", "malicious"])

        @apply_policies(registry, "input_validation")
        async def process_user_input(content: str, context: dict) -> str:
            return f"Processed: {content}"
        ```
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Extract content and context
            content = kwargs.get("content", args[0] if args else "")
            context = kwargs.get("context", {})

            # Evaluate policies
            decision = await registry.make_decision(chain_name, str(content), context)

            if decision.action.value == "block":
                from model_governance.core.exceptions import PolicyViolationError

                raise PolicyViolationError(decision.reason, policy_name=decision.policy_name)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_trust_level(required_level: TrustLevel):
    """Decorator to enforce trust level requirements.

    Args:
        required_level: Minimum trust level required.

    Returns:
        Decorator function.

    Example:
        ```python
        @with_trust_level(TrustLevel.HIGH)
        async def sensitive_operation(content: str, trust_level: TrustLevel) -> str:
            return f"Processed with HIGH trust: {content}"
        ```
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Get trust level from kwargs or args
            trust_level = kwargs.get("trust_level")

            if trust_level is None:
                from model_governance.core.exceptions import TrustLevelError

                raise TrustLevelError("Trust level not provided")

            # Parse if string
            if isinstance(trust_level, str):
                trust_level = TrustLevel[trust_level.upper()]

            if not trust_level.can_access(required_level):
                from model_governance.core.exceptions import TrustLevelError

                raise TrustLevelError(
                    f"Requires {required_level.name} trust level, got {trust_level.name}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def async_pipeline(func: Callable[P, Any]) -> Callable[P, Any]:
    """Decorator for async pipeline functions with error handling.

    Args:
        func: The async function to decorate.

    Returns:
        Decorated function with error handling.

    Example:
        ```python
        @async_pipeline
        async def my_pipeline(content: str) -> PipelineResult:
            # Processing logic here
            return PipelineResult(success=True, data=content)
        ```
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> PipelineResult:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return PipelineResult(
                success=False,
                errors=[str(e)],
                blocked=True,
                block_reason=f"Pipeline error: {type(e).__name__}",
            )

    return wrapper


def timed(timeout: float):
    """Decorator to add timeout to async functions.

    Args:
        timeout: Timeout in seconds.

    Returns:
        Decorator function.

    Example:
        ```python
        @timed(5.0)
        async def slow_operation() -> str:
            await asyncio.sleep(10)  # Will timeout
            return "Done"
        ```
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                from model_governance.core.exceptions import GovernanceError

                raise GovernanceError(f"Operation timed out after {timeout} seconds")

        return wrapper

    return decorator


def logged(func: Callable[P, Any]) -> Callable[P, Any]:
    """Decorator to log function calls and results.

    Args:
        func: The function to decorate.

    Returns:
        Decorated function with logging.

    Example:
        ```python
        @logged
        async def process_data(data: str) -> str:
            return data.upper()
        ```
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        import logging

        logger = logging.getLogger(func.__module__)

        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")

        try:
            result = await func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised: {e}")
            raise

    return wrapper
