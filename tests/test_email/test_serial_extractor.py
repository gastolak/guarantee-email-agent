"""Tests for serial number extractor."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.config.schema import AgentConfig


# Mock config fixture
@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=AgentConfig)
    config.secrets = Mock()
    config.secrets.anthropic_api_key = "test_api_key"
    return config


# Test email fixtures
@pytest.fixture
def test_email_simple_serial():
    """Email with simple serial number format."""
    return EmailMessage(
        subject="Warranty inquiry",
        body="Hi, my serial number is SN12345. Can you check warranty?",
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )


@pytest.fixture
def test_email_multiple_serials():
    """Email with multiple serial numbers."""
    return EmailMessage(
        subject="Multiple devices",
        body="I have two devices: SN12345 and SN67890",
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )


@pytest.fixture
def test_email_no_serial():
    """Email without serial number."""
    return EmailMessage(
        subject="General question",
        body="Do you offer warranty on products?",
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )


def test_pattern_extraction_sn_format(mock_config):
    """Test pattern extraction with SN format."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    result = extractor.extract_with_patterns("My serial is SN12345")

    assert result.is_successful()
    assert result.serial_number == "12345"
    assert result.extraction_method == "pattern"
    assert result.confidence >= 0.9
    assert not result.multiple_serials_detected


def test_pattern_extraction_serial_colon_format(mock_config):
    """Test pattern extraction with 'Serial: ABC-123' format."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    result = extractor.extract_with_patterns("Serial Number: ABC-123")

    assert result.is_successful()
    assert result.serial_number == "ABC-123"
    assert result.extraction_method == "pattern"


def test_pattern_extraction_slash_n_format(mock_config):
    """Test pattern extraction with S/N format."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    result = extractor.extract_with_patterns("Product S/N: XYZ789")

    assert result.is_successful()
    assert result.serial_number == "XYZ789"


def test_pattern_extraction_multiple_serials(mock_config):
    """Test pattern extraction with multiple serials detected."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    result = extractor.extract_with_patterns("Devices: SN12345 and SN67890")

    assert result.multiple_serials_detected
    assert len(result.all_detected_serials) == 2
    assert result.ambiguous  # Multiple serials = ambiguous
    assert result.confidence < 0.9  # Lower confidence due to ambiguity


def test_pattern_extraction_no_serial_found(mock_config):
    """Test pattern extraction when no serial number found."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    result = extractor.extract_with_patterns("No serial number in this text")

    assert not result.is_successful()
    assert result.serial_number is None
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_llm_extraction_success(mock_config):
    """Test LLM extraction successfully finds serial."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    # Mock Anthropic client response
    mock_response = Mock()
    mock_response.content = [Mock(text="SN12345")]

    # Patch the client.messages.create method directly
    with patch.object(extractor.client.messages, 'create', return_value=mock_response) as mock_create:
        result = await extractor.extract_with_llm("My serial is SN12345")

        assert result.is_successful()
        assert result.serial_number == "SN12345"
        assert result.extraction_method == "llm"
        assert result.confidence > 0.5
        # Verify create was called
        assert mock_create.called


@pytest.mark.asyncio
async def test_llm_extraction_not_found(mock_config):
    """Test LLM extraction when serial not found."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    # Mock Anthropic client returning NONE
    mock_response = Mock()
    mock_response.content = [Mock(text="NONE")]

    with patch.object(extractor.client.messages, 'create', return_value=mock_response):
        result = await extractor.extract_with_llm("No serial here")

        assert not result.is_successful()
        assert result.serial_number is None
        assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_extract_serial_number_pattern_fast_path(mock_config, test_email_simple_serial):
    """Test main extraction uses pattern fast path when confident."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    # Pattern should find it immediately - no LLM needed
    # But mock anyway in case pattern fails
    mock_response = Mock()
    mock_response.content = [Mock(text="12345")]

    with patch.object(extractor.client.messages, 'create', return_value=mock_response):
        result = await extractor.extract_serial_number(test_email_simple_serial)

        # Should use pattern extraction (no LLM call)
        assert result.is_successful()
        assert result.extraction_method == "pattern"
        assert result.serial_number == "12345"


@pytest.mark.asyncio
async def test_extract_serial_number_llm_fallback(mock_config):
    """Test main extraction falls back to LLM when pattern fails."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    # Email with unconventional serial format (pattern won't find it)
    email = EmailMessage(
        subject="Warranty",
        body="Product code is ABC123XYZ",
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )

    # Mock LLM to return the serial
    mock_response = Mock()
    mock_response.content = [Mock(text="ABC123XYZ")]

    with patch.object(extractor.client.messages, 'create', return_value=mock_response):
        result = await extractor.extract_serial_number(email)

        # Should fall back to LLM
        assert result.is_successful()
        assert result.extraction_method == "llm"


@pytest.mark.asyncio
async def test_extract_serial_number_both_methods_fail(mock_config, test_email_no_serial):
    """Test extraction when both pattern and LLM fail."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    # Mock LLM to return NONE
    mock_response = Mock()
    mock_response.content = [Mock(text="NONE")]

    with patch.object(extractor.client.messages, 'create', return_value=mock_response):
        result = await extractor.extract_serial_number(test_email_no_serial)

        assert not result.is_successful()
        assert result.serial_number is None
        assert result.extraction_method == "none"


@pytest.mark.asyncio
async def test_extraction_error_handling_graceful(mock_config):
    """Test extraction errors handled gracefully without crashing."""
    extractor = SerialNumberExtractor(mock_config, "test instruction")

    email = EmailMessage(
        subject="Test",
        body="Test body",
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )

    # Mock LLM to raise exception
    with patch.object(extractor.client.messages, 'create', side_effect=Exception("API Error")):
        # Should NOT crash - should return failed result
        result = await extractor.extract_serial_number(email)

        assert not result.is_successful()
        assert result.serial_number is None
        assert result.ambiguous  # Error cases marked ambiguous for degradation


def test_serial_extraction_result_should_use_graceful_degradation(mock_config):
    """Test graceful degradation logic."""
    # Ambiguous case
    result1 = SerialExtractionResult(
        serial_number="SN123",
        confidence=0.9,
        multiple_serials_detected=False,
        all_detected_serials=["SN123"],
        extraction_method="pattern",
        ambiguous=True
    )
    assert result1.should_use_graceful_degradation()

    # Multiple serials with low confidence
    result2 = SerialExtractionResult(
        serial_number="SN123",
        confidence=0.6,
        multiple_serials_detected=True,
        all_detected_serials=["SN123", "SN456"],
        extraction_method="pattern",
        ambiguous=True
    )
    assert result2.should_use_graceful_degradation()

    # High confidence single serial - no degradation
    result3 = SerialExtractionResult(
        serial_number="SN123",
        confidence=0.95,
        multiple_serials_detected=False,
        all_detected_serials=["SN123"],
        extraction_method="pattern",
        ambiguous=False
    )
    assert not result3.should_use_graceful_degradation()
