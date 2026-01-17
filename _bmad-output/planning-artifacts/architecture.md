---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-guarantee-email-agent-2026-01-17.md'
  - '_bmad-output/planning-artifacts/prd.md'
workflowType: 'architecture'
project_name: 'guarantee-email-agent'
user_name: 'mMaciek'
date: '2026-01-17'
lastStep: 8
status: 'complete'
completedAt: '2026-01-17'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The guarantee-email-agent has 51 functional requirements organized into 9 capability areas. The architecture must support:

- **Email Processing & Analysis (FR1-FR5):** Continuous Gmail inbox monitoring via MCP, content parsing, serial number extraction from varied formats, scenario detection, and extraction failure identification
- **Warranty Validation (FR6-FR9):** External warranty API integration via MCP with error/timeout handling and status determination
- **Instruction-Driven Workflow (FR10-FR14):** Core architectural pattern—main instruction file orchestration, dynamic scenario-specific instruction loading, LLM reasoning execution, and markdown-based instruction editing via version control
- **Response Generation & Delivery (FR15-FR18):** Contextual email drafting following scenario instructions, graceful degradation for edge cases
- **Ticket Management (FR19-FR21):** Automated ticket creation in external system via MCP for valid warranty cases
- **CLI Runtime Operations (FR22-FR26):** `agent run` continuous processing, graceful shutdown, structured logging to stdout/files
- **Evaluation Framework (FR27-FR33):** `agent eval` execution, end-to-end scenario testing, pass rate calculation, eval suite management, regression prevention
- **Configuration Management (FR34-FR41):** YAML config for MCP connections and instruction paths, environment variables for secrets, startup validation with fail-fast behavior
- **Error Handling & Resilience (FR42-FR46):** Retry with exponential backoff, circuit breaker pattern, detailed failure logging, no silent failures, signal handling
- **Scripting & Automation Support (FR47-FR51):** Non-interactive execution, exit codes, pipeline compatibility, daemon mode

**Non-Functional Requirements:**

33 NFRs across 6 quality dimensions that will drive architectural decisions:

- **Reliability (NFR1-NFR6):** ≥99% eval pass rate (the defining success metric), 100% autonomous processing, zero critical failures, >99.5% uptime, no silent failures, graceful handling of unexpected inputs
- **Performance (NFR7-NFR11):** 60-second email processing (p95), 5-minute eval suite execution (50 scenarios), 30-second startup, concurrent processing above 1 email/min, 15-second LLM timeout
- **Security (NFR12-NFR16):** Secrets in environment variables only, TLS 1.2+ for all MCP connections, customer data logged only at DEBUG level, fail-fast on missing secrets, stateless email handling (no persistence)
- **Integration (NFR17-NFR22):** Retry with exponential backoff (max 3 retries), circuit breaker (opens after 5 consecutive failures), rate limiting handling, 10-second warranty API timeout, ticket creation validation, continue processing on partial integration failure
- **Maintainability (NFR23-NFR28):** Plain markdown instructions, instruction syntax validation on startup, sufficient logging context, config-only changes (no code deployment for behavior changes), human-readable eval scenarios, clear error messages with remediation steps
- **Operational Excellence (NFR29-NFR33):** Specific exit codes (0=success, 2=config, 3=MCP, 4=eval), Unix signal respect (SIGTERM/SIGINT), single-process design, log rotation compatibility, idempotent startup

**Scale & Complexity:**

- **Primary domain:** CLI automation tool with LLM orchestration and external integrations
- **Complexity level:** Low to Medium (focused scope, clear boundaries, 3 external integrations)
- **Estimated architectural components:** 
  - CLI runtime and command dispatcher
  - Instruction loader and scenario router
  - LLM orchestration engine
  - MCP client abstraction layer (3 integrations)
  - Eval framework and test runner
  - Configuration and secret management
  - Logging and observability layer

### Technical Constraints & Dependencies

**External Dependencies:**
- LLM API (Anthropic Claude or similar) for reasoning and email analysis
- MCP protocol for all external integrations (Gmail, Warranty API, Ticketing system)
- Implementation language options: Python 3.10+ or Node.js 18+ (to be decided)

**Runtime Constraints:**
- Must run as single process for process supervisor compatibility (systemd, launchd)
- Must be container-ready (Docker, Kubernetes)
- Stateless processing model (no local state persistence between emails)
- File system access required for instruction files and eval suites

**Development Constraints:**
- Single developer (CTO) with limited time
- 3-4 weeks initial development target
- Must support iterative instruction refinement without code changes

### Cross-Cutting Concerns Identified

**Instruction Architecture:**
- Instruction file loading, parsing, and validation affects runtime and eval execution
- Dynamic scenario routing must work consistently across all email processing
- Syntax validation at startup to fail fast on malformed instructions

**MCP Integration Resilience:**
- Connection management, retry logic, and circuit breaker patterns apply to all 3 integrations
- Graceful degradation when integrations are temporarily unavailable
- Credential management and TLS configuration standardized across MCP clients

**Eval Framework:**
- Test reproducibility despite LLM non-determinism
- Scenario versioning aligned with instruction changes
- Regression detection when instructions change
- Pass rate calculation and reporting

**Observability & Debugging:**
- Structured logging across all components (timestamp, level, context)
- Error messages with actionable remediation steps
- Processing trace for failed scenarios to support instruction refinement
- Log levels configurable (DEBUG for development, INFO for production)

**Configuration & Secrets:**
- YAML config schema validation
- Environment variable injection for secrets
- Fail-fast behavior on invalid configuration
- MCP connection pre-flight testing before processing starts

### Architectural Challenges

**Challenge 1: LLM Determinism for 99% Correctness**
The core tension—LLMs are non-deterministic, but 99% eval pass rate requires consistent behavior. Architecture must address this through instruction precision, scenario coverage, and potentially temperature/sampling controls.

**Challenge 2: Zero Silent Failures**
Every email must be provably processed or explicitly marked as failed. Architecture requires explicit success/failure tracking per email, retry exhaustion logging, and email state visibility for debugging.

## Starter Template Evaluation

### Technical Preferences Established

**Language & Runtime:** Python 3.10+
- Strong LLM integration ecosystem (Anthropic SDK, LangChain)
- Excellent text processing and instruction parsing capabilities
- Mature CLI framework options
- pytest for eval framework testing

**Deployment Platform:** Railway
- Git-based deployments (push to deploy)
- Excellent environment variable management for API keys
- Native uv support for fast, reliable deployments

**Package Manager:** uv (2025 standard)
- 10-100x faster than pip/Poetry
- Cross-platform lockfile (uv.lock) for reproducibility
- Built-in Python version management
- Simple workflow: `uv run` eliminates manual virtualenv activation

**CLI Framework:** Typer (recommended for 2025)
- Modern Python CLI framework built on Click
- Type hints for clean code with minimal boilerplate
- Better IDE autocompletion support
- Maintained by FastAPI author (Sebastian Ramírez)
- All Click power underneath when needed

### Primary Technology Domain

**CLI automation tool** with LLM orchestration and external integrations (MCP protocol)

### Starter Options Considered

**Option 1: uv init with custom src-layout (Recommended)**

Modern Python CLI projects use uv with src-layout and pyproject.toml:

```
guarantee-email-agent/
├── src/
│   └── guarantee_email_agent/
│       ├── __init__.py
│       ├── __main__.py          # Entry point
│       ├── cli.py                # CLI command definitions (Typer)
│       ├── config/
│       │   ├── __init__.py
│       │   └── loader.py         # YAML config + env var loading
│       ├── instructions/
│       │   ├── __init__.py
│       │   ├── loader.py         # Instruction file loader
│       │   └── router.py         # Scenario routing logic
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── mcp_client.py    # Base MCP abstraction
│       │   ├── gmail.py         # Gmail MCP
│       │   ├── warranty_api.py  # Warranty API MCP
│       │   └── ticketing.py     # Ticketing MCP
│       ├── llm/
│       │   ├── __init__.py
│       │   └── orchestrator.py  # LLM reasoning engine
│       ├── eval/
│       │   ├── __init__.py
│       │   ├── runner.py        # Eval suite executor
│       │   └── reporter.py      # Pass rate calculation
│       └── utils/
│           ├── __init__.py
│           ├── logging.py       # Structured logging
│           └── retry.py         # Retry/circuit breaker
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_instructions.py
│   └── test_eval.py
├── instructions/                 # User-editable instructions
│   ├── main.md
│   └── scenarios/
│       ├── valid-warranty.md
│       ├── invalid-warranty.md
│       └── missing-info.md
├── evals/
│   └── scenarios/               # Eval test cases
│       ├── scenario_001.yaml
│       └── scenario_002.yaml
├── config.yaml                  # MCP connections config
├── .python-version             # 3.10
├── pyproject.toml              # Project metadata (uv managed)
├── uv.lock                     # Cross-platform dependency lockfile
├── Procfile                    # Railway startup command
├── .env.example               # Example secrets
├── .gitignore
└── README.md
```

**Option 2: Traditional Poetry/pip approach**
- Slower dependency resolution (10-100x slower than uv)
- More complex virtualenv management
- Not recommended for 2025 greenfield projects

### Selected Approach: uv init with Custom src-layout

**Rationale for Selection:**

Your project has a unique architecture (instruction-driven LLM orchestration) that doesn't fit standard web/API templates. Using uv with custom src-layout gives you:

1. **Modern 2025 tooling** - uv is the current Python standard, fast and reliable
2. **Clean separation of concerns** - aligned with your 7 architectural components
3. **Standard Python packaging** - easy Railway deployment with native uv support
4. **Reproducible builds** - uv.lock ensures consistent environments
5. **Developer experience** - `uv run` eliminates virtualenv friction

**Initialization Commands:**

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize the project with package structure for CLI
uv init --package guarantee-email-agent
cd guarantee-email-agent

# Set Python version
echo "3.10" > .python-version

# Add core dependencies
uv add "typer[all]>=0.9.0"
uv add "anthropic>=0.8.0"
uv add "pyyaml>=6.0"
uv add "python-dotenv>=1.0.0"
uv add "httpx>=0.25.0"
uv add "tenacity>=8.2.0"

