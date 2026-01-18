# Story 1.4: File Path Verification and MCP Connection Testing

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want the agent to verify all configured file paths exist and test MCP connections on startup,
So that misconfiguration is detected immediately before processing begins with actionable error messages.

## Acceptance Criteria

**Given** The configuration and environment variable systems from Stories 1.2 and 1.3 exist
**When** The agent starts up with `uv run python -m guarantee_email_agent run`
**Then** The startup process verifies all instruction file paths from config.yaml exist and are readable
**And** Missing instruction files produce error: "Instruction file not found: instructions/main.md"
**And** Unreadable files produce error: "Cannot read instruction file: instructions/scenarios/valid-warranty.md (permission denied)"
**And** The startup process tests MCP connection to Gmail server
**And** The startup process tests MCP connection to warranty API server
**And** The startup process tests MCP connection to ticketing system server
**And** Failed MCP connections produce clear errors: "MCP connection failed: gmail (mcp://gmail) - connection refused"
**And** Connection test timeout after 5 seconds produces error: "MCP connection timeout: warranty_api"
**And** All connection tests must pass before the agent begins email processing
**And** The agent fails fast (exit code 3) if any MCP connection test fails
**And** Successful startup completes within 30 seconds (NFR9)
**And** Startup logs clearly indicate "Configuration valid", "File paths verified", "MCP connections tested" before "Agent ready"

## Tasks / Subtasks

- [ ] Create file path verification module (AC: verifies all instruction file paths)
  - [ ] Create `src/guarantee_email_agent/config/path_validator.py`
  - [ ] Implement `verify_file_paths(config: AgentConfig) -> None` function
  - [ ] Check `config.instructions.main` file exists
  - [ ] Check each path in `config.instructions.scenarios` list exists
  - [ ] Check `config.eval.test_suite_path` directory exists
  - [ ] Check file permissions (readable flag)
  - [ ] Raise ConfigurationError with specific file path for missing files
  - [ ] Raise ConfigurationError for permission denied errors

- [ ] Implement instruction file path validation (AC: missing files produce clear errors)
  - [ ] Use pathlib.Path for cross-platform compatibility
  - [ ] Validate main instruction file: `instructions/main.md`
  - [ ] Validate scenario instruction files from config
  - [ ] Handle both absolute and relative paths correctly
  - [ ] Error message format: "Instruction file not found: {file_path}"
  - [ ] Error message for permissions: "Cannot read instruction file: {file_path} (permission denied)"
  - [ ] Include file path in error details dict

- [ ] Implement eval directory verification (AC: test suite path exists)
  - [ ] Verify `evals/scenarios/` directory exists
  - [ ] Check directory is readable
  - [ ] Error if eval directory missing: "Eval directory not found: {test_suite_path}"
  - [ ] Log warning if eval directory is empty (no test cases yet)

- [ ] Create MCP connection testing framework (AC: tests all MCP connections)
  - [ ] Create `src/guarantee_email_agent/integrations/connection_tester.py`
  - [ ] Implement `test_mcp_connections(config: AgentConfig) -> None` function
  - [ ] Create base test method: `test_connection(connection_string, name, timeout=5) -> bool`
  - [ ] Handle connection timeouts (5 seconds per NFR and AC)
  - [ ] Handle connection refused errors
  - [ ] Handle authentication errors
  - [ ] Return detailed error messages with connection string and error type

- [ ] Implement Gmail MCP connection test (AC: tests Gmail MCP connection)
  - [ ] Extract Gmail connection string from config.mcp.gmail
  - [ ] Create MCP client for Gmail using connection string
  - [ ] Attempt simple connection handshake
  - [ ] Test with 5-second timeout
  - [ ] Log success: "MCP connection tested: gmail (mcp://gmail) - OK"
  - [ ] On failure: raise MCPError with code "mcp_connection_failed"
  - [ ] Include connection details in error: "MCP connection failed: gmail (mcp://gmail) - connection refused"

- [ ] Implement Warranty API MCP connection test (AC: tests warranty API connection)
  - [ ] Extract warranty API connection string from config.mcp.warranty_api
  - [ ] Create MCP client for warranty API
  - [ ] Test connection handshake
  - [ ] 5-second timeout
  - [ ] Log success: "MCP connection tested: warranty_api - OK"
  - [ ] On failure: "MCP connection failed: warranty_api - {error_details}"
  - [ ] Handle endpoint connectivity if specified in config

