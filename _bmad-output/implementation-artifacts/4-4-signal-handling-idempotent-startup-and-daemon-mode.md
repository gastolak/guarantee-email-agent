# Story 4.4: Signal Handling, Idempotent Startup, and Daemon Mode

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want the agent to respect Unix signals, support daemon mode, and have idempotent startup,
So that it integrates with process supervisors and can be deployed reliably.

## Acceptance Criteria

**Given** The complete agent with all hardening from previous stories
**When** I deploy the agent to production

**Then - Unix Signal Handling:**
**And** Signal handler in `src/guarantee_email_agent/agent/runner.py` catches all required signals
**And** SIGTERM: Triggers graceful shutdown (complete in-flight, exit code 0 per NFR30)
**And** SIGINT: Triggers immediate stop (Ctrl+C, exit code 0 per NFR30)
**And** SIGHUP: Triggers log rotation (closes/reopens log files per NFR32)
**And** Signal handling logs clearly: "SIGTERM received, initiating graceful shutdown"
**And** Works with systemd: `systemctl stop agent` sends SIGTERM
**And** Works with launchd: macOS process management
**And** Process supervisors (supervisord) can manage lifecycle
**And** Agent exits cleanly without orphaned processes
**And** Signal handling does not interfere with normal operations

**Then - Idempotent Startup:**
**And** Startup is idempotent - safe to run repeatedly (NFR33)
**And** Configuration validation runs on every startup (not cached)
**And** MCP connection tests run on every startup
**And** Instruction file validation runs on every startup
**And** No state persists between restarts (stateless per NFR16)
**And** Restarting doesn't duplicate email processing (emails in Gmail until processed)
**And** Crashed agent can restart cleanly without manual cleanup
**And** Startup logs: "Agent starting (restart safe, idempotent)"
**And** Runs as single process manageable by systemd/launchd (NFR31)
**And** No background threads or child processes that survive restart
**And** All resources cleaned up on exit (no leaked connections)

**Then - Stdout/Stderr Output:**
**And** Normal logs (INFO, DEBUG) write to stdout (FR50)
**And** Error logs (WARN, ERROR) write to stderr (FR50)
**And** Works in shell pipelines: `agent run | grep "Email processed"`
**And** Stderr redirectable separately: `agent run 2> errors.log`
**And** Works in CI/CD: logs captured correctly by Jenkins, GitHub Actions
**And** Background daemon captures logs: `agent run > agent.log 2>&1 &`
**And** Respects Unix conventions for stdout/stderr
**And** Output suitable for log aggregation tools (NFR31)

**Then - Daemon Mode Deployment:**
**And** Agent can run as background daemon: `uv run python -m guarantee_email_agent run &`
**And** Continues running after terminal disconnect (nohup compatible)
**And** Writes logs to configured file for persistent monitoring
**And** Process checkable: `pgrep -f "agent run"` returns PID
**And** Process stoppable: `pkill -TERM -f "agent run"` triggers graceful shutdown
**And** Integrates with systemd service files for automatic startup
**And** Integrates with launchd plists for macOS daemon mode
**And** Railway deployment works with Procfile: `web: uv run python -m guarantee_email_agent run`
**And** Single-process (no child processes) per NFR31
**And** Container deployment works: runs correctly in Docker/Kubernetes

**Then - Log Rotation Support:**
**And** SIGHUP signal triggers log rotation
**And** On SIGHUP: close current log file handlers
**And** On SIGHUP: reopen log files with same paths
**And** Log rotation doesn't interrupt agent operation
**And** Compatible with logrotate utility
**And** Log: "SIGHUP received, rotating log files"
**And** File handles released properly for external rotation tools

**Then - Process Management Integration:**
**And** Systemd service file example provided in `deployment/systemd/agent.service`
**And** Launchd plist example provided in `deployment/launchd/com.example.agent.plist`
**And** Docker entrypoint example provided in `deployment/docker/entrypoint.sh`
**And** Railway Procfile already exists and works
**And** All examples tested and documented
**And** Process supervisor configuration examples (optional)

## Tasks / Subtasks

### Signal Handler Enhancement

