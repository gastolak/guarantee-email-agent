"""Unit tests for function calling data models."""

import pytest

from guarantee_email_agent.llm.function_calling import (
    FunctionDefinition,
    FunctionCall,
    FunctionCallingResult,
)


class TestFunctionDefinition:
    """Tests for FunctionDefinition model."""

    def test_function_definition_creation(self):
        """Test creating a FunctionDefinition."""
        func_def = FunctionDefinition(
            name="check_warranty",
            description="Check warranty status for a product serial number",
            parameters={
                "type": "object",
                "properties": {
                    "serial_number": {
                        "type": "string",
                        "description": "Product serial number to check"
                    }
                },
                "required": ["serial_number"]
            }
        )

        assert func_def.name == "check_warranty"
        assert func_def.description == "Check warranty status for a product serial number"
        assert func_def.parameters["type"] == "object"
        assert "serial_number" in func_def.parameters["properties"]

    def test_function_definition_is_frozen(self):
        """Test that FunctionDefinition is immutable."""
        func_def = FunctionDefinition(
            name="test",
            description="test function",
            parameters={"type": "object"}
        )

        with pytest.raises(AttributeError):
            func_def.name = "modified"

    def test_to_gemini_tool_format(self):
        """Test conversion to Gemini Tool format."""
        func_def = FunctionDefinition(
            name="send_email",
            description="Send email response to customer",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body"}
                },
                "required": ["to", "subject", "body"]
            }
        )

        gemini_tool = func_def.to_gemini_tool()

        assert gemini_tool["name"] == "send_email"
        assert gemini_tool["description"] == "Send email response to customer"
        assert gemini_tool["parameters"]["type"] == "object"
        assert "to" in gemini_tool["parameters"]["properties"]
        assert "subject" in gemini_tool["parameters"]["properties"]
        assert "body" in gemini_tool["parameters"]["properties"]

    def test_to_gemini_tool_minimal_params(self):
        """Test to_gemini_tool with minimal parameters."""
        func_def = FunctionDefinition(
            name="get_status",
            description="Get current status",
            parameters={"type": "object", "properties": {}}
        )

        gemini_tool = func_def.to_gemini_tool()

        assert gemini_tool["name"] == "get_status"
        assert gemini_tool["parameters"]["properties"] == {}


class TestFunctionCall:
    """Tests for FunctionCall model."""

    def test_function_call_success(self):
        """Test creating a successful function call record."""
        func_call = FunctionCall(
            function_name="check_warranty",
            arguments={"serial_number": "SN12345"},
            result={"status": "valid", "expiration_date": "2025-12-31"},
            execution_time_ms=150,
            success=True
        )

        assert func_call.function_name == "check_warranty"
        assert func_call.arguments["serial_number"] == "SN12345"
        assert func_call.result["status"] == "valid"
        assert func_call.execution_time_ms == 150
        assert func_call.success is True
        assert func_call.error_message is None

    def test_function_call_failure(self):
        """Test creating a failed function call record."""
        func_call = FunctionCall(
            function_name="create_ticket",
            arguments={"serial_number": "SN12345", "customer_email": "test@example.com"},
            result={},
            execution_time_ms=500,
            success=False,
            error_message="Ticketing API connection failed"
        )

        assert func_call.function_name == "create_ticket"
        assert func_call.success is False
        assert func_call.error_message == "Ticketing API connection failed"
        assert func_call.result == {}

    def test_function_call_is_frozen(self):
        """Test that FunctionCall is immutable."""
        func_call = FunctionCall(
            function_name="test",
            arguments={},
            result={},
            execution_time_ms=100,
            success=True
        )

        with pytest.raises(AttributeError):
            func_call.success = False

    def test_function_call_with_complex_result(self):
        """Test function call with nested result structure."""
        func_call = FunctionCall(
            function_name="send_email",
            arguments={
                "to": "customer@example.com",
                "subject": "Re: Warranty Request",
                "body": "Your warranty is valid."
            },
            result={
                "message_id": "msg-abc123",
                "status": "sent",
                "metadata": {
                    "timestamp": "2026-01-19T10:00:00Z",
                    "retries": 0
                }
            },
            execution_time_ms=250,
            success=True
        )

        assert func_call.result["message_id"] == "msg-abc123"
        assert func_call.result["metadata"]["retries"] == 0


