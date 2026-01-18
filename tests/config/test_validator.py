"""Tests for configuration validator."""

import pytest
from pathlib import Path
from guarantee_email_agent.config.schema import (
    AgentConfig,
    MCPConfig,
    MCPConnectionConfig,
    InstructionsConfig,
    EvalConfig,
    LoggingConfig,
    SecretsConfig
)
from guarantee_email_agent.config.validator import validate_config
from guarantee_email_agent.utils.errors import ConfigurationError


def create_valid_config(tmp_path):
    """Helper to create a valid configuration with existing files."""
    # Create required directories and files
    instructions_dir = tmp_path / "instructions" / "scenarios"
    instructions_dir.mkdir(parents=True, exist_ok=True)

    main_file = tmp_path / "instructions" / "main.md"
    main_file.write_text("# Main instructions")

    scenario_file = instructions_dir / "valid-warranty.md"
    scenario_file.write_text("# Scenario instructions")

    evals_dir = tmp_path / "evals" / "scenarios"
    evals_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(main_file),
            scenarios=tuple([str(scenario_file)])
        ),
        eval=EvalConfig(
            test_suite_path=str(evals_dir),
            pass_threshold=99.0
        ),
        logging=LoggingConfig(
            level="INFO",
            output="stdout",
            file=str(logs_dir / "agent.log")
        ),
        secrets=SecretsConfig(
            anthropic_api_key="test-anthropic-key",
            gmail_api_key="test-gmail-key",
            warranty_api_key="test-warranty-key",
            ticketing_api_key="test-ticketing-key"
        )
    )


def test_validate_valid_config(tmp_path):
    """Test validation passes with complete valid config."""
    config = create_valid_config(tmp_path)
    # Should not raise any exception
    validate_config(config)


def test_validate_missing_gmail_connection_string(tmp_path):
    """Test validation catches missing gmail connection string."""
    # Create config with empty gmail connection_string (immutable, so recreate)
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string=""),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=create_valid_config(tmp_path).instructions,
        eval=create_valid_config(tmp_path).eval,
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "mcp.gmail.connection_string" in exc_info.value.message


def test_validate_missing_warranty_api_connection_string(tmp_path):
    """Test validation catches missing warranty_api connection string."""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string=""),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=create_valid_config(tmp_path).instructions,
        eval=create_valid_config(tmp_path).eval,
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "mcp.warranty_api.connection_string" in exc_info.value.message


def test_validate_missing_ticketing_connection_string(tmp_path):
    """Test validation catches missing ticketing_system connection string."""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="")
        ),
        instructions=create_valid_config(tmp_path).instructions,
        eval=create_valid_config(tmp_path).eval,
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "mcp.ticketing_system.connection_string" in exc_info.value.message


def test_validate_missing_main_instruction_path(tmp_path):
    """Test validation catches missing main instruction path."""
    config = AgentConfig(
        mcp=create_valid_config(tmp_path).mcp,
        instructions=InstructionsConfig(main="", scenarios=tuple(["./test.md"])),
        eval=create_valid_config(tmp_path).eval,
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "instructions.main" in exc_info.value.message


def test_validate_empty_scenarios_list(tmp_path):
    """Test validation catches empty scenarios list."""
    config = AgentConfig(
        mcp=create_valid_config(tmp_path).mcp,
        instructions=InstructionsConfig(main="./test.md", scenarios=tuple()),
        eval=create_valid_config(tmp_path).eval,
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "instructions.scenarios" in exc_info.value.message


def test_validate_missing_eval_test_suite_path(tmp_path):
    """Test validation catches missing eval test_suite_path."""
    config = AgentConfig(
        mcp=create_valid_config(tmp_path).mcp,
        instructions=create_valid_config(tmp_path).instructions,
        eval=EvalConfig(test_suite_path="", pass_threshold=99.0),
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_missing_field"
    assert "eval.test_suite_path" in exc_info.value.message


def test_validate_invalid_eval_threshold_too_low(tmp_path):
    """Test validation catches eval threshold <= 0."""
    config = AgentConfig(
        mcp=create_valid_config(tmp_path).mcp,
        instructions=create_valid_config(tmp_path).instructions,
        eval=EvalConfig(test_suite_path=str(tmp_path / "evals"), pass_threshold=0),
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_invalid_value"
    assert "eval.pass_threshold" in exc_info.value.message


def test_validate_invalid_eval_threshold_too_high(tmp_path):
    """Test validation catches eval threshold > 100."""
    config = AgentConfig(
        mcp=create_valid_config(tmp_path).mcp,
        instructions=create_valid_config(tmp_path).instructions,
        eval=EvalConfig(test_suite_path=str(tmp_path / "evals"), pass_threshold=101),
        logging=create_valid_config(tmp_path).logging,
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_invalid_value"
    assert "eval.pass_threshold" in exc_info.value.message


def test_validate_invalid_log_level(tmp_path):
    """Test validation catches invalid log level."""
    config = AgentConfig(
        mcp=create_valid_config(tmp_path).mcp,
        instructions=create_valid_config(tmp_path).instructions,
        eval=create_valid_config(tmp_path).eval,
        logging=LoggingConfig(level="INVALID", output="stdout", file=str(tmp_path / "logs" / "agent.log")),
        secrets=create_valid_config(tmp_path).secrets
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert exc_info.value.code == "config_invalid_value"
    assert "logging.level" in exc_info.value.message


def test_validate_valid_log_levels(tmp_path):
    """Test validation accepts all valid log levels."""
    valid_levels = ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"]

    for level in valid_levels:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        config = AgentConfig(
            mcp=create_valid_config(tmp_path).mcp,
            instructions=create_valid_config(tmp_path).instructions,
            eval=create_valid_config(tmp_path).eval,
            logging=LoggingConfig(level=level, output="stdout", file=str(logs_dir / "agent.log")),
            secrets=create_valid_config(tmp_path).secrets
        )
        # Should not raise
        validate_config(config)


def test_validate_log_level_case_insensitive(tmp_path):
    """Test validation accepts log levels in any case."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    config = AgentConfig(
        mcp=create_valid_config(tmp_path).mcp,
        instructions=create_valid_config(tmp_path).instructions,
        eval=create_valid_config(tmp_path).eval,
        logging=LoggingConfig(level="info", output="stdout", file=str(logs_dir / "agent.log")),
        secrets=create_valid_config(tmp_path).secrets
    )
    # Should not raise (converted to uppercase internally)
    validate_config(config)
