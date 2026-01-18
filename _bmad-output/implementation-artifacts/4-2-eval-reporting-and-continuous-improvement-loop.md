# Story 4.2: Eval Reporting and Continuous Improvement Loop

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want detailed failure reporting and the ability to add failed cases to the eval suite,
So that I can refine instructions iteratively and prevent regressions.

## Acceptance Criteria

**Given** The eval command from Story 4.1 runs
**When** Some scenarios fail or real-world failures occur

**Then - Failed Scenario Reporting:**
**And** Reporter provides detailed failure information for each failed scenario
**And** Failure details: scenario_id, description, expected vs actual values
**And** For response_body_contains: shows expected phrases and actual response excerpt
**And** For response_body_excludes: shows phrases present but should be absent
**And** For ticket_created: shows expected vs actual creation status
**And** For scenario_instruction_used: shows expected vs actual scenario
**And** Processing time failures show: expected threshold vs actual time
**And** Output clear and actionable: "FAILED: valid_warranty_001 - Expected 'warranty is valid', got 'warranty has expired'"
**And** Failed scenarios logged with full context
**And** Output helps identify if failure is instruction refinement or code bug
**And** Failure report includes actual response body for debugging
**And** Reporter suggests potential fixes based on failure type

**Then - Continuous Improvement Loop:**
**And** When real-world email fails processing, can create new YAML eval case
**And** New test case captures: actual email, expected behavior, current failure
**And** Adding to `evals/scenarios/` includes it in next eval run
**And** Re-running `agent eval` shows new scenario in results
**And** Failed evals added to permanent suite (continuous improvement per FR32)
**And** Process documented: failed email → YAML case → refine instructions → re-run eval
**And** New cases follow same YAML format and naming convention
**And** Suite can grow from 10-20 to 50+ scenarios over time
**And** NEVER delete passing scenarios - prevent regression (FR33)
**And** Template provided for creating new test cases quickly
**And** Documentation explains how to convert real failures to eval cases

**Then - Instruction Refinement Validation:**
**And** When modifying instruction files to fix failed eval
**And** Re-run `agent eval` to validate against updated instructions
**And** Framework loads modified instructions (not cached from previous run)
**And** Previously passing scenarios must still pass
**And** Target failed scenario should now pass after refinement
**And** If changes break passing scenarios, pass rate decreases visibly
**And** Workflow: identify failed → refine instructions → re-run full suite → verify maintained/improved
**And** Safe iterative refinement without breaking existing behavior
**And** Eval suite acts as regression prevention (FR32)
**And** CTO can iterate toward 99% with confidence
**And** Diff report shows: which scenarios changed status (pass→fail, fail→pass)

**Then - Detailed Failure Analysis:**
**And** Reporter categorizes failure types: response content, scenario routing, ticket creation, performance
**And** Failure reports include confidence score for suggested fixes
**And** For scenario routing failures: suggests reviewing scenario detection logic
**And** For response content failures: suggests refining scenario instruction files
**And** For ticket creation failures: suggests reviewing ticket creation logic
**And** For performance failures: suggests optimization targets
**And** Reporter highlights patterns: multiple failures in same category

## Tasks / Subtasks

### Enhanced Failure Reporting

- [ ] Extend reporter with detailed failure output (AC: detailed failure information)
  - [ ] Update `src/guarantee_email_agent/eval/reporter.py`
  - [ ] Add `print_detailed_failures(results: List[EvalResult])` method
  - [ ] For each failed result, print comprehensive failure analysis
  - [ ] Include scenario_id, description, category
  - [ ] Show all failure reasons from result.failures list
  - [ ] Format for readability with clear sections

- [ ] Implement expected vs actual comparison (AC: shows expected vs actual values)
  - [ ] Create `format_failure_comparison(failure: str, expected: Any, actual: Any) -> str` helper
  - [ ] For response_body_contains failures:
    - [ ] Show expected phrase: "Expected phrase: 'warranty is valid'"
    - [ ] Show actual response excerpt: "Actual response: '...warranty has expired...'"
    - [ ] Highlight context around missing phrase
  - [ ] For response_body_excludes failures:
    - [ ] Show excluded phrase that was present
    - [ ] Show where it appears in actual response
  - [ ] For ticket_created failures:
    - [ ] Show: "Expected ticket: True, Actual: False"
  - [ ] For scenario_instruction_used failures:
    - [ ] Show: "Expected scenario: 'valid-warranty', Actual: 'invalid-warranty'"

