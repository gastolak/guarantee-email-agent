---
project_name: 'guarantee-email-agent'
user_name: 'mMaciek'
date: '2026-01-17'
sections_completed: ['technology_stack', 'language_rules', 'architecture_rules', 'testing_rules', 'anti_patterns']
existing_patterns_found: 10
status: 'complete'
rule_count: 50
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

**Core Technologies:**
- Python: 3.10+
- Package Manager: uv (2025 standard, 10-100x faster than pip/Poetry)
- CLI Framework: Typer >= 0.9.0 with `[all]` extras

**LLM & Integration:**
- Anthropic SDK: >= 0.8.0
- MCP Python SDK: v1.25.0 (stable release)
- Model: claude-3-5-sonnet-20241022 (pinned version)
- Temperature: 0 (maximum determinism for 99% eval pass rate)

**Core Dependencies:**
- PyYAML: >= 6.0 (instruction file parsing)
- python-dotenv: >= 1.0.0 (secrets management)
- httpx: >= 0.25.0 (async HTTP client)
- tenacity: >= 8.2.0 (retry logic with exponential backoff)

**Development:**
- pytest: >= 7.4.0
- pytest-asyncio: >= 0.21.0

**Deployment:**
- Railway platform (native uv support)
- Single-process architecture (systemd/launchd compatible)

**Critical Version Constraints:**
- NEVER use pip, pipenv, or Poetry - this project MUST use uv exclusively
- MCP SDK v1.25.0 is stable; v2 available Q1 2026 but not yet adopted
- Python 3.10+ required for modern async patterns and type hints
- DO NOT use manual virtualenv activation - always use `uv run <command>`

## Critical Implementation Rules

### Python Language-Specific Rules

**Project Structure (MANDATORY):**
- ALWAYS use src-layout: `src/guarantee_email_agent/` for all application code
- NEVER import from project root - all imports must be from `guarantee_email_agent` package
- Entry point: `src/guarantee_email_agent/__main__.py`
- CLI commands: `src/guarantee_email_agent/cli.py` using Typer decorators

