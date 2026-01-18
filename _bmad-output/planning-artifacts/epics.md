---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
status: 'complete'
totalEpics: 6
totalStories: 31
totalFRsCovered: 51
totalNFRsCovered: 33
validationStatus: 'passed'
completedAt: '2026-01-17'
---

# guarantee-email-agent - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for guarantee-email-agent, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Email Processing & Analysis (FR1-FR5):**
- FR1: Monitor designated Gmail inbox continuously for incoming warranty inquiry emails
- FR2: Parse email content, metadata, subject lines, and sender information
- FR3: Extract serial numbers from email body text in various formats
- FR4: Detect warranty inquiry scenarios from email content analysis
- FR5: Identify when serial number extraction fails or is ambiguous

**Warranty Validation (FR6-FR9):**
- FR6: Query external warranty API with extracted serial numbers
- FR7: Determine warranty status (valid, expired, not found) from API responses
- FR8: Handle warranty API errors and timeouts gracefully
- FR9: Validate warranty eligibility based on API response data

**Instruction-Driven Workflow (FR10-FR14):**
- FR10: Load and parse main instruction file for workflow orchestration
- FR11: Dynamically select scenario-specific instruction files based on detected scenario
- FR12: Execute LLM reasoning following instruction file guidance
- FR13: Route to appropriate scenario instructions (valid warranty, invalid warranty, missing information, edge cases)
- FR14: Edit instruction files directly in markdown format via version control

**Response Generation & Delivery (FR15-FR18):**
- FR15: Draft contextually appropriate email responses based on warranty status
- FR16: Follow scenario-specific instruction guidance for response tone and content
- FR17: Send automated email responses via Gmail
- FR18: Generate graceful degradation responses for out-of-scope cases (attachments, missing serial numbers)

**Ticket Management (FR19-FR21):**
- FR19: Create support tickets in external ticketing system for valid warranty cases
- FR20: Populate tickets with serial number, warranty status, and customer details
- FR21: Determine when ticket creation is required based on warranty validation results

**CLI Runtime Operations (FR22-FR26):**
- FR22: Start the warranty email agent for continuous processing (`agent run`)
- FR23: Stop the agent gracefully without losing in-flight emails
- FR24: Log processing activity with timestamps, levels, and contextual information
- FR25: Output logs to stdout and log files simultaneously
- FR26: View real-time processing status from log output

**Evaluation Framework (FR27-FR33):**
- FR27: Execute the complete evaluation test suite (`agent eval`)
- FR28: Run eval scenarios end-to-end (input email → expected response/action)
- FR29: Calculate and display pass rate percentage
- FR30: Identify and report failed eval scenarios with details
- FR31: Add new eval scenarios to the test suite (example email → expected response mapping)
- FR32: Validate that instruction changes don't break existing passing scenarios
- FR33: Create eval cases from real-world failed emails for reproduction

**Configuration Management (FR34-FR41):**
- FR34: Configure MCP connection settings via YAML configuration file
- FR35: Specify instruction file paths in configuration
- FR36: Set eval pass threshold percentage in configuration
- FR37: Provide API keys and credentials via environment variables
- FR38: Validate configuration schema on startup
- FR39: Verify file paths exist and are readable before processing
- FR40: Test MCP connections before starting email processing
- FR41: Fail fast with clear error messages for invalid configuration

**Error Handling & Resilience (FR42-FR46):**
- FR42: Retry MCP operations with exponential backoff for transient failures
- FR43: Implement circuit breaker for repeated API failures
- FR44: Log failures with sufficient detail for troubleshooting
- FR45: Ensure no silent failures (emails marked as unprocessed if errors occur)
- FR46: Handle graceful shutdown on SIGTERM/SIGINT signals

**Scripting & Automation Support (FR47-FR51):**
- FR47: Execute non-interactively without requiring user prompts
- FR48: Return appropriate exit codes (0 for success, specific codes for failure types)
- FR49: Support invocation from shell scripts, CI/CD pipelines, and cron jobs
- FR50: Output to stdout/stderr for pipeline compatibility
- FR51: Run as background daemon process

### NonFunctional Requirements

**Reliability (NFR1-NFR6):**
- NFR1: Achieve ≥99% eval pass rate across comprehensive test suite
- NFR2: Process 100% of warranty emails autonomously without manual intervention
- NFR3: Zero critical failures (no incorrect warranty status, no failed API calls causing incorrect responses, no unsent emails)
- NFR4: Uptime target: >99.5% measured over rolling 30-day period
- NFR5: No silent failures—all processing errors logged and emails marked as unprocessed
- NFR6: Gracefully handle unexpected inputs without crashing

**Performance (NFR7-NFR11):**
- NFR7: Email processing completes within 60 seconds from receipt to response sent (95th percentile)
- NFR8: Full eval suite execution completes within 5 minutes for suites up to 50 scenarios
- NFR9: Startup (configuration validation + MCP connection testing) completes within 30 seconds
- NFR10: Process emails concurrently when volume exceeds 1 email/minute
- NFR11: LLM API calls complete within 15 seconds or timeout with retry logic

**Security (NFR12-NFR16):**
- NFR12: API keys and credentials stored only in environment variables, never in code or configuration files
- NFR13: All MCP connections use encrypted transport (TLS 1.2+)
- NFR14: Email content and customer data logged only at DEBUG level, not in production INFO logs
- NFR15: Configuration validation fails fast if secrets are missing or invalid
- NFR16: Do not persist customer email content beyond processing (stateless email handling)

**Integration (NFR17-NFR22):**
- NFR17: MCP connections implement retry logic with exponential backoff (max 3 retries)
- NFR18: Implement circuit breaker pattern for repeated MCP failures (opens after 5 consecutive failures)
- NFR19: Gmail MCP integration handles rate limiting gracefully without data loss
- NFR20: Warranty API integration tolerates response times up to 10 seconds before timeout
- NFR21: Ticketing system integration validates ticket creation success before marking email as processed
- NFR22: Continue processing other emails if one integration temporarily fails

**Maintainability (NFR23-NFR28):**
- NFR23: Instruction files use plain markdown format editable in any text editor
- NFR24: Validate instruction file syntax on startup and fail with clear error messages
- NFR25: Log output includes sufficient context for troubleshooting without requiring code inspection
- NFR26: Configuration changes require only file edits and restart, no code changes
- NFR27: Eval scenarios use human-readable format (example email text + expected response description)
- NFR28: Provide clear error messages with actionable remediation steps for common failure modes

