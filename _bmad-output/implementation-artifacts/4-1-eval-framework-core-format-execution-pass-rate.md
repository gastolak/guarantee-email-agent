# Story 4.1: Eval Framework Core (Format, Execution, Pass Rate)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want to define eval test cases in YAML and run them to calculate a pass rate,
So that I can measure progress toward 99% correctness and validate agent behavior.

## Acceptance Criteria

**Given** The project foundation and complete processing pipeline from Epic 3 exist
**When** I create YAML eval test cases and run `uv run python -m guarantee_email_agent eval`

**Then - YAML Eval Format:**
**And** Eval loader in `src/guarantee_email_agent/eval/loader.py` parses YAML test cases
**And** File naming: `{category}_{number}.yaml` (e.g., `valid_warranty_001.yaml`, `missing_info_003.yaml`)
**And** Each YAML includes frontmatter: scenario_id, description, category, created date
**And** Each defines input section: email (subject, body, from, received), mock_responses (warranty_api data)
**And** Each defines expected_output: email_sent, response_body_contains, response_body_excludes, ticket_created, ticket_fields, scenario_instruction_used, processing_time_ms
**And** Loader validates YAML schema on eval startup
**And** Invalid YAML produces error with file path and missing field
**And** Successfully loaded test cases stored in memory
**And** Test cases use human-readable format (NFR27)
**And** Eval files located in `evals/scenarios/` directory

**Then - End-to-End Execution:**
**And** Eval runner in `src/guarantee_email_agent/eval/runner.py` executes complete workflow
**And** Input email from test case fed into email parser
**And** MCP integrations mocked with responses from test case mock_responses
**And** Eval framework uses mocks in `src/guarantee_email_agent/eval/mocks.py`
**And** Agent processes: parse → extract serial → detect scenario → validate warranty → respond → create ticket
**And** Execution validates expected_output against actual behavior
**And** Each scenario runs independently in isolation
**And** Uses same instruction files as production
**And** Processing time measured and validated against threshold (<60s per NFR7)
**And** Eval execution does NOT modify production data or send real emails
**And** Each scenario logs: "Executing eval: valid_warranty_001"
**And** Mock responses deterministic for reproducible results

**Then - CLI Command `agent eval` with Pass Rate:**
**And** Eval CLI command in `cli.py` executes complete eval suite
**And** Discovers all YAML test cases in `evals/scenarios/` directory
**And** All discovered scenarios executed sequentially
**And** Reporter in `src/guarantee_email_agent/eval/reporter.py` calculates pass rate
**And** Output shows: "Running evaluation suite... (N scenarios)"
**And** Shows per-scenario: "✓ valid_warranty_001: Valid warranty inquiry" or "✗ missing_info_003: Missing serial - FAILED"
**And** Shows final: "Pass rate: 34/35 (97.1%)" or "Pass rate: 35/35 (100%)"
**And** If pass rate ≥99%, exits with code 0 (success per NFR29)
**And** If pass rate <99%, exits with code 4 (eval failure per NFR29)
**And** Full suite completes within 5 minutes for ≤50 scenarios (NFR8)
**And** Command non-interactive, suitable for CI/CD (FR49)
**And** Detailed failure information logged for troubleshooting

## Tasks / Subtasks

### Eval Data Structures

- [ ] Create eval test case dataclass (AC: YAML includes frontmatter and sections)
  - [ ] Create `src/guarantee_email_agent/eval/models.py`
  - [ ] Define `EvalTestCase` dataclass with @dataclass decorator
  - [ ] Fields: scenario_id (str), description (str), category (str), created (str)
  - [ ] Field: input (EvalInput with email and mock_responses)
  - [ ] Field: expected_output (EvalExpectedOutput)
  - [ ] Add type hints to all fields
  - [ ] Make immutable with frozen=True

- [ ] Create eval input dataclass (AC: defines input section)
  - [ ] Define `EvalInput` dataclass in models.py
  - [ ] Field: email (EvalEmail with subject, body, from, received)
  - [ ] Field: mock_responses (Dict with warranty_api, etc.)
  - [ ] All fields typed appropriately
  - [ ] Example mock_responses: {"warranty_api": {"status": "valid", "expiration_date": "2025-12-31"}}

- [ ] Create eval expected output dataclass (AC: defines expected_output)
  - [ ] Define `EvalExpectedOutput` dataclass in models.py
  - [ ] Field: email_sent (bool)
  - [ ] Field: response_body_contains (List[str]) - phrases that must be present
  - [ ] Field: response_body_excludes (List[str]) - phrases that must NOT be present
  - [ ] Field: ticket_created (bool)
  - [ ] Field: ticket_fields (Optional[Dict]) - expected ticket data
  - [ ] Field: scenario_instruction_used (str) - expected scenario name
  - [ ] Field: processing_time_ms (int) - maximum acceptable processing time
  - [ ] Add helper method: matches(actual: ProcessingResult) -> Tuple[bool, List[str]]

- [ ] Create eval result dataclass (AC: tracks execution results)
  - [ ] Define `EvalResult` dataclass in models.py
  - [ ] Field: test_case (EvalTestCase)
  - [ ] Field: passed (bool)
  - [ ] Field: failures (List[str]) - list of failure reasons
  - [ ] Field: actual_output (Dict) - actual agent behavior
  - [ ] Field: processing_time_ms (int)
  - [ ] Add helper method: format_for_display() -> str

### YAML Eval Loader

- [ ] Create eval loader module (AC: loader parses YAML test cases)
  - [ ] Create `src/guarantee_email_agent/eval/loader.py`
  - [ ] Import yaml module (PyYAML)
  - [ ] Import eval models
  - [ ] Create `EvalLoader` class
  - [ ] Add logger with __name__

