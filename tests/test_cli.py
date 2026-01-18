"""Tests for CLI functionality."""

import pytest
from typer.testing import CliRunner

from guarantee_email_agent.cli import app

runner = CliRunner()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock required environment variables for CLI testing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("GMAIL_API_KEY", "test-gmail-key")
    monkeypatch.setenv("WARRANTY_API_KEY", "test-warranty-key")
    monkeypatch.setenv("TICKETING_API_KEY", "test-ticketing-key")


def test_cli_help():
    """Test that CLI help displays correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Instruction-driven AI agent for warranty email automation" in result.stdout


def test_run_command_exists(mock_env_vars):
    """Test that run command exists."""
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0
    assert "Agent run command - to be implemented in Epic 4" in result.stdout


def test_eval_command_exists(mock_env_vars):
    """Test that eval command exists."""
    result = runner.invoke(app, ["eval"])
    assert result.exit_code == 0
    assert "Agent eval command - to be implemented in Epic 5" in result.stdout
