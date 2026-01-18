"""Tests for stdout/stderr separation in logging."""

import logging
import sys
from io import StringIO
import pytest

from guarantee_email_agent.utils.logging import (
    StdoutFilter,
    configure_logging,
    setup_file_logging
)


def test_stdout_filter_allows_info():
    """Test StdoutFilter allows INFO level."""
    filter = StdoutFilter()
    
    # Create INFO record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    assert filter.filter(record) is True


def test_stdout_filter_allows_debug():
    """Test StdoutFilter allows DEBUG level."""
    filter = StdoutFilter()
    
    # Create DEBUG record
    record = logging.LogRecord(
        name="test",
        level=logging.DEBUG,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    assert filter.filter(record) is True


def test_stdout_filter_blocks_warning():
    """Test StdoutFilter blocks WARNING level."""
    filter = StdoutFilter()
    
    # Create WARNING record
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    assert filter.filter(record) is False


def test_stdout_filter_blocks_error():
    """Test StdoutFilter blocks ERROR level."""
    filter = StdoutFilter()
    
    # Create ERROR record
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    assert filter.filter(record) is False


def test_stdout_filter_blocks_critical():
    """Test StdoutFilter blocks CRITICAL level."""
    filter = StdoutFilter()
    
    # Create CRITICAL record
    record = logging.LogRecord(
        name="test",
        level=logging.CRITICAL,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    assert filter.filter(record) is False


def test_configure_logging_with_stderr_separation():
    """Test configure_logging creates stdout and stderr handlers."""
    # Capture stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        # Configure logging with separation
        configure_logging(
            log_level="INFO",
            json_format=False,
            use_stderr_separation=True
        )
        
        # Get logger
        logger = logging.getLogger("test_logger")
        
        # Log INFO message
        logger.info("Info message")
        stdout_content = sys.stdout.getvalue()
        stderr_content = sys.stderr.getvalue()
        
        # INFO should be in stdout
        assert "Info message" in stdout_content
        # INFO should NOT be in stderr
        assert "Info message" not in stderr_content
        
        # Flush handlers before clearing buffers
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Clear buffers
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        # Update handlers to use new StringIO objects
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                if hasattr(handler, 'stream'):
                    # Check if this is stdout or stderr handler
                    if handler.level == logging.WARNING:
                        handler.stream = sys.stderr
                    else:
                        handler.stream = sys.stdout

        # Log ERROR message
        logger.error("Error message")

        # Flush handlers
        for handler in logging.getLogger().handlers:
            handler.flush()

        stdout_content = sys.stdout.getvalue()
        stderr_content = sys.stderr.getvalue()

        # ERROR should be in stderr
        assert "Error message" in stderr_content
        # ERROR should NOT be in stdout
        assert "Error message" not in stdout_content
    
    finally:
        # Restore original stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Clean up logger handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()


def test_configure_logging_without_stderr_separation():
    """Test configure_logging without separation (legacy mode)."""
    # Capture stdout
    old_stdout = sys.stdout
    
    try:
        sys.stdout = StringIO()
        
        # Configure logging without separation
        configure_logging(
            log_level="INFO",
            json_format=False,
            use_stderr_separation=False
        )
        
        # Get logger
        logger = logging.getLogger("test_logger")
        
        # Log INFO and ERROR
        logger.info("Info message")
        logger.error("Error message")
        
        stdout_content = sys.stdout.getvalue()
        
        # Both should be in stdout
        assert "Info message" in stdout_content
        assert "Error message" in stdout_content
    
    finally:
        # Restore original stdout
        sys.stdout = old_stdout
        
        # Clean up logger handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()


def test_configure_logging_respects_log_level():
    """Test configure_logging respects log level setting."""
    # Capture stdout
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        # Configure logging with WARNING level
        configure_logging(
            log_level="WARNING",
            json_format=False,
            use_stderr_separation=True
        )
        
        # Get logger
        logger = logging.getLogger("test_logger")
        
        # Log at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        
        stdout_content = sys.stdout.getvalue()
        stderr_content = sys.stderr.getvalue()
        
        # DEBUG and INFO should NOT appear (level is WARNING)
        assert "Debug message" not in stdout_content
        assert "Info message" not in stdout_content
        
        # WARNING should appear in stderr
        assert "Warning message" in stderr_content
    
    finally:
        # Restore original stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Clean up logger handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()


def test_setup_file_logging_creates_directory(tmp_path):
    """Test setup_file_logging creates log directory."""
    log_file = tmp_path / "logs" / "agent.log"
    
    # Setup file logging
    setup_file_logging(str(log_file))
    
    # Verify directory created
    assert log_file.parent.exists()
    
    # Clean up
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)


def test_setup_file_logging_writes_to_file(tmp_path):
    """Test setup_file_logging writes logs to file."""
    log_file = tmp_path / "agent.log"

    # Set root logger level to ensure messages are processed
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Setup file logging
    setup_file_logging(str(log_file))

    # Log a message
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    logger.info("File log message")

    # Flush all handlers to ensure write
    for handler in logging.getLogger().handlers:
        handler.flush()

    # Verify written to file
    assert log_file.exists()
    content = log_file.read_text()
    assert "File log message" in content

    # Clean up
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)


def test_configure_logging_with_file_path(tmp_path):
    """Test configure_logging with file_path creates file handler."""
    log_file = tmp_path / "agent.log"
    
    # Configure with file path
    configure_logging(
        log_level="INFO",
        json_format=False,
        file_path=str(log_file),
        use_stderr_separation=True
    )
    
    # Log a message
    logger = logging.getLogger("test_logger")
    logger.info("Test message")
    
    # Verify written to file
    assert log_file.exists()
    content = log_file.read_text()
    assert "Test message" in content
    
    # Clean up
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)
    root_logger.handlers.clear()
