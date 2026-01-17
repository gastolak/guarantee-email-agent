"""Configuration loader for YAML configuration files."""

import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

from guarantee_email_agent.config.schema import (
    AgentConfig,
    MCPConfig,
    MCPConnectionConfig,
    InstructionsConfig,
    EvalConfig,
    LoggingConfig,
    SecretsConfig
)
from guarantee_email_agent.utils.errors import ConfigurationError

# Load .env file at module import time
load_dotenv()


def load_secrets() -> SecretsConfig:
    """Load secrets from environment variables.

    Returns:
        SecretsConfig: Loaded API keys and credentials

    Raises:
        ConfigurationError: If required environment variable is missing
    """
    required_secrets = {
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "GMAIL_API_KEY": "gmail_api_key",
        "WARRANTY_API_KEY": "warranty_api_key",
        "TICKETING_API_KEY": "ticketing_api_key",
    }

    secrets = {}
    for env_var, field_name in required_secrets.items():
        value = os.getenv(env_var)
        if not value or value.strip() == "":
            raise ConfigurationError(
                message=f"Missing required environment variable: {env_var}",
                code="config_missing_secret",
                details={"env_var": env_var}
            )
        secrets[field_name] = value.strip()

    return SecretsConfig(**secrets)


def load_config(config_path: str = None) -> AgentConfig:
    """Load and parse YAML configuration file and environment variables.

    Args:
        config_path: Path to config.yaml (default: from CONFIG_PATH env var or "config.yaml")

    Returns:
        AgentConfig: Complete configuration including secrets

    Raises:
        ConfigurationError: If config invalid or secrets missing
    """
    # Allow CONFIG_PATH environment variable to override default
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config.yaml")

    # Load secrets first (fail fast if missing)
    secrets = load_secrets()

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
            logging=logging_config,
            secrets=secrets
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
