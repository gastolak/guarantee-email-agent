"""Integration tests for main instruction flow."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from guarantee_email_agent.instructions.loader import load_instruction, clear_instruction_cache
from guarantee_email_agent.llm.orchestrator import Orchestrator
from guarantee_email_agent.config.schema import (
    AgentConfig,
    InstructionsConfig,
    SecretsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear instruction cache before each test."""
    clear_instruction_cache()
    yield
    clear_instruction_cache()


@pytest.fixture
def main_instruction_file(tmp_path: Path):
    """Create main instruction file for integration testing."""
    instruction_file = tmp_path / "main.md"
    instruction_file.write_text("""---
name: main-orchestration
description: Main orchestration instruction for warranty email processing
version: 1.0.0
---

<objective>
Process warranty inquiry emails by analyzing email content, extracting serial numbers, and determining the appropriate scenario for response generation.
</objective>

<workflow>
Follow this workflow for every email:
1. Analyze email content to understand customer intent
2. Extract serial number using the patterns defined below
3. Determine which scenario applies based on email characteristics
4. Return structured output with scenario, serial number, and confidence
</workflow>

<serial-number-patterns>
Recognize serial numbers in these common formats:
- "SN12345" or "SN-12345" (with or without hyphen)
- "Serial: ABC-123" or "Serial Number: ABC-123"
- "S/N: XYZ789" or "S/N XYZ789"
</serial-number-patterns>

<scenario-detection>
Identify the appropriate scenario based on email characteristics:

**valid-warranty**:
- Email contains a clear serial number
- Customer is inquiring about warranty status

**missing-info**:
- No serial number found in email body
- Serial number is ambiguous or unclear

**out-of-scope**:
- Email is not about warranty
- Spam, unrelated inquiry
</scenario-detection>

<output-format>
Return valid JSON in this exact format:
{
  "scenario": "scenario-name",
  "serial_number": "extracted-serial-or-null",
  "confidence": 0.95
}
</output-format>
""")
    return str(instruction_file)


@pytest.fixture
def integration_config(main_instruction_file: str):
    """Create configuration for integration testing."""
    return AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="test://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="test://warranty"),
            ticketing_system=MCPConnectionConfig(connection_string="test://ticketing"),
        ),
        instructions=InstructionsConfig(
            main=main_instruction_file,
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


def test_complete_instruction_loading_flow(integration_config: AgentConfig):
    """Test complete flow: load main instruction → create orchestrator."""
    # Load main instruction
    main_instruction = load_instruction(integration_config.instructions.main)

    # Verify instruction loaded correctly
    assert main_instruction.name == "main-orchestration"
    assert main_instruction.version == "1.0.0"
    assert "<objective>" in main_instruction.body
    assert "<workflow>" in main_instruction.body
    assert "serial-number-patterns" in main_instruction.body
    assert "scenario-detection" in main_instruction.body

    # Create orchestrator with loaded instruction
    orchestrator = Orchestrator(integration_config)

    # Verify orchestrator initialized correctly
    assert orchestrator.main_instruction.name == main_instruction.name
    assert orchestrator.main_instruction.version == main_instruction.version


@pytest.mark.asyncio
async def test_end_to_end_email_orchestration_valid_warranty(integration_config: AgentConfig):
    """Test end-to-end flow: email with serial number → valid-warranty scenario."""
    orchestrator = Orchestrator(integration_config)

    # Mock Anthropic API response
    mock_response = Mock()
    mock_response.content = [
        Mock(text='{"scenario": "valid-warranty", "serial_number": "SN12345", "confidence": 0.98}')
    ]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response):
        email_content = "Hi, I need to check the warranty status for serial number SN12345. Thanks!"
        result = await orchestrator.orchestrate(email_content)

    # Verify scenario detection
    assert result["scenario"] == "valid-warranty"
    assert result["serial_number"] == "SN12345"
    assert result["confidence"] == 0.98


@pytest.mark.asyncio
async def test_end_to_end_email_orchestration_missing_info(integration_config: AgentConfig):
    """Test end-to-end flow: email without serial number → missing-info scenario."""
    orchestrator = Orchestrator(integration_config)

    mock_response = Mock()
    mock_response.content = [
        Mock(text='{"scenario": "missing-info", "serial_number": null, "confidence": 0.92}')
    ]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response):
        email_content = "I bought your product last year and need warranty info. Can you help?"
        result = await orchestrator.orchestrate(email_content)

    assert result["scenario"] == "missing-info"
    assert result["serial_number"] is None
    assert result["confidence"] == 0.92


@pytest.mark.asyncio
async def test_end_to_end_email_orchestration_out_of_scope(integration_config: AgentConfig):
    """Test end-to-end flow: unrelated email → out-of-scope scenario."""
    orchestrator = Orchestrator(integration_config)

    mock_response = Mock()
    mock_response.content = [
        Mock(text='{"scenario": "out-of-scope", "serial_number": null, "confidence": 0.95}')
    ]

    with patch.object(orchestrator.client.messages, 'create', return_value=mock_response):
        email_content = "How much does your product cost? Where can I buy it?"
        result = await orchestrator.orchestrate(email_content)

    assert result["scenario"] == "out-of-scope"
    assert result["serial_number"] is None


@pytest.mark.asyncio
async def test_system_message_includes_instruction_content(integration_config: AgentConfig):
    """Test that system message constructed from main instruction includes all sections."""
    orchestrator = Orchestrator(integration_config)

    system_message = orchestrator.build_system_message(orchestrator.main_instruction)

    # Verify all instruction sections included
    assert "warranty email processing agent" in system_message
    assert "<objective>" in system_message
    assert "<workflow>" in system_message
    assert "<serial-number-patterns>" in system_message
    assert "<scenario-detection>" in system_message
    assert "<output-format>" in system_message


def test_instruction_caching_in_integration_flow(integration_config: AgentConfig):
    """Test that instruction caching works in integration scenario."""
    # Clear cache first
    clear_instruction_cache()

    # Create first orchestrator - loads instruction
    orchestrator1 = Orchestrator(integration_config)
    instruction1 = orchestrator1.main_instruction

    # Create second orchestrator - should use cached instruction
    orchestrator2 = Orchestrator(integration_config)
    instruction2 = orchestrator2.main_instruction

    # Both should reference same cached instruction
    assert instruction1.name == instruction2.name
    assert instruction1.version == instruction2.version
    assert instruction1.file_path == instruction2.file_path
