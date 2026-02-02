"""Unit tests for function dispatcher."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from guarantee_email_agent.llm.function_dispatcher import FunctionDispatcher
from guarantee_email_agent.llm.function_calling import FunctionCall


@pytest.fixture
def mock_crm_abacus_tool():
    """Create mock CRM Abacus tool (combines warranty + ticketing)."""
    tool = MagicMock()
    tool.check_warranty = AsyncMock(return_value={
        "serial_number": "SN12345",
        "status": "valid",
        "expiration_date": "2025-12-31"
    })
    tool.create_ticket = AsyncMock(return_value={
        "ticket_id": 12345,
        "status": "created",
        "created_at": "2026-01-19T10:00:00Z"
    })
    return tool


@pytest.fixture
def mock_gmail_tool():
    """Create mock Gmail tool."""
    tool = MagicMock()
    tool.send_email = AsyncMock(return_value="msg-abc123")
    return tool


@pytest.fixture
def dispatcher(mock_crm_abacus_tool, mock_gmail_tool):
    """Create dispatcher with all mock tools."""
    return FunctionDispatcher(
        crm_abacus_tool=mock_crm_abacus_tool,
        gmail_tool=mock_gmail_tool
    )


class TestFunctionDispatcherInit:
    """Tests for FunctionDispatcher initialization."""

    def test_init_with_all_tools(self, mock_crm_abacus_tool, mock_gmail_tool):
        """Test initialization with all tools."""
        dispatcher = FunctionDispatcher(
            crm_abacus_tool=mock_crm_abacus_tool,
            gmail_tool=mock_gmail_tool
        )

        assert dispatcher._crm_abacus_tool is mock_crm_abacus_tool
        assert dispatcher._gmail_tool is mock_gmail_tool

    def test_init_with_no_tools(self):
        """Test initialization with no tools."""
        dispatcher = FunctionDispatcher()

        assert dispatcher._crm_abacus_tool is None
        assert dispatcher._gmail_tool is None

    def test_init_with_partial_tools(self, mock_gmail_tool):
        """Test initialization with only some tools."""
        dispatcher = FunctionDispatcher(gmail_tool=mock_gmail_tool)

        assert dispatcher._crm_abacus_tool is None
        assert dispatcher._gmail_tool is mock_gmail_tool


class TestCheckWarrantyExecution:
    """Tests for check_warranty function execution."""

    @pytest.mark.asyncio
    async def test_check_warranty_success(self, dispatcher, mock_crm_abacus_tool):
        """Test successful warranty check."""
        result = await dispatcher.execute(
            function_name="check_warranty",
            arguments={"serial_number": "SN12345"}
        )

        assert isinstance(result, FunctionCall)
        assert result.function_name == "check_warranty"
        assert result.arguments == {"serial_number": "SN12345"}
        assert result.success is True
        assert result.result["status"] == "valid"
        assert result.result["serial_number"] == "SN12345"
        assert result.execution_time_ms >= 0
        assert result.error_message is None

        mock_crm_abacus_tool.check_warranty.assert_called_once_with("SN12345")

    @pytest.mark.asyncio
    async def test_check_warranty_no_client(self):
        """Test warranty check fails without client."""
        dispatcher = FunctionDispatcher()

        result = await dispatcher.execute(
            function_name="check_warranty",
            arguments={"serial_number": "SN12345"}
        )

        assert result.success is False
        assert "CRM Abacus tool not configured" in result.error_message

    @pytest.mark.asyncio
    async def test_check_warranty_missing_serial_number(self, dispatcher):
        """Test warranty check fails without serial number."""
        result = await dispatcher.execute(
            function_name="check_warranty",
            arguments={}
        )

        assert result.success is False
        assert "serial_number" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_check_warranty_client_error(self, mock_crm_abacus_tool):
        """Test warranty check handles client error."""
        mock_crm_abacus_tool.check_warranty = AsyncMock(
            side_effect=ConnectionError("Connection failed")
        )
        dispatcher = FunctionDispatcher(crm_abacus_tool=mock_crm_abacus_tool)

        result = await dispatcher.execute(
            function_name="check_warranty",
            arguments={"serial_number": "SN12345"}
        )

        assert result.success is False
        assert "Connection failed" in result.error_message


class TestCreateTicketExecution:
    """Tests for create_ticket function execution."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, dispatcher, mock_crm_abacus_tool):
        """Test successful ticket creation."""
        ticket_args = {
            "serial_number": "SN12345",
            "customer_email": "customer@example.com",
            "priority": "normal"
        }

        result = await dispatcher.execute(
            function_name="create_ticket",
            arguments=ticket_args
        )

        assert result.success is True
        assert result.result["ticket_id"] == 12345
        assert result.result["status"] == "created"

        mock_crm_abacus_tool.create_ticket.assert_called_once_with(ticket_args)

    @pytest.mark.asyncio
    async def test_create_ticket_no_client(self):
        """Test ticket creation fails without client."""
        dispatcher = FunctionDispatcher()

        result = await dispatcher.execute(
            function_name="create_ticket",
            arguments={"serial_number": "SN12345"}
        )

        assert result.success is False
        assert "CRM Abacus tool not configured" in result.error_message

    @pytest.mark.asyncio
    async def test_create_ticket_client_error(self, mock_crm_abacus_tool):
        """Test ticket creation handles client error."""
        mock_crm_abacus_tool.create_ticket = AsyncMock(
            side_effect=Exception("API error")
        )
        dispatcher = FunctionDispatcher(crm_abacus_tool=mock_crm_abacus_tool)

        result = await dispatcher.execute(
            function_name="create_ticket",
            arguments={"serial_number": "SN12345"}
        )

        assert result.success is False
        assert "API error" in result.error_message