**Operational Excellence (NFR29-NFR33):**
- NFR29: Return appropriate exit codes for automation (0=success, 1=general failure, 2=config error, 3=MCP failure, 4=eval failure)
- NFR30: Respect standard Unix signals (SIGTERM for graceful shutdown, SIGINT for immediate stop)
- NFR31: Run as a single process manageable by standard process supervisors (systemd, launchd)
- NFR32: Log rotation compatible (responds to SIGHUP)
- NFR33: Startup is idempotent (safe to restart without side effects)

### Additional Requirements

**From Architecture - Starter Template:**
- Initialize project using uv package manager (2025 Python standard, 10-100x faster than pip/Poetry)
- Use src-layout: `src/guarantee_email_agent/` for all application code
- Python 3.10+ with Typer CLI framework
- Railway deployment platform with native uv support

**From Architecture - MCP Integration:**
- Main agent is MCP CLIENT connecting to 3 MCP servers via stdio transport
- Gmail: Use community MCP server (e.g., GongRzhe/Gmail-MCP-Server)
- Warranty API: Custom MCP server in `mcp_servers/warranty_mcp_server/`
- Ticketing: Custom MCP server in `mcp_servers/ticketing_mcp_server/`
- All MCP integration must go through official MCP Python SDK v1.25.0

**From Architecture - Instruction File Format:**
- ALL instruction files use YAML frontmatter + XML body pattern
- File naming: kebab-case (e.g., `valid-warranty.md`, `missing-info.md`)
- Main instruction: `instructions/main.md`
- Scenario instructions: `instructions/scenarios/{scenario-name}.md`
- Validate instruction syntax on startup - fail fast on malformed files

**From Architecture - LLM Determinism:**
- **Primary Provider: Gemini 2.0 Flash** (`gemini-2.0-flash-exp`, temperature=0.7)
- **Alternative Provider: Anthropic Claude** (`claude-3-5-sonnet-20241022`, temperature=0)
- Multi-provider architecture via factory pattern: `create_llm_provider(config)`
- ALWAYS pin model versions to prevent behavior drift
- 15-second timeout on all LLM API calls
- Retry on timeout (max 3 attempts), then mark email unprocessed

**From Architecture - Eval Framework:**
- Eval test cases are YAML files in `evals/scenarios/`
- File naming: `{category}_{number}.yaml` (e.g., `valid_warranty_001.yaml`)
- Each eval validates COMPLETE end-to-end scenario (email → response + ticket creation)
- Run eval suite with: `uv run python -m guarantee_email_agent eval`
- Exit code 4 if pass rate < 99%

**From Architecture - Error Handling:**
- ALWAYS use @retry decorator from tenacity on external calls (MCP, LLM)
- Max retries: 3 attempts with exponential backoff (1s, 2s, 4s, 8s max)
- Circuit breaker opens after 5 consecutive failures
- ALWAYS use AgentError hierarchy with error codes: `{component}_{error_type}`

**From Architecture - Stateless Processing:**
- NEVER persist email content to disk or database
- Email content lives ONLY in memory during processing
- NO email archive, NO state database, NO local storage
- Log customer data ONLY at DEBUG level

### FR Coverage Map

**Epic 1 - Project Foundation & Configuration:**
- FR34: Configure MCP connection settings via YAML configuration file
- FR35: Specify instruction file paths in configuration
- FR36: Set eval pass threshold percentage in configuration
- FR37: Provide API keys and credentials via environment variables
- FR38: Validate configuration schema on startup
- FR39: Verify file paths exist and are readable before processing
- FR40: Test MCP connections before starting email processing
- FR41: Fail fast with clear error messages for invalid configuration

**Epic 2 - MCP Integration Layer:**
- FR1: Monitor designated Gmail inbox continuously for incoming warranty inquiry emails
- FR6: Query external warranty API with extracted serial numbers
- FR19: Create support tickets in external ticketing system for valid warranty cases
- FR42: Retry MCP operations with exponential backoff for transient failures
- FR43: Implement circuit breaker for repeated API failures

**Epic 3 - Instruction-Driven Workflow Engine:**
- FR10: Load and parse main instruction file for workflow orchestration
- FR11: Dynamically select scenario-specific instruction files based on detected scenario
- FR12: Execute LLM reasoning following instruction file guidance
- FR13: Route to appropriate scenario instructions (valid warranty, invalid warranty, missing information, edge cases)
- FR14: Edit instruction files directly in markdown format via version control
- FR15: Draft contextually appropriate email responses based on warranty status
- FR16: Follow scenario-specific instruction guidance for response tone and content

**Epic 4 - Email Processing Workflow:**
- FR2: Parse email content, metadata, subject lines, and sender information
- FR3: Extract serial numbers from email body text in various formats
- FR4: Detect warranty inquiry scenarios from email content analysis
- FR5: Identify when serial number extraction fails or is ambiguous
- FR7: Determine warranty status (valid, expired, not found) from API responses
- FR8: Handle warranty API errors and timeouts gracefully
- FR9: Validate warranty eligibility based on API response data
- FR17: Send automated email responses via Gmail
- FR18: Generate graceful degradation responses for out-of-scope cases (attachments, missing serial numbers)
- FR20: Populate tickets with serial number, warranty status, and customer details
- FR21: Determine when ticket creation is required based on warranty validation results
- FR22: Start the warranty email agent for continuous processing (`agent run`)
- FR23: Stop the agent gracefully without losing in-flight emails
- FR24: Log processing activity with timestamps, levels, and contextual information
- FR25: Output logs to stdout and log files simultaneously
- FR26: View real-time processing status from log output

**Epic 5 - Evaluation Framework:**
- FR27: Execute the complete evaluation test suite (`agent eval`)
- FR28: Run eval scenarios end-to-end (input email → expected response/action)
- FR29: Calculate and display pass rate percentage
- FR30: Identify and report failed eval scenarios with details
- FR31: Add new eval scenarios to the test suite (example email → expected response mapping)
- FR32: Validate that instruction changes don't break existing passing scenarios
- FR33: Create eval cases from real-world failed emails for reproduction

**Epic 6 - Production Hardening & Operational Excellence:**
- FR44: Log failures with sufficient detail for troubleshooting
- FR45: Ensure no silent failures (emails marked as unprocessed if errors occur)
- FR46: Handle graceful shutdown on SIGTERM/SIGINT signals
- FR47: Execute non-interactively without requiring user prompts
- FR48: Return appropriate exit codes (0 for success, specific codes for failure types)
- FR49: Support invocation from shell scripts, CI/CD pipelines, and cron jobs
- FR50: Output to stdout/stderr for pipeline compatibility
- FR51: Run as background daemon process

## Epic List

### Epic 1: Project Foundation & Configuration
CTO can initialize the guarantee-email-agent project with proper structure, dependencies, and configuration files ready for development. This epic establishes the project skeleton using uv package manager, src-layout with Typer CLI framework, creates config.yaml for MCP connections, and establishes environment variable patterns for secrets.

