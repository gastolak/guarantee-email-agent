"""Tests for configuration validator."""

import pytest
from guarantee_email_agent.config.schema import (
    AgentConfig,
    MCPConfig,
    MCPConnectionConfig,
    InstructionsConfig,
    EvalConfig,
    LoggingConfig
)
from guarantee_email_agent.config.validator import validate_config
from guarantee_email_agent.utils.errors import ConfigurationError


def create_valid_config():
    """Helper to create a valid configuration."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main="./instructions/main.md",
            scenarios=["./instructions/scenarios/valid-warranty.md"]
        ),
        eval=EvalConfig(
            test_suite_path="./evals/scenarios/",
            pass_threshold=99.0
        ),
        logging=LoggingConfig(
            level="INFO",
            output="stdout",
            file="./logs/agent.log"
        )
    )


def test_validate_valid_config():
    """Test validation passes with complete valid config."""
    config = create_valid_config()
    # Should not raise any exception
    validate_config(config)


def test_validate_missing_gmail_connection_string():
    """Test validation catches missing gmail connection string."""
    config = create_valid_config()
    config.mcp.gmail.connection_string = ""

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "mcp.gmail.connection_string" in exc_info.value.message


def test_validate_missing_warranty_api_connection_string():
    """Test validation catches missing warranty_api connection string."""
    config = create_valid_config()
    config.mcp.warranty_api.connection_string = ""

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "mcp.warranty_api.connection_string" in exc_info.value.message


def test_validate_missing_ticketing_connection_string():
    """Test validation catches missing ticketing_system connection string."""
    config = create_valid_config()
    config.mcp.ticketing_system.connection_string = ""

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "mcp.ticketing_system.connection_string" in exc_info.value.message


def test_validate_missing_main_instruction_path():
    """Test validation catches missing main instruction path."""
    config = create_valid_config()
    config.instructions.main = ""

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "instructions.main" in exc_info.value.message


def test_validate_empty_scenarios_list():
    """Test validation catches empty scenarios list."""
    config = create_valid_config()
    config.instructions.scenarios = []

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "instructions.scenarios" in exc_info.value.message


def test_validate_missing_eval_test_suite_path():
    """Test validation catches missing eval test_suite_path."""
    config = create_valid_config()
    config.eval.test_suite_path = ""

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "eval.test_suite_path" in exc_info.value.message


def test_validate_invalid_eval_threshold_too_low():
    """Test validation catches eval threshold <= 0."""
    config = create_valid_config()
    config.eval.pass_threshold = 0

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_invalid_value"
    assert "eval.pass_threshold" in exc_info.value.message


def test_validate_invalid_eval_threshold_too_high():
    """Test validation catches eval threshold > 100."""
    config = create_valid_config()
    config.eval.pass_threshold = 101

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_invalid_value"
    assert "eval.pass_threshold" in exc_info.value.message


def test_validate_invalid_log_level():
    """Test validation catches invalid log level."""
    config = create_valid_config()
    config.logging.level = "INVALID"

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_invalid_value"
    assert "logging.level" in exc_info.value.message


def test_validate_valid_log_levels():
    """Test validation accepts all valid log levels."""
    valid_levels = ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"]

    for level in valid_levels:
        config = create_valid_config()
        config.logging.level = level
        # Should not raise
        validate_config(config)


def test_validate_log_level_case_insensitive():
    """Test validation accepts log levels in any case."""
    config = create_valid_config()
    config.logging.level = "info"  # lowercase
    # Should not raise (converted to uppercase internally)
    validate_config(config)
