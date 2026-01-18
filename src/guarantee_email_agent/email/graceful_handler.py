"""Graceful degradation handler for edge cases and failures.

Implements:
- FR18: Graceful degradation for out-of-scope cases
- NFR5: No silent failures (all errors logged)
- Never crashes on unexpected input
- Polite, helpful responses for all degradation scenarios
"""

import logging
from typing import List, Optional

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.email.processor_models import ProcessingResult
from guarantee_email_agent.llm.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


class GracefulDegradationHandler:
    """Handle edge cases and failures with graceful degradation.

    Provides graceful responses for:
    - Out-of-scope emails (billing, spam, non-warranty)
    - Missing information (no serial number, unclear intent)
    - API failures (LLM timeout, warranty API down, ticketing unavailable)
    - Edge cases (malformed emails, extraction failures, ambiguous scenarios)

    Never crashes - always returns ProcessingResult even when handler fails.
    """

    def __init__(self, config: AgentConfig, response_generator: ResponseGenerator):
        """Initialize graceful degradation handler.

        Args:
            config: Agent configuration
            response_generator: Response generator for degradation responses
        """
        self.config = config
        self.response_generator = response_generator
        logger.info("Graceful degradation handler initialized")

    async def handle_out_of_scope(
        self,
        email: EmailMessage,
        reason: str
    ) -> ProcessingResult:
        """Handle out-of-scope emails (non-warranty inquiries).

        Examples:
        - Billing inquiries
        - General support questions
        - Spam/junk emails
        - Unrelated topics

        Args:
            email: Email message
            reason: Reason for out-of-scope classification

        Returns:
            ProcessingResult with graceful degradation response

        Note:
            Uses graceful-degradation scenario instruction
        """
        logger.warning(
            f"Out-of-scope email handled: {reason}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "reason": reason,
                "degradation_type": "out_of_scope"
            }
        )

        try:
            # Generate graceful degradation response
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=True,  # Handled gracefully = success
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,  # Set by processor when actually sent
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,  # Set by processor
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Graceful degradation handler failed: {e}",
                extra={
                    "email_id": email.message_id,
                    "error": str(e),
                    "degradation_type": "out_of_scope"
                },
                exc_info=True
            )

            # Use fallback response if handler fails (never crash)
            return self._fallback_response(email, "out_of_scope")

    async def handle_missing_info(
        self,
        email: EmailMessage,
        missing: List[str]
    ) -> ProcessingResult:
        """Handle emails with missing required information.

        Examples:
        - No serial number provided
        - Unclear intent
        - Partial data

        Args:
            email: Email message
            missing: List of missing fields (e.g., ["serial_number"])

        Returns:
            ProcessingResult with missing-info response

        Note:
            Uses missing-info scenario instruction
        """
        logger.warning(
            f"Missing information handled: {', '.join(missing)}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "missing_fields": missing,
                "degradation_type": "missing_info"
            }
        )

        try:
            # Use missing-info scenario instruction
            response = await self.response_generator.generate_response(
                scenario_name="missing-info",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=True,  # Gracefully handled
                email_id=email.message_id or "unknown",
                scenario_used="missing-info",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Missing info handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "missing_info")

    async def handle_api_failure(
        self,
        email: EmailMessage,
        failed_api: str,
        error: str
    ) -> ProcessingResult:
        """Handle API failures (LLM, warranty API, ticketing).

        Examples:
        - LLM timeout (>15s)
        - Warranty API down/timeout
        - Ticketing system unavailable

        Args:
            email: Email message
            failed_api: Name of failed API (e.g., "warranty_api", "llm", "ticketing")
            error: Error message

        Returns:
            ProcessingResult with graceful degradation

        Note:
            success=False because API failure is a true failure,
            but we still send a graceful response
        """
        logger.error(
            f"API failure handled: {failed_api}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "failed_api": failed_api,
                "error": error,
                "degradation_type": "api_failure"
            },
            exc_info=False  # Error already captured
        )

        try:
            # Generate apology response
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=False,  # API failure is a failure
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=f"API failure: {failed_api} - {error}",
                failed_step=failed_api
            )

        except Exception as e:
            logger.error(
                f"API failure handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "api_failure")

    async def handle_edge_case(
        self,
        email: EmailMessage,
        issue: str
    ) -> ProcessingResult:
        """Handle edge cases (malformed emails, extraction failures).

        Examples:
        - Malformed email structure
        - Encoding issues
        - Extraction failures
        - Parsing errors

        Args:
            email: Email message
            issue: Description of edge case

        Returns:
            ProcessingResult with graceful degradation
        """
        logger.warning(
            f"Edge case handled: {issue}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "issue": issue,
                "degradation_type": "edge_case"
            }
        )

        try:
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body if email.body else "",
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=True,  # Gracefully handled
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Edge case handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "edge_case")

    async def handle_ambiguous(
        self,
        email: EmailMessage,
        scenarios: List[str]
    ) -> ProcessingResult:
        """Handle ambiguous scenarios (multiple possibilities).

        When multiple scenarios could apply and confidence is low.

        Args:
            email: Email message
            scenarios: List of possible scenarios

        Returns:
            ProcessingResult with clarification request
        """
        logger.warning(
            f"Ambiguous scenario handled: {', '.join(scenarios)}",
            extra={
                "email_id": email.message_id,
                "subject": email.subject,
                "from": email.from_address,
                "possible_scenarios": scenarios,
                "degradation_type": "ambiguous"
            }
        )

        try:
            response = await self.response_generator.generate_response(
                scenario_name="graceful-degradation",
                email_content=email.body,
                serial_number=None,
                warranty_data=None
            )

            return ProcessingResult(
                success=True,  # Gracefully handled
                email_id=email.message_id or "unknown",
                scenario_used="graceful-degradation",
                serial_number=None,
                warranty_status=None,
                response_sent=False,
                ticket_created=False,
                ticket_id=None,
                processing_time_ms=0,
                error_message=None,
                failed_step=None
            )

        except Exception as e:
            logger.error(
                f"Ambiguous scenario handler failed: {e}",
                extra={"email_id": email.message_id, "error": str(e)},
                exc_info=True
            )
            return self._fallback_response(email, "ambiguous")

    def _fallback_response(
        self,
        email: EmailMessage,
        degradation_type: str
    ) -> ProcessingResult:
        """Fallback response when degradation handler fails.

        This is the last line of defense - NEVER raise exceptions.
        Ensures agent never crashes on unexpected input (FR18, NFR5).

        Args:
            email: Email message
            degradation_type: Type of degradation that failed

        Returns:
            ProcessingResult with fallback handling
        """
        logger.error(
            f"Using fallback response for {degradation_type}",
            extra={
                "email_id": email.message_id,
                "degradation_type": degradation_type
            }
        )

        # Return minimal ProcessingResult
        # Actual fallback response template would be handled by processor
        # E.g., "We received your email. Our team will review and respond."
        return ProcessingResult(
            success=False,
            email_id=email.message_id or "unknown",
            scenario_used="fallback",
            serial_number=None,
            warranty_status=None,
            response_sent=False,
            ticket_created=False,
            ticket_id=None,
            processing_time_ms=0,
            error_message=f"Degradation handler failed: {degradation_type}",
            failed_step="graceful_degradation"
        )