**FRs covered:** FR34, FR35, FR36, FR37, FR38, FR39, FR40, FR41

### Epic 2: MCP Integration Layer
The agent can connect to all external systems (Gmail, Warranty API, Ticketing) via MCP with reliable error handling and retry logic. This implements the hybrid MCP architecture (community Gmail server + custom warranty/ticketing servers) with @retry decorators, exponential backoff, and circuit breaker patterns.

**FRs covered:** FR1, FR6, FR19, FR42, FR43

### Epic 3: Instruction-Driven Workflow Engine
The agent can load instruction files (main + scenarios), parse them, and execute LLM reasoning following instruction guidance. This includes YAML frontmatter + XML body instruction parser, dynamic scenario instruction loading, and LLM orchestration with temperature=0 and pinned model.

**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR16

### Epic 4: Email Processing Workflow
CTO can run `agent run` to autonomously process warranty emails end-to-end: read inbox → analyze → validate warranty → respond → create tickets. This delivers the core business value by implementing the complete email processing pipeline using MCP integrations and instruction engine for LLM-driven decision-making, including graceful degradation for edge cases.

**FRs covered:** FR2, FR3, FR4, FR5, FR7, FR8, FR9, FR17, FR18, FR20, FR21, FR22, FR23, FR24, FR25, FR26

### Epic 5: Evaluation Framework
CTO can run `agent eval` to validate the agent achieves ≥99% correctness across comprehensive test scenarios, enabling confidence-driven iterative refinement. This implements YAML eval test cases with end-to-end scenario validation, pass rate calculation and reporting, and the continuous improvement loop (failed eval → refine instructions → re-validate).

**FRs covered:** FR27, FR28, FR29, FR30, FR31, FR32, FR33

### Epic 6: Production Hardening & Operational Excellence
The agent runs reliably in production with proper error handling, logging, signal management, and operational controls for long-term autonomous operation. This includes comprehensive structured logging with DEBUG-level customer data protection, Unix signal handling, proper exit codes for automation, idempotent startup, and daemon mode support.

**FRs covered:** FR44, FR45, FR46, FR47, FR48, FR49, FR50, FR51

---

## Epic 1: Project Foundation & Configuration

CTO can initialize the guarantee-email-agent project with proper structure, dependencies, and configuration files ready for development. This epic establishes the project skeleton using uv package manager, src-layout with Typer CLI framework, creates config.yaml for MCP connections, and establishes environment variable patterns for secrets.

### Story 1.1: Initialize Python Project with uv

As a CTO,
I want to initialize the guarantee-email-agent project using uv package manager with src-layout and Typer CLI framework,
So that I have a modern, fast, reproducible Python project foundation ready for development.

**Acceptance Criteria:**

**Given** I have uv installed on my system
**When** I run the project initialization commands from the architecture document
**Then** The project is created with src-layout structure: `src/guarantee_email_agent/`
**And** pyproject.toml exists with Python 3.10+ requirement
**And** Typer CLI framework is added as dependency with `[all]` extras
**And** Core dependencies are specified: google-generativeai>=0.3.0, anthropic>=0.8.0, pyyaml>=6.0, python-dotenv>=1.0.0, httpx>=0.25.0, tenacity>=8.2.0
**And** Dev dependencies include pytest>=7.4.0 and pytest-asyncio>=0.21.0
**And** All required directories exist: `src/guarantee_email_agent/{config,email,instructions,integrations,llm,eval,utils}`
**And** All user content directories exist: `instructions/scenarios/`, `evals/scenarios/`, `mcp_servers/{warranty_mcp_server,ticketing_mcp_server}`
**And** Test directory structure mirrors src structure
**And** Basic CLI entry point exists at `src/guarantee_email_agent/cli.py`
**And** `__main__.py` enables `python -m guarantee_email_agent` execution
**And** Running `uv run python -m guarantee_email_agent --help` displays CLI help without errors

### Story 1.2: Create Configuration Schema and Validation

As a CTO,
I want to define and validate a YAML configuration schema for MCP connections and agent settings,
So that configuration errors are caught at startup with clear error messages before any processing begins.

**Acceptance Criteria:**

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

### Story 1.3: Environment Variable Management for Secrets

As a CTO,
I want to manage API keys and credentials exclusively through environment variables,
So that secrets are never committed to code or configuration files and fail-fast validation ensures production readiness.

**Acceptance Criteria:**

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

### Story 1.4: File Path Verification and MCP Connection Testing

As a CTO,
I want the agent to verify all configured file paths exist and test MCP connections on startup,
So that misconfiguration is detected immediately before processing begins with actionable error messages.

**Acceptance Criteria:**

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

---

## Epic 2: MCP Integration Layer

The agent can connect to all external systems (Gmail, Warranty API, Ticketing) via MCP with reliable error handling and retry logic. This implements the hybrid MCP architecture (community Gmail server + custom warranty/ticketing servers) with @retry decorators, exponential backoff, and circuit breaker patterns.

### Story 2.1: Gmail MCP Client with Retry Logic

As a CTO,
I want to integrate with a community Gmail MCP server to monitor inbox and send emails with retry logic,
So that the agent can reliably read warranty inquiries and send responses despite transient network issues.

**Acceptance Criteria:**

**Given** The configuration system from Epic 1 is complete
**When** I configure the Gmail MCP connection in config.yaml
**Then** The Gmail client in `src/guarantee_email_agent/integrations/gmail.py` connects to the community Gmail MCP server via stdio transport
**And** The client uses MCP Python SDK v1.25.0
**And** The `monitor_inbox()` method can read emails from the designated inbox label
**And** The `send_email()` method can send email responses via Gmail API
**And** All MCP calls use @retry decorator from tenacity with exponential backoff
**And** Retry configuration: max 3 attempts, exponential wait (1s, 2s, 4s, 8s max)
**And** Transient errors (network, timeout, rate limit) are retried
**And** Non-transient errors (auth failures, invalid params) are NOT retried
**And** Each MCP call has a 30-second timeout (NFR19)
**And** Rate limiting is handled gracefully without data loss (NFR19)
**And** Failed operations log error with context: "Gmail MCP call failed: send_email (attempt 3/3) - connection timeout"
**And** Successful operations complete and return email data/confirmation

### Story 2.2: Warranty API Custom MCP Server and Client

As a CTO,
I want to create a custom MCP server wrapping our warranty API and integrate it with retry logic,
So that the agent can reliably validate warranty status despite API intermittency.

**Acceptance Criteria:**

