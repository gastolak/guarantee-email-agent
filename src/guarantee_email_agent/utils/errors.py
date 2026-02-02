"""Agent error hierarchy with error codes.

Error code pattern: {component}_{error_type}
Components: config, mcp, instruction, llm, processing, eval, email
Error types: connection_failed, parse_error, timeout, validation_error, not_found

Examples:
- mcp_connection_failed
- instruction_parse_error
- llm_timeout
- config_missing_field
"""

# Exit code constants (NFR29)
EXIT_SUCCESS = 0  # Success
EXIT_GENERAL_ERROR = 1  # General/unexpected errors
EXIT_CONFIG_ERROR = 2  # Configuration errors
EXIT_MCP_ERROR = 3  # MCP connection failures during startup (kept for backward compat)
EXIT_INTEGRATION_ERROR = 3  # Integration failures (tools, APIs) during startup
EXIT_EVAL_FAILURE = 4  # Eval pass rate <99%


class AgentError(Exception):
    """Base exception for agent errors.

    All domain errors should use this hierarchy with appropriate
    error codes and contextual details for debugging.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code following pattern {component}_{error_type}
        details: Dict with additional error context (serial_number, file_path, etc.)
    """

    def __init__(self, message: str, code: str, details: dict = None):
        """Initialize AgentError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code (e.g., 'config_missing_field')
            details: Optional dict with additional error context
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation with code and key details."""
        parts = [f"{self.message} (code: {self.code})"]
        if self.details:
            # Show first 3 detail items for brevity
            detail_items = list(self.details.items())[:3]
            detail_str = ", ".join(f"{k}={v}" for k, v in detail_items)
            parts.append(f"[{detail_str}]")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"details={self.details!r})"
        )

    def add_context(self, **kwargs) -> "AgentError":
        """Add additional context to error details.

        Useful for enriching errors during exception handling.

        Args:
            **kwargs: Key-value pairs to add to details dict

        Returns:
            Self for method chaining

        Example:
            try:
                process_email(email)
            except AgentError as e:
                raise e.add_context(email_id="123", serial="SN456")
        """
        self.details.update(kwargs)
        return self

    @property
    def is_transient(self) -> bool:
        """Check if error is transient and should be retried.

        Transient errors: timeouts, network errors, rate limits, 5xx responses
        Permanent errors: validation errors, auth failures, 4xx (except 429)

        Returns:
            True if error should be retried, False otherwise
        """
        # Default: permanent unless explicitly transient
        # Subclasses can override or use TransientError base class
        return False


class ConfigurationError(AgentError):
    """Configuration-related errors."""
    pass


class MCPConnectionError(AgentError):
    """MCP connection-related errors."""
    pass


class InstructionError(AgentError):
    """Base class for instruction-related errors."""
    pass


class InstructionParseError(InstructionError):
    """Instruction file parsing failures."""
    pass


class InstructionValidationError(InstructionError):
    """Instruction file validation failures."""
    pass


class TransientError(AgentError):
    """Base class for transient errors that should be retried.

    Transient errors include:
    - Network timeouts
    - Connection failures
    - Rate limiting (429)
    - 5xx server errors
    - Temporary resource unavailability
    """

    @property
    def is_transient(self) -> bool:
        """Transient errors should always be retried."""
        return True


class LLMError(AgentError):
    """Base class for LLM-related errors."""
    pass


class LLMTimeoutError(TransientError):
    """LLM timeout - transient, should retry."""
    pass


class LLMRateLimitError(TransientError):
    """Rate limit - transient, should retry."""
    pass


class LLMConnectionError(TransientError):
    """Connection error - transient, should retry."""
    pass


class LLMAuthenticationError(LLMError):
    """Auth error - non-transient, do NOT retry."""
    pass


class EmailParseError(AgentError):
    """Email parsing failures."""
    pass


class ProcessingError(AgentError):
    """Email processing pipeline failures.

    Use for errors during email processing steps:
    - Parsing failures
    - Serial number extraction failures
    - Scenario detection failures
    - Response generation failures

    Include in details: email_id, serial_number, failed_step
    """
    pass


class EvalError(AgentError):
    """Eval framework-related errors.

    Use for eval test case errors:
    - Test case file not found
    - YAML parsing errors
    - Execution failures
    - Validation errors

    Include in details: scenario_id, file_path
    """
    pass


class IntegrationError(TransientError):
    """External API integration errors.

    Use for tool/API call failures:
    - HTTP errors (5xx, connection errors)
    - API timeouts
    - Service unavailable
    - Network failures

    Most integration errors are transient and should be retried.
    Permanent errors (404, 403) can be caught and handled specifically.

    Include in details: tool_name, operation, status_code, endpoint
    """
    pass