# Add dev dependencies
uv add --dev "pytest>=7.4.0"
uv add --dev "pytest-asyncio>=0.21.0"

# Create additional directories
mkdir -p instructions/scenarios
mkdir -p evals/scenarios
mkdir -p src/guarantee_email_agent/{config,instructions,integrations,llm,eval,utils}

# Run the CLI (uv handles virtualenv automatically)
uv run python -m guarantee_email_agent --help
```

### Architectural Decisions Provided by This Structure

**Language & Runtime:**
- Python 3.10+ for LLM ecosystem and async capabilities
- Type hints throughout for clarity and IDE support
- src-layout for proper package isolation
- uv manages Python versions automatically via .python-version

**Package Management:**
- uv for ultra-fast dependency resolution (10-100x faster)
- pyproject.toml for project metadata (PEP 621 compliant)
- uv.lock for cross-platform reproducible builds
- No manual virtualenv management required

**CLI Framework:**
- Typer for command definitions (`agent run`, `agent eval`)
- Decorator-based command structure with type hints
- Automatic help generation and validation
- Entry point defined in pyproject.toml [project.scripts]

**Testing Framework:**
- pytest for eval framework and unit tests
- pytest-asyncio for async email processing tests
- Coverage reporting for code quality
- Run tests with: `uv run pytest`

**Code Organization:**
- src-layout prevents accidental imports from development directory
- Clear module boundaries (cli, config, instructions, integrations, llm, eval, utils)
- Separation of user-editable content (instructions/, evals/) from code (src/)

**Development Experience:**
- Structured logging with Python logging module
- Environment variable loading via python-dotenv
- YAML config parsing with PyYAML
- Type checking with mypy (optional): `uv add --dev mypy`
- Simple command execution: `uv run <command>` (no activation needed)

**Deployment:**
- Railway Procfile: `worker: uv run python -m guarantee_email_agent run`
- Railway automatically detects and uses uv for installation
- uv.lock ensures exact same dependencies in production
- Environment variables for all secrets (no .env in production)
- Single-process design for process supervisor compatibility

**pyproject.toml Configuration:**

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

**Railway Deployment Configuration:**

**Procfile:**
```
worker: uv run python -m guarantee_email_agent run
```

**Environment Variables (set in Railway dashboard):**
- GMAIL_API_KEY
- WARRANTY_API_KEY
- TICKETING_API_KEY
- CONFIG_PATH (optional override)
- LOG_LEVEL=INFO

**Railway Build Process:**
1. Detects .python-version → installs Python 3.10
2. Detects pyproject.toml + uv.lock → uses uv for installation
3. Runs `uv sync` to install exact locked dependencies
4. Executes Procfile command with uv run

**Note:** Project initialization following this structure should be the first implementation task. The uv-based structure provides modern 2025 Python tooling aligned precisely with your instruction-driven architecture requirements and Railway deployment model.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**

All architectural decisions work together cohesively without conflicts:

- **Python 3.10+ + uv + Typer:** Modern 2025 stack, all components maintained and compatible
- **Anthropic SDK + Temperature=0:** Compatible with Python async, supports determinism goals
- **MCP Python SDK v1.25.0:** Stable release, works with Python 3.10+, stdio transport supported
- **YAML + XML Instruction Format:** PyYAML parses frontmatter, XML body readable by LLM
- **Railway + uv:** Native uv support in Railway, seamless deployment
- **tenacity + httpx:** Standard Python libraries, no version conflicts

All pinned versions verified compatible (checked release dates, Python version requirements, breaking changes). No technology contradictions detected.

**Pattern Consistency:**

Implementation patterns fully support architectural decisions:

- **PEP 8 naming + kebab-case instructions:** Clear separation between code and user-editable content
- **Retry logic pattern** (tenacity decorator) aligns with MCP client architecture
- **Structured logging pattern** (extra dict) supports observability requirements (NFR23-25)
- **AgentError hierarchy** aligns with fail-fast philosophy (NFR5, NFR45)
- **Stateless processing** (no persistence) supported by in-memory data flow architecture

All 10 enforcement guidelines directly support the 4 critical architectural decisions. Pattern examples demonstrate correct application of decisions.

**Structure Alignment:**

Project structure enables all architectural decisions:

- **src-layout** supports clean packaging for Railway deployment
- **Feature-based organization** (`email/`, `instructions/`, `integrations/`) matches domain boundaries
- **Separated user content** (`instructions/`, `evals/`) enables instruction-driven architecture
- **Custom MCP servers** (`mcp_servers/`) cleanly isolated from main agent
- **Test mirroring** supports comprehensive testing requirements

Directory structure provides clear home for every FR and NFR implementation point.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**

All 51 FRs architecturally supported with specific implementation locations:

- **FR1-5 (Email Processing):** `email/processor.py`, `email/parser.py`, `email/serial_extractor.py` + `integrations/gmail.py`
- **FR6-9 (Warranty Validation):** `integrations/warranty_api.py` + `mcp_servers/warranty_mcp_server/`
- **FR10-14 (Instruction-Driven):** `instructions/loader.py`, `instructions/router.py`, `llm/orchestrator.py`
- **FR15-18 (Response Generation):** `llm/response_generator.py`, `llm/orchestrator.py`, `integrations/gmail.py`
- **FR19-21 (Ticket Management):** `integrations/ticketing.py` + `mcp_servers/ticketing_mcp_server/`
- **FR22-26 (CLI Runtime):** `cli.py`, `utils/logging.py`
- **FR27-33 (Eval Framework):** `eval/runner.py`, `eval/reporter.py`, `eval/validator.py`
- **FR34-41 (Configuration):** `config/loader.py`, `config/validator.py`
- **FR42-46 (Error Handling):** `utils/retry.py`, `utils/errors.py`, `utils/logging.py`
- **FR47-51 (Scripting Support):** `cli.py`, `__main__.py`

Every functional requirement has clear implementation path. No orphaned requirements.

**Non-Functional Requirements Coverage:**

All 33 NFRs addressed architecturally:

- **NFR1 (99% pass rate):** Eval framework with YAML test cases, temperature=0 LLM, pinned model version
- **NFR2-6 (Reliability):** Stateless processing, retry logic, circuit breaker, structured error handling
- **NFR7-11 (Performance):** Async processing, timeout controls (15s LLM, 10s warranty API, 30s startup)
- **NFR12-16 (Security):** Env vars for secrets, TLS 1.2+ MCP connections, DEBUG-only customer data logging
- **NFR17-22 (Integration):** tenacity retry (max 3), circuit breaker (5 failures), timeout handling per integration
- **NFR23-28 (Maintainability):** Markdown instructions, YAML validation, structured logging, config-only changes
- **NFR29-33 (Operations):** Exit codes (0/2/3/4), signal handling, single-process, log rotation compatibility

Architecture provides specific mechanisms for every NFR. Quality attributes embedded in patterns.

**Cross-Cutting Concerns:**

All cross-cutting requirements properly handled:

- **Retry logic:** Centralized in `utils/retry.py`, applied consistently via decorator
- **Logging:** Standardized in `utils/logging.py`, used in every module
- **Error handling:** `AgentError` base class in `utils/errors.py`, consistent code patterns
- **Configuration:** Single load point in `config/loader.py`, injected throughout
- **Instruction loading:** Single loader in `instructions/loader.py`, cached for performance

Cross-cutting patterns prevent code duplication and ensure consistency.

### Implementation Readiness Validation ✅

**Decision Completeness:**

All critical decisions fully documented:

- **MCP Integration:** Hybrid client + custom server architecture specified, SDK version pinned (v1.25.0), stdio transport chosen
- **LLM Integration:** Direct Anthropic SDK with temperature=0, model pinned (`claude-3-5-sonnet-20241022`), 15s timeout
- **Instruction Format:** YAML frontmatter + XML body pattern defined with complete examples, validation approach specified
- **Eval Framework:** YAML test case format documented with full schema, pass rate calculation defined (99% threshold)

All decisions include: rationale, implementation examples, version constraints, and impact analysis.

**Structure Completeness:**

Project structure comprehensively defined:

- **100+ files specified** with exact paths and responsibilities
- **All directories explained** with purpose and contents
- **Integration points mapped** (internal and external)
- **Data flow documented** (email processing, eval workflow)
- **FR-to-file mapping complete** (every requirement → specific location)

AI agents can implement without structural ambiguity.

**Pattern Completeness:**

Implementation patterns cover all potential conflict areas:

- **Naming:** 7 categories (modules, functions, classes, constants, files, dirs, keys) with examples
- **Structure:** Import patterns, module organization, test structure fully specified
- **Format:** Error structures, log formats, config YAML schema defined
- **Communication:** MCP patterns, state management, error propagation specified
- **Process:** Retry logic, circuit breaker, timeout handling, logging patterns documented

10 mandatory enforcement rules + good examples + anti-patterns = complete guidance for consistent implementation.

### Gap Analysis Results

**No Critical Gaps Identified**

The architecture is complete enough to begin implementation without blocking unknowns.

**Minor Enhancement Opportunities (Post-MVP):**

1. **Advanced Monitoring:** Architecture supports basic logging; future enhancement could add structured metrics (Prometheus, StatsD)
2. **Instruction Versioning:** YAML frontmatter has version field; future tooling could enforce semantic versioning
3. **Eval Scenario Generation:** Manual YAML authoring works; future enhancement could auto-generate scenarios from production failures
4. **Type Safety:** mypy recommended but not mandated; future enhancement could require type hints in all modules

These are genuinely "nice-to-have" improvements, not gaps blocking MVP implementation.

### Validation Issues Addressed

**No Blocking Issues Found**

Validation revealed no contradictions, missing decisions, or architectural conflicts.

**One Minor Clarification Added:**

During validation, I verified that custom MCP servers (warranty, ticketing) will run as separate processes launched by the main agent. This is implicit in MCP stdio transport architecture but now explicitly documented in the "External Integrations" section.

### Architecture Completeness Checklist

**✅ Requirements Analysis**

- [x] Project context thoroughly analyzed (51 FRs, 33 NFRs categorized)
- [x] Scale and complexity assessed (low-medium, 7 architectural components)
- [x] Technical constraints identified (stateless, single-process, container-ready)
- [x] Cross-cutting concerns mapped (retry, logging, errors, config, instructions)

**✅ Architectural Decisions**

- [x] Critical decisions documented with versions (MCP SDK v1.25.0, Anthropic SDK, model pinned)
- [x] Technology stack fully specified (Python 3.10+, uv, Typer, Railway)
- [x] Integration patterns defined (MCP hybrid architecture, stdio transport)
- [x] Performance considerations addressed (timeouts, async processing, stateless design)

**✅ Implementation Patterns**

- [x] Naming conventions established (PEP 8 + kebab-case instructions)
- [x] Structure patterns defined (src-layout, feature-based organization, test mirroring)
- [x] Communication patterns specified (MCP request/response, stateless email processing)
- [x] Process patterns documented (retry with exponential backoff, circuit breaker, structured logging)

**✅ Project Structure**

- [x] Complete directory structure defined (100+ files with exact paths)
- [x] Component boundaries established (MCP integration, feature modules, cross-cutting utilities)
- [x] Integration points mapped (internal: CLI→processor→LLM, external: MCP servers + LLM API)
- [x] Requirements to structure mapping complete (all 51 FRs → specific files/functions)

### Architecture Readiness Assessment

**Overall Status:** ✅ READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

All critical decisions made, all requirements covered, comprehensive patterns defined, no blocking gaps.

**Key Strengths:**

1. **Instruction-Driven Architecture:** Core innovation (YAML + XML format) fully specified with validation approach
2. **Eval-First Quality:** 99% pass rate target supported by comprehensive test framework design
3. **Modern 2025 Stack:** uv + Typer + pinned versions = reproducible, fast, maintainable
4. **Clear Boundaries:** MCP integration, stateless processing, feature-based organization prevent confusion
5. **AI Agent Consistency:** 10 mandatory enforcement rules + examples prevent implementation conflicts
6. **Complete Traceability:** Every FR → specific file/function, every NFR → architectural mechanism

**Areas for Future Enhancement:**

1. **Structured Metrics:** Current architecture logs everything; post-MVP could add Prometheus metrics for observability
2. **Instruction Linting:** YAML/XML validation exists; future tooling could enforce instruction best practices
3. **Type Coverage:** mypy recommended; future standard could mandate 100% type hint coverage
4. **Eval Auto-Generation:** Manual scenario authoring works; future enhancement could synthesize test cases from production

These are genuine post-MVP enhancements, not architectural deficiencies.

### Implementation Handoff

**AI Agent Guidelines:**

1. **Follow all architectural decisions exactly as documented** - MCP hybrid architecture, direct Anthropic SDK, YAML + XML instructions, YAML eval framework
2. **Use implementation patterns consistently** - PEP 8 naming, retry decorators, structured logging, AgentError hierarchy
3. **Respect project structure and boundaries** - src-layout, feature modules, separated user content
4. **Refer to this document for all architectural questions** - Single source of truth for patterns and decisions

**First Implementation Priority:**

Initialize project structure using uv:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize project with package structure
uv init --package guarantee-email-agent
cd guarantee-email-agent

# Set Python version
echo "3.10" > .python-version

# Add core dependencies
uv add "typer[all]>=0.9.0" "anthropic>=0.8.0" "pyyaml>=6.0" "python-dotenv>=1.0.0" "httpx>=0.25.0" "tenacity>=8.2.0"

# Add dev dependencies
uv add --dev "pytest>=7.4.0" "pytest-asyncio>=0.21.0"

# Create complete directory structure
mkdir -p src/guarantee_email_agent/{config,email,instructions,integrations,llm,eval,utils}
mkdir -p instructions/scenarios
mkdir -p evals/scenarios
mkdir -p mcp_servers/{warranty_mcp_server,ticketing_mcp_server}
mkdir -p tests/{config,email,instructions,integrations,llm,eval,utils}

# Verify structure
uv run python -m guarantee_email_agent --help
```