- [ ] Implement YAML parsing (AC: file naming, frontmatter extraction)
  - [ ] Create `load_eval_test_case(file_path: str) -> EvalTestCase` method
  - [ ] Read YAML file content
  - [ ] Parse YAML with yaml.safe_load()
  - [ ] Extract frontmatter: scenario_id, description, category, created
  - [ ] Extract input section: email, mock_responses
  - [ ] Extract expected_output section
  - [ ] Create EvalTestCase instance
  - [ ] Return parsed test case

- [ ] Implement schema validation (AC: validates YAML schema on startup)
  - [ ] Create `validate_test_case(data: Dict) -> None` method
  - [ ] Check required frontmatter fields present
  - [ ] Check input.email has: subject, body, from, received
  - [ ] Check expected_output has required fields
  - [ ] Validate field types (bools, lists, strings)
  - [ ] Raise EvalError if validation fails
  - [ ] Include file path and missing field in error

- [ ] Implement discovery of all test cases (AC: discovers all YAML test cases)
  - [ ] Create `discover_test_cases(directory: str) -> List[EvalTestCase]` method
  - [ ] Scan evals/scenarios/ directory
  - [ ] Find all *.yaml files
  - [ ] Match naming pattern: {category}_{number}.yaml
  - [ ] Load each file with load_eval_test_case()
  - [ ] Collect all test cases in list
  - [ ] Log: "Discovered {count} eval test cases"
  - [ ] Return list of EvalTestCase objects

- [ ] Add error handling for invalid YAML (AC: invalid YAML produces error)
  - [ ] Catch yaml.YAMLError during parsing
  - [ ] Catch KeyError for missing fields
  - [ ] Catch TypeError for wrong field types
  - [ ] Produce clear error message with file path
  - [ ] Example: "Invalid eval file: valid_warranty_001.yaml - Missing field: expected_output.email_sent"
  - [ ] Log error at ERROR level
  - [ ] Don't crash eval suite (skip invalid files, report in results)

### Mock Framework for MCP and LLM

- [ ] Create mock framework module (AC: mocks in eval/mocks.py)
  - [ ] Create `src/guarantee_email_agent/eval/mocks.py`
  - [ ] Import MCP client interfaces
  - [ ] Import Anthropic SDK types
  - [ ] Create mock classes for each integration
  - [ ] Add logger with __name__

