"""Tests for email processor pipeline orchestration."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from guarantee_email_agent.email.processor import EmailProcessor
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.email.processor_models import (
    ProcessingResult,
    ScenarioDetectionResult,
)
from guarantee_email_agent.utils.errors import EmailParseError


@pytest.fixture
def mock_config():
    """Mock agent configuration."""
    config = Mock()
    config.secrets = Mock()
    config.secrets.anthropic_api_key = "test-key"
    return config


@pytest.fixture
def mock_parser():
    """Mock email parser."""
    parser = Mock()
    parser.parse_email = Mock(
        return_value=EmailMessage(
            subject="Warranty check",
            body="My serial is SN12345",
            from_address="customer@example.com",
            received_timestamp=datetime.now(),
            thread_id="thread-123",
            message_id="msg-456",
        )
    )
    return parser


@pytest.fixture
def mock_extractor():
    """Mock serial number extractor."""
    extractor = Mock()
    extractor.extract_serial_number = AsyncMock(
        return_value=SerialExtractionResult(
            serial_number="SN12345",
            confidence=0.95,
            multiple_serials_detected=False,
            all_detected_serials=["SN12345"],
            extraction_method="pattern",
            ambiguous=False,
        )
    )
    return extractor


@pytest.fixture
def mock_detector():
    """Mock scenario detector."""
    detector = Mock()
    detector.detect_scenario = AsyncMock(
        return_value=ScenarioDetectionResult(
            scenario_name="valid-warranty",
            confidence=0.9,
            is_warranty_inquiry=True,
            detected_intent="warranty_check",
            detection_method="heuristic",
            ambiguous=False,
        )
    )
    return detector


@pytest.fixture
def mock_gmail_client():
    """Mock Gmail MCP client."""
    client = Mock()
    client.send_email = AsyncMock(return_value="sent-msg-123")
    return client


@pytest.fixture
def mock_warranty_client():
    """Mock Warranty API MCP client."""
    client = Mock()
    client.check_warranty = AsyncMock(
        return_value={
            "serial_number": "SN12345",
            "status": "valid",
            "expiration_date": "2026-06-15",
        }
    )
    return client


@pytest.fixture
def mock_ticketing_client():
    """Mock Ticketing MCP client."""
    client = Mock()
    client.create_ticket = AsyncMock(
        return_value={"ticket_id": 12345, "status": "created"}
    )
    return client


@pytest.fixture
def mock_response_generator():
    """Mock response generator."""
    generator = Mock()
    generator.generate_response = AsyncMock(
        return_value="Thank you for your inquiry. Your warranty is valid until 2026-06-15."
    )
    return generator


@pytest.fixture
def email_processor(
    mock_config,
    mock_parser,
    mock_extractor,
    mock_detector,
    mock_gmail_client,
    mock_warranty_client,
    mock_ticketing_client,
    mock_response_generator,
):
    """Create EmailProcessor with all mocked dependencies."""
    return EmailProcessor(
        config=mock_config,
        parser=mock_parser,
        extractor=mock_extractor,
        detector=mock_detector,
        gmail_client=mock_gmail_client,
        warranty_client=mock_warranty_client,
        ticketing_client=mock_ticketing_client,
        response_generator=mock_response_generator,
    )


# Test: Successful complete pipeline processing
@pytest.mark.asyncio
async def test_process_email_success_valid_warranty(email_processor):
    """Test complete pipeline with valid warranty."""
    raw_email = {
        "message_id": "test-123",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify successful processing
    assert result.is_successful() is True
    assert result.email_id == "test-123"
    assert result.scenario_used == "valid-warranty"
    assert result.serial_number == "SN12345"
    assert result.warranty_status == "valid"
    assert result.response_sent is True
    assert result.ticket_created is True
    assert result.ticket_id == 12345
    assert result.processing_time_ms >= 0  # Mocks are very fast, may be 0ms
    assert result.error_message is None
    assert result.failed_step is None


@pytest.mark.asyncio
async def test_process_email_invalid_warranty(
    email_processor, mock_warranty_client
):
    """Test processing with invalid/expired warranty."""
    # Mock expired warranty
    mock_warranty_client.check_warranty = AsyncMock(
        return_value={
            "serial_number": "SN12345",
            "status": "expired",
            "expiration_date": "2020-01-01",
        }
    )

    raw_email = {
        "message_id": "test-456",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing completed but no ticket created
    assert result.is_successful() is True
    assert result.scenario_used == "invalid-warranty"
    assert result.warranty_status == "expired"
    assert result.response_sent is True
    assert result.ticket_created is False  # No ticket for expired warranty
    assert result.ticket_id is None


@pytest.mark.asyncio
async def test_process_email_missing_serial(email_processor, mock_extractor):
    """Test processing with missing serial number."""
    # Mock no serial found
    mock_extractor.extract_serial_number = AsyncMock(
        return_value=SerialExtractionResult(
            serial_number=None,
            confidence=0.0,
            multiple_serials_detected=False,
            all_detected_serials=[],
            extraction_method="none",
            ambiguous=False,
        )
    )

    raw_email = {
        "message_id": "test-789",
        "subject": "Warranty check",
        "body": "I need warranty info",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing completed, warranty not called
    assert result.is_successful() is True
    assert result.serial_number is None
    assert result.warranty_status is None  # Warranty API not called
    assert result.response_sent is True
    assert result.ticket_created is False


@pytest.mark.asyncio
async def test_process_email_parsing_failure(email_processor, mock_parser):
    """Test handling of email parsing failure."""
    # Mock parsing error
    mock_parser.parse_email.side_effect = EmailParseError(
        message="Missing required field: from",
        code="email_missing_field",
        details={"field": "from"},
    )

    raw_email = {"message_id": "test-fail", "subject": "Test"}

    result = await email_processor.process_email(raw_email)

    # Verify failure was caught and logged
    assert result.is_successful() is False
    assert result.failed_step == "parse"
    assert result.error_message is not None  # Error message present
    assert "field" in result.error_message.lower()  # Contains field error
    assert result.response_sent is False
    assert result.ticket_created is False


@pytest.mark.asyncio
async def test_process_email_serial_extraction_error(
    email_processor, mock_extractor
):
    """Test handling of serial extraction error (non-critical)."""
    # Mock extraction error
    mock_extractor.extract_serial_number.side_effect = Exception(
        "LLM timeout"
    )

    raw_email = {
        "message_id": "test-extract-error",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing continued with fallback
    assert result.is_successful() is True  # Extraction error is not critical
    assert result.serial_number is None  # Fallback to None
    assert result.response_sent is True


@pytest.mark.asyncio
async def test_process_email_scenario_detection_error(
    email_processor, mock_detector
):
    """Test handling of scenario detection error (fallback to graceful-degradation)."""
    # Mock detection error
    mock_detector.detect_scenario.side_effect = Exception("LLM error")

    raw_email = {
        "message_id": "test-detection-error",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing continued with graceful degradation
    assert result.is_successful() is True
    assert result.scenario_used == "graceful-degradation"
    assert result.response_sent is True


@pytest.mark.asyncio
async def test_process_email_warranty_api_error(
    email_processor, mock_warranty_client
):
    """Test handling of warranty API error (fallback to graceful-degradation)."""
    # Mock warranty API error
    mock_warranty_client.check_warranty.side_effect = Exception(
        "Warranty API timeout"
    )

    raw_email = {
        "message_id": "test-warranty-error",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing continued with graceful degradation
    assert result.is_successful() is True
    assert result.scenario_used == "graceful-degradation"
    assert result.response_sent is True


@pytest.mark.asyncio
async def test_process_email_response_generation_failure(
    email_processor, mock_response_generator
):
    """Test handling of response generation failure (critical)."""
    # Mock response generation error
    mock_response_generator.generate_response.side_effect = Exception(
        "LLM generation failed"
    )

    raw_email = {
        "message_id": "test-response-error",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing marked as failed
    assert result.is_successful() is False
    assert result.failed_step == "generate_response"
    assert result.response_sent is False
    assert result.ticket_created is False


@pytest.mark.asyncio
async def test_process_email_sending_failure(
    email_processor, mock_gmail_client
):
    """Test handling of email sending failure (critical)."""
    # Mock email sending error
    mock_gmail_client.send_email.side_effect = Exception("Gmail API error")

    raw_email = {
        "message_id": "test-send-error",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing marked as failed
    assert result.is_successful() is False
    assert result.failed_step == "send_email"
    assert result.response_sent is False
    assert result.ticket_created is False


@pytest.mark.asyncio
async def test_process_email_ticket_creation_failure(
    email_processor, mock_ticketing_client
):
    """Test handling of ticket creation failure (critical for valid warranty)."""
    # Mock ticket creation error
    mock_ticketing_client.create_ticket.side_effect = Exception(
        "Ticketing API error"
    )

    raw_email = {
        "message_id": "test-ticket-error",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing marked as failed (NFR21: ticket creation critical)
    assert result.is_successful() is False
    assert result.failed_step == "create_ticket"
    assert result.response_sent is True  # Email was sent before ticket failure
    assert result.ticket_created is False


@pytest.mark.asyncio
async def test_process_email_performance_tracking(email_processor):
    """Test that processing time is tracked."""
    raw_email = {
        "message_id": "test-performance",
        "subject": "Warranty check",
        "body": "My serial is SN12345",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify processing time was tracked
    assert result.processing_time_ms >= 0  # Mocks are very fast, may be 0ms
    assert result.processing_time_ms < 60000  # Should be way under 60s in tests


@pytest.mark.asyncio
async def test_process_email_warranty_not_called_for_out_of_scope(
    email_processor, mock_detector, mock_warranty_client
):
    """Test warranty API not called for out-of-scope scenarios."""
    # Mock out-of-scope detection
    mock_detector.detect_scenario = AsyncMock(
        return_value=ScenarioDetectionResult(
            scenario_name="out-of-scope",
            confidence=0.9,
            is_warranty_inquiry=False,
            detected_intent="spam",
            detection_method="heuristic",
            ambiguous=False,
        )
    )

    raw_email = {
        "message_id": "test-out-of-scope",
        "subject": "Unsubscribe",
        "body": "Remove me from list",
        "from": "customer@example.com",
        "received": datetime.now().isoformat(),
    }

    result = await email_processor.process_email(raw_email)

    # Verify warranty API was not called (optimization per AC)
    mock_warranty_client.check_warranty.assert_not_called()
    assert result.is_successful() is True
    assert result.warranty_status is None
    assert result.ticket_created is False


@pytest.mark.asyncio
async def test_process_email_no_silent_failures(
    email_processor, mock_parser
):
    """Test that failures are never silent (NFR5, NFR45)."""
    # Mock parsing error
    mock_parser.parse_email.side_effect = Exception("Parse error")

    raw_email = {"message_id": "test-no-silent"}

    result = await email_processor.process_email(raw_email)

    # Verify failure was explicitly captured
    assert result.is_successful() is False
    assert result.error_message is not None
    assert len(result.error_message) > 0
    assert result.failed_step is not None