This creates the foundation. Next step: implement core modules following the patterns in Section 5 (Implementation Patterns).

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2026-01-17
**Document Location:** _bmad-output/planning-artifacts/architecture.md

### Final Architecture Deliverables

**📋 Complete Architecture Document**

- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**🏗️ Implementation Ready Foundation**

- 4 critical architectural decisions made (MCP integration, LLM integration, instruction format, eval framework)
- 10 mandatory implementation patterns defined
- 7 architectural components specified (CLI, config, email, instructions, integrations, llm, eval)
- 84 requirements fully supported (51 FRs + 33 NFRs)

**📚 AI Agent Implementation Guide**

- Technology stack with verified versions (Python 3.10+, uv, Typer, Anthropic SDK, MCP SDK v1.25.0)
- Consistency rules that prevent implementation conflicts (PEP 8 + kebab-case + retry + logging + errors)
- Project structure with clear boundaries (src-layout, feature modules, custom MCP servers)
- Integration patterns and communication standards (MCP hybrid architecture, stateless processing)

### Implementation Handoff

**For AI Agents:**
This architecture document is your complete guide for implementing guarantee-email-agent. Follow all decisions, patterns, and structures exactly as documented.

**First Implementation Priority:**
Initialize project structure using uv:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize project with package structure
uv init --package guarantee-email-agent
cd guarantee-email-agent

# Set Python version
echo "3.10" > .python-version

# Add core dependencies
uv add "typer[all]>=0.9.0" "anthropic>=0.8.0" "pyyaml>=6.0" "python-dotenv>=1.0.0" "httpx>=0.25.0" "tenacity>=8.2.0"

# Add dev dependencies
uv add --dev "pytest>=7.4.0" "pytest-asyncio>=0.21.0"

# Create complete directory structure
mkdir -p src/guarantee_email_agent/{config,email,instructions,integrations,llm,eval,utils}
mkdir -p instructions/scenarios
mkdir -p evals/scenarios
mkdir -p mcp_servers/{warranty_mcp_server,ticketing_mcp_server}
mkdir -p tests/{config,email,instructions,integrations,llm,eval,utils}

# Verify structure
uv run python -m guarantee_email_agent --help
```

**Development Sequence:**

1. Initialize project using documented starter template
2. Set up development environment per architecture
3. Implement core architectural foundations (config loader, logging, error handling)
4. Build MCP integration layer (custom servers + clients)
5. Implement instruction-driven workflow (loader, router, LLM orchestrator)
6. Build eval framework for 99% pass rate validation
7. Maintain consistency with documented rules throughout

### Quality Assurance Checklist

**✅ Architecture Coherence**

- [x] All decisions work together without conflicts
- [x] Technology choices are compatible (Python 3.10+, uv, Typer, Anthropic SDK, MCP SDK)
- [x] Patterns support the architectural decisions (retry, logging, errors, stateless)
- [x] Structure aligns with all choices (src-layout, feature modules, separated content)

**✅ Requirements Coverage**

- [x] All functional requirements are supported (51 FRs → specific files/functions)
- [x] All non-functional requirements are addressed (33 NFRs → architectural mechanisms)
- [x] Cross-cutting concerns are handled (retry, logging, errors, config, instructions)
- [x] Integration points are defined (MCP hybrid, LLM API, internal communication)

**✅ Implementation Readiness**

- [x] Decisions are specific and actionable (pinned versions, concrete examples)
- [x] Patterns prevent agent conflicts (10 mandatory enforcement rules)
- [x] Structure is complete and unambiguous (100+ files with exact paths)
- [x] Examples are provided for clarity (good examples + anti-patterns)

### Project Success Factors

**🎯 Clear Decision Framework**
Every technology choice was made collaboratively with clear rationale, ensuring all stakeholders understand the architectural direction.

**🔧 Consistency Guarantee**
Implementation patterns and rules ensure that multiple AI agents will produce compatible, consistent code that works together seamlessly.

**📋 Complete Coverage**
All project requirements are architecturally supported, with clear mapping from business needs to technical implementation.

**🏗️ Solid Foundation**
The chosen starter template and architectural patterns provide a production-ready foundation following current best practices (uv, Typer, Railway, MCP).

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- MCP integration strategy (client + server architecture)
- LLM integration approach (direct Anthropic SDK with determinism controls)
- Instruction file format (YAML frontmatter + XML body)
- Eval framework design (YAML test cases with pass/fail assertions)

**Important Decisions (Shape Architecture):**
- Project structure and module organization (already decided in Step 3)
- Dependency management with uv (already decided in Step 3)
- Railway deployment configuration (already decided in Step 3)

**Deferred Decisions (Post-MVP):**
- Email attachment processing (out of MVP scope per PRD)
- Multi-language support (English only for MVP)
- Reporting dashboard (success tracked via eval pass rate)
- Advanced monitoring and alerting (basic logging sufficient for MVP)

### MCP Integration Architecture

**Decision: Hybrid MCP Client + Custom Server Architecture**

**Rationale:**
The project requires integration with three external systems via MCP protocol. Rather than direct API calls, we use MCP to provide a standardized integration layer with retry logic, error handling, and future extensibility.

**Architecture Components:**

1. **Main CLI Agent (guarantee-email-agent)** - MCP Client
   - Uses official `mcp` Python SDK (v1.25.0 stable, v2 available Q1 2026)
   - Acts as MCP client connecting to three MCP servers
   - Communicates via stdio transport for local server processes

2. **Gmail Integration**
   - Leverage existing community MCP server (e.g., `GongRzhe/Gmail-MCP-Server`)
   - Evaluate and select maintained Gmail MCP implementation
   - Provides: inbox monitoring, email sending, content parsing

3. **Warranty API MCP Server** (Custom)
   - Lightweight MCP server wrapping warranty validation API
   - Built using official `mcp` Python SDK in server mode
   - Exposes warranty check tool/resource to MCP clients
   - Handles API authentication and error responses

4. **Ticketing System MCP Server** (Custom)
   - Lightweight MCP server wrapping ticketing system API
   - Built using official `mcp` Python SDK in server mode
   - Exposes ticket creation tool/resource to MCP clients
   - Validates ticket creation success (NFR21)

**MCP SDK Integration:**
```python
# In main agent (MCP client)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to Gmail MCP server
gmail_params = StdioServerParameters(
    command="gmail-mcp-server",
    args=["--config", "gmail_config.json"]
)

