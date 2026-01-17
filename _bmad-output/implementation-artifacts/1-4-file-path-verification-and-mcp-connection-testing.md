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

- [ ] Create file path verification module (AC: verify instruction files exist)
  - [ ] Create `src/guarantee_email_agent/config/path_verifier.py`
  - [ ] Implement `verify_file_exists(file_path: str) -> None` function
  - [ ] Check file exists using Path.exists()
  - [ ] Check file is readable using Path.is_file() and permissions
  - [ ] Raise ConfigurationError with specific file path if missing or unreadable

- [ ] Implement instruction path validation (AC: missing instruction files detected)
  - [ ] Create `verify_instruction_paths(config: AgentConfig) -> None` function
  - [ ] Verify main instruction file exists and is readable
  - [ ] Verify each scenario instruction file exists and is readable
  - [ ] Raise ConfigurationError with clear message for each missing file
  - [ ] Include full file path in error details

- [ ] Implement eval path validation (AC: eval directory verified)
  - [ ] Create `verify_eval_paths(config: AgentConfig) -> None` function
  - [ ] Verify eval test_suite_path directory exists
  - [ ] Create directory if missing (with warning log)
  - [ ] Verify directory is readable
  - [ ] Raise ConfigurationError if directory cannot be created or accessed

- [ ] Create MCP connection testing module (AC: MCP connections tested)
  - [ ] Create `src/guarantee_email_agent/config/mcp_tester.py`
  - [ ] Create MCPConnectionTester class
  - [ ] Implement `test_connection(connection_string: str, timeout: int = 5) -> bool` method
  - [ ] Note: Actual MCP SDK integration happens in Epic 2
  - [ ] For now, create stub that validates connection string format
  - [ ] Add TODO comment for Epic 2 implementation

- [ ] Implement MCP connection string validation (AC: connection format validated)
  - [ ] Create `validate_mcp_connection_string(connection_string: str) -> None` function
  - [ ] Validate format matches "mcp://<service-name>"
  - [ ] Raise ConfigurationError if format invalid
  - [ ] Provide example of correct format in error message

- [ ] Create startup validator orchestrator (AC: all validation in one place)
  - [ ] Create `src/guarantee_email_agent/config/startup_validator.py`
  - [ ] Implement `validate_startup(config: AgentConfig) -> None` function
  - [ ] Call verify_instruction_paths(config)
  - [ ] Call verify_eval_paths(config)
  - [ ] Call validate_mcp_connections(config)
  - [ ] Log progress at each stage
  - [ ] Aggregate all validation errors for comprehensive error reporting

- [ ] Add MCP connection error handling (AC: exit code 3 for MCP failures)
  - [ ] Create MCPConnectionError in utils/errors.py
  - [ ] Subclass of AgentError with code "mcp_connection_failed"
  - [ ] Include connection details in error (service name, connection string)
  - [ ] CLI catches MCPConnectionError and exits with code 3

- [ ] Integrate startup validation into CLI (AC: startup validates before processing)
  - [ ] Update cli.py to call validate_startup() after config loading
  - [ ] Log "Configuration valid" after config loads
  - [ ] Log "File paths verified" after path verification
  - [ ] Log "MCP connections tested" after connection validation
  - [ ] Log "Agent ready" only after all validation passes
  - [ ] Catch ConfigurationError (exit code 2) and MCPConnectionError (exit code 3)

- [ ] Add startup timing validation (AC: startup completes within 30 seconds)
  - [ ] Add startup timing measurement
  - [ ] Log total startup time
  - [ ] Warn if startup exceeds 30 seconds (NFR9)
  - [ ] Add performance metrics for each validation stage

- [ ] Create unit tests for validation (AC: validation tested)
  - [ ] Create tests/config/test_path_verifier.py
  - [ ] Test file exists validation
  - [ ] Test file readable validation
  - [ ] Test missing file error
  - [ ] Create tests/config/test_mcp_tester.py
  - [ ] Test connection string validation
  - [ ] Create tests/config/test_startup_validator.py
  - [ ] Test complete startup validation flow

- [ ] Verify startup validation integration (AC: startup logs clear progress)
  - [ ] Run agent with valid config and all files present
  - [ ] Verify logs show validation progress
  - [ ] Remove instruction file and verify error
  - [ ] Verify exit code 2 for missing files
  - [ ] Test invalid MCP connection string
  - [ ] Verify exit code 3 for MCP failures
  - [ ] Measure startup time (should be < 30 seconds)

