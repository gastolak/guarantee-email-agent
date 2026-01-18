# Story 4.3: Error Handling, Exit Codes, and Comprehensive Logging

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want a standardized error hierarchy with clear codes and proper exit codes for automation,
So that all failures are logged consistently and scripts can handle different error types.

## Acceptance Criteria

**Given** The complete agent implementation from Epics 1-3 exists
**When** I implement error handling throughout

**Then - AgentError Exception Hierarchy:**
**And** Base class AgentError exists in `src/guarantee_email_agent/utils/errors.py`
**And** AgentError includes: message, code, details (dict)
**And** Error code pattern: `{component}_{error_type}` (e.g., "mcp_connection_failed", "instruction_parse_error")
**And** Specific subclasses: ConfigError, MCPError, InstructionError, LLMError, ProcessingError, EvalError
**And** All domain errors use AgentError hierarchy (not generic exceptions)
**And** Error details include actionable context: serial_number, scenario, file_path, step
**And** Example: `raise ConfigError(message="Missing field", code="config_missing_field", details={"field": "mcp.gmail"})`
**And** All errors logged with error code and details
**And** Error messages clear and actionable (NFR28)
**And** Transient vs permanent error distinction

**Then - Exit Code Standards:**
**And** Exit codes follow standard from NFR29:
**And** Exit code 0: Success (agent run completed, eval pass rate ≥99%)
**And** Exit code 1: General errors (unexpected exceptions)
**And** Exit code 2: Configuration error (invalid config, missing env vars, invalid paths)
**And** Exit code 3: MCP connection failure during startup
**And** Exit code 4: Eval failure (pass rate <99%)
**And** CLI framework catches exceptions and returns appropriate codes
**And** ConfigError → exit code 2
**And** MCPError during startup → exit code 3
**And** EvalError with pass rate <99% → exit code 4
**And** Eval pass rate <99% → exit code 4 (NFR29)
**And** Automation scripts can check: `agent eval || echo "Failed with $?"`
**And** Exit codes documented in CLI help and README

**Then - Comprehensive Logging:**
**And** Logger logs errors with full context
**And** Error logs include: error code, message, serial_number, scenario, stack trace
**And** Example: `ERROR Warranty API failed: code=mcp_warranty_check_failed, serial=SN12345, attempt=3/3, error=timeout`
**And** Error logs use structured format with extra dict
**And** Stack traces included for debugging (exc_info=True)
**And** Transient errors (retried) logged at WARN
**And** Permanent errors (failed after retries) logged at ERROR
**And** Logs include actionable remediation guidance (NFR28)
**And** Log output sufficient for troubleshooting without code access (NFR25)
**And** All errors logged - no silent failures (NFR5, FR45)

**Then - Error Recovery and Resilience:**
**And** Transient errors trigger retry with exponential backoff
**And** Permanent errors logged and fail fast
**And** Circuit breaker prevents cascading failures
**And** Email processing continues after non-critical errors
**And** Critical errors (startup validation) exit immediately
**And** Error context preserved across retry attempts
**And** Graceful degradation for LLM/API failures
**And** User-friendly error messages in CLI output

## Tasks / Subtasks

### AgentError Exception Hierarchy

- [ ] Create base AgentError class (AC: base class with message, code, details)
  - [ ] Create `src/guarantee_email_agent/utils/errors.py`
  - [ ] Define `AgentError` class extending Exception
  - [ ] Add __init__(self, message: str, code: str, details: Dict[str, Any])
  - [ ] Store message, code, details as instance attributes
  - [ ] Add __str__ and __repr__ for clear error display
  - [ ] Include code and key details in string representation
  - [ ] Make details optional (default to empty dict)

- [ ] Implement error code validation (AC: error code pattern)
  - [ ] Validate code follows pattern: `{component}_{error_type}`
  - [ ] Components: config, mcp, instruction, llm, processing, eval, email
  - [ ] Error types: connection_failed, parse_error, timeout, validation_error, not_found
  - [ ] Example valid codes: "mcp_connection_failed", "instruction_parse_error", "llm_timeout"
  - [ ] Raise ValueError if code doesn't match pattern
  - [ ] Document pattern in docstring

- [ ] Create ConfigError subclass (AC: specific subclasses)
  - [ ] Define `ConfigError(AgentError)` class
  - [ ] Use for: missing config fields, invalid values, schema validation failures
  - [ ] Default code prefix: "config_"
  - [ ] Common codes: config_missing_field, config_invalid_value, config_file_not_found
  - [ ] Include field path in details