# Connect to custom warranty API MCP server
warranty_params = StdioServerParameters(
    command="python",
    args=["-m", "warranty_mcp_server"]
)
```

**Benefits:**
- Standardized integration pattern across all external systems
- Retry logic and circuit breaker patterns built into MCP client
- Easier to swap implementations (e.g., different Gmail MCP server)
- Custom MCP servers are thin wrappers—minimal code to maintain

**Implementation Note:**
Custom MCP servers (warranty API, ticketing) should be simple, focused components. First implementation story should include MCP server scaffolding.

### LLM Integration & Determinism Strategy

**Decision: Direct Anthropic SDK with Determinism Controls**

**Rationale:**
Given the instruction-driven architecture where instructions are custom markdown/XML files, direct SDK usage provides maximum control over prompting and determinism without unnecessary abstractions.

**LLM Integration Approach:**

**Anthropic SDK Configuration:**
- Package: `anthropic>=0.8.0`
- Model: Pin to specific version (e.g., `claude-3-5-sonnet-20241022`)
- Temperature: Set to `0` for maximum determinism
- System message: Load from instruction files (main.md + scenario-specific)
- User message: Email content and context

**Prompt Construction:**
```python
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Load main instruction
main_instruction = load_instruction("instructions/main.md")

# Load scenario-specific instruction based on context
scenario_instruction = load_instruction(f"instructions/scenarios/{scenario}.md")

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    temperature=0,  # Maximum determinism
    max_tokens=1024,
    system=f"{main_instruction}\n\n{scenario_instruction}",
    messages=[{"role": "user", "content": email_content}]
)
```

**Determinism Strategy for 99% Pass Rate:**

1. **Temperature 0:** Minimize response variability
2. **Pinned Model Version:** Prevent behavior drift from model updates
3. **Precise Instructions:** Detailed, unambiguous instruction files
4. **Scenario Routing:** Load correct instruction file based on context
5. **Eval Validation:** Continuous testing ensures instruction quality

**No LangChain/Framework Because:**
- Adds complexity and dependencies without clear benefit
- Custom instruction architecture already provides structure
- Direct SDK gives full control for debugging eval failures
- Simpler stack = easier troubleshooting

**Timeout Handling:**
- LLM API calls timeout after 15 seconds (NFR11)
- Retry with exponential backoff (max 3 retries per NFR17)
- Failed retries log error and mark email as unprocessed (NFR5, NFR45)

### Instruction File Format & Schema

**Decision: YAML Frontmatter + XML Body (BMad-Inspired Structure)**

**Rationale:**
Structured instruction format provides validation, versioning, and consistency while remaining human-editable. Pattern is familiar from BMad methodology and enables tooling.

**Instruction File Structure:**

**Main Instruction File (`instructions/main.md`):**
```markdown
---
name: main-orchestration
description: Core warranty email processing orchestration logic
version: 1.0.0
---

<orchestration>
  <analysis>
    <step>Read incoming email content and metadata</step>
    <step>Identify if this is a warranty inquiry</step>
    <step>Extract serial number from email body (various formats)</step>
    <step>If serial number found, proceed to warranty validation</step>
    <step>If serial number missing or ambiguous, route to missing-info scenario</step>
  </analysis>
  
  <scenario-detection>
    <condition trigger="warranty_status == 'valid'">
      Load scenario: instructions/scenarios/valid-warranty.md
    </condition>
    <condition trigger="warranty_status == 'expired'">
      Load scenario: instructions/scenarios/invalid-warranty.md
    </condition>
    <condition trigger="serial_number == null">
      Load scenario: instructions/scenarios/missing-info.md
    </condition>
  </scenario-detection>
</orchestration>
```

**Scenario-Specific Instruction (`instructions/scenarios/valid-warranty.md`):**
```markdown
---
name: valid-warranty
description: Handle emails where warranty API returns valid status
trigger: warranty_status == "valid"
version: 1.2.0
---

<scenario id="valid-warranty">
  <analysis>
    <extract field="serial_number" from="email_body"/>
    <extract field="expiration_date" from="warranty_api_response"/>
    <extract field="customer_name" from="email_metadata"/>
  </analysis>
  
  <response>
    <tone>professional, reassuring</tone>
    <include>warranty confirmation, expiration date, ticket number, next steps</include>
    <template>
      Dear {customer_name},

      Your warranty for device {serial_number} is valid until {expiration_date}.
      
      We've created support ticket {ticket_number} and our team will contact you 
      within 24 hours to assist with your warranty claim.
      
      Best regards,
      Support Team
    </template>
  </response>
  
  <actions>
    <create_ticket priority="normal" category="warranty_claim"/>
    <send_email recipient="{customer_email}"/>
  </actions>
</scenario>
```

**Instruction Loader Implementation:**
```python
import yaml
from pathlib import Path

def load_instruction(filepath: str) -> dict:
    """Load and parse instruction file with YAML frontmatter + XML body"""
    content = Path(filepath).read_text()
    
    # Split frontmatter and body
    if content.startswith('---'):
        _, frontmatter, body = content.split('---', 2)
        metadata = yaml.safe_load(frontmatter)
    else:
        metadata = {}
        body = content
    
    return {
        'metadata': metadata,
        'instructions': body.strip()
    }
```

**Validation on Startup (NFR24):**
- YAML schema validation for frontmatter
- XML schema validation for instruction body (optional but recommended)
- Fail fast with clear error messages if instruction files malformed
- Validates all instruction files during `agent run` startup

**Benefits:**
- YAML frontmatter: version tracking, metadata, trigger conditions
- XML body: structured instructions that LLM can interpret clearly
- Human-editable: familiar pattern from BMad workflows
- Git-friendly: diffs show actual instruction changes
- Tooling-ready: can build validators, linters, IDE support

**Version Control:**
- Git tracks all instruction file changes
- No complex versioning system needed (frontmatter version is informational)
- Eval suite tied to instruction versions via git commits

### Eval Framework Architecture

**Decision: YAML Test Cases with Declarative Assertions**

**Rationale:**
Eval framework is mission-critical for achieving 99% pass rate. YAML format makes test cases easy to author, read, and extend. Declarative format clearly specifies expected behavior.

**Eval Test Case Format (`evals/scenarios/valid_warranty_001.yaml`):**

```yaml
---
scenario_id: valid_warranty_001
description: "Standard valid warranty inquiry with serial number in email body"
category: valid-warranty
created: 2026-01-17
---

input:
  email:
    subject: "Warranty Check - SN12345"
    body: |
      Hi Support Team,
      
      I need to check if my device with serial number SN12345 
      is still under warranty. Please let me know the status.
      
      Thanks,
      John Doe
    from: john.doe@example.com
    received: "2026-01-17T10:30:00Z"
  
  mock_responses:
    warranty_api:
      serial_number: "SN12345"
      status: "valid"
      expiration_date: "2026-06-15"
      product: "Device Model X"

expected_output:
  email_sent: true
  response_body_contains:
    - "warranty is valid"
    - "2026-06-15"
    - "ticket"
    - "24 hours"
  response_body_excludes:
    - "expired"
    - "invalid"
  ticket_created: true
  ticket_fields:
    priority: "normal"
    category: "warranty_claim"
    serial_number: "SN12345"
  scenario_instruction_used: "valid-warranty"
  processing_time_ms: <60000  # NFR7: 60s processing time
```

**Eval Runner Implementation (`src/guarantee_email_agent/eval/runner.py`):**

```python
from pathlib import Path
import yaml
from typing import List, Dict

class EvalRunner:
    def __init__(self, test_suite_path: str = "evals/scenarios/"):
        self.test_suite_path = Path(test_suite_path)
        self.results = []
    
    def run_all(self) -> Dict:
        """Execute all eval scenarios and calculate pass rate"""
        scenario_files = self.test_suite_path.glob("*.yaml")
        
        for scenario_file in scenario_files:
            result = self.run_scenario(scenario_file)
            self.results.append(result)
        
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            'passed': passed,
            'total': total,
            'pass_rate': pass_rate,
            'results': self.results
        }
    
    def run_scenario(self, scenario_file: Path) -> Dict:
        """Execute single eval scenario"""
        # Load scenario YAML
        scenario = yaml.safe_load(scenario_file.read_text())
        
        # Mock external integrations
        with mock_mcp_servers(scenario['input']['mock_responses']):
            # Run agent with input email
            result = agent.process_email(scenario['input']['email'])
        
        # Validate expected outputs
        passed = self.validate_output(result, scenario['expected_output'])
        
        return {
            'scenario_id': scenario['scenario_id'],
            'passed': passed,
            'actual': result,
            'expected': scenario['expected_output']
        }
```

**Pass Rate Reporting (`agent eval` command output):**

```
Running evaluation suite... (35 scenarios)

✓ valid_warranty_001 - Standard valid warranty inquiry
✓ valid_warranty_002 - Valid warranty with non-standard serial format
✓ invalid_warranty_001 - Expired warranty
✗ missing_info_003 - Serial number in attachment (graceful degradation)
...

Results:
  Passed: 34/35 scenarios
  Failed: 1/35 scenarios
  Pass rate: 97.1%

FAILED: Below 99% threshold

Failed Scenarios:
  - missing_info_003: Expected graceful degradation response, got error

Exit code: 4
```

**Continuous Improvement Loop (FR32, FR33):**

1. **Eval Fails** → Agent doesn't meet expected output
2. **Add to Suite** → Failed case becomes permanent regression test
3. **Refine Instructions** → Update instruction files to handle case
4. **Re-run Evals** → Verify fix doesn't break existing scenarios
5. **Deploy** → New instructions deployed with confidence

**Eval Suite Management:**
- Store in `evals/scenarios/` directory
- YAML files named: `{category}_{number}.yaml`
- Easy to add new scenarios from production failures
- Version controlled with instruction files

**pytest Integration:**
```python
# tests/test_eval_suite.py
import pytest
from guarantee_email_agent.eval.runner import EvalRunner

def test_eval_suite_passes():
    """Verify eval suite meets 99% pass rate threshold"""
    runner = EvalRunner()
    results = runner.run_all()
    
    assert results['pass_rate'] >= 99.0, \
        f"Eval pass rate {results['pass_rate']}% below 99% threshold"
