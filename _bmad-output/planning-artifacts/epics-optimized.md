---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
status: 'optimized'
totalEpics: 4
totalStories: 16
totalFRsCovered: 51
totalNFRsCovered: 33
validationStatus: 'passed'
optimizedFrom: 'epics.md (31 stories → 16 stories, 48% reduction)'
completedAt: '2026-01-17'
---

# guarantee-email-agent - Epic Breakdown (OPTIMIZED)

## Overview

This document provides an **optimized** epic and story breakdown for guarantee-email-agent. The original breakdown (31 stories across 6 epics) has been streamlined to **16 stories across 4 epics** while maintaining 100% requirements coverage.

**Optimization Strategy:**
- **Epic 1**: Kept as-is (4 stories) - already implemented and working
- **Epic 2**: Merged 4 stories → 1 story (all MCP integrations consolidated into single comprehensive story)
- **Epic 3**: Merged Epic 3 + Epic 4 → 6 stories (instruction engine + email processing tightly coupled)
- **Epic 4**: Merged Epic 5 + Epic 6 → 4 stories (eval + production concerns)

**Result:** 52% story reduction, same scope, faster delivery.

## Requirements Inventory

[Same FR and NFR inventory as original epics.md - omitted for brevity]

### FR Coverage Map

**Epic 1 - Project Foundation & Configuration (UNCHANGED):**
- FR34-FR41: Configuration, secrets, validation

**Epic 2 - MCP Integration Layer (CONSOLIDATED):**
- FR1, FR6, FR19, FR42, FR43: All MCP clients + retry + circuit breaker

**Epic 3 - Instruction Engine & Email Processing (MERGED):**
- FR2-FR5, FR7-FR18, FR20-FR26: Complete email workflow + instruction engine

**Epic 4 - Evaluation & Production Readiness (MERGED):**
- FR27-FR33, FR44-FR51: Eval framework + operational excellence

---

## Epic List

### Epic 1: Project Foundation & Configuration (UNCHANGED - 4 stories)
CTO can initialize the guarantee-email-agent project with proper structure, dependencies, and configuration files ready for development. This epic establishes the project skeleton using uv package manager, src-layout with Typer CLI framework, creates config.yaml for MCP connections, and establishes environment variable patterns for secrets.

**FRs covered:** FR34, FR35, FR36, FR37, FR38, FR39, FR40, FR41
**Status:** ✅ 3 stories DONE, 1 story READY-FOR-DEV

### Epic 2: MCP Integration Layer (CONSOLIDATED - 1 story)
The agent can connect to all external systems (Gmail, Warranty API, Ticketing) via MCP with reliable error handling, retry logic, and circuit breaker patterns. All three MCP integrations are built together since they follow the same architectural pattern.

**FRs covered:** FR1, FR6, FR19, FR42, FR43
**NFRs covered:** NFR17, NFR18, NFR19, NFR20, NFR21, NFR22

### Epic 3: Instruction Engine & Email Processing (MERGED - 6 stories)
The agent can load instructions, process warranty emails end-to-end, and run autonomously via `agent run` command. This epic merges the instruction-driven workflow engine with email processing since they're tightly coupled in the actual implementation.

**FRs covered:** FR2-FR18, FR20-FR26
**NFRs covered:** NFR6, NFR7, NFR10, NFR11, NFR14, NFR16, NFR23, NFR24, NFR25

### Epic 4: Evaluation & Production Readiness (MERGED - 4 stories)
CTO can run `agent eval` to validate ≥99% correctness and deploy the agent with production-grade error handling, logging, signal management, and operational controls. This epic combines eval framework with production hardening since both are required before production deployment.

**FRs covered:** FR27-FR33, FR44-FR51
**NFRs covered:** NFR1, NFR5, NFR8, NFR27-NFR33

---

## Epic 1: Project Foundation & Configuration (UNCHANGED)

CTO can initialize the guarantee-email-agent project with proper structure, dependencies, and configuration files ready for development.

### Story 1.1: Initialize Python Project with uv ✅ DONE

