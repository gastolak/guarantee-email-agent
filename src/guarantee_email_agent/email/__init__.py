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
from guarantee_email_agent.tools import GmailTool, CrmAbacusTool
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

    # Initialize tools
    gmail_tool = GmailTool(config.tools.gmail, config.secrets.gmail_oauth_token)
    crm_abacus_tool = CrmAbacusTool(
        config=config.tools.crm_abacus,
        username=config.secrets.crm_abacus_username,
        password=config.secrets.crm_abacus_password
    )

    # Initialize response generator
    response_generator = ResponseGenerator(config, main_instruction)

    # Create processor with all dependencies
    processor = EmailProcessor(
        config=config,
        parser=parser,
        extractor=extractor,
        detector=detector,
        gmail_tool=gmail_tool,
        crm_abacus_tool=crm_abacus_tool,
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
