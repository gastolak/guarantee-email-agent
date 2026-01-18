"""Mock Gmail MCP client for development.

This is a mock implementation. Real MCP integration will be implemented
when Gmail MCP server is available and configured.
"""

import logging
import asyncio
from typing import List, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EmailMessage:
    """Represents an email message."""

    def __init__(
        self,
        message_id: str,
        subject: str,
        from_addr: str,
        body: str,
        received: datetime,
        thread_id: Optional[str] = None
    ):
        self.message_id = message_id
        self.subject = subject
        self.from_addr = from_addr
        self.body = body
        self.received = received
        self.thread_id = thread_id


class GmailMCPClient:
    """Mock Gmail MCP client.

    Returns empty inbox and simulates email sending.
    Real implementation will use MCP Python SDK v1.25.0.
    """

    def __init__(self, connection_string: str):
        """Initialize Gmail MCP client.

        Args:
            connection_string: MCP connection string (e.g., "mcp://gmail")
        """
        self.connection_string = connection_string
        self.connected = False
        logger.info(f"Gmail MCP client initialized: {connection_string}")

    async def connect(self) -> None:
        """Connect to Gmail MCP server (mock)."""
        # Simulate connection delay
        await asyncio.sleep(0.1)
        self.connected = True
        logger.info("Gmail MCP client connected (mock)")

    async def disconnect(self) -> None:
        """Disconnect from Gmail MCP server (mock)."""
        self.connected = False
        logger.info("Gmail MCP client disconnected (mock)")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def monitor_inbox(self, label: str = "INBOX") -> List[EmailMessage]:
        """Monitor Gmail inbox for new emails (mock).

        Args:
            label: Gmail label to monitor (default: "INBOX")

        Returns:
            List of EmailMessage objects (empty in mock)
        """
        if not self.connected:
            raise ConnectionError("Gmail MCP client not connected")

        # Mock: return empty inbox
        logger.info(f"Gmail inbox monitored: {label} - 0 emails found (mock)")
        return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Send email via Gmail (mock).

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            thread_id: Optional thread ID for replies

        Returns:
            Message ID of sent email
        """
        if not self.connected:
            raise ConnectionError("Gmail MCP client not connected")

        # Mock: generate fake message ID
        message_id = f"mock_msg_{datetime.now().timestamp()}"

        logger.info(
            f"Email sent to {to}: subject='{subject}', "
            f"message_id={message_id} (mock)"
        )

        return message_id