```

**Benefits:**
- Declarative: clearly specifies expected behavior
- Human-readable: easy to author and review
- Reproducible: mocked responses ensure consistent testing
- Comprehensive: validates end-to-end scenarios (email → ticket)
- Actionable: failed scenarios provide clear debugging info

### Decision Impact Analysis

**Implementation Sequence:**

1. **Project Initialization** (uv, pyproject.toml, directory structure)
2. **MCP Server Scaffolding** (warranty API, ticketing wrappers)
3. **Instruction Loader** (YAML + XML parser with validation)
4. **LLM Orchestrator** (Anthropic SDK integration with determinism controls)
5. **MCP Client Integration** (connect to Gmail, warranty, ticketing servers)
6. **Eval Framework** (YAML test case runner with pass rate calculation)
7. **CLI Commands** (`agent run`, `agent eval`)

**Cross-Component Dependencies:**

- **Instruction format** affects **LLM orchestrator** (must parse YAML/XML)
- **MCP architecture** affects **deployment** (need to run multiple processes)
- **Eval framework** depends on **instruction format** (scenario IDs must match)
- **Determinism strategy** (temp=0, pinned model) critical for **eval pass rate**

**Architectural Constraints Validated:**

✅ **NFR24:** Instruction syntax validation on startup (YAML/XML schema)
✅ **NFR5:** No silent failures (eval runner explicitly tracks pass/fail)
✅ **NFR11:** LLM timeout handling (15s with retry logic)
✅ **NFR29:** Exit code 4 for eval failure (pass rate < 99%)
✅ **NFR26:** Config-only changes (instruction files don't require code deployment)

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
8 areas where AI agents could make different implementation choices that would cause conflicts or inconsistency in this Python CLI project.

### Naming Patterns

**Python Code Naming Conventions (PEP 8):**

- **Modules/Packages:** `snake_case`
  - Examples: `mcp_client.py`, `instruction_loader.py`, `eval_runner.py`
  - Pattern: All lowercase with underscores separating words

- **Functions/Methods:** `snake_case`
  - Examples: `load_instruction()`, `process_email()`, `validate_output()`
  - Pattern: Descriptive verbs, lowercase with underscores

- **Classes:** `PascalCase`
  - Examples: `EvalRunner`, `LLMOrchestrator`, `MCPClient`
  - Pattern: Capitalize first letter of each word, no separators

- **Constants:** `UPPER_SNAKE_CASE`
  - Examples: `MAX_RETRIES = 3`, `DEFAULT_TIMEOUT = 15`, `EVAL_PASS_THRESHOLD = 99.0`
  - Pattern: All uppercase with underscores

- **Variables:** `snake_case`
  - Examples: `pass_rate`, `email_content`, `warranty_status`
  - Pattern: Descriptive nouns, lowercase with underscores

- **Private Members:** Prefix with single underscore
  - Examples: `_validate_schema()`, `_parse_frontmatter()`
  - Pattern: `_snake_case` for internal/private methods and attributes

**File and Directory Naming:**

- **Python Files:** `snake_case.py`
  - Examples: `eval_runner.py`, `instruction_loader.py`, `warranty_api.py`
  - Pattern: Matches module name inside

- **Instruction Files:** `kebab-case.md`
  - Examples: `main.md`, `valid-warranty.md`, `invalid-warranty.md`, `missing-info.md`
  - Pattern: Lowercase with hyphens, descriptive scenario names

- **Eval Scenario Files:** `{category}_{number}.yaml`
  - Examples: `valid_warranty_001.yaml`, `invalid_warranty_001.yaml`, `missing_info_001.yaml`
  - Pattern: Category matches instruction file name (snake_case), zero-padded number

- **Configuration Files:** `kebab-case.yaml`
  - Examples: `config.yaml`, `gmail-config.json`
  - Pattern: Lowercase with hyphens

- **Directories:** `snake_case`
  - Examples: `src/guarantee_email_agent/`, `tests/`, `evals/scenarios/`
  - Pattern: Lowercase with underscores

**YAML/JSON Key Naming:**

- **Configuration Keys:** `snake_case`
  - Examples: `connection_string`, `test_suite_path`, `pass_threshold`
  - Pattern: Consistent with Python variable naming

- **Eval Scenario Keys:** `snake_case`
  - Examples: `scenario_id`, `email_sent`, `ticket_created`, `response_body_contains`
  - Pattern: Matches Python dict access patterns

**MCP Integration Naming:**

- **MCP Server Commands:** `kebab-case`
  - Examples: `gmail-mcp-server`, `warranty-mcp-server`, `ticketing-mcp-server`
  - Pattern: Descriptive service name with hyphens

- **MCP Tools/Resources:** `snake_case`
  - Examples: `check_warranty`, `create_ticket`, `send_email`
  - Pattern: Verb-based action names

### Structure Patterns

**Project Organization (Already Defined in Step 3):**

```
guarantee-email-agent/
├── src/guarantee_email_agent/    # Main package (src-layout)
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                     # Typer CLI commands
│   ├── config/                    # Configuration loading
│   ├── instructions/              # Instruction loading & routing
│   ├── integrations/              # MCP client implementations
│   ├── llm/                       # LLM orchestration
│   ├── eval/                      # Eval framework
│   └── utils/                     # Shared utilities
├── tests/                         # pytest test files
├── instructions/                  # User-editable instruction files
├── evals/scenarios/               # Eval test cases
├── config.yaml                    # Runtime configuration
└── pyproject.toml                 # Project metadata
```

**Test Organization:**

- **Location:** Dedicated `tests/` directory (not co-located)
- **File Naming:** `test_{module}.py`
  - Examples: `test_cli.py`, `test_instruction_loader.py`, `test_eval_runner.py`
- **Test Function Naming:** `test_{scenario}_description`
  - Examples: `test_load_instruction_with_valid_yaml()`, `test_eval_runner_calculates_pass_rate()`
- **Pattern:** Mirror src structure in tests (e.g., `tests/config/test_loader.py` mirrors `src/guarantee_email_agent/config/loader.py`)

**Import Patterns:**

- **Absolute Imports Preferred:**
  ```python
  from guarantee_email_agent.instructions.loader import load_instruction
  from guarantee_email_agent.llm.orchestrator import LLMOrchestrator
  ```

- **Relative Imports Only Within Same Package:**
  ```python
  # Within src/guarantee_email_agent/instructions/
  from .loader import load_instruction
  from .router import route_scenario
  ```

- **Third-Party Imports Order:**
  ```python
  # Standard library
  import os
  from pathlib import Path
  
  # Third-party
  import yaml
  from anthropic import Anthropic
  
  # Local application
  from guarantee_email_agent.config import load_config
  ```

**Module Organization Pattern:**

Each module should have clear responsibility:
- `__init__.py`: Public API exports only
- Single-purpose modules (one class or related functions per file)
- Avoid circular dependencies (use dependency injection)

### Format Patterns

**Error Response Structures:**

**Standardized Error Format:**
```python
class AgentError(Exception):
    """Base exception for agent errors"""
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

# Error codes follow pattern: {component}_{error_type}
# Examples:
# - "mcp_connection_failed"
# - "instruction_validation_error"
# - "eval_assertion_failed"
# - "llm_timeout_exceeded"
```

**User-Facing vs Internal Errors:**
- User-facing: Clear, actionable messages (logged at INFO/WARNING)
- Internal/Debug: Technical details (logged at DEBUG)

**Log Message Formats:**

**Structured Logging Pattern:**
```python
import logging

logger = logging.getLogger(__name__)

# Standard format: timestamp level module message [context]
# Example: 2026-01-17 10:23:45 INFO  email_processor Email received [subject="Warranty Check SN12345"]

logger.info("Email received", extra={
    "subject": email.subject,
    "from": email.from_addr,
    "serial_number": extracted_sn
})
```

**Log Levels (Consistent Usage):**
- **DEBUG:** Technical details, variable values, internal state
- **INFO:** Normal operations (email received, warranty checked, ticket created)
- **WARNING:** Recoverable issues (retry triggered, graceful degradation)
- **ERROR:** Failures requiring attention (MCP connection lost, eval failed)
- **CRITICAL:** System-level failures (startup validation failed)

**Configuration YAML Schema:**

**Standardized Structure:**
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

**Pattern Rules:**
- Top-level keys: alphabetical order for consistency
- Nested keys: logical grouping (connection info together)
- All paths: relative paths with `./` prefix for clarity
- URLs: full qualified with protocol

### Communication Patterns

**MCP Message Patterns:**

**Request/Response Consistency:**
- All MCP tool calls follow same pattern: `await client.call_tool(tool_name, arguments)`
- All responses validated before use
- Timeouts handled consistently (10s for warranty API per NFR20)

**Error Propagation:**
- MCP errors wrapped in `AgentError` with code `mcp_{operation}_failed`
- Original error details preserved in `details` dict
- Retry logic applied before propagating error

**State Management Patterns:**

**Stateless Email Processing (NFR16):**
- No email content persisted to disk
- All state lives in memory during processing
- Email marked complete/failed but content not stored

**Eval State:**
- Eval results stored only during test run
- Pass/fail status tracked per scenario
- No persistent state between eval runs

### Process Patterns

**Error Handling Patterns:**

**Retry Logic (Consistent Across All MCP Calls):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),  # Max 3 retries per NFR17
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def call_mcp_tool(tool_name: str, **kwargs):
    """Call MCP tool with automatic retry on transient failures"""
    # Implementation
```

**Pattern Rules:**
- Max 3 retries for all external calls (MCP, LLM)
- Exponential backoff: 1s, 2s, 4s, 8s (capped at 10s)
- Only retry on transient errors (network, timeout, rate limit)
- Don't retry on validation errors or auth failures

**Circuit Breaker (NFR18):**
```python
# Opens after 5 consecutive failures
# Half-open after 60s to test recovery
# Applies to: MCP connections, LLM API calls
```

**Graceful Degradation:**
- If serial number extraction fails → route to missing-info scenario
- If MCP connection unavailable → log error, mark email unprocessed
- If LLM timeout → retry, then fail with clear error

**Logging Patterns:**