class TestSendEmailExecution:
    """Tests for send_email function execution."""

    @pytest.mark.asyncio
    async def test_send_email_success(self, dispatcher, mock_gmail_tool):
        """Test successful email send."""
        email_args = {
            "to": "customer@example.com",
            "subject": "Re: Your warranty request",
            "body": "Dear Customer, your warranty is valid."
        }

        result = await dispatcher.execute(
            function_name="send_email",
            arguments=email_args
        )

        assert result.success is True
        assert result.result["message_id"] == "msg-abc123"
        assert result.result["status"] == "sent"

        mock_gmail_tool.send_email.assert_called_once_with(
            to="customer@example.com",
            subject="Re: Your warranty request",
            body="Dear Customer, your warranty is valid.",
            thread_id=None
        )

    @pytest.mark.asyncio
    async def test_send_email_with_thread_id(self, dispatcher, mock_gmail_tool):
        """Test email send with thread ID for reply."""
        email_args = {
            "to": "customer@example.com",
            "subject": "Re: Your warranty request",
            "body": "Thank you for your patience.",
            "thread_id": "thread-xyz789"
        }

        result = await dispatcher.execute(
            function_name="send_email",
            arguments=email_args
        )

        assert result.success is True
        mock_gmail_tool.send_email.assert_called_once_with(
            to="customer@example.com",
            subject="Re: Your warranty request",
            body="Thank you for your patience.",
            thread_id="thread-xyz789"
        )

    @pytest.mark.asyncio
    async def test_send_email_no_client(self):
        """Test email send fails without client."""
        dispatcher = FunctionDispatcher()

        result = await dispatcher.execute(
            function_name="send_email",
            arguments={"to": "test@example.com", "subject": "Test", "body": "Test"}
        )

        assert result.success is False
        assert "Gmail tool not configured" in result.error_message

    @pytest.mark.asyncio
    async def test_send_email_missing_to(self, dispatcher):
        """Test email send fails without 'to' argument."""
        result = await dispatcher.execute(
            function_name="send_email",
            arguments={"subject": "Test", "body": "Test"}
        )

        assert result.success is False
        assert "to" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_send_email_missing_subject(self, dispatcher):
        """Test email send fails without 'subject' argument."""
        result = await dispatcher.execute(
            function_name="send_email",
            arguments={"to": "test@example.com", "body": "Test"}
        )

        assert result.success is False
        assert "subject" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_send_email_missing_body(self, dispatcher):
        """Test email send fails without 'body' argument."""
        result = await dispatcher.execute(
            function_name="send_email",
            arguments={"to": "test@example.com", "subject": "Test"}
        )

        assert result.success is False
        assert "body" in result.error_message.lower()


class TestUnknownFunction:
    """Tests for unknown function handling."""

    @pytest.mark.asyncio
    async def test_unknown_function_raises_error(self, dispatcher):
        """Test that unknown function raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await dispatcher.execute(
                function_name="unknown_function",
                arguments={}
            )

        assert "Unknown function: unknown_function" in str(exc_info.value)


class TestGetAvailableFunctions:
    """Tests for get_available_functions method."""

    def test_all_functions_available(self, mock_crm_abacus_tool, mock_gmail_tool):
        """Test all functions available when all tools configured."""
        dispatcher = FunctionDispatcher(
            crm_abacus_tool=mock_crm_abacus_tool,
            gmail_tool=mock_gmail_tool
        )

        available = dispatcher.get_available_functions()

        assert "check_warranty" in available
        assert "create_ticket" in available
        assert "send_email" in available
        assert len(available) == 3

    def test_no_functions_available(self):
        """Test no functions when no clients configured."""
        dispatcher = FunctionDispatcher()

        available = dispatcher.get_available_functions()

        assert available == []

    def test_partial_functions_available(self, mock_gmail_tool):
        """Test only configured functions available."""
        dispatcher = FunctionDispatcher(gmail_tool=mock_gmail_tool)

        available = dispatcher.get_available_functions()

        assert available == ["send_email"]


class TestExecutionTiming:
    """Tests for execution timing tracking."""

    @pytest.mark.asyncio
    async def test_execution_time_tracked(self, dispatcher):
        """Test that execution time is properly tracked."""
        result = await dispatcher.execute(
            function_name="check_warranty",
            arguments={"serial_number": "SN12345"}
        )

        assert result.execution_time_ms >= 0
        assert isinstance(result.execution_time_ms, int)

    @pytest.mark.asyncio
    async def test_execution_time_on_error(self):
        """Test execution time tracked even on error."""
        dispatcher = FunctionDispatcher()

        result = await dispatcher.execute(
            function_name="send_email",
            arguments={"to": "test@test.com", "subject": "Test", "body": "Test"}
        )

        assert result.success is False
        assert result.execution_time_ms >= 0
