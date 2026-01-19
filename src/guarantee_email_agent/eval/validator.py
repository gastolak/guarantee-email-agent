"""Function call validation for eval framework.

Validates actual function calls against expected function calls,
checking function names, arguments, results, and email body content.
"""

import logging
from typing import Any, Dict, List, Optional

from guarantee_email_agent.eval.models import ExpectedFunctionCall, ActualFunctionCall

logger = logging.getLogger(__name__)


def validate_function_calls(
    expected: List[ExpectedFunctionCall],
    actual: List[ActualFunctionCall]
) -> List[str]:
    """Validate actual function calls against expected calls.

    Performs validation checks:
    - Function count matches
    - Function names in order
    - Arguments match (exact or partial)
    - Results contain expected values
    - send_email body contains expected phrases

    Args:
        expected: List of expected function calls
        actual: List of actual function calls

    Returns:
        List of failure messages (empty if all validations pass)
    """
    failures: List[str] = []

    # Check function count
    if len(expected) != len(actual):
        failures.append(
            f"Function count mismatch: expected {len(expected)}, got {len(actual)}"
        )
        # Continue with partial validation

    # Validate each function call
    for i, exp in enumerate(expected):
        if i >= len(actual):
            failures.append(
                f"Missing function call {i + 1}: expected {exp.function_name}"
            )
            continue

        act = actual[i]

        # Check function name
        if exp.function_name != act.function_name:
            failures.append(
                f"Function {i + 1} name mismatch: expected {exp.function_name}, "
                f"got {act.function_name}"
            )
            continue  # Skip further validation for this function

        # Check success
        if not act.success:
            failures.append(
                f"Function {i + 1} ({act.function_name}) failed: {act.error_message}"
            )
            continue

        # Check exact argument match
        if exp.arguments is not None:
            arg_failures = _validate_exact_match(
                expected=exp.arguments,
                actual=act.arguments,
                prefix=f"Function {i + 1} ({act.function_name}) argument"
            )
            failures.extend(arg_failures)

        # Check partial argument match
        if exp.arguments_contain is not None:
            arg_failures = _validate_contains(
                expected=exp.arguments_contain,
                actual=act.arguments,
                prefix=f"Function {i + 1} ({act.function_name}) argument"
            )
            failures.extend(arg_failures)

        # Check result contains
        if exp.result_contains is not None:
            result_failures = _validate_contains(
                expected=exp.result_contains,
                actual=act.result,
                prefix=f"Function {i + 1} ({act.function_name}) result"
            )
            failures.extend(result_failures)

        # Check body_contains for send_email
        if exp.body_contains is not None and act.function_name == "send_email":
            body = act.arguments.get("body", "")
            for phrase in exp.body_contains:
                if phrase.lower() not in body.lower():
                    failures.append(
                        f"Function {i + 1} (send_email) body missing phrase: '{phrase}'"
                    )

    # Check for extra unexpected function calls
    if len(actual) > len(expected):
        for i in range(len(expected), len(actual)):
            act = actual[i]
            failures.append(
                f"Unexpected function call {i + 1}: {act.function_name}"
            )

    if failures:
        logger.warning(
            f"Function validation failed with {len(failures)} issues",
            extra={"failure_count": len(failures)}
        )
    else:
        logger.debug("Function validation passed")

    return failures


def _validate_exact_match(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    prefix: str
) -> List[str]:
    """Validate exact match between expected and actual values.

    Args:
        expected: Expected values
        actual: Actual values
        prefix: Prefix for error messages

    Returns:
        List of failure messages
    """
    failures = []

    for key, exp_value in expected.items():
        if key not in actual:
            failures.append(f"{prefix} missing key: {key}")
        elif actual[key] != exp_value:
            failures.append(
                f"{prefix} '{key}' mismatch: expected {repr(exp_value)}, "
                f"got {repr(actual[key])}"
            )

    return failures


def _validate_contains(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    prefix: str
) -> List[str]:
    """Validate that actual contains expected values (partial match).

    For string values, checks if expected is substring of actual.
    For other types, checks exact match.

    Args:
        expected: Expected values to find
        actual: Actual values to check
        prefix: Prefix for error messages

    Returns:
        List of failure messages
    """
    failures = []

    for key, exp_value in expected.items():
        if key not in actual:
            failures.append(f"{prefix} missing key: {key}")
        else:
            act_value = actual[key]

            # String substring match (case-insensitive)
            if isinstance(exp_value, str) and isinstance(act_value, str):
                if exp_value.lower() not in act_value.lower():
                    failures.append(
                        f"{prefix} '{key}' does not contain: '{exp_value}'"
                    )
            # Dict recursive check
            elif isinstance(exp_value, dict) and isinstance(act_value, dict):
                nested_failures = _validate_contains(
                    expected=exp_value,
                    actual=act_value,
                    prefix=f"{prefix}['{key}']"
                )
                failures.extend(nested_failures)
            # Exact match for other types
            elif act_value != exp_value:
                failures.append(
                    f"{prefix} '{key}' mismatch: expected {repr(exp_value)}, "
                    f"got {repr(act_value)}"
                )

    return failures


def validate_email_sent(actual_calls: List[ActualFunctionCall]) -> Optional[str]:
    """Validate that send_email was called successfully.

    Args:
        actual_calls: List of actual function calls

    Returns:
        Failure message if send_email not called, None otherwise
    """
    for call in actual_calls:
        if call.function_name == "send_email" and call.success:
            return None

    return "send_email was not called successfully"