As a CTO,
I want to initialize the guarantee-email-agent project using uv package manager with src-layout and Typer CLI framework,
So that I have a modern, fast, reproducible Python project foundation ready for development.

**Acceptance Criteria:**

**Given** I have uv installed on my system
**When** I run the project initialization commands
**Then** The project is created with src-layout structure: `src/guarantee_email_agent/`
**And** pyproject.toml exists with Python 3.10+ requirement
**And** Typer CLI framework is added as dependency with `[all]` extras
**And** Core dependencies: anthropic>=0.8.0, pyyaml>=6.0, python-dotenv>=1.0.0, httpx>=0.25.0, tenacity>=8.2.0
**And** Dev dependencies: pytest>=7.4.0, pytest-asyncio>=0.21.0
**And** All required directories exist: `src/guarantee_email_agent/{config,email,instructions,integrations,llm,eval,utils}`
**And** All user content directories exist: `instructions/scenarios/`, `evals/scenarios/`, `mcp_servers/{warranty_mcp_server,ticketing_mcp_server}`
**And** Test directory structure mirrors src structure
**And** Basic CLI entry point exists at `src/guarantee_email_agent/cli.py`
**And** Running `uv run python -m guarantee_email_agent --help` displays CLI help without errors

### Story 1.2: Create Configuration Schema and Validation ✅ DONE

As a CTO,
I want to define and validate a YAML configuration schema for MCP connections and agent settings,
So that configuration errors are caught at startup with clear error messages.

**Acceptance Criteria:**

**Given** The project structure from Story 1.1 exists
**When** I create a `config.yaml` file with MCP connection settings
**Then** The config loader can parse the YAML file
**And** Configuration schema includes MCP, instructions, eval, and logging sections
**And** Missing required fields produce clear error messages
**And** Invalid YAML syntax produces error: "Configuration file is not valid YAML"
**And** The agent startup fails fast (exit code 2) if configuration is invalid
**And** Valid configuration loads successfully and is accessible throughout the application

### Story 1.3: Environment Variable Management for Secrets ✅ DONE

As a CTO,
I want to manage API keys and credentials exclusively through environment variables,
So that secrets are never committed to code or configuration files.

**Acceptance Criteria:**

**Given** The configuration system from Story 1.2 exists
**When** I set environment variables for API keys
**Then** The config loader loads secrets from environment variables using python-dotenv
**And** Secrets are NOT stored in config.yaml
**And** The validator checks for required environment variables on startup
**And** Missing required secrets produce clear error with env var name
**And** .env.example file documents required environment variables
**And** .gitignore includes .env to prevent accidental commits
**And** CONFIG_PATH environment variable can override default config file location
**And** The agent fails fast (exit code 2) if any required secret is missing

### Story 1.4: File Path Verification and MCP Connection Testing 📋 READY-FOR-DEV

As a CTO,
I want the agent to verify all configured file paths exist and test MCP connections on startup,
So that misconfiguration is detected immediately before processing begins.

**Acceptance Criteria:**

**Given** The configuration and secrets systems exist
**When** The agent starts up
**Then** The startup process verifies all instruction file paths exist and are readable
**And** Missing instruction files produce error with file path
**And** The startup process validates MCP connection strings
**And** Failed MCP connections produce clear errors
**And** All connection tests must pass before the agent begins processing
**And** The agent fails fast (exit code 3) if any MCP connection test fails
**And** Successful startup completes within 30 seconds (NFR9)
**And** Startup logs clearly indicate validation progress

---

## Epic 2: MCP Integration Layer (CONSOLIDATED)

The agent can connect to all external systems (Gmail, Warranty API, Ticketing) via MCP with reliable error handling, retry logic, and circuit breaker patterns.

### Story 2.1: All MCP Clients with Retry Logic and Circuit Breaker

**CONSOLIDATES: Old stories 2.1, 2.2, 2.3, 2.4**

**STATUS: ✅ COMPLETED (Mock Implementation)**

**Implementation Note:** This story was implemented using **mock MCP clients** rather than full MCP SDK integration to unblock Epic 3+ development. Mock behavior:
- Gmail: Returns empty inbox, logs email sends
- Warranty: Always returns "valid" with 1-year future expiration
- Ticketing: Returns random ticket ID (10000-99999)
- Circuit breaker and retry logic are production-ready (real implementations)

