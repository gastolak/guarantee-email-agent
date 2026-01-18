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
from guarantee_email_agent.utils.logging import configure_logging
from guarantee_email_agent.utils.errors import (
    ConfigurationError,
    MCPConnectionError,
    EXIT_SUCCESS,
    EXIT_GENERAL_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_MCP_ERROR,
    EXIT_EVAL_FAILURE,
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
        Exit code per NFR29:
        - 0 (EXIT_SUCCESS): Success
        - 1 (EXIT_GENERAL_ERROR): Unexpected errors
        - 2 (EXIT_CONFIG_ERROR): Configuration errors
        - 3 (EXIT_MCP_ERROR): MCP connection failures during startup
    """
    try:
        # Display startup banner
        print_startup_banner()

        # Load configuration
        config = load_config(str(config_path))

        # Configure logging with stdout/stderr separation
        log_level = getattr(config.logging, 'level', 'INFO')
        log_file = getattr(config.logging, 'file_path', None)
        configure_logging(
            log_level=log_level,
            json_format=False,
            file_path=log_file,
            use_stderr_separation=True
        )
        logger.info(f"Loading configuration from {config_path}")

        # Run startup validations
        logger.info("Running startup validations...")
        try:
            await validate_startup(config)
            logger.info("✓ All startup validations passed")
        except ConfigurationError as e:
            logger.error(f"Configuration validation failed: {e}", exc_info=True)
            return EXIT_CONFIG_ERROR
        except MCPConnectionError as e:
            logger.error(f"MCP connection failed: {e}", exc_info=True)
            return EXIT_MCP_ERROR

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
        return EXIT_SUCCESS

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        return EXIT_SUCCESS
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return EXIT_GENERAL_ERROR


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

    Exit Codes (NFR29):
        0 - Success (clean shutdown)
        1 - Unexpected error
        2 - Configuration error
        3 - MCP connection failure during startup
    """
    exit_code = asyncio.run(run_agent(config_path, once=once))
    sys.exit(exit_code)


async def run_eval(
    eval_dir: Path,
    verbose: bool = False,
    failures_only: bool = False,
    detailed: bool = False
) -> int:
    """
    Run the evaluation suite.

    Args:
        eval_dir: Directory containing eval test cases
        verbose: Show detailed output including full response bodies
        failures_only: Only show failed scenarios
        detailed: Show detailed failure report with suggestions

    Returns:
        Exit code per NFR29:
        - 0 (EXIT_SUCCESS): Pass rate ≥99%
        - 4 (EXIT_EVAL_FAILURE): Pass rate <99%
        - 1 (EXIT_GENERAL_ERROR): Execution error
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
            typer.echo("\nSee evals/scenarios/README.md for template and examples")
            return EXIT_EVAL_FAILURE

        typer.echo(f"\n🔍 Running evaluation suite... ({len(test_cases)} scenarios)\n")

        # Run eval suite
        start_time = time.time()
        results = await runner.run_suite(test_cases)
        duration = time.time() - start_time

        # Print results based on flags
        if failures_only:
            # Only show failed scenarios
            failed_results = [r for r in results if not r.passed]
            for result in failed_results:
                print(result.format_for_display())
                if result.failures:
                    for failure in result.failures:
                        print(f"  - {failure}")
        else:
            # Show all scenarios
            reporter.print_scenario_results(results)

        # Print detailed failures if requested
        if detailed:
            reporter.print_detailed_failures(results, verbose=verbose)

        # Print summary
        reporter.print_summary(results, duration)

        # Determine exit code
        pass_rate = reporter.calculate_pass_rate(results)
        if pass_rate >= 99.0:
            logger.info(f"Eval passed: {pass_rate:.1f}% pass rate")
            return EXIT_SUCCESS
        else:
            logger.warning(f"Eval failed: {pass_rate:.1f}% pass rate (<99%)")
            return EXIT_EVAL_FAILURE

    except Exception as e:
        logger.error(f"Eval execution error: {e}", exc_info=True)
        typer.echo(f"❌ Eval execution error: {e}")
        return EXIT_GENERAL_ERROR


@app.command()
def eval(
    eval_dir: Path = typer.Option(
        "evals/scenarios",
        "--eval-dir",
        help="Directory containing eval test case YAML files"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output including full response bodies"
    ),
    failures_only: bool = typer.Option(
        False,
        "--failures-only",
        "-f",
        help="Only show failed scenarios (useful when many tests pass)"
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        "-d",
        help="Show detailed failure analysis with categorization and fix suggestions"
    )
):
    """
    Run evaluation suite to validate agent correctness.

    Discovers and executes all YAML test cases in the eval directory.
    Reports pass rate and exits with appropriate code per NFR29.

    Exit Codes:
        0 - Success (pass rate ≥99%)
        4 - Eval failure (pass rate <99%)
        1 - Execution error

    Examples:
        # Basic run
        uv run python -m guarantee_email_agent eval

        # Show only failures (when many tests pass)
        uv run python -m guarantee_email_agent eval --failures-only

        # Show detailed failure analysis with suggestions
        uv run python -m guarantee_email_agent eval --detailed

        # Verbose mode with full response bodies
        uv run python -m guarantee_email_agent eval --detailed --verbose

        # Custom eval directory
        uv run python -m guarantee_email_agent eval --eval-dir custom/evals

        # Check exit code in scripts
        uv run python -m guarantee_email_agent eval || echo "Failed with $?"
    """
    exit_code = asyncio.run(run_eval(eval_dir, verbose, failures_only, detailed))
    sys.exit(exit_code)


if __name__ == "__main__":
    app()