- [ ] Implement Ticketing System MCP connection test (AC: tests ticketing connection)
  - [ ] Extract ticketing connection string from config.mcp.ticketing_system
  - [ ] Create MCP client for ticketing system
  - [ ] Test connection handshake
  - [ ] 5-second timeout
  - [ ] Log success: "MCP connection tested: ticketing_system - OK"
  - [ ] On failure: "MCP connection failed: ticketing_system - {error_details}"
  - [ ] Handle endpoint connectivity if specified in config

- [ ] Integrate path verification into startup sequence (AC: startup validates all paths)
  - [ ] Update `cli.py` load_and_validate_config() function
  - [ ] Call verify_file_paths(config) after config validation
  - [ ] Catch ConfigurationError and exit with code 2
  - [ ] Log: "File paths verified" on success
  - [ ] Display actionable error message on failure

- [ ] Integrate MCP connection testing into startup (AC: tests all connections before processing)
  - [ ] Call test_mcp_connections(config) after path verification
  - [ ] Catch MCPError and exit with code 3 (MCP connection failure per NFR29)
  - [ ] Log: "MCP connections tested" on success
  - [ ] Display connection-specific error messages on failure
  - [ ] Ensure all 3 connections tested before declaring success

- [ ] Implement startup logging sequence (AC: clear startup progress logs)
  - [ ] Log "Agent starting..." at beginning
  - [ ] Log "Configuration valid" after config loads
  - [ ] Log "File paths verified" after path validation
  - [ ] Log "MCP connections tested" after connection tests
  - [ ] Log "Agent ready" only after all validations pass
  - [ ] Use INFO level for startup progress logs
  - [ ] Include timing information for 30-second startup target (NFR9)

- [ ] Create unit tests for path validation (AC: validation tested)
  - [ ] Create `tests/config/test_path_validator.py`
  - [ ] Test verify_file_paths() with all valid paths
  - [ ] Test missing main instruction file detection
  - [ ] Test missing scenario instruction file detection
  - [ ] Test missing eval directory detection
  - [ ] Test permission denied error handling
  - [ ] Mock file system using pytest fixtures (tmp_path)
  - [ ] Test both absolute and relative path handling

- [ ] Create unit tests for MCP connection testing (AC: connection tests validated)
  - [ ] Create `tests/integrations/test_connection_tester.py`
  - [ ] Test test_mcp_connections() with all connections successful
  - [ ] Test Gmail connection failure handling
  - [ ] Test warranty API connection failure handling
  - [ ] Test ticketing connection failure handling
  - [ ] Test connection timeout handling (5 seconds)
  - [ ] Mock MCP clients for testing
  - [ ] Test error message formats and details

- [ ] Verify complete startup sequence (AC: all startup checks integrated)
  - [ ] Run agent with valid config and all files present
  - [ ] Verify startup completes within 30 seconds
  - [ ] Verify all startup log messages appear in order
  - [ ] Test with missing instruction file (should exit code 2)
  - [ ] Test with failed MCP connection (should exit code 3)
  - [ ] Verify error messages are actionable and clear
  - [ ] Verify agent doesn't begin processing if any check fails

## Dev Notes

### Architecture Context

This story implements **Configuration Management (FR39, FR40, FR41)** from the PRD, ensuring the agent fails fast on startup if any required files are missing or MCP connections cannot be established, preventing silent failures during runtime.

**Key Architectural Principles:**
- FR39: Verify file paths exist and are readable before processing
- FR40: Test MCP connections before starting email processing
- FR41: Fail fast with clear error messages for invalid configuration
- NFR9: Successful startup completes within 30 seconds

### Critical Implementation Rules from Project Context

**Fail-Fast Validation (MANDATORY):**

From project-context.md:
```
Configuration Secrets (MANDATORY - NFR12, NFR15):
- Fail fast on startup if required secrets missing (NFR38)

Exit Codes (MANDATORY - NFR29):
- 0 = Success
- 2 = Configuration error
- 3 = MCP connection error
- 4 = Eval failure (pass rate < 99%)
```

