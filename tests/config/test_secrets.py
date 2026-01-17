"""Tests for secrets management."""

import pytest
import os
from guarantee_email_agent.config.loader import load_secrets, load_config
from guarantee_email_agent.utils.errors import ConfigurationError


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set mock environment variables."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")


def test_load_secrets_with_all_vars_set(mock_env_vars):
    """Test loading secrets when all environment variables are set."""
    secrets = load_secrets()

    assert secrets.anthropic_api_key == "sk-ant-test-123"
    assert secrets.gmail_api_key == "gmail-test-456"
    assert secrets.warranty_api_key == "warranty-test-789"
    assert secrets.ticketing_api_key == "ticket-test-abc"


def test_load_secrets_missing_anthropic_key(monkeypatch):
    """Test that missing ANTHROPIC_API_KEY raises error."""
    # Set all except ANTHROPIC_API_KEY
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"
    assert "ANTHROPIC_API_KEY" in exc_info.value.message


def test_load_secrets_missing_gmail_key(monkeypatch):
    """Test that missing GMAIL_API_KEY raises error."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")
    monkeypatch.delenv("GMAIL_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"
    assert "GMAIL_API_KEY" in exc_info.value.message


def test_load_secrets_missing_warranty_key(monkeypatch):
    """Test that missing WARRANTY_API_KEY raises error."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")
    monkeypatch.delenv("WARRANTY_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"
    assert "WARRANTY_API_KEY" in exc_info.value.message


def test_load_secrets_missing_ticketing_key(monkeypatch):
    """Test that missing TICKETING_API_KEY raises error."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.delenv("TICKETING_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"
    assert "TICKETING_API_KEY" in exc_info.value.message


def test_load_secrets_empty_value(monkeypatch):
    """Test that empty secret value raises error."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"
    assert "ANTHROPIC_API_KEY" in exc_info.value.message


def test_load_secrets_whitespace_only(monkeypatch):
    """Test that whitespace-only secret value raises error."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"


def test_secrets_are_frozen(mock_env_vars):
    """Test that SecretsConfig is immutable."""
    secrets = load_secrets()

    # Attempting to modify should raise FrozenInstanceError
    with pytest.raises(Exception):  # dataclass frozen raises generic exception
        secrets.anthropic_api_key = "new-value"


def test_config_path_override(monkeypatch, tmp_path, mock_env_vars):
    """Test CONFIG_PATH environment variable override."""
    # Create custom config file
    custom_config = tmp_path / "custom.yaml"
    custom_config.write_text("""
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

    monkeypatch.setenv("CONFIG_PATH", str(custom_config))

    config = load_config()

    # Verify custom config was loaded and secrets included
    assert config.secrets.anthropic_api_key == "sk-ant-test-123"
    assert config.mcp.gmail.connection_string == "mcp://gmail"


def test_config_includes_secrets(monkeypatch, tmp_path, mock_env_vars):
    """Test that load_config includes secrets in AgentConfig."""
    # Create config file
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
    - "./instructions/scenarios/test.md"

eval:
  test_suite_path: "./evals/"
  pass_threshold: 99.0

logging:
  level: "INFO"
  output: "stdout"
  file: "./logs/agent.log"
    """)

    config = load_config(str(config_file))

    # Verify secrets are present in config
    assert hasattr(config, 'secrets')
    assert config.secrets.anthropic_api_key == "sk-ant-test-123"
    assert config.secrets.gmail_api_key == "gmail-test-456"
    assert config.secrets.warranty_api_key == "warranty-test-789"
    assert config.secrets.ticketing_api_key == "ticket-test-abc"
