"""Security validators for input content."""

import re
from typing import Any


# Prompt injection patterns
INJECTION_PATTERNS = [
    "ignore previous",
    "disregard above",
    "override instructions",
    "forget everything",
    "new instructions:",
    "ignore your programming",
    "disregard your training",
    "<end>",
    "<|end|>",
    "[DONE]",
    "\\begin{system}",
    "act as",
    "pretend to be",
    "roleplay as",
]

# Code execution patterns
CODE_EXECUTION_PATTERNS = [
    "eval(",
    "exec(",
    "compile(",
    "__import__",
    "os.system",
    "subprocess",
    "pickle.loads",
    "marshal.loads",
]


def validate_no_injection(content: str, patterns: list[str] | None = None) -> dict[str, Any]:
    """Validate content doesn't contain prompt injection patterns.

    Args:
        content: The content to validate.
        patterns: Optional custom patterns to check. Uses defaults if not provided.

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys.
    """
    check_patterns = patterns or INJECTION_PATTERNS
    content_lower = content.lower()

    for pattern in check_patterns:
        if pattern.lower() in content_lower:
            return {
                "valid": False,
                "reason": f"Potential injection detected: '{pattern}'",
                "pattern": pattern,
            }

    return {"valid": True, "reason": "No injection patterns detected"}


def validate_no_code_execution(content: str, patterns: list[str] | None = None) -> dict[str, Any]:
    """Validate content doesn't contain code execution patterns.

    Args:
        content: The content to validate.
        patterns: Optional custom patterns to check. Uses defaults if not provided.

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys.
    """
    check_patterns = patterns or CODE_EXECUTION_PATTERNS
    content_lower = content.lower()

    for pattern in check_patterns:
        if pattern.lower() in content_lower:
            return {
                "valid": False,
                "reason": f"Code execution pattern detected: '{pattern}'",
                "pattern": pattern,
            }

    return {"valid": True, "reason": "No code execution patterns detected"}


def validate_length(content: str, max_length: int = 10000, min_length: int = 1) -> dict[str, Any]:
    """Validate content length is within bounds.

    Args:
        content: The content to validate.
        max_length: Maximum allowed length.
        min_length: Minimum allowed length.

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys.
    """
    length = len(content)

    if length < min_length:
        return {
            "valid": False,
            "reason": f"Content too short: {length} characters (minimum {min_length})",
            "length": length,
        }

    if length > max_length:
        return {
            "valid": False,
            "reason": f"Content too long: {length} characters (maximum {max_length})",
            "length": length,
        }

    return {
        "valid": True,
        "reason": f"Content length within bounds: {length}/{max_length}",
        "length": length,
    }


def validate_no_html(content: str) -> dict[str, Any]:
    """Validate content doesn't contain HTML tags.

    Args:
        content: The content to validate.

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys.
    """
    html_pattern = re.compile(r"<[^>]+>")

    if html_pattern.search(content):
        return {
            "valid": False,
            "reason": "HTML content detected",
        }

    return {"valid": True, "reason": "No HTML detected"}


def validate_url(content: str, allow_urls: bool = True) -> dict[str, Any]:
    """Validate content for URL presence.

    Args:
        content: The content to validate.
        allow_urls: Whether URLs are allowed in the content.

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys.
    """
    url_pattern = re.compile(r"https?://[^\s]+")

    urls = url_pattern.findall(content)

    if urls and not allow_urls:
        return {
            "valid": False,
            "reason": f"URLs detected but not allowed: {len(urls)} URL(s) found",
            "urls": urls,
        }

    return {
        "valid": True,
        "reason": f"URL validation passed: {len(urls)} URL(s) found" if allow_urls else "No URLs detected",
    }