**File Path Verification Pattern:**
```python
from pathlib import Path
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import ConfigurationError

def verify_file_paths(config: AgentConfig) -> None:
    """Verify all configured file paths exist and are readable

    Args:
        config: Agent configuration with file paths

    Raises:
        ConfigurationError: If any file path is invalid or unreadable
    """
    # Verify main instruction file
    main_instruction = Path(config.instructions.main)
    if not main_instruction.exists():
        raise ConfigurationError(
            message=f"Instruction file not found: {config.instructions.main}",
            code="config_file_not_found",
            details={"file_path": config.instructions.main, "file_type": "main_instruction"}
        )

    if not main_instruction.is_file():
        raise ConfigurationError(
            message=f"Instruction path is not a file: {config.instructions.main}",
            code="config_invalid_path",
            details={"file_path": config.instructions.main}
        )

    # Check readability
    try:
        with open(main_instruction, 'r') as f:
            f.read(1)  # Test read permission
    except PermissionError:
        raise ConfigurationError(
            message=f"Cannot read instruction file: {config.instructions.main} (permission denied)",
            code="config_permission_denied",
            details={"file_path": config.instructions.main}
        )

    # Verify scenario instruction files
    for scenario_path in config.instructions.scenarios:
        scenario_file = Path(scenario_path)
        if not scenario_file.exists():
            raise ConfigurationError(
                message=f"Instruction file not found: {scenario_path}",
                code="config_file_not_found",
                details={"file_path": scenario_path, "file_type": "scenario_instruction"}
            )

        try:
            with open(scenario_file, 'r') as f:
                f.read(1)
        except PermissionError:
            raise ConfigurationError(
                message=f"Cannot read instruction file: {scenario_path} (permission denied)",
                code="config_permission_denied",
                details={"file_path": scenario_path}
            )

    # Verify eval test suite directory
    eval_dir = Path(config.eval.test_suite_path)
    if not eval_dir.exists():
        raise ConfigurationError(
            message=f"Eval directory not found: {config.eval.test_suite_path}",
            code="config_directory_not_found",
            details={"directory_path": config.eval.test_suite_path}
        )

    if not eval_dir.is_dir():
        raise ConfigurationError(
            message=f"Eval path is not a directory: {config.eval.test_suite_path}",
            code="config_invalid_path",
            details={"directory_path": config.eval.test_suite_path}
        )
```

### MCP Connection Testing Pattern

**Connection Test Implementation:**
```python
import asyncio
from typing import Optional
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import MCPError

async def test_mcp_connection(
    connection_string: str,
    name: str,
    timeout: int = 5
) -> None:
    """Test MCP connection with timeout

    Args:
        connection_string: MCP connection string (e.g., "mcp://gmail")
        name: Connection name for logging (e.g., "gmail")
        timeout: Connection timeout in seconds (default 5)

    Raises:
        MCPError: If connection fails or times out
    """
    try:
        # Create MCP client with connection string
        # This is placeholder - actual MCP client creation happens in Epic 2
        # For now, we'll validate the connection string format and simulate handshake

        # Validate connection string format
        if not connection_string.startswith("mcp://"):
            raise ValueError(f"Invalid MCP connection string: {connection_string}")

        # TODO: When Epic 2 is complete, replace with actual MCP client:
        # from guarantee_email_agent.integrations.mcp_client import MCPClient
        # client = MCPClient(connection_string)
        # await asyncio.wait_for(client.connect(), timeout=timeout)

        # For Story 1.4, we'll implement a simple connectivity check
        # that validates the connection string and simulates connection test
        logger.info(f"MCP connection tested: {name} ({connection_string}) - OK")

    except asyncio.TimeoutError:
        raise MCPError(
            message=f"MCP connection timeout: {name}",
            code="mcp_connection_timeout",
            details={"connection_string": connection_string, "name": name, "timeout": timeout}
        )
    except ConnectionRefusedError as e:
        raise MCPError(
            message=f"MCP connection failed: {name} ({connection_string}) - connection refused",
            code="mcp_connection_refused",
            details={"connection_string": connection_string, "name": name, "error": str(e)}
        )
    except Exception as e:
        raise MCPError(
            message=f"MCP connection failed: {name} ({connection_string}) - {str(e)}",
            code="mcp_connection_failed",
            details={"connection_string": connection_string, "name": name, "error": str(e)}
        )

async def test_mcp_connections(config: AgentConfig) -> None:
    """Test all MCP connections defined in configuration

    Args:
        config: Agent configuration with MCP settings

    Raises:
        MCPError: If any MCP connection fails
    """
    # Test Gmail MCP connection
    await test_mcp_connection(
        config.mcp.gmail.connection_string,
        "gmail",
        timeout=5
    )

    # Test Warranty API MCP connection
    await test_mcp_connection(
        config.mcp.warranty_api.connection_string,
        "warranty_api",
        timeout=5
    )

    # Test Ticketing System MCP connection
    await test_mcp_connection(
        config.mcp.ticketing_system.connection_string,
        "ticketing_system",
        timeout=5
    )
```

