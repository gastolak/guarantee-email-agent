"""Gmail tool for direct Gmail API integration."""
import httpx
import logging
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from guarantee_email_agent.utils.circuit_breaker import CircuitBreaker
from guarantee_email_agent.utils.errors import IntegrationError

logger = logging.getLogger(__name__)


class GmailTool:
    """Direct Gmail API integration with retry and circuit breaker."""

    def __init__(
        self,
        api_endpoint: str,
        oauth_token: str,
        timeout: int = 10
    ):
        """Initialize Gmail tool.

        Args:
            api_endpoint: Gmail API base URL (e.g., "https://gmail.googleapis.com/gmail/v1")
            oauth_token: OAuth2 access token
            timeout: Request timeout in seconds
        """
        self.api_endpoint = api_endpoint.rstrip("/")
        self.oauth_token = oauth_token
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(name="gmail", failure_threshold=5)
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {oauth_token}"}
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def fetch_unread_emails(self) -> List[Dict[str, Any]]:
        """Fetch unread emails from inbox.

        Returns:
            List of email message dictionaries

        Raises:
            IntegrationError: If API call fails after retries
        """
        try:
                logger.info(
                    "Fetching unread emails",
                    extra={"tool": "gmail", "operation": "fetch_unread_emails"}
                )

                # List messages with "is:unread" query
                response = await self.client.get(
                    f"{self.api_endpoint}/users/me/messages",
                    params={"q": "is:unread"}
                )
                response.raise_for_status()
                messages_list = response.json()

                message_ids = [msg["id"] for msg in messages_list.get("messages", [])]

                # Fetch full message details for each
                messages = []
                for msg_id in message_ids:
                    msg_response = await self.client.get(
                        f"{self.api_endpoint}/users/me/messages/{msg_id}",
                        params={"format": "full"}
                    )
                    msg_response.raise_for_status()
                    messages.append(msg_response.json())

                logger.info(
                    f"Fetched {len(messages)} unread emails",
                    extra={"tool": "gmail", "operation": "fetch_unread_emails", "count": len(messages)}
                )
                return messages

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to fetch unread emails: {e}",
                extra={"tool": "gmail", "operation": "fetch_unread_emails", "error": str(e)}
            )
            raise IntegrationError(f"Gmail fetch error: {e}", code="integration_error") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str = None
    ) -> str:
        """Send email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            thread_id: Optional thread ID for replies

        Returns:
            Message ID of sent email

        Raises:
            IntegrationError: If API call fails after retries
        """
        try:
                logger.info(
                    "Sending email",
                    extra={"tool": "gmail", "operation": "send_email", "to": to, "subject": subject}
                )

                # Build RFC 2822 message
                import base64
                from email.mime.text import MIMEText

                message = MIMEText(body)
                message["to"] = to
                message["subject"] = subject

                # Encode in base64url format
                encoded_message = base64.urlsafe_b64encode(
                    message.as_bytes()
                ).decode()

                payload = {"raw": encoded_message}
                if thread_id:
                    payload["threadId"] = thread_id

                response = await self.client.post(
                    f"{self.api_endpoint}/users/me/messages/send",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                message_id = result["id"]
                logger.info(
                    "Email sent successfully",
                    extra={"tool": "gmail", "operation": "send_email", "message_id": message_id}
                )
                return message_id

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to send email: {e}",
                extra={"tool": "gmail", "operation": "send_email", "error": str(e)}
            )
            raise IntegrationError(f"Gmail send error: {e}", code="integration_error") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def mark_as_read(self, message_id: str) -> None:
        """Mark email as read.

        Args:
            message_id: Gmail message ID

        Raises:
            IntegrationError: If API call fails after retries
        """
        try:
                logger.info(
                    "Marking email as read",
                    extra={"tool": "gmail", "operation": "mark_as_read", "message_id": message_id}
                )

                response = await self.client.post(
                    f"{self.api_endpoint}/users/me/messages/{message_id}/modify",
                    json={"removeLabelIds": ["UNREAD"]}
                )
                response.raise_for_status()

                logger.info(
                    "Email marked as read",
                    extra={"tool": "gmail", "operation": "mark_as_read", "message_id": message_id}
                )

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to mark email as read: {e}",
                extra={"tool": "gmail", "operation": "mark_as_read", "error": str(e)}
            )
            raise IntegrationError(f"Gmail mark read error: {e}", code="integration_error") from e

    async def close(self) -> None:
        """Close HTTP client connection pool."""
        await self.client.aclose()