- [ ] Add actual response body display (AC: includes actual response body)
  - [ ] Include full response body in failure details
  - [ ] Truncate if >500 chars (show first 300 + "..." + last 200)
  - [ ] Format with indentation for readability
  - [ ] Example:
    ```
    Actual Response Body:
    ---
    Dear customer,
    Your warranty has expired...
    ---
    ```

- [ ] Implement actionable output (AC: output helps identify issue)
  - [ ] For each failure type, suggest likely cause
  - [ ] Response content issue → "Review scenario instruction: {scenario}.md"
  - [ ] Scenario routing issue → "Review scenario detection logic in scenario_detector.py"
  - [ ] Ticket creation issue → "Review ticket creation in processor.py"
  - [ ] Performance issue → "Optimize step: {slow_step}"
  - [ ] Include file paths for quick navigation

- [ ] Add failure categorization (AC: categorizes failure types)
  - [ ] Create `categorize_failure(failure: str) -> str` helper
  - [ ] Categories: "response_content", "scenario_routing", "ticket_creation", "performance", "other"
  - [ ] Group failures by category in report
  - [ ] Show category summary: "Response Content: 3 failures, Scenario Routing: 1 failure"
  - [ ] Help identify systematic issues

- [ ] Implement pattern detection (AC: highlights patterns)
  - [ ] Analyze all failures for common patterns
  - [ ] Detect: multiple failures in same category
  - [ ] Detect: multiple failures for same scenario instruction
  - [ ] Detect: multiple performance failures in same step
  - [ ] Report patterns: "Pattern detected: 3 failures in missing-info scenarios"
  - [ ] Suggest bulk fixes: "Consider reviewing missing-info.md instruction"

### Continuous Improvement Workflow

- [ ] Create eval case template (AC: template for new test cases)
  - [ ] Create `evals/scenarios/_TEMPLATE.yaml`
  - [ ] Include all required sections with comments
  - [ ] Provide examples for each field
  - [ ] Document field meanings
  - [ ] Example values for guidance
  - [ ] Instructions for using template

- [ ] Document conversion process (AC: process documented)
  - [ ] Create `evals/scenarios/README.md` (if not exists from 4.1)
  - [ ] Section: "Adding Failed Cases to Eval Suite"
  - [ ] Step 1: Capture real-world failure (email content, error logs)
  - [ ] Step 2: Create new YAML file using template
  - [ ] Step 3: Fill input section with actual email
  - [ ] Step 4: Define expected behavior
  - [ ] Step 5: Add to evals/scenarios/ directory
  - [ ] Step 6: Re-run eval to verify test case works
  - [ ] Step 7: Refine instructions to fix failure
  - [ ] Step 8: Re-run eval to verify fix

- [ ] Create helper script for case creation (AC: can create new YAML case)
  - [ ] Create `scripts/create_eval_case.py` helper script
  - [ ] Prompt for: scenario_id, description, category
  - [ ] Prompt for: email subject, body, from
  - [ ] Prompt for: expected scenario, ticket creation
  - [ ] Generate YAML file from template
  - [ ] Save to evals/scenarios/ with correct naming
  - [ ] Validate generated YAML
  - [ ] Usage: `uv run python scripts/create_eval_case.py`

- [ ] Document regression prevention (AC: NEVER delete passing scenarios)
  - [ ] Add section to README: "Regression Prevention"
  - [ ] Rule: Once a scenario passes, never delete it
  - [ ] Keep all passing scenarios in suite permanently
  - [ ] If scenario becomes irrelevant, mark as deprecated but keep
  - [ ] Suite acts as living documentation of agent behavior
  - [ ] Growing suite ensures no regressions

- [ ] Add suite growth guidance (AC: suite can grow to 50+ scenarios)
  - [ ] Document expected suite growth trajectory
  - [ ] Start: 10-20 basic scenarios (MVP)
  - [ ] Growth: Add 2-5 scenarios per real-world failure
  - [ ] Target: 50+ scenarios for comprehensive coverage
  - [ ] Organize by category subdirectories if >50 cases
  - [ ] Example structure: `evals/scenarios/valid-warranty/`, `evals/scenarios/missing-info/`
  - [ ] Performance: suite completes in <5 min up to 50 scenarios

### Instruction Refinement Validation

- [ ] Implement cache clearing (AC: loads modified instructions)
  - [ ] Update eval runner to clear instruction cache before run
  - [ ] Ensure instruction files reloaded on each eval execution
  - [ ] Don't use cached instructions from previous run
  - [ ] Log: "Clearing instruction cache for fresh eval run"
  - [ ] Verify instruction file mtimes for changes