Migration to real MCP SDK can be done later by replacing client internals while keeping interfaces unchanged.

As a CTO,
I want to integrate with Gmail, Warranty API, and Ticketing system via MCP with comprehensive error handling,
So that the agent can reliably interact with all external systems despite transient failures.

**Acceptance Criteria:**

**Given** The configuration system from Epic 1 is complete
**When** I configure all three MCP connections in config.yaml

**Then - Gmail MCP Client:**
**And** The Gmail client connects to community Gmail MCP server via stdio transport
**And** Uses MCP Python SDK v1.25.0
**And** `monitor_inbox()` method reads emails from designated inbox label
**And** `send_email()` method sends email responses via Gmail API
**And** All calls use @retry decorator with exponential backoff (max 3 attempts)
**And** Transient errors (network, timeout, rate limit) are retried
**And** Non-transient errors (auth failures) are NOT retried
**And** Each MCP call has a 30-second timeout
**And** Rate limiting is handled gracefully without data loss (NFR19)

**Then - Warranty API Custom MCP Server:**
**And** Custom MCP server in `mcp_servers/warranty_mcp_server/` wraps warranty API
**And** Server exposes `check_warranty` tool via stdio transport
**And** Warranty client connects to this MCP server
**And** `check_warranty(serial_number)` method queries warranty status via MCP
**And** Uses @retry decorator with max 3 attempts and exponential backoff
**And** Each warranty API call has a 10-second timeout (NFR20)
**And** API responses parsed correctly: valid, expired, not_found status
**And** Returns warranty data: {serial_number, status, expiration_date}

**Then - Ticketing System Custom MCP Server:**
**And** Custom MCP server in `mcp_servers/ticketing_mcp_server/` wraps ticketing API
**And** Server exposes `create_ticket` tool via stdio transport
**And** Ticketing client connects to this MCP server
**And** `create_ticket(ticket_data)` method creates tickets via MCP
**And** Ticket data includes: serial_number, warranty_status, customer_email, priority, category
**And** Uses @retry decorator with max 3 attempts
**And** Validates ticket creation success before marking email processed (NFR21)
**And** Returns ticket ID and confirmation

**Then - Circuit Breaker for All Integrations:**
**And** Circuit breaker in `src/guarantee_email_agent/utils/circuit_breaker.py` tracks failures
**And** Circuit breaker opens after 5 consecutive failures per integration (NFR18)
**And** When circuit is OPEN, calls fail fast without retries
**And** Circuit remains OPEN for 60 seconds before attempting to HALF_OPEN
**And** In HALF_OPEN state, single success closes circuit, single failure reopens
**And** Circuit state transitions log clearly
**And** Each MCP client (Gmail, Warranty API, Ticketing) has independent circuit breaker
**And** Agent continues processing other emails when one integration's circuit is open (NFR22)

**Then - Shared Error Handling:**
**And** All MCP failures log error with context: service, attempt count, error type
**And** Failed operations after retries are logged at ERROR level
**And** Transient failures during retry are logged at WARN level
**And** All three integrations follow consistent error patterns
**And** Integration failures don't crash the agent
**And** Emails are marked unprocessed when critical integrations fail

---

## Epic 3: Instruction Engine & Email Processing (MERGED)

The agent can load instructions, process warranty emails end-to-end, and run autonomously via `agent run` command.

### Story 3.1: Instruction Parser and Main Orchestration Logic

**CONSOLIDATES: Old stories 3.1, 3.2**

As a CTO,
I want to parse instruction files with YAML frontmatter and XML body, and load the main orchestration instruction,
So that the agent follows a consistent decision-making process defined in editable files.

**Acceptance Criteria:**

**Given** The project foundation from Epic 1 exists
**When** I create instruction files in `instructions/` with YAML frontmatter + XML body