class TestFunctionCallingResult:
    """Tests for FunctionCallingResult model."""

    def test_function_calling_result_basic(self):
        """Test creating a basic FunctionCallingResult."""
        result = FunctionCallingResult(
            response_text="Email sent successfully.",
            total_turns=3,
            email_sent=True
        )

        assert result.response_text == "Email sent successfully."
        assert result.function_calls == []
        assert result.total_turns == 3
        assert result.email_sent is True

    def test_function_calling_result_with_calls(self):
        """Test FunctionCallingResult with function calls."""
        calls = [
            FunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN12345"},
                result={"status": "valid"},
                execution_time_ms=100,
                success=True
            ),
            FunctionCall(
                function_name="send_email",
                arguments={"to": "test@example.com", "subject": "Re:", "body": "Valid."},
                result={"message_id": "msg-123"},
                execution_time_ms=200,
                success=True
            )
        ]

        result = FunctionCallingResult(
            response_text="Done",
            function_calls=calls,
            total_turns=3,
            email_sent=True
        )

        assert len(result.function_calls) == 2
        assert result.function_calls[0].function_name == "check_warranty"
        assert result.function_calls[1].function_name == "send_email"

    def test_get_function_call_found(self):
        """Test get_function_call returns matching call."""
        calls = [
            FunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN12345"},
                result={"status": "valid"},
                execution_time_ms=100,
                success=True
            ),
            FunctionCall(
                function_name="send_email",
                arguments={"to": "test@example.com"},
                result={"message_id": "msg-123"},
                execution_time_ms=200,
                success=True
            )
        ]

        result = FunctionCallingResult(response_text="Done", function_calls=calls)

        warranty_call = result.get_function_call("check_warranty")
        assert warranty_call is not None
        assert warranty_call.arguments["serial_number"] == "SN12345"

    def test_get_function_call_not_found(self):
        """Test get_function_call returns None when not found."""
        result = FunctionCallingResult(
            response_text="Done",
            function_calls=[
                FunctionCall(
                    function_name="send_email",
                    arguments={},
                    result={},
                    execution_time_ms=100,
                    success=True
                )
            ]
        )

        assert result.get_function_call("check_warranty") is None

    def test_get_all_function_calls(self):
        """Test get_all_function_calls returns all matching calls."""
        calls = [
            FunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN001"},
                result={"status": "valid"},
                execution_time_ms=100,
                success=True
            ),
            FunctionCall(
                function_name="check_warranty",
                arguments={"serial_number": "SN002"},
                result={"status": "expired"},
                execution_time_ms=100,
                success=True
            ),
            FunctionCall(
                function_name="send_email",
                arguments={},
                result={},
                execution_time_ms=100,
                success=True
            )
        ]

        result = FunctionCallingResult(response_text="Done", function_calls=calls)

        warranty_calls = result.get_all_function_calls("check_warranty")
        assert len(warranty_calls) == 2
        assert warranty_calls[0].arguments["serial_number"] == "SN001"
        assert warranty_calls[1].arguments["serial_number"] == "SN002"

    def test_get_all_function_calls_empty(self):
        """Test get_all_function_calls returns empty list when none found."""
        result = FunctionCallingResult(response_text="Done", function_calls=[])

        assert result.get_all_function_calls("check_warranty") == []

    def test_has_function_call_true(self):
        """Test has_function_call returns True when present."""
        result = FunctionCallingResult(
            response_text="Done",
            function_calls=[
                FunctionCall(
                    function_name="send_email",
                    arguments={},
                    result={},
                    execution_time_ms=100,
                    success=True
                )
            ]
        )

        assert result.has_function_call("send_email") is True

    def test_has_function_call_false(self):
        """Test has_function_call returns False when not present."""
        result = FunctionCallingResult(response_text="Done", function_calls=[])

        assert result.has_function_call("send_email") is False

    def test_default_values(self):
        """Test FunctionCallingResult default values."""
        result = FunctionCallingResult(response_text="Response only")

        assert result.function_calls == []
        assert result.total_turns == 1
        assert result.email_sent is False
