# Story 3.6: Structured Logging and Graceful Degradation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want comprehensive structured logging and graceful degradation for edge cases,
So that I can troubleshoot issues quickly and the agent handles unexpected scenarios without crashing.

## Acceptance Criteria

**Given** The complete agent from Stories 3.1-3.5 exists
**When** The agent processes emails and encounters issues

**Then - Structured Logging:**
**And** Logging configured in `src/guarantee_email_agent/utils/logging.py`
**And** Uses Python's logging module with structured format
**And** Log levels: DEBUG, INFO, WARN, ERROR (no TRACE or custom levels)
**And** Structured context via extra dict (not string interpolation)
**And** Log format includes: timestamp, level, logger name, message, context
**And** Customer email body logged ONLY at DEBUG level (NFR14)
**And** Customer metadata (subject, from) logged at INFO level
**And** Serial numbers and warranty status logged at INFO level
**And** All errors logged at ERROR level with exc_info=True for stack traces
**And** Logs include sufficient context for troubleshooting (NFR25)
**And** Processing events logged: email received, serial extracted, scenario detected, warranty validated, response sent, ticket created
**And** Log output to stdout (not files per NFR16 stateless)
**And** JSON log format option for production (machine-readable)

**Then - Graceful Degradation:**
**And** Graceful degradation handler in `src/guarantee_email_agent/email/graceful_handler.py`
**And** Handles out-of-scope emails: non-warranty inquiries, billing, spam
**And** Handles missing information: unclear intent, partial data
**And** Handles API failures: LLM timeout, warranty API down, ticketing unavailable
**And** Handles edge cases: malformed emails, extraction failures, ambiguous scenarios
**And** Uses graceful-degradation scenario instruction (from Story 3.2)
**And** Response tone: polite, helpful, guides customer to next steps
**And** Never crashes on unexpected input (FR18, NFR5)
**And** Logs all degradation triggers with context
**And** Degradation events tracked in metrics for monitoring
**And** Customer receives response even in degradation cases

**Then - Error Context Enrichment:**
**And** All error logs include: email_id, serial_number (if extracted), scenario, processing_step
**And** Error codes follow pattern: `{component}_{error_type}` (e.g., "mcp_warranty_timeout")
**And** Transient vs permanent errors distinguished in logs
**And** Retry attempts logged with attempt number
**And** Circuit breaker state changes logged
**And** Failed step explicitly named in error logs

**Then - Performance Logging:**
**And** Processing time logged for each email (target: <60s per NFR7)
**And** Step timing logged: parse, extract, detect, validate, generate, send, ticket
**And** Slow operations logged at WARN level (>5s for single step)
**And** LLM call latency logged
**And** MCP API call latency logged
**And** P95 latency tracked for monitoring

## Tasks / Subtasks

### Logging Configuration

- [ ] Create logging utility module (AC: logging configured)
  - [ ] Create `src/guarantee_email_agent/utils/logging.py`
  - [ ] Import Python logging module
  - [ ] Create logging configuration function
  - [ ] Define log levels: DEBUG, INFO, WARN, ERROR
  - [ ] Configure log format
  - [ ] Add structured logging helpers