**Then - Instruction Parser:**
**And** Instruction loader in `src/guarantee_email_agent/instructions/loader.py` parses files
**And** Parser extracts YAML frontmatter: name, description, trigger, version
**And** Parser extracts XML body content for LLM processing
**And** File naming follows kebab-case (e.g., `valid-warranty.md`, `missing-info.md`)
**And** Main instruction at `instructions/main.md`
**And** Scenario instructions in `instructions/scenarios/{scenario-name}.md`
**And** Invalid YAML frontmatter produces clear error
**And** Malformed XML body produces error
**And** Loader validates instruction syntax on startup (NFR24)
**And** Agent fails fast if any instruction file is malformed
**And** Successfully parsed instructions cached for performance
**And** Instruction files editable in any text editor (NFR23)

**Then - Main Instruction Orchestration:**
**And** Orchestrator in `src/guarantee_email_agent/llm/orchestrator.py` loads main instruction
**And** Main instruction defines: email analysis, serial number extraction, scenario detection
**And** Orchestrator constructs LLM system messages from main instruction
**And** Main instruction guides LLM to identify scenarios (valid, invalid, missing info)
**And** Uses Anthropic SDK with temperature=0 for determinism
**And** Model pinned to `claude-3-5-sonnet-20241022`
**And** Main instruction loading validated on startup
**And** Failed main instruction loading prevents agent startup
**And** Orchestrator logs when main instruction loaded with version

### Story 3.2: Scenario Routing and LLM Response Generation

**CONSOLIDATES: Old stories 3.3, 3.4**

As a CTO,
I want the agent to dynamically load scenario-specific instructions and generate LLM responses following instruction guidance,
So that all agent behavior is controlled through editable instruction files.

**Acceptance Criteria:**

**Given** The main instruction orchestration from Story 3.1 exists
**When** The agent processes warranty emails

**Then - Scenario Routing:**
**And** Router in `src/guarantee_email_agent/instructions/router.py` selects scenario instruction
**And** Scenario detection triggers map to instruction files via frontmatter trigger field
**And** Router loads matching scenario: `instructions/scenarios/{scenario-name}.md`
**And** Multiple scenarios supported: valid-warranty, invalid-warranty, missing-info, edge-case-*
**And** Orchestrator combines main + scenario instruction for LLM context
**And** If no scenario matches, uses default graceful-degradation scenario
**And** Scenario routing logs clearly with scenario name and file path
**And** Failed scenario loading logs error and falls back to graceful degradation
**And** Router caches loaded scenario instructions for performance

**Then - LLM Response Generation:**
**And** Response generator in `src/guarantee_email_agent/llm/response_generator.py` constructs LLM prompts
**And** System message includes: main instruction + scenario instruction
**And** User message includes: email content, serial number, warranty API response
**And** LLM calls use temperature=0 for maximum determinism
**And** LLM calls use pinned model `claude-3-5-sonnet-20241022`
**And** Each LLM call has 15-second timeout (NFR11)
**And** LLM failures trigger retry with max 3 attempts
**And** After 3 failed attempts, email marked unprocessed
**And** Generated responses follow scenario instruction guidance (FR16)
**And** Generator logs LLM calls with scenario, model, temperature
**And** Responses contextually appropriate for each warranty status (FR15)
**And** Can generate graceful degradation responses for out-of-scope cases (FR18)

### Story 3.3: Email Parser and Serial Number Extraction

**CONSOLIDATES: Old stories 4.1, 4.2**

As a CTO,
I want to parse incoming warranty emails and extract serial numbers using LLM-guided reasoning,
So that the agent has all necessary context for processing.

**Acceptance Criteria:**

**Given** The Gmail MCP client from Epic 2 and instruction engine from Stories 3.1-3.2 exist
**When** The agent receives warranty inquiry emails

**Then - Email Content Parser:**
**And** Email parser in `src/guarantee_email_agent/email/parser.py` extracts metadata
**And** Extracted fields: subject, body, from (sender), received timestamp
**And** Parser handles plain text email bodies
**And** Parser extracts email thread ID for future use
**And** Email content parsed into structured EmailMessage object
**And** Parser logs email receipt with subject and sender
**And** Email content remains in memory only (NFR16 - stateless)
**And** Email content never written to disk or database (NFR16)
**And** Customer email data logged only at DEBUG level (NFR14)
**And** INFO logs show only metadata: subject, from address (no body content)

