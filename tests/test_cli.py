"""Tests for CLI functionality."""

from typer.testing import CliRunner

from guarantee_email_agent.cli import app

runner = CliRunner()


def test_cli_help():
    """Test that CLI help displays correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Instruction-driven AI agent for warranty email automation" in result.stdout


def test_run_command_exists():
    """Test that run command exists."""
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0
    assert "Agent run command - to be implemented in Epic 4" in result.stdout


def test_eval_command_exists():
    """Test that eval command exists."""
    result = runner.invoke(app, ["eval"])
    assert result.exit_code == 0
    assert "Agent eval command - to be implemented in Epic 5" in result.stdout
