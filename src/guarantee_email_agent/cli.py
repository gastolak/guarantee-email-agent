"""CLI interface for the guarantee email agent."""

import sys
import typer

from guarantee_email_agent.config import load_config, validate_config
from guarantee_email_agent.utils.errors import ConfigurationError

app = typer.Typer(
    name="agent",
    help="Instruction-driven AI agent for warranty email automation"
)


def load_and_validate_config(config_path: str = None):
    """Load and validate configuration including secrets, exit with code 2 on error.

    Args:
        config_path: Path to configuration file (default: from CONFIG_PATH env var or "config.yaml")

    Returns:
        AgentConfig: Validated configuration object

    Exits:
        Exit code 2 if configuration is invalid or secrets missing
    """
    try:
        # load_config() now also loads secrets from environment
        config = load_config(config_path)

        # validate_config() now also validates secrets
        validate_config(config)

        return config
    except ConfigurationError as e:
        typer.echo(f"Configuration Error: {e.message}", err=True)
        typer.echo(f"Error Code: {e.code}", err=True)
        if e.details:
            typer.echo(f"Details: {e.details}", err=True)

        # Provide helpful hints for secret errors
        if e.code == "config_missing_secret":
            typer.echo("\nHint: Copy .env.example to .env and fill in your API keys", err=True)
            typer.echo("      Then restart the agent", err=True)

        sys.exit(2)  # Exit code 2 for configuration errors


@app.command()
def run():
    """Start the warranty email agent for continuous processing."""
    config = load_and_validate_config()
    typer.echo("Configuration and secrets loaded successfully")
    # Secrets are now available in config.secrets
    typer.echo("Agent run command - to be implemented in Epic 4")


@app.command()
def eval():
    """Execute the complete evaluation test suite."""
    config = load_and_validate_config()
    typer.echo("Configuration and secrets loaded successfully")
    typer.echo("Agent eval command - to be implemented in Epic 5")


if __name__ == "__main__":
    app()