**Then - Serial Number Extraction:**
**And** Serial extractor in `src/guarantee_email_agent/email/serial_extractor.py` uses LLM
**And** Extraction follows main instruction guidance for serial number patterns
**And** Handles various formats: "SN12345", "Serial: ABC-123", "S/N: XYZ789"
**And** Multiple serial numbers in one email detected and logged
**And** If no serial found, returns None with confidence score
**And** Ambiguous cases flagged for graceful degradation
**And** Extractor logs results: "Serial extracted: SN12345" or "extraction failed"
**And** Failed extraction triggers missing-info scenario instruction
**And** Extraction errors handled gracefully without crashing

### Story 3.4: End-to-End Email Processing Pipeline

**CONSOLIDATES: Old stories 4.3, 4.4**

As a CTO,
I want to process warranty emails end-to-end from inbox monitoring through response sending,
So that customers receive automated warranty status responses without manual intervention.

**Acceptance Criteria:**

**Given** All previous Epic 3 stories complete and MCP integrations from Epic 2 available
**When** The agent processes warranty emails

**Then - Scenario Detection:**
**And** Scenario detector in `src/guarantee_email_agent/email/scenario_detector.py` uses LLM
**And** Detection identifies: valid inquiry, invalid/expired, missing serial, out-of-scope
**And** Scenario classification logged with scenario name
**And** Detector triggers scenario instruction router from Story 3.2
**And** Ambiguous scenarios default to graceful-degradation
**And** Detection happens before warranty API calls to optimize API usage
**And** Detection results include confidence score for monitoring
**And** Handles edge cases: empty emails, spam, non-warranty inquiries

**Then - Complete Processing Pipeline:**
**And** Email processor in `src/guarantee_email_agent/email/processor.py` orchestrates pipeline
**And** Pipeline: monitor inbox → parse → extract serial → detect scenario → validate warranty → generate response → send email → create ticket (if valid)
**And** Each email processed independently and asynchronously
**And** Processing completes within 60 seconds (NFR7 - 95th percentile)
**And** Uses warranty API client to validate serial numbers
**And** Warranty results (valid, expired, not_found) determine response content
**And** Uses LLM response generator to draft contextually appropriate responses
**And** Responses sent via Gmail MCP client
**And** For valid warranties, tickets created via ticketing MCP client
**And** Ticket creation includes: serial_number, warranty_status, customer details, priority
**And** Each step logs progress with email ID and processing status
**And** Failed steps logged with sufficient detail (FR44, NFR25)
**And** Emails marked unprocessed if critical steps fail (FR45, NFR5)

### Story 3.5: CLI `agent run` Command and Graceful Shutdown

**CONSOLIDATES: Old stories 4.5, 4.6**

As a CTO,
I want to start the agent for continuous inbox monitoring and stop it gracefully without losing emails,
So that the agent operates reliably 24/7 and can be safely restarted.

**Acceptance Criteria:**

**Given** The complete processing pipeline from Story 3.4 exists
**When** I run `uv run python -m guarantee_email_agent run`

**Then - CLI Command `agent run`:**
**And** CLI command in `src/guarantee_email_agent/cli.py` starts agent using Typer
**And** Agent continuously monitors Gmail inbox for new warranty emails
**And** New emails trigger processing pipeline automatically
**And** Agent runs until stopped (SIGTERM/SIGINT)
**And** Processing logs stream to stdout in real-time
**And** Logs also write to configured log file simultaneously (FR25)
**And** Command is non-interactive, suitable for background daemon (FR47, FR51)
**And** Agent can run as background process: `agent run &`
**And** Concurrent processing enabled when volume >1 email/minute (NFR10)
**And** Startup validates configuration and tests MCP connections first (Epic 1)
**And** Startup logs: "Agent starting", "Configuration validated", "MCP tested", "Monitoring inbox"

