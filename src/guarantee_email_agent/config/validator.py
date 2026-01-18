"""Configuration validator for schema validation."""

from pathlib import Path
from urllib.parse import urlparse
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

    # Validate MCP endpoint URLs if provided
    def validate_endpoint_url(endpoint: str, field_name: str) -> None:
        """Validate that endpoint URL has valid scheme."""
        if endpoint:
            parsed = urlparse(endpoint)
            if parsed.scheme not in ("http", "https"):
                raise ConfigurationError(
                    message=f"Invalid {field_name}: URL must use http or https scheme",
                    code="config_invalid_url",
                    details={"field": field_name, "value": endpoint, "valid_schemes": ["http", "https"]}
                )

    validate_endpoint_url(config.mcp.gmail.endpoint, "mcp.gmail.endpoint")
    validate_endpoint_url(config.mcp.warranty_api.endpoint, "mcp.warranty_api.endpoint")
    validate_endpoint_url(config.mcp.ticketing_system.endpoint, "mcp.ticketing_system.endpoint")

    # Validate instructions paths
    if not config.instructions.main:
        raise ConfigurationError(
            message="Missing required config field: instructions.main",
            code="config_missing_field",
            details={"field": "instructions.main"}
        )

    # Check for empty scenarios list BEFORE file existence check
    if not config.instructions.scenarios or len(config.instructions.scenarios) == 0:
        raise ConfigurationError(
            message="Missing required config field: instructions.scenarios (must have at least one scenario)",
            code="config_missing_field",
            details={"field": "instructions.scenarios"}
        )

    # Validate main instruction file exists
    main_path = Path(config.instructions.main)
    if not main_path.exists():
        raise ConfigurationError(
            message=f"Instruction file not found: {config.instructions.main}",
            code="config_path_not_found",
            details={"field": "instructions.main", "path": str(main_path)}
        )

    # Validate scenario files exist
    for i, scenario_path in enumerate(config.instructions.scenarios):
        scenario_file = Path(scenario_path)
        if not scenario_file.exists():
            raise ConfigurationError(
                message=f"Scenario instruction file not found: {scenario_path}",
                code="config_path_not_found",
                details={"field": f"instructions.scenarios[{i}]", "path": str(scenario_file)}
            )

    # Validate eval configuration
    if not config.eval.test_suite_path:
        raise ConfigurationError(
            message="Missing required config field: eval.test_suite_path",
            code="config_missing_field",
            details={"field": "eval.test_suite_path"}
        )

    # Validate eval test suite path exists
    eval_path = Path(config.eval.test_suite_path)
    if not eval_path.exists():
        raise ConfigurationError(
            message=f"Evaluation test suite path not found: {config.eval.test_suite_path}",
            code="config_path_not_found",
            details={"field": "eval.test_suite_path", "path": str(eval_path)}
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

    # Validate log file directory exists (create if needed for fail-fast)
    log_file_path = Path(config.logging.file)
    log_dir = log_file_path.parent
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigurationError(
                message=f"Cannot create log directory: {log_dir}",
                code="config_path_not_found",
                details={"field": "logging.file", "path": str(log_dir), "error": str(e)}
            )
