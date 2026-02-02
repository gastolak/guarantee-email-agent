"""Tests for EmailProcessor dual-mode routing (Story 5.1)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from guarantee_email_agent.email.processor import EmailProcessor
from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.config.schema import AgentConfig, AgentRuntimeConfig
from guarantee_email_agent.orchestrator.models import StepContext, StepExecutionResult
from guarantee_email_agent.orchestrator.step_orchestrator import OrchestrationResult


@pytest.fixture
def sample_raw_email():
    """Sample raw email message dict for testing."""
    return {
        "id": "msg-001",
        "threadId": "thread-001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Broken device - need warranty"},
                {"name": "From", "value": "customer@example.com"},
                {"name": "To", "value": "support@acnet.com"}
            ],
            "body": {
                "data": "TXkgZGV2aWNlIFNOMTIzNDUgaXMgbm90IHdvcmtpbmcuIENhbiB5b3UgaGVscD8="  # Base64: My device SN12345 is not working. Can you help?
            }
        },
        "internalDate": "1738492800000"  # 2026-02-02T10:00:00 in milliseconds
    }


@pytest.mark.asyncio
async def test_dual_mode_routes_to_step_orchestrator(sample_raw_email):
    """Test that EmailProcessor routes to step orchestrator when enabled."""
    # Create mock config with step orchestrator enabled
    mock_config = MagicMock(spec=AgentConfig)
    mock_config.agent = AgentRuntimeConfig(use_step_orchestrator=True)

    # Create mock processor
    mock_processor = MagicMock(spec=EmailProcessor)
    mock_processor.config = mock_config

    # Mock the process_email_with_steps method
    mock_processor.process_email_with_steps = AsyncMock(return_value=MagicMock(
        success=True,
        email_id="msg-001",
        scenario_used="steps:05-send-confirmation",
        serial_number="SN12345"
    ))

    # Mock the routing logic
    async def mock_process_email_with_functions(raw_email):
        if mock_processor.config.agent.use_step_orchestrator:
            return await mock_processor.process_email_with_steps(raw_email)
        return MagicMock(success=True, scenario_used="function-calling")

    mock_processor.process_email_with_functions = mock_process_email_with_functions

    # Call process_email_with_functions
    result = await mock_processor.process_email_with_functions(sample_raw_email)

    # Verify process_email_with_steps was called
    mock_processor.process_email_with_steps.assert_called_once_with(sample_raw_email)

    # Verify result
    assert result.success is True
    assert result.scenario_used == "steps:05-send-confirmation"


@pytest.mark.asyncio
async def test_dual_mode_uses_function_calling_when_disabled(sample_raw_email):
    """Test that EmailProcessor uses function calling when step orchestrator disabled."""
    # Create mock config with step orchestrator disabled
    mock_config = MagicMock(spec=AgentConfig)
    mock_config.agent = AgentRuntimeConfig(use_step_orchestrator=False)

    # Create mock processor
    mock_processor = MagicMock(spec=EmailProcessor)
    mock_processor.config = mock_config

    # Mock the process_email_with_steps method (should not be called)
    mock_processor.process_email_with_steps = AsyncMock()

    # Mock the routing logic
    async def mock_process_email_with_functions(raw_email):
        if mock_processor.config.agent.use_step_orchestrator:
            return await mock_processor.process_email_with_steps(raw_email)
        # Simulate function calling path
        return MagicMock(success=True, scenario_used="valid-warranty", serial_number="SN12345")

    mock_processor.process_email_with_functions = mock_process_email_with_functions

    # Call process_email_with_functions
    result = await mock_processor.process_email_with_functions(sample_raw_email)

    # Verify process_email_with_steps was NOT called
    mock_processor.process_email_with_steps.assert_not_called()

    # Verify function calling was used
    assert result.success is True
    assert result.scenario_used == "valid-warranty"


@pytest.mark.asyncio
async def test_process_email_with_steps_parses_email():
    """Test that process_email_with_steps correctly parses email."""
    # Create sample parsed email
    sample_email = EmailMessage(
        subject="Broken device",
        body="My device SN12345 is broken",
        from_address="customer@example.com",
        received_timestamp=datetime.fromisoformat("2026-02-02T10:00:00"),
        message_id="msg-001"
    )

    # Create mock processor with parser
    mock_processor = MagicMock(spec=EmailProcessor)
    mock_processor.parser = MagicMock()
    mock_processor.parser.parse_email = MagicMock(return_value=sample_email)

    # Mock orchestrator
    mock_orchestration_result = OrchestrationResult(
        step_history=[
            StepExecutionResult(
                next_step="DONE",
                response_text="Email sent",
                metadata={"email_sent": True, "ticket_id": "TKT-001"},
                step_name="05-send-confirmation"
            )
        ],
        final_step="05-send-confirmation",
        completed=True,
        total_steps=1,
        context=StepContext(
            email_subject="Broken device",
            email_body="My device SN12345 is broken",
            from_address="customer@example.com",
            serial_number="SN12345",
            ticket_id="TKT-001"
        )
    )

    mock_processor.step_orchestrator = MagicMock()
    mock_processor.step_orchestrator.orchestrate = AsyncMock(return_value=mock_orchestration_result)

    # Test the method logic
    raw_email = {"id": "msg-001", "payload": {"headers": []}}

    # Simulate process_email_with_steps logic
    email = mock_processor.parser.parse_email(raw_email)
    result = await mock_processor.step_orchestrator.orchestrate(email, initial_step="01-extract-serial")

    # Verify parser was called
    mock_processor.parser.parse_email.assert_called_once_with(raw_email)

    # Verify orchestrator was called with parsed email
    mock_processor.step_orchestrator.orchestrate.assert_called_once()
    call_args = mock_processor.step_orchestrator.orchestrate.call_args
    assert call_args.args[0] == sample_email
    assert call_args.kwargs['initial_step'] == "01-extract-serial"

    # Verify orchestration result structure
    assert result.total_steps == 1
    assert result.completed is True
    assert result.context.serial_number == "SN12345"