- [ ] Extend SIGTERM/SIGINT handlers (AC: handles all required signals)
  - [ ] Already implemented in Story 3.5, verify complete
  - [ ] SIGTERM → graceful shutdown (complete in-flight)
  - [ ] SIGINT → immediate stop (Ctrl+C)
  - [ ] Both log signal name and exit with code 0
  - [ ] Verify no orphaned processes after signal
  - [ ] Test with systemd and Docker

- [ ] Add SIGHUP handler for log rotation (AC: SIGHUP triggers log rotation)
  - [ ] Create `_handle_sighup(signum, frame)` method in AgentRunner
  - [ ] Set log rotation flag: `self._log_rotation_requested = True`
  - [ ] Log: "SIGHUP received, rotating log files"
  - [ ] Don't interrupt agent operation
  - [ ] Call log rotation on next loop iteration
  - [ ] Register handler: `signal.signal(signal.SIGHUP, self._handle_sighup)`

- [ ] Implement log rotation logic (AC: close/reopen log files)
  - [ ] Create `_rotate_logs() -> None` method
  - [ ] Close all file log handlers
  - [ ] Reopen log files with same paths
  - [ ] Re-register handlers with logger
  - [ ] Log: "Log rotation complete"
  - [ ] Handle rotation errors gracefully
  - [ ] Compatible with logrotate utility

- [ ] Add signal handling documentation (AC: signal handling logs clearly)
  - [ ] Document all signal behaviors in code comments
  - [ ] Log each signal with clear message
  - [ ] Include signal name and action in logs
  - [ ] Example: "SIGTERM received, initiating graceful shutdown"
  - [ ] Example: "SIGHUP received, rotating log files"
  - [ ] Example: "SIGINT received, stopping immediately"

- [ ] Verify systemd integration (AC: works with systemd)
  - [ ] Test with systemd service file
  - [ ] `systemctl start agent` → agent starts
  - [ ] `systemctl stop agent` → SIGTERM → graceful shutdown
  - [ ] `systemctl restart agent` → stop + start
  - [ ] `systemctl status agent` → shows running status
  - [ ] Logs visible in journalctl

- [ ] Verify launchd integration (AC: works with launchd)
  - [ ] Test with launchd plist file
  - [ ] `launchctl load` → agent starts
  - [ ] `launchctl unload` → SIGTERM → graceful shutdown
  - [ ] `launchctl start` / `launchctl stop`
  - [ ] Logs visible in system logs
  - [ ] Auto-restart on crash if configured

### Idempotent Startup Implementation

- [ ] Document idempotent startup behavior (AC: startup is idempotent)
  - [ ] Add comment in cli.py: "Startup is idempotent - safe to run repeatedly"
  - [ ] Log: "Agent starting (restart safe, idempotent)"
  - [ ] Document in README.md
  - [ ] Explain no manual cleanup needed after crash
  - [ ] Describe stateless architecture (NFR16)

- [ ] Verify configuration validation runs on every startup (AC: validation runs every startup)
  - [ ] Already implemented in Story 3.5 (startup.py)
  - [ ] validate_startup() called every time
  - [ ] No caching of validation results
  - [ ] Config loaded fresh from file each time
  - [ ] Test: modify config, restart → new config loaded

- [ ] Verify MCP connection tests run on every startup (AC: MCP tests every startup)
  - [ ] Already implemented in Story 3.5
  - [ ] test_mcp_connections() called every time
  - [ ] No cached connection status
  - [ ] Fresh connections established
  - [ ] Test: stop MCP server, restart agent → error detected

- [ ] Verify instruction validation runs on every startup (AC: instruction validation every startup)
  - [ ] Already implemented in Story 3.5
  - [ ] validate_instructions() called every time
  - [ ] No cached instruction files
  - [ ] Fresh parsing on each start
  - [ ] Test: modify instruction, restart → changes detected

- [ ] Verify stateless operation (AC: no state persists between restarts)
  - [ ] Review code for any persistent state
  - [ ] No database writes (NFR16)
  - [ ] No local file writes except logs
  - [ ] All state in memory only
  - [ ] Email state managed by Gmail (unread until processed)
  - [ ] Test: restart agent → no duplicate processing

- [ ] Verify single-process architecture (AC: single process manageable)
  - [ ] No child processes spawned
  - [ ] No background threads that survive shutdown
  - [ ] All async tasks cleaned up properly
  - [ ] MCP servers run as separate processes (not children of agent)
  - [ ] Test: `pgrep -f "agent run"` → only one PID

