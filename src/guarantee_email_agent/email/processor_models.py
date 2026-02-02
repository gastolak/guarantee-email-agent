"""Data models for email processing pipeline."""

from dataclasses import dataclass, field
from typing import Any, Optional, List


@dataclass(frozen=True)
class ScenarioDetectionResult:
    """Result of scenario detection from email content.

    Attributes:
        scenario_name: Detected scenario ("valid-warranty", "missing-info", "out-of-scope", etc.)
        confidence: Detection confidence 0.0 to 1.0
        is_warranty_inquiry: True if this is a warranty-related inquiry
        detected_intent: Intent classification ("warranty_check", "missing_information", "spam", etc.)
        detection_method: How scenario was detected ("heuristic", "llm", "fallback")
        ambiguous: True if detection uncertain (triggers graceful degradation)
    """

    scenario_name: str
    confidence: float
    is_warranty_inquiry: bool
    detected_intent: str
    detection_method: str
    ambiguous: bool

    def should_process(self) -> bool:
        """Check if email should be processed.

        Returns:
            False for out-of-scope/spam scenarios, True otherwise
        """
        return self.scenario_name not in ("out-of-scope", "spam")

    def get_scenario_for_routing(self) -> str:
        """Get scenario name for instruction routing.

        Returns:
            Scenario name for ScenarioRouter
        """
        return self.scenario_name


@dataclass(frozen=True)
class ProcessingResult:
    """Result of complete email processing pipeline.

    Tracks outcome of all processing steps from parse → response → ticket.

    Attributes:
        success: True if processing completed successfully
        email_id: Email message ID for tracking
        scenario_used: Scenario name used for response ("valid-warranty", "missing-info", etc.)
        serial_number: Extracted serial number (None if not found)
        warranty_status: Warranty validation result ("valid", "expired", "not_found", None)
        response_sent: True if email response was sent successfully
        ticket_created: True if support ticket was created
        ticket_id: Ticket ID from ticketing system (None if not created)
        processing_time_ms: Total processing time in milliseconds
        error_message: Error message if processing failed (None if successful)
        failed_step: Step where processing failed (None if successful)
        step_sequence: Sequence of steps executed in step-based mode (Story 5.1)
        function_calls: List of function calls made during processing (for eval validation)
    """

    success: bool
    email_id: str
    scenario_used: Optional[str]
    serial_number: Optional[str]
    warranty_status: Optional[str]
    response_sent: bool
    ticket_created: bool
    ticket_id: Optional[str]
    processing_time_ms: int
    error_message: Optional[str]
    failed_step: Optional[str]
    step_sequence: List[str] = field(default_factory=list)
    function_calls: List[Any] = field(default_factory=list)

    def is_successful(self) -> bool:
        """Check if processing completed successfully.

        Returns:
            True if success flag is True
        """
        return self.success

    def requires_retry(self) -> bool:
        """Check if processing should be retried.

        Retry logic: Only retry for transient failures at certain steps.
        Transient steps: validate_warranty, generate_response, send_email

        Returns:
            True if failed at a transient step that should be retried
        """
        transient_steps = ["validate_warranty", "generate_response", "send_email"]
        return not self.success and self.failed_step in transient_steps
