import pytest
import asyncio
from guarantee_email_agent.integrations.mcp.ticketing_client import TicketingMCPClient


@pytest.mark.asyncio
async def test_ticketing_client_initialization():
    """Test Ticketing client initialization"""
    client = TicketingMCPClient("mcp://ticketing")
    assert client.connection_string == "mcp://ticketing"
    assert not client.connected


@pytest.mark.asyncio
async def test_ticketing_client_connect():
    """Test Ticketing client connection"""
    client = TicketingMCPClient("mcp://ticketing")
    await client.connect()
    assert client.connected


@pytest.mark.asyncio
async def test_create_ticket_returns_id():
    """Test creating ticket returns ticket ID (mock)"""
    client = TicketingMCPClient("mcp://ticketing")
    await client.connect()

    ticket_data = {
        "serial_number": "TEST123",
        "warranty_status": "valid",
        "customer_email": "test@example.com",
        "priority": "high",
        "category": "warranty_claim"
    }

    result = await client.create_ticket(ticket_data)

    assert "ticket_id" in result
    assert isinstance(result["ticket_id"], int)
    assert 10000 <= result["ticket_id"] <= 99999
    assert result["status"] == "created"
    assert "created_at" in result


@pytest.mark.asyncio
async def test_ticketing_client_disconnect():
    """Test Ticketing client disconnection"""
    client = TicketingMCPClient("mcp://ticketing")
    await client.connect()
    assert client.connected

    await client.disconnect()
    assert not client.connected


@pytest.mark.asyncio
async def test_create_ticket_requires_connection():
    """Test that create ticket fails when not connected"""
    from tenacity import RetryError

    client = TicketingMCPClient("mcp://ticketing")

    with pytest.raises(RetryError):
        await client.create_ticket({"serial_number": "TEST123"})
