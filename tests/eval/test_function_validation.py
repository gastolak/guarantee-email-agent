"""Unit tests for function call validation."""

import pytest

from guarantee_email_agent.eval.models import ExpectedFunctionCall, ActualFunctionCall
from guarantee_email_agent.eval.validator import (
    validate_function_calls,
    validate_email_sent,
)


class TestValidateFunctionCalls:
    """Tests for validate_function_calls function."""

    def test_all_validations_pass(self):
        """Test when all function calls match expected."""
        expected = [
            ExpectedFunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN12345"},
            ),
            ExpectedFunctionCall(
                function_name="send_email",
                arguments_contain={"to": "customer@"},
                body_contains=["warranty", "valid"],
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN12345"},
                result={"status": "valid"},
                success=True,
                execution_time_ms=100,
            ),
            ActualFunctionCall(
                function_name="send_email",
                arguments={
                    "to": "customer@example.com",
                    "subject": "Re: Warranty",
                    "body": "Your warranty is valid until 2025."
                },
                result={"message_id": "msg-123"},
                success=True,
                execution_time_ms=200,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert failures == []

    def test_function_count_mismatch(self):
        """Test failure when function counts don't match."""
        expected = [
            ExpectedFunctionCall(function_name="check_warranty"),
            ExpectedFunctionCall(function_name="send_email"),
        ]

        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={},
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("count mismatch" in f.lower() for f in failures)

    def test_function_name_mismatch(self):
        """Test failure when function name doesn't match."""
        expected = [
            ExpectedFunctionCall(function_name="check_warranty"),
        ]

        actual = [
            ActualFunctionCall(
                function_name="create_ticket",
                arguments={},
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("name mismatch" in f.lower() for f in failures)
        assert any("check_warranty" in f for f in failures)
        assert any("create_ticket" in f for f in failures)

    def test_exact_argument_match(self):
        """Test exact argument matching."""
        expected = [
            ExpectedFunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN12345"},
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN99999"},  # Wrong value
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("mismatch" in f.lower() for f in failures)
        assert any("SN12345" in f for f in failures)

    def test_partial_argument_match(self):
        """Test partial argument matching with arguments_contain."""
        expected = [
            ExpectedFunctionCall(
                function_name="send_email",
                arguments_contain={"to": "customer@"},
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="send_email",
                arguments={"to": "customer@example.com", "subject": "Test"},
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert failures == []

    def test_partial_argument_not_found(self):
        """Test failure when partial argument not found."""
        expected = [
            ExpectedFunctionCall(
                function_name="send_email",
                arguments_contain={"to": "admin@"},
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="send_email",
                arguments={"to": "customer@example.com"},
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("does not contain" in f.lower() for f in failures)

    def test_result_contains_validation(self):
        """Test result_contains validation."""
        expected = [
            ExpectedFunctionCall(
                function_name="check_warranty",
                result_contains={"status": "valid"},
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={},
                result={"status": "valid", "expiration_date": "2025-12-31"},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert failures == []

    def test_result_contains_failure(self):
        """Test failure when result doesn't contain expected values."""
        expected = [
            ExpectedFunctionCall(
                function_name="check_warranty",
                result_contains={"status": "valid"},
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={},
                result={"status": "expired"},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("does not contain" in f.lower() for f in failures)

    def test_body_contains_validation(self):
        """Test body_contains validation for send_email."""
        expected = [
            ExpectedFunctionCall(
                function_name="send_email",
                body_contains=["warranty", "valid", "SN12345"],
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="send_email",
                arguments={
                    "to": "test@test.com",
                    "subject": "Test",
                    "body": "Your warranty for SN12345 is valid until 2025."
                },
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert failures == []

    def test_body_contains_missing_phrase(self):
        """Test failure when body doesn't contain expected phrase."""
        expected = [
            ExpectedFunctionCall(
                function_name="send_email",
                body_contains=["warranty", "expired"],
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="send_email",
                arguments={
                    "to": "test@test.com",
                    "subject": "Test",
                    "body": "Your warranty is valid."  # Missing "expired"
                },
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("expired" in f.lower() for f in failures)

    def test_function_call_failed(self):
        """Test failure reporting when function call failed."""
        expected = [
            ExpectedFunctionCall(function_name="check_warranty"),
        ]

        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={},
                result={},
                success=False,
                execution_time_ms=100,
                error_message="Connection timeout",
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("failed" in f.lower() for f in failures)
        assert any("Connection timeout" in f for f in failures)

    def test_extra_unexpected_calls(self):
        """Test detection of unexpected function calls."""
        expected = [
            ExpectedFunctionCall(function_name="send_email"),
        ]

        actual = [
            ActualFunctionCall(
                function_name="send_email",
                arguments={},
                result={},
                success=True,
                execution_time_ms=100,
            ),
            ActualFunctionCall(
                function_name="check_warranty",  # Unexpected
                arguments={},
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert any("unexpected" in f.lower() for f in failures)
        assert any("check_warranty" in f for f in failures)

    def test_empty_expected_and_actual(self):
        """Test with empty lists."""
        failures = validate_function_calls([], [])
        assert failures == []

    def test_case_insensitive_body_contains(self):
        """Test that body_contains is case-insensitive."""
        expected = [
            ExpectedFunctionCall(
                function_name="send_email",
                body_contains=["WARRANTY", "VALID"],
            ),
        ]

        actual = [
            ActualFunctionCall(
                function_name="send_email",
                arguments={"body": "your warranty is valid"},
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failures = validate_function_calls(expected, actual)
        assert failures == []


class TestValidateEmailSent:
    """Tests for validate_email_sent function."""

    def test_email_sent_successfully(self):
        """Test when send_email was called successfully."""
        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={},
                result={},
                success=True,
                execution_time_ms=100,
            ),
            ActualFunctionCall(
                function_name="send_email",
                arguments={},
                result={},
                success=True,
                execution_time_ms=200,
            ),
        ]

        failure = validate_email_sent(actual)
        assert failure is None

    def test_email_not_sent(self):
        """Test when send_email was not called."""
        actual = [
            ActualFunctionCall(
                function_name="check_warranty",
                arguments={},
                result={},
                success=True,
                execution_time_ms=100,
            ),
        ]

        failure = validate_email_sent(actual)
        assert failure is not None
        assert "send_email" in failure.lower()

    def test_email_send_failed(self):
        """Test when send_email was called but failed."""
        actual = [
            ActualFunctionCall(
                function_name="send_email",
                arguments={},
                result={},
                success=False,
                execution_time_ms=100,
                error_message="Send failed",
            ),
        ]

        failure = validate_email_sent(actual)
        assert failure is not None
        assert "send_email" in failure.lower()

    def test_empty_calls(self):
        """Test with no function calls."""
        failure = validate_email_sent([])
        assert failure is not None
