"""Tests for StepOrchestrator - the core state machine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from guarantee_email_agent.orchestrator.step_orchestrator import StepOrchestrator
from guarantee_email_agent.orchestrator.models import StepContext, StepExecutionResult
from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.config.schema import AgentConfig


@pytest.fixture
def mock_config():
    """Mock AgentConfig for testing."""
    config = MagicMock(spec=AgentConfig)
    config.llm.timeout_seconds = 15
    config.llm.max_tokens = 8192
    config.llm.model = "claude-sonnet-4-5"
    config.llm.temperature = 0
    return config


@pytest.fixture
def sample_email():
    """Sample email message for testing."""
    from datetime import datetime
    return EmailMessage(
        subject="Broken device - need warranty",
        body="My device SN12345 is not working. Can you help?",
        from_address="customer@example.com",
        received_timestamp=datetime.fromisoformat("2026-02-02T10:00:00"),
        message_id="msg-001"
    )


@pytest.mark.asyncio
async def test_orchestrator_initialization(mock_config):
    """Test StepOrchestrator initializes correctly."""
    orchestrator = StepOrchestrator(
        config=mock_config,
        main_instruction_body="Main instruction content"
    )

    assert orchestrator.config == mock_config
    assert orchestrator.main_instruction_body == "Main instruction content"
    assert orchestrator.max_steps == 10  # Circuit breaker


@pytest.mark.asyncio
async def test_orchestrator_single_step_execution(mock_config, sample_email):
    """Test orchestrator executes a single step correctly."""
    orchestrator = StepOrchestrator(
        config=mock_config,
        main_instruction_body="Main instruction"
    )

    # Mock execute_step to return DONE immediately
    with patch.object(orchestrator, 'execute_step', new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = StepExecutionResult(
            next_step="DONE",
            response_text="Email sent",
            metadata={"status": "complete"},
            step_name="05-send-confirmation"
        )

        # Run orchestration starting from step 05
        result = await orchestrator.orchestrate(
            email=sample_email,
            initial_step="05-send-confirmation"
        )

        # Verify result
        assert result.final_step == "05-send-confirmation"
        assert len(result.step_history) == 1
        assert result.step_history[0].step_name == "05-send-confirmation"
        assert result.completed is True


@pytest.mark.asyncio
async def test_orchestrator_multi_step_flow(mock_config, sample_email):
    """Test orchestrator executes multi-step flow."""
    orchestrator = StepOrchestrator(
        config=mock_config,
        main_instruction_body="Main instruction"
    )

    # Mock execute_step to simulate 3-step flow: 01 -> 02 -> 03a -> DONE
    step_results = [
        StepExecutionResult(
            next_step="02-check-warranty",
            response_text="Serial found: SN12345",
            metadata={"serial": "SN12345"},
            step_name="01-extract-serial"
        ),
        StepExecutionResult(
            next_step="03a-valid-warranty",
            response_text="Warranty is valid",
            metadata={"warranty_status": "valid"},
            step_name="02-check-warranty"
        ),
        StepExecutionResult(
            next_step="DONE",
            response_text="Ticket created",
            metadata={"ticket_id": "TKT-001"},
            step_name="03a-valid-warranty"
        ),
    ]

    with patch.object(orchestrator, 'execute_step', new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = step_results

        result = await orchestrator.orchestrate(
            email=sample_email,
            initial_step="01-extract-serial"
        )

        # Verify 3 steps executed
        assert len(result.step_history) == 3
        assert result.step_history[0].step_name == "01-extract-serial"
        assert result.step_history[1].step_name == "02-check-warranty"
        assert result.step_history[2].step_name == "03a-valid-warranty"
        assert result.final_step == "03a-valid-warranty"
        assert result.completed is True


@pytest.mark.asyncio
async def test_orchestrator_infinite_loop_prevention(mock_config, sample_email):
    """Test orchestrator prevents infinite loops with circuit breaker."""
    orchestrator = StepOrchestrator(
        config=mock_config,
        main_instruction_body="Main instruction"
    )

    # Mock execute_step to always return next_step (never DONE)
    with patch.object(orchestrator, 'execute_step', new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = StepExecutionResult(
            next_step="01-extract-serial",  # Loop back to same step
            response_text="Looping",
            metadata={},
            step_name="01-extract-serial"
        )

        # Should hit max_steps circuit breaker
        with pytest.raises(Exception) as exc_info:
            await orchestrator.orchestrate(
                email=sample_email,
                initial_step="01-extract-serial"
            )

        assert "max_steps" in str(exc_info.value).lower() or "circuit breaker" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_orchestrator_context_passing(mock_config, sample_email):
    """Test orchestrator correctly passes context between steps."""
    orchestrator = StepOrchestrator(
        config=mock_config,
        main_instruction_body="Main instruction"
    )

    captured_contexts = []

    async def mock_execute_step(step_name, context):
        """Capture context for verification."""
        # Capture snapshot of context before modification
        from dataclasses import replace
        context_snapshot = replace(context)
        captured_contexts.append((step_name, context_snapshot))

        if step_name == "01-extract-serial":
            # Update context with serial
            context.serial_number = "SN12345"
            return StepExecutionResult(
                next_step="02-check-warranty",
                response_text="Serial found",
                metadata={"serial": "SN12345"},
                step_name="01-extract-serial"
            )
        elif step_name == "02-check-warranty":
            # Update context with warranty data
            context.warranty_data = {"status": "valid"}
            return StepExecutionResult(
                next_step="DONE",
                response_text="Warranty checked",
                metadata={},
                step_name="02-check-warranty"
            )

    with patch.object(orchestrator, 'execute_step', new=mock_execute_step):
        result = await orchestrator.orchestrate(
            email=sample_email,
            initial_step="01-extract-serial"
        )

        # Verify context was passed and updated between steps
        assert len(captured_contexts) == 2

        # Step 1 context: no serial yet
        step1_name, step1_context = captured_contexts[0]
        assert step1_name == "01-extract-serial"
        assert step1_context.serial_number is None

        # Step 2 context: serial from step 1
        step2_name, step2_context = captured_contexts[1]
        assert step2_name == "02-check-warranty"
        assert step2_context.serial_number == "SN12345"
