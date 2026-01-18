"""Tests for graceful degradation handler."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from guarantee_email_agent.email.graceful_handler import GracefulDegradationHandler
from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.email.processor_models import ProcessingResult
from guarantee_email_agent.config.schema import AgentConfig, LoggingConfig, MCPConfig, MCPConnectionConfig, InstructionsConfig, EvalConfig, SecretsConfig


@pytest.fixture
def mock_config():
    """Create mock agent config."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="gmail://test"),
            warranty_api=MCPConnectionConfig(connection_string="warranty://test"),
            ticketing_system=MCPConnectionConfig(connection_string="ticket://test"),
        ),
        instructions=InstructionsConfig(
            main="main.md",
            scenarios=("test",),
            scenarios_dir="scenarios",
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="gmail-key",
            warranty_api_key="warranty-key",
            ticketing_api_key="ticket-key",
        ),
    )


@pytest.fixture
def mock_response_generator():
    """Create mock response generator."""
    generator = Mock()
    generator.generate_response = AsyncMock(return_value="Graceful response text")
    return generator


@pytest.fixture
def sample_email():
    """Create sample email for testing."""
    return EmailMessage(
        subject="Billing question",
        body="How do I update my payment method?",
        from_address="customer@example.com",
        received_timestamp=datetime.now(),
        message_id="msg-123"
    )


@pytest.mark.asyncio
async def test_handler_initialization(mock_config, mock_response_generator):
    """Test graceful degradation handler initializes correctly."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    assert handler.config == mock_config
    assert handler.response_generator == mock_response_generator


@pytest.mark.asyncio
async def test_handle_out_of_scope_success(mock_config, mock_response_generator, sample_email):
    """Test out-of-scope email handling."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_out_of_scope(sample_email, "billing_inquiry")

    assert isinstance(result, ProcessingResult)
    assert result.success is True  # Gracefully handled
    assert result.email_id == "msg-123"
    assert result.scenario_used == "graceful-degradation"
    assert result.serial_number is None
    assert result.warranty_status is None
    assert result.ticket_created is False
    assert result.failed_step is None

    # Verify response generator called with graceful-degradation scenario
    mock_response_generator.generate_response.assert_called_once()
    call_args = mock_response_generator.generate_response.call_args
    assert call_args.kwargs["scenario_name"] == "graceful-degradation"


@pytest.mark.asyncio
async def test_handle_out_of_scope_generator_failure(mock_config, mock_response_generator, sample_email):
    """Test out-of-scope handling when response generator fails."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    # Simulate response generator failure
    mock_response_generator.generate_response = AsyncMock(side_effect=Exception("LLM error"))

    result = await handler.handle_out_of_scope(sample_email, "billing_inquiry")

    # Should use fallback response (never crash)
    assert isinstance(result, ProcessingResult)
    assert result.success is False  # Fallback = failure
    assert result.scenario_used == "fallback"
    assert result.failed_step == "graceful_degradation"


@pytest.mark.asyncio
async def test_handle_missing_info_success(mock_config, mock_response_generator, sample_email):
    """Test missing information handling."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_missing_info(sample_email, ["serial_number"])

    assert result.success is True
    assert result.scenario_used == "missing-info"
    assert result.serial_number is None
    assert result.email_id == "msg-123"

    # Verify response generator called with missing-info scenario
    call_args = mock_response_generator.generate_response.call_args
    assert call_args.kwargs["scenario_name"] == "missing-info"


@pytest.mark.asyncio
async def test_handle_missing_info_multiple_fields(mock_config, mock_response_generator, sample_email):
    """Test missing information with multiple fields."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_missing_info(sample_email, ["serial_number", "purchase_date"])

    assert result.success is True
    assert result.scenario_used == "missing-info"


@pytest.mark.asyncio
async def test_handle_api_failure_success(mock_config, mock_response_generator, sample_email):
    """Test API failure handling."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_api_failure(sample_email, "warranty_api", "Timeout after 10s")

    assert result.success is False  # API failure = failure
    assert result.scenario_used == "graceful-degradation"
    assert result.failed_step == "warranty_api"
    assert "API failure" in result.error_message
    assert "warranty_api" in result.error_message


