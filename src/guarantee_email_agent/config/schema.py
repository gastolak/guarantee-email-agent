"""Configuration schema definitions using dataclasses."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class GmailToolConfig:
    """Gmail tool configuration."""
    api_endpoint: str = "https://gmail.googleapis.com/gmail/v1"
    timeout_seconds: int = 10


@dataclass(frozen=True)
class TicketDefaults:
    """Default IDs for CRM Abacus ticket creation."""
    dzial_id: int = 2  # Customer Service Department
    typ_zadania_id: int = 156  # Service Request
    typ_wykonania_id: int = 184  # Awaiting Review
    organizacja_id: int = 1  # Suntar
    unrecognized_klient_id: int = 702  # Default when client not found


@dataclass(frozen=True)
class CrmAbacusToolConfig:
    """CRM Abacus tool configuration."""
    base_url: str
    token_endpoint: str = "/token"
    warranty_endpoint: str = "/klienci/znajdz_po_numerze_seryjnym/"
    ticketing_endpoint: str = "/zadania/dodaj_zadanie/"
    ticket_info_endpoint: str = "/zadania/{zadanie_id}/info/"
    task_info_endpoint: str = "/zadania/{zadanie_id}"
    task_feature_check_endpoint: str = "/zadania/{zadanie_id}/cechy/check"
    timeout_seconds: int = 10
    ticket_defaults: TicketDefaults = None
    agent_disable_feature_name: str = "Wyłącz agenta AI"

    def __post_init__(self):
        """Ensure ticket_defaults exists."""
        if self.ticket_defaults is None:
            object.__setattr__(self, 'ticket_defaults', TicketDefaults())


@dataclass(frozen=True)
class ToolsConfig:
    """Tool integrations configuration."""
    gmail: GmailToolConfig
    crm_abacus: CrmAbacusToolConfig


@dataclass(frozen=True)
class InstructionsConfig:
    """Instruction file paths configuration."""
    main: str
    scenarios: tuple  # Changed from List to tuple for immutability
    scenarios_dir: str = "instructions/scenarios"  # Directory for scenario instruction files


@dataclass(frozen=True)
class EvalConfig:
    """Evaluation framework configuration."""
    test_suite_path: str
    pass_threshold: float = 99.0


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration.

    NFR14: Customer email body logged ONLY at DEBUG level
    NFR16: Logs to stdout only (stateless, no files)
    """
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    json_format: bool = False  # True for production (machine-readable), False for development
    log_to_stdout: bool = True  # Always True per NFR16 (stateless)


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "anthropic"  # "anthropic" or "gemini"
    model: str = "claude-3-5-sonnet-20241022"  # Model name for the provider
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout_seconds: int = 15


@dataclass(frozen=True)
class SecretsConfig:
    """API keys and credentials loaded from environment variables.

    Immutable (frozen=True) to prevent accidental modification or leakage.
    """
    anthropic_api_key: Optional[str] = None  # Required if provider=anthropic
    gemini_api_key: Optional[str] = None  # Required if provider=gemini
    gmail_oauth_token: str = ""  # Gmail OAuth2 token
    crm_abacus_username: str = ""  # CRM Abacus username for token acquisition
    crm_abacus_password: str = ""  # CRM Abacus password for token acquisition


@dataclass(frozen=True)
class AgentRuntimeConfig:
    """Agent runtime configuration for polling and lifecycle management."""
    polling_interval_seconds: int = 60
    shutdown_timeout_seconds: int = 30
    max_consecutive_errors: int = 10


@dataclass(frozen=True)
class AgentConfig:
    """Top-level agent configuration."""
    tools: ToolsConfig
    instructions: InstructionsConfig
    eval: EvalConfig
    logging: LoggingConfig
    secrets: SecretsConfig
    llm: LLMConfig = None  # Optional, defaults will be used
    agent: AgentRuntimeConfig = None  # Optional, defaults will be used

    def __post_init__(self):
        """Ensure agent and llm configs exist with defaults."""
        if self.agent is None:
            object.__setattr__(self, 'agent', AgentRuntimeConfig())
        if self.llm is None:
            object.__setattr__(self, 'llm', LLMConfig())
