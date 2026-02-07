"""Unit tests for trust level components."""

import pytest

from model_governance.trust import (
    BlockLowTrustPolicy,
    RequireAuthPolicy,
    TrustClassifier,
    TrustContext,
    TrustLevel,
    parse_trust_level,
)


class TestTrustLevel:
    """Tests for TrustLevel enum."""

    def test_trust_level_hierarchy(self) -> None:
        """Test trust level hierarchy and comparisons."""
        assert TrustLevel.UNTRUSTED < TrustLevel.LOW
        assert TrustLevel.LOW < TrustLevel.MEDIUM
        assert TrustLevel.MEDIUM < TrustLevel.HIGH
        assert TrustLevel.HIGH < TrustLevel.CRITICAL

    def test_can_access(self) -> None:
        """Test the can_access method."""
        assert TrustLevel.HIGH.can_access(TrustLevel.MEDIUM) is True
        assert TrustLevel.LOW.can_access(TrustLevel.HIGH) is False
        assert TrustLevel.MEDIUM.can_access(TrustLevel.MEDIUM) is True

    def test_requires_review(self) -> None:
        """Test the requires_review method."""
        assert TrustLevel.UNTRUSTED.requires_review() is True
        assert TrustLevel.LOW.requires_review() is True
        assert TrustLevel.MEDIUM.requires_review() is False
        assert TrustLevel.HIGH.requires_review() is False

    def test_is_blocked_by_default(self) -> None:
        """Test the is_blocked_by_default method."""
        assert TrustLevel.UNTRUSTED.is_blocked_by_default() is True
        assert TrustLevel.LOW.is_blocked_by_default() is False


class TestParseTrustLevel:
    """Tests for parse_trust_level function."""

    def test_parse_from_enum(self) -> None:
        """Test parsing from TrustLevel enum."""
        result = parse_trust_level(TrustLevel.HIGH)
        assert result == TrustLevel.HIGH

    def test_parse_from_string(self) -> None:
        """Test parsing from string."""
        result = parse_trust_level("HIGH")
        assert result == TrustLevel.HIGH

        result = parse_trust_level("medium")
        assert result == TrustLevel.MEDIUM

    def test_parse_from_int(self) -> None:
        """Test parsing from integer."""
        result = parse_trust_level(3)
        assert result == TrustLevel.HIGH

    def test_parse_invalid(self) -> None:
        """Test parsing invalid values."""
        with pytest.raises(ValueError):
            parse_trust_level("INVALID")

        with pytest.raises(ValueError):
            parse_trust_level(999)


class TestTrustContext:
    """Tests for TrustContext model."""

    def test_trust_context_creation(self) -> None:
        """Test creating a trust context."""
        context = TrustContext(
            source_type="user_input",
            source_id="user123",
            historical_trust=0.85,
        )

        assert context.source_type == "user_input"
        assert context.source_id == "user123"
        assert context.historical_trust == 0.85

    def test_trust_level_validation(self) -> None:
        """Test trust level field validation."""
        context = TrustContext(
            source_type="user_input",
            authentication_level=TrustLevel.HIGH,
        )

        assert context.authentication_level == TrustLevel.HIGH


class TestTrustClassifier:
    """Tests for TrustClassifier."""

    @pytest.mark.asyncio
    async def test_classify_system_prompt(self) -> None:
        """Test classifying system prompts."""
        classifier = TrustClassifier()
        context = TrustContext(source_type="system_prompt")

        level = await classifier.classify(context)
        assert level == TrustLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_classify_user_input_with_history(self) -> None:
        """Test classifying user input with history."""
        classifier = TrustClassifier()

        # High trust history
        context = TrustContext(
            source_type="user_input",
            historical_trust=0.95,
        )
        level = await classifier.classify(context)
        assert level == TrustLevel.HIGH

        # Low trust history
        context = TrustContext(
            source_type="user_input",
            historical_trust=0.4,
        )
        level = await classifier.classify(context)
        assert level == TrustLevel.LOW

    @pytest.mark.asyncio
    async def test_classify_tool_input(self) -> None:
        """Test classifying tool input."""
        classifier = TrustClassifier()
        context = TrustContext(source_type="tool_input")

        level = await classifier.classify(context)
        assert level == TrustLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_classify_attachment(self) -> None:
        """Test classifying attachments."""
        classifier = TrustClassifier()
        context = TrustContext(source_type="attachment")

        level = await classifier.classify(context)
        assert level == TrustLevel.LOW

    @pytest.mark.asyncio
    async def test_classify_base64(self) -> None:
        """Test classifying base64 content."""
        classifier = TrustClassifier()
        context = TrustContext(source_type="base64")

        level = await classifier.classify(context)
        assert level == TrustLevel.LOW

    @pytest.mark.asyncio
    async def test_custom_rule_registration(self) -> None:
        """Test registering custom classification rules."""
        classifier = TrustClassifier()

        async def custom_rule(context):
            return TrustLevel.CRITICAL

        classifier.register_rule("custom", custom_rule)

        context = TrustContext(source_type="custom")
        level = await classifier.classify(context)
        assert level == TrustLevel.CRITICAL


class TestTrustPolicies:
    """Tests for trust-based policies."""

    @pytest.mark.asyncio
    async def test_block_low_trust_policy(self) -> None:
        """Test BlockLowTrustPolicy."""
        policy = BlockLowTrustPolicy()

        # HIGH trust should pass
        allowed, reason = await policy.is_allowed(TrustLevel.HIGH, {})
        assert allowed is True

        # LOW trust should be blocked
        allowed, reason = await policy.is_allowed(TrustLevel.LOW, {})
        assert allowed is False
        assert "MEDIUM" in reason

    @pytest.mark.asyncio
    async def test_require_auth_policy(self) -> None:
        """Test RequireAuthPolicy."""
        policy = RequireAuthPolicy()

        # HIGH trust should pass
        allowed, reason = await policy.is_allowed(TrustLevel.HIGH, {})
        assert allowed is True

        # MEDIUM trust should be blocked
        allowed, reason = await policy.is_allowed(TrustLevel.MEDIUM, {})
        assert allowed is False
        assert "HIGH" in reason