## Dev Notes

### Architecture Context

This story implements **Configuration Management (FR39-FR41)** and completes Epic 1 by ensuring fail-fast validation catches all configuration issues before the agent begins processing emails.

**Key Validation Principles:**
- FR39: Verify file paths exist and are readable
- FR40: Test MCP connections before processing
- FR41: Fail fast with clear error messages
- NFR9: Startup completes within 30 seconds

**Validation Sequence:**
1. Load config.yaml (Story 1.2)
2. Load secrets from environment (Story 1.3)
3. Validate configuration schema
4. **Verify instruction file paths** (This story)
5. **Verify eval directory paths** (This story)
6. **Validate MCP connection strings** (This story)
7. Test MCP connections (stub now, real in Epic 2)
8. Log "Agent ready" and begin processing

### Critical Implementation Rules from Project Context

**Exit Code Standards (NFR29 - MANDATORY):**
- Exit code 2: Configuration error (missing files, invalid paths)
- Exit code 3: MCP connection failure
- Different exit codes help automation scripts distinguish error types

**Fail-Fast Philosophy:**
From project-context.md:
```
Configuration Validation (NFR38, NFR41):
- Validate configuration schema on startup
- Verify file paths exist and are readable before processing
- Test MCP connections before starting email processing
- Fail fast with clear error messages for invalid configuration
```

**Startup Performance (NFR9):**
- Startup (configuration validation + MCP connection testing) completes within 30 seconds
- Log timing for each validation stage
- Warn if approaching limit

### File Path Verification Implementation

**path_verifier.py structure:**

```python
from pathlib import Path
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import ConfigurationError

def verify_file_exists(file_path: str, description: str = "File") -> None:
    """Verify a file exists and is readable

    Args:
        file_path: Path to file to verify
        description: Human-readable description for error messages

    Raises:
        ConfigurationError: If file doesn't exist or isn't readable
    """
    path = Path(file_path)

    if not path.exists():
        raise ConfigurationError(
            message=f"{description} not found: {file_path}",
            code="config_file_not_found",
            details={"file_path": file_path, "description": description}
        )

    if not path.is_file():
        raise ConfigurationError(
            message=f"{description} is not a file: {file_path}",
            code="config_invalid_path",
            details={"file_path": file_path, "description": description}
        )

    # Check if readable
    try:
        with open(path, 'r') as f:
            f.read(1)  # Try reading first byte
    except PermissionError:
        raise ConfigurationError(
            message=f"Cannot read {description}: {file_path} (permission denied)",
            code="config_file_unreadable",
            details={"file_path": file_path, "description": description}
        )
    except Exception as e:
        raise ConfigurationError(
            message=f"Cannot access {description}: {file_path} ({str(e)})",
            code="config_file_error",
            details={"file_path": file_path, "description": description, "error": str(e)}
        )

def verify_instruction_paths(config: AgentConfig) -> None:
    """Verify all instruction file paths exist and are readable

    Args:
        config: Agent configuration with instruction paths

    Raises:
        ConfigurationError: If any instruction file is missing or unreadable
    """
    # Verify main instruction file
    verify_file_exists(
        config.instructions.main,
        description="Main instruction file"
    )

    # Verify each scenario instruction file
    for scenario_path in config.instructions.scenarios:
        verify_file_exists(
            scenario_path,
            description="Scenario instruction file"
        )

def verify_eval_paths(config: AgentConfig) -> None:
    """Verify eval test suite directory exists

    Args:
        config: Agent configuration with eval paths

    Raises:
        ConfigurationError: If eval directory doesn't exist or isn't accessible
    """
    eval_dir = Path(config.eval.test_suite_path)

    if not eval_dir.exists():
        # Try to create directory
        try:
            eval_dir.mkdir(parents=True, exist_ok=True)
            # Log warning that directory was created
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Created eval directory: {config.eval.test_suite_path}")
        except Exception as e:
            raise ConfigurationError(
                message=f"Eval directory does not exist and cannot be created: {config.eval.test_suite_path}",
                code="config_directory_error",
                details={"directory": config.eval.test_suite_path, "error": str(e)}
            )

    if not eval_dir.is_dir():
        raise ConfigurationError(
            message=f"Eval path is not a directory: {config.eval.test_suite_path}",
            code="config_invalid_path",
            details={"path": config.eval.test_suite_path}
        )
```

