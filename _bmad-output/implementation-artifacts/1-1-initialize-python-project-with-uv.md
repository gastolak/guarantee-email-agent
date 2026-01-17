# Story 1.1: Initialize Python Project with uv

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want to initialize the guarantee-email-agent project using uv package manager with src-layout and Typer CLI framework,
So that I have a modern, fast, reproducible Python project foundation ready for development.

## Acceptance Criteria

**Given** I have uv installed on my system
**When** I run the project initialization commands from the architecture document
**Then** The project is created with src-layout structure: `src/guarantee_email_agent/`
**And** pyproject.toml exists with Python 3.10+ requirement
**And** Typer CLI framework is added as dependency with `[all]` extras
**And** Core dependencies are specified: anthropic>=0.8.0, pyyaml>=6.0, python-dotenv>=1.0.0, httpx>=0.25.0, tenacity>=8.2.0
**And** Dev dependencies include pytest>=7.4.0 and pytest-asyncio>=0.21.0
**And** All required directories exist: `src/guarantee_email_agent/{config,email,instructions,integrations,llm,eval,utils}`
**And** All user content directories exist: `instructions/scenarios/`, `evals/scenarios/`, `mcp_servers/{warranty_mcp_server,ticketing_mcp_server}`
**And** Test directory structure mirrors src structure
**And** Basic CLI entry point exists at `src/guarantee_email_agent/cli.py`
**And** `__main__.py` enables `python -m guarantee_email_agent` execution
**And** Running `uv run python -m guarantee_email_agent --help` displays CLI help without errors

## Tasks / Subtasks

- [x] Install and verify uv package manager (AC: displays help)
  - [x] Run installation: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - [x] Verify installation: `uv --version`

- [x] Initialize project with uv and configure Python version (AC: pyproject.toml exists, Python 3.10+)
  - [x] Run: `uv init --package guarantee-email-agent`
  - [x] Navigate to project: `cd guarantee-email-agent`
  - [x] Set Python version: `echo "3.10" > .python-version`

- [x] Add core production dependencies (AC: dependencies specified correctly)
  - [x] Add CLI framework: `uv add "typer[all]>=0.9.0"`
  - [x] Add LLM SDK: `uv add "anthropic>=0.8.0"`
  - [x] Add YAML parser: `uv add "pyyaml>=6.0"`
  - [x] Add env vars: `uv add "python-dotenv>=1.0.0"`
  - [x] Add HTTP client: `uv add "httpx>=0.25.0"`
  - [x] Add retry logic: `uv add "tenacity>=8.2.0"`

- [x] Add development dependencies (AC: dev dependencies included)
  - [x] Add testing framework: `uv add --dev "pytest>=7.4.0"`
  - [x] Add async testing: `uv add --dev "pytest-asyncio>=0.21.0"`

- [x] Create complete directory structure (AC: all directories exist)
  - [x] Create src modules: `mkdir -p src/guarantee_email_agent/{config,email,instructions,integrations,llm,eval,utils}`
  - [x] Create user content: `mkdir -p instructions/scenarios`
  - [x] Create eval scenarios: `mkdir -p evals/scenarios`
  - [x] Create MCP servers: `mkdir -p mcp_servers/{warranty_mcp_server,ticketing_mcp_server}`
  - [x] Create test structure: `mkdir -p tests/{config,email,instructions,integrations,llm,eval,utils}`

- [x] Create Python package structure files (AC: entry points exist)
  - [x] Create `src/guarantee_email_agent/__init__.py` with version export
  - [x] Create `src/guarantee_email_agent/__main__.py` with entry point
  - [x] Create `src/guarantee_email_agent/cli.py` with Typer CLI app
  - [x] Create __init__.py files in all subdirectories

- [x] Configure project metadata in pyproject.toml (AC: correct project configuration)
  - [x] Update [project] section with name, version, description
  - [x] Set requires-python to ">=3.10"
  - [x] Configure [project.scripts] for CLI entry point
  - [x] Add [build-system] configuration

- [x] Create supporting files (AC: complete project structure)
  - [x] Create `.gitignore` for Python projects
  - [x] Create `.env.example` with API key templates
  - [x] Create `README.md` with basic setup instructions
  - [x] Create `Procfile` for Railway deployment

- [x] Verify CLI functionality (AC: CLI help displays without errors)
  - [x] Run: `uv run python -m guarantee_email_agent --help`
  - [x] Verify Typer CLI help output appears
  - [x] Check exit code is 0