- [ ] Create MCPError subclass
  - [ ] Define `MCPError(AgentError)` class
  - [ ] Use for: connection failures, API errors, timeout
  - [ ] Default code prefix: "mcp_"
  - [ ] Common codes: mcp_connection_failed, mcp_timeout, mcp_api_error
  - [ ] Include service name (gmail, warranty, ticketing) in details
  - [ ] Distinguish transient (timeout, network) vs permanent (auth, invalid)

- [ ] Create InstructionError subclass
  - [ ] Define `InstructionError(AgentError)` class
  - [ ] Use for: file not found, parse errors, validation failures
  - [ ] Default code prefix: "instruction_"
  - [ ] Common codes: instruction_not_found, instruction_parse_error, instruction_validation_failed
  - [ ] Include file_path in details

- [ ] Create LLMError subclass
  - [ ] Define `LLMError(AgentError)` class
  - [ ] Use for: API failures, timeout, rate limiting
  - [ ] Default code prefix: "llm_"
  - [ ] Common codes: llm_timeout, llm_rate_limit, llm_api_error
  - [ ] Include model name, prompt length in details
  - [ ] Mark as transient or permanent

- [ ] Create ProcessingError subclass
  - [ ] Define `ProcessingError(AgentError)` class
  - [ ] Use for: email processing failures, step failures
  - [ ] Default code prefix: "processing_"
  - [ ] Common codes: processing_parse_failed, processing_extraction_failed, processing_step_failed
  - [ ] Include email_id, serial_number, failed_step in details

- [ ] Create EvalError subclass
  - [ ] Define `EvalError(AgentError)` class
  - [ ] Use for: eval framework errors, test case failures
  - [ ] Default code prefix: "eval_"
  - [ ] Common codes: eval_file_not_found, eval_yaml_invalid, eval_execution_failed
  - [ ] Include scenario_id, file_path in details

- [ ] Add transient error marker (AC: transient vs permanent distinction)
  - [ ] Add `is_transient: bool` property to AgentError
  - [ ] Transient errors: timeouts, network errors, rate limits, 5xx
  - [ ] Permanent errors: validation errors, auth failures, 4xx (except 429)
  - [ ] Use for retry decision logic
  - [ ] Document transient error types

- [ ] Add error context helpers (AC: details include actionable context)
  - [ ] Create `add_context(**kwargs) -> AgentError` method
  - [ ] Allows adding context after error creation
  - [ ] Useful for adding context during exception handling
  - [ ] Example: `error.add_context(email_id="123", serial="SN456")`
  - [ ] Returns self for chaining

### Exit Code Implementation

- [ ] Define exit code constants (AC: exit codes follow standard)
  - [ ] Create constants in errors.py or cli.py
  - [ ] `EXIT_SUCCESS = 0` - Success
  - [ ] `EXIT_GENERAL_ERROR = 1` - General/unexpected errors
  - [ ] `EXIT_CONFIG_ERROR = 2` - Configuration errors
  - [ ] `EXIT_MCP_ERROR = 3` - MCP connection failures
  - [ ] `EXIT_EVAL_FAILURE = 4` - Eval pass rate <99%
  - [ ] Document each code with comment

- [ ] Implement exception to exit code mapping (AC: CLI catches exceptions)
  - [ ] Update CLI command handlers in `cli.py`
  - [ ] Wrap command execution in try/except
  - [ ] Map exception types to exit codes:
    - [ ] ConfigError → 2
    - [ ] MCPError (during startup) → 3
    - [ ] EvalError (pass rate <99%) → 4
    - [ ] Other AgentError → 1
    - [ ] Unexpected exceptions → 1
  - [ ] Log exception before exiting
  - [ ] Return exit code from command

- [ ] Update eval command exit logic (AC: eval pass rate <99% → code 4)
  - [ ] In eval command, check final pass rate
  - [ ] If pass_rate >= 99.0: return EXIT_SUCCESS (0)
  - [ ] If pass_rate < 99.0: return EXIT_EVAL_FAILURE (4)
  - [ ] Log: "Exiting with code {code}: {reason}"
  - [ ] Already implemented in 4.1, verify consistency

