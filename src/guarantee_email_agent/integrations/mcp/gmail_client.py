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
        self._poll_count = 0  # Track number of polls for mock data
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
            List of EmailMessage objects (returns 1 real email on first poll, then empty)
        """
        if not self.connected:
            raise ConnectionError("Gmail MCP client not connected")

        self._poll_count += 1

        # Return a real email on first poll for testing
        if self._poll_count == 1:
            # Real email from ACNET about RMA warranty claim
            mock_email = {
                "message_id": "CAAP6shSLNa0_NPqKPxueDps8=xRpNfG50Wg0cFxKKOMBgUpkmA@mail.gmail.com",
                "subject": "Re: [Ticket#72277145] [EXT] Mediant Teletaxi v1",
                "from": "Adam Przetak <adam.przetak@acnet.com.pl>",
                "to": "wirtualny.serwis-test@acnet.com.pl",
                "date": "2025-10-27T15:38:29+01:00",
                "body": """Dzień dobry,

Zgłaszamy na RMA jako uszkodzoną kolejną (drugą) bramę Mediant pod tego klienta. Brama nie działa prawidłowo, jest obecnie w jakimś trybie 'awaryjnym' i nie udało nam się uzyskać poprzez serwis odpowiedzi na ten problem od inżyniera Audiocodes. Czy możemy zmienić bramę w tym projekcie na normalnego Medianta M500 lub M500L (z serii SBC) zamianst M500Li (seria MSBR)? Uruchomiliśmy dziesiątki M500/M500L i nigdby nie było problemów, a tu druga pod rząd M500Li, która nie działa poprawnie.

pozdrawiam,

Pozdrawiam/Regards
Adam Przetak
CTO
+48 603 753 793
adam.przetak@acnet.com.pl

ul. Sokołowska 9 lok. U4 01-142 Warszawa
NIP: 525 192 06 57"""
            }

            logger.info(f"Gmail inbox monitored: {label} - 1 email found (mock)")
            return [mock_email]

        # Subsequent polls return empty inbox
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
