"""Structured logging configuration for warranty email agent.

Implements:
- Structured logging with Python logging module
- JSON formatter for production machine-readable logs
- Customer data protection (NFR14): email body ONLY at DEBUG level
- Stdout-only logging (NFR16): stateless, no file handlers
- Context enrichment for troubleshooting (NFR25)
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Standard context keys for consistency across codebase
CONTEXT_EMAIL_ID = "email_id"
CONTEXT_SERIAL_NUMBER = "serial_number"
CONTEXT_SCENARIO = "scenario"
CONTEXT_PROCESSING_STEP = "processing_step"
CONTEXT_ERROR_CODE = "error_code"
CONTEXT_RETRY_ATTEMPT = "retry_attempt"
CONTEXT_PROCESSING_TIME_MS = "processing_time_ms"
CONTEXT_WARRANTY_STATUS = "warranty_status"
CONTEXT_STEP_DURATION_MS = "step_duration_ms"
CONTEXT_FAILED_API = "failed_api"
CONTEXT_DEGRADATION_TYPE = "degradation_type"


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production machine-readable logs.

    Formats log records as single-line JSON with:
    - timestamp (ISO 8601 UTC)
    - level (DEBUG, INFO, WARNING, ERROR)
    - logger (module name)
    - message (log message)
    - context (structured data from extra dict)
    - exception (stack trace if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record from logging module

        Returns:
            Single-line JSON string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context from extra dict
        if hasattr(record, "context"):
            log_data["context"] = record.context
        else:
            # Collect any extra attributes as context
            context = {}
            # Exclude standard LogRecord attributes
            standard_attrs = {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info", "taskName"
            }
            for key, value in record.__dict__.items():
                if key not in standard_attrs:
                    context[key] = value
            if context:
                log_data["context"] = context

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = False
) -> None:
    """Configure application logging.

    Configures Python logging with:
    - Structured format (text or JSON)
    - Stdout-only output (NFR16: stateless)
    - Environment variable overrides

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR). Default: INFO
        json_format: Use JSON format (True) or text format (False). Default: False

    Environment Variables:
        LOG_LEVEL: Override log_level parameter
        LOG_FORMAT: Override json_format ("json" or "text")

    Example:
        >>> configure_logging(log_level="INFO", json_format=False)
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Test", extra={"key": "value"})
    """
    # Check environment variables (take precedence)
    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    log_format_env = os.getenv("LOG_FORMAT", "text" if not json_format else "json")
    json_format = log_format_env.lower() == "json"

    # Validate log level
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
    if log_level not in valid_levels:
        log_level = "INFO"

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stdout handler (NFR16: logs to stdout only, no files)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level))

    # Set formatter based on format preference
    if json_format:
        formatter = JSONFormatter()
    else:
        # Text format with timestamp, level, logger, message
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Log configuration (using extra for JSON compatibility)
    root_logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_format": "json" if json_format else "text",
            "output": "stdout"
        }
    )


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any
) -> None:
    """Log message with structured context.

    Helper function for consistent structured logging across codebase.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error)
        message: Log message
        **context: Context key-value pairs for structured logging

    Example:
        >>> log_with_context(
        ...     logger, "info", "Email received",
        ...     email_id="123", subject="Warranty inquiry"
        ... )
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra={"context": context})


def build_error_context(
    email_id: Optional[str] = None,
    serial_number: Optional[str] = None,
    scenario: Optional[str] = None,
    processing_step: Optional[str] = None,
    error_code: Optional[str] = None,
    retry_attempt: Optional[int] = None,
    error_type: Optional[str] = None,
    **additional: Any
) -> Dict[str, Any]:
    """Build error context dictionary for structured logging.

    Creates standardized error context with common fields for
    troubleshooting and monitoring.

    Args:
        email_id: Email message ID
        serial_number: Product serial number (if extracted)
        scenario: Detected scenario name
        processing_step: Step where error occurred
        error_code: Error code (format: component_error_type)
        retry_attempt: Retry attempt number (1-indexed)
        error_type: "transient" or "permanent"
        **additional: Additional context fields

    Returns:
        Dictionary with error context

    Example:
        >>> context = build_error_context(
        ...     email_id="msg-123",
        ...     serial_number="SN-456",
        ...     scenario="valid-warranty",
        ...     processing_step="validate_warranty",
        ...     error_code="mcp_warranty_timeout",
        ...     error_type="transient",
        ...     retry_attempt=2
        ... )
    """
    context = {}

    if email_id:
        context[CONTEXT_EMAIL_ID] = email_id
    if serial_number:
        context[CONTEXT_SERIAL_NUMBER] = serial_number
    if scenario:
        context[CONTEXT_SCENARIO] = scenario
    if processing_step:
        context[CONTEXT_PROCESSING_STEP] = processing_step
    if error_code:
        context[CONTEXT_ERROR_CODE] = error_code
    if retry_attempt is not None:
        context[CONTEXT_RETRY_ATTEMPT] = retry_attempt
    if error_type:
        context["error_type"] = error_type

    # Add timestamp
    context["timestamp"] = datetime.utcnow().isoformat() + "Z"

    # Add any additional context
    context.update(additional)

    return context


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_ms: int,
    threshold_ms: Optional[int] = None,
    **context: Any
) -> None:
    """Log operation performance with optional slow operation warning.

    Args:
        logger: Logger instance
        operation: Operation name (e.g., "parse", "extract_serial")
        duration_ms: Operation duration in milliseconds
        threshold_ms: Slow operation threshold (log WARNING if exceeded)
        **context: Additional context

    Example:
        >>> log_performance(
        ...     logger, "extract_serial", 3500,
        ...     threshold_ms=3000,
        ...     email_id="msg-123"
        ... )
    """
    perf_context = {
        "operation": operation,
        "duration_ms": duration_ms,
        **context
    }

    if threshold_ms and duration_ms > threshold_ms:
        perf_context["threshold_ms"] = threshold_ms
        logger.warning(
            f"Slow operation: {operation} took {duration_ms}ms (threshold: {threshold_ms}ms)",
            extra=perf_context
        )
    else:
        logger.debug(
            f"Operation {operation} completed in {duration_ms}ms",
            extra=perf_context
        )