**Then - Graceful Shutdown:**
**And** When SIGTERM or SIGINT sent, shutdown handler catches signal
**And** Agent stops accepting new emails from inbox
**And** Agent completes processing of all in-flight emails before terminating
**And** In-flight emails allowed up to 60 seconds to complete
**And** After 60 seconds, remaining emails marked unprocessed
**And** Agent logs: "Shutdown signal received, completing in-flight emails (N remaining)"
**And** When complete: "All in-flight emails processed, shutting down gracefully"
**And** Agent exits with code 0 for successful graceful shutdown
**And** SIGTERM triggers graceful shutdown (systemd/launchd)
**And** SIGINT triggers immediate stop (Ctrl+C)
**And** No email silently lost during shutdown (NFR5)

### Story 3.6: Structured Logging and Graceful Degradation

**CONSOLIDATES: Old stories 4.7, 4.8**

As a CTO,
I want comprehensive logging with contextual information and graceful handling of out-of-scope cases,
So that I can monitor the agent and customers receive helpful responses even for edge cases.

**Acceptance Criteria:**

**Given** The processing pipeline from Stories 3.4-3.5 is operational
**When** The agent processes emails

**Then - Structured Logging:**
**And** Logger in `src/guarantee_email_agent/utils/logging.py` provides structured logging
**And** Log format: timestamp, log level, message, contextual extra fields
**And** Log levels: DEBUG, INFO, WARN, ERROR
**And** INFO logs: email received, serial extracted, warranty status, response sent, ticket created
**And** DEBUG logs include customer email content (body text) per NFR14
**And** INFO logs never include customer email content - only metadata
**And** ERROR logs include: serial number, scenario, error details, stack traces
**And** Each log entry includes context via extra dict: `{"serial": "SN12345", "scenario": "valid"}`
**And** Logs output to stdout for real-time monitoring (FR26)
**And** Logs simultaneously write to configured file path (FR25)
**And** Log format: `2026-01-17 10:23:45 INFO Email received: subject="Warranty check SN12345"`
**And** Logs include sufficient context for troubleshooting (NFR25)

**Then - Graceful Degradation:**
**And** When out-of-scope cases encountered: missing serial, serial in attachments, ambiguous
**And** Graceful degradation handler uses missing-info or edge-case scenario instructions
**And** For missing serial: sends response asking for serial in email body
**And** For attachment-based serials: sends response requesting serial in body
**And** For ambiguous cases: sends response asking for clarification
**And** Degradation responses polite, professional, provide clear guidance
**And** Out-of-scope emails logged: "Graceful degradation: missing-serial, response sent"
**And** Out-of-scope cases do NOT create tickets (no warranty validated)
**And** Cases do NOT crash agent or cause silent failures
**And** Customers receive responses explaining issue and next steps
**And** Agent continues processing other emails after graceful degradation

---

## Epic 4: Evaluation & Production Readiness (MERGED)

CTO can run `agent eval` to validate ≥99% correctness and deploy the agent with production-grade operational controls.

### Story 4.1: Eval Framework Core (Format, Execution, Pass Rate)

**CONSOLIDATES: Old stories 5.1, 5.2, 5.3**

As a CTO,
I want to define eval test cases in YAML and run them to calculate a pass rate,
So that I can measure progress toward 99% correctness and validate agent behavior.

**Acceptance Criteria:**

**Given** The project foundation and complete processing pipeline exist
**When** I create YAML eval test cases and run `uv run python -m guarantee_email_agent eval`

**Then - YAML Eval Format:**
**And** Eval loader in `src/guarantee_email_agent/eval/loader.py` parses YAML test cases
**And** File naming: `{category}_{number}.yaml` (e.g., `valid_warranty_001.yaml`)
**And** Each YAML includes frontmatter: scenario_id, description, category, created date
**And** Each defines input section: email (subject, body, from), mock_responses (warranty_api, etc.)
**And** Each defines expected_output: email_sent, response_body_contains, response_body_excludes, ticket_created, ticket_fields, scenario_used, processing_time_ms
**And** Loader validates YAML schema on eval startup
**And** Invalid YAML produces error with file path and missing field
**And** Successfully loaded test cases stored in memory
**And** Test cases use human-readable format (NFR27)

