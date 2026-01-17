# Story 1.2: Create Configuration Schema and Validation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want to define and validate a YAML configuration schema for MCP connections and agent settings,
So that configuration errors are caught at startup with clear error messages before any processing begins.

## Acceptance Criteria

**Given** The project structure from Story 1.1 exists
**When** I create a `config.yaml` file with MCP connection settings, instruction paths, and eval configuration
**Then** The config loader in `src/guarantee_email_agent/config/loader.py` can parse the YAML file
**And** Configuration schema includes MCP section with gmail, warranty_api, and ticketing_system connection strings
**And** Configuration schema includes instructions section with main path and scenarios list
**And** Configuration schema includes eval section with test_suite_path and pass_threshold (99.0)
**And** Configuration schema includes logging section with level, output, and file path
**And** The validator in `src/guarantee_email_agent/config/validator.py` checks for required fields
**And** Missing required fields produce clear error messages: "Missing required config field: mcp.gmail.connection_string"
**And** Invalid YAML syntax produces error: "Configuration file is not valid YAML"
**And** The agent startup fails fast (exit code 2) if configuration is invalid
**And** Valid configuration loads successfully and is accessible throughout the application

## Tasks / Subtasks

- [ ] Create config module structure (AC: module files exist)
  - [ ] Create `src/guarantee_email_agent/config/__init__.py` with public API exports
  - [ ] Create `src/guarantee_email_agent/config/loader.py` for YAML loading
  - [ ] Create `src/guarantee_email_agent/config/validator.py` for schema validation
  - [ ] Create `src/guarantee_email_agent/config/schema.py` for schema definitions

- [ ] Define configuration data models (AC: schema classes defined)
  - [ ] Create MCPConfig dataclass for MCP connection settings
  - [ ] Create InstructionsConfig dataclass for instruction file paths
  - [ ] Create EvalConfig dataclass for eval suite settings
  - [ ] Create LoggingConfig dataclass for logging configuration
  - [ ] Create AgentConfig dataclass as top-level config container

- [ ] Implement YAML configuration loader (AC: config loader parses YAML)
  - [ ] Implement `load_config(config_path: str) -> AgentConfig` function
  - [ ] Read YAML file using PyYAML's `safe_load()`
  - [ ] Handle YAML parsing errors with clear error messages
  - [ ] Parse nested configuration sections into dataclasses
  - [ ] Return populated AgentConfig object

- [ ] Implement configuration validator (AC: validator checks required fields)
  - [ ] Create `validate_config(config: AgentConfig) -> None` function
  - [ ] Validate MCP section has all required connection strings
  - [ ] Validate instructions section has main path and scenarios list
  - [ ] Validate eval section has test_suite_path and pass_threshold
  - [ ] Validate logging section has level, output, and file path
  - [ ] Raise ConfigurationError with specific field path for missing fields

- [ ] Create example config.yaml template (AC: configuration schema complete)
  - [ ] Create `config.yaml` in project root with all required sections
  - [ ] Document MCP connection settings for gmail, warranty_api, ticketing
  - [ ] Document instruction file paths (main + scenarios)
  - [ ] Document eval configuration (test_suite_path, pass_threshold: 99.0)
  - [ ] Document logging configuration (level, output, file)
  - [ ] Add comments explaining each section

- [ ] Implement error handling with AgentError (AC: clear error messages)
  - [ ] Create ConfigurationError class in `utils/errors.py`
  - [ ] Use error code pattern: `config_missing_field`, `config_invalid_yaml`
  - [ ] Include field path in error details dict
  - [ ] Format error messages for user clarity

- [ ] Integrate config loading into CLI (AC: startup fails fast on invalid config)
  - [ ] Update `cli.py` to load config at startup
  - [ ] Catch ConfigurationError and exit with code 2
  - [ ] Log configuration errors to stderr
  - [ ] Display actionable error message before exit