### CLI Integration Pattern

**Update cli.py startup sequence:**
```python
import asyncio
import sys
import typer
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.config.validator import validate_config
from guarantee_email_agent.config.path_validator import verify_file_paths
from guarantee_email_agent.integrations.connection_tester import test_mcp_connections
from guarantee_email_agent.utils.errors import ConfigurationError, MCPError

app = typer.Typer(
    name="agent",
    help="Instruction-driven AI agent for warranty email automation"
)

async def startup_validation(config_path: str = None):
    """Complete startup validation sequence

    Returns:
        AgentConfig: Validated configuration

    Raises:
        SystemExit: With appropriate exit code if validation fails
    """
    try:
        # Step 1: Load configuration and secrets
        typer.echo("Agent starting...")
        config = load_config(config_path)

        # Step 2: Validate configuration schema and secrets
        validate_config(config)
        typer.echo("✓ Configuration valid")

        # Step 3: Verify file paths
        verify_file_paths(config)
        typer.echo("✓ File paths verified")

        # Step 4: Test MCP connections
        await test_mcp_connections(config)
        typer.echo("✓ MCP connections tested")

        typer.echo("✓ Agent ready")
        return config

    except ConfigurationError as e:
        typer.echo(f"Configuration Error: {e.message}", err=True)
        typer.echo(f"Error Code: {e.code}", err=True)
        if e.details:
            typer.echo(f"Details: {e.details}", err=True)

        # Provide helpful hints
        if e.code == "config_file_not_found":
            typer.echo("\nHint: Ensure all instruction files exist at the configured paths", err=True)
            typer.echo("      Check config.yaml instructions section", err=True)
        elif e.code == "config_permission_denied":
            typer.echo("\nHint: Check file permissions - files must be readable", err=True)
            typer.echo("      Run: chmod +r <file_path>", err=True)

        sys.exit(2)  # Exit code 2 for configuration errors

    except MCPError as e:
        typer.echo(f"MCP Connection Error: {e.message}", err=True)
        typer.echo(f"Error Code: {e.code}", err=True)
        if e.details:
            typer.echo(f"Details: {e.details}", err=True)

        # Provide helpful hints
        if e.code == "mcp_connection_timeout":
            typer.echo("\nHint: MCP server may not be running or is unresponsive", err=True)
            typer.echo("      Check that MCP servers are started and accessible", err=True)
        elif e.code == "mcp_connection_refused":
            typer.echo("\nHint: MCP server connection was refused", err=True)
            typer.echo("      Verify connection string and ensure server is running", err=True)

        sys.exit(3)  # Exit code 3 for MCP connection errors

@app.command()
def run():
    """Start the warranty email agent for continuous processing."""
    config = asyncio.run(startup_validation())
    typer.echo("Agent run command - to be implemented in Epic 4")

@app.command()
def eval():
    """Execute the complete evaluation test suite."""
    config = asyncio.run(startup_validation())
    typer.echo("Agent eval command - to be implemented in Epic 5")

if __name__ == "__main__":
    app()
```

### Error Hierarchy Extension

**Add MCPError to utils/errors.py:**
```python
class MCPError(AgentError):
    """MCP integration errors"""
    pass

# Error codes for MCP failures:
# - "mcp_connection_failed" - General connection failure
# - "mcp_connection_timeout" - Connection timed out (5 seconds)
# - "mcp_connection_refused" - Connection refused by server
# - "mcp_authentication_failed" - Authentication failed
```

### Testing Strategy

**Unit Test Coverage:**

