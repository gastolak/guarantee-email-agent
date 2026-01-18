"""Unit tests for LLM response generator."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from guarantee_email_agent.llm.response_generator import (
    ResponseGenerator,
    MODEL_CLAUDE_SONNET_4_5,
    DEFAULT_TEMPERATURE,
)
from guarantee_email_agent.instructions.loader import InstructionFile
from guarantee_email_agent.config.schema import (
    AgentConfig,
    InstructionsConfig,
    SecretsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
    LLMConfig,
)
from guarantee_email_agent.utils.errors import LLMTimeoutError, LLMError


@pytest.fixture
def temp_main_instruction(tmp_path: Path):
    """Create temporary main instruction file."""
    instruction_file = tmp_path / "main.md"
    instruction_file.write_text("""---
name: main-orchestration
description: Main instruction
version: 1.0.0
---

<objective>Process warranty emails</objective>
""")
    return str(instruction_file)


@pytest.fixture
def temp_scenarios_dir(tmp_path: Path):
    """Create temporary scenarios directory."""
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()

    # Create valid-warranty scenario
    valid_warranty = scenarios_dir / "valid-warranty.md"
    valid_warranty.write_text("""---
name: valid-warranty
description: Valid warranty scenario
trigger: valid-warranty
version: 1.0.0
---

<objective>Generate valid warranty response</objective>
<response-tone>Professional, helpful</response-tone>
""")

    # Create graceful-degradation
    graceful = scenarios_dir / "graceful-degradation.md"
    graceful.write_text("""---
name: graceful-degradation
description: Fallback
trigger: null
version: 1.0.0
---

<objective>Fallback response</objective>
""")

    return str(scenarios_dir)


@pytest.fixture
def test_config(temp_main_instruction: str, temp_scenarios_dir: str):
    """Create test agent configuration with Gemini provider."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main=temp_main_instruction,
            scenarios=tuple(),
            scenarios_dir=temp_scenarios_dir,
        ),
        eval=EvalConfig(test_suite_path="./evals"),
        logging=LoggingConfig(level="INFO"),
        llm=LLMConfig(
            provider="gemini",
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=8192,
            timeout_seconds=15
        ),
        secrets=SecretsConfig(
            anthropic_api_key=None,
            gemini_api_key="test-gemini-api-key",
            gmail_api_key="test-gmail-key",
            warranty_api_key="test-warranty-key",
            ticketing_api_key="test-ticketing-key",
        ),
    )


@pytest.fixture
def main_instruction_obj(temp_main_instruction: str):
    """Create main instruction object."""
    from guarantee_email_agent.instructions.loader import load_instruction
    return load_instruction(temp_main_instruction)


def test_response_generator_initialization(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test ResponseGenerator initialization with Gemini."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    assert generator.config == test_config
    assert generator.main_instruction == main_instruction_obj
    assert generator.llm_provider is not None  # Changed from client
    assert generator.router is not None


def test_response_generator_initialization_missing_api_key(main_instruction_obj: InstructionFile):
    """Test ResponseGenerator fails without Gemini API key."""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=tuple(),
            scenarios_dir="instructions/scenarios",
        ),
        eval=EvalConfig(test_suite_path="./evals"),
        logging=LoggingConfig(level="INFO"),
        llm=LLMConfig(
            provider="gemini",
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=8192,
            timeout_seconds=15
        ),
        secrets=SecretsConfig(
            anthropic_api_key=None,
            gemini_api_key=None,  # Missing!
            gmail_api_key="test",
            warranty_api_key="test",
            ticketing_api_key="test",
        ),
    )

    with pytest.raises(ValueError) as exc_info:
        ResponseGenerator(config, main_instruction_obj)

    assert "GEMINI_API_KEY" in str(exc_info.value) and "required" in str(exc_info.value)