**Given** The MCP foundation from Story 2.1 exists
**When** I implement the custom warranty API MCP server in `mcp_servers/warranty_mcp_server/`
**Then** The MCP server exposes a `check_warranty` tool that wraps the external warranty API
**And** The server handles stdio transport communication
**And** The warranty client in `src/guarantee_email_agent/integrations/warranty_api.py` connects to this MCP server
**And** The `check_warranty(serial_number: str)` method queries warranty status via MCP
**And** The method uses @retry decorator with max 3 attempts and exponential backoff
**And** Each warranty API call has a 10-second timeout (NFR20)
**And** API responses are parsed correctly: valid, expired, not_found status
**And** API errors and timeouts are handled gracefully with retries
**And** Failed validations log error: "Warranty API check failed: SN12345 (attempt 3/3) - timeout"
**And** Successful validations return warranty data: {serial_number, status, expiration_date}
**And** The integration tolerates response times up to 10 seconds before timeout (NFR20)

### Story 2.3: Ticketing System Custom MCP Server and Client

As a CTO,
I want to create a custom MCP server wrapping our ticketing system and integrate it with retry logic,
So that the agent can reliably create support tickets for valid warranty cases.

**Acceptance Criteria:**

**Given** The MCP foundation from Stories 2.1 and 2.2 exists
**When** I implement the custom ticketing MCP server in `mcp_servers/ticketing_mcp_server/`
**Then** The MCP server exposes a `create_ticket` tool that wraps the external ticketing API
**And** The server handles stdio transport communication
**And** The ticketing client in `src/guarantee_email_agent/integrations/ticketing.py` connects to this MCP server
**And** The `create_ticket(ticket_data: dict)` method creates tickets via MCP
**And** Ticket data includes: serial_number, warranty_status, customer_email, customer_details, priority, category
**And** The method uses @retry decorator with max 3 attempts and exponential backoff
**And** Ticket creation validates success before marking email as processed (NFR21)
**And** Failed ticket creation logs error: "Ticket creation failed: SN12345 (attempt 3/3) - API returned 500"
**And** Successful creation returns ticket ID and confirmation
**And** The integration continues processing other emails if one ticket creation fails (NFR22)

### Story 2.4: Circuit Breaker Pattern for MCP Failures

As a CTO,
I want circuit breaker logic to prevent cascading failures when MCP integrations repeatedly fail,
So that the agent can gracefully degrade and recover without overwhelming external systems.

**Acceptance Criteria:**

**Given** All MCP clients from Stories 2.1-2.3 are implemented
**When** An MCP integration experiences repeated failures
**Then** The circuit breaker in `src/guarantee_email_agent/utils/circuit_breaker.py` tracks consecutive failures per integration
**And** Circuit breaker opens after 5 consecutive failures (NFR18)
**And** When circuit is OPEN, calls to that integration fail fast without retries
**And** Circuit remains OPEN for 60 seconds before attempting to HALF_OPEN
**And** In HALF_OPEN state, a single successful call closes the circuit
**And** In HALF_OPEN state, a single failed call reopens the circuit
**And** Circuit state transitions log clearly: "Circuit OPEN: gmail_mcp (5 consecutive failures)"
**And** Each MCP client (Gmail, Warranty API, Ticketing) has its own independent circuit breaker
**And** Circuit state is queryable for monitoring
**And** The agent continues processing other emails when one integration's circuit is open (NFR22)

---

## Epic 3: Instruction-Driven Workflow Engine

The agent can load instruction files (main + scenarios), parse them, and execute LLM reasoning following instruction guidance. This includes YAML frontmatter + XML body instruction parser, dynamic scenario instruction loading, and LLM orchestration with temperature=0 and pinned model.

### Story 3.1: Instruction File Parser (YAML Frontmatter + XML Body)

As a CTO,
I want to parse instruction files with YAML frontmatter and XML body format,
So that I can define agent behavior in human-readable, version-controlled markdown files.

**Acceptance Criteria:**

**Given** The project foundation from Epic 1 exists
**When** I create instruction files in `instructions/` directory with YAML frontmatter and XML body
**Then** The instruction loader in `src/guarantee_email_agent/instructions/loader.py` can parse the files
**And** The parser extracts YAML frontmatter fields: name, description, trigger, version
**And** The parser extracts XML body content for LLM processing
**And** File naming follows kebab-case convention (e.g., `valid-warranty.md`, `missing-info.md`)
**And** Main instruction file is at `instructions/main.md`
**And** Scenario instruction files are in `instructions/scenarios/{scenario-name}.md`
**And** Invalid YAML frontmatter produces clear error: "Invalid instruction file: instructions/main.md - YAML parsing failed"
**And** Malformed XML body produces error: "Invalid instruction file: instructions/scenarios/valid-warranty.md - XML not well-formed"
**And** The loader validates instruction syntax on startup (NFR24)
**And** Agent fails fast on startup if any instruction file is malformed
**And** Successfully parsed instructions are cached for performance
**And** Instruction files can be edited in any text editor (NFR23)

### Story 3.2: Main Instruction Orchestration Logic

As a CTO,
I want to load the main instruction file that defines workflow orchestration and scenario detection,
So that the agent follows a consistent decision-making process for all warranty emails.

**Acceptance Criteria:**

**Given** The instruction parser from Story 3.1 exists
**When** I create `instructions/main.md` with orchestration logic
**Then** The orchestrator in `src/guarantee_email_agent/llm/orchestrator.py` loads the main instruction
**And** Main instruction defines: email analysis approach, serial number extraction guidance, scenario detection logic
**And** The orchestrator constructs LLM system messages from main instruction content
**And** Main instruction guides the LLM to identify which scenario applies (valid warranty, invalid warranty, missing info)
**And** The orchestrator uses LLM provider abstraction via `create_llm_provider(config)` (from architecture)
**And** Default provider is Gemini with model `gemini-2.0-flash-exp` (from config.yaml)
**And** Temperature is configurable per provider (Gemini: 0.7, Anthropic: 0) for determinism balance
**And** Main instruction loading is validated on startup
**And** Failed main instruction loading prevents agent startup
**And** The orchestrator logs when main instruction is loaded: "Main instruction loaded: version 1.0.0"

### Story 3.3: Dynamic Scenario Instruction Loading and Routing

As a CTO,
I want the agent to dynamically load scenario-specific instruction files based on detected warranty scenarios,
So that each case type (valid, invalid, missing info) follows tailored guidance for responses and actions.

**Acceptance Criteria:**

