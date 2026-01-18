"""Tests for email processing data models."""

import pytest
from guarantee_email_agent.email.processor_models import (
    ProcessingResult,
    ScenarioDetectionResult
)


def test_processing_result_creation():
    """Test ProcessingResult dataclass creation with all fields."""
    result = ProcessingResult(
        success=True,
        email_id="msg_123",
        scenario_used="valid-warranty",
        serial_number="SN12345",
        warranty_status="valid",
        response_sent=True,
        ticket_created=True,
        ticket_id="TKT-456",
        processing_time_ms=5000,
        error_message=None,
        failed_step=None
    )

    assert result.success is True
    assert result.email_id == "msg_123"
    assert result.scenario_used == "valid-warranty"
    assert result.serial_number == "SN12345"
    assert result.warranty_status == "valid"
    assert result.response_sent is True
    assert result.ticket_created is True
    assert result.ticket_id == "TKT-456"
    assert result.processing_time_ms == 5000
    assert result.error_message is None
    assert result.failed_step is None


def test_processing_result_is_successful():
    """Test is_successful() helper method."""
    success_result = ProcessingResult(
        success=True,
        email_id="msg_123",
        scenario_used="valid-warranty",
        serial_number="SN12345",
        warranty_status="valid",
        response_sent=True,
        ticket_created=True,
        ticket_id="TKT-456",
        processing_time_ms=5000,
        error_message=None,
        failed_step=None
    )

    failed_result = ProcessingResult(
        success=False,
        email_id="msg_123",
        scenario_used=None,
        serial_number=None,
        warranty_status=None,
        response_sent=False,
        ticket_created=False,
        ticket_id=None,
        processing_time_ms=1000,
        error_message="Parse failed",
        failed_step="parse"
    )

    assert success_result.is_successful() is True
    assert failed_result.is_successful() is False


def test_processing_result_requires_retry():
    """Test requires_retry() for transient failures."""
    # Transient failure - should retry
    warranty_api_failure = ProcessingResult(
        success=False,
        email_id="msg_123",
        scenario_used="valid-warranty",
        serial_number="SN12345",
        warranty_status=None,
        response_sent=False,
        ticket_created=False,
        ticket_id=None,
        processing_time_ms=2000,
        error_message="Warranty API timeout",
        failed_step="validate_warranty"
    )

    llm_failure = ProcessingResult(
        success=False,
        email_id="msg_123",
        scenario_used="valid-warranty",
        serial_number="SN12345",
        warranty_status="valid",
        response_sent=False,
        ticket_created=False,
        ticket_id=None,
        processing_time_ms=3000,
        error_message="LLM timeout",
        failed_step="generate_response"
    )

    # Non-transient failure - should NOT retry
    parse_failure = ProcessingResult(
        success=False,
        email_id="msg_123",
        scenario_used=None,
        serial_number=None,
        warranty_status=None,
        response_sent=False,
        ticket_created=False,
        ticket_id=None,
        processing_time_ms=100,
        error_message="Invalid email format",
        failed_step="parse"
    )

    assert warranty_api_failure.requires_retry() is True
    assert llm_failure.requires_retry() is True
    assert parse_failure.requires_retry() is False


def test_processing_result_immutable():
    """Test ProcessingResult is immutable (frozen=True)."""
    result = ProcessingResult(
        success=True,
        email_id="msg_123",
        scenario_used="valid-warranty",
        serial_number="SN12345",
        warranty_status="valid",
        response_sent=True,
        ticket_created=True,
        ticket_id="TKT-456",
        processing_time_ms=5000,
        error_message=None,
        failed_step=None
    )

    with pytest.raises(AttributeError):
        result.success = False


def test_scenario_detection_result_creation():
    """Test ScenarioDetectionResult dataclass creation."""
    result = ScenarioDetectionResult(
        scenario_name="valid-warranty",
        confidence=0.95,
        is_warranty_inquiry=True,
        detected_intent="warranty_check",
        detection_method="heuristic",
        ambiguous=False
    )

    assert result.scenario_name == "valid-warranty"
    assert result.confidence == 0.95
    assert result.is_warranty_inquiry is True
    assert result.detected_intent == "warranty_check"
    assert result.detection_method == "heuristic"
    assert result.ambiguous is False


def test_scenario_detection_result_should_process():
    """Test should_process() helper method."""
    # Should process
    valid_inquiry = ScenarioDetectionResult(
        scenario_name="valid-warranty",
        confidence=0.9,
        is_warranty_inquiry=True,
        detected_intent="warranty_check",
        detection_method="heuristic",
        ambiguous=False
    )

    missing_info = ScenarioDetectionResult(
        scenario_name="missing-info",
        confidence=0.95,
        is_warranty_inquiry=True,
        detected_intent="missing_information",
        detection_method="heuristic",
        ambiguous=False
    )

    # Should NOT process
    spam = ScenarioDetectionResult(
        scenario_name="out-of-scope",
        confidence=0.9,
        is_warranty_inquiry=False,
        detected_intent="spam",
        detection_method="heuristic",
        ambiguous=False
    )

    assert valid_inquiry.should_process() is True
    assert missing_info.should_process() is True
    assert spam.should_process() is False


def test_scenario_detection_result_get_scenario_for_routing():
    """Test get_scenario_for_routing() returns correct scenario name."""
    result = ScenarioDetectionResult(
        scenario_name="graceful-degradation",
        confidence=0.5,
        is_warranty_inquiry=False,
        detected_intent="unknown",
        detection_method="fallback",
        ambiguous=True
    )

    assert result.get_scenario_for_routing() == "graceful-degradation"


def test_scenario_detection_result_immutable():
    """Test ScenarioDetectionResult is immutable."""
    result = ScenarioDetectionResult(
        scenario_name="valid-warranty",
        confidence=0.9,
        is_warranty_inquiry=True,
        detected_intent="warranty_check",
        detection_method="heuristic",
        ambiguous=False
    )

    with pytest.raises(AttributeError):
        result.confidence = 0.5