@pytest.mark.asyncio
async def test_handle_api_failure_llm_timeout(mock_config, mock_response_generator, sample_email):
    """Test LLM timeout handling."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_api_failure(sample_email, "llm", "Request timeout: 15s")

    assert result.success is False
    assert result.failed_step == "llm"
    assert "API failure: llm" in result.error_message


@pytest.mark.asyncio
async def test_handle_edge_case_success(mock_config, mock_response_generator, sample_email):
    """Test edge case handling."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_edge_case(sample_email, "Malformed email structure")

    assert result.success is True  # Gracefully handled
    assert result.scenario_used == "graceful-degradation"
    assert result.failed_step is None


@pytest.mark.asyncio
async def test_handle_edge_case_encoding_issue(mock_config, mock_response_generator):
    """Test edge case with encoding issue."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    # Email with None body
    email = EmailMessage(
        subject="Test",
        body=None,
        from_address="test@example.com",
        received_timestamp=datetime.now(),
        message_id="msg-456"
    )

    result = await handler.handle_edge_case(email, "Encoding error")

    assert result.success is True
    assert result.email_id == "msg-456"


@pytest.mark.asyncio
async def test_handle_ambiguous_success(mock_config, mock_response_generator, sample_email):
    """Test ambiguous scenario handling."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_ambiguous(sample_email, ["valid-warranty", "invalid-warranty"])

    assert result.success is True
    assert result.scenario_used == "graceful-degradation"


@pytest.mark.asyncio
async def test_handle_ambiguous_single_scenario(mock_config, mock_response_generator, sample_email):
    """Test ambiguous handling with single scenario (should still work)."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_ambiguous(sample_email, ["uncertain"])

    assert result.success is True


@pytest.mark.asyncio
async def test_fallback_response_never_crashes(mock_config, mock_response_generator):
    """Test fallback response never raises exceptions."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    email = EmailMessage(
        subject=None,  # None values
        body=None,
        from_address=None,
        received_timestamp=None,
        message_id=None
    )

    # Should not crash even with None values
    result = handler._fallback_response(email, "test_type")

    assert isinstance(result, ProcessingResult)
    assert result.success is False
    assert result.scenario_used == "fallback"
    assert result.failed_step == "graceful_degradation"


@pytest.mark.asyncio
async def test_all_handlers_never_crash_on_exception(mock_config, mock_response_generator, sample_email):
    """Test that all handlers never crash, always return ProcessingResult."""
    # Simulate complete failure of response generator
    mock_response_generator.generate_response = AsyncMock(side_effect=Exception("Total failure"))

    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    # All should return ProcessingResult, never raise
    result1 = await handler.handle_out_of_scope(sample_email, "test")
    assert isinstance(result1, ProcessingResult)

    result2 = await handler.handle_missing_info(sample_email, ["test"])
    assert isinstance(result2, ProcessingResult)

    result3 = await handler.handle_api_failure(sample_email, "test", "error")
    assert isinstance(result3, ProcessingResult)

    result4 = await handler.handle_edge_case(sample_email, "test")
    assert isinstance(result4, ProcessingResult)

    result5 = await handler.handle_ambiguous(sample_email, ["test"])
    assert isinstance(result5, ProcessingResult)


@pytest.mark.asyncio
async def test_response_generator_receives_correct_params(mock_config, mock_response_generator, sample_email):
    """Test that response generator receives correct parameters."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    await handler.handle_out_of_scope(sample_email, "billing")

    call_args = mock_response_generator.generate_response.call_args
    assert call_args.kwargs["scenario_name"] == "graceful-degradation"
    assert call_args.kwargs["email_content"] == sample_email.body
    assert call_args.kwargs["serial_number"] is None
    assert call_args.kwargs["warranty_data"] is None


@pytest.mark.asyncio
async def test_processing_result_fields_consistency(mock_config, mock_response_generator, sample_email):
    """Test that ProcessingResult fields are consistent across handlers."""
    handler = GracefulDegradationHandler(mock_config, mock_response_generator)

    result = await handler.handle_out_of_scope(sample_email, "test")

    # Verify all required fields present
    assert hasattr(result, 'success')
    assert hasattr(result, 'email_id')
    assert hasattr(result, 'scenario_used')
    assert hasattr(result, 'serial_number')
    assert hasattr(result, 'warranty_status')
    assert hasattr(result, 'response_sent')
    assert hasattr(result, 'ticket_created')
    assert hasattr(result, 'ticket_id')
    assert hasattr(result, 'processing_time_ms')
    assert hasattr(result, 'error_message')
    assert hasattr(result, 'failed_step')
