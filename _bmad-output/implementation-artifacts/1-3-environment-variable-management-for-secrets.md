# Story 1.3: Environment Variable Management for Secrets

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want to manage API keys and credentials exclusively through environment variables,
So that secrets are never committed to code or configuration files and fail-fast validation ensures production readiness.

## Acceptance Criteria

**Given** The configuration system from Story 1.2 exists
**When** I set environment variables for GMAIL_API_KEY, WARRANTY_API_KEY, and TICKETING_API_KEY
**Then** The config loader loads secrets from environment variables using python-dotenv
**And** Secrets are NOT stored in config.yaml (only non-secret config)
**And** The validator checks for required environment variables on startup
**And** Missing required secrets produce clear error: "Missing required environment variable: WARRANTY_API_KEY"
**And** .env.example file documents required environment variables without actual values
**And** .gitignore includes .env to prevent accidental commits
**And** CONFIG_PATH environment variable can override default config file location
**And** The agent fails fast (exit code 2) if any required secret is missing
**And** Secrets are accessible to MCP clients and LLM integration modules

## Tasks / Subtasks

- [x] Create .env.example template file (AC: documents required env vars)
  - [x] Document ANTHROPIC_API_KEY for LLM integration
  - [x] Document GMAIL_API_KEY for Gmail MCP authentication
  - [x] Document WARRANTY_API_KEY for warranty API authentication
  - [x] Document TICKETING_API_KEY for ticketing system authentication
  - [x] Document CONFIG_PATH as optional override
  - [x] Document LOG_LEVEL as optional override
  - [x] Add comments explaining each variable's purpose

- [x] Update .gitignore to protect secrets (AC: .env prevented from commits)
  - [x] Add .env to .gitignore
  - [x] Add *.env to catch variations
  - [x] Ensure .env.example is NOT ignored (it should be committed)
  - [x] Add comment explaining secrets protection

- [x] Enhance config loader to load environment variables (AC: secrets loaded from env)
  - [x] Add python-dotenv import to loader.py
  - [x] Call load_dotenv() at module import time
  - [x] Create load_secrets() function to read env vars
  - [x] Return dict with all required API keys
  - [x] Handle missing env vars with clear error messages

- [x] Create secrets configuration dataclass (AC: secrets accessible throughout app)
  - [x] Create SecretsConfig dataclass in schema.py
  - [x] Add fields: anthropic_api_key, gmail_api_key, warranty_api_key, ticketing_api_key
  - [x] Add to AgentConfig as secrets field
  - [x] Make secrets immutable (frozen=True)

- [x] Implement environment variable validation (AC: validator checks required secrets)
  - [x] Create validate_secrets() function in validator.py
  - [x] Check ANTHROPIC_API_KEY is set and non-empty
  - [x] Check GMAIL_API_KEY is set and non-empty
  - [x] Check WARRANTY_API_KEY is set and non-empty
  - [x] Check TICKETING_API_KEY is set and non-empty
  - [x] Raise ConfigurationError with specific variable name if missing

- [x] Add CONFIG_PATH environment variable support (AC: can override config location)
  - [x] Update load_config() to check os.getenv("CONFIG_PATH")
  - [x] Use CONFIG_PATH if set, otherwise default to "config.yaml"
  - [x] Document CONFIG_PATH in .env.example
  - [x] Test with custom config path

- [x] Integrate secrets loading into CLI startup (AC: fails fast if secrets missing)
  - [x] Update CLI to load secrets before config validation
  - [x] Call validate_secrets() during startup
  - [x] Catch ConfigurationError for missing secrets
  - [x] Exit with code 2 and clear error message

- [x] Create unit tests for secrets management (AC: validation tested)
  - [x] Create tests/config/test_secrets.py
  - [x] Test load_secrets() with all env vars set
  - [x] Test missing ANTHROPIC_API_KEY detection
  - [x] Test missing WARRANTY_API_KEY detection
  - [x] Test empty env var detection
  - [x] Test CONFIG_PATH override functionality
  - [x] Mock environment variables using pytest fixtures

