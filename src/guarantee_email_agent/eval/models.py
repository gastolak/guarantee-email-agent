"""Data models for eval framework."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass(frozen=True)
class EvalEmail:
    """Email input for eval test case."""

    subject: str
    body: str
    from_address: str  # 'from' is Python keyword, use from_address
    received: str


@dataclass(frozen=True)
class ExpectedFunctionCall:
    """Expected function call in eval test case."""

    function_name: str
    arguments: Optional[Dict[str, Any]] = None  # Exact match
    arguments_contain: Optional[Dict[str, Any]] = None  # Partial match
    result_contains: Optional[Dict[str, Any]] = None  # Validate result
    body_contains: Optional[List[str]] = None  # For send_email: check body content


@dataclass(frozen=True)
class EvalInput:
    """Input section of eval test case."""

    email: EvalEmail
    mock_responses: Dict[str, Dict]  # Legacy format
    mock_function_responses: Optional[Dict[str, Dict]] = None  # New format for function calling


@dataclass(frozen=True)
class EvalExpectedOutput:
    """Expected output section of eval test case."""

    scenario_instruction_used: str
    processing_time_ms: int = 60000

    # Function call expectations (new - primary validation method)
    expected_function_calls: Optional[List[ExpectedFunctionCall]] = None

    # Step-based workflow expectations (Story 5.1)
    expected_steps: Optional[List[str]] = None  # Expected step sequence (e.g., ["01-extract-serial", "02-check-warranty", "DONE"])

    # Legacy fields (kept for backwards compatibility, derived from function calls)
    email_sent: Optional[bool] = None  # Derived from send_email function call
    response_body_contains: Optional[List[str]] = None  # Moved to send_email body_contains
    response_body_excludes: Optional[List[str]] = None
    ticket_created: Optional[bool] = None  # Derived from create_ticket function call
    ticket_fields: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class EvalTestCase:
    """Complete eval test case."""

    scenario_id: str
    description: str
    category: str
    created: str
    input: EvalInput
    expected_output: EvalExpectedOutput


@dataclass(frozen=True)
class ActualFunctionCall:
    """Actual function call recorded during eval execution."""

    function_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    execution_time_ms: int
    error_message: Optional[str] = None


@dataclass
class EvalResult:
    """Result of executing one eval test case."""

    test_case: EvalTestCase
    passed: bool
    failures: List[str]
    actual_output: Dict[str, Any]
    processing_time_ms: int
    actual_function_calls: List[ActualFunctionCall] = field(default_factory=list)
    actual_steps: List[str] = field(default_factory=list)  # Actual step sequence (Story 5.1)

    def format_for_display(self) -> str:
        """Format result for display."""
        status = "✓" if self.passed else "✗"
        result_text = f"{status} {self.test_case.scenario_id}: {self.test_case.description}"
        if not self.passed:
            result_text += " - FAILED"
        return result_text

    def format_function_calls(self) -> str:
        """Format function calls for display."""
        if not self.actual_function_calls:
            return "  No function calls recorded"

        lines = []
        for i, fc in enumerate(self.actual_function_calls, 1):
            status = "✓" if fc.success else "✗"
            lines.append(f"  {i}. {status} {fc.function_name}({_format_args(fc.arguments)})")
            if fc.result:
                lines.append(f"     → {_truncate(str(fc.result), 60)}")
            if fc.error_message:
                lines.append(f"     ✗ Error: {fc.error_message}")
        return "\n".join(lines)


def _format_args(args: Dict[str, Any]) -> str:
    """Format function arguments for display."""
    if not args:
        return ""
    parts = [f"{k}={_truncate(repr(v), 30)}" for k, v in args.items()]
    return ", ".join(parts)


def _truncate(s: str, max_len: int) -> str:
    """Truncate string with ellipsis."""
    return s if len(s) <= max_len else s[:max_len - 3] + "..."
