"""Email processing module for warranty inquiry emails."""

from guarantee_email_agent.email.models import (
    EmailMessage,
    SerialExtractionResult,
)
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor

__all__ = [
    "EmailMessage",
    "SerialExtractionResult",
    "EmailParser",
    "SerialNumberExtractor",
]
