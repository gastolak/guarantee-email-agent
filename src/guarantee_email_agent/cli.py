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


async def run_agent(config_path: Path, once: bool = False) -> int:
    """
    Run the agent with complete lifecycle management.

    Args:
        config_path: Path to configuration file
        once: If True, process emails once and exit (for testing)

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

        # Register signal handlers (unless in once mode)
        if not once:
            runner.register_signal_handlers()

        # Start monitoring loop
        if once:
            logger.info("Running in --once mode (process emails once and exit)")
            await runner.run_once()
        else:
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
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="Process emails once and exit (for testing)"
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
    exit_code = asyncio.run(run_agent(config_path, once=once))
    sys.exit(exit_code)


async def run_eval(eval_dir: Path) -> int:
    """
    Run the evaluation suite.

    Args:
        eval_dir: Directory containing eval test cases

    Returns:
        Exit code (0 if ≥99%, 4 if <99%)
    """
    import time
    from guarantee_email_agent.eval.loader import EvalLoader
    from guarantee_email_agent.eval.runner import EvalRunner
    from guarantee_email_agent.eval.reporter import EvalReporter

    try:
        # Initialize eval components
        loader = EvalLoader()
        runner = EvalRunner()
        reporter = EvalReporter()

        # Discover test cases
        logger.info(f"Discovering eval test cases in {eval_dir}")
        test_cases = loader.discover_test_cases(str(eval_dir))

        if not test_cases:
            logger.error(f"No eval test cases found in {eval_dir}")
            typer.echo(f"❌ No eval test cases found in {eval_dir}")
            typer.echo("\nCreate eval test cases in YAML format:")
            typer.echo(f"  {eval_dir}/valid_warranty_001.yaml")
            return 4

        typer.echo(f"\n Running evaluation suite... ({len(test_cases)} scenarios)\n")

        # Run eval suite
        start_time = time.time()
        results = await runner.run_suite(test_cases)
        duration = time.time() - start_time

        # Print results
        reporter.print_scenario_results(results)
        reporter.print_summary(results, duration)

        # Determine exit code
        pass_rate = reporter.calculate_pass_rate(results)
        if pass_rate >= 99.0:
            logger.info(f"Eval passed: {pass_rate:.1f}% pass rate")
            return 0
        else:
            logger.warning(f"Eval failed: {pass_rate:.1f}% pass rate (<99%)")
            return 4

    except Exception as e:
        logger.error(f"Eval execution error: {e}", exc_info=True)
        typer.echo(f"❌ Eval execution error: {e}")
        return 1


@app.command()
def eval(
    eval_dir: Path = typer.Option(
        "evals/scenarios",
        "--eval-dir",
        help="Directory containing eval test case YAML files"
    )
):
    """
    Run evaluation suite to validate agent correctness.

    Discovers and executes all YAML test cases in the eval directory.
    Reports pass rate and exits with code 0 if ≥99%, code 4 if <99%.

    Example:
        uv run python -m guarantee_email_agent eval
        uv run python -m guarantee_email_agent eval --eval-dir custom/evals
    """
    exit_code = asyncio.run(run_eval(eval_dir))
    sys.exit(exit_code)


if __name__ == "__main__":
    app()
