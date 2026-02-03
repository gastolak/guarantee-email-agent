"""Mock framework for tools and LLM clients in eval."""

import logging
import time
from typing import Dict, List, Any, Optional

from guarantee_email_agent.eval.models import EvalTestCase, ActualFunctionCall
from guarantee_email_agent.llm.function_calling import FunctionCall

logger = logging.getLogger(__name__)


class MockGmailTool:
    """Mock Gmail tool for eval."""

    def __init__(self, test_case: EvalTestCase):
        """Initialize with test case data.

        Args:
            test_case: Eval test case with input email
        """
        self.test_case = test_case
        self.sent_emails: List[Dict[str, Any]] = []

    async def fetch_unread_emails(self) -> List[Dict[str, Any]]:
        """Return email from test case."""
        # Not used in eval (email provided directly)
        return []

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
    ) -> str:
        """Capture sent email (don't actually send).

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            thread_id: Optional thread ID

        Returns:
            Mock message ID
        """
        sent_email = {
            "to": to,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
        }
        self.sent_emails.append(sent_email)
        logger.debug(f"Mock: Email sent to {to}")
        return f"mock-msg-{len(self.sent_emails)}"

    async def mark_as_read(self, message_id: str) -> None:
        """Mark as read (no-op for mock)."""
        pass

    async def close(self) -> None:
        """Close connection (no-op for mock)."""
        pass


class MockCrmAbacusTool:
    """Mock CRM Abacus tool for eval (combines warranty + ticketing)."""

    def __init__(self, test_case: EvalTestCase):
        """Initialize with mock responses from test case.

        Args:
            test_case: Eval test case with mock_responses
        """
        self.test_case = test_case
        # Support both legacy and new format
        if test_case.input.mock_function_responses:
            self.mock_responses = test_case.input.mock_function_responses
        else:
            # Legacy format mapping
            self.mock_responses = {
                "check_warranty": test_case.input.mock_responses.get("warranty_api", {}),
                "create_ticket": test_case.input.mock_responses.get("ticketing_system", {})
            }
        self.created_tickets: List[Dict[str, Any]] = []
        self.history_entries: List[Dict[str, Any]] = []

    async def check_warranty(self, serial_number: str) -> Dict[str, Any]:
        """Return mock warranty data.

        Args:
            serial_number: Serial number to check

        Returns:
            Mock warranty data from test case
        """
        logger.debug(f"Mock: Checking warranty for {serial_number}")
        return self.mock_responses.get("check_warranty", {})

    async def create_ticket(
        self,
        subject: str,
        description: str,
        customer_email: Optional[str] = None,
        priority: Optional[str] = None
    ) -> str:
        """Capture ticket creation (don't actually create).

        Args:
            subject: Ticket subject
            description: Ticket description
            customer_email: Customer email (optional)
            priority: Priority level (optional)

        Returns:
            Mock ticket ID from test case or generated
        """
        ticket = {
            "subject": subject,
            "description": description,
            "customer_email": customer_email,
            "priority": priority
        }
        self.created_tickets.append(ticket)

        # Return mock ticket_id from test case if available
        mock_response = self.mock_responses.get("create_ticket", {})
        if "ticket_id" in mock_response:
            ticket_id = mock_response["ticket_id"]
            logger.debug(f"Mock: Created ticket {ticket_id} (from mock_responses)")
        else:
            ticket_id = f"TICKET-{len(self.created_tickets)}"
            logger.debug(f"Mock: Created ticket {ticket_id} (generated)")
        return ticket_id

    async def add_ticket_info(self, zadanie_id: int, info_text: str) -> None:
        """Add info to ticket (no-op for mock)."""
        pass

    async def append_ticket_history(self, ticket_id: str, sender: str, message: str) -> Dict[str, str]:
        """Capture conversation history entry.

        Args:
            ticket_id: Ticket ID (positive or negative)
            sender: Message sender ("CLIENT" or "AGENT")
            message: Message content

        Returns:
            Mock status confirmation
        """
        history_entry = {
            "ticket_id": ticket_id,
            "sender": sender,
            "message": message
        }
        self.history_entries.append(history_entry)
        logger.debug(f"Mock: Stored history entry for ticket {ticket_id} - sender: {sender}")
        return {"status": "stored", "ticket_id": ticket_id, "sender": sender}

    async def get_task_info(self, zadanie_id: int) -> Dict[str, Any]:
        """Get task info (mock)."""
        return {"zadanie_id": zadanie_id, "temat": "Mock Task"}

    async def check_agent_disabled(self, zadanie_id: int) -> bool:
        """Check if agent disabled via mock response.

        Args:
            zadanie_id: Task ID to check

        Returns:
            Mock agent disabled status from test case
        """
        mock_response = self.mock_responses.get("check_agent_disabled", {})
        agent_disabled = mock_response.get("posiada_ceche", False)
        logger.debug(f"Mock: check_agent_disabled({zadanie_id}) -> {agent_disabled}")
        return agent_disabled

    async def close(self) -> None:
        """Close connection (no-op for mock)."""
        pass


# Legacy aliases for backward compatibility
MockGmailClient = MockGmailTool
MockWarrantyAPIClient = MockCrmAbacusTool


class MockTicketingSystemClient:
    """Legacy mock - redirects to MockCrmAbacusTool."""

    def __init__(self, test_case: EvalTestCase):
        self._tool = MockCrmAbacusTool(test_case)
        self.created_tickets = self._tool.created_tickets

    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create ticket with legacy interface."""
        ticket_id = await self._tool.create_ticket(
            subject=ticket_data.get("subject", ""),
            description=ticket_data.get("description", ""),
            customer_email=ticket_data.get("customer_email"),
            priority=ticket_data.get("priority")
        )
        return {"ticket_id": ticket_id, "status": "created"}

    async def close(self) -> None:
        await self._tool.close()

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
    Create mock tools for eval execution.

    Args:
        test_case: Eval test case

    Returns:
        Dict with mock tool instances (gmail_tool, crm_abacus_tool)
    """
    logger.info("Using mocked tools for eval")
    crm_tool = MockCrmAbacusTool(test_case)
    return {
        "gmail_tool": MockGmailTool(test_case),
        "crm_abacus_tool": crm_tool,
        # Legacy keys for backward compatibility
        "gmail": MockGmailClient(test_case),
        "warranty": crm_tool,
        "ticketing": MockTicketingSystemClient(test_case),
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