- [ ] Create unit tests for config module (AC: validation tested)
  - [ ] Create `tests/config/test_loader.py`
  - [ ] Test valid YAML config loading
  - [ ] Test invalid YAML syntax handling
  - [ ] Test missing required fields detection
  - [ ] Create `tests/config/test_validator.py`
  - [ ] Test all validation rules
  - [ ] Test error message clarity

- [ ] Verify config integration (AC: config accessible throughout app)
  - [ ] Load config in CLI and verify no errors
  - [ ] Test with valid config.yaml
  - [ ] Test with missing required field (should fail with exit code 2)
  - [ ] Test with invalid YAML syntax (should fail with clear message)

## Dev Notes

### Architecture Context

This story implements **Configuration Management (FR34-FR41)** from the PRD, establishing the foundation for all runtime configuration including MCP connections, instruction paths, and eval settings.

**Key Architecture Decisions:**
- YAML configuration file for non-secret settings
- Environment variables for secrets (implemented in Story 1.3)
- Fail-fast validation on startup (NFR38, NFR41)
- Clear error messages with field paths (NFR28)

### Critical Implementation Rules from Project Context

**Configuration YAML Schema (from architecture.md):**

```yaml
# Top-level keys in alphabetical order
eval:
  pass_threshold: 99.0
  test_suite_path: "./evals/scenarios/"

instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"
    - "./instructions/scenarios/invalid-warranty.md"
    - "./instructions/scenarios/missing-info.md"

logging:
  file: "./logs/agent.log"
  level: "INFO"
  output: "stdout"

mcp:
  gmail:
    connection_string: "mcp://gmail"
  ticketing_system:
    connection_string: "mcp://ticketing"
    endpoint: "https://tickets.example.com/api/v1"
  warranty_api:
    connection_string: "mcp://warranty-api"
    endpoint: "https://api.example.com/warranty/check"
```

**YAML/JSON Key Naming (MANDATORY):**
- Configuration Keys: `snake_case` (e.g., `connection_string`, `test_suite_path`)
- Consistent with Python variable naming
- Top-level keys: alphabetical order for consistency

**Error Handling Pattern (AgentError Hierarchy):**
```python
class AgentError(Exception):
    """Base exception for agent errors"""
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class ConfigurationError(AgentError):
    """Configuration-related errors"""
    pass

# Error codes follow pattern: {component}_{error_type}
# Examples:
# - "config_missing_field"
# - "config_invalid_yaml"
# - "config_validation_error"
```

**Exit Codes (NFR29 - MANDATORY):**
- Exit code 2: Configuration error
- Used when config.yaml is invalid or missing required fields
- CLI must catch ConfigurationError and exit with code 2

### Configuration Data Model Design

**Python Dataclass Pattern:**

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MCPConnectionConfig:
    """Configuration for a single MCP connection"""
    connection_string: str
    endpoint: Optional[str] = None

@dataclass
class MCPConfig:
    """MCP integration configuration"""
    gmail: MCPConnectionConfig
    warranty_api: MCPConnectionConfig
    ticketing_system: MCPConnectionConfig

@dataclass
class InstructionsConfig:
    """Instruction file paths configuration"""
    main: str
    scenarios: List[str]

@dataclass
class EvalConfig:
    """Evaluation framework configuration"""
    test_suite_path: str
    pass_threshold: float = 99.0

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    output: str = "stdout"
    file: str = "./logs/agent.log"

@dataclass
class AgentConfig:
    """Top-level agent configuration"""
    mcp: MCPConfig
    instructions: InstructionsConfig
    eval: EvalConfig
    logging: LoggingConfig
```

**Why Dataclasses:**
- Type hints for IDE support and validation
- Immutable configuration object
- Clear structure matching YAML schema
- Easy to test and mock

### Configuration Loader Implementation Pattern

**loader.py structure:**

```python
from pathlib import Path
import yaml
from guarantee_email_agent.config.schema import AgentConfig, MCPConfig, MCPConnectionConfig, InstructionsConfig, EvalConfig, LoggingConfig
from guarantee_email_agent.utils.errors import ConfigurationError