- [ ] Add pre/post comparison reporting (AC: diff report shows changes)
  - [ ] Create `EvalComparison` dataclass to store before/after results
  - [ ] Store previous eval results in `.eval-results.json` (optional)
  - [ ] Compare current run to previous run
  - [ ] Show scenarios that changed status:
    - [ ] Pass → Fail (regression!)
    - [ ] Fail → Pass (improvement!)
    - [ ] New scenarios (added since last run)
  - [ ] Print diff summary: "+2 now passing, -1 regressed, +3 new scenarios"

- [ ] Implement regression detection (AC: if changes break passing scenarios)
  - [ ] Track which scenarios passed in previous run
  - [ ] Alert if previously passing scenario now fails
  - [ ] Print prominent warning: "⚠️  REGRESSION: valid_warranty_001 now fails!"
  - [ ] List all regressions at end of report
  - [ ] Suggest reverting instruction changes if regressions detected
  - [ ] Exit with warning even if overall pass rate ≥99%

- [ ] Add pass rate trend tracking (AC: can iterate toward 99%)
  - [ ] Store historical pass rates in `.eval-history.json`
  - [ ] Track: date, pass_rate, total_scenarios, passed, failed
  - [ ] Show trend: "Pass rate: 34/35 (97.1%) ↑ from 32/35 (91.4%)"
  - [ ] Visualize progress toward 99% goal
  - [ ] Log all runs for historical analysis
  - [ ] Optional: generate trend chart (ASCII or link to data)

- [ ] Create refinement workflow documentation (AC: workflow documented)
  - [ ] Create `docs/eval-refinement-workflow.md`
  - [ ] Document complete refinement cycle
  - [ ] Example: Failed scenario "missing_info_003"
  - [ ] Step 1: Run eval, identify failure
  - [ ] Step 2: Review failure details
  - [ ] Step 3: Identify instruction file to modify
  - [ ] Step 4: Edit instruction file (e.g., missing-info.md)
  - [ ] Step 5: Re-run eval with: `uv run python -m guarantee_email_agent eval`
  - [ ] Step 6: Verify target scenario now passes
  - [ ] Step 7: Check no regressions in other scenarios
  - [ ] Step 8: Commit instruction changes
  - [ ] Provide examples of common refinements

### Suggested Fix Generation

- [ ] Create fix suggestion engine (AC: suggests potential fixes)
  - [ ] Create `src/guarantee_email_agent/eval/suggestions.py`
  - [ ] Analyze failure type and suggest fix
  - [ ] Use heuristics to generate suggestions
  - [ ] Create `SuggestedFix` dataclass with: fix_type, confidence, description, action

- [ ] Implement response content fix suggestions (AC: for response content failures)
  - [ ] Analyze response_body_contains failures
  - [ ] Suggest: "Add phrase to scenario instruction response template"
  - [ ] Suggest: "Review response generation logic"
  - [ ] Include instruction file path: `instructions/scenarios/{scenario}.md`
  - [ ] Confidence: high if pattern detected, medium otherwise

- [ ] Implement scenario routing fix suggestions (AC: for scenario routing failures)
  - [ ] Analyze scenario_instruction_used failures
  - [ ] Suggest: "Review scenario detection heuristics"
  - [ ] Suggest: "Add/modify trigger keywords"
  - [ ] Include detector file path: `src/guarantee_email_agent/email/scenario_detector.py`
  - [ ] Show expected vs actual scenario with reasoning

- [ ] Implement ticket creation fix suggestions (AC: for ticket creation failures)
  - [ ] Analyze ticket_created failures
  - [ ] Suggest: "Review warranty status → ticket creation logic"
  - [ ] Suggest: "Check ticket_fields mapping"
  - [ ] Include processor file path: `src/guarantee_email_agent/email/processor.py`
  - [ ] Show ticket data captured in eval

- [ ] Implement performance fix suggestions (AC: for performance failures)
  - [ ] Analyze processing_time_ms failures
  - [ ] Identify slow step from step timings
  - [ ] Suggest: "Optimize {step_name} (took {duration}ms, threshold: {threshold}ms)"
  - [ ] Suggest specific optimizations:
    - [ ] LLM calls: "Consider reducing prompt size"
    - [ ] API calls: "Consider caching or parallel execution"
    - [ ] Parsing: "Consider optimizing regex patterns"

- [ ] Add confidence scoring (AC: confidence score for suggestions)
  - [ ] Score suggestions: high (0.8-1.0), medium (0.5-0.8), low (0.0-0.5)
  - [ ] High confidence: Pattern detected across multiple failures
  - [ ] Medium confidence: Single failure with clear cause
  - [ ] Low confidence: Ambiguous failure, multiple possible causes
  - [ ] Display confidence: "Suggested fix (confidence: high):"

