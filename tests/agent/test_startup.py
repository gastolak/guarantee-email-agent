"""Tests for agent startup validation."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from guarantee_email_agent.agent.startup import (
    validate_startup,
    validate_config,
    validate_secrets,
    validate_instructions,
    validate_mcp_connections,
)
from guarantee_email_agent.config.schema import (
    AgentConfig,
    AgentRuntimeConfig,
    InstructionsConfig,
    SecretsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
    LLMConfig,
)
from guarantee_email_agent.utils.errors import ConfigurationError, MCPConnectionError


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock agent config for testing."""
    # Create temp instruction files with all required fields
    main_inst = tmp_path / "main.md"
    main_inst.write_text("---\nname: main\ndescription: Test main instruction\nversion: 1.0.0\n---\n<instruction>test</instruction>")

    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()

    for scenario in ["valid-warranty", "invalid-warranty", "missing-info", "graceful-degradation"]:
        (scenarios_dir / f"{scenario}.md").write_text(f"---\nname: {scenario}\ndescription: Test {scenario}\nversion: 1.0.0\n---\n<scenario>test</scenario>")

    return AgentConfig(
        llm=LLMConfig(
            provider="gemini",
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=8192,
            timeout_seconds=15
        ),
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="gmail://test"),
            warranty_api=MCPConnectionConfig(connection_string="warranty://test"),
            ticketing_system=MCPConnectionConfig(connection_string="ticket://test"),
        ),
        instructions=InstructionsConfig(
            main=str(main_inst),
            scenarios=("valid-warranty",),
            scenarios_dir=str(scenarios_dir),
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(),
        secrets=SecretsConfig(
            anthropic_api_key="test-anthropic-key",
            gemini_api_key="test-gemini-key",
            gmail_api_key="gmail-key",
            warranty_api_key="warranty-key",
            ticketing_api_key="ticket-key",
        ),
        agent=AgentRuntimeConfig(polling_interval_seconds=60),
    )


@pytest.mark.asyncio
async def test_validate_startup_success(mock_config):
    """Test successful startup validation."""
    await validate_startup(mock_config)
    # Should complete without raising exceptions


def test_validate_config_success(mock_config):
    """Test config validation with valid config."""
    validate_config(mock_config)
    # Should complete without raising exceptions


def test_validate_config_invalid_polling_interval(mock_config):
    """Test config validation fails with invalid polling interval."""
    bad_config = AgentConfig(
        mcp=mock_config.mcp,
        instructions=mock_config.instructions,
        eval=mock_config.eval,
        logging=mock_config.logging,
        secrets=mock_config.secrets,
        agent=AgentRuntimeConfig(polling_interval_seconds=5),  # Too low
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(bad_config)

    assert "Polling interval must be >= 10 seconds" in str(exc_info.value.message)
    assert exc_info.value.code == "invalid_polling_interval"


def test_validate_config_missing_main_instruction(tmp_path):
    """Test config validation fails with missing main instruction path."""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="gmail://test"),
            warranty_api=MCPConnectionConfig(connection_string="warranty://test"),
            ticketing_system=MCPConnectionConfig(connection_string="ticket://test"),
        ),
        instructions=InstructionsConfig(
            main="",  # Empty path
            scenarios=(),
            scenarios_dir=str(tmp_path),
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="gmail-key",
            warranty_api_key="warranty-key",
            ticketing_api_key="ticket-key",
        ),
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_config(config)

    assert "Main instruction path not configured" in str(exc_info.value.message)


def test_validate_secrets_success(mock_config):
    """Test secrets validation with all required secrets present."""
    validate_secrets(mock_config)
    # Should complete without raising exceptions


def test_validate_secrets_missing_anthropic_key():
    """Test secrets validation fails when Anthropic key missing for Anthropic provider."""
    config = AgentConfig(
        llm=LLMConfig(
            provider="anthropic",  # Using Anthropic provider
            model="claude-3-5-sonnet-20241022",
            temperature=0,
            max_tokens=8192,
            timeout_seconds=15
        ),
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="gmail://test"),
            warranty_api=MCPConnectionConfig(connection_string="warranty://test"),
            ticketing_system=MCPConnectionConfig(connection_string="ticket://test"),
        ),
        instructions=InstructionsConfig(
            main="main.md",
            scenarios=(),
            scenarios_dir="scenarios",
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(),
        secrets=SecretsConfig(
            anthropic_api_key="",  # Missing!
            gemini_api_key="gemini-key",  # Has Gemini key but using Anthropic provider
            gmail_api_key="gmail-key",
            warranty_api_key="warranty-key",
            ticketing_api_key="ticket-key",
        ),
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_secrets(config)

    assert "Missing required secrets" in str(exc_info.value.message)
    assert "ANTHROPIC_API_KEY" in str(exc_info.value.message)


def test_validate_instructions_success(mock_config):
    """Test instruction file validation with all files present."""
    validate_instructions(mock_config)
    # Should complete without raising exceptions


def test_validate_instructions_main_not_found(mock_config):
    """Test instruction validation fails when main instruction missing."""
    bad_config = AgentConfig(
        mcp=mock_config.mcp,
        instructions=InstructionsConfig(
            main="/nonexistent/main.md",  # Doesn't exist
            scenarios=mock_config.instructions.scenarios,
            scenarios_dir=mock_config.instructions.scenarios_dir,
        ),
        eval=mock_config.eval,
        logging=mock_config.logging,
        secrets=mock_config.secrets,
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_instructions(bad_config)

    assert "Main instruction file not found" in str(exc_info.value.message)
    assert exc_info.value.code == "main_instruction_not_found"


def test_validate_instructions_scenario_not_found(mock_config, tmp_path):
    """Test instruction validation fails when required scenario missing."""
    scenarios_dir = tmp_path / "incomplete_scenarios"
    scenarios_dir.mkdir()

    # Only create some scenarios with proper format, not all required ones
    (scenarios_dir / "valid-warranty.md").write_text("---\nname: test\ndescription: Test\nversion: 1.0.0\n---\n<scenario>test</scenario>")

    bad_config = AgentConfig(
        mcp=mock_config.mcp,
        instructions=InstructionsConfig(
            main=mock_config.instructions.main,
            scenarios=mock_config.instructions.scenarios,
            scenarios_dir=str(scenarios_dir),  # Missing required scenarios
        ),
        eval=mock_config.eval,
        logging=mock_config.logging,
        secrets=mock_config.secrets,
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_instructions(bad_config)

    assert "Required scenario file not found" in str(exc_info.value.message)
    assert exc_info.value.code == "required_scenario_not_found"


@pytest.mark.asyncio
async def test_validate_mcp_connections_success(mock_config):
    """Test MCP connection validation (stub implementation)."""
    await validate_mcp_connections(mock_config)
    # Should complete without raising exceptions (stub for Story 2.1)


@pytest.mark.asyncio
async def test_validate_startup_timing(mock_config):
    """Test that startup validation completes quickly."""
    import time

    start = time.time()
    await validate_startup(mock_config)
    duration_ms = (time.time() - start) * 1000

    # Should complete well under 10 seconds
    assert duration_ms < 10000, f"Validation took {duration_ms}ms, exceeds 10s target"
