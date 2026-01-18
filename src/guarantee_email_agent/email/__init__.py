"""Email processing module for warranty inquiry emails."""

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.models import (
    EmailMessage,
    SerialExtractionResult,
)
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.processor import EmailProcessor
from guarantee_email_agent.email.processor_models import (
    ProcessingResult,
    ScenarioDetectionResult,
)
from guarantee_email_agent.email.scenario_detector import ScenarioDetector
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.instructions.loader import load_instruction_cached
from guarantee_email_agent.integrations.mcp.gmail_client import GmailMCPClient
from guarantee_email_agent.integrations.mcp.ticketing_client import TicketingMCPClient
from guarantee_email_agent.integrations.mcp.warranty_client import WarrantyMCPClient
from guarantee_email_agent.llm.response_generator import ResponseGenerator


def create_email_processor(config: AgentConfig) -> EmailProcessor:
    """Factory function to create EmailProcessor with all dependencies.

    Args:
        config: Agent configuration

    Returns:
        Fully initialized EmailProcessor

    Raises:
        ValueError: If required configuration missing
    """
    # Load main instruction
    main_instruction = load_instruction_cached(config.instructions.main)

    # Initialize parsers and extractors
    parser = EmailParser()
    extractor = SerialNumberExtractor(config, main_instruction.body)
    detector = ScenarioDetector(config, main_instruction.body)

    # Initialize MCP clients
    gmail_client = GmailMCPClient(config.mcp.gmail)
    warranty_client = WarrantyMCPClient(config.mcp.warranty_api)
    ticketing_client = TicketingMCPClient(config.mcp.ticketing_system)

    # Initialize response generator
    response_generator = ResponseGenerator(config, main_instruction)

    # Create processor with all dependencies
    processor = EmailProcessor(
        config=config,
        parser=parser,
        extractor=extractor,
        detector=detector,
        gmail_client=gmail_client,
        warranty_client=warranty_client,
        ticketing_client=ticketing_client,
        response_generator=response_generator,
    )

    return processor


__all__ = [
    "EmailMessage",
    "SerialExtractionResult",
    "EmailParser",
    "SerialNumberExtractor",
    "ScenarioDetector",
    "ScenarioDetectionResult",
    "EmailProcessor",
    "ProcessingResult",
    "create_email_processor",
]
