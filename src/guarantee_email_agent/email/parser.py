"""Email parser for extracting structured data from raw emails."""

import logging
import re
from datetime import datetime
from typing import Dict, Any

from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.utils.errors import EmailParseError

logger = logging.getLogger(__name__)


class EmailParser:
    """Parse raw email data into structured EmailMessage.

    Handles plain text and HTML emails, extracts metadata, and ensures
    stateless processing (no disk I/O per NFR16).

    Logging follows NFR14: customer data (body) logged ONLY at DEBUG level.
    """

    def parse_email(self, raw_email: Dict[str, Any]) -> EmailMessage:
        """Parse raw email to EmailMessage dataclass.

        Args:
            raw_email: Raw email data from Gmail MCP
                Expected fields: subject, body (or text_body), from, received
                Optional fields: thread_id, message_id, content_type

        Returns:
            Parsed EmailMessage object (immutable, in-memory only)

        Raises:
            EmailParseError: If email cannot be parsed (missing required fields)
        """
        try:
            # Extract required fields
            subject = raw_email.get('subject', '(No Subject)')
            from_address = raw_email['from']  # Required - will raise KeyError if missing

            # Extract timestamp (use current time if not provided)
            received = raw_email.get('received', datetime.now())

            # Extract body (prefer text_body, fall back to body)
            body = raw_email.get('text_body') or raw_email.get('body', '')

            # Handle HTML emails (convert to plain text)
            content_type = raw_email.get('content_type', '')
            if content_type.startswith('text/html') and body:
                body = self._html_to_text(body)

            # Extract optional fields
            thread_id = raw_email.get('thread_id')
            message_id = raw_email.get('message_id')

            # Parse timestamp to datetime if it's a string
            if isinstance(received, str):
                received_timestamp = datetime.fromisoformat(received)
            else:
                received_timestamp = received

            # Create EmailMessage (immutable dataclass)
            email = EmailMessage(
                subject=subject,
                body=body,
                from_address=from_address,
                received_timestamp=received_timestamp,
                thread_id=thread_id,
                message_id=message_id
            )

            # Log email receipt at INFO level (NO body per NFR14)
            logger.info(
                f"Email received: subject='{email.subject}' from='{email.from_address}'",
                extra={
                    "subject": email.subject,
                    "from": email.from_address,
                    "received": email.received_timestamp.isoformat(),
                    "message_id": email.message_id
                }
            )

            # Log full content at DEBUG level ONLY (NFR14)
            logger.debug(
                f"Email content: {email.body[:100]}...",  # Truncated in message
                extra={
                    "subject": email.subject,
                    "from": email.from_address,
                    "body": email.body,  # Full body in extra dict, ONLY visible at DEBUG level
                    "thread_id": email.thread_id,
                    "message_id": email.message_id
                }
            )

            return email

        except KeyError as e:
            # Missing required field
            raise EmailParseError(
                message=f"Missing required email field: {e}",
                code="email_missing_field",
                details={"field": str(e), "available_fields": list(raw_email.keys())}
            )
        except Exception as e:
            # Any other parsing error
            raise EmailParseError(
                message=f"Email parsing failed: {str(e)}",
                code="email_parse_failed",
                details={"error": str(e)}
            )

    def _html_to_text(self, html: str) -> str:
        """Convert HTML email body to plain text.

        Simple HTML stripping - removes tags and normalizes whitespace.
        For production, consider using html2text library for better conversion.

        Args:
            html: HTML content

        Returns:
            Plain text version with tags stripped
        """
        # Strip HTML tags using regex
        text = re.sub('<[^<]+?>', '', html)

        # Normalize whitespace
        text = text.strip()

        # Replace multiple spaces/newlines with single space
        text = re.sub(r'\s+', ' ', text)

        return text
