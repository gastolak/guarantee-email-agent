# Eval Scenarios

This directory contains YAML test cases for the eval framework.

## File Naming Convention

Files should follow the pattern: `{category}_{number}.yaml`

Examples:
- `valid_warranty_001.yaml`
- `invalid_warranty_001.yaml`
- `missing_info_001.yaml`

## YAML Format

Each eval test case must include:

### Top-level Fields
- `scenario_id`: Unique identifier (e.g., "valid_warranty_001")
- `description`: Human-readable description
- `category`: Scenario category (e.g., "valid-warranty")
- `created`: Date created (format: "YYYY-MM-DD")

### Input Section
```yaml
input:
  email:
    subject: "Email subject"
    body: "Email body text"
    from: "sender@example.com"
    received: "2026-01-18T10:00:00Z"

  mock_responses:
    warranty_api:
      status: "valid"
      expiration_date: "2025-12-31"
```

### Expected Output Section
```yaml
expected_output:
  email_sent: true  # Required
  response_body_contains:  # Optional list
    - "warranty is valid"
  response_body_excludes:  # Optional list
    - "expired"
  ticket_created: true  # Required
  ticket_fields:  # Optional dict
    serial_number: "SN12345"
    priority: "normal"
  scenario_instruction_used: "valid-warranty"  # Required
  processing_time_ms: 60000  # Optional, defaults to 60000
```

## Example Template

```yaml
scenario_id: example_001
description: "Description of what this scenario tests"
category: example-category
created: "2026-01-18"

input:
  email:
    subject: "Test subject"
    body: "Test body with serial number SN12345"
    from: "test@example.com"
    received: "2026-01-18T10:00:00Z"

  mock_responses:
    warranty_api:
      status: "valid"

expected_output:
  email_sent: true
  response_body_contains:
    - "expected phrase"
  response_body_excludes:
    - "unwanted phrase"
  ticket_created: false
  scenario_instruction_used: "scenario-name"
  processing_time_ms: 60000
```

## Running Evals

```bash
# Basic run - show all scenarios
uv run python -m guarantee_email_agent eval

# Show only failures (useful when many tests pass)
uv run python -m guarantee_email_agent eval --failures-only

# Show detailed failure analysis with fix suggestions
uv run python -m guarantee_email_agent eval --detailed

# Verbose mode with full response bodies
uv run python -m guarantee_email_agent eval --detailed --verbose

# Custom directory
uv run python -m guarantee_email_agent eval --eval-dir path/to/evals
```

## Continuous Improvement Workflow

### Adding Failed Cases to Eval Suite (FR32)

When a real-world email fails processing, convert it to an eval test case:

**Step 1: Capture the Failure**
- Save the actual email content (subject, body, from, date)
- Note the error or incorrect behavior
- Document what the agent should have done

**Step 2: Create New Test Case**
- Copy `_TEMPLATE.yaml` to new file: `{category}_{number}.yaml`
- Fill in `input.email` section with actual email content
- Define `expected_output` with correct behavior
- Add `mock_responses` if needed for warranty API data

**Step 3: Add to Eval Suite**
- Place file in `evals/scenarios/` directory
- File is automatically discovered on next eval run
- Follow naming convention: lowercase, underscore-separated

**Step 4: Run Eval to Verify**
```bash
uv run python -m guarantee_email_agent eval
```
- New scenario should appear in results
- Will likely FAIL initially (expected - that's why we're adding it!)

**Step 5: Refine Instructions**
- Review failure details with: `eval --detailed`
- Identify which instruction file needs modification
- Edit instruction file (e.g., `instructions/scenarios/valid-warranty.md`)
- Modify prompts, add examples, adjust logic

**Step 6: Re-Run Eval**
```bash
uv run python -m guarantee_email_agent eval --detailed
```
- Verify target scenario now PASSES
- Check no regressions in other scenarios
- Pass rate should maintain or improve

**Step 7: Commit Changes**
```bash
git add evals/scenarios/{new-test-case}.yaml
git add instructions/scenarios/{modified-instruction}.md
git commit -m "Add eval case for {scenario} and refine instructions"
```

### Regression Prevention (FR33)

**Critical Rule: NEVER delete passing scenarios**

- Once a scenario passes, it becomes part of the permanent regression suite
- Deleting scenarios loses validation of that behavior
- Suite grows over time (10-20 → 50+ scenarios)
- Growing suite ensures no regressions as system evolves

**If scenario becomes irrelevant:**
- Mark in description: "(DEPRECATED - kept for regression prevention)"
- Keep file in place
- Do not delete

### Instruction Refinement Cycle

**Iterative improvement toward 99% target:**

1. **Identify Failure**
   - Run eval, review failures with `--detailed` flag
   - Note failure category and suggested fix

2. **Analyze Root Cause**
   - Response content issue → instruction file needs refinement
   - Scenario routing issue → detection logic needs adjustment
   - Ticket creation issue → processor logic needs fix

3. **Make Changes**
   - Edit instruction files in `instructions/scenarios/`
   - Modify detection heuristics if needed
   - Update processor logic if needed

4. **Validate Changes**
   ```bash
   uv run python -m guarantee_email_agent eval --detailed
   ```
   - Target scenario should now pass
   - All previous passing scenarios must still pass
   - No regressions introduced

5. **Track Progress**
   - Pass rate should increase: 85% → 92% → 97% → 99%
   - Monitor trend over time
   - Target: ≥99% before production deployment

### Suite Growth Strategy

**Start (MVP):** 10-20 core scenarios
- Valid warranty (various formats)
- Expired warranty
- Missing information
- Out of scope / spam

**Growth (Production):** Add 2-5 scenarios per real-world failure
- Capture edge cases as they occur
- Document unusual email formats
- Cover all customer communication patterns

**Mature (50+ scenarios):** Comprehensive coverage
- Organize into subdirectories by category
- `evals/scenarios/valid-warranty/*.yaml`
- `evals/scenarios/missing-info/*.yaml`
- Suite completes in <5 minutes

## Pass Rate Target

- Target: ≥99% pass rate (NFR1)
- Exit code 0 if ≥99%
- Exit code 4 if <99%
- Use detailed mode for diagnosis: `eval --detailed`

## Template

See `_TEMPLATE.yaml` for a complete template with comments explaining each field.