## Dev Notes

### Architecture Context

This story implements the foundation from the **Architecture Decision Document - Starter Template Evaluation**. Key decisions:

1. **Package Manager:** uv (2025 Python standard, 10-100x faster than pip/Poetry)
2. **CLI Framework:** Typer with `[all]` extras for modern Python CLI development
3. **Project Structure:** src-layout for proper package isolation
4. **Deployment Platform:** Railway (configured via Procfile)

### Critical Implementation Rules from Project Context

**MANDATORY: Use ONLY uv package manager**
- NEVER use pip, pipenv, or Poetry
- All dependency management via `uv add` commands
- Run commands via `uv run` (no manual virtualenv activation)

**Project Structure Pattern (CRITICAL):**
- MUST use src-layout: `src/guarantee_email_agent/`
- NEVER import from project root
- All imports from `guarantee_email_agent` package
- Entry point: `src/guarantee_email_agent/__main__.py`
- CLI commands: `src/guarantee_email_agent/cli.py`

**Naming Conventions (PEP 8 Strict):**
- Modules/packages: `snake_case` (e.g., `mcp_client.py`)
- Functions/methods: `snake_case` (e.g., `load_instruction()`)
- Classes: `PascalCase` (e.g., `EvalRunner`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES = 3`)

### Technology Stack Requirements

**Python & Dependencies:**
- Python 3.10+ (set via `.python-version`)
- Core Dependencies (exact versions from architecture):
  - `typer[all]>=0.9.0` - CLI framework
  - `anthropic>=0.8.0` - LLM integration
  - `pyyaml>=6.0` - Instruction file parsing
  - `python-dotenv>=1.0.0` - Environment variable management
  - `httpx>=0.25.0` - Async HTTP client for API calls
  - `tenacity>=8.2.0` - Retry logic with exponential backoff
- Dev Dependencies:
  - `pytest>=7.4.0` - Testing framework
  - `pytest-asyncio>=0.21.0` - Async testing support

**MCP SDK (Not added in this story):**
- MCP Python SDK v1.25.0 will be added in Epic 2 (MCP Integration Layer)
- Architecture specifies: "Uses official mcp Python SDK (v1.25.0 stable)"

### Project Structure Notes

**Directory Organization (Feature-Based):**
```
guarantee-email-agent/
├── src/guarantee_email_agent/    # Main package (src-layout)
│   ├── config/                    # Configuration loading
│   ├── email/                     # Email processing
│   ├── instructions/              # Instruction loading & routing
│   ├── integrations/              # MCP client implementations
│   ├── llm/                       # LLM orchestration
│   ├── eval/                      # Eval framework
│   └── utils/                     # Shared utilities
├── tests/                         # Test directory (mirrors src/)
├── instructions/                  # User-editable instruction files
├── evals/scenarios/               # Eval test cases
└── mcp_servers/                   # Custom MCP servers
```

**Why src-layout:**
- Prevents accidental imports from development directory
- Ensures proper packaging for Railway deployment
- Standard modern Python project structure
- Clear separation of concerns

### CLI Entry Point Pattern

**Basic Typer CLI Structure:**

The `cli.py` file should follow this pattern:

```python
import typer
from typing_extensions import Annotated

app = typer.Typer(
    name="agent",
    help="Instruction-driven AI agent for warranty email automation"
)

@app.command()
def run():
    """Start the warranty email agent for continuous processing."""
    typer.echo("Agent run command - to be implemented in Epic 4")

@app.command()
def eval():
    """Execute the complete evaluation test suite."""
    typer.echo("Agent eval command - to be implemented in Epic 5")

if __name__ == "__main__":
    app()
```

**__main__.py pattern:**
```python
from guarantee_email_agent.cli import app

if __name__ == "__main__":
    app()
```

### pyproject.toml Configuration

**Minimum required configuration:**

```toml
[project]
name = "guarantee-email-agent"
version = "0.1.0"
description = "Instruction-driven AI agent for warranty email automation"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "typer[all]>=0.9.0",
    "anthropic>=0.8.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.25.0",
    "tenacity>=8.2.0",
]

[project.scripts]
agent = "guarantee_email_agent.cli:app"

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Railway Deployment Configuration

**Procfile (for Railway):**
```
worker: uv run python -m guarantee_email_agent run
```

