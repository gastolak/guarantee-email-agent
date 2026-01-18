"""Scenario detector for email classification using heuristics and LLM fallback."""

import asyncio
import logging
import re
from typing import Optional

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.email.processor_models import ScenarioDetectionResult
from guarantee_email_agent.utils.errors import TransientError, LLMError

logger = logging.getLogger(__name__)

# Spam/junk keywords for heuristic detection
SPAM_KEYWORDS = [
    'unsubscribe', 'viagra', 'casino', 'lottery', 'click here',
    'free money', 'congratulations you won', 'click to claim'
]


class ScenarioDetector:
    """Detect warranty inquiry scenarios using heuristics and LLM fallback.

    Two-stage detection:
    1. Heuristic-based (fast path) - regex and keyword matching
    2. LLM-based (fallback) - when heuristics have low confidence

    Handles edge cases:
    - Empty emails → out-of-scope
    - Spam detection → out-of-scope
    - Missing serial number → missing-info
    - Ambiguous cases → graceful-degradation
    """

    def __init__(self, config: AgentConfig, main_instruction_body: str):
        """Initialize scenario detector.

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
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=api_key)

        logger.info("Scenario detector initialized")

    def detect_with_heuristics(
        self,
        email: EmailMessage,
        serial_result: SerialExtractionResult
    ) -> ScenarioDetectionResult:
        """Fast heuristic-based scenario detection.

        Uses simple rules to classify emails:
        - Spam keywords → out-of-scope (checked first)
        - Very short email → potential spam (low confidence)
        - No serial found → missing-info
        - "warranty" keyword + serial → warranty inquiry

        Args:
            email: Parsed email message
            serial_result: Serial number extraction result

        Returns:
            ScenarioDetectionResult with heuristic detection
        """
        email_text = f"{email.subject} {email.body}".lower()

        # Heuristic 1: Spam detection (highest priority)
        if any(keyword in email_text for keyword in SPAM_KEYWORDS):
            logger.info("Heuristic: Spam keywords detected → out-of-scope")
            return ScenarioDetectionResult(
                scenario_name="out-of-scope",
                confidence=0.85,
                is_warranty_inquiry=False,
                detected_intent="spam",
                detection_method="heuristic",
                ambiguous=False
            )

        # Heuristic 2: Very short email (likely spam or incomplete)
        if len(email.body.strip()) < 20:
            logger.info("Heuristic: Very short email → potential spam (low confidence)")
            return ScenarioDetectionResult(
                scenario_name="out-of-scope",
                confidence=0.6,  # Low confidence → will trigger LLM fallback
                is_warranty_inquiry=False,
                detected_intent="incomplete",
                detection_method="heuristic",
                ambiguous=True
            )

        # Heuristic 3: "warranty" keyword present → warranty inquiry
        if re.search(r'\bwarranty\b', email_text, re.IGNORECASE):
            # Check if serial found
            if serial_result.is_successful():
                logger.info("Heuristic: Warranty keyword + serial found → warranty inquiry")
                return ScenarioDetectionResult(
                    scenario_name="valid-warranty",  # Will be refined after API call
                    confidence=0.85,
                    is_warranty_inquiry=True,
                    detected_intent="warranty_check",
                    detection_method="heuristic",
                    ambiguous=False
                )
            else:
                logger.info("Heuristic: Warranty keyword but no serial → missing-info")
                return ScenarioDetectionResult(
                    scenario_name="missing-info",
                    confidence=0.9,
                    is_warranty_inquiry=True,
                    detected_intent="missing_information",
                    detection_method="heuristic",
                    ambiguous=False
                )

        # Default: Ambiguous case → low confidence, trigger LLM fallback
        # Covers: no warranty keyword, no serial, >20 chars, not spam
        logger.info("Heuristic: Ambiguous case → low confidence (will use LLM)")
        return ScenarioDetectionResult(
            scenario_name="valid-warranty",  # Tentative
            confidence=0.5,  # Low confidence triggers LLM
            is_warranty_inquiry=True,
            detected_intent="unknown",
            detection_method="heuristic",
            ambiguous=True
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def detect_with_llm(
        self,
        email: EmailMessage,
        serial_result: SerialExtractionResult
    ) -> ScenarioDetectionResult:
        """LLM-based scenario detection (fallback method).

        Uses Anthropic Claude with main instruction guidance to classify
        emails when heuristics are inconclusive.

        Args:
            email: Parsed email message
            serial_result: Serial number extraction result

        Returns:
            ScenarioDetectionResult with LLM detection

        Raises:
            LLMError: On LLM call failure after retries
        """
        logger.info("LLM detection: classifying email scenario")

        try:
            # Build system message
            system_message = (
                f"{self.main_instruction_body}\n\n"
                f"Classify this customer email into ONE of these categories:\n"
                f"1. valid_warranty_inquiry - Customer asking about warranty status with serial number\n"
                f"2. missing_information - Customer inquiry but missing serial number\n"
                f"3. out_of_scope - Not a warranty inquiry (billing, support, spam, etc.)\n\n"
                f"Respond with ONLY the category name (e.g., 'valid_warranty_inquiry')."
            )

            # Build user message
            user_message = (
                f"Customer email:\n"
                f"Subject: {email.subject}\n"
                f"From: {email.from_address}\n"
                f"Body: {email.body}\n\n"
                f"Serial number found: {serial_result.serial_number or 'None'}\n\n"
                f"Classify this email:"
            )

            # Call Anthropic API with timeout (NFR11: 15 seconds)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-3-5-sonnet-20241022",  # Pinned version
                    max_tokens=50,
                    temperature=0,  # Maximum determinism per NFR1
                    system=system_message,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                ),
                timeout=15  # NFR11: 15-second timeout
            )

            # Extract classification
            classification = response.content[0].text.strip().lower()

            logger.debug(f"LLM classification: {classification}")

            # Map LLM response to scenario
            if "valid_warranty" in classification:
                scenario_name = "valid-warranty"
                is_warranty = True
                intent = "warranty_check"
            elif "missing_information" in classification or "missing" in classification:
                scenario_name = "missing-info"
                is_warranty = True
                intent = "missing_information"
            elif "out_of_scope" in classification or "out" in classification:
                scenario_name = "out-of-scope"
                is_warranty = False
                intent = "non_warranty"
            else:
                # Ambiguous LLM response → graceful degradation
                logger.warning(f"LLM returned ambiguous classification: {classification}")
                scenario_name = "graceful-degradation"
                is_warranty = False
                intent = "unknown"

            logger.info(f"LLM detection: {scenario_name} (intent={intent})")

            return ScenarioDetectionResult(
                scenario_name=scenario_name,
                confidence=0.85,  # LLM confidence
                is_warranty_inquiry=is_warranty,
                detected_intent=intent,
                detection_method="llm",
                ambiguous=False
            )

        except asyncio.TimeoutError:
            raise LLMError(
                message="LLM scenario detection timeout (15s)",
                code="llm_scenario_detection_timeout",
                details={"timeout": 15}
            )
        except Exception as e:
            raise LLMError(
                message=f"LLM scenario detection failed: {str(e)}",
                code="llm_scenario_detection_failed",
                details={"error": str(e)}
            )

    async def detect_scenario(
        self,
        email: EmailMessage,
        serial_result: SerialExtractionResult
    ) -> ScenarioDetectionResult:
        """Detect email scenario (tries heuristics then LLM).

        Two-stage detection with graceful error handling:
        1. Heuristic detection (fast path)
        2. LLM detection (fallback if heuristic confidence < 0.8)

        Args:
            email: Parsed email message
            serial_result: Serial number extraction result

        Returns:
            ScenarioDetectionResult with detected scenario (never crashes)
        """
        logger.info(
            f"Detecting scenario for email: subject='{email.subject}'"
        )

        try:
            # Try heuristic detection first (fast path)
            heuristic_result = self.detect_with_heuristics(email, serial_result)

            # If high confidence, return immediately
            if heuristic_result.confidence >= 0.8:
                logger.info(
                    f"Scenario detected via heuristic: {heuristic_result.scenario_name} "
                    f"(confidence={heuristic_result.confidence})"
                )
                return heuristic_result

            # Low confidence heuristic → fallback to LLM
            logger.info("Heuristic confidence low, trying LLM detection")
            llm_result = await self.detect_with_llm(email, serial_result)

            logger.info(
                f"Scenario detected via LLM: {llm_result.scenario_name} "
                f"(confidence={llm_result.confidence})"
            )
            return llm_result

        except Exception as e:
            # Detection failure → graceful degradation (NFR5: no silent failures)
            logger.error(
                f"Scenario detection error: {str(e)} - using graceful-degradation",
                extra={
                    "subject": email.subject,
                    "from": email.from_address,
                    "error": str(e)
                },
                exc_info=True
            )

            return ScenarioDetectionResult(
                scenario_name="graceful-degradation",
                confidence=0.5,
                is_warranty_inquiry=False,
                detected_intent="error",
                detection_method="fallback",
                ambiguous=True
            )
