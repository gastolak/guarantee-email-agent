"""Tests for step orchestrator models."""

import pytest
from guarantee_email_agent.orchestrator.models import (
    StepContext,
    StepExecutionResult,
    StepRoutingResult
)


def test_step_context_creation():
    """Test StepContext dataclass creation."""
    context = StepContext(
        email_subject="Test subject",
        email_body="Test body",
        from_address="test@example.com",
        serial_number="SN12345",
        warranty_data={"status": "valid"},
        ticket_id="TKT-001"
    )

    assert context.email_subject == "Test subject"
    assert context.serial_number == "SN12345"
    assert context.warranty_data["status"] == "valid"
    assert context.ticket_id == "TKT-001"


def test_step_execution_result():
    """Test StepExecutionResult with routing decision."""
    result = StepExecutionResult(
        next_step="02-check-warranty",
        response_text="Serial found: SN12345",
        metadata={"serial": "SN12345", "reason": "Serial extracted"},
        step_name="01-extract-serial"
    )

    assert result.next_step == "02-check-warranty"
    assert result.step_name == "01-extract-serial"
    assert result.metadata["serial"] == "SN12345"
    assert result.is_done() is False


def test_step_execution_result_done():
    """Test StepExecutionResult DONE state."""
    result = StepExecutionResult(
        next_step="DONE",
        response_text="Email sent successfully",
        metadata={},
        step_name="05-send-confirmation"
    )

    assert result.is_done() is True


def test_step_routing_result():
    """Test StepRoutingResult for initial routing."""
    routing = StepRoutingResult(
        step_name="01-extract-serial",
        confidence=1.0,
        routing_method="default"
    )

    assert routing.step_name == "01-extract-serial"
    assert routing.confidence == 1.0
    assert routing.routing_method == "default"