- [x] Verify secrets integration (AC: secrets accessible, gitignore works)
  - [x] Create .env file locally with test values
  - [x] Run agent with valid secrets (should start)
  - [x] Remove one required env var (should fail with exit code 2)
  - [x] Verify .env is in .gitignore (git status should not show .env)
  - [x] Verify secrets are accessible in config object

## Dev Notes

### Architecture Context

This story implements **Security Requirements (NFR12-NFR16)** from the PRD, ensuring secrets are never persisted in code or configuration files and proper fail-fast validation prevents production issues.

**Key Security Principles:**
- NFR12: API keys stored ONLY in environment variables
- NFR15: Configuration validation fails fast if secrets missing
- Secrets never committed to git (protected by .gitignore)
- All secrets loaded via python-dotenv for local development
- Production uses native environment variables (Railway, Docker, etc.)

### Critical Security Rules from Project Context

**MANDATORY: Secrets in Environment Variables ONLY**

From project-context.md:
```
Configuration Secrets (MANDATORY - NFR12, NFR15):
- Secrets MUST come from environment variables only
- NEVER hardcode API keys in code
- NEVER commit .env files (use .env.example as template)
- Fail fast on startup if required secrets missing (NFR38)
```

**Forbidden Anti-Pattern:**
```yaml
# ❌ WRONG - Secrets in config.yaml
mcp:
  gmail:
    api_key: "sk-12345abc"  # NEVER DO THIS!

# ✅ CORRECT - Config.yaml has NO secrets
mcp:
  gmail:
    connection_string: "mcp://gmail"
    # API key loaded from GMAIL_API_KEY env var
```

**Exit Code Pattern:**
- Exit code 2: Configuration/secrets error
- Missing secrets = configuration error
- CLI must fail fast before any processing

### Environment Variable Design

**Required Environment Variables:**

```bash
# .env.example (committed to git)

# LLM API Key (required)
# Get your API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Gmail MCP Authentication (required)
# Configure Gmail API and get credentials
GMAIL_API_KEY=your_gmail_api_key_here

# Warranty API Authentication (required)
# Contact warranty provider for API key
WARRANTY_API_KEY=your_warranty_api_key_here

# Ticketing System Authentication (required)
# Get from ticketing system admin panel
TICKETING_API_KEY=your_ticketing_api_key_here

# Optional: Override default config file location
# CONFIG_PATH=./custom-config.yaml

# Optional: Override log level (DEBUG, INFO, WARN, ERROR)
# LOG_LEVEL=INFO
```

**Local .env file (NOT committed):**
```bash
# .env (in .gitignore - NEVER commit this file!)
ANTHROPIC_API_KEY=sk-ant-api03-xyz123...
GMAIL_API_KEY=ya29.a0AfH6SMBq...
WARRANTY_API_KEY=wk_live_abc123...
TICKETING_API_KEY=tk_prod_xyz789...
```

### Secrets Configuration Dataclass

**Add to schema.py:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # Immutable secrets
class SecretsConfig:
    """API keys and credentials loaded from environment variables"""
    anthropic_api_key: str
    gmail_api_key: str
    warranty_api_key: str
    ticketing_api_key: str

@dataclass
class AgentConfig:
    """Top-level agent configuration"""
    mcp: MCPConfig
    instructions: InstructionsConfig
    eval: EvalConfig
    logging: LoggingConfig
    secrets: SecretsConfig  # Added secrets
```

**Why frozen=True:**
- Secrets should never be modified after loading
- Immutability prevents accidental secret leakage via modification
- Clear signal that these are read-only configuration values

### Secrets Loader Implementation

**Update loader.py:**

```python
import os
from pathlib import Path
from dotenv import load_dotenv
from guarantee_email_agent.config.schema import AgentConfig, SecretsConfig
from guarantee_email_agent.utils.errors import ConfigurationError

# Load .env file at module import time
load_dotenv()

def load_secrets() -> SecretsConfig:
    """Load secrets from environment variables

    Returns:
        SecretsConfig: Loaded API keys and credentials

    Raises:
        ConfigurationError: If required environment variable is missing
    """
    required_secrets = {
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "GMAIL_API_KEY": "gmail_api_key",
        "WARRANTY_API_KEY": "warranty_api_key",
        "TICKETING_API_KEY": "ticketing_api_key",
    }

    secrets = {}
    for env_var, field_name in required_secrets.items():
        value = os.getenv(env_var)
        if not value or value.strip() == "":
            raise ConfigurationError(
                message=f"Missing required environment variable: {env_var}",
                code="config_missing_secret",
                details={"env_var": env_var}
            )
        secrets[field_name] = value.strip()

    return SecretsConfig(**secrets)