### MCP Connection Testing Implementation

**mcp_tester.py structure (stub for now, real implementation in Epic 2):**

```python
import re
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import MCPConnectionError

def validate_mcp_connection_string(connection_string: str, service_name: str) -> None:
    """Validate MCP connection string format

    Args:
        connection_string: MCP connection string (e.g., "mcp://gmail")
        service_name: Service name for error messages

    Raises:
        MCPConnectionError: If connection string format is invalid
    """
    # Validate format: mcp://<service-name>
    pattern = r'^mcp://[a-z0-9\-_]+$'
    if not re.match(pattern, connection_string, re.IGNORECASE):
        raise MCPConnectionError(
            message=f"Invalid MCP connection string for {service_name}: {connection_string}",
            code="mcp_invalid_connection_string",
            details={
                "service": service_name,
                "connection_string": connection_string,
                "expected_format": "mcp://<service-name>"
            }
        )

def validate_mcp_connections(config: AgentConfig) -> None:
    """Validate MCP connection strings (stub for Epic 2)

    In Epic 2, this will actually test connections to MCP servers.
    For now, we only validate connection string format.

    Args:
        config: Agent configuration with MCP connection settings

    Raises:
        MCPConnectionError: If any connection string is invalid
    """
    # Validate Gmail connection string
    validate_mcp_connection_string(
        config.mcp.gmail.connection_string,
        service_name="gmail"
    )

    # Validate Warranty API connection string
    validate_mcp_connection_string(
        config.mcp.warranty_api.connection_string,
        service_name="warranty_api"
    )

    # Validate Ticketing System connection string
    validate_mcp_connection_string(
        config.mcp.ticketing_system.connection_string,
        service_name="ticketing_system"
    )

    # TODO (Epic 2): Implement actual MCP connection testing
    # - Import MCP Python SDK
    # - Attempt to connect to each MCP server
    # - Use 5-second timeout for each connection test
    # - Raise MCPConnectionError if connection fails
    # For now, connection string validation is sufficient
```

### Startup Validator Orchestrator

**startup_validator.py structure:**

```python
import time
import logging
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.config.path_verifier import verify_instruction_paths, verify_eval_paths
from guarantee_email_agent.config.mcp_tester import validate_mcp_connections

logger = logging.getLogger(__name__)

def validate_startup(config: AgentConfig) -> None:
    """Complete startup validation orchestrator

    Validates all configuration, file paths, and MCP connections.
    Logs progress and timing for each stage.

    Args:
        config: Complete agent configuration

    Raises:
        ConfigurationError: If file paths are invalid
        MCPConnectionError: If MCP connections fail
    """
    start_time = time.time()

    # Stage 1: Verify instruction file paths
    logger.info("Verifying instruction file paths...")
    stage_start = time.time()
    verify_instruction_paths(config)
    logger.info(f"Instruction paths verified ({time.time() - stage_start:.2f}s)")

    # Stage 2: Verify eval directory
    logger.info("Verifying eval directory...")
    stage_start = time.time()
    verify_eval_paths(config)
    logger.info(f"Eval paths verified ({time.time() - stage_start:.2f}s)")

    # Stage 3: Validate MCP connection strings (stub for Epic 2)
    logger.info("Validating MCP connection strings...")
    stage_start = time.time()
    validate_mcp_connections(config)
    logger.info(f"MCP connections validated ({time.time() - stage_start:.2f}s)")

    # Calculate total startup time
    total_time = time.time() - start_time
    logger.info(f"Startup validation complete ({total_time:.2f}s)")

    # Warn if approaching 30-second limit (NFR9)
    if total_time > 25:
        logger.warning(f"Startup validation took {total_time:.2f}s (approaching 30s limit)")
    elif total_time > 30:
        logger.error(f"Startup validation exceeded 30s limit: {total_time:.2f}s")
```

### Error Handling: MCPConnectionError

**Add to utils/errors.py:**

```python
class MCPConnectionError(AgentError):
    """MCP connection-related errors"""
    pass

# Usage:
# raise MCPConnectionError(
#     message="MCP connection failed: gmail (mcp://gmail) - connection refused",
#     code="mcp_connection_failed",
#     details={"service": "gmail", "connection_string": "mcp://gmail"}
# )
```

