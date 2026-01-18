"""Integration tests for scenario-based response generation."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from guarantee_email_agent.llm.response_generator import ResponseGenerator
from guarantee_email_agent.instructions.router import ScenarioRouter
from guarantee_email_agent.instructions.loader import load_instruction
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


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear instruction cache before each test."""
    from guarantee_email_agent.instructions.loader import clear_instruction_cache
    clear_instruction_cache()
    yield
    clear_instruction_cache()


@pytest.fixture
def integration_scenarios_dir(tmp_path: Path):
    """Create complete scenarios directory for integration testing."""
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()

    # Create valid-warranty scenario
    (scenarios_dir / "valid-warranty.md").write_text("""---
name: valid-warranty
description: Valid warranty response instructions
trigger: valid-warranty
version: 1.0.0
---

<objective>
Generate professional response confirming valid warranty.
</objective>

<response-structure>
1. Greeting
2. Confirm warranty is valid
3. Provide expiration date
4. Explain next steps
5. Professional closing
</response-structure>
""")

    # Create invalid-warranty scenario
    (scenarios_dir / "invalid-warranty.md").write_text("""---
name: invalid-warranty
description: Invalid/expired warranty response instructions
trigger: invalid-warranty
version: 1.0.0
---

<objective>
Generate empathetic response for expired warranty with alternatives.
</objective>

<response-structure>
1. Greeting
2. Explain warranty has expired
3. Empathetic acknowledgment
4. Offer alternatives
5. Professional closing
</response-structure>
""")

    # Create missing-info scenario
    (scenarios_dir / "missing-info.md").write_text("""---
name: missing-info
description: Request missing information
trigger: missing-info
version: 1.0.0
---

<objective>
Politely request serial number needed for warranty check.
</objective>

<response-structure>
1. Greeting
2. Explain need for serial number
3. Guide where to find it
4. Request they provide it
5. Assure prompt help
</response-structure>
""")

    # Create graceful-degradation scenario
    (scenarios_dir / "graceful-degradation.md").write_text("""---
name: graceful-degradation
description: Fallback for unclear cases
trigger: null
version: 1.0.0
---

<objective>
Handle unclear inquiries with helpful response.
</objective>

<response-structure>
1. Greeting
2. Request clarification
3. Provide support contact
4. Assure assistance
</response-structure>
""")

    return str(scenarios_dir)


@pytest.fixture
def integration_main_instruction(tmp_path: Path):
    """Create main instruction for integration testing."""
    main_file = tmp_path / "main.md"
    main_file.write_text("""---
name: main-orchestration
description: Main orchestration instruction
version: 1.0.0
---

<objective>
Process warranty inquiry emails by analyzing content and generating appropriate responses.
</objective>

<workflow>
1. Analyze email content
2. Extract serial number
3. Determine scenario
4. Generate response
</workflow>
""")
    return str(main_file)


