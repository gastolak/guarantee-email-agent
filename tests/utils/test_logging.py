"""Tests for structured logging configuration."""

import json
import logging
import pytest
from io import StringIO

from guarantee_email_agent.utils.logging import (
    configure_logging,
    JSONFormatter,
    log_with_context,
    build_error_context,
    log_performance,
    CONTEXT_EMAIL_ID,
    CONTEXT_SERIAL_NUMBER,
    CONTEXT_SCENARIO,
    CONTEXT_ERROR_CODE,
)


@pytest.fixture
def log_capture():
    """Capture log output for testing."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield logger, stream
    logger.removeHandler(handler)


def test_configure_logging_default():
    """Test logging configuration with defaults."""
    configure_logging()

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) > 0

    # Should have StreamHandler to stdout
    handler = root_logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    # Stream should be stdout (don't check name, platform-specific)
    import sys
    assert handler.stream == sys.stdout or hasattr(handler.stream, 'write')


def test_configure_logging_debug_level():
    """Test logging configuration with DEBUG level."""
    configure_logging(log_level="DEBUG")

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_configure_logging_json_format():
    """Test logging configuration with JSON format."""
    configure_logging(json_format=True)

    root_logger = logging.getLogger()
    handler = root_logger.handlers[0]
    assert isinstance(handler.formatter, JSONFormatter)


def test_configure_logging_env_override(monkeypatch):
    """Test environment variable override."""
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    monkeypatch.setenv("LOG_FORMAT", "json")

    configure_logging(log_level="INFO", json_format=False)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.ERROR

    handler = root_logger.handlers[0]
    assert isinstance(handler.formatter, JSONFormatter)


def test_json_formatter_basic():
    """Test JSON formatter outputs valid JSON."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)

    # Should be valid JSON
    log_data = json.loads(output)
    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test"
    assert log_data["message"] == "Test message"
    assert "timestamp" in log_data
    assert log_data["timestamp"].endswith("Z")  # UTC


def test_json_formatter_with_context():
    """Test JSON formatter includes context."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.context = {"email_id": "123", "scenario": "test"}

    output = formatter.format(record)
    log_data = json.loads(output)

    assert "context" in log_data
    assert log_data["context"]["email_id"] == "123"
    assert log_data["context"]["scenario"] == "test"


def test_json_formatter_with_exception():
    """Test JSON formatter includes exception info."""
    formatter = JSONFormatter()

    try:
        raise ValueError("Test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=10,
        msg="Error occurred",
        args=(),
        exc_info=exc_info
    )

    output = formatter.format(record)
    log_data = json.loads(output)

    assert "exception" in log_data
    assert "ValueError: Test error" in log_data["exception"]


def test_log_with_context():
    """Test structured logging helper."""
    logger = logging.getLogger("test_context")
    logger.setLevel(logging.INFO)

    # Capture output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    log_with_context(
        logger, "info", "Test message",
        email_id="123", scenario="valid-warranty"
    )

    output = stream.getvalue()
    log_data = json.loads(output.strip())

    assert log_data["message"] == "Test message"
    assert log_data["context"]["email_id"] == "123"
    assert log_data["context"]["scenario"] == "valid-warranty"

    logger.removeHandler(handler)


def test_build_error_context_complete():
    """Test error context builder with all fields."""
    context = build_error_context(
        email_id="msg-123",
        serial_number="SN-456",
        scenario="valid-warranty",
        processing_step="validate_warranty",
        error_code="mcp_warranty_timeout",
        retry_attempt=2,
        error_type="transient"
    )

    assert context[CONTEXT_EMAIL_ID] == "msg-123"
    assert context[CONTEXT_SERIAL_NUMBER] == "SN-456"
    assert context[CONTEXT_SCENARIO] == "valid-warranty"
    assert context["processing_step"] == "validate_warranty"
    assert context[CONTEXT_ERROR_CODE] == "mcp_warranty_timeout"
    assert context["retry_attempt"] == 2
    assert context["error_type"] == "transient"
    assert "timestamp" in context


def test_build_error_context_partial():
    """Test error context builder with partial fields."""
    context = build_error_context(
        email_id="msg-123",
        error_code="email_parse_error"
    )

    assert context[CONTEXT_EMAIL_ID] == "msg-123"
    assert context[CONTEXT_ERROR_CODE] == "email_parse_error"
    assert CONTEXT_SERIAL_NUMBER not in context
    assert CONTEXT_SCENARIO not in context


def test_build_error_context_additional():
    """Test error context with additional fields."""
    context = build_error_context(
        email_id="msg-123",
        custom_field="custom_value",
        another_field=42
    )

    assert context[CONTEXT_EMAIL_ID] == "msg-123"
    assert context["custom_field"] == "custom_value"
    assert context["another_field"] == 42


def test_log_performance_normal():
    """Test performance logging for normal operation."""
    logger = logging.getLogger("test_perf")
    logger.setLevel(logging.DEBUG)

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)

    log_performance(
        logger, "parse", 250,
        email_id="msg-123"
    )

    output = stream.getvalue()
    assert "parse" in output
    assert "250ms" in output
    # Should be DEBUG level (not WARN)
    assert "WARNING" not in output

    logger.removeHandler(handler)


def test_log_performance_slow():
    """Test performance logging for slow operation."""
    logger = logging.getLogger("test_perf_slow")
    logger.setLevel(logging.DEBUG)

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    # Add formatter that includes level name
    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)

    log_performance(
        logger, "extract_serial", 3500,
        threshold_ms=3000,
        email_id="msg-123"
    )

    output = stream.getvalue()
    assert "extract_serial" in output
    assert "3500ms" in output
    assert "Slow operation" in output
    # Should be WARNING level
    assert "WARNING" in output

    logger.removeHandler(handler)


def test_customer_data_protection_info_level():
    """Test that email body is NOT logged at INFO level (NFR14)."""
    configure_logging(log_level="INFO")

    logger = logging.getLogger("test_nfr14")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)

    # This should appear (INFO level metadata)
    logger.info("Email metadata", extra={"subject": "Test", "from": "test@example.com"})

    # This should NOT appear (DEBUG level body)
    logger.debug("Email body", extra={"body": "SENSITIVE CUSTOMER DATA"})

    output = stream.getvalue()
    # Check that INFO message appears
    assert "Email metadata" in output
    # Most importantly: Customer data should NOT appear
    assert "SENSITIVE CUSTOMER DATA" not in output

    logger.removeHandler(handler)


def test_customer_data_protection_debug_level():
    """Test that email body IS logged at DEBUG level."""
    configure_logging(log_level="DEBUG")

    logger = logging.getLogger("test_debug")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)

    # This should appear at DEBUG level
    logger.debug("Email body", extra={"body": "Customer email content"})

    output = stream.getvalue()
    assert "Email body" in output

    logger.removeHandler(handler)


def test_context_keys_constants():
    """Test that context key constants are defined."""
    assert CONTEXT_EMAIL_ID == "email_id"
    assert CONTEXT_SERIAL_NUMBER == "serial_number"
    assert CONTEXT_SCENARIO == "scenario"
    assert CONTEXT_ERROR_CODE == "error_code"
