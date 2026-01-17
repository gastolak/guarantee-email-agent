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