- [ ] Add resource cleanup verification (AC: all resources cleaned up)
  - [ ] All MCP connections closed in cleanup
  - [ ] All file handles closed
  - [ ] All async tasks cancelled
  - [ ] No leaked sockets or connections
  - [ ] Test with lsof/netstat after shutdown

- [ ] Add restart safety tests
  - [ ] Test: start → stop → start → verify works
  - [ ] Test: start → kill -9 → start → verify works (crash recovery)
  - [ ] Test: start → SIGTERM → start → verify works
  - [ ] Test: modify config → restart → new config applied
  - [ ] Test: restart during email processing → no duplicates

### Stdout/Stderr Output Implementation

- [ ] Configure stdout/stderr logging (AC: INFO/DEBUG to stdout, WARN/ERROR to stderr)
  - [ ] Update `src/guarantee_email_agent/utils/logging.py`
  - [ ] Create two handlers: stdout_handler, stderr_handler
  - [ ] stdout_handler: level=DEBUG, stream=sys.stdout
  - [ ] stderr_handler: level=WARNING, stream=sys.stderr
  - [ ] Add both handlers to root logger
  - [ ] Test output redirection works correctly

- [ ] Implement log level filtering (AC: separate streams)
  - [ ] Create custom filter for stdout handler
  - [ ] Filter: only DEBUG and INFO levels
  - [ ] stderr handler gets WARN, ERROR, CRITICAL
  - [ ] Ensure no duplicate logs across streams
  - [ ] Test: `agent run | grep INFO` captures stdout only
  - [ ] Test: `agent run 2> errors.log` captures stderr only

- [ ] Verify shell pipeline compatibility (AC: works in pipelines)
  - [ ] Test: `agent run | grep "Email processed"` works
  - [ ] Test: `agent run | head -10` works
  - [ ] Test: `agent run 2>&1 | tee full.log` works
  - [ ] Test: `agent run > stdout.log 2> stderr.log` works
  - [ ] Output buffering doesn't interfere
  - [ ] Flush logs appropriately

- [ ] Verify CI/CD compatibility (AC: works in CI/CD)
  - [ ] Test in Jenkins: logs captured correctly
  - [ ] Test in GitHub Actions: logs visible in workflow
  - [ ] Test in GitLab CI: logs separated by level
  - [ ] Exit codes work correctly for CI failure detection
  - [ ] No output buffering issues in CI

- [ ] Add background daemon log capture (AC: daemon captures logs)
  - [ ] Test: `agent run > agent.log 2>&1 &` works
  - [ ] Logs written to agent.log continuously
  - [ ] File logging enabled via config
  - [ ] Both stdout and file logging work simultaneously
  - [ ] Test log rotation with background daemon

- [ ] Document output conventions (AC: respects Unix conventions)
  - [ ] Document stdout/stderr separation in README
  - [ ] Provide examples of redirection
  - [ ] Explain log aggregation compatibility
  - [ ] Document file logging configuration
  - [ ] Add examples for common scenarios

### Daemon Mode Support

- [ ] Verify background daemon operation (AC: runs as background daemon)
  - [ ] Test: `uv run python -m guarantee_email_agent run &` works
  - [ ] Agent continues running in background
  - [ ] Returns control to shell immediately
  - [ ] Logs written to configured file
  - [ ] Test: exit shell → agent still running

- [ ] Add nohup compatibility (AC: continues after terminal disconnect)
  - [ ] Test: `nohup agent run &` works
  - [ ] Agent survives terminal disconnect
  - [ ] Output redirected to nohup.out if not specified
  - [ ] SIGHUP ignored when running with nohup
  - [ ] Document nohup usage in README

- [ ] Implement file logging configuration (AC: writes logs to configured file)
  - [ ] Add file_path to logging config section
  - [ ] Create file handler if path configured
  - [ ] Log to both stdout and file simultaneously
  - [ ] Rotate file logs on SIGHUP
  - [ ] Example config: `logging.file_path: "./logs/agent.log"`
  - [ ] Create log directory if doesn't exist

