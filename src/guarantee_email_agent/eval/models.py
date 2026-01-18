"""Data models for eval framework."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


@dataclass(frozen=True)
class EvalEmail:
    """Email input for eval test case."""

    subject: str
    body: str
    from_address: str  # 'from' is Python keyword, use from_address
    received: str


@dataclass(frozen=True)
class EvalInput:
    """Input section of eval test case."""

    email: EvalEmail
    mock_responses: Dict[str, Dict]


@dataclass(frozen=True)
class EvalExpectedOutput:
    """Expected output section of eval test case."""

    email_sent: bool
    response_body_contains: List[str]
    response_body_excludes: List[str]
    ticket_created: bool
    ticket_fields: Optional[Dict[str, str]]
    scenario_instruction_used: str
    processing_time_ms: int


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
class EvalResult:
    """Result of executing one eval test case."""

    test_case: EvalTestCase
    passed: bool
    failures: List[str]
    actual_output: Dict[str, Any]
    processing_time_ms: int

    def format_for_display(self) -> str:
        """Format result for display."""
        status = "✓" if self.passed else "✗"
        result_text = f"{status} {self.test_case.scenario_id}: {self.test_case.description}"
        if not self.passed:
            result_text += " - FAILED"
        return result_text
