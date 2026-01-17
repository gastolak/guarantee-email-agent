"""Configuration validator for schema validation."""

from guarantee_email_agent.config.schema import AgentConfig, SecretsConfig
from guarantee_email_agent.utils.errors import ConfigurationError


def validate_secrets(secrets: SecretsConfig) -> None:
    """Validate secrets configuration.

    Args:
        secrets: Loaded secrets configuration

    Raises:
        ConfigurationError: If secrets validation fails
    """
    if not secrets.anthropic_api_key:
        raise ConfigurationError(
            message="ANTHROPIC_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "ANTHROPIC_API_KEY"}
        )

    if not secrets.gmail_api_key:
        raise ConfigurationError(
            message="GMAIL_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "GMAIL_API_KEY"}
        )

    if not secrets.warranty_api_key:
        raise ConfigurationError(
            message="WARRANTY_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "WARRANTY_API_KEY"}
        )

    if not secrets.ticketing_api_key:
        raise ConfigurationError(
            message="TICKETING_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "TICKETING_API_KEY"}
        )


def validate_config(config: AgentConfig) -> None:
    """Validate complete configuration including secrets.

    Args:
        config: Complete agent configuration

    Raises:
        ConfigurationError: If validation fails
    """
    # Validate secrets first
    validate_secrets(config.secrets)

    # Validate MCP connections
    if not config.mcp.gmail.connection_string:
        raise ConfigurationError(
            message="Missing required config field: mcp.gmail.connection_string",
            code="config_missing_field",
            details={"field": "mcp.gmail.connection_string"}
        )

    if not config.mcp.warranty_api.connection_string:
        raise ConfigurationError(
            message="Missing required config field: mcp.warranty_api.connection_string",
            code="config_missing_field",
            details={"field": "mcp.warranty_api.connection_string"}
        )

    if not config.mcp.ticketing_system.connection_string:
        raise ConfigurationError(
            message="Missing required config field: mcp.ticketing_system.connection_string",
            code="config_missing_field",
            details={"field": "mcp.ticketing_system.connection_string"}
        )

    # Validate instructions paths
    if not config.instructions.main:
        raise ConfigurationError(
            message="Missing required config field: instructions.main",
            code="config_missing_field",
            details={"field": "instructions.main"}
        )

    if not config.instructions.scenarios or len(config.instructions.scenarios) == 0:
        raise ConfigurationError(
            message="Missing required config field: instructions.scenarios (must have at least one scenario)",
            code="config_missing_field",
            details={"field": "instructions.scenarios"}
        )

    # Validate eval configuration
    if not config.eval.test_suite_path:
        raise ConfigurationError(
            message="Missing required config field: eval.test_suite_path",
            code="config_missing_field",
            details={"field": "eval.test_suite_path"}
        )

    if config.eval.pass_threshold <= 0 or config.eval.pass_threshold > 100:
        raise ConfigurationError(
            message="Invalid eval.pass_threshold: must be between 0 and 100",
            code="config_invalid_value",
            details={"field": "eval.pass_threshold", "value": config.eval.pass_threshold}
        )

    # Validate logging configuration
    valid_log_levels = ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"]
    if config.logging.level.upper() not in valid_log_levels:
        raise ConfigurationError(
            message=f"Invalid logging.level: must be one of {valid_log_levels}",
            code="config_invalid_value",
            details={"field": "logging.level", "value": config.logging.level, "valid_values": valid_log_levels}
        )
