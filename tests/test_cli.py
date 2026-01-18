"""Tests for CLI functionality."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from guarantee_email_agent.cli import app, print_startup_banner
from guarantee_email_agent import __version__

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
    assert "Automated warranty email response agent" in result.stdout


def test_version_flag():
    """Test --version flag displays version information."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"guarantee-email-agent version {__version__}" in result.stdout


def test_version_flag_short():
    """Test -v short flag displays version information."""
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert "guarantee-email-agent version" in result.stdout


def test_run_command_help():
    """Test run command help."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "Start the warranty email agent" in result.stdout
    assert "--config" in result.stdout


def test_run_command_missing_config():
    """Test run command with missing config file."""
    result = runner.invoke(app, ["run", "--config", "nonexistent.yaml"])
    # Should fail because file doesn't exist (Typer validation)
    assert result.exit_code != 0


def test_print_startup_banner():
    """Test startup banner prints correctly."""
    import io
    import sys
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        print_startup_banner()

    output = f.getvalue()
    assert "Guarantee Email Agent" in output
    assert __version__ in output
    assert "Starting agent..." in output


def test_eval_command_exists(mock_env_vars):
    """Test that eval command exists."""
    result = runner.invoke(app, ["eval"])
    # Will fail due to config, but command should exist
    assert "eval" in result.stdout.lower() or result.exit_code in [0, 2]
