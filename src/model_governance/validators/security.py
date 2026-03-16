"""Security validators for input content."""

import re
from typing import Any

from model_governance.core.patterns import SecurityPatterns

# For backward compatibility, export from SecurityPatterns
INJECTION_PATTERNS = SecurityPatterns.INJECTION_PATTERNS
CODE_EXECUTION_PATTERNS = SecurityPatterns.CODE_EXECUTION_PATTERNS
SQL_INJECTION_PATTERNS = SecurityPatterns.SQL_INJECTION_PATTERNS


def validate_no_injection(content: str, patterns: list[str] | None = None) -> dict[str, Any]:
    """Validate content doesn't contain prompt injection patterns.

    Args:
        content: The content to validate.
        patterns: Optional custom patterns to check. Uses defaults if not provided.

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys.
    """
    check_patterns = patterns or SecurityPatterns.get_injection_patterns()
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
    check_patterns = patterns or SecurityPatterns.get_code_execution_patterns()
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


def validate_no_sql_injection(content: str, patterns: list[str] | None = None) -> dict[str, Any]:
    """Validate content doesn't contain SQL injection patterns.

    Args:
        content: The content to validate (typically SQL queries or parameters).
        patterns: Optional custom patterns to check. Uses defaults if not provided.

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys.
    """
    check_patterns = patterns or SecurityPatterns.get_sql_injection_patterns()
    content_lower = content.lower()

    for pattern in check_patterns:
        if pattern.lower() in content_lower:
            return {
                "valid": False,
                "reason": f"SQL injection pattern detected: '{pattern}'",
                "pattern": pattern,
            }

    return {"valid": True, "reason": "No SQL injection patterns detected"}


def sanitize_content(content: str, pattern: str, replacement: str = "[REDACTED]") -> dict[str, Any]:
    """Sanitize content by removing or redacting a problematic pattern.

    Args:
        content: The content to sanitize.
        pattern: The pattern to remove/redact.
        replacement: Text to replace the pattern with (default: "[REDACTED]").

    Returns:
        Dict with 'sanitized' (str), 'original' (str), 'pattern_removed' (str),
        and 'modified' (bool) keys.
    """
    # Try case-insensitive replacement
    pattern_regex = re.compile(re.escape(pattern), re.IGNORECASE)

    # Find all matches for reporting
    matches = pattern_regex.findall(content)
    modified = len(matches) > 0

    # Replace all occurrences
    sanitized = pattern_regex.sub(replacement, content)

    return {
        "sanitized": sanitized,
        "original": content,
        "pattern_removed": pattern,
        "modified": modified,
        "replacements_count": len(matches),
    }