### Enhanced CLI Output

- [ ] Add verbose mode for detailed output (AC: detailed output option)
  - [ ] Add --verbose flag to eval command
  - [ ] In verbose mode, show detailed failures automatically
  - [ ] In non-verbose mode, show summary only
  - [ ] Usage: `uv run python -m guarantee_email_agent eval --verbose`
  - [ ] Document flag in command help

- [ ] Implement failure-only reporting option
  - [ ] Add --failures-only flag to eval command
  - [ ] Show only failed scenarios (skip passed scenarios)
  - [ ] Useful for focusing on issues when many tests pass
  - [ ] Usage: `uv run python -m guarantee_email_agent eval --failures-only`

- [ ] Add JSON output option for automation
  - [ ] Add --output-json flag to eval command
  - [ ] Output eval results as JSON to stdout
  - [ ] Format: {"pass_rate": 97.1, "passed": 34, "failed": 1, "failures": [...]}
  - [ ] Useful for CI/CD dashboards and tracking
  - [ ] Usage: `uv run python -m guarantee_email_agent eval --output-json`

- [ ] Create summary-only mode
  - [ ] Add --summary flag to eval command
  - [ ] Show only: pass rate, total, passed, failed counts
  - [ ] No per-scenario details
  - [ ] Fast overview for quick checks
  - [ ] Usage: `uv run python -m guarantee_email_agent eval --summary`

### Testing

- [ ] Create detailed reporter tests
  - [ ] Create `tests/eval/test_reporter_detailed.py`
  - [ ] Test print_detailed_failures() with various failure types
  - [ ] Test expected vs actual formatting
  - [ ] Test failure categorization
  - [ ] Test pattern detection
  - [ ] Capture stdout for assertions

- [ ] Create suggestion engine tests
  - [ ] Create `tests/eval/test_suggestions.py`
  - [ ] Test fix suggestions for each failure type
  - [ ] Test confidence scoring
  - [ ] Test suggestion formatting
  - [ ] Verify actionable output

- [ ] Create regression detection tests
  - [ ] Test comparison of eval results
  - [ ] Test regression detection (pass→fail)
  - [ ] Test improvement detection (fail→pass)
  - [ ] Test with mock previous results

- [ ] Create CLI flag tests
  - [ ] Test --verbose flag
  - [ ] Test --failures-only flag
  - [ ] Test --output-json flag
  - [ ] Test --summary flag
  - [ ] Verify output formats

- [ ] Create integration tests
  - [ ] Test complete refinement workflow
  - [ ] Test adding new eval case
  - [ ] Test instruction modification detection
  - [ ] Test regression prevention
  - [ ] Verify continuous improvement loop

## Dev Notes

### Architecture Context

This story implements **Eval Reporting and Continuous Improvement Loop** (consolidates old stories 5.4, 5.5, 5.6), enabling iterative refinement of instructions based on eval results and real-world failures.

**Key Architectural Principles:**
- FR32: Failed evals added to permanent suite (continuous improvement)
- FR33: Never delete passing scenarios (regression prevention)
- NFR1: Iterate toward 99% eval pass rate target
- Actionable failure reporting for quick diagnosis

### Critical Implementation Rules from Project Context

**Detailed Failure Reporting Implementation:**