- [ ] Add process management utilities (AC: process checkable/stoppable)
  - [ ] Document: `pgrep -f "agent run"` to find PID
  - [ ] Document: `pkill -TERM -f "agent run"` to stop
  - [ ] Document: `ps aux | grep agent` to check status
  - [ ] Create helper script: `scripts/agent-status.sh`
  - [ ] Create helper script: `scripts/agent-stop.sh`
  - [ ] Add to README

- [ ] Verify single-process requirement (AC: single-process)
  - [ ] No forking or multiprocessing
  - [ ] No subprocess spawning from agent
  - [ ] MCP servers are separate processes (not children)
  - [ ] All async via asyncio (single thread)
  - [ ] Test: only one process shows in `ps`

- [ ] Add container deployment verification (AC: works in Docker/Kubernetes)
  - [ ] Create Dockerfile for testing
  - [ ] Test: `docker run agent` works
  - [ ] Test: logs visible in `docker logs`
  - [ ] Test: `docker stop` → graceful shutdown
  - [ ] Test: Kubernetes pod restart → works cleanly
  - [ ] Document container best practices

### Process Supervisor Integration

- [ ] Create systemd service file (AC: systemd service file example)
  - [ ] Create `deployment/systemd/agent.service`
  - [ ] Configure: Type=simple (single process)
  - [ ] Configure: ExecStart with full command
  - [ ] Configure: Restart=on-failure
  - [ ] Configure: Environment variables
  - [ ] Configure: WorkingDirectory
  - [ ] Test with systemd

- [ ] Create launchd plist file (AC: launchd plist example)
  - [ ] Create `deployment/launchd/com.example.agent.plist`
  - [ ] Configure: ProgramArguments
  - [ ] Configure: RunAtLoad=true
  - [ ] Configure: KeepAlive=true
  - [ ] Configure: StandardOutPath and StandardErrorPath
  - [ ] Configure: WorkingDirectory
  - [ ] Test on macOS

- [ ] Create Docker entrypoint (AC: Docker entrypoint example)
  - [ ] Create `deployment/docker/entrypoint.sh`
  - [ ] Handle signal forwarding to agent
  - [ ] Set up environment variables
  - [ ] Configure logging
  - [ ] Execute agent with exec (PID 1)
  - [ ] Test in container

- [ ] Verify Railway Procfile (AC: Railway Procfile works)
  - [ ] Procfile already exists from project setup
  - [ ] Content: `web: uv run python -m guarantee_email_agent run`
  - [ ] Verify Railway detects and uses it
  - [ ] Verify logs visible in Railway dashboard
  - [ ] Verify graceful shutdown on redeploy
  - [ ] Document Railway deployment

- [ ] Add supervisord configuration example (AC: examples provided)
  - [ ] Create `deployment/supervisord/agent.conf` (optional)
  - [ ] Configure: command, autostart, autorestart
  - [ ] Configure: stdout/stderr log paths
  - [ ] Configure: environment variables
  - [ ] Document but mark as optional

- [ ] Document all deployment options
  - [ ] Create `docs/deployment.md`
  - [ ] Section: Systemd deployment
  - [ ] Section: Launchd deployment
  - [ ] Section: Docker deployment
  - [ ] Section: Railway deployment
  - [ ] Section: Kubernetes deployment (optional)
  - [ ] Include examples for each

### Railway Deployment Enhancements

- [ ] Verify Railway configuration
  - [ ] Procfile: `web: uv run python -m guarantee_email_agent run`
  - [ ] Environment variables set in Railway dashboard
  - [ ] Logs visible in Railway logs view
  - [ ] Graceful shutdown on redeploy
  - [ ] Health check endpoint (optional for future)

- [ ] Add Railway deployment documentation
  - [ ] Document environment variable setup
  - [ ] Document build process (uv sync)
  - [ ] Document logs access
  - [ ] Document restart/redeploy process
  - [ ] Add troubleshooting section

### Testing

- [ ] Create signal handler tests
  - [ ] Create `tests/agent/test_signals.py`
  - [ ] Test SIGTERM handler → graceful shutdown
  - [ ] Test SIGINT handler → immediate stop
  - [ ] Test SIGHUP handler → log rotation
  - [ ] Test signal during processing → completes then exits
  - [ ] Mock signals for testing
  - [ ] Verify exit codes correct

