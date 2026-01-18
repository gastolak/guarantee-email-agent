"""Serial number extractor using patterns and LLM fallback."""

import asyncio
import logging
import re
from typing import List

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.utils.errors import TransientError, LLMError

logger = logging.getLogger(__name__)

# Serial number regex patterns - matches common formats
# Note: Must contain at least one digit to be a valid serial (5-15 chars total)
SERIAL_PATTERNS = [
    r'(?i)SN[-\s:]?([A-Z0-9-]*\d[A-Z0-9-]*)\b',  # SN12345, SN-ABC123 (must have digit)
    r'(?i)Serial\s*(?:Number)?[:\s]+([A-Z0-9-]*\d[A-Z0-9-]*)\b',  # Serial: ABC-123 (must have digit)
    r'(?i)S/N[:\s]+([A-Z0-9-]*\d[A-Z0-9-]*)\b',  # S/N: XYZ789 (must have digit)
    r'(?i)Serial#[:\s]*([A-Z0-9-]*\d[A-Z0-9-]*)\b',  # Serial#: ABC123 (must have digit)
]


class SerialNumberExtractor:
    """Extract serial numbers from emails using patterns and LLM fallback.

    Two-stage extraction:
    1. Pattern-based (fast path) - regex matching for common formats
    2. LLM-based (fallback) - when patterns fail or low confidence

    Handles edge cases:
    - Multiple serial numbers (ambiguous, requires graceful degradation)
    - No serial found (return None, trigger missing-info scenario)
    - Extraction errors (graceful handling, no crashes)
    """

    def __init__(self, config: AgentConfig, main_instruction_body: str):
        """Initialize serial number extractor.

        Args:
            config: Agent configuration with API keys
            main_instruction_body: Main instruction for LLM guidance

        Raises:
            ValueError: If ANTHROPIC_API_KEY not configured
        """
        self.config = config
        self.main_instruction_body = main_instruction_body

        # Initialize Anthropic client
        api_key = config.secrets.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured in secrets")

        self.client = Anthropic(api_key=api_key)

        logger.info("Serial number extractor initialized")

    def extract_with_patterns(self, email_body: str) -> SerialExtractionResult:
        """Try pattern-based extraction (fast path).

        Uses regex patterns to match common serial number formats.
        High confidence when single match found, ambiguous when multiple.

        Args:
            email_body: Email body text

        Returns:
            SerialExtractionResult with pattern extraction results
        """
        all_matches: List[str] = []

        # Try all patterns ((?i) in patterns makes them case-insensitive)
        for pattern in SERIAL_PATTERNS:
            matches = re.findall(pattern, email_body)
            # Filter to only 5-15 character serials
            valid_matches = [m for m in matches if 5 <= len(m) <= 15]
            all_matches.extend(valid_matches)

        # Deduplicate matches
        unique_serials = list(set(all_matches))

        if not unique_serials:
            # No serial found via patterns
            logger.debug("Pattern extraction: no serial numbers found")
            return SerialExtractionResult(
                serial_number=None,
                confidence=0.0,
                multiple_serials_detected=False,
                all_detected_serials=[],
                extraction_method="pattern",
                ambiguous=False
            )

        if len(unique_serials) == 1:
            # Single serial found - high confidence
            serial = unique_serials[0]
            logger.info(f"Pattern extraction: serial found: {serial}")
            return SerialExtractionResult(
                serial_number=serial,
                confidence=0.95,
                multiple_serials_detected=False,
                all_detected_serials=[serial],
                extraction_method="pattern",
                ambiguous=False
            )

        # Multiple serials detected - ambiguous
        logger.warning(f"Pattern extraction: multiple serials detected: {unique_serials}")
        return SerialExtractionResult(
            serial_number=unique_serials[0],  # Choose first
            confidence=0.7,  # Lower confidence due to ambiguity
            multiple_serials_detected=True,
            all_detected_serials=unique_serials,
            extraction_method="pattern",
            ambiguous=True
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def extract_with_llm(self, email_body: str) -> SerialExtractionResult:
        """Extract serial number using LLM (fallback method).

        Uses Anthropic Claude with main instruction guidance to extract
        serial numbers from unconventional formats.

        Args:
            email_body: Email body text

        Returns:
            SerialExtractionResult with LLM extraction results

        Raises:
            LLMError: On LLM call failure after retries
        """
        logger.info("LLM extraction: attempting serial number extraction")

        try:
            # Build system message with main instruction + extraction guidance
            system_message = (
                f"{self.main_instruction_body}\n\n"
                f"Extract the product serial number from the customer email. "
                f"Serial numbers are typically alphanumeric codes 5-15 characters long. "
                f"Return ONLY the serial number text, or the word 'NONE' if no serial number found."
            )

            # Build user message
            user_message = f"Customer email:\n\n{email_body}\n\nExtract the serial number:"

            # Call Anthropic API with timeout (NFR11: 15 seconds)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-3-5-sonnet-20241022",  # Pinned version per project context
                    max_tokens=100,
                    temperature=0,  # Maximum determinism per NFR1
                    system=system_message,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                ),
                timeout=15  # NFR11: 15-second timeout
            )

            # Extract response text
            response_text = response.content[0].text.strip()

            logger.debug(f"LLM extraction response: {response_text}")

            # Parse response
            if response_text.upper() == 'NONE' or not response_text:
                logger.info("LLM extraction: no serial number found")
                return SerialExtractionResult(
                    serial_number=None,
                    confidence=0.0,
                    multiple_serials_detected=False,
                    all_detected_serials=[],
                    extraction_method="llm",
                    ambiguous=False
                )

            # Serial number found
            logger.info(f"LLM extraction: serial found: {response_text}")
            return SerialExtractionResult(
                serial_number=response_text,
                confidence=0.85,  # LLM confidence slightly lower than pattern
                multiple_serials_detected=False,
                all_detected_serials=[response_text],
                extraction_method="llm",
                ambiguous=False
            )

        except asyncio.TimeoutError:
            raise LLMError(
                message="LLM serial extraction timeout (15s)",
                code="llm_serial_extraction_timeout",
                details={"timeout": 15}
            )
        except Exception as e:
            raise LLMError(
                message=f"LLM serial extraction failed: {str(e)}",
                code="llm_serial_extraction_failed",
                details={"error": str(e)}
            )

    async def extract_serial_number(self, email: EmailMessage) -> SerialExtractionResult:
        """Extract serial number from email (tries patterns then LLM).

        Two-stage extraction with graceful error handling:
        1. Pattern extraction (fast path)
        2. LLM extraction (fallback if pattern fails/low confidence)

        Args:
            email: Parsed email message

        Returns:
            SerialExtractionResult with extraction outcome (never crashes)
        """
        logger.info(
            f"Extracting serial number from email: subject='{email.subject}'"
        )

        try:
            # Try pattern-based extraction first (fast path)
            pattern_result = self.extract_with_patterns(email.body)

            # If pattern extraction succeeded with high confidence, return immediately
            if pattern_result.is_successful() and pattern_result.confidence >= 0.8:
                logger.info(
                    f"Serial extracted via pattern: {pattern_result.serial_number} "
                    f"(confidence={pattern_result.confidence})"
                )
                return pattern_result

            # Pattern extraction failed or low confidence - fallback to LLM
            logger.info("Pattern extraction inconclusive, trying LLM extraction")
            llm_result = await self.extract_with_llm(email.body)

            if llm_result.is_successful():
                logger.info(
                    f"Serial extracted via LLM: {llm_result.serial_number} "
                    f"(confidence={llm_result.confidence})"
                )
                return llm_result

            # Both methods failed - no serial found
            logger.warning("Serial number extraction failed: not found in email")
            return SerialExtractionResult(
                serial_number=None,
                confidence=0.0,
                multiple_serials_detected=False,
                all_detected_serials=[],
                extraction_method="none",
                ambiguous=False
            )

        except Exception as e:
            # Graceful error handling - don't crash (NFR5: zero silent failures)
            logger.error(
                f"Serial extraction error: {str(e)}",
                extra={
                    "subject": email.subject,
                    "from": email.from_address,
                    "error": str(e)
                },
                exc_info=True
            )

            # Return failed result (don't propagate exception)
            # Mark as ambiguous to trigger graceful degradation
            return SerialExtractionResult(
                serial_number=None,
                confidence=0.0,
                multiple_serials_detected=False,
                all_detected_serials=[],
                extraction_method="error",
                ambiguous=True  # Route to graceful degradation
            )