def load_config(config_path: str = "config.yaml") -> AgentConfig:
    """Load and parse YAML configuration file

    Args:
        config_path: Path to config.yaml file

    Returns:
        AgentConfig: Parsed configuration object

    Raises:
        ConfigurationError: If YAML is invalid or cannot be parsed
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise ConfigurationError(
            message=f"Configuration file not found: {config_path}",
            code="config_file_not_found",
            details={"config_path": config_path}
        )

    try:
        with open(config_file, 'r') as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(
            message="Configuration file is not valid YAML",
            code="config_invalid_yaml",
            details={"config_path": config_path, "error": str(e)}
        )

    # Parse nested sections into dataclasses
    try:
        mcp_config = MCPConfig(
            gmail=MCPConnectionConfig(**raw_config['mcp']['gmail']),
            warranty_api=MCPConnectionConfig(**raw_config['mcp']['warranty_api']),
            ticketing_system=MCPConnectionConfig(**raw_config['mcp']['ticketing_system'])
        )

        instructions_config = InstructionsConfig(**raw_config['instructions'])
        eval_config = EvalConfig(**raw_config['eval'])
        logging_config = LoggingConfig(**raw_config['logging'])

        return AgentConfig(
            mcp=mcp_config,
            instructions=instructions_config,
            eval=eval_config,
            logging=logging_config
        )
    except KeyError as e:
        raise ConfigurationError(
            message=f"Missing required config field: {e}",
            code="config_missing_field",
            details={"field": str(e)}
        )
    except TypeError as e:
        raise ConfigurationError(
            message=f"Invalid config field type: {e}",
            code="config_invalid_type",
            details={"error": str(e)}
        )
```

### Configuration Validator Implementation Pattern

**validator.py structure:**

```python
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import ConfigurationError

def validate_config(config: AgentConfig) -> None:
    """Validate configuration has all required fields with valid values

    Args:
        config: Parsed configuration object

    Raises:
        ConfigurationError: If validation fails
    """
    # Validate MCP connections
    if not config.mcp.gmail.connection_string:
        raise ConfigurationError(
            message="Missing required config field: mcp.gmail.connection_string",
            code="config_missing_field",
            details={"field": "mcp.gmail.connection_string"}
        )

    if not config.mcp.warranty_api.connection_string:
        raise ConfigurationError(
            message="Missing required config field: mcp.warranty_api.connection_string",
            code="config_missing_field",
            details={"field": "mcp.warranty_api.connection_string"}
        )

    if not config.mcp.ticketing_system.connection_string:
        raise ConfigurationError(
            message="Missing required config field: mcp.ticketing_system.connection_string",
            code="config_missing_field",
            details={"field": "mcp.ticketing_system.connection_string"}
        )

    # Validate instructions paths
    if not config.instructions.main:
        raise ConfigurationError(
            message="Missing required config field: instructions.main",
            code="config_missing_field",
            details={"field": "instructions.main"}
        )

    if not config.instructions.scenarios or len(config.instructions.scenarios) == 0:
        raise ConfigurationError(
            message="Missing required config field: instructions.scenarios (must have at least one scenario)",
            code="config_missing_field",
            details={"field": "instructions.scenarios"}
        )

    # Validate eval configuration
    if not config.eval.test_suite_path:
        raise ConfigurationError(
            message="Missing required config field: eval.test_suite_path",
            code="config_missing_field",
            details={"field": "eval.test_suite_path"}
        )

    if config.eval.pass_threshold <= 0 or config.eval.pass_threshold > 100:
        raise ConfigurationError(
            message="Invalid eval.pass_threshold: must be between 0 and 100",
            code="config_invalid_value",
            details={"field": "eval.pass_threshold", "value": config.eval.pass_threshold}
        )

    # Validate logging configuration
    valid_log_levels = ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"]
    if config.logging.level.upper() not in valid_log_levels:
        raise ConfigurationError(
            message=f"Invalid logging.level: must be one of {valid_log_levels}",
            code="config_invalid_value",
            details={"field": "logging.level", "value": config.logging.level, "valid_values": valid_log_levels}
        )
```

### CLI Integration Pattern

**Update cli.py to load config at startup:**

```python
import typer
import sys
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.config.validator import validate_config
from guarantee_email_agent.utils.errors import ConfigurationError

app = typer.Typer(
    name="agent",
    help="Instruction-driven AI agent for warranty email automation"
)

def load_and_validate_config(config_path: str = "config.yaml"):
    """Load and validate configuration, exit with code 2 on error"""
    try:
        config = load_config(config_path)
        validate_config(config)
        return config
    except ConfigurationError as e:
        typer.echo(f"Configuration Error: {e.message}", err=True)
        typer.echo(f"Error Code: {e.code}", err=True)
        if e.details:
            typer.echo(f"Details: {e.details}", err=True)
        sys.exit(2)  # Exit code 2 for configuration errors

@app.command()
def run():
    """Start the warranty email agent for continuous processing."""
    config = load_and_validate_config()
    typer.echo(f"Configuration loaded successfully")
    typer.echo("Agent run command - to be implemented in Epic 4")

@app.command()
def eval():
    """Execute the complete evaluation test suite."""
    config = load_and_validate_config()
    typer.echo(f"Configuration loaded successfully")
    typer.echo("Agent eval command - to be implemented in Epic 5")

if __name__ == "__main__":
    app()
```

### Example config.yaml Template

**Complete config.yaml with all sections:**

```yaml
# MCP Connection Configuration
# These connection strings will be used to connect to MCP servers
mcp:
  gmail:
    connection_string: "mcp://gmail"
    # Gmail MCP server configuration (community server)

  warranty_api:
    connection_string: "mcp://warranty-api"
    endpoint: "https://api.example.com/warranty/check"
    # Custom MCP server wrapping warranty API

  ticketing_system:
    connection_string: "mcp://ticketing"
    endpoint: "https://tickets.example.com/api/v1"
    # Custom MCP server wrapping ticketing system

# Instruction File Paths
# Main orchestration instruction and scenario-specific instructions
instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"
    - "./instructions/scenarios/invalid-warranty.md"
    - "./instructions/scenarios/missing-info.md"

# Evaluation Suite Configuration
# Test suite path and pass rate threshold
eval:
  test_suite_path: "./evals/scenarios/"
  pass_threshold: 99.0  # Target: ≥99% pass rate (NFR1)

# Logging Configuration
# Log level, output destination, and file path
logging:
  level: "INFO"  # Options: DEBUG, INFO, WARN, ERROR
  output: "stdout"  # Output to standard output
  file: "./logs/agent.log"  # Log file path
```

### Testing Strategy

**Unit Test Coverage:**

1. **test_loader.py:**
   - Test loading valid config.yaml
   - Test missing config file error
   - Test invalid YAML syntax error
   - Test missing required field error
   - Test parsing nested structures

2. **test_validator.py:**
   - Test validation with complete valid config
   - Test validation catches missing MCP connection strings
   - Test validation catches missing instruction paths
   - Test validation catches invalid eval threshold
   - Test validation catches invalid log level
   - Test error messages include field paths

3. **test_schema.py:**
   - Test dataclass instantiation
   - Test default values
   - Test type hints

**Example Test:**

```python
# tests/config/test_loader.py
import pytest
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.utils.errors import ConfigurationError

def test_load_valid_config(tmp_path):
    """Test loading a valid configuration file"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