@pytest.fixture
def integration_config(integration_main_instruction: str, integration_scenarios_dir: str):
    """Create configuration for integration testing with Gemini provider."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main=integration_main_instruction,
            scenarios=tuple(),
            scenarios_dir=integration_scenarios_dir,
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


@pytest.mark.asyncio
async def test_end_to_end_valid_warranty_response(integration_config: AgentConfig, integration_main_instruction: str):
    """Test end-to-end flow for valid warranty scenario."""
    # Load main instruction
    main_instruction = load_instruction(integration_main_instruction)

    # Create response generator
    generator = ResponseGenerator(integration_config, main_instruction)

    # Mock LLM provider response (returns string directly)
    mock_response_text = "Dear Customer,\n\nI'm pleased to confirm your warranty is valid until 2025-12-31.\n\nBest regards,\nSupport Team"

    with patch.object(generator.llm_provider, 'create_message', return_value=mock_response_text):
        response = await generator.generate_response(
            scenario_name="valid-warranty",
            email_content="Hi, I need to check warranty for serial SN12345",
            serial_number="SN12345",
            warranty_data={"status": "valid", "expiration_date": "2025-12-31"}
        )

    # Verify response generated
    assert len(response) > 0
    assert "valid" in response.lower() or "2025-12-31" in response


@pytest.mark.asyncio
async def test_end_to_end_invalid_warranty_response(integration_config: AgentConfig, integration_main_instruction: str):
    """Test end-to-end flow for invalid/expired warranty scenario."""
    main_instruction = load_instruction(integration_main_instruction)
    generator = ResponseGenerator(integration_config, main_instruction)

    # Mock LLM provider response
    mock_response_text = "Dear Customer,\n\nYour warranty expired on 2024-06-30. We offer extended warranty options.\n\nBest regards,\nSupport Team"

    with patch.object(generator.llm_provider, 'create_message', return_value=mock_response_text):
        response = await generator.generate_response(
            scenario_name="invalid-warranty",
            email_content="Check my warranty for SN12345",
            serial_number="SN12345",
            warranty_data={"status": "expired", "expiration_date": "2024-06-30"}
        )

    assert len(response) > 0
    assert "expired" in response.lower() or "2024-06-30" in response


@pytest.mark.asyncio
async def test_end_to_end_missing_info_response(integration_config: AgentConfig, integration_main_instruction: str):
    """Test end-to-end flow for missing information scenario."""
    main_instruction = load_instruction(integration_main_instruction)
    generator = ResponseGenerator(integration_config, main_instruction)

    # Mock LLM provider response
    mock_response_text = "Dear Customer,\n\nTo check your warranty, I'll need your product serial number.\n\nBest regards,\nSupport Team"

    with patch.object(generator.llm_provider, 'create_message', return_value=mock_response_text):
        response = await generator.generate_response(
            scenario_name="missing-info",
            email_content="I need warranty information",
            serial_number=None,
            warranty_data=None
        )

    assert len(response) > 0
    assert "serial" in response.lower() or "number" in response.lower()


@pytest.mark.asyncio
async def test_end_to_end_graceful_degradation_fallback(integration_config: AgentConfig, integration_main_instruction: str):
    """Test end-to-end flow for graceful degradation fallback."""
    main_instruction = load_instruction(integration_main_instruction)
    generator = ResponseGenerator(integration_config, main_instruction)

    # Mock LLM provider response
    mock_response_text = "Dear Customer,\n\nThank you for contacting us. Please provide more details.\n\nBest regards,\nSupport Team"

    with patch.object(generator.llm_provider, 'create_message', return_value=mock_response_text):
        # Try to use nonexistent scenario - should fall back to graceful-degradation
        response = await generator.generate_response(
            scenario_name="nonexistent-scenario",
            email_content="Some unclear inquiry",
            serial_number=None,
            warranty_data=None
        )

    # Should get graceful degradation response
    assert len(response) > 0


def test_scenario_router_loads_all_scenarios(integration_config: AgentConfig):
    """Test that scenario router can load all scenario files."""
    router = ScenarioRouter(integration_config)

    scenarios = ["valid-warranty", "invalid-warranty", "missing-info", "graceful-degradation"]

    for scenario_name in scenarios:
        scenario = router.select_scenario(scenario_name)
        assert scenario.name == scenario_name
        assert scenario.version == "1.0.0"


@pytest.mark.asyncio
async def test_system_message_combines_main_and_scenario(integration_config: AgentConfig, integration_main_instruction: str):
    """Test that system message properly combines main and scenario instructions."""
    main_instruction = load_instruction(integration_main_instruction)
    generator = ResponseGenerator(integration_config, main_instruction)

    # Load scenario instruction
    scenario_instruction = generator.router.select_scenario("valid-warranty")

    # Build system message
    system_message = generator.build_response_system_message(main_instruction, scenario_instruction)

    # Verify both instructions present
    assert "Main Instruction:" in system_message
    assert "Scenario-Specific Instruction" in system_message
    assert main_instruction.body in system_message
    assert scenario_instruction.body in system_message