- [ ] Create idempotent startup tests
  - [ ] Test startup runs all validations every time
  - [ ] Test restart after clean shutdown
  - [ ] Test restart after crash (simulated)
  - [ ] Test restart after SIGTERM
  - [ ] Test modified config picked up on restart
  - [ ] Test no duplicate email processing
  - [ ] Verify stateless operation

- [ ] Create stdout/stderr output tests
  - [ ] Test INFO logs go to stdout
  - [ ] Test ERROR logs go to stderr
  - [ ] Test redirection works: `> stdout.log 2> stderr.log`
  - [ ] Test pipeline works: `| grep`
  - [ ] Test file + stdout logging simultaneously
  - [ ] Capture and assert on output streams

- [ ] Create daemon mode tests
  - [ ] Test background execution: `run &`
  - [ ] Test process findable with pgrep
  - [ ] Test process stoppable with pkill
  - [ ] Test file logging works in background
  - [ ] Test nohup compatibility
  - [ ] Verify single process

- [ ] Create log rotation tests
  - [ ] Test SIGHUP triggers rotation
  - [ ] Test log file closed and reopened
  - [ ] Test rotation doesn't interrupt operation
  - [ ] Test new logs written to rotated file
  - [ ] Mock signal for testing
  - [ ] Verify file handles released

- [ ] Create deployment integration tests
  - [ ] Test systemd service (if on Linux)
  - [ ] Test launchd plist (if on macOS)
  - [ ] Test Docker deployment
  - [ ] Test Railway deployment (integration test)
  - [ ] Verify all deployment examples work
  - [ ] Optional: test in CI environment

## Dev Notes

### Architecture Context

This story implements **Signal Handling, Idempotent Startup, and Daemon Mode** (consolidates old stories 6.3, 6.4, 6.6, 6.7), completing Epic 4 and providing production-grade operational capabilities.

**Key Architectural Principles:**
- NFR30: Respect standard Unix signals (SIGTERM/SIGINT/SIGHUP)
- NFR31: Run as single process manageable by systemd/launchd
- NFR32: Log rotation compatible (SIGHUP)
- NFR33: Idempotent startup (safe to restart)
- NFR16: Stateless operation (no persistent state)
- FR50: Stdout/stderr output separation

### Critical Implementation Rules from Project Context

**Enhanced Signal Handling:**

```python
# src/guarantee_email_agent/agent/runner.py (extend existing)
import signal
import logging

logger = logging.getLogger(__name__)

class AgentRunner:
    def __init__(self, config: AgentConfig, processor: EmailProcessor):
        # ... existing init ...
        self._shutdown_requested = False
        self._log_rotation_requested = False

    def register_signal_handlers(self):
        """Register all signal handlers"""
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGHUP, self._handle_sighup)
        logger.info("Signal handlers registered (SIGTERM, SIGINT, SIGHUP)")

    def _handle_shutdown_signal(self, signum, frame):
        """Handle SIGTERM/SIGINT for graceful shutdown

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(f"{signal_name} received, initiating graceful shutdown")
        self._shutdown_requested = True

    def _handle_sighup(self, signum, frame):
        """Handle SIGHUP for log rotation

        Args:
            signum: Signal number (SIGHUP)
            frame: Current stack frame
        """
        logger.info("SIGHUP received, rotating log files")
        self._log_rotation_requested = True

    async def run(self) -> None:
        """Run main monitoring loop with signal handling"""
        logger.info("Agent starting (restart safe, idempotent)")
        logger.info("Entering monitoring loop")

        try:
            while not self._shutdown_requested:
                # Check log rotation flag
                if self._log_rotation_requested:
                    self._rotate_logs()
                    self._log_rotation_requested = False

                # ... existing polling logic ...

                if self._shutdown_requested:
                    break

                await asyncio.sleep(self.polling_interval)

            logger.info("Shutdown flag set, exiting monitoring loop")
            await self._graceful_shutdown()

        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}", exc_info=True)
            raise

    def _rotate_logs(self):
        """Rotate log files by closing and reopening handlers"""
        try:
            logger.info("Starting log rotation...")

            # Get root logger
            root_logger = logging.getLogger()

            # Close all file handlers
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    root_logger.removeHandler(handler)

            # Reopen file handlers (will be recreated by logging config)
            # In practice, we'd reload logging configuration here
            from guarantee_email_agent.utils.logging import setup_file_logging
            setup_file_logging(self.config.logging.file_path)

            logger.info("Log rotation complete")

        except Exception as e:
            logger.error(f"Error during log rotation: {e}", exc_info=True)
```

