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

    def test_trust_level_hierarchy(self, test_output) -> None:
        """Test trust level hierarchy and comparisons."""
        test_output.print_section("Trust Level Hierarchy Test")

        comparisons = [
            (TrustLevel.UNTRUSTED, TrustLevel.LOW, "UNTRUSTED < LOW"),
            (TrustLevel.LOW, TrustLevel.MEDIUM, "LOW < MEDIUM"),
            (TrustLevel.MEDIUM, TrustLevel.HIGH, "MEDIUM < HIGH"),
            (TrustLevel.HIGH, TrustLevel.CRITICAL, "HIGH < CRITICAL"),
        ]

        for lower, higher, description in comparisons:
            test_output.print_input("Comparison", description)
            result = lower < higher
            test_output.print_output(f"Result: {description}", result)

        assert TrustLevel.UNTRUSTED < TrustLevel.LOW
        assert TrustLevel.LOW < TrustLevel.MEDIUM
        assert TrustLevel.MEDIUM < TrustLevel.HIGH
        assert TrustLevel.HIGH < TrustLevel.CRITICAL

    def test_can_access(self, test_output) -> None:
        """Test the can_access method."""
        test_output.print_section("Can Access Test")

        test_output.print_input("HIGH accessing MEDIUM", True)
        result1 = TrustLevel.HIGH.can_access(TrustLevel.MEDIUM)
        test_output.print_output("HIGH can_access MEDIUM", result1)

        test_output.print_input("LOW accessing HIGH", False)
        result2 = TrustLevel.LOW.can_access(TrustLevel.HIGH)
        test_output.print_output("LOW can_access HIGH", result2)

        test_output.print_input("MEDIUM accessing MEDIUM", True)
        result3 = TrustLevel.MEDIUM.can_access(TrustLevel.MEDIUM)
        test_output.print_output("MEDIUM can_access MEDIUM", result3)

        assert TrustLevel.HIGH.can_access(TrustLevel.MEDIUM) is True
        assert TrustLevel.LOW.can_access(TrustLevel.HIGH) is False
        assert TrustLevel.MEDIUM.can_access(TrustLevel.MEDIUM) is True

    def test_requires_review(self, test_output) -> None:
        """Test the requires_review method."""
        test_output.print_section("Requires Review Test")

        levels = [
            (TrustLevel.UNTRUSTED, True),
            (TrustLevel.LOW, True),
            (TrustLevel.MEDIUM, False),
            (TrustLevel.HIGH, False),
        ]

        for level, expected in levels:
            test_output.print_input(f"Level: {level.name}", expected)
            result = level.requires_review()
            test_output.print_output(f"{level.name}.requires_review()", result)

        assert TrustLevel.UNTRUSTED.requires_review() is True
        assert TrustLevel.LOW.requires_review() is True
        assert TrustLevel.MEDIUM.requires_review() is False
        assert TrustLevel.HIGH.requires_review() is False

    def test_is_blocked_by_default(self, test_output) -> None:
        """Test the is_blocked_by_default method."""
        test_output.print_section("Is Blocked By Default Test")

        result1 = TrustLevel.UNTRUSTED.is_blocked_by_default()
        test_output.print_output("UNTRUSTED.is_blocked_by_default()", result1)

        result2 = TrustLevel.LOW.is_blocked_by_default()
        test_output.print_output("LOW.is_blocked_by_default()", result2)

        assert TrustLevel.UNTRUSTED.is_blocked_by_default() is True
        assert TrustLevel.LOW.is_blocked_by_default() is False


class TestParseTrustLevel:
    """Tests for parse_trust_level function."""

    def test_parse_from_enum(self, test_output) -> None:
        """Test parsing from TrustLevel enum."""
        test_output.print_section("Parse From Enum Test")

        input_level = TrustLevel.HIGH
        test_output.print_input("Input", input_level)

        result = parse_trust_level(input_level)
        test_output.print_output("Result", result)

        assert result == TrustLevel.HIGH

    def test_parse_from_string(self, test_output) -> None:
        """Test parsing from string."""
        test_output.print_section("Parse From String Test")

        # Test uppercase
        test_output.print_input("Input", "HIGH")
        result1 = parse_trust_level("HIGH")
        test_output.print_output("Result", result1)

        # Test lowercase
        test_output.print_input("Input", "medium")
        result2 = parse_trust_level("medium")
        test_output.print_output("Result", result2)

        assert result1 == TrustLevel.HIGH
        assert result2 == TrustLevel.MEDIUM

    def test_parse_from_int(self, test_output) -> None:
        """Test parsing from integer."""
        test_output.print_section("Parse From Int Test")

        test_output.print_input("Input", 3)
        result = parse_trust_level(3)
        test_output.print_output("Result", result)

        assert result == TrustLevel.HIGH

    def test_parse_invalid(self, test_output) -> None:
        """Test parsing invalid values."""
        test_output.print_section("Parse Invalid Test")

        try:
            test_output.print_input("Input", "INVALID")
            parse_trust_level("INVALID")
            test_output.print_output("Result", "Should have raised ValueError")
        except ValueError as e:
            test_output.print_output("ValueError", str(e))

        try:
            test_output.print_input("Input", 999)
            parse_trust_level(999)
            test_output.print_output("Result", "Should have raised ValueError")
        except ValueError as e:
            test_output.print_output("ValueError", str(e))

        with pytest.raises(ValueError):
            parse_trust_level("INVALID")

        with pytest.raises(ValueError):
            parse_trust_level(999)


