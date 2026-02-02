"""Tests for step sequence validator."""

import pytest

from guarantee_email_agent.eval.step_validator import (
    validate_step_sequence,
    format_step_validation_failure,
    _is_valid_final_step,
    _build_step_diff
)


def test_validate_no_expected_steps():
    """Test validation passes when expected_steps is None (opt-in)."""
    result = validate_step_sequence(
        expected_steps=None,
        actual_steps=["01-extract-serial", "02-check-warranty"]
    )

    assert result.passed is True
    assert len(result.failures) == 0
    assert result.expected_steps == []


def test_validate_empty_expected_steps():
    """Test validation fails when expected_steps is empty."""
    result = validate_step_sequence(
        expected_steps=[],
        actual_steps=["01-extract-serial"]
    )

    assert result.passed is False
    assert len(result.failures) == 1
    assert "cannot be empty" in result.failures[0]


def test_validate_exact_match():
    """Test validation passes with exact match."""
    expected = ["01-extract-serial", "02-check-warranty", "03a-valid-warranty", "05-send-confirmation"]
    actual = ["01-extract-serial", "02-check-warranty", "03a-valid-warranty", "05-send-confirmation"]

    result = validate_step_sequence(expected, actual)

    assert result.passed is True
    assert len(result.failures) == 0
    assert result.expected_steps == expected
    assert result.actual_steps == actual


def test_validate_step_mismatch():
    """Test validation fails when steps don't match."""
    expected = ["01-extract-serial", "02-check-warranty", "03a-valid-warranty"]
    actual = ["01-extract-serial", "02-check-warranty", "03b-device-not-found"]

    result = validate_step_sequence(expected, actual)

    assert result.passed is False
    assert len(result.failures) == 1
    assert "Step 3 mismatch" in result.failures[0]
    assert "03a-valid-warranty" in result.failures[0]
    assert "03b-device-not-found" in result.failures[0]


def test_validate_too_many_steps():
    """Test validation fails when too many steps executed."""
    expected = ["01-extract-serial", "02-check-warranty"]
    actual = ["01-extract-serial", "02-check-warranty", "03a-valid-warranty", "05-send-confirmation"]

    result = validate_step_sequence(expected, actual)

    assert result.passed is False
    assert any("Too many steps" in f for f in result.failures)
    assert any("Unexpected steps" in f for f in result.failures)


def test_validate_missing_steps_invalid_termination():
    """Test validation fails when workflow ends prematurely at non-final step."""
    expected = ["01-extract-serial", "02-check-warranty", "03a-valid-warranty", "05-send-confirmation"]
    actual = ["01-extract-serial", "02-check-warranty"]  # Ends at 02, not a valid final step

    result = validate_step_sequence(expected, actual)

    assert result.passed is False
    assert any("Missing steps" in f for f in result.failures)


def test_validate_early_termination_valid_final_step():
    """Test validation allows early termination if steps match and end at valid final step."""
    expected = ["01-extract-serial", "04-out-of-scope"]
    actual = ["01-extract-serial", "04-out-of-scope"]  # Matches expected and ends at valid final step

    result = validate_step_sequence(expected, actual)

    # This should pass because it matches expected steps and ends at valid final step
    assert result.passed is True
    assert len(result.failures) == 0


def test_validate_ends_with_done():
    """Test validation passes when workflow ends with DONE."""
    expected = ["01-extract-serial", "02-check-warranty", "DONE"]
    actual = ["01-extract-serial", "02-check-warranty", "DONE"]

    result = validate_step_sequence(expected, actual)

    assert result.passed is True
    assert len(result.failures) == 0


def test_is_valid_final_step_send_confirmation():
    """Test 05-send-confirmation is recognized as valid final step."""
    assert _is_valid_final_step("05-send-confirmation") is True


def test_is_valid_final_step_out_of_scope():
    """Test 04-out-of-scope is recognized as valid final step."""
    assert _is_valid_final_step("04-out-of-scope") is True


def test_is_valid_final_step_request_serial():
    """Test 03d-request-serial is recognized as valid final step."""
    assert _is_valid_final_step("03d-request-serial") is True


def test_is_valid_final_step_done():
    """Test DONE is recognized as valid final step."""
    assert _is_valid_final_step("DONE") is True


def test_is_valid_final_step_invalid():
    """Test non-final steps are not recognized as valid final steps."""
    assert _is_valid_final_step("01-extract-serial") is False
    assert _is_valid_final_step("02-check-warranty") is False
    assert _is_valid_final_step("03a-valid-warranty") is False
    assert _is_valid_final_step(None) is False


def test_build_step_diff_exact_match():
    """Test diff builder with exact match."""
    expected = ["01-extract-serial", "02-check-warranty"]
    actual = ["01-extract-serial", "02-check-warranty"]

    diff = _build_step_diff(expected, actual)

    assert "Expected:" in diff
    assert "Actual:" in diff
    assert "01-extract-serial → 02-check-warranty" in diff
    assert "mismatch" not in diff  # No mismatch indicator


def test_build_step_diff_mismatch():
    """Test diff builder with mismatch."""
    expected = ["01-extract-serial", "02-check-warranty", "03a-valid-warranty"]
    actual = ["01-extract-serial", "02-check-warranty", "03b-device-not-found"]

    diff = _build_step_diff(expected, actual)

    assert "Expected:" in diff
    assert "Actual:" in diff
    assert "03a-valid-warranty" in diff
    assert "03b-device-not-found" in diff
    assert "mismatch" in diff


def test_build_step_diff_empty():
    """Test diff builder with empty sequences."""
    diff = _build_step_diff([], [])

    assert "No steps" in diff


def test_format_step_validation_failure():
    """Test formatting of validation failure."""
    result = validate_step_sequence(
        expected_steps=["01-extract-serial", "02-check-warranty"],
        actual_steps=["01-extract-serial", "03a-valid-warranty"]
    )

    formatted = format_step_validation_failure(result)

    assert "Step validation failed" in formatted
    assert "Expected:" in formatted
    assert "Actual:" in formatted
    assert "Step 2 mismatch" in formatted


def test_format_step_validation_success():
    """Test formatting returns empty string for success."""
    result = validate_step_sequence(
        expected_steps=["01-extract-serial"],
        actual_steps=["01-extract-serial"]
    )

    formatted = format_step_validation_failure(result)

    assert formatted == ""