- [ ] Implement Gmail MCP mock (AC: MCP integrations mocked)
  - [ ] Create `MockGmailClient` class
  - [ ] Implement `get_unread_emails() -> List[Dict]` method
  - [ ] Returns email from test case input
  - [ ] Implement `send_email(to, subject, body, thread_id)` async method
  - [ ] Captures sent email (doesn't actually send)
  - [ ] Store sent emails for validation
  - [ ] Implement `close()` method (no-op)

- [ ] Implement Warranty API MCP mock (AC: mock_responses from test case)
  - [ ] Create `MockWarrantyAPIClient` class
  - [ ] Initialize with mock_responses dict from test case
  - [ ] Implement `check_warranty(serial_number: str) -> Dict` async method
  - [ ] Return mock warranty data from test case
  - [ ] Simulate realistic API delays (optional)
  - [ ] Implement `close()` method (no-op)

- [ ] Implement Ticketing MCP mock
  - [ ] Create `MockTicketingClient` class
  - [ ] Implement `create_ticket(ticket_data: Dict) -> Dict` async method
  - [ ] Captures ticket data (doesn't actually create)
  - [ ] Returns mock ticket_id: "MOCK-TICKET-001"
  - [ ] Store created tickets for validation
  - [ ] Implement `close()` method (no-op)

- [ ] Implement Anthropic LLM mock (AC: uses same instructions as production)
  - [ ] Create `MockAnthropicClient` class
  - [ ] Implement `messages.create(...)` method
  - [ ] Generate deterministic responses based on scenario
  - [ ] Use actual instruction files (not mocked)
  - [ ] Map scenario_instruction_used to expected response patterns
  - [ ] Return mock Message object with expected content
  - [ ] Ensure deterministic for reproducible results

- [ ] Create mock factory (AC: eval execution uses mocks)
  - [ ] Create `create_mock_clients(test_case: EvalTestCase) -> Dict` function
  - [ ] Returns dict: {"gmail": MockGmailClient, "warranty": MockWarrantyAPIClient, ...}
  - [ ] Initialize mocks with test case data
  - [ ] Mocks injected into EmailProcessor for eval runs
  - [ ] Log: "Using mocked integrations for eval"

### Eval Execution Engine

- [ ] Create eval runner module (AC: runner executes complete workflow)
  - [ ] Create `src/guarantee_email_agent/eval/runner.py`
  - [ ] Import EmailProcessor and dependencies
  - [ ] Import EvalTestCase, EvalResult models
  - [ ] Import mock framework
  - [ ] Create `EvalRunner` class
  - [ ] Initialize with config

- [ ] Implement single test case execution (AC: input email fed into parser)
  - [ ] Create `run_test_case(test_case: EvalTestCase) -> EvalResult` async method
  - [ ] Create mock clients from test case
  - [ ] Inject mocks into EmailProcessor (DI)
  - [ ] Convert test case input to raw_email format
  - [ ] Call processor.process_email(raw_email)
  - [ ] Capture ProcessingResult
  - [ ] Validate against expected_output
  - [ ] Return EvalResult with pass/fail and details

- [ ] Implement output validation (AC: validates expected_output against actual)
  - [ ] Create `validate_output(expected: EvalExpectedOutput, actual: ProcessingResult) -> Tuple[bool, List[str]]` method
  - [ ] Check email_sent matches
  - [ ] Check response_body_contains: all phrases present in actual response
  - [ ] Check response_body_excludes: no excluded phrases in actual response
  - [ ] Check ticket_created matches
  - [ ] Check ticket_fields match if ticket created
  - [ ] Check scenario_instruction_used matches
  - [ ] Check processing_time_ms <= expected threshold
  - [ ] Return (passed, failures) tuple

- [ ] Implement isolation between test cases (AC: scenarios run independently)
  - [ ] Each test case gets fresh mock clients
  - [ ] No shared state between test cases
  - [ ] Reload instruction files for each test (no caching)
  - [ ] Clear any in-memory caches between tests
  - [ ] Log: "Executing eval: {scenario_id}"
  - [ ] Each test starts with clean state

- [ ] Add processing time measurement (AC: processing time measured)
  - [ ] Track execution time for run_test_case()
  - [ ] Start timer before processor.process_email()
  - [ ] Stop timer after result returned
  - [ ] Include in EvalResult.processing_time_ms
  - [ ] Validate against expected_output.processing_time_ms
  - [ ] Log if exceeds 60s target (NFR7)

- [ ] Implement suite execution (AC: all scenarios executed)
  - [ ] Create `run_suite(test_cases: List[EvalTestCase]) -> List[EvalResult]` async method
  - [ ] Execute each test case sequentially (not parallel - isolation)
  - [ ] Collect all EvalResults
  - [ ] Log progress: "Executing {current}/{total}: {scenario_id}"
  - [ ] Continue on individual test failures (don't stop suite)
  - [ ] Return list of all results

- [ ] Add safety: no production data modification (AC: does NOT modify production data)
  - [ ] Mocks prevent real Gmail API calls
  - [ ] Mocks prevent real warranty API calls
  - [ ] Mocks prevent real ticketing API calls
  - [ ] No actual emails sent
  - [ ] No real tickets created
  - [ ] Log clearly: "Running in eval mode - using mocks"
  - [ ] Document that eval is safe to run repeatedly

### Pass Rate Calculation and Reporting

- [ ] Create reporter module (AC: reporter calculates pass rate)
  - [ ] Create `src/guarantee_email_agent/eval/reporter.py`
  - [ ] Import EvalResult model
  - [ ] Create `EvalReporter` class
  - [ ] Add logger with __name__

- [ ] Implement pass rate calculation (AC: calculates pass rate)
  - [ ] Create `calculate_pass_rate(results: List[EvalResult]) -> float` method
  - [ ] Count passed: sum(1 for r in results if r.passed)
  - [ ] Calculate rate: (passed / total) * 100
  - [ ] Return as percentage (0-100)
  - [ ] Handle edge case: 0 test cases → 0% pass rate

- [ ] Implement per-scenario reporting (AC: shows per-scenario results)
  - [ ] Create `print_scenario_results(results: List[EvalResult])` method
  - [ ] For each result, print: "✓ {scenario_id}: {description}" or "✗ {scenario_id}: {description} - FAILED"
  - [ ] Use colors if terminal supports (green ✓, red ✗)
  - [ ] Print in order: passed tests first, then failed
  - [ ] Include failure reasons for failed tests
  - [ ] Log all results at INFO level

- [ ] Implement summary reporting (AC: shows final pass rate)
  - [ ] Create `print_summary(results: List[EvalResult])` method
  - [ ] Calculate pass rate
  - [ ] Print: "Pass rate: {passed}/{total} ({percentage}%)"
  - [ ] Print: "✓ Passed: {passed}" in green
  - [ ] Print: "✗ Failed: {failed}" in red
  - [ ] Print: "Duration: {duration}s"
  - [ ] If pass rate ≥99%, print: "🎉 Eval passed! (≥99% threshold)"
  - [ ] If pass rate <99%, print: "⚠️  Eval failed (<99% threshold)"

- [ ] Implement detailed failure reporting (AC: detailed failure information logged)
  - [ ] Create `print_failure_details(result: EvalResult)` method
  - [ ] For each failure in result.failures:
    - [ ] Print failure reason
    - [ ] Print expected vs actual values
    - [ ] For response_body_contains: show missing phrases
    - [ ] For response_body_excludes: show present phrases
    - [ ] For ticket_created: show expected vs actual
    - [ ] For scenario_instruction_used: show expected vs actual
  - [ ] Include actual response excerpt for debugging
  - [ ] Format clearly for actionability

### CLI Eval Command

- [ ] Add eval command to CLI (AC: CLI command executes eval suite)
  - [ ] Add to `src/guarantee_email_agent/cli.py`
  - [ ] Add @app.command() for `eval`
  - [ ] Command description: "Run evaluation suite to validate agent correctness"
  - [ ] No required arguments (discovers all test cases)
  - [ ] Optional --eval-dir argument to specify test case directory
  - [ ] Make command async

- [ ] Implement eval command workflow (AC: discovers, executes, reports)
  - [ ] Create `eval(eval_dir: Path = "evals/scenarios/")` async function
  - [ ] Load configuration
  - [ ] Discover all test cases with EvalLoader
  - [ ] Print: "Running evaluation suite... ({count} scenarios)"
  - [ ] Run eval suite with EvalRunner
  - [ ] Print per-scenario results with EvalReporter
  - [ ] Print summary with pass rate
  - [ ] Return exit code based on pass rate

- [ ] Implement exit code logic (AC: exit code 0 if ≥99%, 4 if <99%)
  - [ ] Calculate pass rate from results
  - [ ] If pass_rate >= 99.0: return 0
  - [ ] If pass_rate < 99.0: return 4 (eval failure per NFR29)
  - [ ] Log exit code: "Exiting with code {code}"
  - [ ] Use sys.exit(code) to set exit code
  - [ ] Document exit codes in command help

- [ ] Add performance target (AC: completes within 5 minutes for ≤50 scenarios)
  - [ ] Track total suite execution time
  - [ ] Log: "Eval suite completed in {duration}s"
  - [ ] If duration >300s for ≤50 scenarios, log warning
  - [ ] Target: ~6s per scenario average (allows buffer)
  - [ ] Most time in LLM calls (mocked → fast)

- [ ] Make non-interactive for CI/CD (AC: suitable for CI/CD)
  - [ ] No prompts or user input during execution
  - [ ] All output to stdout/stderr
  - [ ] Exit code deterministic based on results
  - [ ] Works in headless environments
  - [ ] Example CI usage: `uv run python -m guarantee_email_agent eval || exit 1`

### Example Eval Test Cases

- [ ] Create example eval directory structure
  - [ ] Create `evals/` directory
  - [ ] Create `evals/scenarios/` directory
  - [ ] Add .gitkeep or README.md explaining structure
  - [ ] Document YAML format in README

- [ ] Create valid warranty eval case (AC: human-readable format)
  - [ ] Create `evals/scenarios/valid_warranty_001.yaml`
  - [ ] Scenario: Customer with valid warranty
  - [ ] Input: Email with serial number SN12345
  - [ ] Mock: Warranty API returns valid, expires 2025-12-31
  - [ ] Expected: Email sent, response contains "warranty is valid" and "2025-12-31", ticket created, scenario=valid-warranty
  - [ ] Processing time: <60000ms

- [ ] Create invalid warranty eval case
  - [ ] Create `evals/scenarios/invalid_warranty_001.yaml`
  - [ ] Scenario: Customer with expired warranty
  - [ ] Input: Email with serial number SN99999
  - [ ] Mock: Warranty API returns expired
  - [ ] Expected: Email sent, response contains "expired", response excludes "valid", no ticket, scenario=invalid-warranty

- [ ] Create missing serial eval case
  - [ ] Create `evals/scenarios/missing_info_001.yaml`
  - [ ] Scenario: Customer forgot serial number
  - [ ] Input: Email without serial number
  - [ ] Mock: N/A (no warranty API call)
  - [ ] Expected: Email sent, response contains "serial number", scenario=missing-info, no ticket

- [ ] Document eval YAML format
  - [ ] Create `evals/scenarios/README.md`
  - [ ] Document frontmatter fields
  - [ ] Document input section format
  - [ ] Document expected_output fields
  - [ ] Provide template for new test cases
  - [ ] Explain naming convention: {category}_{number}.yaml

### Testing

- [ ] Create eval loader tests
  - [ ] Create `tests/eval/test_loader.py`
  - [ ] Test load_eval_test_case() with valid YAML
  - [ ] Test validation with invalid YAML (missing fields)
  - [ ] Test discover_test_cases() finds all files
  - [ ] Test file naming pattern matching
  - [ ] Test error handling for malformed YAML
  - [ ] Use pytest tmp_path for test files

- [ ] Create mock framework tests
  - [ ] Create `tests/eval/test_mocks.py`
  - [ ] Test MockGmailClient captures sent emails
  - [ ] Test MockWarrantyAPIClient returns mock data
  - [ ] Test MockTicketingClient captures tickets
  - [ ] Test mock factory creates all clients
  - [ ] Test mocks are deterministic

- [ ] Create eval runner tests
  - [ ] Create `tests/eval/test_runner.py`
  - [ ] Test run_test_case() with passing scenario
  - [ ] Test run_test_case() with failing scenario
  - [ ] Test output validation logic
  - [ ] Test isolation between test cases
  - [ ] Test processing time measurement
  - [ ] Test suite execution
  - [ ] Mock EmailProcessor and integrations

- [ ] Create reporter tests
  - [ ] Create `tests/eval/test_reporter.py`
  - [ ] Test calculate_pass_rate() with various results
  - [ ] Test print_scenario_results() output format
  - [ ] Test print_summary() output
  - [ ] Test failure detail formatting
  - [ ] Capture stdout for assertions

- [ ] Create CLI eval command tests
  - [ ] Create `tests/test_cli_eval.py`
  - [ ] Test eval command with passing suite
  - [ ] Test eval command with failing suite
  - [ ] Test exit code 0 when ≥99%
  - [ ] Test exit code 4 when <99%
  - [ ] Test test case discovery
  - [ ] Use Typer testing utilities

- [ ] Create integration tests
  - [ ] Create `tests/eval/test_eval_integration.py`
  - [ ] Test complete eval flow: load → execute → validate → report
  - [ ] Test with multiple test cases
  - [ ] Test pass rate calculation accuracy
  - [ ] Test with real instruction files
  - [ ] Verify no production side effects

## Dev Notes

### Architecture Context

This story implements **Eval Framework Core** (consolidates old stories 5.1, 5.2, 5.3), establishing the evaluation system for measuring and improving agent correctness toward the 99% target.

**Key Architectural Principles:**
- FR49: Non-interactive eval command for CI/CD
- NFR1: 99% eval pass rate target
- NFR8: Eval suite completes in <5 minutes for ≤50 scenarios
- NFR27: Human-readable YAML test case format
- NFR29: Exit code 0 if ≥99%, code 4 if <99%

### Critical Implementation Rules from Project Context

**YAML Eval Test Case Format:**

```yaml
# evals/scenarios/valid_warranty_001.yaml
---
scenario_id: valid_warranty_001
description: "Customer with valid warranty requests status check"
category: valid-warranty
created: 2026-01-18
---

input:
  email:
    subject: "Warranty status inquiry"
    body: "Hi, I need to check my warranty status for serial number SN12345. Thanks!"
    from: "customer@example.com"
    received: "2026-01-18T10:00:00Z"

  mock_responses:
    warranty_api:
      status: "valid"
      expiration_date: "2025-12-31"
      coverage: "full"

expected_output:
  email_sent: true
  response_body_contains:
    - "warranty is valid"
    - "2025-12-31"
    - "fully covered"
  response_body_excludes:
    - "expired"
    - "invalid"
    - "not found"
  ticket_created: true
  ticket_fields:
    serial_number: "SN12345"
    warranty_status: "valid"
    priority: "normal"
    category: "warranty_claim"
  scenario_instruction_used: "valid-warranty"
  processing_time_ms: 60000  # Max acceptable time
```

**Eval Data Models:**

```python
# src/guarantee_email_agent/eval/models.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass(frozen=True)
class EvalEmail:
    """Email input for eval test case"""
    subject: str
    body: str
    from_address: str  # 'from' is Python keyword, use from_address
    received: str

@dataclass(frozen=True)
class EvalInput:
    """Input section of eval test case"""
    email: EvalEmail
    mock_responses: Dict[str, Dict]

@dataclass(frozen=True)
class EvalExpectedOutput:
    """Expected output section of eval test case"""
    email_sent: bool
    response_body_contains: List[str]
    response_body_excludes: List[str]
    ticket_created: bool
    ticket_fields: Optional[Dict[str, str]]
    scenario_instruction_used: str
    processing_time_ms: int

@dataclass(frozen=True)
class EvalTestCase:
    """Complete eval test case"""
    scenario_id: str
    description: str
    category: str
    created: str
    input: EvalInput
    expected_output: EvalExpectedOutput

@dataclass(frozen=True)
class EvalResult:
    """Result of executing one eval test case"""
    test_case: EvalTestCase
    passed: bool
    failures: List[str]
    actual_output: Dict
    processing_time_ms: int

    def format_for_display(self) -> str:
        """Format result for display"""
        status = "✓" if self.passed else "✗"
        result_text = f"{status} {self.test_case.scenario_id}: {self.test_case.description}"
        if not self.passed:
            result_text += " - FAILED"
        return result_text
```

**Eval Loader Implementation:**

```python
# src/guarantee_email_agent/eval/loader.py
import logging
from pathlib import Path
from typing import List, Dict, Any
import yaml
from guarantee_email_agent.eval.models import (
    EvalTestCase, EvalInput, EvalExpectedOutput, EvalEmail
)
from guarantee_email_agent.utils.errors import EvalError

logger = logging.getLogger(__name__)

class EvalLoader:
    """Load and validate eval test cases from YAML files"""

    def load_eval_test_case(self, file_path: str) -> EvalTestCase:
        """
        Load and parse single eval test case from YAML.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed EvalTestCase

        Raises:
            EvalError: If YAML invalid or schema validation fails
        """
        try:
            # Read YAML file
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            # Validate schema
            self.validate_test_case(data, file_path)

            # Parse sections
            eval_email = EvalEmail(
                subject=data['input']['email']['subject'],
                body=data['input']['email']['body'],
                from_address=data['input']['email']['from'],
                received=data['input']['email']['received']
            )

            eval_input = EvalInput(
                email=eval_email,
                mock_responses=data['input'].get('mock_responses', {})
            )

            eval_expected = EvalExpectedOutput(
                email_sent=data['expected_output']['email_sent'],
                response_body_contains=data['expected_output'].get('response_body_contains', []),
                response_body_excludes=data['expected_output'].get('response_body_excludes', []),
                ticket_created=data['expected_output']['ticket_created'],
                ticket_fields=data['expected_output'].get('ticket_fields'),
                scenario_instruction_used=data['expected_output']['scenario_instruction_used'],
                processing_time_ms=data['expected_output'].get('processing_time_ms', 60000)
            )

            test_case = EvalTestCase(
                scenario_id=data['scenario_id'],
                description=data['description'],
                category=data['category'],
                created=data['created'],
                input=eval_input,
                expected_output=eval_expected
            )

            logger.debug(f"Loaded eval test case: {test_case.scenario_id}")
            return test_case

        except FileNotFoundError:
            raise EvalError(
                message=f"Eval file not found: {file_path}",
                code="eval_file_not_found",
                details={"file_path": file_path}
            )
        except yaml.YAMLError as e:
            raise EvalError(
                message=f"Invalid YAML in eval file: {file_path}",
                code="eval_yaml_invalid",
                details={"file_path": file_path, "error": str(e)}
            )
        except KeyError as e:
            raise EvalError(
                message=f"Missing required field in eval file: {file_path} - {e}",
                code="eval_missing_field",
                details={"file_path": file_path, "field": str(e)}
            )

    def validate_test_case(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Validate eval test case schema.

        Args:
            data: Parsed YAML data
            file_path: File path for error messages

        Raises:
            EvalError: If validation fails
        """
        required_top_level = ['scenario_id', 'description', 'category', 'created', 'input', 'expected_output']
        for field in required_top_level:
            if field not in data:
                raise EvalError(
                    message=f"Missing required field: {field}",
                    code="eval_missing_field",
                    details={"file_path": file_path, "field": field}
                )

        # Validate input section
        if 'email' not in data['input']:
            raise EvalError(
                message="Missing input.email section",
                code="eval_missing_field",
                details={"file_path": file_path, "field": "input.email"}
            )

        required_email_fields = ['subject', 'body', 'from', 'received']
        for field in required_email_fields:
            if field not in data['input']['email']:
                raise EvalError(
                    message=f"Missing input.email.{field}",
                    code="eval_missing_field",
                    details={"file_path": file_path, "field": f"input.email.{field}"}
                )

        # Validate expected_output section
        required_output_fields = ['email_sent', 'ticket_created', 'scenario_instruction_used']
        for field in required_output_fields:
            if field not in data['expected_output']:
                raise EvalError(
                    message=f"Missing expected_output.{field}",
                    code="eval_missing_field",
                    details={"file_path": file_path, "field": f"expected_output.{field}"}
                )

    def discover_test_cases(self, directory: str) -> List[EvalTestCase]:
        """
        Discover all eval test cases in directory.

        Args:
            directory: Path to evals/scenarios directory

        Returns:
            List of EvalTestCase objects

        Note:
            Files must match pattern: {category}_{number}.yaml
        """
        test_cases = []
        eval_dir = Path(directory)

        if not eval_dir.exists():
            logger.warning(f"Eval directory not found: {directory}")
            return []

        # Find all .yaml files
        yaml_files = sorted(eval_dir.glob("*.yaml"))

        logger.info(f"Discovering eval test cases in {directory}")

        for yaml_file in yaml_files:
            try:
                test_case = self.load_eval_test_case(str(yaml_file))
                test_cases.append(test_case)
                logger.debug(f"Discovered: {test_case.scenario_id}")
            except EvalError as e:
                logger.error(f"Failed to load {yaml_file.name}: {e.message}")
                # Continue loading other files

        logger.info(f"Discovered {len(test_cases)} eval test cases")
        return test_cases
```

**Mock Framework Implementation:**

```python
# src/guarantee_email_agent/eval/mocks.py
import logging
from typing import Dict, List, Any, Optional
from guarantee_email_agent.eval.models import EvalTestCase

logger = logging.getLogger(__name__)

class MockGmailClient:
    """Mock Gmail MCP client for eval"""

    def __init__(self, test_case: EvalTestCase):
        """Initialize with test case data

        Args:
            test_case: Eval test case with input email
        """
        self.test_case = test_case
        self.sent_emails = []

    async def get_unread_emails(self) -> List[Dict[str, Any]]:
        """Return email from test case"""
        # Not used in eval (email provided directly)
        return []

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None
    ) -> None:
        """Capture sent email (don't actually send)

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            thread_id: Optional thread ID
        """
        sent_email = {
            "to": to,
            "subject": subject,
            "body": body,
            "thread_id": thread_id
        }
        self.sent_emails.append(sent_email)
        logger.debug(f"Mock: Email sent to {to}")

    async def close(self) -> None:
        """Close connection (no-op for mock)"""
        pass

class MockWarrantyAPIClient:
    """Mock Warranty API MCP client for eval"""

    def __init__(self, test_case: EvalTestCase):
        """Initialize with mock responses from test case

        Args:
            test_case: Eval test case with mock_responses
        """
        self.mock_responses = test_case.input.mock_responses.get('warranty_api', {})

    async def check_warranty(self, serial_number: str) -> Dict[str, Any]:
        """Return mock warranty data

        Args:
            serial_number: Serial number to check

        Returns:
            Mock warranty data from test case
        """
        logger.debug(f"Mock: Checking warranty for {serial_number}")
        return self.mock_responses

    async def test_connection(self) -> None:
        """Test connection (no-op for mock)"""
        pass

    async def close(self) -> None:
        """Close connection (no-op for mock)"""
        pass

class MockTicketingClient:
    """Mock Ticketing MCP client for eval"""

    def __init__(self):
        """Initialize mock ticketing client"""
        self.created_tickets = []

    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, str]:
        """Capture ticket data (don't actually create)

        Args:
            ticket_data: Ticket data to create

        Returns:
            Mock ticket ID
        """
        ticket_id = f"MOCK-TICKET-{len(self.created_tickets) + 1:03d}"
        ticket = {
            "ticket_id": ticket_id,
            "data": ticket_data
        }
        self.created_tickets.append(ticket)
        logger.debug(f"Mock: Ticket created: {ticket_id}")
        return {"ticket_id": ticket_id}

    async def test_connection(self) -> None:
        """Test connection (no-op for mock)"""
        pass

    async def close(self) -> None:
        """Close connection (no-op for mock)"""
        pass

def create_mock_clients(test_case: EvalTestCase) -> Dict[str, Any]:
    """
    Create mock clients for eval execution.

    Args:
        test_case: Eval test case

    Returns:
        Dict with mock client instances
    """
    return {
        "gmail": MockGmailClient(test_case),
        "warranty": MockWarrantyAPIClient(test_case),
        "ticketing": MockTicketingClient()
    }
```

**Eval Runner Implementation (Partial):**

```python
# src/guarantee_email_agent/eval/runner.py
import asyncio
import logging
import time
from typing import List, Tuple
from guarantee_email_agent.config.loader import load_config
from guarantee_email_agent.email.processor import EmailProcessor
from guarantee_email_agent.eval.models import EvalTestCase, EvalResult, EvalExpectedOutput
from guarantee_email_agent.eval.mocks import create_mock_clients
from guarantee_email_agent.email.processor_models import ProcessingResult

logger = logging.getLogger(__name__)

class EvalRunner:
    """Execute eval test cases and validate results"""

    def __init__(self, config):
        """Initialize eval runner

        Args:
            config: Agent configuration
        """
        self.config = config
        logger.info("Eval runner initialized")

    async def run_test_case(self, test_case: EvalTestCase) -> EvalResult:
        """
        Execute single eval test case.

        Args:
            test_case: Eval test case to execute

        Returns:
            EvalResult with pass/fail and details
        """
        logger.info(f"Executing eval: {test_case.scenario_id}")

        start_time = time.time()

        try:
            # Create mock clients
            mocks = create_mock_clients(test_case)

            # Create processor with mocked clients
            # (In real implementation, inject mocks via DI)
            processor = self._create_processor_with_mocks(mocks)

            # Convert test case input to raw_email format
            raw_email = {
                "subject": test_case.input.email.subject,
                "body": test_case.input.email.body,
                "from": test_case.input.email.from_address,
                "received": test_case.input.email.received,
                "message_id": f"eval-{test_case.scenario_id}"
            }

            # Execute processing
            result = await processor.process_email(raw_email)

            # Measure processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Validate output
            passed, failures = self.validate_output(
                test_case.expected_output,
                result,
                mocks,
                processing_time_ms
            )

            # Build actual output for reporting
            actual_output = {
                "email_sent": len(mocks["gmail"].sent_emails) > 0,
                "response_body": mocks["gmail"].sent_emails[0]["body"] if mocks["gmail"].sent_emails else "",
                "ticket_created": len(mocks["ticketing"].created_tickets) > 0,
                "scenario_used": result.scenario_used,
                "processing_time_ms": processing_time_ms
            }

            return EvalResult(
                test_case=test_case,
                passed=passed,
                failures=failures,
                actual_output=actual_output,
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"Eval execution failed: {test_case.scenario_id} - {e}", exc_info=True)
            return EvalResult(
                test_case=test_case,
                passed=False,
                failures=[f"Execution error: {str(e)}"],
                actual_output={},
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

    def validate_output(
        self,
        expected: EvalExpectedOutput,
        actual: ProcessingResult,
        mocks: Dict,
        processing_time_ms: int
    ) -> Tuple[bool, List[str]]:
        """
        Validate actual output against expected output.

        Args:
            expected: Expected output from test case
            actual: Actual ProcessingResult
            mocks: Mock clients with captured data
            processing_time_ms: Actual processing time

        Returns:
            Tuple of (passed, list of failure reasons)
        """
        failures = []

        # Check email sent
        email_sent = len(mocks["gmail"].sent_emails) > 0
        if expected.email_sent != email_sent:
            failures.append(f"email_sent: expected {expected.email_sent}, got {email_sent}")

        # Check response body contains
        if mocks["gmail"].sent_emails:
            response_body = mocks["gmail"].sent_emails[0]["body"]
            for phrase in expected.response_body_contains:
                if phrase.lower() not in response_body.lower():
                    failures.append(f"response_body_contains: missing phrase '{phrase}'")

            # Check response body excludes
            for phrase in expected.response_body_excludes:
                if phrase.lower() in response_body.lower():
                    failures.append(f"response_body_excludes: unwanted phrase '{phrase}' present")

        # Check ticket created
        ticket_created = len(mocks["ticketing"].created_tickets) > 0
        if expected.ticket_created != ticket_created:
            failures.append(f"ticket_created: expected {expected.ticket_created}, got {ticket_created}")

        # Check ticket fields if ticket created
        if expected.ticket_created and ticket_created and expected.ticket_fields:
            actual_ticket = mocks["ticketing"].created_tickets[0]["data"]
            for key, expected_value in expected.ticket_fields.items():
                if actual_ticket.get(key) != expected_value:
                    failures.append(
                        f"ticket_field[{key}]: expected '{expected_value}', "
                        f"got '{actual_ticket.get(key)}'"
                    )

        # Check scenario instruction used
        if expected.scenario_instruction_used != actual.scenario_used:
            failures.append(
                f"scenario_instruction_used: expected '{expected.scenario_instruction_used}', "
                f"got '{actual.scenario_used}'"
            )

        # Check processing time
        if processing_time_ms > expected.processing_time_ms:
            failures.append(
                f"processing_time_ms: {processing_time_ms}ms exceeds threshold "
                f"{expected.processing_time_ms}ms"
            )

        passed = len(failures) == 0
        return passed, failures

    async def run_suite(self, test_cases: List[EvalTestCase]) -> List[EvalResult]:
        """
        Execute complete eval suite.

        Args:
            test_cases: List of eval test cases

        Returns:
            List of EvalResults
        """
        logger.info(f"Running eval suite: {len(test_cases)} scenarios")

        results = []
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Executing {i}/{len(test_cases)}: {test_case.scenario_id}")
            result = await self.run_test_case(test_case)
            results.append(result)

        logger.info(f"Eval suite complete: {len(results)} results")
        return results

    def _create_processor_with_mocks(self, mocks: Dict) -> EmailProcessor:
        """Create EmailProcessor with mocked clients (DI)"""
        # In real implementation, this would inject mocks
        # For now, placeholder
        pass
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Using real APIs in eval:**
   ```python
   # WRONG - Real API calls during eval
   warranty_client = WarrantyAPIClient(config)  # Real client!
   result = await warranty_client.check_warranty(serial)

   # CORRECT - Mock clients
   mock_client = MockWarrantyAPIClient(test_case)
   result = await mock_client.check_warranty(serial)
   ```

2. **Shared state between test cases:**
   ```python
   # WRONG - Shared mocks between tests
   mocks = create_mock_clients(test_cases[0])
   for test in test_cases:
       result = await run_test(test, mocks)  # State accumulates!

   # CORRECT - Fresh mocks per test
   for test in test_cases:
       mocks = create_mock_clients(test)  # Fresh state
       result = await run_test(test, mocks)
   ```

3. **Wrong exit code:**
   ```python
   # WRONG - Generic exit code
   if pass_rate < 99:
       sys.exit(1)  # Should be 4!

   # CORRECT - Exit code 4 for eval failure
   if pass_rate < 99:
       sys.exit(4)  # NFR29
   ```

4. **Missing validation checks:**
   ```python
   # WRONG - Only checking email sent
   if mocks["gmail"].sent_emails:
       return True

   # CORRECT - Check all expected output fields
   failures = []
   if email_sent != expected.email_sent:
       failures.append("email_sent mismatch")
   for phrase in expected.response_body_contains:
       if phrase not in response:
           failures.append(f"missing phrase: {phrase}")
   # ... check all fields
   ```

5. **Not making eval reproducible:**
   ```python
   # WRONG - Non-deterministic mock responses
   return {"status": random.choice(["valid", "expired"])}

   # CORRECT - Deterministic from test case
   return test_case.input.mock_responses["warranty_api"]
   ```

### Verification Commands

```bash
# 1. Create sample eval test case
mkdir -p evals/scenarios
cat > evals/scenarios/valid_warranty_001.yaml << 'EOF'
---
scenario_id: valid_warranty_001
description: "Customer with valid warranty"
category: valid-warranty
created: 2026-01-18
---
input:
  email:
    subject: "Warranty check"
    body: "Hi, I need warranty info for SN12345"
    from: "test@example.com"
    received: "2026-01-18T10:00:00Z"
  mock_responses:
    warranty_api:
      status: "valid"
      expiration_date: "2025-12-31"
expected_output:
  email_sent: true
  response_body_contains:
    - "warranty is valid"
    - "2025-12-31"
  response_body_excludes:
    - "expired"
  ticket_created: true
  ticket_fields:
    serial_number: "SN12345"
    warranty_status: "valid"
  scenario_instruction_used: "valid-warranty"
  processing_time_ms: 60000
EOF

# 2. Test eval loader
uv run python -c "
from guarantee_email_agent.eval.loader import EvalLoader

loader = EvalLoader()
test_case = loader.load_eval_test_case('evals/scenarios/valid_warranty_001.yaml')
print(f'Loaded: {test_case.scenario_id} - {test_case.description}')
"

# 3. Test eval discovery
uv run python -c "
from guarantee_email_agent.eval.loader import EvalLoader

loader = EvalLoader()
test_cases = loader.discover_test_cases('evals/scenarios/')
print(f'Discovered {len(test_cases)} test cases')
"

# 4. Run eval command
uv run python -m guarantee_email_agent eval

# 5. Check exit code
uv run python -m guarantee_email_agent eval
echo "Exit code: $?"

# 6. Run with explicit directory
uv run python -m guarantee_email_agent eval --eval-dir evals/scenarios

# 7. Run unit tests
uv run pytest tests/eval/test_loader.py -v
uv run pytest tests/eval/test_mocks.py -v
uv run pytest tests/eval/test_runner.py -v
uv run pytest tests/eval/test_reporter.py -v

# 8. Test in CI/CD
uv run python -m guarantee_email_agent eval || echo "Eval failed with $?"
```

### Dependency Notes

**Depends on:**
- Epic 3: Complete email processing pipeline
- Story 3.4: EmailProcessor for execution
- Story 3.2: Scenario instructions
- Story 3.1: Main instruction
- All Epic 1 stories for configuration

**Blocks:**
- Story 4.2: Reporting and continuous improvement (uses this framework)
- Production deployment: 99% pass rate required

**Integration Points:**
- EvalRunner → EmailProcessor → complete pipeline
- Mock clients → replace real MCP clients via DI
- YAML test cases → instruction files (production)
- Pass rate → exit code for CI/CD

### Previous Story Intelligence

From Story 3.6 (Logging and Graceful Degradation):
- Structured logging with extra dict
- Error context enrichment
- Performance timing patterns

From Story 3.4 (Email Processing Pipeline):
- ProcessingResult dataclass
- Complete processing flow
- Error handling at each step

From Story 3.2 (Scenario Routing):
- Scenario instruction files
- Graceful-degradation fallback

**Learnings to Apply:**
- Dataclasses for all eval models
- Comprehensive validation with clear errors
- Deterministic execution for reproducibility
- Clear pass/fail criteria
- Actionable failure reporting

### Git Intelligence Summary

Recent commits show:
- Dataclass patterns for structured data
- YAML parsing with validation
- Factory functions for object creation
- Comprehensive error handling
- Testing with mocked dependencies

**Code Patterns to Continue:**
- @dataclass(frozen=True) for immutability
- Schema validation with clear errors
- Mock framework with deterministic behavior
- Exit codes for automation
- Structured reporting with ✓/✗ symbols

### References

**Architecture Document Sections:**
- [Source: architecture.md#Eval Framework] - Test case format and execution
- [Source: architecture.md#Mock Strategy] - MCP and LLM mocking
- [Source: project-context.md#Exit Codes] - NFR29 requirements

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 4: Story 4.1] - Complete acceptance criteria
- [Source: prd.md#NFR1] - 99% eval pass rate target
- [Source: prd.md#NFR8] - 5-minute suite completion
- [Source: prd.md#NFR27] - Human-readable YAML format
- [Source: prd.md#NFR29] - Exit code 4 for eval failure
- [Source: prd.md#FR49] - Non-interactive for CI/CD

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context from all Epic 3 stories
- Story consolidates 3 original stories (5.1, 5.2, 5.3)
- YAML eval test case format with frontmatter + input + expected_output
- EvalTestCase, EvalInput, EvalExpectedOutput, EvalResult dataclasses
- EvalLoader with YAML parsing and validation
- Mock framework: Gmail, Warranty API, Ticketing, Anthropic clients
- EvalRunner executes test cases with mocked integrations
- Output validation: email_sent, response_body_contains/excludes, ticket_created, scenario, timing
- EvalReporter calculates pass rate and formats results
- CLI eval command: discover → execute → validate → report → exit code
- Exit code 0 if ≥99%, code 4 if <99% (NFR29)
- Non-interactive for CI/CD integration
- Complete isolation between test cases
- Example eval test cases with documentation
- Testing strategy: loader, mocks, runner, reporter, CLI, integration
- Verification commands for eval workflow

### File List

**Eval Data Models:**
- `src/guarantee_email_agent/eval/models.py` - EvalTestCase and related dataclasses

**Eval Loader:**
- `src/guarantee_email_agent/eval/loader.py` - YAML loading and validation

**Mock Framework:**
- `src/guarantee_email_agent/eval/mocks.py` - Mock MCP clients and LLM

**Eval Runner:**
- `src/guarantee_email_agent/eval/runner.py` - Test case execution and validation

**Eval Reporter:**
- `src/guarantee_email_agent/eval/reporter.py` - Pass rate calculation and reporting

**CLI Update:**
- `src/guarantee_email_agent/cli.py` - Add eval command

**Module Exports:**
- `src/guarantee_email_agent/eval/__init__.py` - Eval module exports

**Example Eval Cases:**
- `evals/scenarios/valid_warranty_001.yaml` - Valid warranty example
- `evals/scenarios/invalid_warranty_001.yaml` - Invalid warranty example
- `evals/scenarios/missing_info_001.yaml` - Missing serial example
- `evals/scenarios/README.md` - Format documentation

**Tests:**
- `tests/eval/test_loader.py` - Eval loader tests
- `tests/eval/test_mocks.py` - Mock framework tests
- `tests/eval/test_runner.py` - Eval runner tests
- `tests/eval/test_reporter.py` - Reporter tests
- `tests/test_cli_eval.py` - CLI eval command tests
- `tests/eval/test_eval_integration.py` - End-to-end integration tests