class TestTrustContext:
    """Tests for TrustContext model."""

    def test_trust_context_creation(self, test_output) -> None:
        """Test creating a trust context."""
        test_output.print_section("Trust Context Creation Test")

        context = TrustContext(
            source_type="user_input",
            source_id="user123",
            historical_trust=0.85,
        )

        test_output.print_output("Context", context)

        assert context.source_type == "user_input"
        assert context.source_id == "user123"
        assert context.historical_trust == 0.85

    def test_trust_level_validation(self, test_output) -> None:
        """Test trust level field validation."""
        test_output.print_section("Trust Level Validation Test")

        context = TrustContext(
            source_type="user_input",
            authentication_level=TrustLevel.HIGH,
        )

        test_output.print_output("Context", context)
        test_output.print_output("Authentication Level", context.authentication_level)

        assert context.authentication_level == TrustLevel.HIGH


class TestTrustClassifier:
    """Tests for TrustClassifier."""

    @pytest.mark.asyncio
    async def test_classify_system_prompt(self, test_output) -> None:
        """Test classifying system prompts."""
        test_output.print_section("Classify System Prompt Test")

        classifier = TrustClassifier()
        context = TrustContext(source_type="system_prompt")

        test_output.print_input("Context", context)
        level = await classifier.classify(context)

        test_output.print_output("Trust Level", level)

        assert level == TrustLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_classify_user_input_with_history(self, test_output) -> None:
        """Test classifying user input with history."""
        test_output.print_section("Classify User Input With History Test")

        classifier = TrustClassifier()

        # High trust history
        test_output.print_subsection("High Trust History")
        context = TrustContext(
            source_type="user_input",
            historical_trust=0.95,
        )
        test_output.print_input("Historical Trust", 0.95)
        level = await classifier.classify(context)
        test_output.print_output("Trust Level", level)
        assert level == TrustLevel.HIGH

        # Low trust history
        test_output.print_subsection("Low Trust History")
        context = TrustContext(
            source_type="user_input",
            historical_trust=0.4,
        )
        test_output.print_input("Historical Trust", 0.4)
        level = await classifier.classify(context)
        test_output.print_output("Trust Level", level)
        assert level == TrustLevel.LOW

    @pytest.mark.asyncio
    async def test_classify_tool_input(self, test_output) -> None:
        """Test classifying tool input."""
        test_output.print_section("Classify Tool Input Test")

        classifier = TrustClassifier()
        context = TrustContext(source_type="tool_input")

        test_output.print_input("Context", context)
        level = await classifier.classify(context)

        test_output.print_output("Trust Level", level)

        assert level == TrustLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_classify_attachment(self, test_output) -> None:
        """Test classifying attachments."""
        test_output.print_section("Classify Attachment Test")

        classifier = TrustClassifier()
        context = TrustContext(source_type="attachment")

        test_output.print_input("Context", context)
        level = await classifier.classify(context)

        test_output.print_output("Trust Level", level)

        assert level == TrustLevel.LOW

    @pytest.mark.asyncio
    async def test_classify_base64(self, test_output) -> None:
        """Test classifying base64 content."""
        test_output.print_section("Classify Base64 Test")

        classifier = TrustClassifier()
        context = TrustContext(source_type="base64")

        test_output.print_input("Context", context)
        level = await classifier.classify(context)

        test_output.print_output("Trust Level", level)

        assert level == TrustLevel.LOW

    @pytest.mark.asyncio
    async def test_custom_rule_registration(self, test_output) -> None:
        """Test registering custom classification rules."""
        test_output.print_section("Custom Rule Registration Test")

        classifier = TrustClassifier()

        async def custom_rule(context):
            return TrustLevel.CRITICAL

        classifier.register_rule("custom", custom_rule)

        context = TrustContext(source_type="custom")

        test_output.print_input("Context", context)
        level = await classifier.classify(context)

        test_output.print_output("Trust Level", level)

        assert level == TrustLevel.CRITICAL


class TestTrustPolicies:
    """Tests for trust-based policies."""

    @pytest.mark.asyncio
    async def test_block_low_trust_policy(self, test_output) -> None:
        """Test BlockLowTrustPolicy."""
        test_output.print_section("Block Low Trust Policy Test")

        policy = BlockLowTrustPolicy()

        # HIGH trust should pass
        test_output.print_subsection("HIGH Trust")
        test_output.print_input("Trust Level", TrustLevel.HIGH)
        allowed, reason = await policy.is_allowed(TrustLevel.HIGH, {})
        test_output.print_output("Allowed", allowed)
        test_output.print_output("Reason", reason)
        assert allowed is True

        # LOW trust should be blocked
        test_output.print_subsection("LOW Trust")
        test_output.print_input("Trust Level", TrustLevel.LOW)
        allowed, reason = await policy.is_allowed(TrustLevel.LOW, {})
        test_output.print_output("Allowed", allowed)
        test_output.print_output("Reason", reason)
        assert allowed is False
        assert "MEDIUM" in reason

    @pytest.mark.asyncio
    async def test_require_auth_policy(self, test_output) -> None:
        """Test RequireAuthPolicy."""
        test_output.print_section("Require Auth Policy Test")

        policy = RequireAuthPolicy()

        # HIGH trust should pass
        test_output.print_subsection("HIGH Trust")
        test_output.print_input("Trust Level", TrustLevel.HIGH)
        allowed, reason = await policy.is_allowed(TrustLevel.HIGH, {})
        test_output.print_output("Allowed", allowed)
        test_output.print_output("Reason", reason)
        assert allowed is True

        # MEDIUM trust should be blocked
        test_output.print_subsection("MEDIUM Trust")
        test_output.print_input("Trust Level", TrustLevel.MEDIUM)
        allowed, reason = await policy.is_allowed(TrustLevel.MEDIUM, {})
        test_output.print_output("Allowed", allowed)
        test_output.print_output("Reason", reason)
        assert allowed is False
        assert "HIGH" in reason