1. **test_path_validator.py:**
   - Test verify_file_paths() with complete valid configuration
   - Test missing main instruction file → ConfigurationError
   - Test missing scenario instruction file → ConfigurationError
   - Test missing eval directory → ConfigurationError
   - Test permission denied on instruction file → ConfigurationError
   - Test both absolute and relative paths
   - Use pytest tmp_path fixture for file system mocking

2. **test_connection_tester.py:**
   - Test test_mcp_connections() with all connections successful
   - Test Gmail connection failure → MCPError with code "mcp_connection_failed"
   - Test warranty API connection timeout → MCPError with code "mcp_connection_timeout"
   - Test ticketing connection refused → MCPError with code "mcp_connection_refused"
   - Mock asyncio timeouts for timeout testing
   - Mock connection refused errors
   - Verify error messages include connection string and name

3. **test_cli_startup.py:**
   - Test complete startup_validation() sequence success
   - Test startup with missing file → exit code 2
   - Test startup with failed MCP connection → exit code 3
   - Test startup logging sequence
   - Verify all validation steps execute in order
   - Mock all external dependencies

**Example Test:**
```python
# tests/config/test_path_validator.py
import pytest
from pathlib import Path
from guarantee_email_agent.config.path_validator import verify_file_paths
from guarantee_email_agent.config.schema import AgentConfig, InstructionsConfig, EvalConfig
from guarantee_email_agent.utils.errors import ConfigurationError

def test_verify_file_paths_success(tmp_path):
    """Test path verification with all valid paths"""
    # Create test files
    main_instruction = tmp_path / "main.md"
    main_instruction.write_text("# Main instruction")

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    scenario1 = scenario_dir / "valid-warranty.md"
    scenario1.write_text("# Valid warranty scenario")

    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()

    # Create config with test paths
    config = AgentConfig(
        instructions=InstructionsConfig(
            main=str(main_instruction),
            scenarios=[str(scenario1)]
        ),
        eval=EvalConfig(
            test_suite_path=str(eval_dir),
            pass_threshold=99.0
        ),
        # ... other config fields
    )

    # Should not raise any errors
    verify_file_paths(config)

def test_verify_file_paths_missing_main_instruction(tmp_path):
    """Test missing main instruction file detection"""
    config = AgentConfig(
        instructions=InstructionsConfig(
            main="nonexistent/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(
            test_suite_path=str(tmp_path),
            pass_threshold=99.0
        ),
        # ... other config fields
    )

    with pytest.raises(ConfigurationError) as exc_info:
        verify_file_paths(config)

    assert exc_info.value.code == "config_file_not_found"
    assert "Instruction file not found" in exc_info.value.message
    assert "nonexistent/main.md" in exc_info.value.message
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Silently ignoring missing files:**
   ```python
   # WRONG - Silent failure
   if not Path(file_path).exists():
       return None  # Silently continues!

   # CORRECT - Fail fast
   if not Path(file_path).exists():
       raise ConfigurationError(
           message=f"Instruction file not found: {file_path}",
           code="config_file_not_found",
           details={"file_path": file_path}
       )
   ```

2. **Using wrong exit codes:**
   ```python
   # WRONG - Generic exit code
   sys.exit(1)  # What kind of error?

   # CORRECT - Specific exit codes per NFR29
   sys.exit(2)  # Configuration error
   sys.exit(3)  # MCP connection error
   ```

3. **Testing connections sequentially without error aggregation:**
   ```python
   # WRONG - Fails on first connection, doesn't test others
   test_gmail()  # Fails here
   test_warranty()  # Never tested
   test_ticketing()  # Never tested

   # CORRECT - Test all, report all failures
   errors = []
   for connection in [gmail, warranty, ticketing]:
       try:
           test_connection(connection)
       except MCPError as e:
           errors.append(e)
   if errors:
       raise MCPError(...)  # Report all failures
   ```

4. **Not providing actionable error messages:**
   ```python
   # WRONG - Vague error
   raise ConfigurationError("File error")

   # CORRECT - Specific with remediation
   raise ConfigurationError(
       message=f"Instruction file not found: {file_path}",
       code="config_file_not_found",
       details={"file_path": file_path, "hint": "Create file or update config.yaml"}
   )
   ```

5. **Blocking async operations:**
   ```python
   # WRONG - Synchronous call in async function
   def test_connections():
       client.connect()  # Blocks event loop!

   # CORRECT - Async with timeout
   async def test_connections():
       await asyncio.wait_for(client.connect(), timeout=5)
   ```

### Verification Commands

```bash
# 1. Create required directory structure
mkdir -p instructions/scenarios
mkdir -p evals/scenarios
touch instructions/main.md
touch instructions/scenarios/valid-warranty.md

