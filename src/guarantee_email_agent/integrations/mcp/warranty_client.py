"""Mock Warranty API MCP client for development.

This is a mock implementation. Real MCP integration will use custom
warranty_mcp_server in mcp_servers/warranty_mcp_server/.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class WarrantyMCPClient:
    """Mock Warranty API MCP client.

    Returns valid warranty with future expiration date.
    Real implementation will connect to custom MCP server wrapping warranty API.
    """

    def __init__(self, connection_string: str):
        """Initialize Warranty API MCP client.

        Args:
            connection_string: MCP connection string (e.g., "mcp://warranty-api")
        """
        self.connection_string = connection_string
        self.connected = False
        logger.info(f"Warranty MCP client initialized: {connection_string}")

    async def connect(self) -> None:
        """Connect to Warranty API MCP server (mock)."""
        # Simulate connection delay
        await asyncio.sleep(0.1)
        self.connected = True
        logger.info("Warranty MCP client connected (mock)")

    async def disconnect(self) -> None:
        """Disconnect from Warranty API MCP server (mock)."""
        self.connected = False
        logger.info("Warranty MCP client disconnected (mock)")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def check_warranty(self, serial_number: str) -> Dict[str, Any]:
        """Check warranty status for serial number (mock).

        Args:
            serial_number: Product serial number

        Returns:
            Dict with warranty information:
            {
                "serial_number": str,
                "status": "valid" | "expired" | "not_found",
                "expiration_date": str (ISO format)
            }
        """
        if not self.connected:
            raise ConnectionError("Warranty MCP client not connected")

        # Mock: always return valid warranty with future expiration
        expiration_date = (datetime.now() + timedelta(days=365)).date().isoformat()

        warranty_data = {
            "serial_number": serial_number,
            "status": "valid",
            "expiration_date": expiration_date
        }

        logger.info(
            f"Warranty checked for {serial_number}: "
            f"status={warranty_data['status']}, "
            f"expires={warranty_data['expiration_date']} (mock)"
        )

        return warranty_data