**Given** The main instruction orchestration from Story 3.2 exists
**When** The agent detects a specific warranty scenario from email analysis
**Then** The router in `src/guarantee_email_agent/instructions/router.py` selects the appropriate scenario instruction file
**And** Scenario detection triggers map to instruction files via trigger field in YAML frontmatter
**And** The router loads the matching scenario instruction: `instructions/scenarios/{scenario-name}.md`
**And** Multiple scenarios can exist: valid-warranty.md, invalid-warranty.md, missing-info.md, edge-case-*.md
**And** The orchestrator combines main instruction + scenario instruction for LLM context
**And** If no scenario matches, the agent uses a default graceful-degradation scenario
**And** Scenario routing logic logs clearly: "Scenario detected: valid-warranty, loading instructions/scenarios/valid-warranty.md"
**And** Failed scenario instruction loading logs error and falls back to graceful degradation
**And** The router caches loaded scenario instructions for performance

### Story 3.4: LLM Response Generation Following Instructions

As a CTO,
I want the LLM to generate email responses and action decisions by following the loaded instruction guidance,
So that all agent behavior is controlled through editable instruction files rather than hardcoded logic.

**Acceptance Criteria:**

**Given** The scenario instruction routing from Story 3.3 exists
**When** The agent processes a warranty email with loaded instructions
**Then** The response generator in `src/guarantee_email_agent/llm/response_generator.py` constructs LLM prompts from instructions
**And** System message includes: main instruction content + scenario-specific instruction content
**And** User message includes: email content, extracted serial number, warranty API response
**And** LLM API calls use temperature=0 for maximum determinism (from architecture)
**And** LLM API calls use configured provider and model (default: Gemini `gemini-2.0-flash-exp`) (from architecture)
**And** Each LLM call has a 15-second timeout (NFR11, from architecture)
**And** LLM call failures trigger retry with max 3 attempts (from architecture)
**And** After 3 failed attempts, email is marked unprocessed (from architecture)
**And** Generated responses follow scenario instruction guidance for tone, content, and next steps (FR16)
**And** The generator logs LLM calls: "LLM call: provider=gemini, scenario=valid-warranty, model=gemini-2.0-flash-exp, temp=0.7"
**And** Instruction-driven responses are contextually appropriate for each warranty status (FR15)
**And** The agent can generate graceful degradation responses for out-of-scope cases (FR18)

---

## Epic 4: Email Processing Workflow

CTO can run `agent run` to autonomously process warranty emails end-to-end: read inbox → analyze → validate warranty → respond → create tickets. This delivers the core business value by implementing the complete email processing pipeline using MCP integrations and instruction engine for LLM-driven decision-making, including graceful degradation for edge cases.

### Story 4.1: Email Content Parser and Metadata Extraction

As a CTO,
I want to parse incoming warranty emails to extract content, metadata, subject lines, and sender information,
So that the agent has all necessary context for processing warranty inquiries.

**Acceptance Criteria:**

**Given** The Gmail MCP client from Epic 2 is implemented
**When** The agent receives a warranty inquiry email from the Gmail inbox
**Then** The email parser in `src/guarantee_email_agent/email/parser.py` extracts all email metadata
**And** Extracted fields include: subject, body, from (sender email), received timestamp
**And** The parser handles plain text email bodies
**And** The parser extracts email thread ID for potential future use
**And** Email content is parsed into a structured EmailMessage object
**And** The parser logs email receipt: "Email received: subject='Warranty check SN12345', from='customer@example.com'"
**And** Email content remains in memory only (NFR16 - stateless processing)
**And** Email content is never written to disk or database (NFR16)
**And** All customer email data is logged only at DEBUG level (NFR14)
**And** INFO level logs show only metadata: subject, from address (no body content)

### Story 4.2: Serial Number Extraction from Email Body

As a CTO,
I want to extract serial numbers from warranty email body text in various formats,
So that the agent can identify products for warranty validation.

**Acceptance Criteria:**

**Given** The email parser from Story 4.1 exists and instruction engine from Epic 3 is complete
**When** The agent analyzes email body content using instruction-guided LLM reasoning
**Then** The serial extractor in `src/guarantee_email_agent/email/serial_extractor.py` uses LLM to identify serial numbers
**And** Extraction follows guidance from main instruction file for serial number patterns
**And** The extractor handles various formats: "SN12345", "Serial: ABC-123", "S/N: XYZ789"
**And** Multiple serial numbers in one email are detected and logged
**And** If no serial number is found, extraction returns None with confidence score
**And** Ambiguous cases (multiple serials, unclear format) are flagged for graceful degradation
**And** The extractor logs results: "Serial number extracted: SN12345" or "Serial number extraction failed: ambiguous"
**And** Failed extraction triggers the missing-info scenario instruction
**And** Serial extraction errors are handled gracefully without crashing

### Story 4.3: Warranty Scenario Detection and Classification

As a CTO,
I want the agent to detect and classify warranty inquiry scenarios from email content,
So that the appropriate scenario-specific instructions are loaded for response generation.

**Acceptance Criteria:**

**Given** The serial number extraction from Story 4.2 exists
**When** The agent analyzes the email content and context
**Then** The scenario detector in `src/guarantee_email_agent/email/scenario_detector.py` uses LLM reasoning following main instruction guidance
**And** Detection identifies scenario types: valid warranty inquiry, invalid/expired warranty, missing serial number, out-of-scope (attachments)
**And** Scenario classification is logged: "Scenario detected: valid-warranty-inquiry"
**And** The detector triggers scenario instruction router from Epic 3 Story 3.3
**And** Ambiguous scenarios default to graceful-degradation
**And** Scenario detection happens before warranty API calls to optimize API usage
**And** Detection results include confidence score for monitoring
**And** The detector handles edge cases: empty emails, spam, non-warranty inquiries

### Story 4.4: Complete Email-to-Response Processing Pipeline

As a CTO,
I want to process warranty emails end-to-end from inbox monitoring through response sending,
So that customers receive automated warranty status responses without manual intervention.

**Acceptance Criteria:**

**Given** All previous Epic 4 stories are complete and MCP integrations from Epic 2 are available
**When** The agent runs with `uv run python -m guarantee_email_agent run`
**Then** The email processor in `src/guarantee_email_agent/email/processor.py` orchestrates the complete pipeline
**And** Pipeline steps execute in order: monitor inbox → parse email → extract serial → detect scenario → validate warranty → generate response → send email → create ticket (if valid)
**And** Each email is processed independently and asynchronously
**And** Processing completes within 60 seconds from receipt to response sent (NFR7 - 95th percentile)
**And** The processor uses warranty API client from Epic 2 to validate serial numbers
**And** Warranty validation results (valid, expired, not_found) determine response content
**And** The processor uses LLM response generator from Epic 3 to draft contextually appropriate responses
**And** Responses are sent via Gmail MCP client from Epic 2
**And** For valid warranties, tickets are created via ticketing MCP client from Epic 2
**And** Ticket creation includes: serial_number, warranty_status, customer_email, priority, category
**And** Each step logs progress: "Email processed: SN12345 → warranty=valid → response sent → ticket TKT-8829 created"
**And** Failed steps are logged with sufficient detail for troubleshooting (FR44, NFR25)
**And** Emails are marked as unprocessed if any critical step fails (FR45, NFR5)