def load_config(config_path: str = None) -> AgentConfig:
    """Load configuration from YAML file and environment variables

    Args:
        config_path: Path to config.yaml (default: from CONFIG_PATH env var or "config.yaml")

    Returns:
        AgentConfig: Complete configuration including secrets

    Raises:
        ConfigurationError: If config invalid or secrets missing
    """
    # Allow CONFIG_PATH environment variable to override default
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config.yaml")

    # Load secrets first (fail fast if missing)
    secrets = load_secrets()

    # Load YAML configuration (from Story 1.2)
    config_file = Path(config_path)
    if not config_file.exists():
        raise ConfigurationError(
            message=f"Configuration file not found: {config_path}",
            code="config_file_not_found",
            details={"config_path": config_path}
        )

    # ... [YAML parsing code from Story 1.2] ...

    return AgentConfig(
        mcp=mcp_config,
        instructions=instructions_config,
        eval=eval_config,
        logging=logging_config,
        secrets=secrets  # Include loaded secrets
    )
```

### Secrets Validator Implementation

**Update validator.py:**

```python
from guarantee_email_agent.config.schema import AgentConfig, SecretsConfig
from guarantee_email_agent.utils.errors import ConfigurationError

def validate_secrets(secrets: SecretsConfig) -> None:
    """Validate secrets configuration

    Args:
        secrets: Loaded secrets configuration

    Raises:
        ConfigurationError: If secrets validation fails
    """
    # Check all secrets are non-empty (already validated in load_secrets)
    # This is a secondary validation for robustness

    if not secrets.anthropic_api_key:
        raise ConfigurationError(
            message="ANTHROPIC_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "ANTHROPIC_API_KEY"}
        )

    if not secrets.gmail_api_key:
        raise ConfigurationError(
            message="GMAIL_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "GMAIL_API_KEY"}
        )

    if not secrets.warranty_api_key:
        raise ConfigurationError(
            message="WARRANTY_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "WARRANTY_API_KEY"}
        )

    if not secrets.ticketing_api_key:
        raise ConfigurationError(
            message="TICKETING_API_KEY is empty",
            code="config_invalid_secret",
            details={"env_var": "TICKETING_API_KEY"}
        )

def validate_config(config: AgentConfig) -> None:
    """Validate complete configuration including secrets

    Args:
        config: Complete agent configuration

    Raises:
        ConfigurationError: If validation fails
    """
    # Validate secrets first
    validate_secrets(config.secrets)

    # ... [rest of validation from Story 1.2] ...
```

### .gitignore Configuration

**Update .gitignore:**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Secrets - NEVER commit these files!
.env
*.env
!.env.example  # .env.example should be committed

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db

# Project specific
uv.lock  # May want to commit this for reproducibility
```

**Critical:** The `!.env.example` line ensures .env.example is tracked by git even though .env is ignored.

### CLI Integration with Secrets

**Update cli.py:**

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

def load_and_validate_config(config_path: str = None):
    """Load and validate configuration including secrets, exit with code 2 on error"""
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
```

### Testing Strategy with Mock Environment

**Unit Test Pattern (tests/config/test_secrets.py):**

```python
import pytest
import os
from guarantee_email_agent.config.loader import load_secrets
from guarantee_email_agent.utils.errors import ConfigurationError

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set mock environment variables"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")

def test_load_secrets_with_all_vars_set(mock_env_vars):
    """Test loading secrets when all environment variables are set"""
    secrets = load_secrets()

    assert secrets.anthropic_api_key == "sk-ant-test-123"
    assert secrets.gmail_api_key == "gmail-test-456"
    assert secrets.warranty_api_key == "warranty-test-789"
    assert secrets.ticketing_api_key == "ticket-test-abc"

def test_load_secrets_missing_anthropic_key(monkeypatch):
    """Test that missing ANTHROPIC_API_KEY raises error"""
    # Set all except ANTHROPIC_API_KEY
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"
    assert "ANTHROPIC_API_KEY" in exc_info.value.message