- [ ] Update run command exit logic (AC: startup failures → appropriate codes)
  - [ ] In run command, catch startup validation errors
  - [ ] ConfigError during startup → EXIT_CONFIG_ERROR (2)
  - [ ] MCPError during startup → EXIT_MCP_ERROR (3)
  - [ ] Successful run completion → EXIT_SUCCESS (0)
  - [ ] Runtime errors → EXIT_GENERAL_ERROR (1)
  - [ ] Log exit reason clearly

- [ ] Document exit codes (AC: documented in CLI help and README)
  - [ ] Add section to `README.md`: "Exit Codes"
  - [ ] List all codes with meanings
  - [ ] Provide examples for each
  - [ ] Explain automation use cases
  - [ ] Add to CLI --help output
  - [ ] Document in code comments

- [ ] Add exit code examples (AC: automation scripts can check)
  - [ ] Document shell usage examples
  - [ ] Example: `uv run python -m guarantee_email_agent eval || exit 1`
  - [ ] Example: `if uv run python -m guarantee_email_agent run; then echo "Success"; fi`
  - [ ] Example: Check specific code: `uv run python -m guarantee_email_agent eval; [ $? -eq 4 ] && echo "Eval failed"`
  - [ ] CI/CD examples for different codes

### Comprehensive Error Logging

- [ ] Implement error logging standard (AC: logs errors with full context)
  - [ ] All errors logged with ERROR level
  - [ ] Include error code in log
  - [ ] Include error message
  - [ ] Include context from details dict
  - [ ] Format: "ERROR {message}: code={code}, {details}"
  - [ ] Use structured logging (extra dict)

- [ ] Add stack trace logging (AC: stack traces included)
  - [ ] Always use exc_info=True when logging errors
  - [ ] Example: `logger.error("Error occurred", exc_info=True, extra={...})`
  - [ ] Stack traces help identify error source
  - [ ] Include full traceback in logs
  - [ ] Format properly for readability

- [ ] Implement retry logging (AC: transient errors logged at WARN)
  - [ ] Log retry attempts at WARN level
  - [ ] Include attempt number: "Retry attempt 2/3"
  - [ ] Include backoff delay: "Retrying in 2s"
  - [ ] Log error that triggered retry
  - [ ] Final failure after retries → ERROR level

- [ ] Add actionable remediation guidance (AC: logs include guidance)
  - [ ] For common errors, include fix suggestions in logs
  - [ ] ConfigError: "Check config.yaml field: {field}"
  - [ ] MCPError: "Verify MCP server is running and credentials valid"
  - [ ] InstructionError: "Check instruction file exists: {path}"
  - [ ] LLMError: "Check API key and rate limits"
  - [ ] Include in log message or details

- [ ] Implement error context enrichment (AC: sufficient for troubleshooting)
  - [ ] All error logs include relevant context
  - [ ] Email processing errors: email_id, serial_number, scenario, step
  - [ ] MCP errors: service_name, endpoint, attempt_count
  - [ ] Instruction errors: file_path, line_number
  - [ ] LLM errors: model, temperature, prompt_length
  - [ ] Make logs self-documenting (NFR25)

- [ ] Add no silent failures verification (AC: all errors logged)
  - [ ] Audit all exception handlers
  - [ ] Ensure all caught exceptions are logged
  - [ ] No bare `except:` without logging
  - [ ] No swallowed exceptions
  - [ ] Every error path logs before handling
  - [ ] Verify NFR5, FR45 compliance

### Error Recovery and Resilience

- [ ] Implement retry logic for transient errors (AC: transient errors trigger retry)
  - [ ] Use @retry decorator from tenacity
  - [ ] Configure: stop_after_attempt(3)
  - [ ] Configure: wait_exponential(multiplier=1, min=1, max=10)
  - [ ] Only retry transient errors
  - [ ] Log each retry attempt
  - [ ] Already implemented in Story 2.1, verify consistency

- [ ] Add fail-fast for permanent errors (AC: permanent errors logged and fail fast)
  - [ ] Don't retry permanent errors
  - [ ] Log at ERROR level immediately
  - [ ] Raise exception to caller
  - [ ] Examples: validation errors, auth failures
  - [ ] Mark email as unprocessed
  - [ ] Exit if during startup validation

- [ ] Implement graceful degradation integration (AC: graceful degradation for failures)
  - [ ] LLM timeout → graceful degradation scenario
  - [ ] Warranty API down → graceful degradation response
  - [ ] Instruction load failure → default instruction
  - [ ] Log degradation trigger
  - [ ] Already implemented in Story 3.6, verify integration