- [ ] Implement structured log format (AC: structured context via extra dict)
  - [ ] Create `configure_logging(log_level: str = "INFO", json_format: bool = False)` function
  - [ ] Text format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s | %(context)s`
  - [ ] JSON format: `{"timestamp": "...", "level": "...", "logger": "...", "message": "...", "context": {...}}`
  - [ ] Parse extra dict into context field
  - [ ] Configure output to stdout (not files)
  - [ ] Support LOG_LEVEL environment variable

- [ ] Add JSON formatter for production (AC: JSON log format option)
  - [ ] Create `JSONFormatter` class extending logging.Formatter
  - [ ] Override format() method to output JSON
  - [ ] Include all standard fields: timestamp, level, logger, message
  - [ ] Include context from extra dict
  - [ ] Include exception info if present
  - [ ] Ensure single-line JSON per log entry

- [ ] Implement structured logging helpers (AC: structured context)
  - [ ] Create `log_with_context(logger, level, message, **context)` helper
  - [ ] Helper adds context to extra dict automatically
  - [ ] Example: `log_with_context(logger, "info", "Email received", email_id=123, subject="...")`
  - [ ] Ensure context keys are consistent across codebase
  - [ ] Document standard context keys

- [ ] Configure log levels per component
  - [ ] Default: INFO level for production
  - [ ] DEBUG level option for development/troubleshooting
  - [ ] WARN level for potential issues (slow operations, high errors)
  - [ ] ERROR level for failures with stack traces
  - [ ] Configure via environment variable: LOG_LEVEL

- [ ] Add customer data protection (AC: email body ONLY at DEBUG)
  - [ ] Audit all logging statements across codebase
  - [ ] Ensure email body never logged at INFO/WARN/ERROR
  - [ ] Customer email metadata (subject, from) allowed at INFO
  - [ ] Serial numbers and warranty status allowed at INFO
  - [ ] Document NFR14 compliance in logging module
  - [ ] Add code comments where body is logged at DEBUG

### Graceful Degradation Handler

- [ ] Create graceful degradation module (AC: handler for edge cases)
  - [ ] Create `src/guarantee_email_agent/email/graceful_handler.py`
  - [ ] Import EmailMessage, ProcessingResult, scenario components
  - [ ] Create `GracefulDegradationHandler` class
  - [ ] Initialize with config and response generator
  - [ ] Add logger with __name__

- [ ] Implement out-of-scope email handling (AC: handles non-warranty inquiries)
  - [ ] Create `handle_out_of_scope(email: EmailMessage, reason: str) -> ProcessingResult` async method
  - [ ] Use graceful-degradation scenario instruction
  - [ ] Generate polite response explaining out-of-scope
  - [ ] Suggest customer contact appropriate channel (billing, support, etc.)
  - [ ] Log: "Out-of-scope email handled: reason={reason}"
  - [ ] Return ProcessingResult with success=True (handled gracefully)

- [ ] Implement missing information handling (AC: handles unclear intent, partial data)
  - [ ] Create `handle_missing_info(email: EmailMessage, missing: List[str]) -> ProcessingResult` async method
  - [ ] Use missing-info scenario instruction (from Story 3.2)
  - [ ] Generate response requesting missing information
  - [ ] Guide customer on where to find serial number
  - [ ] Log: "Missing information handled: missing={missing}"
  - [ ] Return ProcessingResult with success=True

- [ ] Implement API failure handling (AC: handles LLM timeout, warranty API down)
  - [ ] Create `handle_api_failure(email: EmailMessage, failed_api: str, error: str) -> ProcessingResult` async method
  - [ ] Use graceful-degradation scenario instruction
  - [ ] Generate apology response explaining temporary unavailability
  - [ ] Provide alternative: "We'll process your request shortly" or manual contact
  - [ ] Log: "API failure handled: api={failed_api}, error={error}"
  - [ ] Return ProcessingResult with success=False, degradation=True

- [ ] Implement edge case handling (AC: malformed emails, extraction failures)
  - [ ] Create `handle_edge_case(email: EmailMessage, issue: str) -> ProcessingResult` async method
  - [ ] Detect: malformed email structure, encoding issues, extraction failures
  - [ ] Use graceful-degradation scenario instruction
  - [ ] Generate helpful response asking customer to clarify
  - [ ] Log: "Edge case handled: issue={issue}"
  - [ ] Return ProcessingResult with success=True (handled)

- [ ] Implement ambiguous scenario handling (AC: ambiguous scenarios)
  - [ ] Create `handle_ambiguous(email: EmailMessage, scenarios: List[str]) -> ProcessingResult` async method
  - [ ] When multiple scenarios could apply
  - [ ] Use graceful-degradation scenario
  - [ ] Generate response asking for clarification
  - [ ] Log: "Ambiguous scenario handled: possible_scenarios={scenarios}"
  - [ ] Return ProcessingResult with success=True

- [ ] Add degradation response generation (AC: polite, helpful tone)
  - [ ] All degradation handlers use ResponseGenerator
  - [ ] Pass graceful-degradation scenario to generator
  - [ ] Ensure response tone: polite, empathetic, helpful
  - [ ] Provide actionable next steps for customer
  - [ ] Never blame customer or expose technical errors
  - [ ] Response structure: acknowledgment, explanation, next steps, contact info

- [ ] Implement degradation logging (AC: logs all degradation triggers)
  - [ ] Log at WARN level when degradation triggered
  - [ ] Include degradation reason and context
  - [ ] Format: "Graceful degradation: reason={reason}, email_id={id}"
  - [ ] Include which scenario instruction used
  - [ ] Track degradation events for metrics
  - [ ] Ensure sufficient context for troubleshooting (NFR25)

- [ ] Add never-crash guarantee (AC: never crashes on unexpected input)
  - [ ] Wrap all degradation handlers in try/except
  - [ ] If degradation handler fails, use fallback template response
  - [ ] Fallback: "We received your email. Our team will review and respond."
  - [ ] Log degradation handler failures at ERROR level
  - [ ] Always return ProcessingResult (never raise exception)
  - [ ] Document FR18, NFR5 compliance

### Error Context Enrichment

- [ ] Create error context builder (AC: error logs include email_id, serial, scenario, step)
  - [ ] Create `build_error_context(**kwargs) -> Dict[str, Any]` helper
  - [ ] Standard fields: email_id, serial_number, scenario, processing_step
  - [ ] Add timestamp, error_code, error_message
  - [ ] Add retry_attempt if applicable
  - [ ] Add circuit_breaker_state if applicable
  - [ ] Return dict for logging extra

- [ ] Implement error code patterns (AC: error codes follow pattern)
  - [ ] Pattern: `{component}_{error_type}`
  - [ ] Examples: "mcp_warranty_timeout", "llm_response_failed", "email_parse_error"
  - [ ] Document all error codes in errors.py
  - [ ] Use error codes consistently across codebase
  - [ ] Include error code in all error logs

- [ ] Add transient vs permanent error distinction (AC: distinguished in logs)
  - [ ] Tag errors as "transient" or "permanent" in logs
  - [ ] Transient: network errors, timeouts, 5xx, rate limits
  - [ ] Permanent: validation errors, auth failures, 4xx (except 429)
  - [ ] Log: "Error type: transient" or "Error type: permanent"
  - [ ] Use error type to determine retry behavior

- [ ] Implement retry attempt logging (AC: retry attempts logged)
  - [ ] Log each retry attempt at WARN level
  - [ ] Include attempt number: "Retry attempt 2/3"
  - [ ] Include backoff delay: "Retrying in 2s"
  - [ ] Log final outcome: "Retry succeeded" or "All retries exhausted"
  - [ ] Use structured context for retry metadata

- [ ] Add circuit breaker logging (AC: circuit breaker state changes logged)
  - [ ] Log circuit breaker state transitions
  - [ ] States: closed, open, half-open
  - [ ] Log: "Circuit breaker opened for {api}" at WARN level
  - [ ] Log: "Circuit breaker half-open, testing {api}" at INFO level
  - [ ] Log: "Circuit breaker closed for {api}" at INFO level
  - [ ] Include failure count and threshold in logs

- [ ] Implement failed step tracking (AC: failed step explicitly named)
  - [ ] When processing fails, log which step failed
  - [ ] Steps: parse, extract_serial, detect_scenario, validate_warranty, generate_response, send_email, create_ticket
  - [ ] Log: "Processing failed at step: {step_name}"
  - [ ] Include step name in ProcessingResult.failed_step
  - [ ] Use for targeted troubleshooting and metrics

### Performance Logging

- [ ] Implement processing time tracking (AC: processing time logged)
  - [ ] Track total processing time per email
  - [ ] Log at INFO level: "Email processed in {ms}ms"
  - [ ] Log at WARN level if >60s: "Slow processing detected: {ms}ms"
  - [ ] Include processing time in ProcessingResult
  - [ ] Track for p95 latency calculation

- [ ] Add step timing logging (AC: step timing logged)
  - [ ] Time each processing step individually
  - [ ] Log at DEBUG level: "Step {step_name} completed in {ms}ms"
  - [ ] Log at WARN level if step >5s: "Slow step: {step_name} took {ms}ms"
  - [ ] Track step timings for bottleneck identification
  - [ ] Include in structured logs for analysis

- [ ] Implement slow operation warnings (AC: slow operations logged at WARN)
  - [ ] Define slow thresholds:
    - [ ] Parse: >500ms
    - [ ] Extract serial: >3s (LLM call)
    - [ ] Detect scenario: >3s (LLM call)
    - [ ] Validate warranty: >2s (API call)
    - [ ] Generate response: >5s (LLM call)
    - [ ] Send email: >2s (API call)
    - [ ] Create ticket: >2s (API call)
  - [ ] Log WARN: "Slow operation: {step_name} took {ms}ms (threshold: {threshold}ms)"

- [ ] Add LLM call latency logging (AC: LLM call latency logged)
  - [ ] Log each LLM API call latency
  - [ ] Log at DEBUG level: "LLM call: model={model}, latency={ms}ms"
  - [ ] Include prompt tokens and completion tokens if available
  - [ ] Log at WARN level if >15s (near timeout)
  - [ ] Track for LLM performance monitoring

- [ ] Add MCP API call latency logging (AC: MCP API call latency logged)
  - [ ] Log each MCP API call latency
  - [ ] Log at DEBUG level: "MCP call: {api_name}, latency={ms}ms"
  - [ ] Include API endpoint and method if available
  - [ ] Log at WARN level if approaching timeout
  - [ ] Track for MCP performance monitoring

- [ ] Implement p95 latency tracking (AC: p95 latency tracked)
  - [ ] Track processing times in memory (sliding window)
  - [ ] Calculate p95 periodically (every 100 emails or 10 minutes)
  - [ ] Log p95 at INFO level: "P95 latency: {p95_ms}ms (target: 60000ms)"
  - [ ] Alert if p95 exceeds 60s target
  - [ ] Export p95 for external monitoring

### Logging Integration Across Codebase

- [ ] Audit existing logging statements
  - [ ] Review all logger.info/warn/error calls
  - [ ] Ensure structured context used (extra dict)
  - [ ] Verify customer data protection (NFR14)
  - [ ] Ensure consistent context keys
  - [ ] Add missing context where needed

- [ ] Add processing event logging (AC: processing events logged)
  - [ ] Log: "Email received" (INFO, metadata only)
  - [ ] Log: "Serial extracted: {serial}" (INFO)
  - [ ] Log: "Scenario detected: {scenario}" (INFO)
  - [ ] Log: "Warranty validated: {status}" (INFO)
  - [ ] Log: "Response generated: {length} chars" (INFO)
  - [ ] Log: "Email sent to {to}" (INFO)
  - [ ] Log: "Ticket created: {ticket_id}" (INFO)
  - [ ] All with structured context

- [ ] Update error logging throughout codebase
  - [ ] All exceptions logged with exc_info=True
  - [ ] Include error context in all error logs
  - [ ] Use ERROR level for failures
  - [ ] Use WARN level for retryable errors
  - [ ] Include error codes in all error logs

- [ ] Add startup/shutdown logging
  - [ ] Log startup events: config loaded, validations passed, components initialized
  - [ ] Log shutdown events: shutdown signal, cleanup steps, final statistics
  - [ ] Use INFO level for lifecycle events
  - [ ] Include agent version in startup logs

### Configuration Updates

- [ ] Add logging configuration section
  - [ ] Update `config.yaml` with logging section
  - [ ] Add log_level: "INFO" (default)
  - [ ] Add json_format: false (text format default, JSON for production)
  - [ ] Add log_to_stdout: true (per NFR16 stateless)
  - [ ] Document configuration options

- [ ] Add environment variable support
  - [ ] Support LOG_LEVEL environment variable
  - [ ] Support LOG_FORMAT environment variable (text or json)
  - [ ] Override config.yaml values if env vars set
  - [ ] Document env var precedence

### Testing

- [ ] Create logging configuration tests
  - [ ] Create `tests/utils/test_logging.py`
  - [ ] Test configure_logging() with different levels
  - [ ] Test JSON formatter output
  - [ ] Test structured context in logs
  - [ ] Test customer data protection (body not in INFO logs)
  - [ ] Capture log output for assertions

- [ ] Create graceful degradation handler tests
  - [ ] Create `tests/email/test_graceful_handler.py`
  - [ ] Test handle_out_of_scope() with non-warranty emails
  - [ ] Test handle_missing_info() with incomplete data
  - [ ] Test handle_api_failure() with API errors
  - [ ] Test handle_edge_case() with malformed emails
  - [ ] Test handle_ambiguous() with multiple scenarios
  - [ ] Mock ResponseGenerator for all tests
  - [ ] Verify never crashes on unexpected input

- [ ] Create error context tests
  - [ ] Test build_error_context() with various inputs
  - [ ] Test error code patterns
  - [ ] Test transient vs permanent error tagging
  - [ ] Test retry attempt logging
  - [ ] Test circuit breaker logging
  - [ ] Verify context includes all required fields

- [ ] Create performance logging tests
  - [ ] Test processing time tracking
  - [ ] Test step timing logging
  - [ ] Test slow operation warnings
  - [ ] Test LLM/MCP latency logging
  - [ ] Test p95 calculation
  - [ ] Use mocked timers for deterministic tests

- [ ] Create integration tests
  - [ ] Test complete processing with logging
  - [ ] Test graceful degradation scenarios end-to-end
  - [ ] Test error handling with context enrichment
  - [ ] Capture and verify log output
  - [ ] Test JSON log format parsing
  - [ ] Verify NFR14 compliance (no body at INFO)

## Dev Notes

### Architecture Context

This story implements **Structured Logging and Graceful Degradation** (consolidates old stories 4.7 and 4.8), completing Epic 3 with comprehensive observability and resilience for production operation.

**Key Architectural Principles:**
- FR18: Graceful degradation for out-of-scope cases
- FR44: Failed steps logged with sufficient detail
- NFR5: No silent failures (all errors logged)
- NFR14: Customer email body ONLY at DEBUG level
- NFR16: Stateless (logs to stdout, not files)
- NFR25: Sufficient context for troubleshooting
- NFR7: Performance tracking (<60s p95 target)

### Critical Implementation Rules from Project Context

**Structured Logging Implementation:**

```python
# src/guarantee_email_agent/utils/logging.py
import logging
import json
import sys
from typing import Any, Dict
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON log formatter for production"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON

        Args:
            record: Log record

        Returns:
            JSON-formatted log string
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
            # Collect any extra attributes
            context = {}
            for key, value in record.__dict__.items():
                if key not in ["name", "msg", "args", "created", "filename", "funcName",
                              "levelname", "levelno", "lineno", "module", "msecs",
                              "message", "pathname", "process", "processName",
                              "relativeCreated", "thread", "threadName", "exc_info",
                              "exc_text", "stack_info"]:
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
    """
    Configure application logging.

    Args:
        log_level: Log level (DEBUG, INFO, WARN, ERROR)
        json_format: Use JSON format (True) or text format (False)

    Environment Variables:
        LOG_LEVEL: Override log_level parameter
        LOG_FORMAT: Override json_format ("json" or "text")
    """
    # Check environment variables
    import os
    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    log_format_env = os.getenv("LOG_FORMAT", "text" if not json_format else "json")
    json_format = log_format_env.lower() == "json"

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level))

    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        # Text format with structured context
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Log configuration
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
    """
    Log message with structured context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error)
        message: Log message
        **context: Context key-value pairs

    Example:
        log_with_context(
            logger, "info", "Email received",
            email_id="123", subject="Warranty inquiry"
        )
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra={"context": context})

# Standard context keys for consistency
CONTEXT_EMAIL_ID = "email_id"
CONTEXT_SERIAL_NUMBER = "serial_number"
CONTEXT_SCENARIO = "scenario"
CONTEXT_PROCESSING_STEP = "processing_step"
CONTEXT_ERROR_CODE = "error_code"
CONTEXT_RETRY_ATTEMPT = "retry_attempt"
CONTEXT_PROCESSING_TIME_MS = "processing_time_ms"
CONTEXT_WARRANTY_STATUS = "warranty_status"
```

**Graceful Degradation Handler Implementation:**

```python
# src/guarantee_email_agent/email/graceful_handler.py
import logging
from typing import List
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.email.processor_models import ProcessingResult
from guarantee_email_agent.llm.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)

class GracefulDegradationHandler:
    """Handle edge cases and failures with graceful degradation"""

    def __init__(self, config: AgentConfig, response_generator: ResponseGenerator):
        """Initialize graceful degradation handler

        Args:
            config: Agent configuration
            response_generator: Response generator for degradation responses
        """
        self.config = config
        self.response_generator = response_generator
        logger.info("Graceful degradation handler initialized")

    async def handle_out_of_scope(
        self,
        email: EmailMessage,
        reason: str
    ) -> ProcessingResult:
        """
        Handle out-of-scope emails (non-warranty inquiries).

        Args:
            email: Email message
            reason: Reason for out-of-scope classification

        Returns:
            ProcessingResult with graceful degradation response

        Examples:
            - Billing inquiries
            - General support questions
            - Spam/junk
        """
        logger.warning(
            f"Out-of-scope email handled: {reason}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "reason": reason,
                "degradation_type": "out_of_scope"
            }
        )

        try:
            # Generate graceful degradation response
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            # Send response (via processor)
            # Note: Actual sending handled by processor, we just generate response

            return ProcessingResult(
                success=True,
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,  # Set by processor
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,  # Set by processor
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Graceful degradation handler failed: {e}",
                extra={
                    "email_id": email.message_id,
                    "error": str(e),
                    "degradation_type": "out_of_scope"
                },
                exc_info=True
            )

            # Use fallback template if handler fails
            return self._fallback_response(email, "out_of_scope")

    async def handle_missing_info(
        self,
        email: EmailMessage,
        missing: List[str]
    ) -> ProcessingResult:
        """
        Handle emails with missing required information.

        Args:
            email: Email message
            missing: List of missing fields (e.g., ["serial_number"])

        Returns:
            ProcessingResult with missing-info response
        """
        logger.warning(
            f"Missing information handled: {', '.join(missing)}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "missing_fields": missing,
                "degradation_type": "missing_info"
            }
        )

        try:
            # Use missing-info scenario instruction
            response = await self.response_generator.generate_response(
                scenario_name="missing-info",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=True,
                email_id=email.message_id or "unknown",
                scenario_used="missing-info",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Missing info handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "missing_info")

    async def handle_api_failure(
        self,
        email: EmailMessage,
        failed_api: str,
        error: str
    ) -> ProcessingResult:
        """
        Handle API failures (LLM, warranty API, ticketing).

        Args:
            email: Email message
            failed_api: Name of failed API (e.g., "warranty_api")
            error: Error message

        Returns:
            ProcessingResult with graceful degradation
        """
        logger.error(
            f"API failure handled: {failed_api}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "failed_api": failed_api,
                "error": error,
                "degradation_type": "api_failure"
            },
            exc_info=False  # Error already captured
        )

        try:
            # Generate apology response
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=False,  # API failure is a failure
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=f"API failure: {failed_api}",
                failed_step=failed_api
            )

        except Exception as e:
            logger.error(
                f"API failure handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "api_failure")

    async def handle_edge_case(
        self,
        email: EmailMessage,
        issue: str
    ) -> ProcessingResult:
        """
        Handle edge cases (malformed emails, extraction failures).

        Args:
            email: Email message
            issue: Description of edge case

        Returns:
            ProcessingResult with graceful degradation
        """
        logger.warning(
            f"Edge case handled: {issue}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "issue": issue,
                "degradation_type": "edge_case"
            }
        )

        try:
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=True,
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Edge case handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "edge_case")

    async def handle_ambiguous(
        self,
        email: EmailMessage,
        scenarios: List[str]
    ) -> ProcessingResult:
        """
        Handle ambiguous scenarios (multiple possibilities).

        Args:
            email: Email message
            scenarios: List of possible scenarios

        Returns:
            ProcessingResult with clarification request
        """
        logger.warning(
            f"Ambiguous scenario handled: {', '.join(scenarios)}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "possible_scenarios": scenarios,
                "degradation_type": "ambiguous"
            }
        )

        try:
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=True,
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Ambiguous scenario handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "ambiguous")

    def _fallback_response(
        self,
        email: EmailMessage,
        degradation_type: str
    ) -> ProcessingResult:
        """
        Fallback response when degradation handler fails.

        This is the last line of defense - NEVER raise exceptions.

        Args:
            email: Email message
            degradation_type: Type of degradation that failed

        Returns:
            ProcessingResult with fallback handling
        """
        logger.error(
            f"Using fallback response for {degradation_type}",
            extra={
                "email_id": email.message_id,
                "degradation_type": degradation_type
            }
        )

        # Return minimal ProcessingResult
        # Actual fallback response would be handled by processor
        return ProcessingResult(
            success=False,
            email_id=email.message_id or "unknown",
            scenario_used="fallback",
            serial_number=None,
            warranty_status=None,
            response_sent=False,
            ticket_created=False,
            ticket_id=None,
            processing_time_ms=0,
            error_message=f"Degradation handler failed: {degradation_type}",
            failed_step="graceful_degradation"
        )
```

**Performance Logging Integration:**

```python
# Add to email/processor.py
import time

class EmailProcessor:
    async def process_email(self, raw_email: Dict[str, Any]) -> ProcessingResult:
        start_time = time.time()
        step_times = {}

        # Step 1: Parse
        step_start = time.time()
        email = self.parser.parse_email(raw_email)
        step_times["parse"] = int((time.time() - step_start) * 1000)

        if step_times["parse"] > 500:
            logger.warning(
                f"Slow parsing: {step_times['parse']}ms",
                extra={"step": "parse", "duration_ms": step_times["parse"], "threshold_ms": 500}
            )

        # Similar timing for other steps...

        # Final timing
        processing_time_ms = int((time.time() - start_time) * 1000)

        if processing_time_ms > 60000:
            logger.warning(
                f"Slow processing: {processing_time_ms}ms (target: 60000ms)",
                extra={
                    "email_id": email_id,
                    "processing_time_ms": processing_time_ms,
                    "target_ms": 60000,
                    "step_times": step_times
                }
            )

        logger.info(
            f"Email processed in {processing_time_ms}ms",
            extra={
                "email_id": email_id,
                "processing_time_ms": processing_time_ms,
                "step_times": step_times
            }
        )
```

### Configuration Updates

**Add logging section to config.yaml:**

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARN, ERROR
  json_format: false  # true for production, false for development
  log_to_stdout: true  # Always true per NFR16 (stateless)
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Logging customer data at INFO level (NFR14 violation):**
   ```python
   # WRONG - Email body at INFO level
   logger.info(f"Processing email: {email.body}")

   # CORRECT - Body only at DEBUG, metadata at INFO
   logger.info("Processing email", extra={"subject": email.subject, "from": email.from_address})
   logger.debug("Email content", extra={"body": email.body})
   ```

2. **String interpolation instead of structured logging:**
   ```python
   # WRONG - String interpolation, loses structure
   logger.info(f"Email {email_id} processed with scenario {scenario}")

   # CORRECT - Structured context
   logger.info("Email processed", extra={"email_id": email_id, "scenario": scenario})
   ```

3. **Crashing on edge cases:**
   ```python
   # WRONG - Raises exception on unexpected input
   def handle_edge_case(email):
       raise ValueError("Unsupported email format")

   # CORRECT - Always returns graceful result
   def handle_edge_case(email):
       logger.warning("Edge case detected")
       return graceful_response(email)
   ```

4. **Missing error context:**
   ```python
   # WRONG - No context in error log
   logger.error("Processing failed")

   # CORRECT - Rich context for troubleshooting
   logger.error(
       "Processing failed",
       extra={
           "email_id": email_id,
           "serial_number": serial,
           "scenario": scenario,
           "failed_step": "validate_warranty",
           "error_code": "mcp_warranty_timeout"
       },
       exc_info=True
   )
   ```

5. **Logging to files (NFR16 violation):**
   ```python
   # WRONG - File handler violates stateless requirement
   file_handler = logging.FileHandler("agent.log")
   logger.addHandler(file_handler)

   # CORRECT - Only stdout handler
   stdout_handler = logging.StreamHandler(sys.stdout)
   logger.addHandler(stdout_handler)
   ```

### Verification Commands

```bash
# 1. Test logging configuration
uv run python -c "
from guarantee_email_agent.utils.logging import configure_logging
import logging

configure_logging(log_level='INFO', json_format=False)
logger = logging.getLogger('test')
logger.info('Test message', extra={'key': 'value'})
"

# 2. Test JSON logging
uv run python -c "
from guarantee_email_agent.utils.logging import configure_logging
import logging

configure_logging(log_level='INFO', json_format=True)
logger = logging.getLogger('test')
logger.info('Test message', extra={'key': 'value'})
"

# 3. Test customer data protection (NFR14)
LOG_LEVEL=INFO uv run python -c "
from guarantee_email_agent.utils.logging import configure_logging
import logging

configure_logging()
logger = logging.getLogger('test')

# This should appear (INFO level)
logger.info('Email metadata', extra={'subject': 'Test', 'from': 'test@example.com'})

# This should NOT appear at INFO level
logger.debug('Email body', extra={'body': 'SENSITIVE CUSTOMER DATA'})
"

# 4. Test graceful degradation handler
uv run python -c "
import asyncio
from guarantee_email_agent.email.graceful_handler import GracefulDegradationHandler
from guarantee_email_agent.email.models import EmailMessage
from datetime import datetime

async def test():
    # Mock handler initialization
    # handler = GracefulDegradationHandler(config, generator)

    email = EmailMessage(
        subject='Billing question',
        body='How do I update my payment method?',
        from_address='test@example.com',
        received_timestamp=datetime.now()
    )

    # result = await handler.handle_out_of_scope(email, 'billing_inquiry')
    # print(f'Result: {result.success}, scenario: {result.scenario_used}')
    print('Graceful degradation handler test setup complete')

asyncio.run(test())
"

# 5. Run unit tests
uv run pytest tests/utils/test_logging.py -v
uv run pytest tests/email/test_graceful_handler.py -v

# 6. Test with JSON logs
LOG_FORMAT=json uv run python -m guarantee_email_agent run --config config.yaml

# 7. Verify NFR14 compliance
LOG_LEVEL=INFO uv run python -m guarantee_email_agent run | grep -i "body"
# Should NOT see customer email bodies in output
```

### Dependency Notes

**Depends on:**
- Story 3.5: Agent runner for integration
- Story 3.4: EmailProcessor for performance logging
- Story 3.2: ResponseGenerator for degradation responses
- Story 3.1: Instruction loader
- All previous stories for complete integration

**Blocks:**
- Epic 4: Eval framework needs logging
- Production deployment: Monitoring needs structured logs

**Integration Points:**
- Logging → All components (cross-cutting concern)
- GracefulDegradationHandler → ResponseGenerator → graceful-degradation scenario
- Performance logging → EmailProcessor → step timing
- Error context → All error handlers

### Previous Story Intelligence

From Story 3.5 (CLI and Graceful Shutdown):
- Agent lifecycle with startup and shutdown
- State tracking for statistics
- Signal handlers and graceful completion

From Story 3.4 (Email Processing Pipeline):
- ProcessingResult with detailed tracking
- Error handling at each step
- Processing time measurement

From Story 3.2 (Scenario Routing):
- graceful-degradation scenario instruction
- ResponseGenerator for all responses
- Scenario-based routing

**Learnings to Apply:**
- Structured logging with extra dict throughout
- Never crash on edge cases (FR18, NFR5)
- Rich error context for troubleshooting (NFR25)
- Performance tracking at each step
- Customer data protection at all times (NFR14)

### Git Intelligence Summary

Recent commits show:
- Comprehensive error handling patterns
- Structured logging with context
- Graceful error recovery
- Never-crash guarantees
- Testing with mocked components

**Code Patterns to Continue:**
- Try/except with structured logging
- Fallback responses when handlers fail
- Performance timing with warnings
- JSON formatter for production
- Context enrichment for all logs

### References

**Architecture Document Sections:**
- [Source: architecture.md#Logging Strategy] - Structured logging approach
- [Source: architecture.md#Graceful Degradation] - Edge case handling
- [Source: project-context.md#Customer Data Logging] - NFR14 protection
- [Source: project-context.md#Stateless Processing] - NFR16 stdout only

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 3: Story 3.6] - Complete acceptance criteria
- [Source: prd.md#FR18] - Graceful degradation requirement
- [Source: prd.md#FR44] - Failed steps logged with detail
- [Source: prd.md#NFR5] - No silent failures
- [Source: prd.md#NFR7] - Performance tracking (<60s)
- [Source: prd.md#NFR14] - Customer data protection
- [Source: prd.md#NFR16] - Stateless (stdout logs)
- [Source: prd.md#NFR25] - Sufficient troubleshooting context

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context from all Epic 3 stories
- Story consolidates 2 original stories (4.7 Logging + 4.8 Graceful Degradation)
- Structured logging with Python logging module + JSON formatter
- Customer data protection: email body ONLY at DEBUG level (NFR14)
- Logs to stdout only (NFR16 stateless)
- GracefulDegradationHandler for all edge cases
- Never-crash guarantee: fallback responses when handlers fail
- Error context enrichment: email_id, serial, scenario, step, error_code
- Performance logging: processing time, step timing, LLM/MCP latency
- P95 latency tracking with 60s target (NFR7)
- Transient vs permanent error distinction
- Retry and circuit breaker state logging
- Complete logging integration across codebase
- Configuration with LOG_LEVEL and LOG_FORMAT env vars
- Testing strategy: logging, degradation, performance, integration
- Verification commands for NFR14 compliance

### File List

**Logging Utilities:**
- `src/guarantee_email_agent/utils/logging.py` - Logging configuration, JSON formatter, helpers

**Graceful Degradation:**
- `src/guarantee_email_agent/email/graceful_handler.py` - GracefulDegradationHandler with all edge cases

**Configuration Updates:**
- `config.yaml` - Add logging section

**Tests:**
- `tests/utils/test_logging.py` - Logging configuration and formatter tests
- `tests/email/test_graceful_handler.py` - Graceful degradation handler tests
- `tests/utils/test_error_context.py` - Error context enrichment tests
- `tests/utils/test_performance_logging.py` - Performance logging tests
