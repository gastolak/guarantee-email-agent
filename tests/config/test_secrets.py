"""Tests for secrets management."""

import pytest
import os
from guarantee_email_agent.config.loader import load_secrets, load_config
from guarantee_email_agent.utils.errors import ConfigurationError


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set mock environment variables for Gemini provider."""
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key-123")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")


def test_load_secrets_with_all_vars_set(mock_env_vars):
    """Test loading secrets when all environment variables are set."""
    secrets = load_secrets()

    assert secrets.gemini_api_key == "gemini-test-key-123"
    assert secrets.anthropic_api_key is None  # Not set
    assert secrets.gmail_api_key == "gmail-test-456"
    assert secrets.warranty_api_key == "warranty-test-789"
    assert secrets.ticketing_api_key == "ticket-test-abc"


def test_load_secrets_allows_missing_llm_keys_for_eval_mode(monkeypatch):
    """Test that LLM API keys are optional (for eval/mock mode)."""
    # Clear all LLM keys
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")

    # Should NOT raise error - allows empty keys for eval/mock mode
    secrets = load_secrets()
    assert secrets.anthropic_api_key is None
    assert secrets.gemini_api_key is None
    assert secrets.gmail_api_key == "gmail-test-456"


def test_load_secrets_allows_missing_mcp_keys_for_eval_mode(monkeypatch):
    """Test that MCP API keys are optional (for eval/mock mode)."""
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-123")
    # Clear MCP keys
    monkeypatch.delenv("GMAIL_API_KEY", raising=False)
    monkeypatch.delenv("WARRANTY_API_KEY", raising=False)
    monkeypatch.delenv("TICKETING_API_KEY", raising=False)

    # Should NOT raise error - allows empty keys for eval/mock mode
    secrets = load_secrets()
    assert secrets.gemini_api_key == "gemini-test-123"
    assert secrets.gmail_api_key == ""
    assert secrets.warranty_api_key == ""
    assert secrets.ticketing_api_key == ""


def test_load_secrets_empty_values_allowed(monkeypatch):
    """Test that empty secret values are allowed for eval/mock mode."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GMAIL_API_KEY", "")
    monkeypatch.setenv("WARRANTY_API_KEY", "")
    monkeypatch.setenv("TICKETING_API_KEY", "")

    # Should NOT raise error - allows empty values
    secrets = load_secrets()
    assert secrets.gemini_api_key is None  # Empty string → None
    assert secrets.gmail_api_key == ""
    assert secrets.warranty_api_key == ""
    assert secrets.ticketing_api_key == ""


def test_load_secrets_whitespace_stripped(monkeypatch):
    """Test that whitespace-only values are treated as empty."""
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")

    secrets = load_secrets()
    assert secrets.gemini_api_key is None  # Whitespace → None
    assert secrets.gmail_api_key == "gmail-test-456"


def test_secrets_are_frozen(mock_env_vars):
    """Test that SecretsConfig is immutable."""
    secrets = load_secrets()

    # Attempting to modify should raise FrozenInstanceError
    with pytest.raises(Exception):  # dataclass frozen raises generic exception
        secrets.gemini_api_key = "new-value"


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
  json_format: false
    """)

    monkeypatch.setenv("CONFIG_PATH", str(custom_config))

    config = load_config()

    # Verify custom config was loaded and secrets included
    assert config.secrets.gemini_api_key == "gemini-test-key-123"
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
  json_format: false
    """)

    config = load_config(str(config_file))

    # Verify secrets are present in config
    assert hasattr(config, 'secrets')
    assert config.secrets.gemini_api_key == "gemini-test-key-123"
    assert config.secrets.gmail_api_key == "gmail-test-456"
    assert config.secrets.warranty_api_key == "warranty-test-789"
    assert config.secrets.ticketing_api_key == "ticket-test-abc"
