"""Tests for eval data models."""

import pytest
from guarantee_email_agent.eval.models import (
    EvalEmail,
    EvalInput,
    EvalExpectedOutput,
    EvalTestCase,
    EvalResult,
)


def test_eval_email_creation():
    """Test creating EvalEmail dataclass."""
    email = EvalEmail(
        subject="Test subject",
        body="Test body",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    assert email.subject == "Test subject"
    assert email.body == "Test body"
    assert email.from_address == "test@example.com"
    assert email.received == "2026-01-18T10:00:00Z"


def test_eval_email_immutability():
    """Test that EvalEmail is immutable (frozen=True)."""
    email = EvalEmail(
        subject="Test",
        body="Body",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    with pytest.raises(AttributeError):
        email.subject = "Changed"


def test_eval_input_creation():
    """Test creating EvalInput dataclass."""
    email = EvalEmail(
        subject="Test",
        body="Body",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    input_data = EvalInput(
        email=email,
        mock_responses={
            "warranty_api": {"status": "valid", "expiration_date": "2025-12-31"}
        }
    )

    assert input_data.email == email
    assert input_data.mock_responses["warranty_api"]["status"] == "valid"


def test_eval_expected_output_creation():
    """Test creating EvalExpectedOutput dataclass."""
    expected = EvalExpectedOutput(
        email_sent=True,
        response_body_contains=["warranty is valid"],
        response_body_excludes=["expired"],
        ticket_created=True,
        ticket_fields={"serial_number": "SN12345", "priority": "normal"},
        scenario_instruction_used="valid-warranty",
        processing_time_ms=60000
    )

    assert expected.email_sent is True
    assert "warranty is valid" in expected.response_body_contains
    assert "expired" in expected.response_body_excludes
    assert expected.ticket_created is True
    assert expected.ticket_fields["serial_number"] == "SN12345"
    assert expected.scenario_instruction_used == "valid-warranty"
    assert expected.processing_time_ms == 60000


def test_eval_expected_output_optional_ticket_fields():
    """Test EvalExpectedOutput with None ticket_fields."""
    expected = EvalExpectedOutput(
        email_sent=True,
        response_body_contains=[],
        response_body_excludes=[],
        ticket_created=False,
        ticket_fields=None,
        scenario_instruction_used="test-scenario",
        processing_time_ms=30000
    )

    assert expected.ticket_fields is None


def test_eval_test_case_creation():
    """Test creating complete EvalTestCase."""
    email = EvalEmail(
        subject="Test",
        body="Body with SN12345",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    input_data = EvalInput(
        email=email,
        mock_responses={"warranty_api": {"status": "valid"}}
    )

    expected = EvalExpectedOutput(
        email_sent=True,
        response_body_contains=["valid"],
        response_body_excludes=["expired"],
        ticket_created=True,
        ticket_fields={"serial_number": "SN12345"},
        scenario_instruction_used="valid-warranty",
        processing_time_ms=60000
    )

    test_case = EvalTestCase(
        scenario_id="valid_warranty_001",
        description="Customer with valid warranty",
        category="valid-warranty",
        created="2026-01-18",
        input=input_data,
        expected_output=expected
    )

    assert test_case.scenario_id == "valid_warranty_001"
    assert test_case.description == "Customer with valid warranty"
    assert test_case.category == "valid-warranty"
    assert test_case.input == input_data
    assert test_case.expected_output == expected


def test_eval_result_creation_passed():
    """Test creating EvalResult for passing test."""
    email = EvalEmail(
        subject="Test",
        body="Body",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    input_data = EvalInput(email=email, mock_responses={})
    expected = EvalExpectedOutput(
        email_sent=True,
        response_body_contains=[],
        response_body_excludes=[],
        ticket_created=False,
        ticket_fields=None,
        scenario_instruction_used="test",
        processing_time_ms=60000
    )

    test_case = EvalTestCase(
        scenario_id="test_001",
        description="Test scenario",
        category="test",
        created="2026-01-18",
        input=input_data,
        expected_output=expected
    )

    result = EvalResult(
        test_case=test_case,
        passed=True,
        failures=[],
        actual_output={"email_sent": True},
        processing_time_ms=5000
    )

    assert result.passed is True
    assert len(result.failures) == 0
    assert result.processing_time_ms == 5000


def test_eval_result_creation_failed():
    """Test creating EvalResult for failing test."""
    email = EvalEmail(
        subject="Test",
        body="Body",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    input_data = EvalInput(email=email, mock_responses={})
    expected = EvalExpectedOutput(
        email_sent=True,
        response_body_contains=["warranty is valid"],
        response_body_excludes=[],
        ticket_created=False,
        ticket_fields=None,
        scenario_instruction_used="test",
        processing_time_ms=60000
    )

    test_case = EvalTestCase(
        scenario_id="test_002",
        description="Test scenario",
        category="test",
        created="2026-01-18",
        input=input_data,
        expected_output=expected
    )

    result = EvalResult(
        test_case=test_case,
        passed=False,
        failures=["response_body_contains: missing phrase 'warranty is valid'"],
        actual_output={"email_sent": True, "response_body": "Different text"},
        processing_time_ms=5000
    )

    assert result.passed is False
    assert len(result.failures) == 1
    assert "missing phrase" in result.failures[0]


def test_eval_result_format_for_display_passed():
    """Test format_for_display() method for passed test."""
    email = EvalEmail(
        subject="Test",
        body="Body",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    input_data = EvalInput(email=email, mock_responses={})
    expected = EvalExpectedOutput(
        email_sent=True,
        response_body_contains=[],
        response_body_excludes=[],
        ticket_created=False,
        ticket_fields=None,
        scenario_instruction_used="test",
        processing_time_ms=60000
    )

    test_case = EvalTestCase(
        scenario_id="test_003",
        description="Passing test scenario",
        category="test",
        created="2026-01-18",
        input=input_data,
        expected_output=expected
    )

    result = EvalResult(
        test_case=test_case,
        passed=True,
        failures=[],
        actual_output={},
        processing_time_ms=5000
    )

    display = result.format_for_display()

    assert "✓" in display
    assert "test_003" in display
    assert "Passing test scenario" in display
    assert "FAILED" not in display


def test_eval_result_format_for_display_failed():
    """Test format_for_display() method for failed test."""
    email = EvalEmail(
        subject="Test",
        body="Body",
        from_address="test@example.com",
        received="2026-01-18T10:00:00Z"
    )

    input_data = EvalInput(email=email, mock_responses={})
    expected = EvalExpectedOutput(
        email_sent=True,
        response_body_contains=[],
        response_body_excludes=[],
        ticket_created=False,
        ticket_fields=None,
        scenario_instruction_used="test",
        processing_time_ms=60000
    )

    test_case = EvalTestCase(
        scenario_id="test_004",
        description="Failing test scenario",
        category="test",
        created="2026-01-18",
        input=input_data,
        expected_output=expected
    )

    result = EvalResult(
        test_case=test_case,
        passed=False,
        failures=["Some failure"],
        actual_output={},
        processing_time_ms=5000
    )

    display = result.format_for_display()

    assert "✗" in display
    assert "test_004" in display
    assert "Failing test scenario" in display
    assert "FAILED" in display
