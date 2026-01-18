"""Tests for scenario detector."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from guarantee_email_agent.email.scenario_detector import ScenarioDetector
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.email.processor_models import ScenarioDetectionResult
from guarantee_email_agent.config.schema import AgentConfig


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=AgentConfig)
    config.secrets = Mock()
    config.secrets.anthropic_api_key = "test_api_key"
    return config


@pytest.fixture
def test_email_with_serial():
    """Email with warranty inquiry and serial number."""
    return EmailMessage(
        subject="Warranty check",
        body="Hi, I need to check warranty status for my product. Serial number is SN12345.",
        from_address="customer@example.com",
        received_timestamp=datetime.now()
    )


@pytest.fixture
def test_email_no_serial():
    """Email with warranty inquiry but missing serial."""
    return EmailMessage(
        subject="Warranty question",
        body="Hi, I need warranty information but I don't have my serial number handy.",
        from_address="customer@example.com",
        received_timestamp=datetime.now()
    )


@pytest.fixture
def test_email_spam():
    """Spam email."""
    return EmailMessage(
        subject="Click here for free money!",
        body="Congratulations you won the lottery! Click here to claim your prize!",
        from_address="spam@example.com",
        received_timestamp=datetime.now()
    )


@pytest.fixture
def serial_result_found():
    """Serial extraction result with serial found."""
    return SerialExtractionResult(
        serial_number="SN12345",
        confidence=0.95,
        multiple_serials_detected=False,
        all_detected_serials=["SN12345"],
        extraction_method="pattern",
        ambiguous=False
    )


@pytest.fixture
def serial_result_not_found():
    """Serial extraction result with no serial."""
    return SerialExtractionResult(
        serial_number=None,
        confidence=0.0,
        multiple_serials_detected=False,
        all_detected_serials=[],
        extraction_method="none",
        ambiguous=False
    )


def test_heuristic_detection_no_serial(mock_config, test_email_with_serial, serial_result_not_found):
    """Test heuristic detects missing-info when no serial found."""
    detector = ScenarioDetector(mock_config, "test instruction")

    result = detector.detect_with_heuristics(test_email_with_serial, serial_result_not_found)

    assert result.scenario_name == "missing-info"
    assert result.confidence >= 0.8
    assert result.is_warranty_inquiry is True
    assert result.detected_intent == "missing_information"
    assert result.detection_method == "heuristic"


def test_heuristic_detection_spam(mock_config, test_email_spam, serial_result_not_found):
    """Test heuristic detects spam keywords."""
    detector = ScenarioDetector(mock_config, "test instruction")

    result = detector.detect_with_heuristics(test_email_spam, serial_result_not_found)

    assert result.scenario_name == "out-of-scope"
    assert result.is_warranty_inquiry is False
    assert result.detected_intent == "spam"
    assert result.detection_method == "heuristic"


def test_heuristic_detection_warranty_keyword(mock_config, test_email_with_serial, serial_result_found):
    """Test heuristic detects warranty keyword with serial."""
    detector = ScenarioDetector(mock_config, "test instruction")

    result = detector.detect_with_heuristics(test_email_with_serial, serial_result_found)

    assert result.scenario_name == "valid-warranty"
    assert result.confidence >= 0.8
    assert result.is_warranty_inquiry is True
    assert result.detected_intent == "warranty_check"
    assert result.detection_method == "heuristic"


def test_heuristic_detection_short_email(mock_config, serial_result_not_found):
    """Test heuristic detects very short emails as potential spam."""
    short_email = EmailMessage(
        subject="Hi",
        body="Test",  # Very short
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )

    detector = ScenarioDetector(mock_config, "test instruction")

    result = detector.detect_with_heuristics(short_email, serial_result_not_found)

    assert result.scenario_name == "out-of-scope"
    assert result.confidence < 0.8  # Low confidence should trigger LLM fallback
    assert result.ambiguous is True


@pytest.mark.asyncio
async def test_llm_detection_valid_warranty(mock_config, test_email_with_serial, serial_result_found):
    """Test LLM detection identifies valid warranty inquiry."""
    detector = ScenarioDetector(mock_config, "test instruction")

    # Mock Anthropic response
    mock_response = Mock()
    mock_response.content = [Mock(text="valid_warranty_inquiry")]

    with patch.object(detector.client.messages, 'create', return_value=mock_response):
        result = await detector.detect_with_llm(test_email_with_serial, serial_result_found)

        assert result.scenario_name == "valid-warranty"
        assert result.is_warranty_inquiry is True
        assert result.detected_intent == "warranty_check"
        assert result.detection_method == "llm"


@pytest.mark.asyncio
async def test_llm_detection_missing_info(mock_config, test_email_no_serial, serial_result_not_found):
    """Test LLM detection identifies missing information."""
    detector = ScenarioDetector(mock_config, "test instruction")

    mock_response = Mock()
    mock_response.content = [Mock(text="missing_information")]

    with patch.object(detector.client.messages, 'create', return_value=mock_response):
        result = await detector.detect_with_llm(test_email_no_serial, serial_result_not_found)

        assert result.scenario_name == "missing-info"
        assert result.is_warranty_inquiry is True
        assert result.detected_intent == "missing_information"


@pytest.mark.asyncio
async def test_llm_detection_out_of_scope(mock_config, serial_result_not_found):
    """Test LLM detection identifies out-of-scope emails."""
    non_warranty_email = EmailMessage(
        subject="Billing question",
        body="I have a question about my recent invoice.",
        from_address="customer@example.com",
        received_timestamp=datetime.now()
    )

    detector = ScenarioDetector(mock_config, "test instruction")

    mock_response = Mock()
    mock_response.content = [Mock(text="out_of_scope")]

    with patch.object(detector.client.messages, 'create', return_value=mock_response):
        result = await detector.detect_with_llm(non_warranty_email, serial_result_not_found)

        assert result.scenario_name == "out-of-scope"
        assert result.is_warranty_inquiry is False
        assert result.detected_intent == "non_warranty"


@pytest.mark.asyncio
async def test_llm_detection_ambiguous_response(mock_config, test_email_with_serial, serial_result_found):
    """Test LLM detection handles ambiguous classification."""
    detector = ScenarioDetector(mock_config, "test instruction")

    mock_response = Mock()
    mock_response.content = [Mock(text="unknown_category")]

    with patch.object(detector.client.messages, 'create', return_value=mock_response):
        result = await detector.detect_with_llm(test_email_with_serial, serial_result_found)

        # Should default to graceful-degradation for ambiguous response
        assert result.scenario_name == "graceful-degradation"
        assert result.is_warranty_inquiry is False
        assert result.detected_intent == "unknown"


@pytest.mark.asyncio
async def test_detect_scenario_high_confidence_heuristic(mock_config, test_email_with_serial, serial_result_found):
    """Test main detection uses heuristic when confidence >= 0.8."""
    detector = ScenarioDetector(mock_config, "test instruction")

    # Should NOT call LLM if heuristic confidence is high
    with patch.object(detector, 'detect_with_llm') as mock_llm:
        result = await detector.detect_scenario(test_email_with_serial, serial_result_found)

        # Heuristic should return high confidence for warranty keyword + serial
        assert result.scenario_name == "valid-warranty"
        assert result.detection_method == "heuristic"
        # LLM should NOT be called
        mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_detect_scenario_low_confidence_fallback_to_llm(mock_config, serial_result_not_found):
    """Test main detection falls back to LLM when heuristic confidence low."""
    # Email without clear indicators (ambiguous)
    ambiguous_email = EmailMessage(
        subject="Product inquiry",
        body="I have a question about my recent purchase.",
        from_address="customer@example.com",
        received_timestamp=datetime.now()
    )

    detector = ScenarioDetector(mock_config, "test instruction")

    # Mock LLM response
    mock_response = Mock()
    mock_response.content = [Mock(text="out_of_scope")]

    with patch.object(detector.client.messages, 'create', return_value=mock_response):
        result = await detector.detect_scenario(ambiguous_email, serial_result_not_found)

        # Should have used LLM fallback
        assert result.detection_method == "llm"


@pytest.mark.asyncio
async def test_detect_scenario_error_handling(mock_config, serial_result_not_found):
    """Test detection errors default to graceful-degradation."""
    # Use ambiguous email to force LLM fallback (no warranty keyword, no serial)
    ambiguous_email = EmailMessage(
        subject="Product question",
        body="I have a question about my recent purchase from your company.",
        from_address="customer@example.com",
        received_timestamp=datetime.now()
    )

    detector = ScenarioDetector(mock_config, "test instruction")

    # Mock LLM to raise error
    with patch.object(detector.client.messages, 'create', side_effect=Exception("API Error")):
        result = await detector.detect_scenario(ambiguous_email, serial_result_not_found)

        # Should fall back to graceful-degradation on error
        assert result.scenario_name == "graceful-degradation"
        assert result.ambiguous is True
        assert result.detection_method == "fallback"


def test_scenario_detector_initialization_missing_api_key():
    """Test detector raises error if API key not configured."""
    config = Mock(spec=AgentConfig)
    config.secrets = Mock()
    config.secrets.anthropic_api_key = None

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not configured"):
        ScenarioDetector(config, "test instruction")
