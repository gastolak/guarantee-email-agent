"""Configuration loader for YAML configuration files."""

import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

from guarantee_email_agent.config.schema import (
    AgentConfig,
    AgentRuntimeConfig,
    MCPConfig,
    MCPConnectionConfig,
    InstructionsConfig,
    EvalConfig,
    LLMConfig,
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

    Note:
        At least one of ANTHROPIC_API_KEY or GEMINI_API_KEY must be set.
        The specific one required depends on config.yaml llm.provider setting.
    """
    # Optional LLM API keys (at least one must be provided)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip() or None
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or None

    # Other API keys (can be empty for testing/mock mode)
    gmail_key = os.getenv("GMAIL_API_KEY", "").strip()
    warranty_key = os.getenv("WARRANTY_API_KEY", "").strip()
    ticketing_key = os.getenv("TICKETING_API_KEY", "").strip()

    return SecretsConfig(
        anthropic_api_key=anthropic_key,
        gemini_api_key=gemini_key,
        gmail_api_key=gmail_key,
        warranty_api_key=warranty_key,
        ticketing_api_key=ticketing_key
    )


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

        # Parse agent runtime config (optional, uses defaults if not present)
        agent_config = None
        if 'agent' in raw_config:
            try:
                agent_config = AgentRuntimeConfig(**raw_config['agent'])
            except TypeError as e:
                raise ConfigurationError(
                    message=f"Invalid agent config: {e}",
                    code="config_invalid_type",
                    details={"field": "agent", "error": str(e)}
                )

        return AgentConfig(
            mcp=mcp_config,
            instructions=instructions_config,
            eval=eval_config,
            logging=logging_config,
            secrets=secrets,
            agent=agent_config
        )
    except TypeError as e:
        raise ConfigurationError(
            message=f"Invalid config field type: {e}",
            code="config_invalid_type",
            details={"error": str(e)}
        )
