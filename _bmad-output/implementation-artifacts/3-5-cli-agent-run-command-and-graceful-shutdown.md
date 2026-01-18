# Story 3.5: CLI Agent Run Command and Graceful Shutdown

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want a CLI command to start the agent and gracefully shut it down on signals,
So that I can run the agent as a long-lived process with clean lifecycle management.

## Acceptance Criteria

**Given** The complete email processing pipeline from Story 3.4 exists
**When** The agent is started and stopped

**Then - CLI Run Command:**
**And** CLI command `uv run python -m guarantee_email_agent run` starts agent
**And** CLI implemented in `src/guarantee_email_agent/cli.py` using Typer framework
**And** Run command initializes all components: config, MCP clients, processor
**And** Command validates configuration before starting (fail fast per NFR38)
**And** Command tests MCP connections on startup (fail fast if unavailable per NFR38)
**And** Command enters inbox monitoring loop
**And** Agent polls Gmail inbox at configured interval (default: 60 seconds per NFR10)
**And** Each new email processed independently through pipeline
**And** Processing continues until shutdown signal received
**And** CLI outputs startup banner with version and configuration summary
**And** CLI shows processing status in real-time (emails processed, errors)
**And** CLI command exits with appropriate exit code (0=success, 2=config error, 3=MCP error per NFR29)

**Then - Graceful Shutdown:**
**And** Agent handles SIGTERM and SIGINT signals gracefully (NFR36)
**And** On signal, agent completes current email processing before shutdown
**And** In-flight emails not abandoned (complete or mark unprocessed per NFR5)
**And** MCP connections closed cleanly on shutdown
**And** Agent logs shutdown reason (signal received, error, user requested)
**And** Shutdown timeout: 30 seconds max to complete in-flight processing
**And** If timeout exceeded, force shutdown with warning log
**And** Agent returns exit code 0 on clean shutdown
**And** Agent can be safely restarted without state corruption (NFR16 stateless)

**Then - Inbox Monitoring Loop:**
**And** Monitor loop in `src/guarantee_email_agent/agent/runner.py` polls Gmail
**And** Loop uses Gmail MCP client to fetch unread emails
**And** Each email passed to EmailProcessor.process_email() async
**And** Concurrent processing when multiple emails present (NFR10)
**And** Processing errors logged but don't crash agent loop
**And** Failed emails marked unprocessed, agent continues
**And** Loop respects shutdown flag (check between iterations)
**And** Polling interval configurable via config.yaml (default: 60s)
**And** Loop logs activity: "Checking inbox...", "No new emails", "Processing N emails"

**Then - Startup Validation:**
**And** Validator in `src/guarantee_email_agent/agent/startup.py` runs before loop
**And** Validates configuration schema (Story 1.2)
**And** Validates all required secrets present (ANTHROPIC_API_KEY, etc. per NFR12)
**And** Tests MCP connection to Gmail server
**And** Tests MCP connection to Warranty API server
**And** Tests MCP connection to Ticketing server
**And** Loads and validates main instruction file
**And** Validates scenario instruction files exist
**And** All validations logged with clear pass/fail status
**And** If any validation fails, exit with code 2 (config) or 3 (MCP) immediately
**And** Startup validation completes within 10 seconds (NFR38)

## Tasks / Subtasks

### CLI Framework Setup

- [ ] Create CLI module (AC: CLI implemented with Typer)
  - [ ] Create `src/guarantee_email_agent/cli.py`
  - [ ] Import Typer framework with [all] extras
  - [ ] Create Typer app instance
  - [ ] Add version callback for `--version` flag
  - [ ] Add help text and command descriptions
  - [ ] Configure CLI output formatting

- [ ] Implement main CLI entry point (AC: CLI command starts agent)
  - [ ] Update `src/guarantee_email_agent/__main__.py`
  - [ ] Import CLI app from cli.py
  - [ ] Call `app()` to run CLI
  - [ ] Ensure proper exit code propagation
  - [ ] Handle unexpected exceptions at top level

- [ ] Add version information (AC: startup banner with version)
  - [ ] Create `src/guarantee_email_agent/__version__.py`
  - [ ] Define VERSION constant (e.g., "0.1.0")
  - [ ] Export version in __init__.py
  - [ ] Use version in --version flag
  - [ ] Display version in startup banner

### Startup Validation

- [ ] Create startup validation module (AC: validator runs before loop)
  - [ ] Create `src/guarantee_email_agent/agent/startup.py`
  - [ ] Import all necessary components for validation
  - [ ] Create `StartupValidator` class
  - [ ] Initialize with config
  - [ ] Add logger with __name__

- [ ] Implement configuration validation (AC: validates configuration schema)
  - [ ] Create `validate_config(config: AgentConfig) -> bool` method
  - [ ] Check all required config sections present
  - [ ] Validate config values (paths exist, values in range)
  - [ ] Log: "✓ Configuration valid" or "✗ Configuration invalid: {reason}"
  - [ ] Return True if valid, raise ConfigError if invalid
  - [ ] Use schema validation from Story 1.2

- [ ] Implement secrets validation (AC: validates required secrets present)
  - [ ] Create `validate_secrets(config: AgentConfig) -> bool` method
  - [ ] Check ANTHROPIC_API_KEY present (NFR12)
  - [ ] Check Gmail credentials present
  - [ ] Check Warranty API credentials present (if needed)
  - [ ] Check Ticketing API credentials present (if needed)
  - [ ] Log: "✓ All secrets present" or "✗ Missing secrets: {list}"
  - [ ] Return True if all present, raise ConfigError if missing
  - [ ] Don't log secret values (security)

