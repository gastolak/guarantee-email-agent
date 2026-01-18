"""Agent error hierarchy with error codes."""


class AgentError(Exception):
    """Base exception for agent errors."""

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
    """Base class for transient errors that should be retried."""
    pass


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


class EvalError(AgentError):
    """Eval framework-related errors."""
    pass