```python
# src/guarantee_email_agent/eval/reporter.py (extended from 4.1)
from typing import List, Dict, Any
from guarantee_email_agent.eval.models import EvalResult

class EvalReporter:
    """Enhanced eval reporter with detailed failure analysis"""

    def print_detailed_failures(self, results: List[EvalResult]) -> None:
        """
        Print detailed failure information for all failed scenarios.

        Args:
            results: List of eval results
        """
        failed_results = [r for r in results if not r.passed]

        if not failed_results:
            print("\n✓ All scenarios passed!")
            return

        print(f"\n{'='*80}")
        print(f"DETAILED FAILURE REPORT ({len(failed_results)} failures)")
        print(f"{'='*80}\n")

        for i, result in enumerate(failed_results, 1):
            self._print_single_failure(result, i, len(failed_results))

    def _print_single_failure(
        self,
        result: EvalResult,
        index: int,
        total: int
    ) -> None:
        """Print detailed information for single failed scenario"""
        print(f"[{index}/{total}] FAILURE: {result.test_case.scenario_id}")
        print(f"Description: {result.test_case.description}")
        print(f"Category: {result.test_case.category}")
        print()

        # Group failures by category
        failures_by_category = self._categorize_failures(result.failures)

        for category, failures in failures_by_category.items():
            print(f"  {category.upper()} FAILURES:")
            for failure in failures:
                self._print_failure_detail(failure, result.actual_output)
            print()

        # Show actual response body if relevant
        if "response_body" in result.actual_output and result.actual_output["response_body"]:
            response = result.actual_output["response_body"]
            if len(response) > 500:
                response = response[:300] + "\n...\n" + response[-200:]

            print("  Actual Response Body:")
            print("  " + "-" * 78)
            for line in response.split('\n'):
                print(f"  {line}")
            print("  " + "-" * 78)
            print()

        # Suggest potential fixes
        suggestions = self._generate_suggestions(result)
        if suggestions:
            print("  SUGGESTED FIXES:")
            for suggestion in suggestions:
                confidence_str = f"(confidence: {suggestion.confidence})"
                print(f"  • {suggestion.description} {confidence_str}")
                if suggestion.action:
                    print(f"    → {suggestion.action}")
            print()

        print("-" * 80 + "\n")

    def _categorize_failures(self, failures: List[str]) -> Dict[str, List[str]]:
        """Categorize failures by type"""
        categories = {
            "Response Content": [],
            "Scenario Routing": [],
            "Ticket Creation": [],
            "Performance": [],
            "Other": []
        }

        for failure in failures:
            if "response_body_contains" in failure or "response_body_excludes" in failure:
                categories["Response Content"].append(failure)
            elif "scenario_instruction_used" in failure:
                categories["Scenario Routing"].append(failure)
            elif "ticket_created" in failure or "ticket_field" in failure:
                categories["Ticket Creation"].append(failure)
            elif "processing_time_ms" in failure:
                categories["Performance"].append(failure)
            else:
                categories["Other"].append(failure)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _print_failure_detail(self, failure: str, actual_output: Dict) -> None:
        """Print formatted failure detail with context"""
        print(f"    ✗ {failure}")

        # Add context based on failure type
        if "response_body_contains" in failure:
            # Extract expected phrase from failure message
            if "missing phrase" in failure:
                phrase_start = failure.find("'") + 1
                phrase_end = failure.rfind("'")
                phrase = failure[phrase_start:phrase_end]
                print(f"      Expected phrase: '{phrase}'")
                print(f"      Actual response did not contain this phrase")

        elif "response_body_excludes" in failure:
            if "unwanted phrase" in failure:
                phrase_start = failure.find("'") + 1
                phrase_end = failure.rfind("'")
                phrase = failure[phrase_start:phrase_end]
                print(f"      Unwanted phrase: '{phrase}'")
                print(f"      This phrase was present but should be excluded")

    def _generate_suggestions(self, result: EvalResult) -> List['SuggestedFix']:
        """Generate suggested fixes for failures"""
        from guarantee_email_agent.eval.suggestions import generate_fix_suggestions
        return generate_fix_suggestions(result)

    def print_comparison(
        self,
        current_results: List[EvalResult],
        previous_results: List[EvalResult]
    ) -> None:
        """
        Print comparison between current and previous eval runs.

        Args:
            current_results: Current eval results
            previous_results: Previous eval results
        """
        if not previous_results:
            print("\nNo previous results to compare")
            return

        print(f"\n{'='*80}")
        print("COMPARISON WITH PREVIOUS RUN")
        print(f"{'='*80}\n")

        # Build scenario status maps
        previous_status = {r.test_case.scenario_id: r.passed for r in previous_results}
        current_status = {r.test_case.scenario_id: r.passed for r in current_results}

        # Find changes
        improvements = []  # fail → pass
        regressions = []   # pass → fail
        new_scenarios = []

        for scenario_id, passed in current_status.items():
            if scenario_id not in previous_status:
                new_scenarios.append(scenario_id)
            elif not previous_status[scenario_id] and passed:
                improvements.append(scenario_id)
            elif previous_status[scenario_id] and not passed:
                regressions.append(scenario_id)

        # Print summary
        print(f"Improvements (fail → pass): {len(improvements)}")
        for scenario_id in improvements:
            print(f"  ✓ {scenario_id} now passing!")

        if regressions:
            print(f"\n⚠️  REGRESSIONS (pass → fail): {len(regressions)}")
            for scenario_id in regressions:
                print(f"  ✗ {scenario_id} now failing (was passing)")
            print("\n⚠️  Consider reverting recent instruction changes")

        if new_scenarios:
            print(f"\nNew scenarios: {len(new_scenarios)}")
            for scenario_id in new_scenarios:
                status = "✓ passing" if current_status[scenario_id] else "✗ failing"
                print(f"  + {scenario_id} ({status})")

        print()
```

**Suggestion Engine Implementation:**

