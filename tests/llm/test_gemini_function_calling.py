"""Integration tests for Gemini function calling.

These tests use mocks to simulate Gemini API responses without
requiring a real API key or network calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from guarantee_email_agent.llm.function_calling import (
    FunctionDefinition,
    FunctionCall,
    FunctionCallingResult,
)
from guarantee_email_agent.llm.function_dispatcher import FunctionDispatcher
from guarantee_email_agent.config.schema import LLMConfig
from guarantee_email_agent.utils.errors import LLMError


@pytest.fixture
def llm_config():
    """Create LLM configuration for Gemini."""
    return LLMConfig(
        provider="gemini",
        model="gemini-2.0-flash-exp",
        temperature=0,
        max_tokens=8192,
        timeout_seconds=15
    )


@pytest.fixture
def check_warranty_function():
    """Create check_warranty function definition."""
    return FunctionDefinition(
        name="check_warranty",
        description="Check warranty status for a serial number",
        parameters={
            "type": "object",
            "properties": {
                "serial_number": {
                    "type": "string",
                    "description": "Product serial number"
                }
            },
            "required": ["serial_number"]
        }
    )


@pytest.fixture
def send_email_function():
    """Create send_email function definition."""
    return FunctionDefinition(
        name="send_email",
        description="Send email to customer",
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


@pytest.fixture
def mock_dispatcher():
    """Create mock function dispatcher."""
    dispatcher = MagicMock(spec=FunctionDispatcher)

    # Mock check_warranty
    async def mock_check_warranty(function_name, arguments):
        return FunctionCall(
            function_name="check_warranty",
            arguments=arguments,
            result={"status": "valid", "expiration_date": "2025-12-31"},
            execution_time_ms=100,
            success=True
        )

    # Mock send_email
    async def mock_send_email(function_name, arguments):
        return FunctionCall(
            function_name="send_email",
            arguments=arguments,
            result={"message_id": "msg-123", "status": "sent"},
            execution_time_ms=200,
            success=True
        )

    async def execute(function_name, arguments):
        if function_name == "check_warranty":
            return await mock_check_warranty(function_name, arguments)
        elif function_name == "send_email":
            return await mock_send_email(function_name, arguments)
        else:
            return FunctionCall(
                function_name=function_name,
                arguments=arguments,
                result={},
                execution_time_ms=0,
                success=False,
                error_message=f"Unknown function: {function_name}"
            )

    dispatcher.execute = AsyncMock(side_effect=execute)
    return dispatcher


class TestGeminiProviderFunctionCalling:
    """Tests for GeminiProvider.create_message_with_functions."""

    @pytest.mark.asyncio
    async def test_function_calling_with_mocked_gemini(
        self,
        llm_config,
        check_warranty_function,
        send_email_function,
        mock_dispatcher
    ):
        """Test function calling with mocked Gemini API."""
        # This test verifies the function calling logic works correctly
        # by mocking the Gemini API responses

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                # Setup mock chat
                mock_chat = MagicMock()
                mock_model_instance = MagicMock()
                mock_model_instance.start_chat.return_value = mock_chat
                mock_model_class.return_value = mock_model_instance

                # Create mock responses for multi-turn conversation
                # Turn 1: LLM calls check_warranty
                mock_fc_response_1 = MagicMock()
                mock_fc_part_1 = MagicMock()
                mock_fc_part_1.function_call.name = "check_warranty"
                mock_fc_part_1.function_call.args = {"serial_number": "SN12345"}
                mock_fc_response_1.candidates = [MagicMock()]
                mock_fc_response_1.candidates[0].content.parts = [mock_fc_part_1]

                # Turn 2: LLM calls send_email
                mock_fc_response_2 = MagicMock()
                mock_fc_part_2 = MagicMock()
                mock_fc_part_2.function_call.name = "send_email"
                mock_fc_part_2.function_call.args = {
                    "to": "customer@test.com",
                    "subject": "Re: Warranty",
                    "body": "Your warranty is valid."
                }
                mock_fc_response_2.candidates = [MagicMock()]
                mock_fc_response_2.candidates[0].content.parts = [mock_fc_part_2]

                # Turn 3: LLM returns final text
                mock_final_response = MagicMock()
                mock_final_part = MagicMock()
                mock_final_part.text = "Email sent successfully."
                # Set function_call.name to empty to indicate no function call
                mock_final_part.function_call = MagicMock()
                mock_final_part.function_call.name = ""
                mock_final_response.candidates = [MagicMock()]
                mock_final_response.candidates[0].content.parts = [mock_final_part]

                # Setup send_message to return responses in sequence
                mock_chat.send_message.side_effect = [
                    mock_fc_response_1,
                    mock_fc_response_2,
                    mock_final_response
                ]

                # Create provider
                from guarantee_email_agent.llm.provider import GeminiProvider
                provider = GeminiProvider(llm_config, "test-api-key")

                # Execute
                result = await provider.create_message_with_functions(
                    system_prompt="You are a warranty agent.",
                    user_prompt="Check warranty for SN12345 and send response.",
                    available_functions=[check_warranty_function, send_email_function],
                    function_dispatcher=mock_dispatcher
                )

                # Verify result
                assert isinstance(result, FunctionCallingResult)
                assert result.response_text == "Email sent successfully."
                assert len(result.function_calls) == 2
                assert result.function_calls[0].function_name == "check_warranty"
                assert result.function_calls[1].function_name == "send_email"
                assert result.email_sent is True
                assert result.total_turns == 3

    @pytest.mark.asyncio
    async def test_function_calling_no_functions_called(
        self,
        llm_config,
        send_email_function,
        mock_dispatcher
    ):
        """Test when LLM doesn't call any functions."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_chat = MagicMock()
                mock_model_instance = MagicMock()
                mock_model_instance.start_chat.return_value = mock_chat
                mock_model_class.return_value = mock_model_instance

                # LLM responds with text directly (no function call)
                mock_response = MagicMock()
                mock_part = MagicMock()
                mock_part.text = "I need more information."
                mock_part.function_call = MagicMock()
                mock_part.function_call.name = ""
                mock_response.candidates = [MagicMock()]
                mock_response.candidates[0].content.parts = [mock_part]

                mock_chat.send_message.return_value = mock_response

                from guarantee_email_agent.llm.provider import GeminiProvider
                provider = GeminiProvider(llm_config, "test-api-key")

                result = await provider.create_message_with_functions(
                    system_prompt="You are a warranty agent.",
                    user_prompt="Hello",
                    available_functions=[send_email_function],
                    function_dispatcher=mock_dispatcher
                )

                assert result.response_text == "I need more information."
                assert len(result.function_calls) == 0
                assert result.email_sent is False
                assert result.total_turns == 1

    @pytest.mark.asyncio
    async def test_function_calling_max_iterations(
        self,
        llm_config,
        check_warranty_function,
        mock_dispatcher
    ):
        """Test that function calling stops at max iterations."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_chat = MagicMock()
                mock_model_instance = MagicMock()
                mock_model_instance.start_chat.return_value = mock_chat
                mock_model_class.return_value = mock_model_instance

                # Create response that always calls function (infinite loop scenario)
                def create_fc_response():
                    mock_fc_response = MagicMock()
                    mock_fc_part = MagicMock()
                    mock_fc_part.function_call.name = "check_warranty"
                    mock_fc_part.function_call.args = {"serial_number": "SN12345"}
                    # Set text to None to indicate no text response
                    mock_fc_part.text = None
                    mock_fc_response.candidates = [MagicMock()]
                    mock_fc_response.candidates[0].content.parts = [mock_fc_part]
                    return mock_fc_response

                # Always return function call response
                mock_chat.send_message.side_effect = [create_fc_response() for _ in range(15)]

                from guarantee_email_agent.llm.provider import GeminiProvider
                provider = GeminiProvider(llm_config, "test-api-key")

                result = await provider.create_message_with_functions(
                    system_prompt="You are a warranty agent.",
                    user_prompt="Check warranty repeatedly",
                    available_functions=[check_warranty_function],
                    function_dispatcher=mock_dispatcher
                )

                # Should stop at max iterations (10)
                # Loop condition is total_turns < 10, so after initial send we can do 9 more
                # Initial turn 1, then 9 function call turns = 10 total
                assert result.total_turns == 10
                # We get 9 function calls (turns 2-10 each have a function call)
                assert len(result.function_calls) == 9
                # Response text is empty since we hit max iterations
                assert result.response_text == ""

    @pytest.mark.asyncio
    async def test_function_calling_handles_error(
        self,
        llm_config,
        check_warranty_function
    ):
        """Test error handling during function calling."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model_instance = MagicMock()
                mock_model_instance.start_chat.side_effect = Exception("API Error")
                mock_model_class.return_value = mock_model_instance

                from guarantee_email_agent.llm.provider import GeminiProvider
                provider = GeminiProvider(llm_config, "test-api-key")

                mock_dispatcher = MagicMock()

                with pytest.raises(LLMError) as exc_info:
                    await provider.create_message_with_functions(
                        system_prompt="Test",
                        user_prompt="Test",
                        available_functions=[check_warranty_function],
                        function_dispatcher=mock_dispatcher
                    )

                assert "function calling error" in exc_info.value.message.lower()
                assert exc_info.value.code == "gemini_function_calling_error"


class TestTypeMapping:
    """Tests for JSON type to Proto type mapping."""

    def test_map_json_type_to_proto(self, llm_config):
        """Test JSON type mapping."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                from guarantee_email_agent.llm.provider import GeminiProvider
                import google.generativeai as genai

                provider = GeminiProvider(llm_config, "test-api-key")

                # Test mappings
                assert provider._map_json_type_to_proto("string") == genai.protos.Type.STRING
                assert provider._map_json_type_to_proto("number") == genai.protos.Type.NUMBER
                assert provider._map_json_type_to_proto("integer") == genai.protos.Type.INTEGER
                assert provider._map_json_type_to_proto("boolean") == genai.protos.Type.BOOLEAN
                assert provider._map_json_type_to_proto("array") == genai.protos.Type.ARRAY
                assert provider._map_json_type_to_proto("object") == genai.protos.Type.OBJECT

                # Unknown type defaults to STRING
                assert provider._map_json_type_to_proto("unknown") == genai.protos.Type.STRING