- [ ] Implement instruction file validation (AC: validates instruction files exist)
  - [ ] Create `validate_instructions(config: AgentConfig) -> bool` method
  - [ ] Check main instruction file exists at config.instructions.main
  - [ ] Load and parse main instruction (catch parse errors)
  - [ ] Check scenarios directory exists
  - [ ] Check required scenario files exist: valid-warranty, invalid-warranty, missing-info, graceful-degradation
  - [ ] Log: "✓ Instruction files valid" or "✗ Instruction validation failed: {reason}"
  - [ ] Return True if valid, raise InstructionError if invalid

- [ ] Implement MCP connection testing (AC: tests all MCP connections)
  - [ ] Create `test_mcp_connections(config: AgentConfig) -> bool` async method
  - [ ] Test Gmail MCP connection: call simple API (e.g., get inbox count)
  - [ ] Test Warranty API MCP connection: call health check or simple query
  - [ ] Test Ticketing API MCP connection: call health check or list endpoint
  - [ ] Each test has 5-second timeout
  - [ ] Log: "✓ Gmail MCP connected" or "✗ Gmail MCP connection failed: {error}"
  - [ ] Return True if all connected, raise MCPConnectionError if any fail
  - [ ] Use MCP clients from Story 2.1

- [ ] Implement complete startup validation workflow (AC: startup validation completes within 10s)
  - [ ] Create `validate_startup(config: AgentConfig) -> None` async method
  - [ ] Run all validations in sequence
  - [ ] Track validation time (target: <10s per NFR38)
  - [ ] Log each validation step with result
  - [ ] If any validation fails, raise appropriate error and exit
  - [ ] Log: "All startup validations passed" if successful
  - [ ] Return on success, raise on failure (fail fast)

- [ ] Add startup validation logging (AC: validations logged with pass/fail status)
  - [ ] Log at INFO level for each validation step
  - [ ] Use ✓ and ✗ symbols for visual clarity
  - [ ] Format: "[STARTUP] Validating {component}..."
  - [ ] Format: "[STARTUP] ✓ {component} valid" or "[STARTUP] ✗ {component} failed: {reason}"
  - [ ] Include validation timing in DEBUG logs
  - [ ] Summary log: "Startup validation complete in {duration}ms"

### Inbox Monitoring Loop

- [ ] Create agent runner module (AC: monitor loop polls Gmail)
  - [ ] Create `src/guarantee_email_agent/agent/runner.py`
  - [ ] Import asyncio for async loop
  - [ ] Import EmailProcessor and dependencies
  - [ ] Create `AgentRunner` class
  - [ ] Initialize with config and all dependencies
  - [ ] Add shutdown flag: `self._shutdown_requested = False`