```python
# src/guarantee_email_agent/eval/suggestions.py
from dataclasses import dataclass
from typing import List
from guarantee_email_agent.eval.models import EvalResult

@dataclass
class SuggestedFix:
    """Suggested fix for eval failure"""
    fix_type: str  # "response_content", "scenario_routing", "ticket_creation", "performance"
    confidence: str  # "high", "medium", "low"
    description: str
    action: str  # Actionable step

def generate_fix_suggestions(result: EvalResult) -> List[SuggestedFix]:
    """
    Generate suggested fixes for eval failure.

    Args:
        result: Failed eval result

    Returns:
        List of suggested fixes
    """
    suggestions = []

    for failure in result.failures:
        if "response_body_contains" in failure:
            suggestions.append(SuggestedFix(
                fix_type="response_content",
                confidence="high",
                description="Response missing expected phrase",
                action=f"Review scenario instruction: instructions/scenarios/{result.test_case.expected_output.scenario_instruction_used}.md"
            ))

        elif "response_body_excludes" in failure:
            suggestions.append(SuggestedFix(
                fix_type="response_content",
                confidence="high",
                description="Response contains unwanted phrase",
                action=f"Refine scenario instruction to avoid this phrase: instructions/scenarios/{result.test_case.expected_output.scenario_instruction_used}.md"
            ))

        elif "scenario_instruction_used" in failure:
            expected = result.test_case.expected_output.scenario_instruction_used
            actual = result.actual_output.get("scenario_used", "unknown")
            suggestions.append(SuggestedFix(
                fix_type="scenario_routing",
                confidence="medium",
                description=f"Wrong scenario detected: expected '{expected}', got '{actual}'",
                action="Review scenario detection heuristics in: src/guarantee_email_agent/email/scenario_detector.py"
            ))

        elif "ticket_created" in failure:
            suggestions.append(SuggestedFix(
                fix_type="ticket_creation",
                confidence="high",
                description="Ticket creation status mismatch",
                action="Review ticket creation logic in: src/guarantee_email_agent/email/processor.py"
            ))

        elif "processing_time_ms" in failure:
            # Extract timing info from failure message
            suggestions.append(SuggestedFix(
                fix_type="performance",
                confidence="medium",
                description="Processing time exceeded threshold",
                action="Review step timings and optimize slow operations"
            ))

    # Deduplicate suggestions
    unique_suggestions = []
    seen = set()
    for suggestion in suggestions:
        key = (suggestion.fix_type, suggestion.description)
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(suggestion)

    return unique_suggestions
```

**Eval Case Template:**

```yaml
# evals/scenarios/_TEMPLATE.yaml
# Template for creating new eval test cases
# Copy this file and fill in the sections below

---
# Unique identifier for this test case (use: {category}_{number} format)
scenario_id: category_001

# Human-readable description of what this test validates
description: "Brief description of the scenario being tested"

# Category: valid-warranty, invalid-warranty, missing-info, edge-case, etc.
category: valid-warranty

# Date this test case was created (YYYY-MM-DD)
created: 2026-01-18
---

# Input section: The email and mock API responses
input:
  # The customer email to process
  email:
    subject: "Email subject line"
    body: |
      Email body content here.
      Can be multiple lines.
      Include serial number if applicable: SN12345
    from: "customer@example.com"
    received: "2026-01-18T10:00:00Z"

  # Mock responses from external APIs
  mock_responses:
    # Warranty API mock response (returned when check_warranty called)
    warranty_api:
      status: "valid"  # or "expired", "not_found"
      expiration_date: "2025-12-31"
      coverage: "full"

# Expected output section: What should happen
expected_output:
  # Should an email be sent to the customer?
  email_sent: true

  # Phrases that MUST appear in the response email body
  response_body_contains:
    - "warranty is valid"
    - "2025-12-31"
    - "fully covered"

  # Phrases that must NOT appear in the response email body
  response_body_excludes:
    - "expired"
    - "invalid"
    - "not found"

  # Should a ticket be created?
  ticket_created: true

  # If ticket created, what fields should it have?
  ticket_fields:
    serial_number: "SN12345"
    warranty_status: "valid"
    priority: "normal"
    category: "warranty_claim"

  # Which scenario instruction should be used?
  scenario_instruction_used: "valid-warranty"

  # Maximum acceptable processing time (milliseconds)
  processing_time_ms: 60000
```

**Continuous Improvement Documentation:**