### CLI Integration with Exit Codes

**Update cli.py:**

```python
import typer
import sys
import logging
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.config.validator import validate_config
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
    """Load and validate configuration, exit with appropriate code on error"""
    try:
        # Load configuration and secrets
        logger.info("Loading configuration...")
        config = load_config(config_path)
        logger.info("Configuration loaded")

        # Validate configuration schema
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
```

### Testing Strategy

**Unit Tests (tests/config/test_path_verifier.py):**

```python
import pytest
from pathlib import Path
from guarantee_email_agent.config.path_verifier import verify_file_exists, verify_instruction_paths
from guarantee_email_agent.config.schema import AgentConfig, InstructionsConfig, MCPConfig, EvalConfig, LoggingConfig, SecretsConfig
from guarantee_email_agent.utils.errors import ConfigurationError

def test_verify_file_exists_with_valid_file(tmp_path):
    """Test verifying a file that exists"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    # Should not raise
    verify_file_exists(str(test_file), "Test file")

def test_verify_file_exists_missing_file(tmp_path):
    """Test verifying a file that doesn't exist"""
    missing_file = tmp_path / "missing.txt"

    with pytest.raises(ConfigurationError) as exc_info:
        verify_file_exists(str(missing_file), "Test file")

    assert exc_info.value.code == "config_file_not_found"
    assert "missing.txt" in exc_info.value.message

def test_verify_file_exists_unreadable_file(tmp_path):
    """Test verifying a file that isn't readable"""
    test_file = tmp_path / "unreadable.txt"
    test_file.write_text("content")
    test_file.chmod(0o000)  # Remove all permissions

    with pytest.raises(ConfigurationError) as exc_info:
        verify_file_exists(str(test_file), "Test file")

    assert exc_info.value.code in ["config_file_unreadable", "config_file_error"]

    # Restore permissions for cleanup
    test_file.chmod(0o644)

def test_verify_instruction_paths_with_valid_files(tmp_path):
    """Test verifying instruction paths when all files exist"""
    main_file = tmp_path / "main.md"
    main_file.write_text("# Main")

    scenario_file = tmp_path / "scenario.md"
    scenario_file.write_text("# Scenario")

    config = AgentConfig(
        mcp=MCPConfig(...),  # Mock MCP config
        instructions=InstructionsConfig(
            main=str(main_file),
            scenarios=[str(scenario_file)]
        ),
        eval=EvalConfig(...),
        logging=LoggingConfig(...),
        secrets=SecretsConfig(...)
    )

    # Should not raise
    verify_instruction_paths(config)
```

**Unit Tests (tests/config/test_mcp_tester.py):**

```python
import pytest
from guarantee_email_agent.config.mcp_tester import validate_mcp_connection_string
from guarantee_email_agent.utils.errors import MCPConnectionError

def test_validate_valid_connection_string():
    """Test validating a valid MCP connection string"""
    # Should not raise
    validate_mcp_connection_string("mcp://gmail", "gmail")
    validate_mcp_connection_string("mcp://warranty-api", "warranty")

def test_validate_invalid_connection_string_format():
    """Test validating invalid connection string format"""
    with pytest.raises(MCPConnectionError) as exc_info:
        validate_mcp_connection_string("http://gmail", "gmail")

    assert exc_info.value.code == "mcp_invalid_connection_string"
    assert "mcp://" in exc_info.value.details["expected_format"]

def test_validate_empty_connection_string():
    """Test validating empty connection string"""
    with pytest.raises(MCPConnectionError):
        validate_mcp_connection_string("", "gmail")
```

### Startup Validation Flow Diagram

