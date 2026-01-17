"""Configuration loader for YAML configuration files."""

from pathlib import Path
import yaml

from guarantee_email_agent.config.schema import (
    AgentConfig,
    MCPConfig,
    MCPConnectionConfig,
    InstructionsConfig,
    EvalConfig,
    LoggingConfig
)
from guarantee_email_agent.utils.errors import ConfigurationError


def load_config(config_path: str = "config.yaml") -> AgentConfig:
    """Load and parse YAML configuration file.

    Args:
        config_path: Path to config.yaml file

    Returns:
        AgentConfig: Parsed configuration object

    Raises:
        ConfigurationError: If YAML is invalid or cannot be parsed
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise ConfigurationError(
            message=f"Configuration file not found: {config_path}",
            code="config_file_not_found",
            details={"config_path": config_path}
        )

    try:
        with open(config_file, 'r') as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(
            message="Configuration file is not valid YAML",
            code="config_invalid_yaml",
            details={"config_path": config_path, "error": str(e)}
        )

    # Parse nested sections into dataclasses
    try:
        mcp_config = MCPConfig(
            gmail=MCPConnectionConfig(**raw_config['mcp']['gmail']),
            warranty_api=MCPConnectionConfig(**raw_config['mcp']['warranty_api']),
            ticketing_system=MCPConnectionConfig(**raw_config['mcp']['ticketing_system'])
        )

        instructions_config = InstructionsConfig(**raw_config['instructions'])
        eval_config = EvalConfig(**raw_config['eval'])
        logging_config = LoggingConfig(**raw_config['logging'])

        return AgentConfig(
            mcp=mcp_config,
            instructions=instructions_config,
            eval=eval_config,
            logging=logging_config
        )
    except KeyError as e:
        raise ConfigurationError(
            message=f"Missing required config field: {e}",
            code="config_missing_field",
            details={"field": str(e)}
        )
    except TypeError as e:
        raise ConfigurationError(
            message=f"Invalid config field type: {e}",
            code="config_invalid_type",
            details={"error": str(e)}
        )