def test_load_secrets_empty_value(monkeypatch):
    """Test that empty secret value raises error"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("GMAIL_API_KEY", "gmail-test-456")
    monkeypatch.setenv("WARRANTY_API_KEY", "warranty-test-789")
    monkeypatch.setenv("TICKETING_API_KEY", "ticket-test-abc")

    with pytest.raises(ConfigurationError) as exc_info:
        load_secrets()

    assert exc_info.value.code == "config_missing_secret"

def test_config_path_override(monkeypatch, tmp_path):
    """Test CONFIG_PATH environment variable override"""
    # Create custom config file
    custom_config = tmp_path / "custom.yaml"
    custom_config.write_text("...")  # Valid config YAML

    monkeypatch.setenv("CONFIG_PATH", str(custom_config))
    # Set required secrets...

    config = load_config()
    # Verify custom config was loaded
```

### Common Security Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Committing secrets to git:**
   ```bash
   # WRONG - .env file in git
   git add .env  # NEVER!

   # CORRECT - .env in .gitignore, only commit .env.example
   git add .env.example
   ```

2. **Hardcoding secrets in code:**
   ```python
   # WRONG - Hardcoded API key
   ANTHROPIC_API_KEY = "sk-ant-api03-xyz123"

   # CORRECT - Load from environment
   anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
   ```

3. **Storing secrets in config.yaml:**
   ```yaml
   # WRONG - Secrets in YAML
   secrets:
     anthropic_key: "sk-ant-api03-xyz123"

   # CORRECT - config.yaml has NO secrets
   # Secrets loaded separately from environment
   ```

4. **Silent missing secrets:**
   ```python
   # WRONG - Default to empty string
   api_key = os.getenv("API_KEY", "")

   # CORRECT - Fail fast if missing
   api_key = os.getenv("API_KEY")
   if not api_key:
       raise ConfigurationError("Missing API_KEY")
   ```

5. **Logging secrets:**
   ```python
   # WRONG - Logging secret values
   logger.info(f"API Key: {config.secrets.anthropic_api_key}")

   # CORRECT - Never log secrets
   logger.info("API keys loaded successfully")
   ```

### Railway Deployment Configuration

**Railway automatically loads environment variables:**

1. Set in Railway Dashboard → Variables:
   - `ANTHROPIC_API_KEY`
   - `GMAIL_API_KEY`
   - `WARRANTY_API_KEY`
   - `TICKETING_API_KEY`

2. Railway injects these as environment variables
3. python-dotenv works locally, native env vars work in production
4. No .env file needed in production (Railway provides env vars)

### Verification Commands

```bash
# 1. Verify .env.example exists and is tracked by git
ls -la .env.example
git status  # Should show .env.example as tracked

# 2. Verify .env is in .gitignore
cat .gitignore | grep "^\.env$"

# 3. Create local .env file for testing
cp .env.example .env
# Edit .env with test API keys

# 4. Verify .env is ignored by git
touch .env
git status  # Should NOT show .env

# 5. Test loading secrets with valid .env
uv run python -c "from guarantee_email_agent.config.loader import load_secrets; s = load_secrets(); print('Secrets loaded')"

# 6. Test missing secret error
mv .env .env.bak
uv run python -m guarantee_email_agent run
# Should fail with exit code 2 and "Missing required environment variable" error
echo $?  # Should be 2
mv .env.bak .env

# 7. Test CONFIG_PATH override
export CONFIG_PATH=./custom-config.yaml
# Create custom config...
uv run python -m guarantee_email_agent run

# 8. Run secrets tests
uv run pytest tests/config/test_secrets.py -v

# 9. Verify secrets in loaded config
uv run python -c "from guarantee_email_agent.config.loader import load_config; c = load_config(); print('Anthropic key loaded:', bool(c.secrets.anthropic_api_key))"
```

### Security Best Practices Checklist

**Development:**
- [x] .env file created locally (NOT committed)
- [x] .env.example committed with placeholder values
- [x] .gitignore includes .env pattern
- [x] All secrets loaded via os.getenv()
- [x] No secrets in config.yaml
- [x] No secrets hardcoded in Python files

**Production:**
- [x] Environment variables set in Railway dashboard
- [x] No .env file deployed to production
- [x] Secrets validated on startup (fail fast)
- [x] Exit code 2 for missing secrets
- [x] Clear error messages guide configuration

**Testing:**
- [x] Use monkeypatch to mock env vars in tests
- [x] Test all required secrets
- [x] Test missing secret detection
- [x] Test empty secret detection
- [x] Never use real secrets in tests

### References

**Architecture Document Sections:**
- [Source: architecture.md#Configuration Schema] - Environment variables section
- [Source: architecture.md#Railway Deployment] - Environment variable management
- [Source: project-context.md#Configuration Secrets] - Mandatory secrets rules (NFR12, NFR15)
- [Source: project-context.md#Critical Anti-Patterns] - Forbidden secrets patterns

**Epic/PRD Context:**
- [Source: epics.md#Epic 1: Project Foundation & Configuration] - Parent epic
- [Source: epics.md#Story 1.3] - Complete acceptance criteria
- [Source: prd.md#Security Requirements NFR12-NFR16] - Secrets security requirements
- [Source: prd.md#Configuration Management FR37] - Environment variable requirements

**Dependencies:**
- Story 1.1: python-dotenv dependency must be installed
- Story 1.2: Configuration loader and validator infrastructure
- Story 1.4: Will use secrets for MCP connection testing

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

claude-sonnet-4-5-20250929

### Debug Log References

No debugging required - all tasks completed successfully on first attempt.

### Completion Notes List

**Implementation Summary:**
- Enhanced .env.example with comprehensive documentation for all required secrets
- Updated .gitignore with `!.env.example` exception to ensure template is tracked
- Created frozen SecretsConfig dataclass for immutable API keys
- Implemented load_secrets() function with fail-fast validation
- Enhanced load_config() to load secrets and support CONFIG_PATH override
- Implemented validate_secrets() function with field-level validation
- Integrated secrets loading into CLI with helpful error hints
- Created 10 comprehensive unit tests for secrets management (all passing)
- Verified CLI integration with valid/invalid secrets scenarios

**All Acceptance Criteria Met:**
✅ Secrets loaded from environment variables using python-dotenv
✅ Secrets NOT stored in config.yaml (only non-secret config)
✅ Validator checks for all required environment variables on startup
✅ Missing secrets produce clear error messages with env var names
✅ .env.example documents required variables without actual values
✅ .gitignore includes .env protection (with .env.example exception)
✅ CONFIG_PATH environment variable can override config file location
✅ Agent fails fast (exit code 2) if any required secret is missing
✅ Secrets accessible throughout app via config.secrets

**Test Results:**
- 10/10 secrets tests passing (28 total config tests with Story 1.2)
- Valid secrets: loads successfully ✅
- Missing ANTHROPIC_API_KEY: exit code 2 with helpful hint ✅
- CONFIG_PATH override: works correctly ✅
- .env correctly ignored by git ✅
- SecretsConfig is immutable (frozen=True) ✅

**Code Review Fixes Applied (Post-Implementation):**
- Fixed all subtask completion markers (were incorrectly [ ] instead of [x])
- All config dataclasses now immutable (frozen=True) for consistency with SecretsConfig
- Enhanced error handling to show full dotted field paths
- Added file path and URL validation to validator
- All 28 tests passing after comprehensive review

**Security Verification:**
- .env file NOT tracked by git ✅
- .env.example IS tracked by git ✅
- No secrets in config.yaml ✅
- All secrets validated on startup ✅
- Helpful hints provided for missing secrets ✅

### File List

- .env.example (updated)
- .gitignore (updated)
- src/guarantee_email_agent/config/__init__.py (updated)
- src/guarantee_email_agent/config/schema.py (updated - added SecretsConfig)
- src/guarantee_email_agent/config/loader.py (updated - added load_secrets, CONFIG_PATH support)
- src/guarantee_email_agent/config/validator.py (updated - added validate_secrets)
- src/guarantee_email_agent/cli.py (updated - enhanced error handling)
- tests/config/test_secrets.py (new - 10 tests)
- tests/config/test_validator.py (updated - added SecretsConfig to helper)
- .env (created locally for testing - NOT committed)
