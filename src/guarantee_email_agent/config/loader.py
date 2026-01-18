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

    # Parse nested sections into dataclasses with detailed error tracking
    try:
        # Parse MCP config with field path tracking
        try:
            mcp_data = raw_config['mcp']
        except KeyError:
            raise ConfigurationError(
                message="Missing required config field: mcp",
                code="config_missing_field",
                details={"field": "mcp"}
            )

        try:
            gmail_conn = MCPConnectionConfig(**mcp_data['gmail'])
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: mcp.gmail.{e.args[0] if e.args else 'gmail'}",
                code="config_missing_field",
                details={"field": f"mcp.gmail.{e.args[0] if e.args else 'gmail'}"}
            )

        try:
            warranty_conn = MCPConnectionConfig(**mcp_data['warranty_api'])
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: mcp.warranty_api.{e.args[0] if e.args else 'warranty_api'}",
                code="config_missing_field",
                details={"field": f"mcp.warranty_api.{e.args[0] if e.args else 'warranty_api'}"}
            )

        try:
            ticketing_conn = MCPConnectionConfig(**mcp_data['ticketing_system'])
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: mcp.ticketing_system.{e.args[0] if e.args else 'ticketing_system'}",
                code="config_missing_field",
                details={"field": f"mcp.ticketing_system.{e.args[0] if e.args else 'ticketing_system'}"}
            )

        mcp_config = MCPConfig(
            gmail=gmail_conn,
            warranty_api=warranty_conn,
            ticketing_system=ticketing_conn
        )

        # Parse instructions config
        try:
            instructions_data = raw_config['instructions'].copy()
            instructions_data['scenarios'] = tuple(instructions_data['scenarios'])
            instructions_config = InstructionsConfig(**instructions_data)
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: instructions.{e.args[0] if e.args else 'instructions'}",
                code="config_missing_field",
                details={"field": f"instructions.{e.args[0] if e.args else 'instructions'}"}
            )

        # Parse eval config
        try:
            eval_config = EvalConfig(**raw_config['eval'])
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: eval.{e.args[0] if e.args else 'eval'}",
                code="config_missing_field",
                details={"field": f"eval.{e.args[0] if e.args else 'eval'}"}
            )

        # Parse logging config
        try:
            logging_config = LoggingConfig(**raw_config['logging'])
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: logging.{e.args[0] if e.args else 'logging'}",
                code="config_missing_field",
                details={"field": f"logging.{e.args[0] if e.args else 'logging'}"}
            )

        return AgentConfig(
            mcp=mcp_config,
            instructions=instructions_config,
            eval=eval_config,
            logging=logging_config,
            secrets=secrets
        )
    except TypeError as e:
        raise ConfigurationError(
            message=f"Invalid config field type: {e}",
            code="config_invalid_type",
            details={"error": str(e)}
        )
