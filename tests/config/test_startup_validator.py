import pytest
from pathlib import Path
from guarantee_email_agent.config.startup_validator import validate_startup
from guarantee_email_agent.config.schema import (
    AgentConfig,
    InstructionsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
    SecretsConfig
)
from guarantee_email_agent.utils.errors import ConfigurationError, MCPConnectionError


def test_validate_startup_with_valid_config(tmp_path):
    """Test complete startup validation with valid configuration"""
    # Create test instruction files
    main_file = tmp_path / "main.md"
    main_file.write_text("""---
name: main
description: Main instruction
version: 1.0.0
---

<objective>Test</objective>
""")

    scenario_file = tmp_path / "scenario.md"
    scenario_file.write_text("""---
name: scenario
description: Scenario instruction
version: 1.0.0
---

<objective>Test scenario</objective>
""")

    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(main_file),
            scenarios=[str(scenario_file)]
        ),
        eval=EvalConfig(test_suite_path=str(eval_dir)),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    # Should not raise
    validate_startup(config)


def test_validate_startup_fails_on_missing_instruction_file(tmp_path):
    """Test startup validation fails when instruction file is missing"""
    missing_main = tmp_path / "missing_main.md"
    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(missing_main),
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path=str(eval_dir)),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(ConfigurationError) as exc_info:
        validate_startup(config)

    assert exc_info.value.code == "config_file_not_found"


def test_validate_startup_fails_on_invalid_mcp_connection(tmp_path):
    """Test startup validation fails when MCP connection string is invalid"""
    main_file = tmp_path / "main.md"
    main_file.write_text("""---
name: main
description: Main instruction
version: 1.0.0
---

<objective>Test</objective>
""")
    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="http://gmail"),  # Invalid
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(main_file),
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path=str(eval_dir)),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(MCPConnectionError) as exc_info:
        validate_startup(config)

    assert exc_info.value.code == "mcp_invalid_connection_string"


def test_validate_startup_creates_eval_directory_if_missing(tmp_path):
    """Test startup validation creates eval directory if it doesn't exist"""
    main_file = tmp_path / "main.md"
    main_file.write_text("""---
name: main
description: Main instruction
version: 1.0.0
---

<objective>Test</objective>
""")
    eval_dir = tmp_path / "evals"  # Not created yet

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(main_file),
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path=str(eval_dir)),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    # Should not raise and should create directory
    validate_startup(config)

    assert eval_dir.exists()
    assert eval_dir.is_dir()


def test_validate_startup_timing_within_limits(tmp_path):
    """Test startup validation completes within reasonable time"""
    import time

    main_file = tmp_path / "main.md"
    main_file.write_text("""---
name: main
description: Main instruction
version: 1.0.0
---

<objective>Test</objective>
""")
    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(main_file),
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path=str(eval_dir)),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    start_time = time.time()
    validate_startup(config)
    elapsed_time = time.time() - start_time

    # Should complete well within 30 seconds (using 5s as generous limit for tests)
    assert elapsed_time < 5.0, f"Startup validation took {elapsed_time:.2f}s (expected < 5s)"
