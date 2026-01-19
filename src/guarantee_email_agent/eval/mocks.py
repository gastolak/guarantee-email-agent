"""Mock framework for MCP and LLM clients in eval."""

import logging
import time
from typing import Dict, List, Any, Optional

from guarantee_email_agent.eval.models import EvalTestCase, ActualFunctionCall
from guarantee_email_agent.llm.function_calling import FunctionCall

logger = logging.getLogger(__name__)


class MockGmailClient:
    """Mock Gmail MCP client for eval."""

    def __init__(self, test_case: EvalTestCase):
        """Initialize with test case data.

        Args:
            test_case: Eval test case with input email
        """
        self.test_case = test_case
        self.sent_emails: List[Dict[str, Any]] = []

    async def get_unread_emails(self) -> List[Dict[str, Any]]:
        """Return email from test case."""
        # Not used in eval (email provided directly)
        return []

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
    ) -> None:
        """Capture sent email (don't actually send).

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            thread_id: Optional thread ID
        """
        sent_email = {
            "to": to,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
        }
        self.sent_emails.append(sent_email)
        logger.debug(f"Mock: Email sent to {to}")

    async def close(self) -> None:
        """Close connection (no-op for mock)."""
        pass


class MockWarrantyAPIClient:
    """Mock Warranty API MCP client for eval."""

    def __init__(self, test_case: EvalTestCase):
        """Initialize with mock responses from test case.

        Args:
            test_case: Eval test case with mock_responses
        """
        self.mock_responses = test_case.input.mock_responses.get("warranty_api", {})

    async def check_warranty(self, serial_number: str) -> Dict[str, Any]:
        """Return mock warranty data.

        Args:
            serial_number: Serial number to check

        Returns:
            Mock warranty data from test case
        """
        logger.debug(f"Mock: Checking warranty for {serial_number}")
        return self.mock_responses

    async def test_connection(self) -> None:
        """Test connection (no-op for mock)."""
        pass

    async def close(self) -> None:
        """Close connection (no-op for mock)."""
        pass


class MockTicketingClient:
    """Mock Ticketing MCP client for eval."""

    def __init__(self):
        """Initialize mock ticketing client."""
        self.created_tickets: List[Dict[str, Any]] = []

    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, str]:
        """Capture ticket data (don't actually create).

        Args:
            ticket_data: Ticket data to create

        Returns:
            Mock ticket ID
        """
        ticket_id = f"MOCK-TICKET-{len(self.created_tickets) + 1:03d}"
        ticket = {"ticket_id": ticket_id, "data": ticket_data}
        self.created_tickets.append(ticket)
        logger.debug(f"Mock: Ticket created: {ticket_id}")
        return {"ticket_id": ticket_id}

    async def test_connection(self) -> None:
        """Test connection (no-op for mock)."""
        pass

    async def close(self) -> None:
        """Close connection (no-op for mock)."""
        pass


def create_mock_clients(test_case: EvalTestCase) -> Dict[str, Any]:
    """
    Create mock clients for eval execution.

    Args:
        test_case: Eval test case

    Returns:
        Dict with mock client instances
    """
    logger.info("Using mocked integrations for eval")
    return {
        "gmail": MockGmailClient(test_case),
        "warranty": MockWarrantyAPIClient(test_case),
        "ticketing": MockTicketingClient(),
    }


class MockFunctionDispatcher:
    """Mock FunctionDispatcher for eval with pre-configured responses.

    Uses mock_function_responses from test case to return predetermined
    results for function calls, while tracking all calls for validation.
    """

    def __init__(self, mock_function_responses: Optional[Dict[str, Dict]] = None):
        """Initialize mock dispatcher.

        Args:
            mock_function_responses: Dict mapping function names to their mock responses.
                Example: {"check_warranty": {"status": "valid", "expiry": "2025-12-31"}}
        """
        self._mock_responses = mock_function_responses or {}
        self._function_calls: List[ActualFunctionCall] = []

    async def execute(
        self,
        function_name: str,
        arguments: Dict[str, Any]
    ) -> FunctionCall:
        """Execute a function call with mock response.

        Args:
            function_name: Name of function to call
            arguments: Function arguments

        Returns:
            FunctionCall with mock result
        """
        start_time = time.time()

        logger.debug(
            f"Mock dispatcher: {function_name}",
            extra={"function": function_name, "arguments": arguments}
        )

        # Get mock response or default empty dict
        mock_result = self._mock_responses.get(function_name, {})
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Track for validation
        actual_call = ActualFunctionCall(
            function_name=function_name,
            arguments=arguments,
            result=mock_result,
            success=True,
            execution_time_ms=execution_time_ms
        )
        self._function_calls.append(actual_call)

        return FunctionCall(
            function_name=function_name,
            arguments=arguments,
            result=mock_result,
            execution_time_ms=execution_time_ms,
            success=True
        )

    def get_function_calls(self) -> List[ActualFunctionCall]:
        """Get all recorded function calls.

        Returns:
            List of ActualFunctionCall records
        """
        return self._function_calls.copy()

    def get_available_functions(self) -> List[str]:
        """Get list of available functions.

        Returns:
            List of function names with mock responses configured
        """
        return list(self._mock_responses.keys())


def create_mock_function_dispatcher(
    test_case: EvalTestCase
) -> MockFunctionDispatcher:
    """Create mock function dispatcher from test case.

    Args:
        test_case: Eval test case with mock_function_responses

    Returns:
        Configured MockFunctionDispatcher
    """
    mock_responses = test_case.input.mock_function_responses or {}
    logger.info(
        "Created mock function dispatcher",
        extra={"functions": list(mock_responses.keys())}
    )
    return MockFunctionDispatcher(mock_responses)
