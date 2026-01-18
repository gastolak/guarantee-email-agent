"""CLI interface for the guarantee email agent."""

import sys
import logging
import typer

from guarantee_email_agent.config import load_config, validate_config
from guarantee_email_agent.config.startup_validator import validate_startup
from guarantee_email_agent.utils.errors import ConfigurationError, MCPConnectionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="agent",
    help="Instruction-driven AI agent for warranty email automation"
)


def load_and_validate_config(config_path: str = None):
    """Load and validate configuration, file paths, and MCP connections.

    Complete startup sequence with proper exit codes:
    - Exit code 2: Configuration errors (schema, missing secrets, file paths)
    - Exit code 3: MCP connection errors

    Args:
        config_path: Path to configuration file (default: from CONFIG_PATH env var or "config.yaml")

    Returns:
        AgentConfig: Fully validated configuration object

    Exits:
        Exit code 2 if configuration is invalid, secrets missing, or file paths invalid
        Exit code 3 if MCP connection validation fails
    """
    try:
        # Load configuration and secrets
        logger.info("Loading configuration...")
        config = load_config(config_path)
        logger.info("Configuration loaded")

        # Validate configuration schema and secrets
        logger.info("Validating configuration schema...")
        validate_config(config)
        logger.info("Configuration valid")

        # Startup validation (file paths, MCP connections)
        logger.info("Running startup validation...")
        validate_startup(config)
        logger.info("File paths verified")
        logger.info("MCP connections tested")

        logger.info("Agent ready")
        return config

    except ConfigurationError as e:
        logger.error(f"Configuration Error: {e.message}")
        logger.error(f"Error Code: {e.code}")
        if e.details:
            logger.error(f"Details: {e.details}")

        # Provide helpful hints
        if e.code == "config_missing_secret":
            logger.info("Hint: Copy .env.example to .env and fill in your API keys")
        elif e.code == "config_file_not_found":
            logger.info("Hint: Check that the file path in config.yaml is correct")

        sys.exit(2)  # Exit code 2 for configuration errors

    except MCPConnectionError as e:
        logger.error(f"MCP Connection Error: {e.message}")
        logger.error(f"Error Code: {e.code}")
        if e.details:
            logger.error(f"Details: {e.details}")

        logger.info("Hint: Check MCP connection strings in config.yaml")
        logger.info("      In Epic 2, actual MCP servers will be tested")

        sys.exit(3)  # Exit code 3 for MCP connection failures


@app.command()
def run():
    """Start the warranty email agent for continuous processing."""
    config = load_and_validate_config()
    typer.echo("Agent run command - to be implemented in Epic 4")


@app.command()
def eval():
    """Execute the complete evaluation test suite."""
    config = load_and_validate_config()
    typer.echo("Agent eval command - to be implemented in Epic 5")


if __name__ == "__main__":
    app()