- [ ] Add error context preservation (AC: context preserved across retries)
  - [ ] Pass error context through retry attempts
  - [ ] Accumulate retry history in context
  - [ ] Include all attempts in final error log
  - [ ] Don't lose context during exception re-raising
  - [ ] Use error.add_context() for accumulation

- [ ] Implement user-friendly CLI error messages (AC: user-friendly messages)
  - [ ] CLI displays simplified error messages
  - [ ] Technical details in logs, not CLI output
  - [ ] Example CLI: "Configuration error: Missing API key"
  - [ ] Example log: "ERROR code=config_missing_field, field=secrets.api_key, ..."
  - [ ] Suggest next steps in CLI output

### Error Handling Audit and Refactoring

- [ ] Audit existing exception handling (AC: all domain errors use hierarchy)
  - [ ] Search codebase for generic Exception usage
  - [ ] Replace with appropriate AgentError subclass
  - [ ] Ensure all errors have codes
  - [ ] Verify error details populated
  - [ ] Check logging is comprehensive

- [ ] Replace generic exceptions (AC: not generic exceptions)
  - [ ] Replace `raise Exception("...")` with specific error
  - [ ] Replace `raise ValueError("...")` with ConfigError
  - [ ] Replace `raise RuntimeError("...")` with ProcessingError
  - [ ] Replace `raise IOError("...")` with InstructionError
  - [ ] Keep standard library exceptions for stdlib code only

- [ ] Add error handling to uncovered areas
  - [ ] Identify areas without exception handling
  - [ ] Add try/except with proper logging
  - [ ] Use appropriate error types
  - [ ] Ensure context included
  - [ ] Test error paths

- [ ] Verify error code consistency
  - [ ] All errors follow naming pattern
  - [ ] No duplicate error codes
  - [ ] Document all error codes
  - [ ] Create error code registry (optional)
  - [ ] Example: ERROR_CODES.md with all codes

### Testing

- [ ] Create error hierarchy tests
  - [ ] Create `tests/utils/test_errors.py`
  - [ ] Test AgentError creation
  - [ ] Test all subclasses
  - [ ] Test error code validation
  - [ ] Test context addition
  - [ ] Test transient marker
  - [ ] Test string representations

- [ ] Create exit code tests
  - [ ] Test CLI returns correct exit codes
  - [ ] Test ConfigError → code 2
  - [ ] Test MCPError → code 3
  - [ ] Test EvalError → code 4
  - [ ] Test successful runs → code 0
  - [ ] Use subprocess to verify actual exit codes

- [ ] Create error logging tests
  - [ ] Test error logs include all required fields
  - [ ] Test structured logging format
  - [ ] Test stack traces included
  - [ ] Test retry logging at WARN
  - [ ] Test final failure at ERROR
  - [ ] Capture log output for assertions

- [ ] Create error recovery tests
  - [ ] Test retry on transient errors
  - [ ] Test fail-fast on permanent errors
  - [ ] Test graceful degradation triggers
  - [ ] Test context preservation
  - [ ] Mock errors for testing

- [ ] Create integration tests
  - [ ] Test end-to-end error handling
  - [ ] Test startup validation errors
  - [ ] Test runtime processing errors
  - [ ] Test eval execution errors
  - [ ] Verify all error paths work correctly

## Dev Notes

### Architecture Context

This story implements **Error Handling, Exit Codes, and Comprehensive Logging** (consolidates old stories 6.1, 6.2, 6.5), establishing standardized error handling across the entire application.

**Key Architectural Principles:**
- NFR28: Clear, actionable error messages
- NFR29: Standard exit codes for automation
- NFR5: No silent failures - all errors logged
- NFR25: Logs sufficient for troubleshooting without code access
- FR45: Failed steps logged with details

### Critical Implementation Rules from Project Context

**AgentError Hierarchy Implementation:**

