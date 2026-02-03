"""Models for step-based orchestration."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StepContext:
    """Context data passed between steps in the state machine.

    Attributes:
        email_subject: Email subject line
        email_body: Email body content
        from_address: Sender email address
        serial_number: Extracted serial number (None if not found)
        issue_description: Brief description of the issue (extracted from email)
        warranty_data: Warranty check response data
        ticket_id: Created ticket ID (None until ticket created)
        thread_id: Gmail thread ID for threading replies
        message_id: Original email message ID for In-Reply-To header
        function_calls: List of all function calls made during workflow
        metadata: Additional context data
    """
    email_subject: str
    email_body: str
    from_address: str
    serial_number: Optional[str] = None
    issue_description: str = "Brak opisu"
    warranty_data: Optional[Dict[str, Any]] = None
    ticket_id: Optional[str] = None
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    function_calls: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepExecutionResult:
    """Result from executing a step in the workflow.

    Attributes:
        next_step: Name of next step to execute (or "DONE")
        response_text: LLM response text from this step
        metadata: Extracted structured data (serial, reason, etc.)
        step_name: Name of the step that produced this result
        function_calls: List of function calls made during this step
    """
    next_step: str
    response_text: str
    metadata: Dict[str, Any]
    step_name: str
    function_calls: List[str] = field(default_factory=list)

    def is_done(self) -> bool:
        """Check if this is the final step (DONE state).

        Returns:
            True if workflow is complete, False otherwise
        """
        return self.next_step == "DONE"


@dataclass
class StepRoutingResult:
    """Result from initial step routing (entry point selection).

    Attributes:
        step_name: Name of step to start with
        confidence: Confidence score (0.0-1.0)
        routing_method: How step was selected (default, heuristic, llm)
    """
    step_name: str
    confidence: float
    routing_method: str
