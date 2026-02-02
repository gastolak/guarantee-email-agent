"""Tests for GmailTool."""
import pytest
from tenacity import RetryError
from guarantee_email_agent.tools.gmail_tool import GmailTool
from guarantee_email_agent.utils.errors import IntegrationError


@pytest.mark.asyncio
async def test_fetch_unread_emails_success(httpx_mock):
    """Test successful fetch of unread emails."""
    # Mock list messages response
    httpx_mock.add_response(
        url="https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is%3Aunread",
        json={"messages": [{"id": "msg1"}, {"id": "msg2"}]}
    )

    # Mock individual message fetches
    httpx_mock.add_response(
        url="https://gmail.googleapis.com/gmail/v1/users/me/messages/msg1?format=full",
        json={"id": "msg1", "snippet": "Test email 1"}
    )
    httpx_mock.add_response(
        url="https://gmail.googleapis.com/gmail/v1/users/me/messages/msg2?format=full",
        json={"id": "msg2", "snippet": "Test email 2"}
    )

    tool = GmailTool(
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        oauth_token="test-token",
        timeout=10
    )

    messages = await tool.fetch_unread_emails()
    assert len(messages) == 2
    assert messages[0]["id"] == "msg1"
    assert messages[1]["id"] == "msg2"

    await tool.close()


@pytest.mark.asyncio
async def test_fetch_unread_emails_empty(httpx_mock):
    """Test fetch when no unread emails."""
    httpx_mock.add_response(
        url="https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is%3Aunread",
        json={}
    )

    tool = GmailTool(
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        oauth_token="test-token",
        timeout=10
    )

    messages = await tool.fetch_unread_emails()
    assert len(messages) == 0

    await tool.close()


@pytest.mark.asyncio
async def test_fetch_unread_emails_error(httpx_mock):
    """Test fetch with HTTP error (retries 3 times)."""
    # Add same response 3 times for retry attempts
    for _ in range(3):
        httpx_mock.add_response(
            url="https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is%3Aunread",
            status_code=500
        )

    tool = GmailTool(
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        oauth_token="test-token",
        timeout=10
    )

    with pytest.raises(RetryError):
        await tool.fetch_unread_emails()

    await tool.close()


@pytest.mark.asyncio
async def test_send_email_success(httpx_mock):
    """Test successful email send."""
    httpx_mock.add_response(
        url="https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        json={"id": "sent-msg-123", "threadId": "thread-456"}
    )

    tool = GmailTool(
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        oauth_token="test-token",
        timeout=10
    )

    message_id = await tool.send_email(
        to="customer@example.com",
        subject="Test Subject",
        body="Test body",
        thread_id="thread-456"
    )

    assert message_id == "sent-msg-123"
    await tool.close()


@pytest.mark.asyncio
async def test_send_email_error(httpx_mock):
    """Test send email with HTTP error (retries 3 times)."""
    for _ in range(3):
        httpx_mock.add_response(
            url="https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            status_code=403
        )

    tool = GmailTool(
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        oauth_token="test-token",
        timeout=10
    )

    with pytest.raises(RetryError):
        await tool.send_email(
            to="customer@example.com",
            subject="Test",
            body="Body"
        )

    await tool.close()


@pytest.mark.asyncio
async def test_mark_as_read_success(httpx_mock):
    """Test successful mark as read."""
    httpx_mock.add_response(
        url="https://gmail.googleapis.com/gmail/v1/users/me/messages/msg123/modify",
        json={"id": "msg123", "labelIds": []}
    )

    tool = GmailTool(
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        oauth_token="test-token",
        timeout=10
    )

    await tool.mark_as_read("msg123")
    await tool.close()


@pytest.mark.asyncio
async def test_mark_as_read_error(httpx_mock):
    """Test mark as read with HTTP error (retries 3 times)."""
    for _ in range(3):
        httpx_mock.add_response(
            url="https://gmail.googleapis.com/gmail/v1/users/me/messages/msg123/modify",
            status_code=404
        )

    tool = GmailTool(
        api_endpoint="https://gmail.googleapis.com/gmail/v1",
        oauth_token="test-token",
        timeout=10
    )

    with pytest.raises(RetryError):
        await tool.mark_as_read("msg123")

    await tool.close()