**Stdout/Stderr Logging Configuration:**

```python
# src/guarantee_email_agent/utils/logging.py (enhance existing)
import sys
import logging

class StdoutFilter(logging.Filter):
    """Filter that only allows INFO and DEBUG levels"""

    def filter(self, record):
        return record.levelno <= logging.INFO

def setup_logging(config):
    """
    Setup logging with stdout/stderr separation.

    - DEBUG, INFO → stdout
    - WARNING, ERROR, CRITICAL → stderr
    - Optionally write to file as well

    Args:
        config: Logging configuration
    """
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Stdout handler (DEBUG and INFO only)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(StdoutFilter())

    # Stderr handler (WARNING and above)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)

    # Add file handler if configured
    if hasattr(config, 'file_path') and config.file_path:
        setup_file_logging(config.file_path)

    logging.info("Logging configured (stdout/stderr separation)")

def setup_file_logging(file_path: str):
    """Add file logging handler

    Args:
        file_path: Path to log file
    """
    try:
        # Create directory if needed
        from pathlib import Path
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        logging.info(f"File logging enabled: {file_path}")

    except Exception as e:
        logging.error(f"Failed to setup file logging: {e}", exc_info=True)
```

**Systemd Service File:**

```ini
# deployment/systemd/agent.service
[Unit]
Description=Guarantee Email Agent
After=network.target

[Service]
Type=simple
User=agent
Group=agent
WorkingDirectory=/opt/guarantee-email-agent

# Environment variables
Environment="ANTHROPIC_API_KEY=your-key-here"
Environment="GMAIL_CREDENTIALS=/opt/guarantee-email-agent/credentials.json"
Environment="WARRANTY_API_KEY=your-key-here"
Environment="TICKETING_API_KEY=your-key-here"

# Start command
ExecStart=/usr/local/bin/uv run python -m guarantee_email_agent run --config /opt/guarantee-email-agent/config.yaml

# Restart policy
Restart=on-failure
RestartSec=10s

# Logs
StandardOutput=journal
StandardError=journal

# Process management
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

**Launchd Plist File:**

```xml
<!-- deployment/launchd/com.example.agent.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.example.guarantee-email-agent</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/uv</string>
        <string>run</string>
        <string>python</string>
        <string>-m</string>
        <string>guarantee_email_agent</string>
        <string>run</string>
        <string>--config</string>
        <string>/opt/guarantee-email-agent/config.yaml</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/opt/guarantee-email-agent</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>your-key-here</string>
        <key>GMAIL_CREDENTIALS</key>
        <string>/opt/guarantee-email-agent/credentials.json</string>
        <key>WARRANTY_API_KEY</key>
        <string>your-key-here</string>
        <key>TICKETING_API_KEY</key>
        <string>your-key-here</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/opt/guarantee-email-agent/logs/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/opt/guarantee-email-agent/logs/stderr.log</string>
</dict>
</plist>
```

**Docker Entrypoint:**

```bash
#!/bin/bash
# deployment/docker/entrypoint.sh

set -e

# Handle signals and forward to agent
_term() {
    echo "SIGTERM received, forwarding to agent..."
    kill -TERM "$agent_pid" 2>/dev/null
}

trap _term SIGTERM SIGINT

# Start agent in background
uv run python -m guarantee_email_agent run &
agent_pid=$!

# Wait for agent to exit
wait "$agent_pid"
exit_code=$?

echo "Agent exited with code $exit_code"
exit $exit_code
```

**Dockerfile:**

```dockerfile
# deployment/docker/Dockerfile
FROM python:3.10-slim

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY instructions/ ./instructions/
COPY config.yaml ./

# Install dependencies
RUN uv sync --frozen

# Copy entrypoint
COPY deployment/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run as non-root user
RUN useradd -m -u 1000 agent
USER agent