```python
# src/guarantee_email_agent/utils/errors.py
from typing import Dict, Any, Optional

class AgentError(Exception):
    """Base exception for all agent-specific errors

    Attributes:
        message: Human-readable error message
        code: Error code following pattern {component}_{error_type}
        details: Additional context as key-value pairs
        is_transient: Whether error is transient (retryable)

    Example:
        raise AgentError(
            message="Configuration validation failed",
            code="config_validation_failed",
            details={"field": "mcp.gmail.credentials"}
        )
    """

    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        is_transient: bool = False
    ):
        """Initialize agent error

        Args:
            message: Error message
            code: Error code (pattern: {component}_{error_type})
            details: Additional context
            is_transient: Whether error is retryable

        Raises:
            ValueError: If code doesn't match pattern
        """
        super().__init__(message)
        self.message = message
        self.code = self._validate_code(code)
        self.details = details or {}
        self.is_transient = is_transient

    def _validate_code(self, code: str) -> str:
        """Validate error code follows pattern"""
        if "_" not in code:
            raise ValueError(
                f"Error code must follow pattern {{component}}_{{error_type}}, "
                f"got: {code}"
            )
        return code

    def add_context(self, **kwargs) -> 'AgentError':
        """Add additional context to error

        Args:
            **kwargs: Context key-value pairs

        Returns:
            Self for chaining
        """
        self.details.update(kwargs)
        return self

    def __str__(self) -> str:
        """String representation with code and key details"""
        details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
        if details_str:
            return f"{self.message} [code={self.code}, {details_str}]"
        return f"{self.message} [code={self.code}]"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', code='{self.code}', details={self.details})"

class ConfigError(AgentError):
    """Configuration-related errors

    Use for: missing config fields, invalid values, schema validation

    Common codes:
    - config_missing_field: Required field not present
    - config_invalid_value: Field value invalid
    - config_file_not_found: Config file doesn't exist
    - config_validation_failed: Schema validation failed
    """

    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details, is_transient=False)

class MCPError(AgentError):
    """MCP integration errors

    Use for: connection failures, API errors, timeouts

    Common codes:
    - mcp_connection_failed: Cannot connect to MCP server
    - mcp_timeout: MCP call timed out
    - mcp_api_error: MCP API returned error
    - mcp_auth_failed: Authentication failure

    Note: Timeouts and network errors are transient
    """

    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        is_transient: bool = True
    ):
        super().__init__(message, code, details, is_transient)

class InstructionError(AgentError):
    """Instruction file errors

    Use for: file not found, parse errors, validation

    Common codes:
    - instruction_not_found: Instruction file missing
    - instruction_parse_error: YAML/XML parsing failed
    - instruction_validation_failed: Schema validation failed
    """

    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details, is_transient=False)

class LLMError(AgentError):
    """LLM API errors

    Use for: API failures, timeouts, rate limiting

    Common codes:
    - llm_timeout: LLM API call timed out
    - llm_rate_limit: Rate limit exceeded
    - llm_api_error: LLM API returned error
    - llm_auth_failed: API key invalid

    Note: Timeouts and rate limits are transient
    """

    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        is_transient: bool = True
    ):
        super().__init__(message, code, details, is_transient)

class ProcessingError(AgentError):
    """Email processing errors

    Use for: parse failures, step failures, validation

    Common codes:
    - processing_parse_failed: Email parsing failed
    - processing_extraction_failed: Serial extraction failed
    - processing_step_failed: Processing step failed
    """

    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        is_transient: bool = False
    ):
        super().__init__(message, code, details, is_transient)

class EvalError(AgentError):
    """Eval framework errors

    Use for: test case errors, execution failures

    Common codes:
    - eval_file_not_found: Eval file missing
    - eval_yaml_invalid: YAML parsing failed
    - eval_execution_failed: Test execution failed
    - eval_pass_rate_below_threshold: Pass rate <99%
    """

    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details, is_transient=False)

# Transient error helper
class TransientError(AgentError):
    """Helper for marking transient errors"""

    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, details, is_transient=True)
```

**Exit Code Implementation:**

