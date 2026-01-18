import pytest
import asyncio
from datetime import datetime
from guarantee_email_agent.integrations.mcp.warranty_client import WarrantyMCPClient


@pytest.mark.asyncio
async def test_warranty_client_initialization():
    """Test Warranty client initialization"""
    client = WarrantyMCPClient("mcp://warranty-api")
    assert client.connection_string == "mcp://warranty-api"
    assert not client.connected


@pytest.mark.asyncio
async def test_warranty_client_connect():
    """Test Warranty client connection"""
    client = WarrantyMCPClient("mcp://warranty-api")
    await client.connect()
    assert client.connected


@pytest.mark.asyncio
async def test_warranty_check_returns_valid():
    """Test warranty check returns valid status with future date (mock)"""
    client = WarrantyMCPClient("mcp://warranty-api")
    await client.connect()

    result = await client.check_warranty("TEST123")

    assert result["serial_number"] == "TEST123"
    assert result["status"] == "valid"
    assert "expiration_date" in result

    # Verify expiration date is in the future
    expiration = datetime.fromisoformat(result["expiration_date"])
    assert expiration > datetime.now()


@pytest.mark.asyncio
async def test_warranty_client_disconnect():
    """Test Warranty client disconnection"""
    client = WarrantyMCPClient("mcp://warranty-api")
    await client.connect()
    assert client.connected

    await client.disconnect()
    assert not client.connected


@pytest.mark.asyncio
async def test_warranty_check_requires_connection():
    """Test that warranty check fails when not connected"""
    from tenacity import RetryError

    client = WarrantyMCPClient("mcp://warranty-api")

    with pytest.raises(RetryError):
        await client.check_warranty("TEST123")