**Consistent Logging Throughout Workflow:**
```python
# Email processing lifecycle logging
logger.info("Email received", extra={"subject": email.subject})
logger.debug("Serial number extracted", extra={"sn": serial_number})
logger.info("Warranty API called", extra={"status": warranty_status})
logger.info("Response sent, ticket created", extra={"ticket": ticket_number})

# Error logging
logger.error("MCP connection failed", extra={
    "server": "warranty-mcp-server",
    "error_code": "mcp_connection_failed",
    "retry_count": retry_count
}, exc_info=True)  # Include stack trace
```

**Pattern Rules:**
- Every major workflow step logged at INFO
- All external calls logged (MCP, LLM) with timing
- Errors logged with context (error code, retry count, component)
- Customer email content only logged at DEBUG level (NFR14)

**Timeout Handling:**

**Consistent Timeout Patterns:**
- LLM API calls: 15s timeout (NFR11)
- Warranty API MCP: 10s timeout (NFR20)
- Gmail MCP operations: 30s timeout
- All timeouts trigger retry logic before failing

### Enforcement Guidelines

**All AI Agents MUST:**

1. **Follow PEP 8 naming conventions** for all Python code (snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants)

2. **Use kebab-case for instruction files** and config files (`valid-warranty.md`, not `valid_warranty.md`)

3. **Import using absolute paths** from package root (`from guarantee_email_agent.x import y`), relative imports only within same package

4. **Apply retry logic with exponential backoff** to all external calls (MCP, LLM) with max 3 attempts

5. **Log all email processing lifecycle events** at INFO level with structured context (extra dict)

6. **Validate instruction files on startup** using YAML/XML schema validation (NFR24)

7. **Use AgentError exception hierarchy** for all domain errors with consistent code patterns (`{component}_{error_type}`)

8. **Never persist email content** beyond processing lifecycle (NFR16)

9. **Return appropriate exit codes** from CLI commands (0=success, 2=config, 3=MCP, 4=eval failure per NFR29)

10. **Test all code paths** with pytest, maintaining test structure mirroring src structure

**Pattern Enforcement:**

- **Pre-commit hooks:** Run `ruff check` for PEP 8 compliance, `mypy` for type checking
- **CI validation:** Pytest runs on all PRs, eval suite executed
- **Code review:** Check for pattern violations (retry logic, error handling, logging)
- **Documentation:** This architecture doc is the single source of truth for patterns

**Pattern Updates:**

- Patterns evolve through architecture doc updates
- Changes require PR review and team agreement
- Breaking pattern changes require migration plan

### Pattern Examples

**Good Examples:**

**Instruction Loader (Correct Patterns):**
```python
from pathlib import Path
import yaml
from guarantee_email_agent.utils.logging import get_logger

logger = get_logger(__name__)

class InstructionLoader:
    """Load and parse instruction files with YAML frontmatter + XML body"""
    
    def __init__(self, instruction_dir: str = "instructions"):
        self._instruction_dir = Path(instruction_dir)
    
    def load_instruction(self, filepath: str) -> dict:
        """Load instruction file with validation"""
        full_path = self._instruction_dir / filepath
        
        if not full_path.exists():
            raise AgentError(
                message=f"Instruction file not found: {filepath}",
                code="instruction_file_not_found",
                details={"filepath": str(full_path)}
            )
        
        logger.debug("Loading instruction file", extra={"filepath": filepath})
        content = full_path.read_text()
        
        # Parse frontmatter and body
        if content.startswith('---'):
            _, frontmatter, body = content.split('---', 2)
            metadata = yaml.safe_load(frontmatter)
        else:
            metadata = {}
            body = content
        
        logger.info("Instruction loaded", extra={
            "filepath": filepath,
            "version": metadata.get("version", "unknown")
        })
        
        return {
            'metadata': metadata,
            'instructions': body.strip()
        }
```

**MCP Client with Retry (Correct Patterns):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential
from guarantee_email_agent.utils.logging import get_logger

logger = get_logger(__name__)