**Naming Conventions (PEP 8 Strict):**
- Modules/packages: `snake_case` (e.g., `mcp_client.py`, `instruction_loader.py`)
- Functions/methods: `snake_case` (e.g., `load_instruction()`, `process_email()`)
- Classes: `PascalCase` (e.g., `EvalRunner`, `LLMOrchestrator`, `MCPClient`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES = 3`, `EVAL_PASS_THRESHOLD = 99.0`)
- Private members: Prefix with `_` (e.g., `_validate_schema()`, `_parse_frontmatter()`)

**Import Patterns (CRITICAL):**
- ALWAYS use absolute imports from package root: `from guarantee_email_agent.config import load_config`
- Relative imports ONLY within same package: `from .loader import load_instruction`
- Import order: (1) standard library, (2) third-party, (3) local application
- NO circular dependencies - use dependency injection instead

**Async Patterns:**
- Email processing is async: `async def process_email(email) -> ProcessedEmail`
- ALL MCP client methods are async: `async def check_warranty(serial: str) -> dict`
- LLM API calls are async: `async def generate_response(...) -> str`
- Use `await` for all external calls (MCP, LLM, I/O operations)

**Type Hints (Strongly Encouraged):**
- Add type hints to all function signatures: `def load_instruction(filepath: str) -> dict:`
- Use `Optional[T]` for nullable types
- Use `dict`, `list` for simple structures or TypedDict for complex ones
- mypy compatibility recommended (not mandatory for MVP)

**Error Handling (MANDATORY):**
- NEVER use bare `except:` - always specify exception types
- ALWAYS use `AgentError` hierarchy for domain errors (defined in `utils/errors.py`)
- Error code pattern: `{component}_{error_type}` (e.g., "mcp_connection_failed", "instruction_validation_error")
- Include actionable details in error messages: `details={"serial_number": sn, "error": str(e)}`

### Architecture-Specific Rules

**Instruction File Format (CRITICAL - Core Innovation):**
- ALL instruction files use YAML frontmatter + XML body pattern
- File naming: kebab-case (e.g., `valid-warranty.md`, `missing-info.md`, NOT `valid_warranty.md`)
- Main instruction: `instructions/main.md`
- Scenario instructions: `instructions/scenarios/{scenario-name}.md`
- ALWAYS validate instruction syntax on startup (NFR24) - fail fast on malformed files
- Version field in frontmatter is informational (git provides versioning)

**Instruction File Structure:**
```yaml
---
name: scenario-name
description: What this scenario handles
trigger: condition_expression
version: 1.0.0
---

<scenario id="scenario-name">
  <analysis>...</analysis>
  <response>...</response>
  <actions>...</actions>
</scenario>
```

**MCP Integration Architecture (MANDATORY):**
- Main agent is MCP CLIENT connecting to 3 MCP servers via stdio transport
- Gmail: Use community MCP server (e.g., GongRzhe/Gmail-MCP-Server)
- Warranty API: Custom MCP server in `mcp_servers/warranty_mcp_server/`
- Ticketing: Custom MCP server in `mcp_servers/ticketing_mcp_server/`
- NEVER make direct API calls - ALWAYS go through MCP abstraction
- All MCP client methods MUST have retry logic (tenacity decorator)
- All MCP calls MUST have timeout (10s warranty API, 30s Gmail, 15s LLM)

**Stateless Processing (CRITICAL - NFR16):**
- NEVER persist email content to disk or database
- Email content lives ONLY in memory during processing
- NO email archive, NO state database, NO local storage
- Log customer data ONLY at DEBUG level (NFR14)
- Email marked complete/failed but content not stored

**Retry & Circuit Breaker Patterns (MANDATORY - NFR17, NFR18):**
- ALL external calls (MCP, LLM) MUST use @retry decorator from tenacity
- Max retries: 3 attempts with exponential backoff (1s, 2s, 4s, 8s max)
- Circuit breaker opens after 5 consecutive failures
- ONLY retry transient errors (network, timeout, rate limit)
- NEVER retry validation errors or auth failures

**Example Retry Pattern:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def check_warranty(self, serial_number: str) -> dict:
    # Implementation with timeout
    response = await self.client.call_tool(
        "check_warranty",
        arguments={"serial_number": serial_number},
        timeout=10  # NFR20
    )
    return response
```

**LLM Determinism Strategy (99% Pass Rate - NFR1):**
- ALWAYS use temperature=0 for maximum determinism
- ALWAYS pin model version: `claude-3-5-sonnet-20241022`
- Load main instruction + scenario-specific instruction for every email
- Construct system message from combined instructions
- 15-second timeout on all LLM API calls (NFR11)
- Retry on timeout (max 3 attempts), then mark email unprocessed

### Testing & Eval Framework Rules

**Eval Framework (MISSION CRITICAL - 99% Pass Rate NFR1):**
- Eval test cases are YAML files in `evals/scenarios/`
- File naming: `{category}_{number}.yaml` (e.g., `valid_warranty_001.yaml`, `missing_info_003.yaml`)
- Each eval validates COMPLETE end-to-end scenario (email → response + ticket creation)
- Target: ≥99% pass rate before deployment
- Run eval suite with: `uv run python -m guarantee_email_agent eval`
- Exit code 4 if pass rate < 99% (NFR29)

**Eval Test Case Structure:**
```yaml
---
scenario_id: valid_warranty_001
description: "What this test validates"
category: valid-warranty
created: 2026-01-17
---

input:
  email: {subject, body, from, received}
  mock_responses:
    warranty_api: {serial_number, status, expiration_date}

expected_output:
  email_sent: true
  response_body_contains: ["warranty is valid", "2026-06-15"]
  response_body_excludes: ["expired", "invalid"]
  ticket_created: true
  ticket_fields: {priority, category, serial_number}
  scenario_instruction_used: "valid-warranty"
  processing_time_ms: <60000
```

**Continuous Improvement Loop (FR32, FR33):**
- When agent fails an eval → add that case to permanent test suite
- Refine instruction files to handle the edge case
- Re-run full eval suite to verify fix doesn't break existing scenarios
- System becomes progressively more reliable over time
- NEVER delete passing eval scenarios (they prevent regression)

**Unit Testing (pytest):**
- Test structure mirrors src: `tests/config/test_loader.py` mirrors `src/guarantee_email_agent/config/loader.py`
- Test file naming: `test_{module}.py`
- Test function naming: `test_{scenario}_description()`
- Use pytest fixtures for common setup (defined in `tests/conftest.py`)
- Mock external dependencies: MCP servers, LLM API, file system I/O
- Run tests with: `uv run pytest`
- Coverage recommended but not mandatory for MVP

**Mock Patterns:**
- Mock MCP server responses in eval framework using `eval/mocks.py`
- Mock Anthropic LLM responses for deterministic unit tests
- NEVER mock internal application logic (only external boundaries)
- Keep mocks simple and realistic (use actual API response formats)

**Test Organization:**
- Unit tests: `tests/{module}/test_{file}.py`
- Eval scenarios: `evals/scenarios/{category}_{number}.yaml`
- Test fixtures: `tests/conftest.py`
- Mock utilities: `src/guarantee_email_agent/eval/mocks.py`

### Critical Anti-Patterns & Don't-Miss Rules

**❌ NEVER DO THESE:**

**Forbidden: Using Wrong Package Manager**
```python
# ❌ WRONG - Do NOT use pip, pipenv, or Poetry
pip install anthropic
poetry add anthropic

# ✅ CORRECT - ONLY use uv
uv add anthropic>=0.8.0
```

**Forbidden: Manual Virtualenv Management**
```bash
# ❌ WRONG - Do NOT manually activate virtualenvs
source venv/bin/activate
python -m guarantee_email_agent run

# ✅ CORRECT - Use uv run
uv run python -m guarantee_email_agent run
```

**Forbidden: Persisting Email Content (CRITICAL - NFR16)**
```python
# ❌ WRONG - NEVER write email content to disk
with open("emails.log", "a") as f:
    f.write(email.body)

# ❌ WRONG - NEVER store in database
db.save_email(email.body)

# ✅ CORRECT - Process in memory only
result = await process_email(email)  # No persistence
```

**Forbidden: Logging Customer Data at INFO Level (CRITICAL - NFR14)**
```python
# ❌ WRONG - Customer data visible in production logs
logger.info(f"Processing email: {email.body}")

# ✅ CORRECT - Customer data only at DEBUG level
logger.debug("Email content", extra={"body": email.body})
logger.info("Email received", extra={"subject": email.subject})  # Safe metadata only
```

**Forbidden: Silent Failures (CRITICAL - NFR5)**
```python
# ❌ WRONG - Silent failure with bare except
try:
    warranty = check_warranty(serial)
except:
    pass  # Email silently lost!

# ✅ CORRECT - Explicit error handling and logging
try:
    warranty = await check_warranty(serial)
except Exception as e:
    logger.error("Warranty check failed", extra={"serial": serial, "error": str(e)}, exc_info=True)
    raise AgentError(
        message="Warranty API check failed",
        code="mcp_warranty_check_failed",
        details={"serial_number": serial}
    )
```

**Forbidden: Missing Retry Logic on External Calls**
```python
# ❌ WRONG - Direct external call without retry
response = await client.call_tool("check_warranty", ...)

# ✅ CORRECT - Always use @retry decorator
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def check_warranty(self, serial: str) -> dict:
    response = await self.client.call_tool("check_warranty", ...)
    return response
```

**Forbidden: Wrong Instruction File Naming**
```python
# ❌ WRONG - Using snake_case for instruction files
instructions/scenarios/valid_warranty.md

# ✅ CORRECT - Use kebab-case
instructions/scenarios/valid-warranty.md
```

**Forbidden: Direct API Calls (Bypassing MCP)**
```python
# ❌ WRONG - Direct HTTP call to warranty API
response = httpx.post("https://api.example.com/warranty", ...)

# ✅ CORRECT - Always go through MCP abstraction
response = await warranty_client.check_warranty(serial_number)
```

**Forbidden: Non-Deterministic LLM Calls**
```python
# ❌ WRONG - Default temperature or unspecified model
client.messages.create(
    model="claude-3-5-sonnet",  # Unpinned version!
    messages=[...]
)

# ✅ CORRECT - Pinned model + temperature=0
client.messages.create(
    model="claude-3-5-sonnet-20241022",  # Pinned version
    temperature=0,  # Maximum determinism
    messages=[...]
)
```

**Forbidden: Importing from Project Root**
```python
# ❌ WRONG - Importing from project root directory
import config.loader  # This will fail!

# ✅ CORRECT - Import from package
from guarantee_email_agent.config import loader
```

**🚨 CRITICAL EDGE CASES:**

**Exit Codes (MANDATORY - NFR29):**
- 0 = Success
- 2 = Configuration error
- 3 = MCP connection error
- 4 = Eval failure (pass rate < 99%)
- NEVER use exit code 1 (reserved for general errors)

**Configuration Secrets (MANDATORY - NFR12, NFR15):**
- Secrets MUST come from environment variables only
- NEVER hardcode API keys in code
- NEVER commit .env files (use .env.example as template)
- Fail fast on startup if required secrets missing (NFR38)

**Structured Logging Format (MANDATORY):**
```python
# ❌ WRONG - String interpolation, no context
logger.info(f"Email received from {email.from_addr}")

# ✅ CORRECT - Structured logging with extra dict
logger.info("Email received", extra={
    "from": email.from_addr,
    "subject": email.subject,
    "serial_number": extracted_sn
})
```

**File Naming Consistency:**
- Python files: `snake_case.py`
- Instruction files: `kebab-case.md`
- Eval files: `{category}_{number}.yaml`
- Config files: `kebab-case.yaml`
- Directories: `snake_case/`

**Zero Silent Failures (NFR5, NFR45):**
- Every email MUST be provably processed OR explicitly marked failed
- Log ALL failures with actionable error messages
- NEVER swallow exceptions without logging
- Always include context in error logs (serial number, email ID, etc.)

---

## Quick Reference: 10 Mandatory Rules

1. **ONLY use uv** - Never pip, pipenv, or Poetry
2. **ALWAYS use @retry decorator** on external calls (MCP, LLM)
3. **NEVER persist email content** - in-memory only (NFR16)
4. **ALWAYS use temperature=0** and pinned model for LLM
5. **NEVER log customer data at INFO** - DEBUG only (NFR14)
6. **ALWAYS use AgentError hierarchy** with error codes
7. **NEVER use bare except** - explicit error handling only
8. **ALWAYS validate instructions on startup** - fail fast
9. **NEVER bypass MCP** - all external calls through MCP clients
10. **ALWAYS use structured logging** with extra dict

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Cross-reference with architecture.md for detailed context
- Update this file if new patterns emerge during implementation

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time
- Add new rules when edge cases are discovered

**Reference Priority:**
1. This file (project-context.md) - Critical implementation rules
2. architecture.md - Complete architectural decisions and patterns
3. PRD.md - Requirements and business context

Last Updated: 2026-01-17