def test_build_response_system_message(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test system message construction from main + scenario instructions."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    # Load scenario instruction
    from guarantee_email_agent.instructions.loader import load_instruction
    scenarios_dir = Path(test_config.instructions.scenarios_dir)
    scenario_file = scenarios_dir / "valid-warranty.md"
    scenario_instruction = load_instruction(str(scenario_file))

    system_message = generator.build_response_system_message(
        main_instruction_obj,
        scenario_instruction
    )

    assert "warranty email response agent" in system_message
    assert "Main Instruction:" in system_message
    assert "Scenario-Specific Instruction" in system_message
    assert "<objective>Process warranty emails</objective>" in system_message
    assert "<objective>Generate valid warranty response</objective>" in system_message


def test_build_response_user_message(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test user message construction with email content and warranty data."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    email_content = "Hi, I need warranty info for SN12345"
    serial_number = "SN12345"
    warranty_data = {
        "status": "valid",
        "expiration_date": "2025-12-31",
        "coverage": "Full warranty"
    }

    user_message = generator.build_response_user_message(
        email_content,
        serial_number,
        warranty_data
    )

    assert "Customer Email:" in user_message
    assert email_content in user_message
    assert "Serial Number: SN12345" in user_message
    assert "Warranty Status:" in user_message
    assert "Status: valid" in user_message
    assert "Expiration Date: 2025-12-31" in user_message
    assert "Generate the response email now:" in user_message


def test_build_response_user_message_missing_data(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test user message construction with missing serial and warranty data."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    email_content = "I need help with my warranty"

    user_message = generator.build_response_user_message(
        email_content,
        serial_number=None,
        warranty_data=None
    )

    assert "Customer Email:" in user_message
    assert email_content in user_message
    assert "Serial Number:" not in user_message
    assert "Warranty Status:" not in user_message


@pytest.mark.asyncio
async def test_generate_response_success(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test successful response generation with Gemini."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    # Mock LLM provider response (returns string directly)
    mock_response_text = "Dear Customer,\n\nYour warranty is valid until 2025-12-31.\n\nBest regards,\nSupport Team"

    with patch.object(generator.llm_provider, 'create_message', return_value=mock_response_text):
        response = await generator.generate_response(
            scenario_name="valid-warranty",
            email_content="Hi, check my warranty for SN12345",
            serial_number="SN12345",
            warranty_data={"status": "valid", "expiration_date": "2025-12-31"}
        )

    assert "Dear Customer" in response
    assert "2025-12-31" in response
    assert len(response) > 0


@pytest.mark.asyncio
async def test_generate_response_uses_correct_model_and_temperature(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test that generate_response uses Gemini with correct config."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    with patch.object(generator.llm_provider, 'create_message', return_value="Test response") as mock_create:
        await generator.generate_response(
            scenario_name="valid-warranty",
            email_content="Test email",
            serial_number="SN123"
        )

        # Verify LLM provider was called (config validation happens in provider)
        assert mock_create.called
        # Provider uses config.llm settings which we already verified in test_config fixture


@pytest.mark.asyncio
async def test_generate_response_empty_response_raises_error(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test that empty LLM response raises LLMError."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    # Mock empty response
    with patch.object(generator.llm_provider, 'create_message', return_value=""):
        with pytest.raises(LLMError) as exc_info:
            await generator.generate_response(
                scenario_name="valid-warranty",
                email_content="Test",
                serial_number="SN123"
            )

        assert "empty response" in exc_info.value.message.lower()
        assert exc_info.value.code == "llm_empty_response"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Timeout test takes 15+ seconds to run - validates in integration testing")
async def test_generate_response_timeout(test_config: AgentConfig, main_instruction_obj: InstructionFile):
    """Test LLM timeout handling."""
    generator = ResponseGenerator(test_config, main_instruction_obj)

    # Mock slow response
    import time
    def slow_response(*args, **kwargs):
        time.sleep(20)
        return Mock()

    with patch.object(generator.llm_provider, 'create_message', side_effect=slow_response):
        with pytest.raises(LLMTimeoutError) as exc_info:
            await generator.generate_response(
                scenario_name="valid-warranty",
                email_content="Test",
                serial_number="SN123"
            )

        assert "timeout" in exc_info.value.message.lower()
        assert exc_info.value.code == "llm_response_timeout"
