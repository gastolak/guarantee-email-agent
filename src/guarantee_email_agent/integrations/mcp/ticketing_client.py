"""Mock Ticketing System MCP client for development.

This is a mock implementation. Real MCP integration will use custom
ticketing_mcp_server in mcp_servers/ticketing_mcp_server/.
"""

import logging
import asyncio
import random
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class TicketingMCPClient:
    """Mock Ticketing System MCP client.

    Returns random ticket ID for created tickets.
    Real implementation will connect to custom MCP server wrapping ticketing API.
    """

    def __init__(self, connection_string: str):
        """Initialize Ticketing System MCP client.

        Args:
            connection_string: MCP connection string (e.g., "mcp://ticketing")
        """
        self.connection_string = connection_string
        self.connected = False
        logger.info(f"Ticketing MCP client initialized: {connection_string}")

    async def connect(self) -> None:
        """Connect to Ticketing System MCP server (mock)."""
        # Simulate connection delay
        await asyncio.sleep(0.1)
        self.connected = True
        logger.info("Ticketing MCP client connected (mock)")

    async def disconnect(self) -> None:
        """Disconnect from Ticketing System MCP server (mock)."""
        self.connected = False
        logger.info("Ticketing MCP client disconnected (mock)")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create support ticket (mock).

        Args:
            ticket_data: Ticket information dict containing:
                - serial_number: str
                - warranty_status: str
                - customer_email: str
                - priority: str
                - category: str
                - description: str (optional)

        Returns:
            Dict with ticket creation result:
            {
                "ticket_id": int,
                "status": "created",
                "created_at": str (ISO format)
            }
        """
        if not self.connected:
            raise ConnectionError("Ticketing MCP client not connected")

        # Mock: generate random ticket ID
        ticket_id = random.randint(10000, 99999)

        from datetime import datetime
        result = {
            "ticket_id": ticket_id,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }

        logger.info(
            f"Ticket created: ticket_id={ticket_id}, "
            f"serial={ticket_data.get('serial_number', 'N/A')}, "
            f"priority={ticket_data.get('priority', 'N/A')} (mock)"
        )

        return result
