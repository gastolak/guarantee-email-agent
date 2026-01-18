import pytest
from pathlib import Path
from guarantee_email_agent.config.path_verifier import (
    verify_file_exists,
    verify_instruction_paths,
    verify_eval_paths
)
from guarantee_email_agent.config.schema import (
    AgentConfig,
    InstructionsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
    SecretsConfig
)
from guarantee_email_agent.utils.errors import ConfigurationError


def test_verify_file_exists_with_valid_file(tmp_path):
    """Test verifying a file that exists"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    # Should not raise
    verify_file_exists(str(test_file), "Test file")


def test_verify_file_exists_missing_file(tmp_path):
    """Test verifying a file that doesn't exist"""
    missing_file = tmp_path / "missing.txt"

    with pytest.raises(ConfigurationError) as exc_info:
        verify_file_exists(str(missing_file), "Test file")

    assert exc_info.value.code == "config_file_not_found"
    assert "missing.txt" in exc_info.value.message


def test_verify_file_exists_unreadable_file(tmp_path):
    """Test verifying a file that isn't readable"""
    test_file = tmp_path / "unreadable.txt"
    test_file.write_text("content")
    test_file.chmod(0o000)  # Remove all permissions

    try:
        with pytest.raises(ConfigurationError) as exc_info:
            verify_file_exists(str(test_file), "Test file")

        assert exc_info.value.code in ["config_file_unreadable", "config_file_error"]
    finally:
        # Restore permissions for cleanup
        test_file.chmod(0o644)


def test_verify_file_exists_directory_not_file(tmp_path):
    """Test verifying a directory instead of file"""
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()

    with pytest.raises(ConfigurationError) as exc_info:
        verify_file_exists(str(test_dir), "Test file")

    assert exc_info.value.code == "config_invalid_path"
    assert "not a file" in exc_info.value.message


def test_verify_instruction_paths_with_valid_files(tmp_path):
    """Test verifying instruction paths when all files exist"""
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
        eval=EvalConfig(test_suite_path=str(tmp_path / "evals")),
        logging=LoggingConfig(level="INFO", output="stdout"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    # Should not raise
    verify_instruction_paths(config)


def test_verify_instruction_paths_missing_main_file(tmp_path):
    """Test verifying instruction paths when main file is missing"""
    missing_main = tmp_path / "missing_main.md"
    scenario_file = tmp_path / "scenario.md"
    scenario_file.write_text("# Scenario")

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(missing_main),
            scenarios=[str(scenario_file)]
        ),
        eval=EvalConfig(test_suite_path=str(tmp_path / "evals")),
        logging=LoggingConfig(level="INFO", output="stdout"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(ConfigurationError) as exc_info:
        verify_instruction_paths(config)

    assert exc_info.value.code == "config_file_not_found"
    assert "Main instruction file" in exc_info.value.message


def test_verify_instruction_paths_missing_scenario_file(tmp_path):
    """Test verifying instruction paths when scenario file is missing"""
    main_file = tmp_path / "main.md"
    main_file.write_text("""---
name: main
description: Main instruction
version: 1.0.0
---

<objective>Test</objective>
""")
    missing_scenario = tmp_path / "missing_scenario.md"

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main=str(main_file),
            scenarios=[str(missing_scenario)]
        ),
        eval=EvalConfig(test_suite_path=str(tmp_path / "evals")),
        logging=LoggingConfig(level="INFO", output="stdout"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(ConfigurationError) as exc_info:
        verify_instruction_paths(config)

    assert exc_info.value.code == "config_file_not_found"
    assert "Scenario instruction file" in exc_info.value.message


def test_verify_eval_paths_creates_missing_directory(tmp_path):
    """Test verifying eval paths creates directory if missing"""
    eval_dir = tmp_path / "evals"

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path=str(eval_dir)),
        logging=LoggingConfig(level="INFO", output="stdout"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    # Should not raise and should create directory
    verify_eval_paths(config)

    assert eval_dir.exists()
    assert eval_dir.is_dir()


def test_verify_eval_paths_with_existing_directory(tmp_path):
    """Test verifying eval paths when directory already exists"""
    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path=str(eval_dir)),
        logging=LoggingConfig(level="INFO", output="stdout"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    # Should not raise
    verify_eval_paths(config)


def test_verify_eval_paths_invalid_path_is_file(tmp_path):
    """Test verifying eval paths when path is a file not directory"""
    eval_file = tmp_path / "evals.txt"
    eval_file.write_text("not a directory")

    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path=str(eval_file)),
        logging=LoggingConfig(level="INFO", output="stdout"),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(ConfigurationError) as exc_info:
        verify_eval_paths(config)

    assert exc_info.value.code == "config_invalid_path"
    assert "not a directory" in exc_info.value.message
