"""Email data models for structured email processing."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class EmailMessage:
    """Structured email message (immutable, in-memory only per NFR16).

    Email content is never persisted to disk or database. It lives only in
    memory during processing to maintain stateless operation.

    Attributes:
        subject: Email subject line
        body: Email body content (plain text)
        from_address: Sender email address
        received_timestamp: When email was received
        thread_id: Optional email thread identifier for future use
        message_id: Optional unique message identifier
    """

    subject: str
    body: str
    from_address: str
    received_timestamp: datetime
    thread_id: Optional[str] = None
    message_id: Optional[str] = None

    def __str__(self) -> str:
        """String representation excluding body per NFR14.

        Customer email data (body) must not appear in INFO-level logs.
        Only metadata (subject, from, timestamp) is safe to log at INFO.

        Returns:
            String with subject, from, and timestamp (no body)
        """
        return (
            f"EmailMessage(subject='{self.subject}', "
            f"from='{self.from_address}', "
            f"received={self.received_timestamp.isoformat()})"
        )


@dataclass(frozen=True)
class SerialExtractionResult:
    """Result of serial number extraction from email.

    Attributes:
        serial_number: Extracted serial number (None if not found)
        confidence: Confidence score 0.0 to 1.0
        multiple_serials_detected: True if multiple serials found
        all_detected_serials: List of all detected serials
        extraction_method: How serial was extracted ("pattern", "llm", "none", "error")
        ambiguous: True if extraction uncertain (triggers graceful degradation)
    """

    serial_number: Optional[str]
    confidence: float
    multiple_serials_detected: bool
    all_detected_serials: List[str]
    extraction_method: str
    ambiguous: bool

    def is_successful(self) -> bool:
        """Check if serial number extraction succeeded.

        Returns:
            True if serial_number is not None
        """
        return self.serial_number is not None

    def should_use_graceful_degradation(self) -> bool:
        """Check if graceful degradation is recommended.

        Graceful degradation should be used when:
        - Extraction is ambiguous (multiple serials, unusual format)
        - Multiple serials detected with confidence < 0.8

        Returns:
            True if graceful degradation recommended
        """
        return self.ambiguous or (
            self.multiple_serials_detected and self.confidence < 0.8
        )