### Story 4.5: CLI Command `agent run` for Continuous Processing

As a CTO,
I want to start the warranty email agent for continuous inbox monitoring and autonomous processing,
So that all incoming warranty emails are handled automatically 24/7.

**Acceptance Criteria:**

**Given** The complete processing pipeline from Story 4.4 exists
**When** I run `uv run python -m guarantee_email_agent run`
**Then** The CLI command in `src/guarantee_email_agent/cli.py` starts the agent using Typer framework
**And** The agent continuously monitors the Gmail inbox for new warranty emails
**And** New emails trigger the processing pipeline automatically
**And** The agent runs until stopped (SIGTERM/SIGINT)
**And** Processing logs stream to stdout in real-time showing each email's progress
**And** Logs also write to configured log file simultaneously (FR25)
**And** The command is non-interactive and suitable for background daemon operation (FR47, FR51)
**And** The agent can run as a background process: `agent run &`
**And** Concurrent email processing is enabled when volume exceeds 1 email/minute (NFR10)
**And** The agent startup validates configuration and tests MCP connections before beginning processing (from Epic 1)
**And** Startup logs clearly indicate: "Agent starting...", "Configuration validated", "MCP connections tested", "Monitoring inbox for warranty emails"

### Story 4.6: Graceful Shutdown Without Losing In-Flight Emails

As a CTO,
I want the agent to stop gracefully when I send a termination signal without losing emails currently being processed,
So that I can safely restart or update the agent without dropping customer inquiries.

**Acceptance Criteria:**

**Given** The `agent run` command from Story 4.5 is running and processing emails
**When** I send SIGTERM or SIGINT to the agent process
**Then** The shutdown handler in `src/guarantee_email_agent/cli.py` catches the signal
**And** The agent stops accepting new emails from the inbox
**And** The agent completes processing of all in-flight emails before terminating
**And** In-flight emails are allowed up to 60 seconds to complete
**And** After 60 seconds, remaining in-flight emails are marked as unprocessed
**And** The agent logs shutdown: "Shutdown signal received, completing in-flight emails (3 remaining)..."
**And** When all in-flight emails complete, agent logs: "All in-flight emails processed, shutting down gracefully"
**And** The agent exits with code 0 for successful graceful shutdown
**And** SIGTERM triggers graceful shutdown (for systemd/launchd)
**And** SIGINT triggers immediate stop (for Ctrl+C)
**And** No email is silently lost during shutdown (NFR5)

### Story 4.7: Structured Logging with Contextual Information

As a CTO,
I want all processing activity logged with timestamps, levels, and contextual information,
So that I can monitor agent behavior and troubleshoot issues effectively.

**Acceptance Criteria:**

**Given** The processing pipeline from Story 4.4 is operational
**When** The agent processes warranty emails
**Then** The logger in `src/guarantee_email_agent/utils/logging.py` provides structured logging
**And** Log format includes: timestamp, log level, message, contextual extra fields
**And** Log levels follow standard: DEBUG, INFO, WARN, ERROR
**And** INFO logs show: email received, serial extracted, warranty status, response sent, ticket created
**And** DEBUG logs include customer email content (body text) per NFR14
**And** INFO logs never include customer email content - only metadata (subject, from)
**And** ERROR logs include full context: serial number, scenario, error details, stack traces
**And** Each log entry includes contextual information via extra dict: `{"serial": "SN12345", "scenario": "valid-warranty"}`
**And** Logs output to stdout for real-time monitoring (FR26)
**And** Logs simultaneously write to configured file path (FR25)
**And** Log format example: `2026-01-17 10:23:45 INFO Email received: subject="Warranty check SN12345"`
**And** Logs include sufficient context for troubleshooting without code inspection (NFR25)

### Story 4.8: Graceful Degradation for Out-of-Scope Cases

As a CTO,
I want the agent to handle edge cases gracefully when emails are out of scope,
So that customers receive helpful responses even when the agent cannot fully process their inquiry.

**Acceptance Criteria:**

**Given** The email processing pipeline from Story 4.4 exists
**When** The agent encounters out-of-scope cases: missing serial numbers, serial in attachments, ambiguous emails
**Then** The graceful degradation handler uses the missing-info or edge-case scenario instructions
**And** For missing serial numbers: agent sends response asking customer to provide serial number in email body
**And** For attachment-based serials (out of scope for MVP): agent sends response requesting serial in email body
**And** For ambiguous cases: agent sends response asking for clarification
**And** Graceful degradation responses are polite, professional, and provide clear guidance
**And** Out-of-scope emails are logged: "Graceful degradation: missing-serial-number, response sent requesting info"
**And** Out-of-scope cases do NOT create tickets (no warranty validated)
**And** These cases do NOT crash the agent or cause silent failures
**And** Customers receive responses explaining the issue and next steps
**And** The agent continues processing other emails normally after graceful degradation

---

## Epic 5: Evaluation Framework

CTO can run `agent eval` to validate the agent achieves ≥99% correctness across comprehensive test scenarios, enabling confidence-driven iterative refinement. This implements YAML eval test cases with end-to-end scenario validation, pass rate calculation and reporting, and the continuous improvement loop (failed eval → refine instructions → re-validate).

### Story 5.1: YAML Eval Test Case Format and Loading

As a CTO,
I want to define eval test cases in YAML format with example emails and expected outcomes,
So that I can build a comprehensive test suite that validates end-to-end agent behavior.

**Acceptance Criteria:**

**Given** The project foundation from Epic 1 exists
**When** I create YAML eval test cases in `evals/scenarios/` directory
**Then** The eval loader in `src/guarantee_email_agent/eval/loader.py` can parse YAML test case files
**And** File naming follows pattern: `{category}_{number}.yaml` (e.g., `valid_warranty_001.yaml`, `missing_info_003.yaml`)
**And** Each YAML file includes frontmatter: scenario_id, description, category, created date
**And** Each test case defines input section: email (subject, body, from, received), mock_responses (warranty_api, etc.)
**And** Each test case defines expected_output section: email_sent, response_body_contains, response_body_excludes, ticket_created, ticket_fields, scenario_instruction_used, processing_time_ms
**And** The loader validates YAML schema on eval suite startup
**And** Invalid YAML test cases produce clear error: "Invalid eval file: evals/scenarios/valid_warranty_001.yaml - missing required field 'expected_output'"
**And** Successfully loaded test cases are stored in memory for execution
**And** Eval test cases use human-readable format (NFR27)

### Story 5.2: End-to-End Eval Scenario Execution