**Then - End-to-End Execution:**
**And** Eval runner in `src/guarantee_email_agent/eval/runner.py` executes complete workflow
**And** Input email from test case fed into email parser
**And** MCP integrations mocked with responses from test case
**And** Eval framework uses mocks in `src/guarantee_email_agent/eval/mocks.py`
**And** Agent processes: parse → extract → detect → validate → respond → create ticket
**And** Execution validates expected_output against actual behavior
**And** Each scenario runs independently in isolation
**And** Uses same instruction files as production
**And** Processing time measured and validated against threshold
**And** Eval execution does NOT modify production data or send real emails
**And** Each scenario logs: "Executing eval: valid_warranty_001"

**Then - CLI Command `agent eval` with Pass Rate:**
**And** Eval CLI command executes complete eval suite
**And** Discovers all YAML test cases in `evals/scenarios/`
**And** All discovered scenarios executed sequentially
**And** Reporter in `src/guarantee_email_agent/eval/reporter.py` calculates pass rate
**And** Output shows: "Running evaluation suite... (35 scenarios)"
**And** Shows per-scenario: "✓ Valid warranty" or "✗ Serial in attachment - failed"
**And** Shows final: "Pass rate: 34/35 (97.1%)"
**And** If pass rate ≥99%, exits with code 0
**And** If pass rate <99%, exits with code 4 (NFR29)
**And** Full suite completes within 5 minutes for ≤50 scenarios (NFR8)
**And** Command non-interactive, suitable for CI/CD (FR49)
**And** Detailed failure information logged

### Story 4.2: Eval Reporting and Continuous Improvement Loop

**CONSOLIDATES: Old stories 5.4, 5.5, 5.6**

As a CTO,
I want detailed failure reporting and the ability to add failed cases to the eval suite,
So that I can refine instructions iteratively and prevent regressions.

**Acceptance Criteria:**

**Given** The eval command from Story 4.1 runs
**When** Some scenarios fail or real-world failures occur

**Then - Failed Scenario Reporting:**
**And** Reporter provides detailed failure information for each failed scenario
**And** Failure details: scenario_id, description, expected, actual
**And** For response_body_contains: shows expected phrases and actual response
**And** For response_body_excludes: shows phrases present but should be absent
**And** For ticket_created: shows expected vs actual creation status
**And** For scenario_instruction_used: shows expected vs actual scenario
**And** Processing time failures show: expected threshold vs actual time
**And** Output clear and actionable: "FAILED: valid_warranty_001 - Expected 'warranty is valid', got '...'"
**And** Failed scenarios logged with full context
**And** Output helps identify if failure is instruction refinement or code bug

**Then - Continuous Improvement Loop:**
**And** When real-world email fails processing, can create new YAML eval case
**And** New test case captures: actual email, expected behavior, current failure
**And** Adding to `evals/scenarios/` includes it in next eval run
**And** Re-running `agent eval` shows new scenario in results
**And** Failed evals added to permanent suite (continuous improvement)
**And** Process documented: failed email → YAML case → refine instructions → re-run eval
**And** New cases follow same YAML format and naming
**And** Suite can grow from 10-20 to 50+ scenarios over time
**And** NEVER delete passing scenarios - prevent regression

**Then - Instruction Refinement Validation:**
**And** When modifying instruction files to fix failed eval
**And** Re-run `agent eval` to validate against updated instructions
**And** Framework loads modified instructions (not cached)
**And** Previously passing scenarios must still pass
**And** Target failed scenario should now pass after refinement
**And** If changes break passing scenarios, pass rate decreases visibly
**And** Workflow: identify failed → refine instructions → re-run full suite → verify maintained/improved
**And** Safe iterative refinement without breaking existing behavior
**And** Eval suite acts as regression prevention (FR32)
**And** CTO can iterate toward 99% with confidence

### Story 4.3: Error Handling, Exit Codes, and Comprehensive Logging

**CONSOLIDATES: Old stories 6.1, 6.2, 6.5**

As a CTO,
I want a standardized error hierarchy with clear codes and proper exit codes for automation,
So that all failures are logged consistently and scripts can handle different error types.

**Acceptance Criteria:**

**Given** The complete agent implementation exists
**When** I implement error handling throughout