# Use entrypoint
ENTRYPOINT ["/entrypoint.sh"]
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Not handling SIGHUP correctly:**
   ```python
   # WRONG - Ignore SIGHUP
   signal.signal(signal.SIGHUP, signal.SIG_IGN)

   # CORRECT - Handle for log rotation
   signal.signal(signal.SIGHUP, self._handle_sighup)
   ```

2. **Spawning child processes (violates NFR31):**
   ```python
   # WRONG - Spawns child process
   subprocess.Popen(["mcp-server"])

   # CORRECT - MCP servers run independently, not as children
   # Agent connects to existing MCP servers via stdio
   ```

3. **Not closing file handles on log rotation:**
   ```python
   # WRONG - Don't release file handles
   def rotate_logs():
       logger.info("Rotating...")
       # File still open!

   # CORRECT - Close and reopen
   def rotate_logs():
       for handler in logger.handlers:
           if isinstance(handler, FileHandler):
               handler.close()  # Release file handle
               # Recreate handler
   ```

4. **Mixed stdout/stderr output:**
   ```python
   # WRONG - Everything to stdout
   print("ERROR: Something failed")  # Should go to stderr!

   # CORRECT - Use logging with proper levels
   logger.error("Something failed")  # Goes to stderr
   logger.info("Processing...")  # Goes to stdout
   ```

5. **Stateful startup (violates NFR33):**
   ```python
   # WRONG - Cache validation results
   if not self._validated:
       validate_startup()
       self._validated = True

   # CORRECT - Validate every time
   validate_startup()  # Always run, no caching
   ```

### Verification Commands

```bash
# 1. Test SIGTERM handling
uv run python -m guarantee_email_agent run &
PID=$!
sleep 5
kill -TERM $PID
# Expected: "SIGTERM received, initiating graceful shutdown", exit code 0

# 2. Test SIGHUP log rotation
uv run python -m guarantee_email_agent run &
PID=$!
sleep 5
kill -HUP $PID
# Expected: "SIGHUP received, rotating log files", agent continues running
kill -TERM $PID

# 3. Test stdout/stderr separation
uv run python -m guarantee_email_agent run > stdout.log 2> stderr.log &
PID=$!
sleep 10
kill -TERM $PID
cat stdout.log  # Should have INFO logs
cat stderr.log  # Should have ERROR logs (if any)

# 4. Test idempotent restart
uv run python -m guarantee_email_agent run &
PID=$!
sleep 5
kill -TERM $PID
sleep 2
uv run python -m guarantee_email_agent run
# Expected: Starts cleanly, no errors about existing state

# 5. Test systemd integration (Linux)
sudo cp deployment/systemd/agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start agent
sudo systemctl status agent
# Expected: "active (running)"
sudo systemctl stop agent
# Expected: "SIGTERM received", clean shutdown
sudo systemctl restart agent
# Expected: Stop + start, works cleanly

# 6. Test launchd integration (macOS)
cp deployment/launchd/com.example.agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.example.agent.plist
launchctl list | grep agent
# Expected: Agent listed
launchctl unload ~/Library/LaunchAgents/com.example.agent.plist
# Expected: Clean shutdown

# 7. Test Docker deployment
docker build -t agent -f deployment/docker/Dockerfile .
docker run --name test-agent agent &
sleep 10
docker stop test-agent
# Expected: Graceful shutdown
docker logs test-agent
# Expected: Startup and shutdown logs visible

# 8. Test process findability
uv run python -m guarantee_email_agent run &
pgrep -f "agent run"
# Expected: PID returned
pkill -TERM -f "agent run"
# Expected: Graceful shutdown

# 9. Test nohup compatibility
nohup uv run python -m guarantee_email_agent run &
# Close terminal
# Reopen terminal
pgrep -f "agent run"
# Expected: Still running
pkill -TERM -f "agent run"

# 10. Run unit tests
uv run pytest tests/agent/test_signals.py -v
uv run pytest tests/agent/test_idempotent.py -v
uv run pytest tests/agent/test_daemon.py -v
```

### Dependency Notes

**Depends on:**
- Story 3.5: CLI run command and graceful shutdown (extends signal handling)
- Story 3.6: Structured logging (extends for stdout/stderr)
- Story 4.3: Error handling and exit codes
- All Epic 1-3 stories: Complete implementation

**Blocks:**
- Production deployment: Final production readiness requirement
- None - this is the last story in Epic 4