- [ ] Implement inbox polling logic (AC: loop fetches unread emails)
  - [ ] Create `poll_inbox() -> List[Dict[str, Any]]` async method
  - [ ] Call gmail_client.get_unread_emails() or similar
  - [ ] Filter for unread emails in monitored labels/folders
  - [ ] Return list of raw email data
  - [ ] Handle Gmail API errors gracefully (log, don't crash)
  - [ ] Log: "Checking inbox..." at DEBUG level
  - [ ] Log: "Found {count} unread emails" at INFO level

- [ ] Implement email processing dispatch (AC: each email passed to processor)
  - [ ] Create `process_inbox_emails(emails: List[Dict]) -> List[ProcessingResult]` async method
  - [ ] For each email, call processor.process_email(email)
  - [ ] Use asyncio.gather() for concurrent processing (NFR10)
  - [ ] Collect all ProcessingResults
  - [ ] Log processing summary: "{success_count} succeeded, {failed_count} failed"
  - [ ] Return list of results

- [ ] Implement main monitoring loop (AC: loop continues until shutdown)
  - [ ] Create `run() -> None` async method
  - [ ] Loop: `while not self._shutdown_requested:`
  - [ ] Poll inbox for new emails
  - [ ] If emails found, process them concurrently
  - [ ] If no emails, log "No new emails" at DEBUG level
  - [ ] Sleep for polling_interval seconds (default: 60s)
  - [ ] Check shutdown flag after each iteration
  - [ ] Exit loop cleanly when shutdown requested

- [ ] Implement polling interval configuration (AC: interval configurable via config)
  - [ ] Read polling_interval from config.agent.polling_interval_seconds
  - [ ] Default to 60 seconds if not configured (NFR10)
  - [ ] Validate interval >= 10 seconds (prevent excessive polling)
  - [ ] Log: "Polling interval: {interval}s"
  - [ ] Use asyncio.sleep(interval) between polls

- [ ] Add loop activity logging (AC: loop logs activity)
  - [ ] Log at DEBUG level: "Checking inbox..."
  - [ ] Log at INFO level when emails found: "Processing {count} emails"
  - [ ] Log at DEBUG level when no emails: "No new emails"
  - [ ] Log at INFO level after processing: "Processed {count} emails"
  - [ ] Include processing results summary in logs
  - [ ] Don't spam logs during idle periods (rate limit "no emails" logs)

- [ ] Implement error resilience (AC: processing errors don't crash loop)
  - [ ] Wrap email processing in try/except
  - [ ] Catch processing exceptions and log
  - [ ] Mark email as unprocessed on critical failures
  - [ ] Continue loop after errors (don't exit)
  - [ ] Track consecutive error count
  - [ ] If >10 consecutive errors, log warning and consider pausing
  - [ ] Log: "Error processing email {email_id}: {error} - continuing"

### Graceful Shutdown

- [ ] Create shutdown handler module (AC: handles signals gracefully)
  - [ ] Create signal handlers in runner.py
  - [ ] Import signal module
  - [ ] Create `request_shutdown(signum, frame)` method
  - [ ] Set shutdown flag: `self._shutdown_requested = True`
  - [ ] Log: "Shutdown requested via signal {signum}"
  - [ ] Don't immediately exit (allow graceful completion)

- [ ] Register signal handlers (AC: handles SIGTERM and SIGINT)
  - [ ] Register SIGTERM handler (systemd/Docker)
  - [ ] Register SIGINT handler (Ctrl+C)
  - [ ] Call signal.signal(signal.SIGTERM, self.request_shutdown)
  - [ ] Call signal.signal(signal.SIGINT, self.request_shutdown)
  - [ ] Log: "Signal handlers registered (SIGTERM, SIGINT)"
  - [ ] Handle signals on main thread only

- [ ] Implement graceful completion (AC: completes current emails before shutdown)
  - [ ] When shutdown flag set, finish current poll iteration
  - [ ] Don't start new poll iteration if shutdown requested
  - [ ] Wait for in-flight email processing to complete
  - [ ] Use asyncio.wait_for() with 30-second timeout
  - [ ] Log: "Completing in-flight processing..."
  - [ ] Log: "In-flight processing complete" or "Timeout waiting for completion"

- [ ] Implement shutdown timeout (AC: 30 seconds max to complete)
  - [ ] Set timeout: 30 seconds (configurable)
  - [ ] Start timer when shutdown requested
  - [ ] If timeout exceeded, force shutdown
  - [ ] Log warning: "Shutdown timeout exceeded, forcing exit"
  - [ ] Mark any incomplete emails as unprocessed
  - [ ] Exit with code 0 (graceful, even if forced)

- [ ] Implement clean resource cleanup (AC: MCP connections closed cleanly)
  - [ ] Create `cleanup() -> None` async method
  - [ ] Close Gmail MCP connection: await gmail_client.close()
  - [ ] Close Warranty API MCP connection: await warranty_client.close()
  - [ ] Close Ticketing MCP connection: await ticketing_client.close()
  - [ ] Close Anthropic client if needed
  - [ ] Log: "MCP connections closed"
  - [ ] Handle cleanup errors gracefully (log but don't crash)

- [ ] Add shutdown logging (AC: logs shutdown reason)
  - [ ] Log shutdown trigger: "Shutdown requested: {reason}"
  - [ ] Reason: "SIGTERM received", "SIGINT received", "Error", "User requested"
  - [ ] Log cleanup steps with status
  - [ ] Log final message: "Agent shutdown complete"
  - [ ] Include uptime and emails processed in final log
  - [ ] Use INFO level for shutdown events

### CLI Run Command Implementation

- [ ] Create run command (AC: run command starts agent)
  - [ ] Add @app.command() decorated function: `run()`
  - [ ] Add command help text and description
  - [ ] Make command async: use `asyncio.run()` wrapper
  - [ ] Parse CLI arguments if any (e.g., --config-path)
  - [ ] Call agent startup and run workflow
  - [ ] Handle exceptions and exit codes

- [ ] Implement startup sequence (AC: initializes all components)
  - [ ] Load configuration from config.yaml
  - [ ] Run startup validations (validate_startup)
  - [ ] Initialize email processor (create_email_processor factory)
  - [ ] Initialize agent runner with processor
  - [ ] Register signal handlers
  - [ ] Log startup banner with version and config summary
  - [ ] Enter monitoring loop (runner.run())

- [ ] Add startup banner (AC: outputs startup banner with version)
  - [ ] Display banner when agent starts
  - [ ] Include: agent name, version, start time
  - [ ] Include: configuration summary (polling interval, instruction files)
  - [ ] Include: MCP connection status summary
  - [ ] Format banner with visual separation (ASCII art optional)
  - [ ] Log at INFO level
  - [ ] Example: "guarantee-email-agent v0.1.0 starting..."

- [ ] Implement real-time status display (AC: shows processing status)
  - [ ] Display emails processed count
  - [ ] Display success/failure counts
  - [ ] Display current status: "Idle", "Processing", "Shutting down"
  - [ ] Update status in logs (not terminal UI for MVP)
  - [ ] Log periodic summaries: "Status: {processed} emails, {errors} errors"
  - [ ] Log every 10 minutes or after each processing batch

- [ ] Implement exit code handling (AC: exits with appropriate code)
  - [ ] Return exit code 0 on clean shutdown (NFR29)
  - [ ] Return exit code 2 on configuration error (NFR29)
  - [ ] Return exit code 3 on MCP connection error (NFR29)
  - [ ] Return exit code 1 on unexpected errors
  - [ ] Log exit code before exiting
  - [ ] Use sys.exit(code) to set exit code

- [ ] Add configuration file path option
  - [ ] Add --config CLI option for custom config path
  - [ ] Default to "config.yaml" in current directory
  - [ ] Validate config file exists before loading
  - [ ] Log: "Loading configuration from {path}"
  - [ ] Raise error if config file not found

### Agent Runner Module Integration

- [ ] Create agent module directory
  - [ ] Create `src/guarantee_email_agent/agent/` directory
  - [ ] Create `src/guarantee_email_agent/agent/__init__.py`
  - [ ] Export AgentRunner, StartupValidator
  - [ ] Provide clean public API for agent execution

- [ ] Integrate runner with processor
  - [ ] Import EmailProcessor and create_email_processor from email module
  - [ ] Initialize processor in runner.__init__()
  - [ ] Pass processor to runner methods
  - [ ] Ensure processor lifecycle managed correctly

- [ ] Add runner state tracking
  - [ ] Track: emails_processed_count, errors_count, start_time
  - [ ] Update counters after each processing batch
  - [ ] Calculate uptime: current_time - start_time
  - [ ] Include state in periodic status logs
  - [ ] Reset counters on restart (stateless per NFR16)

### Testing

- [ ] Create startup validation tests
  - [ ] Create `tests/agent/test_startup.py`
  - [ ] Test validate_config() with valid and invalid configs
  - [ ] Test validate_secrets() with missing secrets
  - [ ] Test validate_instructions() with missing files
  - [ ] Test test_mcp_connections() with mocked MCP clients
  - [ ] Test validate_startup() end-to-end
  - [ ] Test startup validation timing (<10s)
  - [ ] Mock all external dependencies

- [ ] Create agent runner tests
  - [ ] Create `tests/agent/test_runner.py`
  - [ ] Test poll_inbox() with mocked Gmail client
  - [ ] Test process_inbox_emails() with mocked processor
  - [ ] Test run() loop with shutdown flag
  - [ ] Test polling interval configuration
  - [ ] Test error resilience (processing errors don't crash loop)
  - [ ] Test concurrent email processing
  - [ ] Mock all MCP clients and processors

- [ ] Create shutdown handler tests
  - [ ] Test signal handler registration
  - [ ] Test graceful shutdown flag setting
  - [ ] Test in-flight processing completion
  - [ ] Test shutdown timeout (force shutdown after 30s)
  - [ ] Test clean resource cleanup
  - [ ] Test shutdown logging
  - [ ] Use mock signals for testing

- [ ] Create CLI tests
  - [ ] Create `tests/test_cli.py`
  - [ ] Test run command with valid config
  - [ ] Test run command with invalid config (exit code 2)
  - [ ] Test run command with MCP connection failure (exit code 3)
  - [ ] Test --version flag
  - [ ] Test --config path option
  - [ ] Test startup banner output
  - [ ] Use Typer testing utilities

- [ ] Create integration tests
  - [ ] Create `tests/agent/test_agent_integration.py`
  - [ ] Test complete startup → run → shutdown flow
  - [ ] Test processing multiple emails in loop
  - [ ] Test graceful shutdown during processing
  - [ ] Test restart after shutdown (stateless)
  - [ ] Mock all external dependencies
  - [ ] Verify no state corruption on restart

## Dev Notes

### Architecture Context

This story implements **CLI Agent Run Command and Graceful Shutdown** (consolidates old stories 4.5 and 4.6), providing the operational interface for running the agent as a long-lived process with proper lifecycle management.

**Key Architectural Principles:**
- FR1: Monitor designated Gmail inbox continuously
- FR44: Failed steps logged with sufficient detail
- NFR5: No silent failures (shutdown doesn't abandon emails)
- NFR10: Poll inbox every 60 seconds, concurrent processing
- NFR12: Environment variable secrets management
- NFR16: Stateless agent (safe restart)
- NFR29: Proper exit codes (0, 2, 3)
- NFR36: Graceful shutdown on SIGTERM/SIGINT
- NFR38: Fail fast on startup if config/MCP invalid

### Critical Implementation Rules from Project Context

**CLI Implementation with Typer:**

```python
# src/guarantee_email_agent/cli.py
import asyncio
import sys
import logging
from pathlib import Path
import typer
from guarantee_email_agent import __version__
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.agent.startup import validate_startup
from guarantee_email_agent.agent.runner import AgentRunner
from guarantee_email_agent.email import create_email_processor
from guarantee_email_agent.utils.errors import ConfigError, MCPConnectionError

# Initialize Typer app
app = typer.Typer(
    name="guarantee-email-agent",
    help="Automated warranty email response agent",
    add_completion=False
)

logger = logging.getLogger(__name__)

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
        except ConfigError as e:
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
        logger.info(f"Polling interval: {config.agent.polling_interval_seconds}s")
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

def print_startup_banner():
    """Print startup banner with version and agent info"""
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
```

**Startup Validation Implementation:**

```python
# src/guarantee_email_agent/agent/startup.py
import asyncio
import logging
import time
from pathlib import Path
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import ConfigError, MCPConnectionError, InstructionError
from guarantee_email_agent.instructions.loader import load_instruction
from guarantee_email_agent.integrations.gmail import GmailClient
from guarantee_email_agent.integrations.warranty_api import WarrantyAPIClient
from guarantee_email_agent.integrations.ticketing import TicketingClient

logger = logging.getLogger(__name__)

# Required scenario instruction files
REQUIRED_SCENARIOS = [
    "valid-warranty",
    "invalid-warranty",
    "missing-info",
    "graceful-degradation"
]

async def validate_startup(config: AgentConfig) -> None:
    """
    Run all startup validations.

    Validates:
    - Configuration schema and values
    - Required secrets present
    - Instruction files exist and parse correctly
    - MCP connections functional

    Args:
        config: Agent configuration

    Raises:
        ConfigError: If configuration or secrets invalid
        InstructionError: If instruction files invalid
        MCPConnectionError: If MCP connections fail

    Note:
        Target completion time: <10 seconds (NFR38)
    """
    start_time = time.time()

    logger.info("[STARTUP] Starting validation sequence...")

    # Validation 1: Configuration
    logger.info("[STARTUP] Validating configuration...")
    validate_config(config)
    logger.info("[STARTUP] ✓ Configuration valid")

    # Validation 2: Secrets
    logger.info("[STARTUP] Validating secrets...")
    validate_secrets(config)
    logger.info("[STARTUP] ✓ All required secrets present")

    # Validation 3: Instruction files
    logger.info("[STARTUP] Validating instruction files...")
    validate_instructions(config)
    logger.info("[STARTUP] ✓ Instruction files valid")

    # Validation 4: MCP connections
    logger.info("[STARTUP] Testing MCP connections...")
    await test_mcp_connections(config)
    logger.info("[STARTUP] ✓ All MCP connections functional")

    # Calculate validation time
    validation_time = int((time.time() - start_time) * 1000)
    logger.info(f"[STARTUP] All validations passed in {validation_time}ms")

    if validation_time > 10000:
        logger.warning(
            f"[STARTUP] Validation exceeded 10s target: {validation_time}ms"
        )

def validate_config(config: AgentConfig) -> None:
    """
    Validate configuration schema and values.

    Args:
        config: Agent configuration

    Raises:
        ConfigError: If configuration invalid
    """
    # Config schema validation handled by Pydantic in Story 1.2
    # Additional validation for specific values

    # Validate polling interval
    if config.agent.polling_interval_seconds < 10:
        raise ConfigError(
            message="Polling interval must be >= 10 seconds",
            code="invalid_polling_interval",
            details={"polling_interval": config.agent.polling_interval_seconds}
        )

    # Validate instruction paths
    if not config.instructions.main:
        raise ConfigError(
            message="Main instruction path not configured",
            code="missing_main_instruction_path",
            details={}
        )

    if not config.instructions.scenarios_dir:
        raise ConfigError(
            message="Scenarios directory not configured",
            code="missing_scenarios_dir",
            details={}
        )

def validate_secrets(config: AgentConfig) -> None:
    """
    Validate all required secrets present.

    Args:
        config: Agent configuration

    Raises:
        ConfigError: If required secrets missing
    """
    missing_secrets = []

    # Check Anthropic API key
    if not config.secrets.anthropic_api_key:
        missing_secrets.append("ANTHROPIC_API_KEY")

    # Check Gmail credentials (exact field names depend on MCP server)
    # Adjust based on actual Gmail MCP server requirements
    if not config.secrets.gmail_credentials:
        missing_secrets.append("GMAIL_CREDENTIALS")

    # Check Warranty API credentials
    if not config.secrets.warranty_api_key:
        missing_secrets.append("WARRANTY_API_KEY")

    # Check Ticketing API credentials
    if not config.secrets.ticketing_api_key:
        missing_secrets.append("TICKETING_API_KEY")

    if missing_secrets:
        raise ConfigError(
            message=f"Missing required secrets: {', '.join(missing_secrets)}",
            code="missing_secrets",
            details={"missing_secrets": missing_secrets}
        )

def validate_instructions(config: AgentConfig) -> None:
    """
    Validate instruction files exist and parse correctly.

    Args:
        config: Agent configuration

    Raises:
        InstructionError: If instruction files invalid
    """
    # Validate main instruction file
    main_path = Path(config.instructions.main)
    if not main_path.exists():
        raise InstructionError(
            message=f"Main instruction file not found: {main_path}",
            code="main_instruction_not_found",
            details={"path": str(main_path)}
        )

    # Try loading and parsing main instruction
    try:
        main_instruction = load_instruction(str(main_path))
        logger.debug(f"Main instruction loaded: {main_instruction.name}")
    except Exception as e:
        raise InstructionError(
            message=f"Failed to parse main instruction: {e}",
            code="main_instruction_parse_failed",
            details={"path": str(main_path), "error": str(e)}
        )

    # Validate scenarios directory
    scenarios_dir = Path(config.instructions.scenarios_dir)
    if not scenarios_dir.exists():
        raise InstructionError(
            message=f"Scenarios directory not found: {scenarios_dir}",
            code="scenarios_dir_not_found",
            details={"path": str(scenarios_dir)}
        )

    # Validate required scenario files exist
    for scenario_name in REQUIRED_SCENARIOS:
        scenario_file = scenarios_dir / f"{scenario_name}.md"
        if not scenario_file.exists():
            raise InstructionError(
                message=f"Required scenario file not found: {scenario_name}.md",
                code="required_scenario_not_found",
                details={"scenario": scenario_name, "path": str(scenario_file)}
            )

        # Try loading scenario
        try:
            scenario = load_instruction(str(scenario_file))
            logger.debug(f"Scenario loaded: {scenario.name}")
        except Exception as e:
            raise InstructionError(
                message=f"Failed to parse scenario {scenario_name}: {e}",
                code="scenario_parse_failed",
                details={"scenario": scenario_name, "error": str(e)}
            )

async def test_mcp_connections(config: AgentConfig) -> None:
    """
    Test all MCP connections functional.

    Args:
        config: Agent configuration

    Raises:
        MCPConnectionError: If any MCP connection fails
    """
    connection_errors = []

    # Test Gmail MCP connection
    try:
        logger.info("[STARTUP] Testing Gmail MCP connection...")
        gmail_client = GmailClient(config)
        await asyncio.wait_for(
            gmail_client.test_connection(),  # Simple health check method
            timeout=5.0
        )
        logger.info("[STARTUP] ✓ Gmail MCP connected")
    except asyncio.TimeoutError:
        connection_errors.append("Gmail MCP connection timeout")
    except Exception as e:
        connection_errors.append(f"Gmail MCP: {str(e)}")

    # Test Warranty API MCP connection
    try:
        logger.info("[STARTUP] Testing Warranty API MCP connection...")
        warranty_client = WarrantyAPIClient(config)
        await asyncio.wait_for(
            warranty_client.test_connection(),
            timeout=5.0
        )
        logger.info("[STARTUP] ✓ Warranty API MCP connected")
    except asyncio.TimeoutError:
        connection_errors.append("Warranty API MCP connection timeout")
    except Exception as e:
        connection_errors.append(f"Warranty API MCP: {str(e)}")

    # Test Ticketing MCP connection
    try:
        logger.info("[STARTUP] Testing Ticketing MCP connection...")
        ticketing_client = TicketingClient(config)
        await asyncio.wait_for(
            ticketing_client.test_connection(),
            timeout=5.0
        )
        logger.info("[STARTUP] ✓ Ticketing MCP connected")
    except asyncio.TimeoutError:
        connection_errors.append("Ticketing MCP connection timeout")
    except Exception as e:
        connection_errors.append(f"Ticketing MCP: {str(e)}")

    if connection_errors:
        raise MCPConnectionError(
            message=f"MCP connection failures: {'; '.join(connection_errors)}",
            code="mcp_connection_test_failed",
            details={"errors": connection_errors}
        )
```

**Agent Runner Implementation:**

```python
# src/guarantee_email_agent/agent/runner.py
import asyncio
import logging
import signal
import time
from typing import List, Dict, Any
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.processor import EmailProcessor, ProcessingResult
from guarantee_email_agent.integrations.gmail import GmailClient

logger = logging.getLogger(__name__)

class AgentRunner:
    """Agent runner with inbox monitoring and graceful shutdown"""

    def __init__(self, config: AgentConfig, processor: EmailProcessor):
        """Initialize agent runner

        Args:
            config: Agent configuration
            processor: Email processor
        """
        self.config = config
        self.processor = processor
        self.gmail_client = processor.gmail_client

        # State tracking
        self._shutdown_requested = False
        self._start_time = time.time()
        self._emails_processed = 0
        self._errors_count = 0
        self._consecutive_errors = 0

        # Configuration
        self.polling_interval = config.agent.polling_interval_seconds
        self.shutdown_timeout = 30  # seconds

        logger.info("Agent runner initialized")

    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        logger.info("Signal handlers registered (SIGTERM, SIGINT)")

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signal

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(f"Shutdown requested via {signal_name}")
        self._shutdown_requested = True

    async def poll_inbox(self) -> List[Dict[str, Any]]:
        """Poll Gmail inbox for unread emails

        Returns:
            List of raw email data

        Raises:
            Exception: On Gmail API error (logged, not propagated)
        """
        try:
            logger.debug("Checking inbox...")
            emails = await self.gmail_client.get_unread_emails()

            if emails:
                logger.info(f"Found {len(emails)} unread emails")
            else:
                logger.debug("No new emails")

            return emails

        except Exception as e:
            logger.error(f"Error polling inbox: {e}", exc_info=True)
            return []  # Return empty list on error (don't crash loop)

    async def process_inbox_emails(
        self,
        emails: List[Dict[str, Any]]
    ) -> List[ProcessingResult]:
        """Process multiple emails concurrently

        Args:
            emails: List of raw email data

        Returns:
            List of processing results
        """
        if not emails:
            return []

        logger.info(f"Processing {len(emails)} emails...")

        # Process emails concurrently
        tasks = [
            self.processor.process_email(email)
            for email in emails
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        success_count = sum(1 for r in results if isinstance(r, ProcessingResult) and r.success)
        failed_count = len(results) - success_count

        logger.info(
            f"Processing complete: {success_count} succeeded, {failed_count} failed",
            extra={
                "emails_processed": len(emails),
                "success_count": success_count,
                "failed_count": failed_count
            }
        )

        # Update state
        self._emails_processed += len(emails)
        self._errors_count += failed_count

        if failed_count > 0:
            self._consecutive_errors += 1
        else:
            self._consecutive_errors = 0

        # Warn if many consecutive errors
        if self._consecutive_errors >= 10:
            logger.warning(
                f"High consecutive error count: {self._consecutive_errors} - "
                f"check MCP connections and configuration"
            )

        return [r for r in results if isinstance(r, ProcessingResult)]

    async def run(self) -> None:
        """
        Run main monitoring loop.

        Polls inbox at configured interval and processes emails until
        shutdown signal received.

        Loop will:
        - Poll inbox for unread emails
        - Process emails concurrently
        - Sleep for polling interval
        - Check shutdown flag
        - Exit gracefully on shutdown

        Note:
            Errors during processing don't crash the loop
        """
        logger.info("Entering monitoring loop")

        try:
            while not self._shutdown_requested:
                # Poll inbox
                emails = await self.poll_inbox()

                # Process emails if any found
                if emails:
                    await self.process_inbox_emails(emails)

                # Log periodic status (every 10 minutes or after processing)
                if emails or (time.time() - self._start_time) % 600 < self.polling_interval:
                    uptime = int(time.time() - self._start_time)
                    logger.info(
                        f"Status: {self._emails_processed} emails processed, "
                        f"{self._errors_count} errors, uptime: {uptime}s"
                    )

                # Check shutdown flag before sleeping
                if self._shutdown_requested:
                    break

                # Sleep until next poll
                await asyncio.sleep(self.polling_interval)

            # Shutdown requested
            logger.info("Shutdown flag set, exiting monitoring loop")
            await self._graceful_shutdown()

        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}", exc_info=True)
            raise

    async def _graceful_shutdown(self) -> None:
        """
        Perform graceful shutdown.

        - Wait for in-flight processing (max 30s)
        - Close MCP connections
        - Log final statistics
        """
        logger.info("Performing graceful shutdown...")

        # Note: In-flight processing already awaited in run() loop
        # This is where we'd wait for background tasks if any

        # Close MCP connections
        logger.info("Closing MCP connections...")
        try:
            await asyncio.wait_for(
                self._cleanup_connections(),
                timeout=self.shutdown_timeout
            )
            logger.info("✓ MCP connections closed")
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout exceeded, forcing cleanup")
            # Force cleanup even if timeout
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

        # Log final statistics
        uptime = int(time.time() - self._start_time)
        logger.info(
            f"Agent shutdown complete - "
            f"Uptime: {uptime}s, "
            f"Emails processed: {self._emails_processed}, "
            f"Errors: {self._errors_count}"
        )

    async def _cleanup_connections(self) -> None:
        """Close all MCP connections cleanly"""
        try:
            await self.processor.gmail_client.close()
        except Exception as e:
            logger.warning(f"Error closing Gmail client: {e}")

        try:
            await self.processor.warranty_client.close()
        except Exception as e:
            logger.warning(f"Error closing Warranty API client: {e}")

        try:
            await self.processor.ticketing_client.close()
        except Exception as e:
            logger.warning(f"Error closing Ticketing client: {e}")
```

**Main Entry Point:**

```python
# src/guarantee_email_agent/__main__.py
"""Main entry point for guarantee-email-agent CLI"""
from guarantee_email_agent.cli import app

if __name__ == "__main__":
    app()
```

**Version File:**

```python
# src/guarantee_email_agent/__version__.py
"""Version information for guarantee-email-agent"""

__version__ = "0.1.0"
```

### Configuration Updates

**Add agent section to config.yaml:**

```yaml
agent:
  polling_interval_seconds: 60  # Poll inbox every 60 seconds (NFR10)
  shutdown_timeout_seconds: 30  # Max time to wait for graceful shutdown
  max_consecutive_errors: 10   # Log warning after this many errors
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Not handling signals gracefully:**
   ```python
   # WRONG - Immediate exit on signal
   def handle_signal(signum, frame):
       sys.exit(0)  # Abandons in-flight emails!

   # CORRECT - Set shutdown flag, allow completion
   def handle_signal(signum, frame):
       self._shutdown_requested = True
       logger.info("Shutdown requested, completing current work...")
   ```

2. **Crashing loop on processing errors:**
   ```python
   # WRONG - Loop exits on error
   while True:
       emails = await poll_inbox()
       await process_emails(emails)  # Raises exception → loop crashes

   # CORRECT - Catch and log errors, continue loop
   while not shutdown_requested:
       try:
           emails = await poll_inbox()
           await process_emails(emails)
       except Exception as e:
           logger.error(f"Processing error: {e}", exc_info=True)
           # Continue loop
   ```

3. **Not validating on startup (NFR38 violation):**
   ```python
   # WRONG - Start agent without validation
   runner = AgentRunner(config, processor)
   await runner.run()  # Fails later during runtime!

   # CORRECT - Fail fast on startup
   await validate_startup(config)  # Raises error if invalid
   runner = AgentRunner(config, processor)
   await runner.run()
   ```

4. **Wrong exit codes (NFR29 violation):**
   ```python
   # WRONG - Generic exit code
   except ConfigError:
       sys.exit(1)  # Should be 2!

   # CORRECT - Specific exit codes
   except ConfigError:
       return 2  # Configuration error
   except MCPConnectionError:
       return 3  # MCP connection error
   ```

5. **Not closing MCP connections:**
   ```python
   # WRONG - Leave connections open
   logger.info("Shutting down")
   sys.exit(0)  # MCP connections still open!

   # CORRECT - Close connections cleanly
   await gmail_client.close()
   await warranty_client.close()
   await ticketing_client.close()
   logger.info("Connections closed")
   ```

### Verification Commands

```bash
# 1. Test CLI help
uv run python -m guarantee_email_agent --help
uv run python -m guarantee_email_agent run --help

# 2. Test version flag
uv run python -m guarantee_email_agent --version

# 3. Test startup validation (should fail with missing config)
uv run python -m guarantee_email_agent run --config missing.yaml
# Expected: Exit code 2 (config error)

# 4. Test with valid config (requires MCP servers running)
uv run python -m guarantee_email_agent run --config config.yaml

# 5. Test graceful shutdown (Ctrl+C)
uv run python -m guarantee_email_agent run &
sleep 5
kill -SIGTERM $!  # Send SIGTERM
# Expected: Graceful shutdown message, exit code 0

# 6. Test startup validation timing
uv run python -c "
import asyncio
import time
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.agent.startup import validate_startup

async def test():
    config = load_config('config.yaml')
    start = time.time()
    await validate_startup(config)
    duration = (time.time() - start) * 1000
    print(f'Validation time: {duration}ms')
    assert duration < 10000, 'Validation exceeded 10s target'

asyncio.run(test())
"

# 7. Run unit tests
uv run pytest tests/agent/test_startup.py -v
uv run pytest tests/agent/test_runner.py -v
uv run pytest tests/test_cli.py -v

# 8. Test with mock MCP servers
uv run pytest tests/agent/test_agent_integration.py -v
```

### Dependency Notes

**Depends on:**
- Story 3.4: EmailProcessor and complete pipeline
- Story 2.1: All MCP clients (Gmail, Warranty API, Ticketing)
- Story 3.1: Main instruction loader
- Story 1.2: Configuration schema and loader
- Story 1.3: Environment variable secrets
- Story 1.4: File path verification

**Blocks:**
- Story 3.6: Logging and graceful degradation (uses runner)
- Epic 4 stories: Eval framework needs running agent
- Deployment: Production deployment needs CLI

**Integration Points:**
- CLI → Startup Validator → Config + MCP validation
- CLI → AgentRunner → EmailProcessor
- AgentRunner → Gmail MCP → poll inbox
- AgentRunner → EmailProcessor → process emails
- Signal Handlers → Shutdown Flag → Graceful Exit

### Previous Story Intelligence

From Story 3.4 (End-to-End Email Processing Pipeline):
- EmailProcessor orchestrates complete workflow
- ProcessingResult tracks outcome with details
- Error handling at each step (no silent failures)
- Processing time tracking with 60s target
- create_email_processor factory for DI

From Story 2.1 (MCP Integration):
- MCP clients: GmailClient, WarrantyAPIClient, TicketingClient
- Connection testing methods (test_connection)
- Close methods for clean shutdown
- Retry and circuit breaker patterns

From Story 1.2 (Configuration):
- AgentConfig schema with Pydantic
- load_config() function
- Configuration validation

From Story 1.3 (Secrets Management):
- Secrets loaded from environment variables
- Validation for required secrets (ANTHROPIC_API_KEY, etc.)

**Learnings to Apply:**
- Fail fast on startup (NFR38)
- Proper exit codes for different error types (NFR29)
- Graceful shutdown completes in-flight work (NFR5)
- Comprehensive logging at each lifecycle stage
- State tracking for monitoring (emails processed, errors)

### Git Intelligence Summary

Recent commits show:
- Complete pipeline orchestration patterns
- Factory functions for dependency injection
- Comprehensive error handling with specific error types
- Async/await throughout
- Structured logging with context
- Testing with mocked dependencies

**Code Patterns to Continue:**
- Signal handlers with shutdown flag
- Try/except at each major step
- Resource cleanup in finally or dedicated method
- State tracking for statistics
- Typer for CLI framework (modern, clean API)

### References

**Architecture Document Sections:**
- [Source: architecture.md#Agent Lifecycle] - Startup and shutdown
- [Source: architecture.md#CLI Interface] - Typer implementation
- [Source: project-context.md#Exit Codes] - NFR29 exit code requirements
- [Source: architecture.md#Inbox Monitoring] - Polling and processing loop

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 3: Story 3.5] - Complete acceptance criteria
- [Source: prd.md#FR1] - Inbox monitoring requirement
- [Source: prd.md#NFR5] - No silent failures (shutdown)
- [Source: prd.md#NFR10] - 60-second polling interval
- [Source: prd.md#NFR12] - Environment variable secrets
- [Source: prd.md#NFR16] - Stateless agent (safe restart)
- [Source: prd.md#NFR29] - Exit code requirements
- [Source: prd.md#NFR36] - Graceful shutdown on signals
- [Source: prd.md#NFR38] - Fail fast on startup validation

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context from all previous Epic 3 stories
- Story consolidates 2 original stories (4.5 CLI Run + 4.6 Graceful Shutdown)
- CLI implementation with Typer framework (modern, clean)
- Startup validation: config, secrets, instructions, MCP connections (<10s target)
- AgentRunner with inbox polling loop and graceful shutdown
- Signal handlers for SIGTERM/SIGINT (systemd/Docker/Ctrl+C)
- Graceful completion of in-flight emails before shutdown
- 30-second shutdown timeout with force shutdown fallback
- Exit codes: 0 (success), 2 (config), 3 (MCP), 1 (other) per NFR29
- Polling interval configurable (default: 60s per NFR10)
- Concurrent email processing with asyncio.gather()
- Error resilience: processing errors don't crash loop
- State tracking: emails processed, errors, uptime
- Clean MCP connection cleanup on shutdown
- Startup banner with version and configuration summary
- Complete CLI implementation with --version and --config options
- Testing strategy: startup validation, runner loop, shutdown, integration
- Verification commands for lifecycle testing

### File List

**CLI and Entry Point:**
- `src/guarantee_email_agent/cli.py` - Typer CLI with run command
- `src/guarantee_email_agent/__main__.py` - Main entry point
- `src/guarantee_email_agent/__version__.py` - Version information

**Startup Validation:**
- `src/guarantee_email_agent/agent/startup.py` - Startup validator with all checks

**Agent Runner:**
- `src/guarantee_email_agent/agent/runner.py` - AgentRunner with monitoring loop and shutdown

**Module Exports:**
- `src/guarantee_email_agent/agent/__init__.py` - Agent module exports

**Configuration Updates:**
- `config.yaml` - Add agent section with polling_interval_seconds

**Tests:**
- `tests/agent/test_startup.py` - Startup validation tests
- `tests/agent/test_runner.py` - Agent runner and loop tests
- `tests/test_cli.py` - CLI command tests
- `tests/agent/test_agent_integration.py` - Complete lifecycle integration tests
