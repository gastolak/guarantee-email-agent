"""Configuration schema definitions using dataclasses."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MCPConnectionConfig:
    """Configuration for a single MCP connection."""
    connection_string: str
    endpoint: Optional[str] = None


@dataclass
class MCPConfig:
    """MCP integration configuration."""
    gmail: MCPConnectionConfig
    warranty_api: MCPConnectionConfig
    ticketing_system: MCPConnectionConfig


@dataclass
class InstructionsConfig:
    """Instruction file paths configuration."""
    main: str
    scenarios: List[str]


@dataclass
class EvalConfig:
    """Evaluation framework configuration."""
    test_suite_path: str
    pass_threshold: float = 99.0


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    output: str = "stdout"
    file: str = "./logs/agent.log"


@dataclass
class AgentConfig:
    """Top-level agent configuration."""
    mcp: MCPConfig
    instructions: InstructionsConfig
    eval: EvalConfig
    logging: LoggingConfig