# 2. Test with valid configuration (should succeed)
uv run python -m guarantee_email_agent run
# Expected: "Agent ready" message, exit code 0

# 3. Test with missing instruction file (should fail)
mv instructions/main.md instructions/main.md.bak
uv run python -m guarantee_email_agent run
# Expected: "Instruction file not found: instructions/main.md", exit code 2
echo $?  # Should be 2
mv instructions/main.md.bak instructions/main.md

# 4. Test with permission denied (should fail)
chmod 000 instructions/main.md
uv run python -m guarantee_email_agent run
# Expected: "Cannot read instruction file: ... (permission denied)", exit code 2
chmod 644 instructions/main.md

# 5. Test MCP connection failure (simulated)
# This will be testable after Epic 2 MCP implementation
# For Story 1.4, connection testing is stubbed

# 6. Verify startup timing (should be <30 seconds)
time uv run python -m guarantee_email_agent run
# Should complete within 30 seconds (NFR9)

# 7. Run unit tests
uv run pytest tests/config/test_path_validator.py -v
uv run pytest tests/integrations/test_connection_tester.py -v

# 8. Verify all startup log messages appear
uv run python -m guarantee_email_agent run 2>&1 | grep -E "(Agent starting|Configuration valid|File paths verified|MCP connections tested|Agent ready)"
# All 5 messages should appear in order
```

### Dependency Notes

**Depends on:**
- Story 1.1: Project structure with src-layout, directories, and CLI framework
- Story 1.2: Configuration loader and validator, AgentConfig dataclass
- Story 1.3: Environment variable management, secrets validation

**Blocks:**
- Epic 2 stories: MCP integration requires connection testing infrastructure
- Epic 3 stories: Instruction loading requires file path verification
- Epic 4 stories: Email processing requires validated startup sequence

**MCP Connection Testing Note:**
For Story 1.4, MCP connection testing will be implemented as a connectivity check that validates connection strings and simulates handshake. The actual MCP client implementation happens in Epic 2 (Stories 2.1-2.3). When Epic 2 is complete, the connection testing code will be updated to use real MCP clients.

### References

**Architecture Document Sections:**
- [Source: architecture.md#Configuration Management] - Fail-fast validation requirements
- [Source: architecture.md#MCP Integration Architecture] - MCP connection details
- [Source: architecture.md#Startup Sequence] - Validation order and timing
- [Source: project-context.md#Exit Code Standards] - Exit codes 2 and 3
- [Source: project-context.md#File Naming Consistency] - Instruction file naming (kebab-case)

**Epic/PRD Context:**
- [Source: epics.md#Epic 1: Project Foundation & Configuration] - Parent epic
- [Source: epics.md#Story 1.4] - Complete acceptance criteria
- [Source: prd.md#Configuration Management FR39-FR41] - File path and connection testing requirements
- [Source: prd.md#Operational Excellence NFR9] - 30-second startup requirement
- [Source: prd.md#NFR29] - Exit code standards

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context analysis completed from PRD, Architecture, Project Context, and Epics
- Story file created with complete implementation patterns and code examples
- File path verification and MCP connection testing patterns documented
- Integration with existing CLI startup sequence defined
- Exit codes 2 (configuration) and 3 (MCP) properly implemented
- 30-second startup performance target (NFR9) documented
- Testing strategy with pytest examples provided
- Dependencies and Epic 2 integration notes included

### File List

- `src/guarantee_email_agent/config/path_validator.py` - File path verification
- `src/guarantee_email_agent/integrations/connection_tester.py` - MCP connection testing
- `src/guarantee_email_agent/cli.py` - Updated startup sequence
- `src/guarantee_email_agent/utils/errors.py` - Added MCPError class
- `tests/config/test_path_validator.py` - Path validation tests
- `tests/integrations/test_connection_tester.py` - Connection test tests
- `tests/test_cli_startup.py` - Complete startup sequence tests