mcp:
  gmail:
    connection_string: "mcp://gmail"
  warranty_api:
    connection_string: "mcp://warranty-api"
    endpoint: "https://api.example.com/warranty"
  ticketing_system:
    connection_string: "mcp://ticketing"
    endpoint: "https://tickets.example.com"

instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"

eval:
  test_suite_path: "./evals/scenarios/"
  pass_threshold: 99.0

logging:
  level: "INFO"
  output: "stdout"
  file: "./logs/agent.log"
    """)

    config = load_config(str(config_file))

    assert config.mcp.gmail.connection_string == "mcp://gmail"
    assert config.eval.pass_threshold == 99.0
    assert config.logging.level == "INFO"

def test_load_missing_config_file():
    """Test loading non-existent config file raises error"""
    with pytest.raises(ConfigurationError) as exc_info:
        load_config("nonexistent.yaml")

    assert exc_info.value.code == "config_file_not_found"

def test_load_invalid_yaml(tmp_path):
    """Test loading invalid YAML raises error"""
    config_file = tmp_path / "bad_config.yaml"
    config_file.write_text("mcp:\n  gmail:\n    - invalid yaml structure")

    with pytest.raises(ConfigurationError) as exc_info:
        load_config(str(config_file))

    assert exc_info.value.code == "config_invalid_yaml"
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Hardcoding secrets in config.yaml:**
   ```yaml
   # WRONG - Secrets in config file
   mcp:
     gmail:
       api_key: "sk-12345"  # NO! Use env vars

   # CORRECT - Secrets from environment (Story 1.3)
   # config.yaml has no secrets, only structure
   ```

2. **Silent configuration errors:**
   ```python
   # WRONG - Silent failure
   try:
       config = load_config()
   except Exception:
       config = None  # Continues with None!

   # CORRECT - Fail fast
   config = load_config()  # Let ConfigurationError propagate
   ```

3. **Using generic exceptions:**
   ```python
   # WRONG - Generic exception
   raise Exception("Config invalid")

   # CORRECT - Specific AgentError
   raise ConfigurationError(
       message="Missing required field",
       code="config_missing_field",
       details={"field": "mcp.gmail.connection_string"}
   )
   ```

4. **Inconsistent YAML key naming:**
   ```yaml
   # WRONG - Mixed naming
   mcp:
     Gmail:  # Should be lowercase
       connectionString:  # Should be snake_case

   # CORRECT - snake_case
   mcp:
     gmail:
       connection_string:
   ```

### Verification Commands

```bash
# 1. Check config module files exist
ls -la src/guarantee_email_agent/config/
# Should show: __init__.py, loader.py, validator.py, schema.py

# 2. Verify config.yaml exists in project root
ls -la config.yaml

# 3. Test loading valid config
uv run python -c "from guarantee_email_agent.config.loader import load_config; config = load_config(); print('Config loaded successfully')"

# 4. Test validation catches missing field (should fail)
# Create invalid config temporarily and test

# 5. Run unit tests
uv run pytest tests/config/ -v

# 6. Test CLI with valid config
uv run python -m guarantee_email_agent run
# Should output "Configuration loaded successfully"

# 7. Test CLI with invalid config (should exit code 2)
mv config.yaml config.yaml.bak
uv run python -m guarantee_email_agent run
echo $?  # Should be 2
mv config.yaml.bak config.yaml
```

### References

**Architecture Document Sections:**
- [Source: architecture.md#Configuration YAML Schema] - Complete config structure
- [Source: architecture.md#Format Patterns] - Error response structures
- [Source: architecture.md#Implementation Patterns] - Naming conventions
- [Source: project-context.md#Critical Anti-Patterns] - What NOT to do
- [Source: project-context.md#Exit Code Standards] - Exit code 2 for config errors

**Epic/PRD Context:**
- [Source: epics.md#Epic 1: Project Foundation & Configuration] - Parent epic
- [Source: epics.md#Story 1.2] - Complete acceptance criteria
- [Source: prd.md#Configuration Schema] - YAML configuration requirements
- [Source: prd.md#Non-Functional Requirements NFR38, NFR41] - Fail-fast validation

**Dependencies:**
- Story 1.1: Project structure and dependencies must exist
- Story 1.3: Environment variable management (secrets loaded separately)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