As a CTO,
I want to execute eval scenarios end-to-end with mocked integrations,
So that I can validate complete agent behavior from email input to final actions.

**Acceptance Criteria:**

**Given** The YAML eval loader from Story 5.1 exists and the complete processing pipeline from Epic 4 is implemented
**When** I run an eval scenario
**Then** The eval runner in `src/guarantee_email_agent/eval/runner.py` executes the complete workflow
**And** Input email from test case is fed into the email parser
**And** MCP integrations (Gmail, warranty API, ticketing) are mocked with responses from test case
**And** The eval framework uses mocks in `src/guarantee_email_agent/eval/mocks.py` for deterministic testing
**And** The agent processes the email following the complete pipeline: parse → extract serial → detect scenario → validate warranty → generate response → send email → create ticket
**And** Eval execution validates expected_output fields against actual agent behavior
**And** Each eval scenario runs independently in isolation
**And** Eval scenarios use the same instruction files as production (instructions/main.md and scenarios)
**And** Processing time is measured and validated against expected_output.processing_time_ms threshold
**And** Eval execution does NOT modify production data or send real emails
**And** Each scenario execution logs: "Executing eval: valid_warranty_001"

### Story 5.3: CLI Command `agent eval` with Pass Rate Calculation

As a CTO,
I want to run the complete eval suite and see a pass rate percentage with detailed results,
So that I can measure progress toward the 99% correctness target.

**Acceptance Criteria:**

**Given** The eval runner from Story 5.2 exists
**When** I run `uv run python -m guarantee_email_agent eval`
**Then** The eval CLI command in `src/guarantee_email_agent/cli.py` executes the complete eval suite
**And** The command discovers all YAML test cases in `evals/scenarios/` directory
**And** All discovered scenarios are executed sequentially
**And** The reporter in `src/guarantee_email_agent/eval/reporter.py` calculates pass rate: (passed / total) × 100
**And** Output shows summary: "Running evaluation suite... (35 scenarios)"
**And** Output shows per-scenario results: "✓ Valid warranty - standard format" or "✗ Serial number in attachment - failed"
**And** Output shows final pass rate: "Pass rate: 34/35 (97.1%)"
**And** If pass rate >= 99%, command exits with code 0
**And** If pass rate < 99%, command exits with code 4 (NFR29)
**And** Full eval suite completes within 5 minutes for suites up to 50 scenarios (NFR8)
**And** The command is non-interactive and suitable for CI/CD automation (FR49)
**And** Detailed failure information is logged for failed scenarios

### Story 5.4: Failed Scenario Reporting and Debugging

As a CTO,
I want detailed reporting for failed eval scenarios,
So that I can identify what went wrong and refine instructions to fix failures.

**Acceptance Criteria:**

**Given** The eval command from Story 5.3 runs and some scenarios fail
**When** I review the eval results
**Then** The reporter provides detailed failure information for each failed scenario
**And** Failure details include: scenario_id, description, what was expected, what actually happened
**And** For response_body_contains failures: shows expected phrases and actual response body
**And** For response_body_excludes failures: shows phrases that should be absent but were present
**And** For ticket_created failures: shows expected (true/false) and actual ticket creation status
**And** For scenario_instruction_used failures: shows expected scenario and actual scenario selected
**And** Processing time failures show: expected threshold and actual processing time
**And** Failure output is clear and actionable: "FAILED: valid_warranty_001 - Expected response to contain 'warranty is valid', but response was: '...'"
**And** Failed scenarios are logged with full context for troubleshooting
**And** The output helps identify whether failure is due to instruction refinement needed or code bugs

### Story 5.5: Continuous Improvement Loop - Add Failed Cases to Suite

As a CTO,
I want to add real-world failed emails as new eval scenarios,
So that the test suite grows comprehensively and prevents regression.

**Acceptance Criteria:**

**Given** The eval framework from previous stories exists and the agent is running in production
**When** A real-world email fails to process correctly
**Then** I can create a new YAML eval test case from the failed email
**And** The new test case captures: actual email content, expected behavior, current failure mode
**And** Adding the new test case to `evals/scenarios/` includes it in the next eval run
**And** Re-running `agent eval` after adding the case shows the new scenario in results
**And** Failed evals are added to the permanent test suite (continuous improvement loop from architecture)
**And** The process is documented: failed email → create YAML test case → add to evals/scenarios/ → refine instructions → re-run eval
**And** New test cases follow the same YAML format and naming convention
**And** Test suite can grow from initial 10-20 scenarios to 50+ scenarios over time
**And** NEVER delete passing eval scenarios - they prevent regression (from architecture)

### Story 5.6: Instruction Refinement Validation (Regression Prevention)

As a CTO,
I want to validate that instruction file changes don't break existing passing scenarios,
So that I can refine instructions confidently without introducing regressions.

**Acceptance Criteria:**

**Given** The eval suite from previous stories exists with passing scenarios
**When** I modify instruction files (main.md or scenario files) to fix a failed eval
**Then** I can re-run `agent eval` to validate all scenarios against the updated instructions
**And** The eval framework loads the modified instruction files (not cached versions)
**And** Previously passing scenarios must still pass after instruction changes
**And** The target failed scenario should now pass after refinement
**And** If instruction changes break previously passing scenarios, pass rate decreases and is clearly visible
**And** The validation workflow is: identify failed eval → refine instructions → re-run full eval suite → verify pass rate maintained or improved
**And** This enables safe iterative refinement without breaking existing behavior
**And** The eval suite acts as regression prevention for instruction changes (FR32)
**And** CTO can iterate toward 99% pass rate with confidence

---

## Epic 6: Production Hardening & Operational Excellence

The agent runs reliably in production with proper error handling, logging, signal management, and operational controls for long-term autonomous operation. This includes comprehensive structured logging with DEBUG-level customer data protection, Unix signal handling, proper exit codes for automation, idempotent startup, and daemon mode support.

### Story 6.1: AgentError Exception Hierarchy with Error Codes

As a CTO,
I want a standardized error hierarchy with clear error codes,
So that all failures are logged consistently and can be diagnosed efficiently.

**Acceptance Criteria:**

**Given** The project foundation from Epic 1 exists
**When** I implement error handling throughout the agent
**Then** The base class AgentError exists in `src/guarantee_email_agent/utils/errors.py`
**And** AgentError includes fields: message, code, details (dict)
**And** Error code pattern follows: `{component}_{error_type}` (e.g., "mcp_connection_failed", "instruction_validation_error")
**And** Specific error subclasses exist: ConfigurationError, MCPError, InstructionError, LLMError, ProcessingError
**And** All domain errors use AgentError hierarchy (not generic exceptions)
**And** Error details include actionable context: serial_number, scenario, file_path, etc.
**And** Example error: `raise ConfigurationError(message="Missing required field", code="config_missing_field", details={"field": "mcp.gmail.connection_string"})`
**And** All errors are logged with error code and details for troubleshooting
**And** Error messages are clear and actionable (NFR28)

