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
            # Check if this is Gmail API format or pre-parsed format
            if 'payload' in raw_email:
                # Gmail API format - extract from payload.headers
                headers = {h['name'].lower(): h['value'] for h in raw_email['payload'].get('headers', [])}
                subject = headers.get('subject', '(No Subject)')
                from_address = headers.get('from')
                if not from_address:
                    raise KeyError("'from'")

                # Extract timestamp from internalDate (milliseconds since epoch)
                internal_date_ms = raw_email.get('internalDate')
                if internal_date_ms:
                    received = datetime.fromtimestamp(int(internal_date_ms) / 1000)
                else:
                    received = datetime.now()

                # Extract body from payload
                body = self._extract_gmail_body(raw_email['payload'])

                # Use Gmail message ID and thread ID
                message_id = raw_email.get('id')
                thread_id = raw_email.get('threadId')
            else:
                # Pre-parsed format (eval/test mode)
                subject = raw_email.get('subject', '(No Subject)')
                from_address = raw_email['from']  # Required - will raise KeyError if missing

                # Extract timestamp (use current time if not provided)
                received = raw_email.get('received', datetime.now())

                # Extract body (prefer text_body, fall back to body)
                body = raw_email.get('text_body') or raw_email.get('body', '')

                # Extract optional fields
                thread_id = raw_email.get('thread_id')
                message_id = raw_email.get('message_id')

            # Parse timestamp to datetime if it's a string (for eval mode)
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
            # IMPORTANT: Email body ONLY in extra dict, NOT in message string
            logger.debug(
                "Email full content available in extra dict (NFR14 compliance)",
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

    def _extract_gmail_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from Gmail API payload.

        Gmail API nests body in parts with different mimeTypes.
        Prefer text/plain, fall back to text/html, decode base64.

        Args:
            payload: Gmail message payload

        Returns:
            Decoded email body text
        """
        import base64

        # Check if body is directly in payload
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        # Check parts for multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')

            # Fall back to text/html if no plain text
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/html' and part.get('body', {}).get('data'):
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    return self._html_to_text(html_body)

        return ''

    def _html_to_text(self, html: str) -> str:
        """Convert HTML email body to plain text.

        Handles HTML tags, entities, and special elements properly.
        Strips <style>, <script>, and HTML comments completely.

        Args:
            html: HTML content

        Returns:
            Plain text version with proper entity decoding
        """
        # Remove style and script tags and their content
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

        # Strip remaining HTML tags
        text = re.sub(r'<[^<]+?>', '', text)

        # Decode common HTML entities
        entity_map = {
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&#39;': "'",
        }
        for entity, char in entity_map.items():
            text = text.replace(entity, char)

        # Normalize whitespace (preserve paragraph breaks)
        text = re.sub(r'[ \t]+', ' ', text)  # Collapse horizontal whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Preserve paragraph breaks
        text = text.strip()

        return text
