"""Centralized security patterns for the governance system.

This module provides a single source of truth for all security-related
patterns used across validators and policies, eliminating duplication.
"""


class SecurityPatterns:
    """Centralized registry of security patterns for content validation.

    These patterns are used by both validators and policies to detect
    potentially harmful content. Having a single source of truth prevents
    inconsistencies and makes updates easier.
    """

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

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        "';",
        "' or '1'='1",
        "' or 1=1--",
        "' or 1=1#",
        "' or 1=1/*",
        ") or ('1'='1",
        "admin'--",
        "admin'/*",
        "drop table",
        "drop database",
        "delete from",
        "truncate",
        "union select",
        "insert into",
        "update ",
        "exec(",
        "execute(",
        "sp_executesql",
        "script ",
        "javascript:",
        "onerror=",
        "onload=",
    ]

    # Self-harm related patterns
    SELF_HARM_PATTERNS = [
        "kill myself",
        "want to die",
        "suicide",
        "end my life",
        "hurt myself",
        "self harm",
        "cut myself",
        "commit suicide",
        "don't want to live",
        "better off dead",
    ]

    # Hate speech patterns
    HATE_SPEECH_PATTERNS = [
        "hate speech",
        "racial slur",
        "discriminat",
        "all [group] are",
        "[group] should be",
        "inferior race",
        "superior race",
        "ethnic cleansing",
        "kill all [group]",
    ]

    # Threats and violence patterns
    THREATS_PATTERNS = [
        "i will kill",
        "going to kill",
        "i will hurt",
        "going to hurt",
        "threaten to",
        "death threat",
        "bomb threat",
        "shoot up",
        "mass shooting",
        "violence against",
        "physically harm",
        "assault",
        "murder",
        "terrorist attack",
    ]

    # Sexual content patterns
    SEXUAL_CONTENT_PATTERNS = [
        "pornography",
        "sexually explicit",
        "nsfw",
        "adult content",
        "explicit content",
    ]

    @classmethod
    def get_injection_patterns(cls) -> list[str]:
        """Get prompt injection patterns.

        Returns:
            List of prompt injection pattern strings.
        """
        return cls.INJECTION_PATTERNS.copy()

    @classmethod
    def get_code_execution_patterns(cls) -> list[str]:
        """Get code execution patterns.

        Returns:
            List of code execution pattern strings.
        """
        return cls.CODE_EXECUTION_PATTERNS.copy()

    @classmethod
    def get_sql_injection_patterns(cls) -> list[str]:
        """Get SQL injection patterns.

        Returns:
            List of SQL injection pattern strings.
        """
        return cls.SQL_INJECTION_PATTERNS.copy()

    @classmethod
    def get_self_harm_patterns(cls) -> list[str]:
        """Get self-harm related patterns.

        Returns:
            List of self-harm pattern strings.
        """
        return cls.SELF_HARM_PATTERNS.copy()

    @classmethod
    def get_hate_speech_patterns(cls) -> list[str]:
        """Get hate speech patterns.

        Returns:
            List of hate speech pattern strings.
        """
        return cls.HATE_SPEECH_PATTERNS.copy()

    @classmethod
    def get_threats_patterns(cls) -> list[str]:
        """Get threats and violence patterns.

        Returns:
            List of threat pattern strings.
        """
        return cls.THREATS_PATTERNS.copy()

    @classmethod
    def get_sexual_content_patterns(cls) -> list[str]:
        """Get sexual content patterns.

        Returns:
            List of sexual content pattern strings.
        """
        return cls.SEXUAL_CONTENT_PATTERNS.copy()
