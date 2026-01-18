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
# Run all eval scenarios
uv run python -m guarantee_email_agent eval

# Run from custom directory
uv run python -m guarantee_email_agent eval --eval-dir path/to/evals
```

## Pass Rate Target

- Target: ≥99% pass rate
- Exit code 0 if ≥99%
- Exit code 4 if <99%
