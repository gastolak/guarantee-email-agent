"""CLI interface for the guarantee email agent."""

import asyncio
import sys
import logging
from pathlib import Path
import typer

from guarantee_email_agent import __version__
from guarantee_email_agent.config import load_config, validate_config
from guarantee_email_agent.agent.startup import validate_startup
from guarantee_email_agent.agent.runner import AgentRunner
from guarantee_email_agent.email import create_email_processor
from guarantee_email_agent.utils.errors import ConfigurationError, MCPConnectionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="guarantee-email-agent",
    help="Automated warranty email response agent",
    add_completion=False
)


def version_callback(value: bool):
    """Display version information"""
    if value:
        typer.echo(f"guarantee-email-agent version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    )
):
    """guarantee-email-agent: Automated warranty email response system"""
    pass


async def load_and_validate_config_async(config_path: str = None):
    """Load and validate configuration asynchronously (for old eval command).

    Note: This is kept for compatibility with eval command. New code should
    use the run_agent async function directly.

    Args:
        config_path: Path to configuration file

    Returns:
        AgentConfig: Fully validated configuration object
    """
    config = load_config(config_path)
    await validate_startup(config)
    return config


def print_startup_banner():
    """Print startup banner with version and agent info."""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         Guarantee Email Agent v{__version__}                     ║
║         Automated Warranty Email Response System             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Starting agent...
"""
    print(banner)


async def run_agent(config_path: Path) -> int:
    """
    Run the agent with complete lifecycle management.

    Args:
        config_path: Path to configuration file

    Returns:
        Exit code (0=success, 2=config error, 3=MCP error, 1=other error)
    """
    try:
        # Display startup banner
        print_startup_banner()

        # Load configuration
        logger.info(f"Loading configuration from {config_path}")
        config = load_config(str(config_path))

        # Run startup validations
        logger.info("Running startup validations...")
        try:
            await validate_startup(config)
            logger.info("✓ All startup validations passed")
        except ConfigurationError as e:
            logger.error(f"Configuration validation failed: {e}")
            return 2  # Exit code 2: Configuration error
        except MCPConnectionError as e:
            logger.error(f"MCP connection failed: {e}")
            return 3  # Exit code 3: MCP connection error

        # Initialize email processor
        logger.info("Initializing email processor...")
        processor = create_email_processor(config)

        # Initialize agent runner
        logger.info("Initializing agent runner...")
        runner = AgentRunner(config, processor)

        # Register signal handlers
        runner.register_signal_handlers()

        # Start monitoring loop
        logger.info("Starting inbox monitoring loop...")
        await runner.run()

        # Clean shutdown
        logger.info("Agent shutdown complete")
        return 0

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


@app.command()
def run(
    config_path: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    )
):
    """
    Start the warranty email agent.

    The agent will:
    - Validate configuration and connections
    - Monitor Gmail inbox for warranty inquiries
    - Process emails and send automated responses
    - Create tickets for valid warranties
    - Run until interrupted (Ctrl+C or SIGTERM)
    """
    exit_code = asyncio.run(run_agent(config_path))
    sys.exit(exit_code)


@app.command()
def eval():
    """Execute the complete evaluation test suite."""
    # Note: Full implementation in Epic 4 (Story 4.1, 4.2)
    typer.echo("Agent eval command - to be implemented in Epic 4")


if __name__ == "__main__":
    app()
