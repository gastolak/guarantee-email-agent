"""Configuration loader for YAML configuration files."""

import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

from guarantee_email_agent.config.schema import (
    AgentConfig,
    AgentRuntimeConfig,
    ToolsConfig,
    GmailToolConfig, CrmAbacusToolConfig, TicketDefaults,
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
    gmail_key = os.getenv("GMAIL_OAUTH_TOKEN", "").strip()
    warranty_key = os.getenv("CRM_ABACUS_USERNAME", "").strip()
    ticketing_key = os.getenv("CRM_ABACUS_PASSWORD", "").strip()

    return SecretsConfig(
        anthropic_api_key=anthropic_key,
        gemini_api_key=gemini_key,
        gmail_oauth_token=gmail_key,
        crm_abacus_username=warranty_key,
        crm_abacus_password=ticketing_key
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
        # Parse tools config with field path tracking
        try:
            tools_data = raw_config['tools']
        except KeyError:
            raise ConfigurationError(
                message="Missing required config field: tools",
                code="config_missing_field",
                details={"field": "tools"}
            )

        try:
            gmail_tool = GmailToolConfig(**tools_data['gmail'])
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: tools.gmail.{e.args[0] if e.args else 'gmail'}",
                code="config_missing_field",
                details={"field": f"tools.gmail.{e.args[0] if e.args else 'gmail'}"}
            )

        try:
            crm_data = tools_data['crm_abacus'].copy()
            # Parse nested ticket_defaults if present
            if 'ticket_defaults' in crm_data and crm_data['ticket_defaults']:
                crm_data['ticket_defaults'] = TicketDefaults(**crm_data['ticket_defaults'])
            crm_abacus_tool = CrmAbacusToolConfig(**crm_data)
        except KeyError as e:
            raise ConfigurationError(
                message=f"Missing required config field: tools.crm_abacus.{e.args[0] if e.args else 'crm_abacus'}",
                code="config_missing_field",
                details={"field": f"tools.crm_abacus.{e.args[0] if e.args else 'crm_abacus'}"}
            )

        tools_config = ToolsConfig(
            gmail=gmail_tool,
            crm_abacus=crm_abacus_tool
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

        # Parse LLM config (optional, uses defaults if not present)
        llm_config = None
        if 'llm' in raw_config:
            try:
                llm_config = LLMConfig(**raw_config['llm'])
            except TypeError as e:
                raise ConfigurationError(
                    message=f"Invalid llm config: {e}",
                    code="config_invalid_type",
                    details={"field": "llm", "error": str(e)}
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
            tools=tools_config,
            instructions=instructions_config,
            eval=eval_config,
            logging=logging_config,
            secrets=secrets,
            llm=llm_config,
            agent=agent_config
        )
    except TypeError as e:
        raise ConfigurationError(
            message=f"Invalid config field type: {e}",
            code="config_invalid_type",
            details={"error": str(e)}
        )