```python
# Exit code constants
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_MCP_ERROR = 3
EXIT_EVAL_FAILURE = 4

# In cli.py
import sys
from guarantee_email_agent.utils.errors import (
    ConfigError, MCPError, EvalError, AgentError,
    EXIT_SUCCESS, EXIT_CONFIG_ERROR, EXIT_MCP_ERROR, EXIT_EVAL_FAILURE, EXIT_GENERAL_ERROR
)

@app.command()
def run(config_path: Path = ...):
    """Run the agent"""
    try:
        exit_code = asyncio.run(run_agent(config_path))
        sys.exit(exit_code)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}", exc_info=True)
        print(f"Configuration error: {e.message}")
        print(f"Fix: Check config field '{e.details.get('field', 'unknown')}'")
        sys.exit(EXIT_CONFIG_ERROR)
    except MCPError as e:
        logger.error(f"MCP connection error: {e}", exc_info=True)
        print(f"MCP connection error: {e.message}")
        print(f"Fix: Verify MCP server '{e.details.get('service', 'unknown')}' is running")
        sys.exit(EXIT_MCP_ERROR)
    except AgentError as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        print(f"Error: {e.message}")
        sys.exit(EXIT_GENERAL_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Unexpected error: {e}")
        sys.exit(EXIT_GENERAL_ERROR)

@app.command()
def eval(eval_dir: Path = ...):
    """Run evaluation suite"""
    try:
        exit_code = asyncio.run(run_eval(eval_dir))
        sys.exit(exit_code)
    except EvalError as e:
        logger.error(f"Eval error: {e}", exc_info=True)
        print(f"Evaluation error: {e.message}")
        sys.exit(EXIT_EVAL_FAILURE if "pass_rate" in e.code else EXIT_GENERAL_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Unexpected error: {e}")
        sys.exit(EXIT_GENERAL_ERROR)
```

**Comprehensive Error Logging:**

```python
# Example error logging throughout codebase
import logging
from guarantee_email_agent.utils.errors import MCPError

logger = logging.getLogger(__name__)

async def check_warranty(self, serial_number: str) -> Dict:
    """Check warranty status"""
    try:
        response = await asyncio.wait_for(
            self.client.call_tool("check_warranty", arguments={"serial_number": serial_number}),
            timeout=10
        )
        return response
    except asyncio.TimeoutError:
        error = MCPError(
            message=f"Warranty API check timed out after 10s",
            code="mcp_warranty_timeout",
            details={
                "service": "warranty_api",
                "serial_number": serial_number,
                "timeout": 10
            },
            is_transient=True
        )
        logger.error(
            f"Warranty API timeout: code={error.code}, serial={serial_number}, timeout=10s",
            exc_info=True,
            extra={
                "error_code": error.code,
                "serial_number": serial_number,
                "service": "warranty_api",
                "timeout": 10,
                "is_transient": True
            }
        )
        raise error
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Using generic exceptions:**
   ```python
   # WRONG - Generic exception
   raise Exception("Configuration failed")

   # CORRECT - Specific error with code
   raise ConfigError(
       message="Configuration validation failed",
       code="config_validation_failed",
       details={"field": "mcp.gmail"}
   )
   ```

2. **Wrong exit codes:**
   ```python
   # WRONG - Generic exit code
   sys.exit(1)  # For all errors

   # CORRECT - Specific exit codes
   if isinstance(error, ConfigError):
       sys.exit(EXIT_CONFIG_ERROR)  # 2
   elif isinstance(error, MCPError):
       sys.exit(EXIT_MCP_ERROR)  # 3
   ```

3. **Silent failures:**
   ```python
   # WRONG - Swallowed exception
   try:
       result = process_email(email)
   except:
       pass  # Silent failure!

   # CORRECT - Log and handle
   try:
       result = process_email(email)
   except ProcessingError as e:
       logger.error(f"Processing failed: {e}", exc_info=True)
       raise
   ```

4. **Missing error context:**
   ```python
   # WRONG - No context
   raise ProcessingError("Processing failed", "processing_failed")

   # CORRECT - Rich context
   raise ProcessingError(
       message="Email processing failed at extraction step",
       code="processing_extraction_failed",
       details={
           "email_id": email_id,
           "serial_number": serial,
           "step": "extract_serial"
       }
   )
   ```

5. **No stack traces:**
   ```python
   # WRONG - No stack trace
   logger.error(f"Error: {e}")

   # CORRECT - With stack trace
   logger.error(f"Error: {e}", exc_info=True)
   ```

### Verification Commands

```bash
# 1. Test configuration error exit code
uv run python -m guarantee_email_agent run --config missing.yaml
echo "Exit code: $?"  # Should be 2

# 2. Test eval failure exit code
uv run python -m guarantee_email_agent eval
echo "Exit code: $?"  # Should be 4 if <99%, 0 if ≥99%

# 3. Test error hierarchy
uv run python -c "
from guarantee_email_agent.utils.errors import ConfigError

try:
    raise ConfigError(
        message='Missing field',
        code='config_missing_field',
        details={'field': 'api_key'}
    )
except ConfigError as e:
    print(f'Code: {e.code}')
    print(f'Message: {e.message}')
    print(f'Details: {e.details}')
    print(f'String: {str(e)}')
"

