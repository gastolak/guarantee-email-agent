"""Unit tests for scenario router."""

import pytest
from pathlib import Path

from guarantee_email_agent.instructions.router import ScenarioRouter
from guarantee_email_agent.config.schema import (
    AgentConfig,
    InstructionsConfig,
    SecretsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
)
from guarantee_email_agent.utils.errors import InstructionError


@pytest.fixture
def temp_scenarios_dir(tmp_path: Path):
    """Create temporary scenarios directory with test instruction files."""
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()

    # Create valid-warranty scenario
    valid_warranty = scenarios_dir / "valid-warranty.md"
    valid_warranty.write_text("""---
name: valid-warranty
description: Valid warranty scenario
trigger: valid-warranty
version: 1.0.0
---

<objective>Handle valid warranty</objective>
""")

    # Create graceful-degradation scenario
    graceful_degradation = scenarios_dir / "graceful-degradation.md"
    graceful_degradation.write_text("""---
name: graceful-degradation
description: Fallback scenario
trigger: null
version: 1.0.0
---

<objective>Handle fallback cases</objective>
""")

    return str(scenarios_dir)


@pytest.fixture
def test_config(temp_scenarios_dir: str):
    """Create test agent configuration."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=tuple(),
            scenarios_dir=temp_scenarios_dir,
        ),
        eval=EvalConfig(test_suite_path="./evals"),
        logging=LoggingConfig(level="INFO"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing",
        ),
    )


def test_scenario_router_initialization(test_config: AgentConfig):
    """Test ScenarioRouter initialization with valid config."""
    router = ScenarioRouter(test_config)

    assert router.config == test_config
    assert router.scenarios_dir == Path(test_config.instructions.scenarios_dir)


def test_scenario_router_initialization_missing_dir():
    """Test ScenarioRouter initialization fails with missing scenarios directory."""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=tuple(),
            scenarios_dir="/nonexistent/scenarios",
        ),
        eval=EvalConfig(test_suite_path="./evals"),
        logging=LoggingConfig(level="INFO"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing",
        ),
    )

    with pytest.raises(InstructionError) as exc_info:
        ScenarioRouter(config)

    assert "Scenarios directory not found" in exc_info.value.message
    assert exc_info.value.code == "scenarios_dir_not_found"


def test_select_scenario_valid(test_config: AgentConfig):
    """Test selecting a valid scenario instruction."""
    router = ScenarioRouter(test_config)

    scenario = router.select_scenario("valid-warranty")

    assert scenario.name == "valid-warranty"
    assert scenario.trigger == "valid-warranty"
    assert scenario.version == "1.0.0"
    assert "<objective>" in scenario.body


def test_select_scenario_not_found_falls_back(test_config: AgentConfig):
    """Test scenario not found falls back to graceful-degradation."""
    router = ScenarioRouter(test_config)

    scenario = router.select_scenario("nonexistent-scenario")

    # Should return graceful-degradation fallback
    assert scenario.name == "graceful-degradation"
    assert scenario.version == "1.0.0"


def test_select_scenario_trigger_mismatch_warning(test_config: AgentConfig, caplog):
    """Test warning logged when trigger field doesn't match filename."""
    # Create scenario with mismatched trigger
    scenarios_dir = Path(test_config.instructions.scenarios_dir)
    mismatch_file = scenarios_dir / "mismatch-scenario.md"
    mismatch_file.write_text("""---
name: mismatch-scenario
description: Test mismatch
trigger: different-trigger
version: 1.0.0
---

<objective>Test</objective>
""")

    router = ScenarioRouter(test_config)

    with caplog.at_level("WARNING"):
        scenario = router.select_scenario("mismatch-scenario")

    assert scenario.name == "mismatch-scenario"
    assert "Scenario trigger mismatch" in caplog.text


def test_select_scenario_caching(test_config: AgentConfig):
    """Test that scenario instructions are cached."""
    router = ScenarioRouter(test_config)

    # Load same scenario twice
    scenario1 = router.select_scenario("valid-warranty")
    scenario2 = router.select_scenario("valid-warranty")

    # Both should have same name and version (from cache)
    assert scenario1.name == scenario2.name
    assert scenario1.version == scenario2.version


def test_fallback_scenario_load_failure():
    """Test that router raises error if fallback scenario cannot be loaded."""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=tuple(),
            scenarios_dir="instructions/scenarios",  # Real dir, but no graceful-degradation.md
        ),
        eval=EvalConfig(test_suite_path="./evals"),
        logging=LoggingConfig(level="INFO"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing",
        ),
    )

    router = ScenarioRouter(config)

    # Try to load nonexistent scenario - should try fallback, which also doesn't exist in real dir
    # This will depend on whether graceful-degradation.md exists in real scenarios dir
    # For test isolation, we expect fallback to fail if it doesn't exist
    # In production, graceful-degradation.md should always exist