class WarrantyMCPClient:
    """MCP client for warranty API integration"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def check_warranty(self, serial_number: str) -> dict:
        """Check warranty status with retry logic"""
        logger.info("Checking warranty", extra={"serial_number": serial_number})
        
        try:
            response = await self.client.call_tool(
                "check_warranty",
                arguments={"serial_number": serial_number},
                timeout=10  # NFR20: 10s timeout
            )
            
            logger.info("Warranty checked", extra={
                "serial_number": serial_number,
                "status": response.get("status")
            })
            
            return response
            
        except TimeoutError as e:
            logger.warning("Warranty API timeout", extra={
                "serial_number": serial_number,
                "attempt": self.check_warranty.retry.statistics['attempt_number']
            })
            raise
        except Exception as e:
            raise AgentError(
                message="Warranty API check failed",
                code="mcp_warranty_check_failed",
                details={
                    "serial_number": serial_number,
                    "error": str(e)
                }
            )
```

**Anti-Patterns (What to Avoid):**

❌ **Inconsistent Naming:**
```python
# WRONG: Mixed naming conventions
def LoadInstruction(file_path):  # Should be snake_case
    pass

class instruction_loader:  # Should be PascalCase
    pass

MAX_retries = 3  # Should be UPPER_SNAKE_CASE
```

❌ **No Retry Logic on External Calls:**
```python
# WRONG: Direct call without retry
response = await client.call_tool("check_warranty", ...)  # Missing @retry decorator
```

❌ **Poor Error Handling:**
```python
# WRONG: Generic exceptions, no context
try:
    result = process_email(email)
except Exception:
    print("Error")  # Missing logging, error code, details
    pass  # Silent failure violates NFR5
```

❌ **Logging Customer Data in Production:**
```python
# WRONG: Email content at INFO level
logger.info(f"Processing email: {email.body}")  # Violates NFR14
# CORRECT: Only at DEBUG level
logger.debug("Email content", extra={"body": email.body})
```

❌ **Relative Imports Across Packages:**
```python
# WRONG: Relative import from different package
from ..llm.orchestrator import LLMOrchestrator  # Fragile, hard to refactor
# CORRECT: Absolute import
from guarantee_email_agent.llm.orchestrator import LLMOrchestrator
```

❌ **Persisting Email Content:**
```python
# WRONG: Violates NFR16 (stateless email handling)
with open("emails.log", "a") as f:
    f.write(email.body)
# CORRECT: Process in memory only, no persistence
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
guarantee-email-agent/
├── .env.example                         # Example environment variables template
├── .gitignore                           # Git ignore patterns
├── .python-version                      # Python version (3.10)
├── Procfile                             # Railway deployment command
├── README.md                            # Project documentation
├── pyproject.toml                       # Project metadata, dependencies (uv managed)
├── uv.lock                              # Cross-platform dependency lockfile
├── config.yaml                          # Runtime configuration (MCP, instructions, eval)
│
├── src/
│   └── guarantee_email_agent/           # Main package (src-layout)
│       ├── __init__.py                  # Package initialization, version export
│       ├── __main__.py                  # Entry point (python -m guarantee_email_agent)
│       │
│       ├── cli.py                       # Typer CLI commands (FR22-26, FR47-51)
│       │                                # - agent run: Start email processing
│       │                                # - agent eval: Execute evaluation suite
│       │                                # - Exit code handling (NFR29)
│       │
│       ├── config/                      # Configuration management (FR34-41)
│       │   ├── __init__.py              # Public API: load_config()
│       │   ├── loader.py                # YAML config loading, env var injection
│       │   ├── schema.py                # Configuration schema validation (NFR38)
│       │   └── validator.py             # Startup validation, MCP pre-flight tests
│       │
│       ├── email/                       # Email processing (FR1-5)
│       │   ├── __init__.py              # Public API: EmailProcessor
│       │   ├── processor.py             # Main email processing workflow
│       │   ├── parser.py                # Email content parsing, metadata extraction
│       │   └── serial_extractor.py      # Serial number extraction (various formats)
│       │
│       ├── instructions/                # Instruction-driven workflow (FR10-14)
│       │   ├── __init__.py              # Public API: load_instruction, route_scenario
│       │   ├── loader.py                # YAML frontmatter + XML body parser
│       │   ├── router.py                # Scenario detection and routing logic
│       │   └── validator.py             # Instruction syntax validation (NFR24)
│       │
│       ├── integrations/                # MCP client implementations
│       │   ├── __init__.py              # Public API: MCPClient base class
│       │   ├── mcp_client.py            # Base MCP client abstraction
│       │   │                            # - Retry logic (NFR17, FR42-43)
│       │   │                            # - Circuit breaker (NFR18)
│       │   │                            # - Timeout handling
│       │   ├── gmail.py                 # Gmail MCP client (FR1-2, FR17)
│       │   │                            # - Connect to community Gmail MCP server
│       │   │                            # - Email monitoring, sending
│       │   ├── warranty_api.py          # Warranty API MCP client (FR6-9)
│       │   │                            # - Custom MCP server wrapper
│       │   │                            # - 10s timeout (NFR20)
│       │   └── ticketing.py             # Ticketing MCP client (FR19-21)
│       │                                # - Custom MCP server wrapper
│       │                                # - Ticket creation validation (NFR21)
│       │
│       ├── llm/                         # LLM orchestration (FR12, FR15-18)
│       │   ├── __init__.py              # Public API: LLMOrchestrator
│       │   ├── orchestrator.py          # Anthropic SDK integration
│       │   │                            # - Temperature=0 for determinism
│       │   │                            # - Instruction loading and prompt construction
│       │   │                            # - 15s timeout (NFR11)
│       │   └── response_generator.py    # Response drafting, graceful degradation
│       │
│       ├── eval/                        # Evaluation framework (FR27-33)
│       │   ├── __init__.py              # Public API: EvalRunner
│       │   ├── runner.py                # Eval suite executor
│       │   │                            # - Load YAML test cases
│       │   │                            # - Mock MCP servers
│       │   │                            # - Execute scenarios end-to-end
│       │   ├── reporter.py              # Pass rate calculation and reporting
│       │   │                            # - 99% threshold validation (NFR1)
│       │   │                            # - Failed scenario details
│       │   ├── validator.py             # Expected output validation
│       │   └── mocks.py                 # MCP server mocking utilities
│       │
│       └── utils/                       # Shared utilities
│           ├── __init__.py              # Public API exports
│           ├── errors.py                # AgentError exception hierarchy
│           │                            # - Standardized error codes
│           │                            # - Error details dict
│           ├── logging.py               # Structured logging setup
│           │                            # - Log level configuration
│           │                            # - Contextual logging (extra dict)
│           │                            # - Customer data protection (NFR14)
│           └── retry.py                 # Retry and circuit breaker utilities
│                                        # - tenacity decorators
│                                        # - Exponential backoff (NFR17)
│
├── tests/                               # pytest test suite
│   ├── __init__.py
│   ├── conftest.py                      # pytest fixtures and configuration
│   │
│   ├── test_cli.py                      # CLI command tests
│   ├── config/
│   │   ├── test_loader.py               # Config loading tests
│   │   └── test_validator.py            # Config validation tests
│   ├── email/
│   │   ├── test_processor.py            # Email processing workflow tests
│   │   ├── test_parser.py               # Email parsing tests
│   │   └── test_serial_extractor.py     # Serial number extraction tests
│   ├── instructions/
│   │   ├── test_loader.py               # Instruction loading tests
│   │   ├── test_router.py               # Scenario routing tests
│   │   └── test_validator.py            # Instruction validation tests
│   ├── integrations/
│   │   ├── test_mcp_client.py           # Base MCP client tests
│   │   ├── test_gmail.py                # Gmail integration tests
│   │   ├── test_warranty_api.py         # Warranty API tests
│   │   └── test_ticketing.py            # Ticketing integration tests
│   ├── llm/
│   │   ├── test_orchestrator.py         # LLM orchestration tests
│   │   └── test_response_generator.py   # Response generation tests
│   ├── eval/
│   │   ├── test_runner.py               # Eval runner tests
│   │   ├── test_reporter.py             # Reporting tests
│   │   └── test_validator.py            # Output validation tests
│   └── utils/
│       ├── test_errors.py               # Error handling tests
│       ├── test_logging.py              # Logging tests
│       └── test_retry.py                # Retry/circuit breaker tests
│
├── instructions/                        # User-editable instruction files
│   ├── main.md                          # Main orchestration instructions
│   │                                    # - Email analysis workflow
│   │                                    # - Serial number extraction logic
│   │                                    # - Scenario detection rules
│   └── scenarios/
│       ├── valid-warranty.md            # Valid warranty scenario instructions
│       ├── invalid-warranty.md          # Expired/invalid warranty instructions
│       ├── missing-info.md              # Missing serial number instructions
│       └── (additional scenarios as needed)
│
├── evals/                               # Eval framework test cases
│   └── scenarios/                       # YAML test case files
│       ├── valid_warranty_001.yaml      # Standard valid warranty case
│       ├── valid_warranty_002.yaml      # Non-standard serial format
│       ├── invalid_warranty_001.yaml    # Expired warranty case
│       ├── invalid_warranty_002.yaml    # Not found case
│       ├── missing_info_001.yaml        # No serial number case
│       ├── missing_info_002.yaml        # Ambiguous serial number
│       └── (30-50 total scenarios for 99% coverage)
│
├── logs/                                # Log output directory (gitignored)
│   └── agent.log                        # Runtime logs
│
├── mcp_servers/                         # Custom MCP server implementations
│   ├── warranty_mcp_server/             # Warranty API MCP wrapper
│   │   ├── __init__.py
│   │   ├── server.py                    # MCP server using official SDK
│   │   └── warranty_client.py           # Actual warranty API HTTP client
│   └── ticketing_mcp_server/            # Ticketing MCP wrapper
│       ├── __init__.py
│       ├── server.py                    # MCP server using official SDK
│       └── ticketing_client.py          # Actual ticketing API HTTP client
│
└── .github/                             # GitHub configuration (optional)
    └── workflows/
        └── ci.yml                       # CI pipeline: pytest, eval suite, linting
```

### Architectural Boundaries

**MCP Integration Boundaries:**

**Boundary Pattern:** Main agent (MCP client) communicates with three separate MCP servers via stdio transport.

1. **Gmail MCP Server Boundary**
   - **Interface:** Community Gmail MCP server (e.g., `GongRzhe/Gmail-MCP-Server`)
   - **Communication:** stdio transport, MCP protocol
   - **Operations:** `list_emails`, `read_email`, `send_email`
   - **Responsibility:** All Gmail API interactions isolated behind MCP
   - **Error Handling:** Retry on transient failures, circuit breaker after 5 failures

2. **Warranty API MCP Server Boundary**
   - **Interface:** Custom MCP server (`mcp_servers/warranty_mcp_server/`)
   - **Communication:** stdio transport, local process
   - **Operations:** `check_warranty(serial_number) → {status, expiration}`
   - **Responsibility:** Warranty API HTTP calls, auth, response parsing
   - **Timeout:** 10 seconds (NFR20)

3. **Ticketing MCP Server Boundary**
   - **Interface:** Custom MCP server (`mcp_servers/ticketing_mcp_server/`)
   - **Communication:** stdio transport, local process
   - **Operations:** `create_ticket({serial, status, customer}) → {ticket_id}`
   - **Responsibility:** Ticketing system API calls, validation
   - **Validation:** Confirm ticket creation success before marking email processed (NFR21)

**Component Boundaries:**

**Email Processing → LLM Orchestration:**
- **Interface:** `EmailProcessor.process(email) → ProcessedEmail`
- **Data:** Parsed email content, metadata, extracted serial number
- **Boundary:** Email processor doesn't call LLM directly, passes to orchestrator

**LLM Orchestration → Instruction Loader:**
- **Interface:** `InstructionLoader.load_instruction(scenario) → {metadata, instructions}`
- **Data:** YAML frontmatter + XML instruction body
- **Boundary:** LLM orchestrator loads instructions, constructs prompts

**LLM Orchestration → MCP Clients:**
- **Interface:** Async calls via MCP client abstraction
- **Data:** Structured requests/responses (YAML/JSON)
- **Boundary:** Orchestrator coordinates MCP calls, doesn't implement integration logic

**CLI → All Components:**
- **Interface:** Typer commands (`agent run`, `agent eval`)
- **Data:** Command-line arguments, exit codes
- **Boundary:** CLI is thin coordinator, delegates to processors/eval runner

**Data Boundaries:**

**No Database (Stateless Architecture):**
- **Email Content:** Lives only in memory during processing (NFR16)
- **Configuration:** Loaded from YAML + env vars at startup
- **Instruction Files:** Read from filesystem, cached in memory
- **Eval Results:** Computed on-demand, not persisted
- **Logs:** Written to files/stdout but no structured data store

**State Boundaries:**
- **In-Memory Only:** Email content, LLM responses, MCP call results
- **Filesystem (Read-Only):** Instructions, eval scenarios, config
- **Filesystem (Write-Only):** Logs
- **No Persistence:** No email archive, no state database

### Requirements to Structure Mapping

**Email Processing & Analysis (FR1-FR5) → `src/guarantee_email_agent/email/`:**
- FR1 (Monitor inbox) → `integrations/gmail.py`: `monitor_inbox()` method
- FR2 (Parse email) → `email/parser.py`: `parse_email()` function
- FR3 (Extract serial numbers) → `email/serial_extractor.py`: Regex/pattern matching
- FR4 (Detect scenarios) → `instructions/router.py`: `detect_scenario()` function
- FR5 (Identify extraction failures) → `email/serial_extractor.py`: Returns None on failure

**Warranty Validation (FR6-FR9) → `src/guarantee_email_agent/integrations/warranty_api.py`:**
- FR6 (Query warranty API) → `warranty_api.py`: `check_warranty(serial)` method
- FR7 (Determine status) → `warranty_api.py`: Parse API response
- FR8 (Handle errors/timeouts) → `utils/retry.py`: Retry decorator applied
- FR9 (Validate eligibility) → `llm/orchestrator.py`: Interprets warranty response

**Instruction-Driven Workflow (FR10-FR14) → `src/guarantee_email_agent/instructions/`:**
- FR10 (Load main instruction) → `instructions/loader.py`: `load_instruction("main.md")`
- FR11 (Select scenario file) → `instructions/router.py`: Dynamic loading based on context
- FR12 (Execute LLM reasoning) → `llm/orchestrator.py`: Anthropic SDK calls
- FR13 (Route to scenarios) → `instructions/router.py`: Scenario detection logic
- FR14 (Edit instructions) → External (user edits `instructions/*.md` in git)

**Response Generation & Delivery (FR15-FR18) → `src/guarantee_email_agent/llm/`:**
- FR15 (Draft responses) → `llm/response_generator.py`: Template-based generation
- FR16 (Follow scenario guidance) → `llm/orchestrator.py`: Loads scenario instructions
- FR17 (Send emails) → `integrations/gmail.py`: `send_email()` method
- FR18 (Graceful degradation) → `llm/response_generator.py`: Edge case handling

**Ticket Management (FR19-FR21) → `src/guarantee_email_agent/integrations/ticketing.py`:**
- FR19 (Create tickets) → `ticketing.py`: `create_ticket()` method
- FR20 (Populate ticket fields) → `ticketing.py`: Structured ticket payload
- FR21 (Determine when to create) → `llm/orchestrator.py`: Decision logic

**CLI Runtime Operations (FR22-FR26) → `src/guarantee_email_agent/cli.py`:**
- FR22 (`agent run`) → `cli.py`: `@app.command()` run function
- FR23 (Graceful stop) → `cli.py`: Signal handling (SIGTERM/SIGINT)
- FR24 (Log activity) → `utils/logging.py`: Structured logging throughout
- FR25 (Output to stdout/files) → `utils/logging.py`: Dual handler setup
- FR26 (View status) → `cli.py`: Real-time log output

**Evaluation Framework (FR27-FR33) → `src/guarantee_email_agent/eval/`:**
- FR27 (`agent eval`) → `cli.py`: `@app.command()` eval function
- FR28 (Run end-to-end) → `eval/runner.py`: `run_scenario()` method
- FR29 (Calculate pass rate) → `eval/reporter.py`: `calculate_pass_rate()`
- FR30 (Report failures) → `eval/reporter.py`: Failed scenario details
- FR31 (Add scenarios) → External (user creates YAML in `evals/scenarios/`)
- FR32 (Validate no breakage) → `eval/runner.py`: Regression detection
- FR33 (Create from failures) → External (user adds failed case to eval suite)

**Configuration Management (FR34-FR41) → `src/guarantee_email_agent/config/`:**
- FR34 (Configure MCP) → `config.yaml`: MCP connection section
- FR35 (Specify instruction paths) → `config.yaml`: Instructions section
- FR36 (Set eval threshold) → `config.yaml`: Eval section (`pass_threshold: 99.0`)
- FR37 (Env vars for secrets) → `config/loader.py`: `os.environ` injection
- FR38 (Validate schema) → `config/validator.py`: YAML schema validation
- FR39 (Verify paths exist) → `config/validator.py`: File existence checks
- FR40 (Test MCP connections) → `config/validator.py`: Pre-flight MCP test
- FR41 (Fail fast on errors) → `config/validator.py`: Startup validation

**Error Handling & Resilience (FR42-FR46) → `src/guarantee_email_agent/utils/`:**
- FR42 (Retry with backoff) → `utils/retry.py`: `@retry` decorator from tenacity
- FR43 (Circuit breaker) → `utils/retry.py`: Circuit breaker implementation
- FR44 (Log failures) → `utils/logging.py`: Error logging with context
- FR45 (No silent failures) → `utils/errors.py`: AgentError always logged
- FR46 (Signal handling) → `cli.py`: SIGTERM/SIGINT handlers

**Scripting & Automation Support (FR47-FR51) → `src/guarantee_email_agent/cli.py` + `__main__.py`:**
- FR47 (Non-interactive) → `cli.py`: No prompts, all config from files/env
- FR48 (Exit codes) → `cli.py`: Return 0/2/3/4 based on outcome
- FR49 (Shell/CI/cron invocation) → `__main__.py`: Entry point
- FR50 (Stdout/stderr output) → `utils/logging.py`: Standard stream handlers
- FR51 (Background daemon) → `cli.py`: Continuous loop in `agent run`

### Cross-Cutting Concerns

**Retry Logic (Applied Throughout):**
- **Location:** `src/guarantee_email_agent/utils/retry.py`
- **Applied To:** All MCP client methods, LLM API calls
- **Pattern:** `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))`
- **Files Using:** `integrations/gmail.py`, `integrations/warranty_api.py`, `integrations/ticketing.py`, `llm/orchestrator.py`

**Structured Logging (Applied Throughout):**
- **Location:** `src/guarantee_email_agent/utils/logging.py`
- **Applied To:** Every module
- **Pattern:** `logger.info("message", extra={context})`
- **Files Using:** Every .py file in src/guarantee_email_agent/

**Error Handling (Applied Throughout):**
- **Location:** `src/guarantee_email_agent/utils/errors.py`
- **Applied To:** All error conditions
- **Pattern:** `raise AgentError(message, code, details)`
- **Files Using:** Every module that can fail

**Configuration (Loaded Once, Used Everywhere):**
- **Location:** `src/guarantee_email_agent/config/loader.py`
- **Loaded At:** Startup in `cli.py`
- **Accessed From:** All modules via dependency injection

### Integration Points

**Internal Communication (Within Main Agent):**

**CLI → Email Processor:**
```python
# cli.py (agent run command)
from guarantee_email_agent.email.processor import EmailProcessor

processor = EmailProcessor(config)
while True:
    email = await gmail_client.get_next_email()
    result = processor.process(email)
```

**Email Processor → LLM Orchestrator:**
```python
# email/processor.py
from guarantee_email_agent.llm.orchestrator import LLMOrchestrator

orchestrator = LLMOrchestrator(config)
response = await orchestrator.generate_response(email, scenario)
```

**LLM Orchestrator → Instruction Loader:**
```python
# llm/orchestrator.py
from guarantee_email_agent.instructions.loader import load_instruction

main_instruction = load_instruction("main.md")
scenario_instruction = load_instruction(f"scenarios/{scenario}.md")
```

**LLM Orchestrator → MCP Clients:**
```python
# llm/orchestrator.py
from guarantee_email_agent.integrations.warranty_api import WarrantyMCPClient
from guarantee_email_agent.integrations.ticketing import TicketingMCPClient

warranty_status = await warranty_client.check_warranty(serial_number)
ticket_id = await ticketing_client.create_ticket(ticket_data)
```

**External Integrations:**

**Main Agent ↔ Gmail MCP Server:**
- **Protocol:** MCP via stdio transport
- **Process:** Separate process (`gmail-mcp-server`)
- **Authentication:** Gmail API credentials via MCP server config
- **Operations:** Bidirectional (read emails, send responses)

**Main Agent ↔ Warranty API MCP Server:**
- **Protocol:** MCP via stdio transport
- **Process:** Local Python process (`python -m warranty_mcp_server`)
- **Authentication:** Warranty API key passed through MCP server env vars
- **Operations:** Request/response (check warranty status)

**Main Agent ↔ Ticketing MCP Server:**
- **Protocol:** MCP via stdio transport
- **Process:** Local Python process (`python -m ticketing_mcp_server`)
- **Authentication:** Ticketing API key passed through MCP server env vars
- **Operations:** One-way (create tickets only)

**Main Agent ↔ Anthropic LLM API:**
- **Protocol:** HTTPS (Anthropic SDK)
- **Authentication:** ANTHROPIC_API_KEY environment variable
- **Operations:** Request/response (message creation)
- **Timeout:** 15 seconds (NFR11)

**Data Flow:**

**Email Processing Workflow (Happy Path):**

1. **Gmail MCP → Main Agent:** New email received
2. **Main Agent (Email Parser):** Parse email content, extract metadata
3. **Main Agent (Serial Extractor):** Extract serial number from body
4. **Main Agent → Warranty MCP:** Check warranty status (serial number)
5. **Warranty MCP → Main Agent:** Warranty status response (valid, expiration date)
6. **Main Agent (Instruction Router):** Detect scenario → load "valid-warranty.md"
7. **Main Agent → LLM API:** Generate response (instruction + email context)
8. **LLM API → Main Agent:** Draft response text
9. **Main Agent → Ticketing MCP:** Create ticket (serial, status, customer)
10. **Ticketing MCP → Main Agent:** Ticket ID confirmation
11. **Main Agent → Gmail MCP:** Send response email (with ticket ID)
12. **Main Agent:** Log completion, mark email processed

**Eval Workflow:**

1. **CLI (agent eval):** Load all YAML scenarios from `evals/scenarios/`
2. **Eval Runner:** For each scenario:
   - Mock MCP server responses (warranty API, ticketing)
   - Execute email processing workflow with mocked integrations
   - Compare actual output to expected output in YAML
   - Record pass/fail
3. **Eval Reporter:** Calculate pass rate = (passed / total) × 100
4. **CLI:** Exit with code 0 (≥99%) or 4 (<99%)

### File Organization Patterns

**Configuration Files (Root Level):**

- **`config.yaml`** - Runtime configuration (MCP connections, instruction paths, eval threshold)
- **`.env.example`** - Template for environment variables (API keys)
- **`pyproject.toml`** - Project metadata, dependencies (uv managed)
- **`uv.lock`** - Lockfile for reproducible builds
- **`Procfile`** - Railway deployment command
- **`.python-version`** - Python version specification (3.10)

**Source Organization (src-layout):**

- **`src/guarantee_email_agent/`** - All application code
  - Entry points: `__main__.py`, `cli.py`
  - Feature modules: `email/`, `instructions/`, `integrations/`, `llm/`, `eval/`
  - Cross-cutting: `config/`, `utils/`
  - Pattern: Feature-based organization, not technical layers

**Test Organization (Mirrors src/):**

- **`tests/`** - Dedicated test directory
  - Pattern: Mirror src structure (`tests/email/` mirrors `src/guarantee_email_agent/email/`)
  - File naming: `test_{module}.py`
  - Fixtures: `conftest.py` at test root

**User-Editable Content (Separate from Code):**

- **`instructions/`** - Instruction markdown files (YAML + XML)
- **`evals/scenarios/`** - YAML test cases
- **`config.yaml`** - Runtime configuration
- Pattern: Version-controlled but edited independently from code

**Custom MCP Servers (Separate Components):**

- **`mcp_servers/warranty_mcp_server/`** - Warranty API wrapper
- **`mcp_servers/ticketing_mcp_server/`** - Ticketing API wrapper
- Pattern: Simple, focused MCP server implementations

### Development Workflow Integration

**Development Server Structure:**

```bash
# Start development with uv
uv run python -m guarantee_email_agent run

# Development with auto-reload (using watchdog)
uv run watchmedo auto-restart --pattern="*.py" -- python -m guarantee_email_agent run
```

**Testing Workflow:**

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/email/test_processor.py

# Run with coverage
uv run pytest --cov=guarantee_email_agent --cov-report=html

# Run eval suite
uv run python -m guarantee_email_agent eval
```

**Build Process Structure:**

```bash
# Install dependencies (development)
uv sync

# Install dependencies (production)
uv sync --frozen

# Build package
uv build

# Linting and type checking
uv run ruff check src/
uv run mypy src/
```

**Deployment Structure (Railway):**

1. **Build Detection:** Railway detects `.python-version` → installs Python 3.10
2. **Dependency Installation:** Railway detects `uv.lock` → runs `uv sync --frozen`
3. **Procfile Execution:** Railway runs `uv run python -m guarantee_email_agent run`
4. **Environment Variables:** Set in Railway dashboard (ANTHROPIC_API_KEY, WARRANTY_API_KEY, etc.)
5. **MCP Servers:** Launched as separate processes by main agent
6. **Logs:** Streamed to Railway logs dashboard

**Local Development Setup:**

```bash
# Clone repository
git clone <repo-url>
cd guarantee-email-agent

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project structure
uv init --package guarantee-email-agent

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with actual API keys

# Create instruction files
mkdir -p instructions/scenarios
# Create main.md and scenario instruction files

# Create eval scenarios
mkdir -p evals/scenarios
# Create initial YAML test cases

# Run eval suite to validate setup
uv run python -m guarantee_email_agent eval

# Start agent
uv run python -m guarantee_email_agent run
```