```markdown
# evals/scenarios/README.md

## Adding Failed Cases to Eval Suite

When the agent fails to process a real-world email correctly, follow this process to add it to the eval suite and prevent regression:

### Step 1: Capture the Failure

- Collect the actual email content (subject, body, sender)
- Identify what went wrong (wrong response, wrong scenario, no ticket, etc.)
- Determine what the correct behavior should have been

### Step 2: Create New Eval Case

1. Copy `_TEMPLATE.yaml` to new file: `{category}_{number}.yaml`
2. Fill in the scenario_id, description, category, created date
3. Copy the actual email content to the `input.email` section
4. Add mock API responses that match what should have been returned
5. Define the expected behavior in `expected_output` section

Example naming:
- `valid_warranty_004.yaml` - Fourth valid warranty test case
- `missing_info_002.yaml` - Second missing information test case
- `edge_case_serial_in_attachment_001.yaml` - Edge case with attachment

### Step 3: Verify Test Case

Run eval to verify the test case executes:

```bash
uv run python -m guarantee_email_agent eval
```

The new case should fail initially (captures current wrong behavior).

### Step 4: Refine Instructions

Identify which instruction file needs modification:
- Response content issues → Scenario instruction file (`instructions/scenarios/{scenario}.md`)
- Scenario routing issues → Scenario detector logic
- Ticket creation issues → Processor logic

Edit the instruction file to address the failure.

### Step 5: Validate Fix

Re-run eval to verify:

```bash
uv run python -m guarantee_email_agent eval
```

The target scenario should now pass. Ensure no regressions in other scenarios.

### Step 6: Commit Changes

Commit both the new eval case and instruction modifications:

```bash
git add evals/scenarios/{new_case}.yaml
git add instructions/scenarios/{modified_instruction}.md
git commit -m "Add eval case and fix for {issue}"
```

### Regression Prevention

**NEVER delete passing eval scenarios.** Once a scenario passes, it becomes part of the permanent regression suite. This ensures:

- Previously fixed issues don't reoccur
- Instruction changes don't break existing behavior
- Agent behavior is fully documented in eval cases
- Confidence in making changes

### Suite Growth

The eval suite will grow over time:

- **Start (MVP):** 10-20 basic scenarios covering main paths
- **Growth:** Add 2-5 scenarios per real-world failure or edge case discovered
- **Target:** 50+ scenarios for comprehensive coverage
- **Organization:** Use subdirectories if suite grows beyond 50 cases

Example structure for large suites:
```
evals/scenarios/
  valid-warranty/
    valid_warranty_001.yaml
    valid_warranty_002.yaml
    ...
  invalid-warranty/
    invalid_warranty_001.yaml
    ...
  missing-info/
    missing_info_001.yaml
    ...
```

Performance target: Complete suite in <5 minutes for ≤50 scenarios.
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Deleting passing scenarios:**
   ```bash
   # WRONG - Removing old test case
   rm evals/scenarios/valid_warranty_001.yaml  # Loses regression protection!

   # CORRECT - Keep all passing scenarios
   # If truly obsolete, mark as deprecated but keep file
   ```

2. **Not comparing to previous results:**
   ```python
   # WRONG - Only showing current results
   print_scenario_results(current_results)

   # CORRECT - Show comparison if previous results exist
   if previous_results:
       print_comparison(current_results, previous_results)
   ```

3. **Vague failure reporting:**
   ```python
   # WRONG - Not actionable
   print("Test failed")

   # CORRECT - Detailed, actionable
   print("FAILED: response_body_contains - missing phrase 'warranty is valid'")
   print("Expected: 'warranty is valid'")
   print("Actual response: '...warranty has expired...'")
   print("Suggested fix: Review instructions/scenarios/valid-warranty.md")
   ```

4. **Not tracking eval history:**
   ```python
   # WRONG - No historical tracking
   run_eval()  # Results disappear after run

   # CORRECT - Save results for comparison
   save_results_to_history(results)
   ```

5. **Not clearing instruction cache:**
   ```python
   # WRONG - Using stale cached instructions
   # (Previous instructions cached in memory)
   results = run_eval()

   # CORRECT - Clear cache before eval
   clear_instruction_cache()
   results = run_eval()  # Fresh instructions
   ```

### Verification Commands

```bash
# 1. Run eval with verbose output
uv run python -m guarantee_email_agent eval --verbose

# 2. Show only failures
uv run python -m guarantee_email_agent eval --failures-only

# 3. Get JSON output for automation
uv run python -m guarantee_email_agent eval --output-json > results.json

# 4. Create new eval case from template
cp evals/scenarios/_TEMPLATE.yaml evals/scenarios/missing_info_004.yaml
# Edit file...

# 5. Run eval and check for regressions
uv run python -m guarantee_email_agent eval
# Review comparison output for regressions