**Then - AgentError Exception Hierarchy:**
**And** Base class AgentError exists in `src/guarantee_email_agent/utils/errors.py`
**And** AgentError includes: message, code, details (dict)
**And** Error code pattern: `{component}_{error_type}` (e.g., "mcp_connection_failed")
**And** Specific subclasses: ConfigurationError, MCPError, InstructionError, LLMError, ProcessingError
**And** All domain errors use AgentError hierarchy (not generic exceptions)
**And** Error details include actionable context: serial_number, scenario, file_path
**And** Example: `raise ConfigurationError(message="Missing field", code="config_missing_field", details={"field": "mcp.gmail"})`
**And** All errors logged with error code and details
**And** Error messages clear and actionable (NFR28)

**Then - Exit Code Standards:**
**And** Exit codes follow standard from NFR29:
**And** Exit code 0: Success (agent run completed, eval pass rate ≥99%)
**And** Exit code 1: General errors
**And** Exit code 2: Configuration error (invalid config, missing env vars, invalid paths)
**And** Exit code 3: MCP connection failure
**And** Exit code 4: Eval failure (pass rate <99%)
**And** CLI framework catches exceptions and returns appropriate codes
**And** ConfigurationError → exit code 2
**And** MCPError during startup → exit code 3
**And** Eval pass rate <99% → exit code 4
**And** Automation scripts can check: `agent eval || echo "Failed with $?"`
**And** Exit codes documented for CI/CD integration

**Then - Comprehensive Logging:**
**And** Logger logs errors with full context
**And** Error logs include: error code, message, serial_number, scenario, stack trace
**And** Example: `ERROR Warranty API failed: code=mcp_warranty_check_failed, serial=SN12345, attempt=3/3, error=timeout`
**And** Error logs use structured format with extra dict
**And** Stack traces included for debugging (exc_info=True)
**And** Transient errors (retried) logged at WARN
**And** Permanent errors (failed after retries) logged at ERROR
**And** Logs include actionable remediation guidance (NFR28)
**And** Log output sufficient for troubleshooting without code (NFR25)
**And** All errors logged - no silent failures (NFR5, FR45)

### Story 4.4: Signal Handling, Idempotent Startup, and Daemon Mode

**CONSOLIDATES: Old stories 6.3, 6.4, 6.6, 6.7**

As a CTO,
I want the agent to respect Unix signals, support daemon mode, and have idempotent startup,
So that it integrates with process supervisors and can be deployed reliably.

**Acceptance Criteria:**

**Given** The complete agent with all hardening from previous stories
**When** I deploy the agent to production

**Then - Unix Signal Handling:**
**And** Signal handler in `src/guarantee_email_agent/cli.py` catches signals
**And** SIGTERM: Triggers graceful shutdown (complete in-flight, exit code 0)
**And** SIGINT: Triggers immediate stop (Ctrl+C, exit code 0)
**And** SIGHUP: Triggers log rotation (closes/reopens log files per NFR32)
**And** Signal handling logs clearly: "SIGTERM received, initiating graceful shutdown"
**And** Works with systemd: `systemctl stop agent` sends SIGTERM
**And** Works with launchd: macOS process management
**And** Process supervisors (supervisord) can manage lifecycle
**And** Agent exits cleanly without orphaned processes

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

---

## Summary

**Optimization Results:**
- **Original:** 6 epics, 31 stories
- **Optimized:** 4 epics, 15 stories
- **Reduction:** 52% fewer stories
- **Coverage:** 100% of FRs and NFRs maintained
- **Benefits:** Faster velocity, less context switching, clearer dependencies

**Epic Breakdown:**
- Epic 1: 4 stories (UNCHANGED - already done)
- Epic 2: 1 story (down from 4 - fully consolidated)
- Epic 3: 6 stories (down from 12)
- Epic 4: 4 stories (down from 13)

**Next Steps:**
1. Complete Story 1.4 (File Path Verification)
2. Begin Epic 2 (MCP Integration Layer)
3. Progress through Epic 3 (Instruction Engine + Email Processing)
4. Finish with Epic 4 (Eval + Production Readiness)