**Railway auto-detects:**
1. `.python-version` → installs Python 3.10
2. `pyproject.toml` + `uv.lock` → uses uv for installation
3. Runs `uv sync` to install exact locked dependencies

### Environment Variables Template

**.env.example (for secrets):**
```
# LLM API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# MCP Integration Keys
GMAIL_API_KEY=your_gmail_api_key_here
WARRANTY_API_KEY=your_warranty_api_key_here
TICKETING_API_KEY=your_ticketing_api_key_here

# Optional Configuration
CONFIG_PATH=./config.yaml
LOG_LEVEL=INFO
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Using wrong package manager:**
   ```bash
   # WRONG
   pip install anthropic
   poetry add anthropic

   # CORRECT
   uv add anthropic>=0.8.0
   ```

2. **Manual virtualenv activation:**
   ```bash
   # WRONG
   source venv/bin/activate
   python -m guarantee_email_agent run

   # CORRECT
   uv run python -m guarantee_email_agent run
   ```

3. **Importing from project root:**
   ```python
   # WRONG
   import config.loader

   # CORRECT
   from guarantee_email_agent.config import loader
   ```

4. **Missing src-layout:**
   ```
   # WRONG structure
   guarantee-email-agent/
   ├── guarantee_email_agent/  # Root level package

   # CORRECT structure
   guarantee-email-agent/
   ├── src/
   │   └── guarantee_email_agent/  # Src-layout
   ```

### Testing the Setup

**Verification Commands:**
```bash
# 1. Check uv is installed
uv --version

# 2. Verify Python version
cat .python-version  # Should show "3.10"

# 3. Check dependencies are locked
ls uv.lock  # Should exist

# 4. Verify project structure
ls -la src/guarantee_email_agent/
ls -la instructions/scenarios/
ls -la evals/scenarios/
ls -la mcp_servers/

# 5. Test CLI entry point
uv run python -m guarantee_email_agent --help
# Should display Typer-generated help without errors
```

### References

**Architecture Document Sections:**
- [Source: architecture.md#Starter Template Evaluation] - uv initialization commands
- [Source: architecture.md#Project Structure & Boundaries] - Complete directory structure
- [Source: architecture.md#Implementation Patterns] - Naming conventions and import patterns
- [Source: project-context.md#Technology Stack & Versions] - Exact dependency versions
- [Source: project-context.md#Python Language-Specific Rules] - src-layout and import patterns

**Epic/PRD Context:**
- [Source: epics.md#Epic 1: Project Foundation & Configuration] - Parent epic context
- [Source: epics.md#Story 1.1] - Complete acceptance criteria
- [Source: prd.md#CLI Tool Specific Requirements] - CLI command structure

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

No debugging required - all tasks completed successfully on first attempt.

### Completion Notes List

**Implementation Summary:**
- Initialized uv-based Python project with src-layout structure
- Configured Python 3.10+ requirement and installed all core/dev dependencies
- Created complete directory structure for modular architecture
- Implemented basic Typer CLI with `run` and `eval` commands
- Configured pyproject.toml with project metadata and CLI entry point
- Created all supporting files (.gitignore, .env.example, README.md, Procfile)
- Verified CLI functionality - help displays correctly with exit code 0

**All Acceptance Criteria Met:**
✅ pyproject.toml exists with Python 3.10+ requirement
✅ Typer CLI framework added with [all] extras
✅ Core dependencies specified correctly (anthropic, pyyaml, python-dotenv, httpx, tenacity)
✅ Dev dependencies included (pytest, pytest-asyncio)
✅ All required directories exist (src structure, instructions, evals, mcp_servers, tests)
✅ CLI entry point exists at src/guarantee_email_agent/cli.py
✅ __main__.py enables python -m execution
✅ uv run python -m guarantee_email_agent --help displays without errors

### File List

- .gitignore
- .env.example
- .python-version
- README.md
- Procfile
- pyproject.toml
- src/guarantee_email_agent/__init__.py
- src/guarantee_email_agent/__main__.py
- src/guarantee_email_agent/cli.py
- src/guarantee_email_agent/config/__init__.py
- src/guarantee_email_agent/email/__init__.py
- src/guarantee_email_agent/instructions/__init__.py
- src/guarantee_email_agent/integrations/__init__.py
- src/guarantee_email_agent/llm/__init__.py
- src/guarantee_email_agent/eval/__init__.py
- src/guarantee_email_agent/utils/__init__.py

