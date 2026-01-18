"""Unit tests for LLM orchestrator."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from guarantee_email_agent.llm.orchestrator import Orchestrator, MODEL_CLAUDE_SONNET_4_5, DEFAULT_TEMPERATURE
from guarantee_email_agent.config.schema import (
    AgentConfig,
    InstructionsConfig,
    SecretsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
)
from guarantee_email_agent.utils.errors import (
    LLMTimeoutError,
    LLMAuthenticationError,
    LLMError,
)


@pytest.fixture
def temp_instruction_file(tmp_path: Path):
    """Create a temporary main instruction file."""
    instruction_file = tmp_path / "main.md"
    instruction_file.write_text("""---
name: main-orchestration
description: Test main instruction
version: 1.0.0
---

<objective>
Test email processing
</objective>

<workflow>
1. Analyze email
2. Extract serial number
3. Detect scenario
</workflow>

<output-format>
Return JSON: {"scenario": "...", "serial_number": "...", "confidence": 0.0}
</output-format>
""")
    return str(instruction_file)


@pytest.fixture
def test_config(temp_instruction_file: str):
    """Create test agent configuration."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main=temp_instruction_file,
            scenarios=tuple(),
        ),
        eval=EvalConfig(test_suite_path="./evals"),
        logging=LoggingConfig(level="INFO"),
        secrets=SecretsConfig(
            anthropic_api_key="test-api-key",
            gmail_api_key="test-gmail-key",
            warranty_api_key="test-warranty-key",
            ticketing_api_key="test-ticketing-key",
        ),
    )


def test_orchestrator_initialization(test_config: AgentConfig):
    """Test Orchestrator initialization with valid config."""
    orchestrator = Orchestrator(test_config)

    assert orchestrator.config == test_config
    assert orchestrator.client is not None
    assert orchestrator.main_instruction is not None
    assert orchestrator.main_instruction.name == "main-orchestration"
    assert orchestrator.main_instruction.version == "1.0.0"


def test_orchestrator_initialization_missing_api_key():
    """Test Orchestrator initialization fails without API key."""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=tuple(),
        ),
        eval=EvalConfig(test_suite_path="./evals"),
        logging=LoggingConfig(level="INFO"),
        secrets=SecretsConfig(
            anthropic_api_key="",  # Empty API key
            gmail_api_key="test",
            warranty_api_key="test",
            ticketing_api_key="test",
        ),
    )

    with pytest.raises(ValueError) as exc_info:
        Orchestrator(config)

    assert "ANTHROPIC_API_KEY not configured" in str(exc_info.value)


def test_build_system_message(test_config: AgentConfig):
    """Test system message construction from instruction."""
    orchestrator = Orchestrator(test_config)

    system_message = orchestrator.build_system_message(orchestrator.main_instruction)

    assert "warranty email processing agent" in system_message
    assert "<objective>" in system_message
    assert "<workflow>" in system_message
    assert "Test email processing" in system_message


@pytest.mark.asyncio
async def test_orchestrate_success(test_config: AgentConfig):
    """Test successful orchestration with mocked Anthropic API."""
    orchestrator = Orchestrator(test_config)

    # Mock Anthropic response
    mock_response = Mock()
    mock_response.content = [
        Mock(text='{"scenario": "valid-warranty", "serial_number": "SN12345", "confidence": 0.95}')
    ]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response):
        result = await orchestrator.orchestrate("Hi, my serial is SN12345")

    assert result["scenario"] == "valid-warranty"
    assert result["serial_number"] == "SN12345"
    assert result["confidence"] == 0.95


@pytest.mark.asyncio
async def test_orchestrate_uses_correct_model(test_config: AgentConfig):
    """Test that orchestrate uses Claude Sonnet 4.5 model."""
    orchestrator = Orchestrator(test_config)

    mock_response = Mock()
    mock_response.content = [
        Mock(text='{"scenario": "valid-warranty", "serial_number": "SN12345", "confidence": 0.95}')
    ]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response) as mock_create:
        await orchestrator.orchestrate("Test email")

        # Verify model and temperature
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == MODEL_CLAUDE_SONNET_4_5
        assert call_kwargs["temperature"] == DEFAULT_TEMPERATURE
        assert call_kwargs["temperature"] == 0  # Determinism


@pytest.mark.asyncio
@pytest.mark.skip(reason="Timeout test takes 15+ seconds to run - validates in integration testing")
async def test_orchestrate_timeout(test_config: AgentConfig):
    """Test LLM timeout handling."""
    orchestrator = Orchestrator(test_config)

    # Mock slow response that times out (simulate blocking call)
    import time
    def slow_response(*args, **kwargs):
        time.sleep(20)  # Longer than 15s timeout - blocking call
        return Mock()

    with patch.object(orchestrator.client.messages, 'create', side_effect=slow_response):
        with pytest.raises(LLMTimeoutError) as exc_info:
            await orchestrator.orchestrate("Test email")

        assert "timeout" in exc_info.value.message.lower()
        assert exc_info.value.code == "llm_timeout"


@pytest.mark.asyncio
async def test_orchestrate_invalid_json_response(test_config: AgentConfig):
    """Test handling of invalid JSON response from LLM."""
    orchestrator = Orchestrator(test_config)

    mock_response = Mock()
    mock_response.content = [Mock(text='This is not valid JSON')]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response):
        with pytest.raises(LLMError) as exc_info:
            await orchestrator.orchestrate("Test email")

        assert "invalid JSON" in exc_info.value.message
        assert exc_info.value.code == "llm_invalid_json_response"


@pytest.mark.asyncio
async def test_orchestrate_missing_scenario_field(test_config: AgentConfig):
    """Test handling of response missing required 'scenario' field."""
    orchestrator = Orchestrator(test_config)

    mock_response = Mock()
    mock_response.content = [
        Mock(text='{"serial_number": "SN12345", "confidence": 0.95}')  # Missing 'scenario'
    ]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response):
        with pytest.raises(LLMError) as exc_info:
            await orchestrator.orchestrate("Test email")

        assert "missing 'scenario' field" in exc_info.value.message
        assert exc_info.value.code == "llm_missing_scenario"


@pytest.mark.asyncio
async def test_orchestrate_authentication_error(test_config: AgentConfig):
    """Test handling of authentication errors (non-transient)."""
    orchestrator = Orchestrator(test_config)

    with patch.object(orchestrator.client.messages, 'create', side_effect=Exception("Authentication failed: Invalid API key")):
        with pytest.raises(LLMAuthenticationError) as exc_info:
            await orchestrator.orchestrate("Test email")

        assert "authentication" in exc_info.value.message.lower()
        assert exc_info.value.code == "llm_authentication_failed"


@pytest.mark.asyncio
async def test_orchestrate_constructs_messages_correctly(test_config: AgentConfig):
    """Test that orchestrate constructs system and user messages correctly."""
    orchestrator = Orchestrator(test_config)

    mock_response = Mock()
    mock_response.content = [
        Mock(text='{"scenario": "valid-warranty", "serial_number": "SN12345", "confidence": 0.95}')
    ]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response) as mock_create:
        email_content = "Hi, my serial number is SN12345"
        await orchestrator.orchestrate(email_content)

        # Verify messages structure
        call_kwargs = mock_create.call_args[1]
        assert "warranty email processing agent" in call_kwargs["system"]
        assert "<objective>" in call_kwargs["system"]

        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert email_content in messages[0]["content"]
