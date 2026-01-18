"""Tests for email data models."""

import pytest
from datetime import datetime
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult


def test_email_message_creation():
    """Test EmailMessage dataclass creation with all fields."""
    email = EmailMessage(
        subject="Warranty check",
        body="Hi, I need warranty info for SN12345",
        from_address="customer@example.com",
        received_timestamp=datetime(2026, 1, 18, 10, 0, 0),
        thread_id="thread_123",
        message_id="msg_456"
    )

    assert email.subject == "Warranty check"
    assert email.body == "Hi, I need warranty info for SN12345"
    assert email.from_address == "customer@example.com"
    assert email.received_timestamp == datetime(2026, 1, 18, 10, 0, 0)
    assert email.thread_id == "thread_123"
    assert email.message_id == "msg_456"


def test_email_message_optional_fields():
    """Test EmailMessage with optional fields as None."""
    email = EmailMessage(
        subject="Test",
        body="Test body",
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )

    assert email.thread_id is None
    assert email.message_id is None


def test_email_message_str_excludes_body():
    """Test EmailMessage __str__ excludes body per NFR14."""
    email = EmailMessage(
        subject="Test Subject",
        body="SENSITIVE CUSTOMER DATA",
        from_address="test@example.com",
        received_timestamp=datetime(2026, 1, 18, 10, 0, 0)
    )

    email_str = str(email)

    # Should NOT include body
    assert "SENSITIVE CUSTOMER DATA" not in email_str

    # Should include other fields
    assert "Test Subject" in email_str
    assert "test@example.com" in email_str


def test_email_message_immutable():
    """Test EmailMessage is immutable (frozen=True)."""
    email = EmailMessage(
        subject="Test",
        body="Test body",
        from_address="test@example.com",
        received_timestamp=datetime.now()
    )

    # Should raise error when trying to modify
    with pytest.raises(AttributeError):
        email.subject = "Modified"


def test_serial_extraction_result_successful():
    """Test SerialExtractionResult for successful extraction."""
    result = SerialExtractionResult(
        serial_number="SN12345",
        confidence=0.95,
        multiple_serials_detected=False,
        all_detected_serials=["SN12345"],
        extraction_method="pattern",
        ambiguous=False
    )

    assert result.serial_number == "SN12345"
    assert result.confidence == 0.95
    assert result.is_successful() is True
    assert result.should_use_graceful_degradation() is False


def test_serial_extraction_result_failed():
    """Test SerialExtractionResult for failed extraction."""
    result = SerialExtractionResult(
        serial_number=None,
        confidence=0.0,
        multiple_serials_detected=False,
        all_detected_serials=[],
        extraction_method="none",
        ambiguous=False
    )

    assert result.serial_number is None
    assert result.is_successful() is False


def test_serial_extraction_result_multiple_serials():
    """Test SerialExtractionResult with multiple serials detected."""
    result = SerialExtractionResult(
        serial_number="SN12345",
        confidence=0.7,
        multiple_serials_detected=True,
        all_detected_serials=["SN12345", "SN67890"],
        extraction_method="pattern",
        ambiguous=True
    )

    assert result.multiple_serials_detected is True
    assert len(result.all_detected_serials) == 2
    assert result.should_use_graceful_degradation() is True


def test_serial_extraction_result_ambiguous_low_confidence():
    """Test SerialExtractionResult triggers graceful degradation on low confidence."""
    result = SerialExtractionResult(
        serial_number="SN12345",
        confidence=0.6,
        multiple_serials_detected=True,
        all_detected_serials=["SN12345", "SN67890"],
        extraction_method="pattern",
        ambiguous=True
    )

    # Should recommend graceful degradation (ambiguous=True)
    assert result.should_use_graceful_degradation() is True


def test_serial_extraction_result_high_confidence_no_degradation():
    """Test SerialExtractionResult doesn't trigger degradation with high confidence."""
    result = SerialExtractionResult(
        serial_number="SN12345",
        confidence=0.95,
        multiple_serials_detected=False,
        all_detected_serials=["SN12345"],
        extraction_method="pattern",
        ambiguous=False
    )

    assert result.should_use_graceful_degradation() is False
