"""Step sequence validator for eval framework (Story 5.1).

Validates that actual step sequences match expected step sequences in eval test cases.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class StepValidationResult:
    """Result of validating a step sequence.

    Attributes:
        passed: Whether the step sequence matches expectations
        failures: List of validation failure messages
        expected_steps: Expected step sequence
        actual_steps: Actual step sequence executed
        step_diff: Human-readable diff of steps
    """

    passed: bool
    failures: List[str]
    expected_steps: List[str]
    actual_steps: List[str]
    step_diff: str


def validate_step_sequence(
    expected_steps: Optional[List[str]],
    actual_steps: List[str]
) -> StepValidationResult:
    """Validate actual step sequence matches expected steps.

    Args:
        expected_steps: Expected step sequence (None means no validation)
        actual_steps: Actual steps executed

    Returns:
        StepValidationResult with validation outcome

    Validation Rules:
    1. If expected_steps is None, validation passes (step validation opt-in)
    2. If expected_steps is empty, validation fails (must specify steps)
    3. Exact match required for all steps in sequence
    4. Order matters: steps must occur in expected order
    5. Early termination allowed: actual can be shorter if ends with valid final step
    """
    failures = []

    # Rule 1: No expected steps means validation passes (opt-in)
    if expected_steps is None:
        return StepValidationResult(
            passed=True,
            failures=[],
            expected_steps=[],
            actual_steps=actual_steps,
            step_diff="Step validation not enabled for this test case"
        )

    # Rule 2: Empty expected_steps is invalid
    if not expected_steps:
        return StepValidationResult(
            passed=False,
            failures=["Expected steps cannot be empty when step validation is enabled"],
            expected_steps=[],
            actual_steps=actual_steps,
            step_diff=""
        )

    # Build step diff
    step_diff = _build_step_diff(expected_steps, actual_steps)

    # Rule 3 & 4: Exact match validation
    if len(actual_steps) > len(expected_steps):
        failures.append(
            f"Too many steps executed: expected {len(expected_steps)}, got {len(actual_steps)}"
        )
        failures.append(f"Unexpected steps: {actual_steps[len(expected_steps):]}")

    # Check each step in order
    for i, expected_step in enumerate(expected_steps):
        if i >= len(actual_steps):
            # Rule 5: Early termination - check if last actual step is a valid final step
            last_actual = actual_steps[-1] if actual_steps else None
            if _is_valid_final_step(last_actual):
                # Early termination is OK if it ends with a final step
                break
            else:
                failures.append(
                    f"Missing steps: expected {expected_steps[i:]}, workflow ended at '{last_actual}'"
                )
                break

        actual_step = actual_steps[i]
        if actual_step != expected_step:
            failures.append(
                f"Step {i + 1} mismatch: expected '{expected_step}', got '{actual_step}'"
            )

    passed = len(failures) == 0

    return StepValidationResult(
        passed=passed,
        failures=failures,
        expected_steps=expected_steps,
        actual_steps=actual_steps,
        step_diff=step_diff
    )


def _is_valid_final_step(step: Optional[str]) -> bool:
    """Check if a step is a valid final step (termination point).

    Valid final steps:
    - 05-send-confirmation (normal completion)
    - 04-out-of-scope (graceful rejection)
    - 03d-request-serial (waiting for more info)
    - DONE (explicit termination)

    Args:
        step: Step name to check

    Returns:
        True if step is a valid final step
    """
    if step is None:
        return False

    valid_final_steps = {
        "05-send-confirmation",  # Normal completion
        "04-out-of-scope",       # Out of scope graceful degradation
        "03d-request-serial",    # Waiting for more information
        "DONE"                   # Explicit termination
    }

    return step in valid_final_steps


def _build_step_diff(expected: List[str], actual: List[str]) -> str:
    """Build human-readable diff of expected vs actual steps.

    Args:
        expected: Expected step sequence
        actual: Actual step sequence

    Returns:
        Formatted diff string

    Format:
        Expected: 01-extract-serial → 02-check-warranty → 03a-valid-warranty
        Actual:   01-extract-serial → 02-check-warranty → 03b-device-not-found
                                                           ^^^^^^^^^ mismatch
    """
    if not expected and not actual:
        return "No steps"

    lines = []

    # Expected steps line
    expected_line = "Expected: " + " → ".join(expected) if expected else "Expected: (none)"
    lines.append(expected_line)

    # Actual steps line
    actual_line = "Actual:   " + " → ".join(actual) if actual else "Actual:   (none)"
    lines.append(actual_line)

    # Mismatch indicator
    if expected and actual:
        # Find first mismatch
        mismatch_index = None
        for i in range(min(len(expected), len(actual))):
            if expected[i] != actual[i]:
                mismatch_index = i
                break

        if mismatch_index is not None:
            # Calculate position of mismatch indicator
            prefix = "          "  # Length of "Actual:   "
            for i in range(mismatch_index):
                prefix += actual[i] + " → "

            indicator = "^" * len(actual[mismatch_index]) + " mismatch"
            lines.append(prefix + indicator)

    return "\n".join(lines)


def format_step_validation_failure(result: StepValidationResult) -> str:
    """Format step validation failure for display.

    Args:
        result: Validation result to format

    Returns:
        Formatted failure message
    """
    if result.passed:
        return ""

    lines = ["Step validation failed:"]
    lines.append("")
    lines.append(result.step_diff)
    lines.append("")

    for failure in result.failures:
        lines.append(f"  • {failure}")

    return "\n".join(lines)
