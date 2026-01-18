"""Tests for signal handling in AgentRunner."""

import asyncio
import signal
import pytest
from unittest.mock import Mock, patch, AsyncMock

from guarantee_email_agent.agent.runner import AgentRunner
from guarantee_email_agent.config.schema import AgentConfig


@pytest.fixture
def mock_config():
    """Create mock agent configuration."""
    config = Mock(spec=AgentConfig)
    config.agent = Mock()
    config.agent.polling_interval_seconds = 1
    return config


@pytest.fixture
def mock_processor():
    """Create mock email processor."""
    processor = Mock()
    processor.gmail_client = Mock()
    processor.gmail_client.connect = AsyncMock()
    processor.gmail_client.close = AsyncMock()
    processor.warranty_client = Mock()
    processor.warranty_client.connect = AsyncMock()
    processor.warranty_client.close = AsyncMock()
    processor.ticketing_client = Mock()
    processor.ticketing_client.connect = AsyncMock()
    processor.ticketing_client.close = AsyncMock()
    return processor


def test_signal_handlers_registered(mock_config, mock_processor):
    """Test signal handlers are registered correctly."""
    runner = AgentRunner(mock_config, mock_processor)
    
    # Mock signal.signal
    with patch('signal.signal') as mock_signal:
        runner.register_signal_handlers()
        
        # Verify all signals registered
        assert mock_signal.call_count == 3
        calls = [call[0] for call in mock_signal.call_args_list]
        assert (signal.SIGTERM, runner._handle_shutdown_signal) in calls
        assert (signal.SIGINT, runner._handle_shutdown_signal) in calls
        assert (signal.SIGHUP, runner._handle_sighup) in calls


def test_handle_sigterm(mock_config, mock_processor):
    """Test SIGTERM handler sets shutdown flag."""
    runner = AgentRunner(mock_config, mock_processor)
    
    assert runner._shutdown_requested is False
    
    # Simulate SIGTERM
    runner._handle_shutdown_signal(signal.SIGTERM, None)
    
    assert runner._shutdown_requested is True


def test_handle_sigint(mock_config, mock_processor):
    """Test SIGINT handler sets shutdown flag."""
    runner = AgentRunner(mock_config, mock_processor)
    
    assert runner._shutdown_requested is False
    
    # Simulate SIGINT
    runner._handle_shutdown_signal(signal.SIGINT, None)
    
    assert runner._shutdown_requested is True


def test_handle_sighup(mock_config, mock_processor):
    """Test SIGHUP handler sets log rotation flag."""
    runner = AgentRunner(mock_config, mock_processor)
    
    assert runner._log_rotation_requested is False
    
    # Simulate SIGHUP
    runner._handle_sighup(signal.SIGHUP, None)
    
    assert runner._log_rotation_requested is True


@pytest.mark.asyncio
async def test_run_loop_exits_on_shutdown_signal(mock_config, mock_processor):
    """Test monitoring loop exits when shutdown signal received."""
    runner = AgentRunner(mock_config, mock_processor)
    
    # Mock poll_inbox to prevent actual polling
    runner.poll_inbox = AsyncMock(return_value=[])
    
    # Set shutdown flag after short delay
    async def set_shutdown():
        await asyncio.sleep(0.1)
        runner._shutdown_requested = True
    
    # Run both tasks concurrently
    await asyncio.gather(
        runner.run(),
        set_shutdown()
    )
    
    # Verify shutdown was triggered
    assert runner._shutdown_requested is True


def test_rotate_logs_closes_file_handlers(mock_config, mock_processor):
    """Test log rotation closes and reopens file handlers."""
    runner = AgentRunner(mock_config, mock_processor)
    
    # Create mock file handler
    import logging
    mock_handler = Mock(spec=logging.FileHandler)
    mock_handler.baseFilename = "/tmp/test.log"
    mock_handler.level = logging.INFO
    mock_handler.formatter = logging.Formatter()
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(mock_handler)
    
    try:
        # Rotate logs
        runner._rotate_logs()
        
        # Verify handler was closed
        mock_handler.close.assert_called_once()
    finally:
        # Clean up
        root_logger.removeHandler(mock_handler)


def test_rotate_logs_handles_errors_gracefully(mock_config, mock_processor):
    """Test log rotation handles errors without crashing."""
    runner = AgentRunner(mock_config, mock_processor)
    
    # Create mock file handler that raises on close
    import logging
    mock_handler = Mock(spec=logging.FileHandler)
    mock_handler.baseFilename = "/tmp/test.log"
    mock_handler.level = logging.INFO
    mock_handler.formatter = logging.Formatter()
    mock_handler.close.side_effect = Exception("Close failed")
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(mock_handler)
    
    try:
        # Rotate logs - should not raise
        runner._rotate_logs()
        
        # Verify close was attempted
        mock_handler.close.assert_called_once()
    finally:
        # Clean up
        root_logger.removeHandler(mock_handler)


@pytest.mark.asyncio
async def test_log_rotation_in_run_loop(mock_config, mock_processor):
    """Test log rotation is triggered during monitoring loop."""
    runner = AgentRunner(mock_config, mock_processor)

    # Mock poll_inbox
    runner.poll_inbox = AsyncMock(return_value=[])

    # Mock _rotate_logs to track calls (don't call original)
    rotate_calls = []
    def mock_rotate():
        rotate_calls.append(True)
    runner._rotate_logs = mock_rotate

    # Set log rotation flag immediately, then shutdown
    runner._log_rotation_requested = True

    # Set shutdown flag after minimal delay to allow one loop iteration
    async def trigger_shutdown():
        await asyncio.sleep(0.05)
        runner._shutdown_requested = True

    # Run both tasks
    await asyncio.gather(
        runner.run(),
        trigger_shutdown()
    )

    # Verify rotation was called
    assert len(rotate_calls) > 0


@pytest.mark.asyncio
async def test_graceful_shutdown_closes_connections(mock_config, mock_processor):
    """Test graceful shutdown closes all MCP connections."""
    runner = AgentRunner(mock_config, mock_processor)

    # Ensure processor clients have close methods
    runner.processor.gmail_client.close = AsyncMock()
    runner.processor.warranty_client.close = AsyncMock()
    runner.processor.ticketing_client.close = AsyncMock()

    # Call graceful shutdown
    await runner._graceful_shutdown()

    # Verify all clients closed
    runner.processor.gmail_client.close.assert_called_once()
    runner.processor.warranty_client.close.assert_called_once()
    runner.processor.ticketing_client.close.assert_called_once()


def test_idempotent_startup_log_message(mock_config, mock_processor):
    """Test idempotent startup message is logged."""
    runner = AgentRunner(mock_config, mock_processor)
    
    # Mock poll_inbox to prevent actual polling
    runner.poll_inbox = AsyncMock(return_value=[])
    runner._shutdown_requested = True  # Exit immediately
    
    # Capture logs
    import logging
    with patch.object(logging.getLogger('guarantee_email_agent.agent.runner'), 'info') as mock_log:
        asyncio.run(runner.run())
        
        # Check for idempotent message
        log_calls = [str(call) for call in mock_log.call_args_list]
        assert any("restart safe, idempotent" in str(call) for call in log_calls)