# 4. Test error logging
uv run python -c "
import logging
from guarantee_email_agent.utils.errors import MCPError

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('test')

error = MCPError(
    message='Connection failed',
    code='mcp_connection_failed',
    details={'service': 'gmail'}
)

logger.error(f'{error}', exc_info=False, extra={'error_code': error.code})
"

# 5. Test transient marker
uv run python -c "
from guarantee_email_agent.utils.errors import MCPError, ConfigError

mcp_error = MCPError('Timeout', 'mcp_timeout', is_transient=True)
config_error = ConfigError('Invalid', 'config_invalid_value')

print(f'MCP transient: {mcp_error.is_transient}')  # True
print(f'Config transient: {config_error.is_transient}')  # False
"

# 6. Run unit tests
uv run pytest tests/utils/test_errors.py -v
uv run pytest tests/test_exit_codes.py -v

# 7. Test in automation script
#!/bin/bash
uv run python -m guarantee_email_agent eval
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Eval passed (≥99%)"
elif [ $EXIT_CODE -eq 4 ]; then
    echo "✗ Eval failed (<99%)"
    exit 1
else
    echo "✗ Error occurred (code: $EXIT_CODE)"
    exit 1
fi
```

### Dependency Notes

**Depends on:**
- All previous stories for error handling integration
- Story 3.6: Logging infrastructure
- Story 4.1: Eval exit codes

**Blocks:**
- Production deployment: Requires proper error handling
- Monitoring integration: Depends on error codes

**Integration Points:**
- Error hierarchy → All modules
- Exit codes → CLI commands
- Error logging → Structured logging from 3.6
- Retry logic → Story 2.1 MCP clients

### Previous Story Intelligence

From Story 3.6 (Logging):
- Structured logging with extra dict
- Error context enrichment patterns
- Log levels (DEBUG, INFO, WARN, ERROR)

From Story 2.1 (MCP Integration):
- Retry logic with tenacity
- Transient vs permanent error distinction
- Circuit breaker patterns

From Story 4.1 (Eval Framework):
- Exit code 4 for eval failure
- EvalError usage patterns

**Learnings to Apply:**
- Consistent error hierarchy across codebase
- Rich context in all errors
- Proper exit codes for automation
- Comprehensive logging with stack traces
- Transient error retry patterns

### Git Intelligence Summary

Recent commits show:
- Exception handling patterns
- Logging with context
- Exit code usage
- Error recovery logic

**Code Patterns to Continue:**
- Custom exception classes
- Error code patterns
- Context dictionaries
- Stack trace inclusion
- Exit code constants

### References

**Architecture Document Sections:**
- [Source: architecture.md#Error Handling] - Error hierarchy design
- [Source: project-context.md#Error Codes] - Code patterns

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 4: Story 4.3] - Complete acceptance criteria
- [Source: prd.md#NFR28] - Clear, actionable error messages
- [Source: prd.md#NFR29] - Standard exit codes
- [Source: prd.md#NFR5] - No silent failures
- [Source: prd.md#NFR25] - Logs sufficient for troubleshooting
- [Source: prd.md#FR45] - Failed steps logged with details

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context from all previous stories
- Story consolidates 3 original stories (6.1, 6.2, 6.5)
- AgentError base class with message, code, details, is_transient
- Error code pattern: {component}_{error_type}
- Specific subclasses: ConfigError, MCPError, InstructionError, LLMError, ProcessingError, EvalError
- Exit code constants: 0 (success), 1 (general), 2 (config), 3 (MCP), 4 (eval)
- Exception to exit code mapping in CLI
- Comprehensive error logging with stack traces
- Transient vs permanent error distinction
- Error context enrichment with add_context()
- Retry logic for transient errors
- Fail-fast for permanent errors
- User-friendly CLI error messages
- Error handling audit checklist
- Complete testing strategy
- Verification commands for exit codes

### File List

**Error Hierarchy:**
- `src/guarantee_email_agent/utils/errors.py` - Complete error hierarchy

**CLI Updates:**
- `src/guarantee_email_agent/cli.py` - Exit code handling

**Documentation:**
- `README.md` - Add exit codes section
- `ERROR_CODES.md` - Error code registry (optional)

**Tests:**
- `tests/utils/test_errors.py` - Error hierarchy tests
- `tests/test_exit_codes.py` - Exit code tests
- `tests/test_error_logging.py` - Error logging tests
- `tests/test_error_recovery.py` - Error recovery tests