### Story 6.2: Exit Code Standards for Automation

As a CTO,
I want the agent to return specific exit codes for different failure types,
So that automation scripts and CI/CD pipelines can handle failures appropriately.

**Acceptance Criteria:**

**Given** The CLI commands from Epic 4 and Epic 5 exist
**When** The agent terminates (successfully or with errors)
**Then** Exit codes follow the standard defined in NFR29:
**And** Exit code 0: Success (agent run completed gracefully, or eval pass rate >= 99%)
**And** Exit code 1: Reserved for general errors
**And** Exit code 2: Configuration error (invalid config.yaml, missing env vars, invalid file paths)
**And** Exit code 3: MCP connection failure (Gmail, warranty API, or ticketing connection failed)
**And** Exit code 4: Eval failure (pass rate < 99%)
**And** The CLI framework in `src/guarantee_email_agent/cli.py` catches exceptions and returns appropriate codes
**And** ConfigurationError exceptions → exit code 2
**And** MCPError exceptions during startup → exit code 3
**And** Eval pass rate < 99% → exit code 4
**And** Automation scripts can check exit codes: `agent eval || echo "Eval failed with code $?"`
**And** Exit codes are documented for scripting and CI/CD integration

### Story 6.3: Unix Signal Handling (SIGTERM, SIGINT, SIGHUP)

As a CTO,
I want the agent to respect standard Unix signals for proper process management,
So that it integrates smoothly with systemd, launchd, and process supervisors.

**Acceptance Criteria:**

**Given** The `agent run` command from Epic 4 Story 4.5 exists
**When** Unix signals are sent to the agent process
**Then** The signal handler in `src/guarantee_email_agent/cli.py` catches and handles signals appropriately
**And** SIGTERM: Triggers graceful shutdown (complete in-flight emails, then exit code 0)
**And** SIGINT: Triggers immediate stop (Ctrl+C, exit code 0)
**And** SIGHUP: Triggers log rotation compatibility (closes and reopens log files per NFR32)
**And** Signal handling logs clearly: "SIGTERM received, initiating graceful shutdown"
**And** The agent works correctly with systemd: `systemctl stop agent` sends SIGTERM
**And** The agent works correctly with launchd: macOS launchd process management
**And** Process supervisors (supervisord, etc.) can manage the agent lifecycle
**And** The agent exits cleanly without orphaned processes or resources

### Story 6.4: Idempotent Startup and State Management

As a CTO,
I want the agent startup to be idempotent and safe to restart,
So that I can deploy updates or recover from crashes without side effects.

**Acceptance Criteria:**

**Given** The agent startup process from Epic 1 and Epic 4 exists
**When** I start the agent multiple times or restart after a crash
**Then** Startup is idempotent - safe to run repeatedly without side effects (NFR33)
**And** Configuration validation runs on every startup (not cached)
**And** MCP connection tests run on every startup
**And** Instruction file validation runs on every startup
**And** No state persists between agent restarts (stateless architecture per NFR16)
**And** Restarting the agent does not duplicate email processing (emails remain in Gmail inbox until processed)
**And** Crashed agent can be restarted cleanly without manual cleanup
**And** Startup logs indicate: "Agent starting (restart safe, idempotent startup)"
**And** The agent can run as a single process manageable by systemd/launchd (NFR31)

### Story 6.5: Error Handling with Detailed Context Logging

As a CTO,
I want all failures logged with sufficient detail for troubleshooting,
So that I can diagnose and fix issues without inspecting code.

**Acceptance Criteria:**

**Given** The AgentError hierarchy from Story 6.1 exists and processing pipeline from Epic 4 is complete
**When** Any error occurs during agent operation
**Then** The logger in `src/guarantee_email_agent/utils/logging.py` logs errors with full context
**And** Error logs include: error code, error message, serial_number, scenario, stack trace
**And** Example error log: `ERROR Warranty API check failed: code=mcp_warranty_check_failed, serial=SN12345, attempt=3/3, error=connection timeout`
**And** Error logs use structured format with extra dict for context
**And** Stack traces are included for debugging (exc_info=True)
**And** Transient errors (retried) are logged at WARN level
**And** Permanent errors (failed after retries) are logged at ERROR level
**And** Logs include actionable remediation guidance where possible (NFR28)
**And** Log output includes sufficient context for troubleshooting without code inspection (NFR25)
**And** All errors are logged - no silent failures (NFR5, FR45)

### Story 6.6: Stdout/Stderr Output for Pipeline Compatibility

As a CTO,
I want the agent to output logs to stdout and errors to stderr following Unix conventions,
So that the agent works correctly in shell pipelines and automation scripts.

**Acceptance Criteria:**

**Given** The structured logging from Epic 4 Story 4.7 exists
**When** The agent runs in various environments (terminal, background, CI/CD)
**Then** Normal logs (INFO, DEBUG) write to stdout (FR50)
**And** Error logs (WARN, ERROR) write to stderr (FR50)
**And** The agent works in shell pipelines: `agent run | grep "Email processed"`
**And** Stderr can be redirected separately: `agent run 2> errors.log`
**And** The agent works in CI/CD: logs are captured correctly by Jenkins, GitHub Actions, etc.
**And** Background daemon mode captures logs: `agent run > agent.log 2>&1 &`
**And** The agent respects standard Unix conventions for stdout/stderr
**And** Output is suitable for log aggregation tools (NFR31)

### Story 6.7: Deployment Automation and Daemon Mode Support

As a CTO,
I want to run the agent as a background daemon process,
So that it operates continuously in production without requiring an active terminal session.

**Acceptance Criteria:**

**Given** The `agent run` command from Epic 4 exists with all hardening from previous Epic 6 stories
**When** I deploy the agent to production
**Then** The agent can run as a background daemon: `uv run python -m guarantee_email_agent run &`
**And** The agent continues running after terminal disconnect (nohup compatible)
**And** The agent writes logs to configured file path for persistent monitoring
**And** Process can be checked: `pgrep -f "agent run"` returns PID
**And** Process can be stopped: `pkill -TERM -f "agent run"` triggers graceful shutdown
**And** The agent integrates with systemd service files for automatic startup
**And** The agent integrates with launchd plists for macOS daemon mode
**And** Railway deployment works with Procfile: `web: uv run python -m guarantee_email_agent run`
**And** The agent is single-process (no child processes to manage) per NFR31
**And** Container deployment works: agent runs correctly in Docker/Kubernetes
