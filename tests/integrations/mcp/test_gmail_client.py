import pytest
import asyncio
from guarantee_email_agent.integrations.mcp.gmail_client import GmailMCPClient


@pytest.mark.asyncio
async def test_gmail_client_initialization():
    """Test Gmail client initialization"""
    client = GmailMCPClient("mcp://gmail")
    assert client.connection_string == "mcp://gmail"
    assert not client.connected


@pytest.mark.asyncio
async def test_gmail_client_connect():
    """Test Gmail client connection"""
    client = GmailMCPClient("mcp://gmail")
    await client.connect()
    assert client.connected


@pytest.mark.asyncio
async def test_gmail_monitor_inbox_empty():
    """Test monitoring inbox returns empty list on second poll (mock)"""
    client = GmailMCPClient("mcp://gmail")
    await client.connect()

    # First poll returns 1 mock email
    emails_first = await client.monitor_inbox()
    assert isinstance(emails_first, list)
    assert len(emails_first) == 1

    # Second poll returns empty
    emails_second = await client.monitor_inbox()
    assert isinstance(emails_second, list)
    assert len(emails_second) == 0


@pytest.mark.asyncio
async def test_gmail_send_email():
    """Test sending email returns message ID (mock)"""
    client = GmailMCPClient("mcp://gmail")
    await client.connect()

    message_id = await client.send_email(
        to="test@example.com",
        subject="Test Subject",
        body="Test Body"
    )

    assert isinstance(message_id, str)
    assert "mock_msg_" in message_id


@pytest.mark.asyncio
async def test_gmail_client_disconnect():
    """Test Gmail client disconnection"""
    client = GmailMCPClient("mcp://gmail")
    await client.connect()
    assert client.connected

    await client.disconnect()
    assert not client.connected


@pytest.mark.asyncio
async def test_gmail_operations_require_connection():
    """Test that operations fail when not connected"""
    from tenacity import RetryError

    client = GmailMCPClient("mcp://gmail")

    with pytest.raises(RetryError):
        await client.monitor_inbox()

    with pytest.raises(RetryError):
        await client.send_email("test@example.com", "Subject", "Body")
