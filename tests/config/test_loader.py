"""Tests for configuration loader."""

import pytest
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.utils.errors import ConfigurationError


def test_load_valid_config(tmp_path):
    """Test loading a valid configuration file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
mcp:
  gmail:
    connection_string: "mcp://gmail"
  warranty_api:
    connection_string: "mcp://warranty-api"
    endpoint: "https://api.example.com/warranty"
  ticketing_system:
    connection_string: "mcp://ticketing"
    endpoint: "https://tickets.example.com"

instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"

eval:
  test_suite_path: "./evals/scenarios/"
  pass_threshold: 99.0

logging:
  level: "INFO"
  output: "stdout"
  file: "./logs/agent.log"
    """)

    config = load_config(str(config_file))

    assert config.mcp.gmail.connection_string == "mcp://gmail"
    assert config.mcp.warranty_api.endpoint == "https://api.example.com/warranty"
    assert config.eval.pass_threshold == 99.0
    assert config.logging.level == "INFO"
    assert config.instructions.main == "./instructions/main.md"
    assert len(config.instructions.scenarios) == 1


def test_load_missing_config_file():
    """Test loading non-existent config file raises error."""
    with pytest.raises(ConfigurationError) as exc_info:
        load_config("nonexistent.yaml")

    assert exc_info.value.code == "config_file_not_found"
    assert "nonexistent.yaml" in exc_info.value.message


def test_load_invalid_yaml(tmp_path):
    """Test loading invalid YAML raises error."""
    config_file = tmp_path / "bad_config.yaml"
    config_file.write_text("mcp:\n  gmail: [invalid: yaml: structure")

    with pytest.raises(ConfigurationError) as exc_info:
        load_config(str(config_file))

    assert exc_info.value.code == "config_invalid_yaml"
    assert "not valid YAML" in exc_info.value.message


def test_load_missing_required_field(tmp_path):
    """Test loading config with missing required field raises error."""
    config_file = tmp_path / "incomplete_config.yaml"
    config_file.write_text("""
mcp:
  gmail:
    connection_string: "mcp://gmail"

instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"

eval:
  test_suite_path: "./evals/scenarios/"
  pass_threshold: 99.0

logging:
  level: "INFO"
  output: "stdout"
  file: "./logs/agent.log"
    """)

    with pytest.raises(ConfigurationError) as exc_info:
        load_config(str(config_file))

    assert exc_info.value.code == "config_missing_field"


def test_load_config_with_optional_fields(tmp_path):
    """Test loading config where optional fields are handled correctly."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
mcp:
  gmail:
    connection_string: "mcp://gmail"
  warranty_api:
    connection_string: "mcp://warranty-api"
  ticketing_system:
    connection_string: "mcp://ticketing"

instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"

eval:
  test_suite_path: "./evals/scenarios/"
  pass_threshold: 99.0

logging:
  level: "INFO"
  output: "stdout"
  file: "./logs/agent.log"
    """)

    config = load_config(str(config_file))

    # Optional endpoint fields should be None
    assert config.mcp.gmail.endpoint is None
    assert config.mcp.warranty_api.endpoint is None
    assert config.mcp.ticketing_system.endpoint is None


def test_load_config_includes_secrets(tmp_path, monkeypatch):
    """Test that load_config includes secrets from environment in AgentConfig."""
    # Set up environment variables
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-123")
    monkeypatch.setenv("GMAIL_API_KEY", "test-gmail-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "test-warranty-789")
    monkeypatch.setenv("TICKETING_API_KEY", "test-ticketing-abc")

    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
mcp:
  gmail:
    connection_string: "mcp://gmail"
  warranty_api:
    connection_string: "mcp://warranty-api"
  ticketing_system:
    connection_string: "mcp://ticketing"

instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"

eval:
  test_suite_path: "./evals/scenarios/"
  pass_threshold: 99.0

logging:
  level: "INFO"
  output: "stdout"
  file: "./logs/agent.log"
    """)

    config = load_config(str(config_file))

    # Verify secrets are included in config
    assert hasattr(config, 'secrets')
    assert config.secrets.anthropic_api_key == "test-anthropic-123"
    assert config.secrets.gmail_api_key == "test-gmail-456"
    assert config.secrets.warranty_api_key == "test-warranty-789"
    assert config.secrets.ticketing_api_key == "test-ticketing-abc"
