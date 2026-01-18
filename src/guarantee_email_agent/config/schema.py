"""Configuration schema definitions using dataclasses."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MCPConnectionConfig:
    """Configuration for a single MCP connection."""
    connection_string: str
    endpoint: Optional[str] = None


@dataclass(frozen=True)
class MCPConfig:
    """MCP integration configuration."""
    gmail: MCPConnectionConfig
    warranty_api: MCPConnectionConfig
    ticketing_system: MCPConnectionConfig


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
class SecretsConfig:
    """API keys and credentials loaded from environment variables.

    Immutable (frozen=True) to prevent accidental modification or leakage.
    """
    anthropic_api_key: str
    gmail_api_key: str
    warranty_api_key: str
    ticketing_api_key: str


@dataclass(frozen=True)
class AgentRuntimeConfig:
    """Agent runtime configuration for polling and lifecycle management."""
    polling_interval_seconds: int = 60
    shutdown_timeout_seconds: int = 30
    max_consecutive_errors: int = 10


@dataclass(frozen=True)
class AgentConfig:
    """Top-level agent configuration."""
    mcp: MCPConfig
    instructions: InstructionsConfig
    eval: EvalConfig
    logging: LoggingConfig
    secrets: SecretsConfig
    agent: AgentRuntimeConfig = None  # Optional, defaults will be used

    def __post_init__(self):
        """Ensure agent config exists with defaults."""
        if self.agent is None:
            object.__setattr__(self, 'agent', AgentRuntimeConfig())
