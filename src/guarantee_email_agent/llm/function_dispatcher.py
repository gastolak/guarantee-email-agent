"""Function dispatcher for routing LLM function calls to clients.

This module provides the FunctionDispatcher class that routes function calls
from the LLM to the appropriate MCP client methods.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional, Protocol

from guarantee_email_agent.llm.function_calling import FunctionCall

logger = logging.getLogger(__name__)


class WarrantyClientProtocol(Protocol):
    """Protocol for warranty client interface."""

    async def check_warranty(self, serial_number: str) -> Dict[str, Any]:
        """Check warranty status for a serial number."""
        ...


class TicketingClientProtocol(Protocol):
    """Protocol for ticketing client interface."""

    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a support ticket."""
        ...


class GmailClientProtocol(Protocol):
    """Protocol for Gmail client interface."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Send an email."""
        ...


class FunctionDispatcher:
    """Dispatch function calls from LLM to appropriate MCP clients.

    Maps function names to client methods and handles execution with
    logging, timing, and error handling.

    Attributes:
        warranty_client: Client for warranty API calls
        ticketing_client: Client for ticketing system calls
        gmail_client: Client for Gmail operations
    """

    def __init__(
        self,
        warranty_client: Optional[WarrantyClientProtocol] = None,
        ticketing_client: Optional[TicketingClientProtocol] = None,
        gmail_client: Optional[GmailClientProtocol] = None
    ):
        """Initialize FunctionDispatcher with client instances.

        Args:
            warranty_client: Warranty API MCP client
            ticketing_client: Ticketing system MCP client
            gmail_client: Gmail MCP client
        """
        self._warranty_client = warranty_client
        self._ticketing_client = ticketing_client
        self._gmail_client = gmail_client

        logger.info(
            "FunctionDispatcher initialized",
            extra={
                "has_warranty_client": warranty_client is not None,
                "has_ticketing_client": ticketing_client is not None,
                "has_gmail_client": gmail_client is not None
            }
        )

    async def execute(
        self,
        function_name: str,
        arguments: Dict[str, Any]
    ) -> FunctionCall:
        """Execute a function call and return the result.

        Routes the function call to the appropriate client method,
        tracks execution time, and returns a FunctionCall record.

        Args:
            function_name: Name of function to call
            arguments: Function arguments as dictionary

        Returns:
            FunctionCall with result and execution metadata

        Raises:
            ValueError: If function_name is unknown
        """
        start_time = time.time()

        logger.info(
            "Executing function",
            extra={
                "function": function_name,
                "arguments": arguments
            }
        )

        # Check for unknown function first - this should raise immediately
        if function_name not in ("check_warranty", "create_ticket", "send_email"):
            raise ValueError(f"Unknown function: {function_name}")

        try:
            if function_name == "check_warranty":
                result = await self._execute_check_warranty(arguments)
            elif function_name == "create_ticket":
                result = await self._execute_create_ticket(arguments)
            elif function_name == "send_email":
                result = await self._execute_send_email(arguments)

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Function executed successfully",
                extra={
                    "function": function_name,
                    "execution_time_ms": execution_time_ms,
                    "result_keys": list(result.keys()) if isinstance(result, dict) else None
                }
            )

            return FunctionCall(
                function_name=function_name,
                arguments=arguments,
                result=result,
                execution_time_ms=execution_time_ms,
                success=True
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "Function execution failed",
                extra={
                    "function": function_name,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms
                },
                exc_info=True
            )

            return FunctionCall(
                function_name=function_name,
                arguments=arguments,
                result={},
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(e)
            )

    async def _execute_check_warranty(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute check_warranty function.

        Args:
            arguments: Must contain 'serial_number'

        Returns:
            Warranty status result

        Raises:
            ValueError: If warranty client not configured or serial_number missing
        """
        if self._warranty_client is None:
            raise ValueError("Warranty client not configured")

        serial_number = arguments.get("serial_number")
        if not serial_number:
            raise ValueError("Missing required argument: serial_number")

        result = await self._warranty_client.check_warranty(serial_number)
        return result

    async def _execute_create_ticket(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create_ticket function.

        Args:
            arguments: Ticket data (serial_number, customer_email, priority, etc.)

        Returns:
            Ticket creation result

        Raises:
            ValueError: If ticketing client not configured
        """
        if self._ticketing_client is None:
            raise ValueError("Ticketing client not configured")

        # Pass all arguments as ticket_data
        result = await self._ticketing_client.create_ticket(arguments)
        return result

    async def _execute_send_email(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute send_email function.

        Args:
            arguments: Must contain 'to', 'subject', 'body'; optional 'thread_id'

        Returns:
            Email send result with message_id and status

        Raises:
            ValueError: If Gmail client not configured or required args missing
        """
        if self._gmail_client is None:
            raise ValueError("Gmail client not configured")

        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")
        thread_id = arguments.get("thread_id")

        if not to:
            raise ValueError("Missing required argument: to")
        if not subject:
            raise ValueError("Missing required argument: subject")
        if not body:
            raise ValueError("Missing required argument: body")

        message_id = await self._gmail_client.send_email(
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id
        )

        return {
            "message_id": message_id,
            "status": "sent"
        }

    def get_available_functions(self) -> list[str]:
        """Get list of available function names based on configured clients.

        Returns:
            List of function names that can be executed
        """
        available = []
        if self._warranty_client is not None:
            available.append("check_warranty")
        if self._ticketing_client is not None:
            available.append("create_ticket")
        if self._gmail_client is not None:
            available.append("send_email")
        return available