```
Agent Startup Sequence:
┌─────────────────────────────────────┐
│ 1. Load config.yaml (Story 1.2)    │
│    ✓ Parse YAML                     │
│    ✓ Validate schema                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 2. Load secrets (Story 1.3)        │
│    ✓ Read environment variables     │
│    ✓ Validate required secrets      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 3. Verify file paths (THIS STORY)  │
│    ✓ Check instruction files exist  │
│    ✓ Check files are readable       │
│    ✓ Verify eval directory          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 4. Validate MCP connections        │
│    ✓ Check connection string format │
│    ✓ TODO: Test actual connections  │
│       (Epic 2)                       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 5. Log "Agent ready"                │
│    ✓ All validation passed          │
│    ✓ Total time < 30 seconds        │
└─────────────────────────────────────┘
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Skipping file verification:**
   ```python
   # WRONG - Assume files exist
   config = load_config()
   # Start processing without verification

   # CORRECT - Verify before processing
   config = load_config()
   validate_startup(config)  # Fails fast if files missing
   ```

2. **Wrong exit codes:**
   ```python
   # WRONG - Generic exit code
   except ConfigurationError:
       sys.exit(1)

   # CORRECT - Specific exit codes
   except ConfigurationError:
       sys.exit(2)  # Config error
   except MCPConnectionError:
       sys.exit(3)  # MCP error
   ```

3. **Silent failures:**
   ```python
   # WRONG - Silently ignore missing files
   if not Path(file_path).exists():
       return None

   # CORRECT - Fail fast with clear error
   if not Path(file_path).exists():
       raise ConfigurationError(
           message=f"File not found: {file_path}",
           code="config_file_not_found"
       )
   ```

4. **Not logging validation progress:**
   ```python
   # WRONG - No visibility into validation
   verify_paths()
   validate_connections()

   # CORRECT - Log each stage
   logger.info("Verifying file paths...")
   verify_paths()
   logger.info("File paths verified")
   ```

### Verification Commands

```bash
# 1. Create required directory structure
mkdir -p instructions/scenarios
mkdir -p evals/scenarios

# 2. Create placeholder instruction files
echo "# Main instruction" > instructions/main.md
echo "# Valid warranty" > instructions/scenarios/valid-warranty.md
echo "# Invalid warranty" > instructions/scenarios/invalid-warranty.md
echo "# Missing info" > instructions/scenarios/missing-info.md

# 3. Test startup with all files present
uv run python -m guarantee_email_agent run
# Should log: "Configuration valid", "File paths verified", "MCP connections tested", "Agent ready"

# 4. Test missing instruction file error
rm instructions/main.md
uv run python -m guarantee_email_agent run
# Should fail with exit code 2 and "Instruction file not found: instructions/main.md"
echo $?  # Should be 2

# 5. Restore file
echo "# Main instruction" > instructions/main.md

# 6. Test invalid MCP connection string
# Edit config.yaml to have invalid connection string like "http://gmail"
uv run python -m guarantee_email_agent run
# Should fail with exit code 3 and "Invalid MCP connection string"
echo $?  # Should be 3

# 7. Run validation tests
uv run pytest tests/config/test_path_verifier.py -v
uv run pytest tests/config/test_mcp_tester.py -v
uv run pytest tests/config/test_startup_validator.py -v

# 8. Measure startup time
time uv run python -m guarantee_email_agent --help
# Should complete in < 30 seconds (NFR9)
```

### NFR9 Startup Performance

**30-Second Startup Budget:**
- Config file loading: < 0.1s
- Secrets loading: < 0.1s
- Schema validation: < 0.1s
- File path verification: < 0.5s (even with many files)
- MCP connection validation: < 1s (stub, real testing in Epic 2 may take 5s per connection = 15s total)
- Total expected: < 2s for MVP (most time will be MCP connection testing in Epic 2)

**Performance Monitoring:**
- Log timing for each validation stage
- Warn if approaching 30s limit
- Error if exceeding 30s limit

### References

**Architecture Document Sections:**
- [Source: architecture.md#Configuration Management] - Startup validation requirements
- [Source: architecture.md#Implementation Patterns] - Error handling patterns
- [Source: project-context.md#Exit Code Standards] - Exit codes 2 and 3
- [Source: project-context.md#Critical Anti-Patterns] - Silent failures forbidden

**Epic/PRD Context:**
- [Source: epics.md#Epic 1: Project Foundation & Configuration] - Parent epic
- [Source: epics.md#Story 1.4] - Complete acceptance criteria
- [Source: prd.md#Configuration Management FR39-FR41] - File verification requirements
- [Source: prd.md#Non-Functional Requirements NFR9] - 30-second startup requirement

**Dependencies:**
- Story 1.1: Project structure exists
- Story 1.2: Configuration loader and validator
- Story 1.3: Secrets management
- Epic 2 (Future): Actual MCP connection testing will replace stubs

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