**Integration Points:**
- Signal handlers → AgentRunner from 3.5
- Log rotation → Logging setup from 3.6
- Idempotent startup → Startup validation from 3.5
- Stdout/stderr → Logging configuration from 3.6
- Daemon mode → CLI from 3.5

### Previous Story Intelligence

From Story 3.5 (CLI Run + Graceful Shutdown):
- SIGTERM/SIGINT handlers already implemented
- Graceful shutdown logic in place
- AgentRunner with monitoring loop
- StartupValidator runs all checks

From Story 3.6 (Logging):
- Structured logging with extra dict
- Log levels: DEBUG, INFO, WARN, ERROR
- Customer data protection
- File logging support

From Story 4.3 (Error Handling):
- Exit codes: 0, 1, 2, 3, 4
- AgentError hierarchy
- Comprehensive error logging
- Stack trace inclusion

**Learnings to Apply:**
- Extend existing signal handlers (don't replace)
- Add SIGHUP without breaking SIGTERM/SIGINT
- Enhance logging setup for stdout/stderr
- Document idempotent behavior clearly
- Provide deployment examples for each platform
- Test thoroughly with process supervisors

### Git Intelligence Summary

Recent commits show:
- Signal handling infrastructure exists
- Graceful shutdown working
- Logging framework in place
- Exit codes implemented
- Stateless operation confirmed

**Code Patterns to Continue:**
- Signal handlers in AgentRunner
- Logging configuration in utils/logging.py
- Exit code constants and mapping
- Async cleanup methods
- Resource cleanup in shutdown

### References

**Architecture Document Sections:**
- [Source: architecture.md#Signal Handling] - Unix signal support
- [Source: architecture.md#Process Management] - Systemd/launchd integration
- [Source: architecture.md#Logging] - Stdout/stderr separation
- [Source: project-context.md#Deployment] - Railway, Docker, Kubernetes

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 4: Story 4.4] - Complete acceptance criteria
- [Source: prd.md#NFR30] - Standard Unix signal handling
- [Source: prd.md#NFR31] - Single-process design
- [Source: prd.md#NFR32] - Log rotation compatibility
- [Source: prd.md#NFR33] - Idempotent startup
- [Source: prd.md#NFR16] - Stateless operation
- [Source: prd.md#FR50] - Stdout/stderr output

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context from all previous stories
- Story 4.4 completes Epic 4 and entire project
- Consolidates 4 original stories (6.3, 6.4, 6.6, 6.7)
- Enhanced signal handling: SIGTERM, SIGINT, SIGHUP
- SIGHUP triggers log rotation without interrupting operation
- Idempotent startup: safe to restart repeatedly
- Stateless operation: no persistent state between restarts
- Stdout/stderr separation: INFO/DEBUG → stdout, WARN/ERROR → stderr
- Daemon mode support: background execution, nohup compatible
- Single-process architecture: manageable by systemd/launchd
- Process management examples: systemd, launchd, Docker, Railway
- Log rotation compatible with logrotate utility
- Complete deployment documentation and examples
- Verification commands for all features
- Testing strategy: signals, idempotent, daemon, deployment

### File List

**Signal Handling Extensions:**
- `src/guarantee_email_agent/agent/runner.py` - Add SIGHUP handler, log rotation

**Logging Enhancements:**
- `src/guarantee_email_agent/utils/logging.py` - Stdout/stderr separation, file logging

**Deployment Examples:**
- `deployment/systemd/agent.service` - Systemd service file
- `deployment/launchd/com.example.agent.plist` - Launchd plist
- `deployment/docker/Dockerfile` - Docker container
- `deployment/docker/entrypoint.sh` - Docker entrypoint with signal forwarding
- `Procfile` - Railway deployment (already exists, verify)

**Documentation:**
- `docs/deployment.md` - Complete deployment guide
- `README.md` - Update with deployment sections

**Helper Scripts:**
- `scripts/agent-status.sh` - Check agent status
- `scripts/agent-stop.sh` - Stop agent gracefully

**Tests:**
- `tests/agent/test_signals.py` - Signal handling tests
- `tests/agent/test_idempotent.py` - Idempotent startup tests
- `tests/agent/test_daemon.py` - Daemon mode tests
- `tests/agent/test_deployment.py` - Deployment integration tests
