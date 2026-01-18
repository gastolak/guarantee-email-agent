"""Tests for agent runner with inbox monitoring and graceful shutdown."""

import asyncio
import signal
import pytest
from unittest.mock import AsyncMock, Mock, patch

from guarantee_email_agent.agent.runner import AgentRunner
from guarantee_email_agent.config.schema import (
    AgentConfig,
    AgentRuntimeConfig,
    InstructionsConfig,
    SecretsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
    LLMConfig,
)
from guarantee_email_agent.email.processor_models import ProcessingResult


@pytest.fixture
def mock_config():
    """Create a mock agent config for testing with Gemini provider."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="gmail://test"),
            warranty_api=MCPConnectionConfig(connection_string="warranty://test"),
            ticketing_system=MCPConnectionConfig(connection_string="ticket://test"),
        ),
        instructions=InstructionsConfig(
            main="main.md",
            scenarios=("test",),
            scenarios_dir="scenarios",
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(),
        llm=LLMConfig(
            provider="gemini",
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=8192,
            timeout_seconds=15
        ),
        secrets=SecretsConfig(
            anthropic_api_key=None,
            gemini_api_key="test-gemini-key",
            gmail_api_key="gmail-key",
            warranty_api_key="warranty-key",
            ticketing_api_key="ticket-key",
        ),
        agent=AgentRuntimeConfig(polling_interval_seconds=1),  # Fast for testing
    )


@pytest.fixture
def mock_processor():
    """Create a mock email processor."""
    processor = Mock()
    processor.gmail_client = Mock()
    processor.gmail_client.get_unread_emails = AsyncMock(return_value=[])
    processor.gmail_client.close = AsyncMock()
    processor.warranty_client = Mock()
    processor.warranty_client.close = AsyncMock()
    processor.ticketing_client = Mock()
    processor.ticketing_client.close = AsyncMock()
    processor.process_email = AsyncMock(return_value=ProcessingResult(
        success=True,
        email_id="test-123",
        scenario_used="valid-warranty",
        serial_number="SN123",
        warranty_status="valid",
        response_sent=True,
        ticket_created=True,
        ticket_id="TICK-123",
        processing_time_ms=100,
        error_message=None,
        failed_step=None
    ))
    return processor


def test_agent_runner_initialization(mock_config, mock_processor):
    """Test AgentRunner initializes correctly."""
    runner = AgentRunner(mock_config, mock_processor)

    assert runner.config == mock_config
    assert runner.processor == mock_processor
    assert runner.polling_interval == 1  # From mock config
    assert runner._shutdown_requested is False
    assert runner._emails_processed == 0


def test_register_signal_handlers(mock_config, mock_processor):
    """Test signal handlers registration."""
    runner = AgentRunner(mock_config, mock_processor)

    with patch('signal.signal') as mock_signal:
        runner.register_signal_handlers()

        # Should register SIGTERM and SIGINT
        assert mock_signal.call_count == 2
        calls = [call[0] for call in mock_signal.call_args_list]
        assert (signal.SIGTERM, runner._handle_shutdown_signal) in calls
        assert (signal.SIGINT, runner._handle_shutdown_signal) in calls


def test_handle_shutdown_signal(mock_config, mock_processor):
    """Test shutdown signal handler sets shutdown flag."""
    runner = AgentRunner(mock_config, mock_processor)

    assert runner._shutdown_requested is False

    # Simulate SIGTERM
    runner._handle_shutdown_signal(signal.SIGTERM, None)

    assert runner._shutdown_requested is True


@pytest.mark.asyncio
async def test_poll_inbox_no_emails(mock_config, mock_processor):
    """Test polling inbox returns empty list when no emails."""
    runner = AgentRunner(mock_config, mock_processor)

    mock_processor.gmail_client.get_unread_emails = AsyncMock(return_value=[])

    emails = await runner.poll_inbox()

    assert emails == []
    mock_processor.gmail_client.get_unread_emails.assert_called_once()


@pytest.mark.asyncio
async def test_poll_inbox_with_emails(mock_config, mock_processor):
    """Test polling inbox returns emails when available."""
    runner = AgentRunner(mock_config, mock_processor)

    test_emails = [
        {"id": "1", "subject": "Test 1"},
        {"id": "2", "subject": "Test 2"},
    ]
    mock_processor.gmail_client.get_unread_emails = AsyncMock(return_value=test_emails)

    emails = await runner.poll_inbox()

    assert emails == test_emails
    assert len(emails) == 2


@pytest.mark.asyncio
async def test_poll_inbox_error_handling(mock_config, mock_processor):
    """Test polling inbox handles errors gracefully."""
    runner = AgentRunner(mock_config, mock_processor)

    # Simulate error
    mock_processor.gmail_client.get_unread_emails = AsyncMock(
        side_effect=Exception("Gmail API error")
    )

    # Should return empty list instead of crashing
    emails = await runner.poll_inbox()

    assert emails == []


@pytest.mark.asyncio
async def test_process_inbox_emails_success(mock_config, mock_processor):
    """Test processing multiple emails concurrently."""
    runner = AgentRunner(mock_config, mock_processor)

    test_emails = [
        {"id": "1", "subject": "Test 1"},
        {"id": "2", "subject": "Test 2"},
    ]

    mock_processor.process_email = AsyncMock(return_value=ProcessingResult(
        success=True,
        email_id="test",
        scenario_used="valid-warranty",
        serial_number="SN123",
        warranty_status="valid",
        response_sent=True,
        ticket_created=True,
        ticket_id="TICK-123",
        processing_time_ms=100,
        error_message=None,
        failed_step=None
    ))

    results = await runner.process_inbox_emails(test_emails)

    assert len(results) == 2
    assert mock_processor.process_email.call_count == 2
    assert runner._emails_processed == 2
    assert runner._errors_count == 0


@pytest.mark.asyncio
async def test_process_inbox_emails_with_failures(mock_config, mock_processor):
    """Test processing emails tracks failures."""
    runner = AgentRunner(mock_config, mock_processor)

    test_emails = [
        {"id": "1", "subject": "Test 1"},
        {"id": "2", "subject": "Test 2"},
    ]

    # First succeeds, second fails
    mock_processor.process_email = AsyncMock(side_effect=[
        ProcessingResult(success=True, email_id="1", scenario_used="test", serial_number="SN1", warranty_status="valid",
                        response_sent=True, ticket_created=True, ticket_id="T1", processing_time_ms=100, error_message=None, failed_step=None),
        ProcessingResult(success=False, email_id="2", scenario_used="error", serial_number=None, warranty_status=None,
                        response_sent=False, ticket_created=False, ticket_id=None, processing_time_ms=50, error_message="Test error", failed_step="parsing"),
    ])

    results = await runner.process_inbox_emails(test_emails)

    assert len(results) == 2
    assert runner._emails_processed == 2
    assert runner._errors_count == 1  # One failure
    assert runner._consecutive_errors == 1


@pytest.mark.asyncio
async def test_process_inbox_emails_empty_list(mock_config, mock_processor):
    """Test processing empty email list."""
    runner = AgentRunner(mock_config, mock_processor)

    results = await runner.process_inbox_emails([])

    assert results == []
    mock_processor.process_email.assert_not_called()


@pytest.mark.asyncio
async def test_run_shutdown_immediately(mock_config, mock_processor):
    """Test run loop exits immediately when shutdown requested."""
    runner = AgentRunner(mock_config, mock_processor)
    runner._shutdown_requested = True  # Request shutdown before starting

    mock_processor.gmail_client.get_unread_emails = AsyncMock(return_value=[])

    await runner.run()

    # Should exit immediately without polling
    mock_processor.gmail_client.get_unread_emails.assert_not_called()


@pytest.mark.asyncio
async def test_run_shutdown_after_one_iteration(mock_config, mock_processor):
    """Test run loop exits after processing one iteration."""
    runner = AgentRunner(mock_config, mock_processor)

    mock_processor.gmail_client.get_unread_emails = AsyncMock(return_value=[])

    # Set shutdown flag after short delay
    async def shutdown_after_delay():
        await asyncio.sleep(0.5)
        runner._shutdown_requested = True

    # Run both tasks concurrently
    await asyncio.gather(
        runner.run(),
        shutdown_after_delay()
    )

    # Should have polled at least once
    assert mock_processor.gmail_client.get_unread_emails.called


@pytest.mark.asyncio
async def test_graceful_shutdown_cleanup(mock_config, mock_processor):
    """Test graceful shutdown closes all connections."""
    runner = AgentRunner(mock_config, mock_processor)

    await runner._graceful_shutdown()

    # Should close all MCP connections
    mock_processor.gmail_client.close.assert_called_once()
    mock_processor.warranty_client.close.assert_called_once()
    mock_processor.ticketing_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_connections_handles_errors(mock_config, mock_processor):
    """Test cleanup handles connection close errors gracefully."""
    runner = AgentRunner(mock_config, mock_processor)

    # Simulate error during cleanup
    mock_processor.gmail_client.close = AsyncMock(side_effect=Exception("Close failed"))

    # Should not raise exception
    await runner._cleanup_connections()

    # Should still attempt to close other connections
    mock_processor.warranty_client.close.assert_called_once()
    mock_processor.ticketing_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_consecutive_error_tracking(mock_config, mock_processor):
    """Test runner tracks consecutive errors."""
    runner = AgentRunner(mock_config, mock_processor)

    test_emails = [{"id": "1", "subject": "Test"}]

    # Simulate multiple failures
    mock_processor.process_email = AsyncMock(return_value=ProcessingResult(
        success=False,
        email_id="1",
        scenario_used="error",
        serial_number=None,
        warranty_status=None,
        response_sent=False,
        ticket_created=False,
        ticket_id=None,
        processing_time_ms=50,
        error_message="Test error",
        failed_step="parsing"
    ))

    # Process same email multiple times to trigger consecutive errors
    for _ in range(10):
        await runner.process_inbox_emails(test_emails)

    # Should track consecutive errors
    assert runner._consecutive_errors == 10
    assert runner._errors_count == 10