# 6. Generate eval case with helper script
uv run python scripts/create_eval_case.py

# 7. Test suggestion engine
uv run python -c "
from guarantee_email_agent.eval.suggestions import generate_fix_suggestions
from guarantee_email_agent.eval.models import EvalResult
# ... create mock failed result
suggestions = generate_fix_suggestions(result)
for s in suggestions:
    print(f'{s.description} - {s.action}')
"

# 8. Run tests
uv run pytest tests/eval/test_reporter_detailed.py -v
uv run pytest tests/eval/test_suggestions.py -v
```

### Dependency Notes

**Depends on:**
- Story 4.1: Eval framework core (loader, runner, reporter)
- Epic 3: Complete agent for instruction refinement
- Story 3.2: Scenario instructions for refinement

**Blocks:**
- Production deployment: Iterative improvement toward 99%
- Story 4.3: Error handling uses eval feedback

**Integration Points:**
- Enhanced reporter → EvalResult from Story 4.1
- Suggestion engine → Failure analysis
- Comparison → Previous results tracking
- Documentation → Continuous improvement workflow

### Previous Story Intelligence

From Story 4.1 (Eval Framework Core):
- EvalResult dataclass with failures list
- EvalReporter with pass rate calculation
- Per-scenario results printing
- Test case YAML format

From Story 3.6 (Logging):
- Structured logging patterns
- Error context enrichment

From Story 3.2 (Scenario Routing):
- Scenario instruction files
- Instruction refinement target

**Learnings to Apply:**
- Build on existing reporter from 4.1
- Extend with detailed failure analysis
- Actionable suggestions with file paths
- Historical tracking for regression detection
- Clear documentation for workflow

### Git Intelligence Summary

Recent commits show:
- Comprehensive reporting patterns
- Dataclasses for structured data
- Template-based code generation
- Documentation-driven workflows
- Helper scripts for common tasks

**Code Patterns to Continue:**
- Detailed error context with suggestions
- Comparison logic for before/after
- Template files for reproducibility
- Helper scripts for automation
- Comprehensive documentation

### References

**Architecture Document Sections:**
- [Source: architecture.md#Eval Framework] - Continuous improvement
- [Source: architecture.md#Instruction Refinement] - Workflow

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 4: Story 4.2] - Complete acceptance criteria
- [Source: prd.md#FR32] - Continuous improvement loop
- [Source: prd.md#FR33] - Never delete passing scenarios
- [Source: prd.md#NFR1] - 99% pass rate target

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context from Story 4.1 eval framework
- Story consolidates 3 original stories (5.4, 5.5, 5.6)
- Enhanced failure reporting with expected vs actual comparisons
- Failure categorization: response content, scenario routing, ticket, performance
- Pattern detection across multiple failures
- Suggestion engine with confidence scoring
- Suggested fix for each failure type with actionable steps
- Continuous improvement workflow documentation
- Eval case template (_TEMPLATE.yaml) for quick case creation
- Helper script (create_eval_case.py) for automation
- Regression detection with pass→fail alerts
- Comparison reporting (before/after eval runs)
- Pass rate trend tracking with historical data
- CLI flags: --verbose, --failures-only, --output-json, --summary
- Instruction cache clearing for fresh eval runs
- Complete refinement workflow documentation
- Never delete passing scenarios (regression prevention)
- Testing strategy: detailed reporter, suggestions, regression, CLI flags
- Verification commands for workflow testing

### File List

**Enhanced Reporter:**
- `src/guarantee_email_agent/eval/reporter.py` - Extended with detailed failure reporting

**Suggestion Engine:**
- `src/guarantee_email_agent/eval/suggestions.py` - Fix suggestion generation

**CLI Updates:**
- `src/guarantee_email_agent/cli.py` - Add --verbose, --failures-only, --output-json, --summary flags

**Templates and Documentation:**
- `evals/scenarios/_TEMPLATE.yaml` - Eval case template
- `evals/scenarios/README.md` - Enhanced with continuous improvement workflow
- `docs/eval-refinement-workflow.md` - Complete refinement workflow documentation

**Helper Scripts:**
- `scripts/create_eval_case.py` - Helper for creating new eval cases

**Result Tracking:**
- `.eval-results.json` - Previous results for comparison (git-ignored)
- `.eval-history.json` - Historical pass rates (git-ignored)

**Tests:**
- `tests/eval/test_reporter_detailed.py` - Enhanced reporter tests
- `tests/eval/test_suggestions.py` - Suggestion engine tests
- `tests/eval/test_regression.py` - Regression detection tests
- `tests/eval/test_cli_flags.py` - CLI flag tests
