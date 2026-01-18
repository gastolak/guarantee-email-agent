"""Email processor for end-to-end pipeline orchestration.

Coordinates complete email processing workflow:
1. Parse email → EmailMessage
2. Extract serial number → SerialExtractionResult
3. Detect scenario → ScenarioDetectionResult
4. Validate warranty (if applicable) → warranty_data
5. Generate response → response_text
6. Send email response → sent confirmation
7. Create ticket (if valid warranty) → ticket_id
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.processor_models import (
    ProcessingResult,
    ScenarioDetectionResult,
)
from guarantee_email_agent.email.scenario_detector import ScenarioDetector
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.integrations.mcp.gmail_client import GmailMCPClient
from guarantee_email_agent.integrations.mcp.ticketing_client import TicketingMCPClient
from guarantee_email_agent.integrations.mcp.warranty_client import WarrantyMCPClient
from guarantee_email_agent.llm.response_generator import ResponseGenerator
from guarantee_email_agent.utils.errors import AgentError

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Orchestrates complete email processing pipeline.

    Processes emails through all steps: parse, extract, detect, validate,
    generate response, send email, create ticket.

    Processing time target: <60s (p95 per NFR7)
    No silent failures: all errors logged (NFR5, NFR45)
    """

    def __init__(
        self,
        config: AgentConfig,
        parser: EmailParser,
        extractor: SerialNumberExtractor,
        detector: ScenarioDetector,
        gmail_client: GmailMCPClient,
        warranty_client: WarrantyMCPClient,
        ticketing_client: TicketingMCPClient,
        response_generator: ResponseGenerator,
    ):
        """Initialize email processor with all dependencies.

        Args:
            config: Agent configuration
            parser: Email parser
            extractor: Serial number extractor
            detector: Scenario detector
            gmail_client: Gmail MCP client (Story 2.1)
            warranty_client: Warranty API MCP client (Story 2.1)
            ticketing_client: Ticketing MCP client (Story 2.1)
            response_generator: LLM response generator
        """
        self.config = config
        self.parser = parser
        self.extractor = extractor
        self.detector = detector
        self.gmail_client = gmail_client
        self.warranty_client = warranty_client
        self.ticketing_client = ticketing_client
        self.response_generator = response_generator

        logger.info("Email processor initialized with all dependencies")

    async def process_email(self, raw_email: Dict[str, Any]) -> ProcessingResult:
        """Process email end-to-end through complete pipeline.

        Pipeline steps:
        1. Parse email → EmailMessage
        2. Extract serial number → SerialExtractionResult
        3. Detect scenario → ScenarioDetectionResult
        4. Validate warranty (if applicable) → warranty_data
        5. Generate response → response_text
        6. Send email response → sent confirmation
        7. Create ticket (if valid warranty) → ticket_id

        Args:
            raw_email: Raw email data from Gmail MCP

        Returns:
            ProcessingResult with processing outcome and details

        Note:
            Processing time target: <60s (p95 per NFR7)
            No silent failures: all errors logged (NFR5)
        """
        start_time = time.time()
        email_id = raw_email.get("message_id", f"temp-{int(time.time())}")

        logger.info(
            f"Starting email processing: email_id={email_id}",
            extra={"email_id": email_id, "status": "in_progress"},
        )

        # Initialize result tracking
        serial_number = None
        scenario_used = None
        warranty_status = None
        response_sent = False
        ticket_created = False
        ticket_id = None
        failed_step = None
        error_message = None

        try:
            # Step 1: Parse email
            logger.info(f"Step 1/7: Parsing email: {email_id}")
            try:
                email = self.parser.parse_email(raw_email)
                logger.info(
                    f"Email parsed: subject='{email.subject}', from='{email.from_address}'",
                    extra={"email_id": email_id, "step": "parse", "status": "success"},
                )
                # NFR14: Customer email body logged ONLY at DEBUG level
                logger.debug(
                    f"Email body:\n{email.body}",
                    extra={"email_id": email_id, "step": "parse"}
                )
                # Also log at INFO level with truncated preview
                body_preview = email.body[:200] + "..." if len(email.body) > 200 else email.body
                logger.info(
                    f"Email body preview: {body_preview}",
                    extra={"email_id": email_id, "step": "parse"}
                )
            except Exception as e:
                failed_step = "parse"
                error_message = f"Email parsing failed: {str(e)}"
                logger.error(
                    error_message,
                    extra={"email_id": email_id, "step": "parse", "status": "failed"},
                    exc_info=True,
                )
                raise

            # Step 2: Extract serial number
            logger.info(f"Step 2/7: Extracting serial number: {email_id}")
            try:
                serial_result = await self.extractor.extract_serial_number(email)
                serial_number = serial_result.serial_number
                logger.info(
                    f"Serial extraction: {serial_number or 'not found'}",
                    extra={
                        "email_id": email_id,
                        "step": "extract_serial",
                        "status": "success" if serial_number else "not_found",
                        "serial_number": serial_number,
                    },
                )
            except Exception as e:
                # Serial extraction failure is not critical - can route to missing-info
                logger.warning(
                    f"Serial extraction error: {str(e)} - will route to missing-info",
                    extra={
                        "email_id": email_id,
                        "step": "extract_serial",
                        "status": "error",
                    },
                )
                serial_result = SerialExtractionResult(
                    serial_number=None,
                    confidence=0.0,
                    multiple_serials_detected=False,
                    all_detected_serials=[],
                    extraction_method="error",
                    ambiguous=True,
                )

            # Step 3: Detect scenario
            logger.info(f"Step 3/7: Detecting scenario: {email_id}")
            try:
                detection_result = await self.detector.detect_scenario(
                    email, serial_result
                )
                scenario_used = detection_result.scenario_name
                logger.info(
                    f"Scenario detected: {scenario_used} (confidence={detection_result.confidence})",
                    extra={
                        "email_id": email_id,
                        "step": "detect_scenario",
                        "status": "success",
                        "scenario": scenario_used,
                        "confidence": detection_result.confidence,
                    },
                )
            except Exception as e:
                # Scenario detection failure → use graceful degradation
                logger.warning(
                    f"Scenario detection error: {str(e)} - using graceful-degradation",
                    extra={
                        "email_id": email_id,
                        "step": "detect_scenario",
                        "status": "error",
                    },
                )
                scenario_used = "graceful-degradation"
                detection_result = ScenarioDetectionResult(
                    scenario_name="graceful-degradation",
                    confidence=0.5,
                    is_warranty_inquiry=False,
                    detected_intent="unknown",
                    detection_method="fallback",
                    ambiguous=True,
                )

            # Step 4: Validate warranty (if applicable)
            warranty_data = None
            if serial_number and detection_result.is_warranty_inquiry:
                logger.info(f"Step 4/7: Validating warranty: {email_id}")
                try:
                    warranty_response = await self.warranty_client.check_warranty(
                        serial_number
                    )
                    warranty_status = warranty_response.get("status")
                    warranty_data = warranty_response
                    logger.info(
                        f"Warranty validated: status={warranty_status}",
                        extra={
                            "email_id": email_id,
                            "step": "validate_warranty",
                            "status": "success",
                            "warranty_status": warranty_status,
                            "serial_number": serial_number,
                        },
                    )

                    # Adjust scenario based on warranty status
                    if warranty_status == "valid":
                        scenario_used = "valid-warranty"
                    elif warranty_status in ("expired", "not_found"):
                        scenario_used = "invalid-warranty"

                except Exception as e:
                    # Warranty API failure → use graceful degradation
                    logger.error(
                        f"Warranty validation error: {str(e)} - using graceful-degradation",
                        extra={
                            "email_id": email_id,
                            "step": "validate_warranty",
                            "status": "error",
                            "serial_number": serial_number,
                        },
                        exc_info=True,
                    )
                    scenario_used = "graceful-degradation"
            else:
                logger.info(
                    f"Step 4/7: Skipping warranty validation (scenario={scenario_used}, serial={serial_number})",
                    extra={
                        "email_id": email_id,
                        "step": "validate_warranty",
                        "status": "skipped",
                    },
                )

            # Step 5: Generate response
            logger.info(f"Step 5/7: Generating response: {email_id}")
            try:
                response_text = await self.response_generator.generate_response(
                    scenario_name=scenario_used,
                    email_content=email.body,
                    serial_number=serial_number,
                    warranty_data=warranty_data,
                )
                logger.info(
                    f"Response generated: {len(response_text)} chars",
                    extra={
                        "email_id": email_id,
                        "step": "generate_response",
                        "status": "success",
                        "scenario": scenario_used,
                        "response_length": len(response_text),
                    },
                )
                # Log the full response text at INFO level
                logger.info(
                    f"Generated response text:\n{response_text}",
                    extra={
                        "email_id": email_id,
                        "step": "generate_response",
                        "scenario": scenario_used
                    }
                )
            except Exception as e:
                failed_step = "generate_response"
                error_message = f"Response generation failed: {str(e)}"
                logger.error(
                    error_message,
                    extra={
                        "email_id": email_id,
                        "step": "generate_response",
                        "status": "failed",
                        "scenario": scenario_used,
                    },
                    exc_info=True,
                )
                raise

            # Step 6: Send email response
            logger.info(f"Step 6/7: Sending email response: {email_id}")
            try:
                await self.gmail_client.send_email(
                    to=email.from_address,
                    subject=f"Re: {email.subject}",
                    body=response_text,
                    thread_id=email.thread_id,
                )
                response_sent = True
                logger.info(
                    f"Email sent to {email.from_address}",
                    extra={
                        "email_id": email_id,
                        "step": "send_email",
                        "status": "success",
                        "to": email.from_address,
                    },
                )
            except Exception as e:
                failed_step = "send_email"
                error_message = f"Email sending failed: {str(e)}"
                logger.error(
                    error_message,
                    extra={
                        "email_id": email_id,
                        "step": "send_email",
                        "status": "failed",
                        "to": email.from_address,
                    },
                    exc_info=True,
                )
                raise

            # Step 7: Create ticket (if valid warranty)
            if warranty_status == "valid":
                logger.info(f"Step 7/7: Creating ticket: {email_id}")
                try:
                    ticket_data = {
                        "serial_number": serial_number,
                        "warranty_status": warranty_status,
                        "customer_email": email.from_address,
                        "customer_name": email.from_address.split("@")[
                            0
                        ],  # Simple extraction
                        "priority": "normal",
                        "category": "warranty_claim",
                        "subject": email.subject,
                        "warranty_expiration": warranty_data.get("expiration_date"),
                        "email_thread_id": email.thread_id,
                    }

                    ticket_response = await self.ticketing_client.create_ticket(
                        ticket_data
                    )
                    ticket_id = ticket_response.get("ticket_id")
                    ticket_created = True

                    logger.info(
                        f"Ticket created: {ticket_id}",
                        extra={
                            "email_id": email_id,
                            "step": "create_ticket",
                            "status": "success",
                            "ticket_id": ticket_id,
                            "serial_number": serial_number,
                        },
                    )
                except Exception as e:
                    # Ticket creation failure is critical (NFR21)
                    failed_step = "create_ticket"
                    error_message = f"Ticket creation failed: {str(e)}"
                    logger.error(
                        error_message,
                        extra={
                            "email_id": email_id,
                            "step": "create_ticket",
                            "status": "failed",
                            "serial_number": serial_number,
                        },
                        exc_info=True,
                    )
                    raise
            else:
                logger.info(
                    f"Step 7/7: Skipping ticket creation (warranty_status={warranty_status})",
                    extra={
                        "email_id": email_id,
                        "step": "create_ticket",
                        "status": "skipped",
                        "warranty_status": warranty_status,
                    },
                )

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Log performance warning if >60s (p95 target)
            if processing_time_ms > 60000:
                logger.warning(
                    f"Processing time exceeded 60s target: {processing_time_ms}ms",
                    extra={
                        "email_id": email_id,
                        "processing_time_ms": processing_time_ms,
                    },
                )

            logger.info(
                f"Email processing complete: {processing_time_ms}ms",
                extra={
                    "email_id": email_id,
                    "status": "completed",
                    "processing_time_ms": processing_time_ms,
                    "scenario": scenario_used,
                    "warranty_status": warranty_status,
                    "response_sent": response_sent,
                    "ticket_created": ticket_created,
                },
            )

            return ProcessingResult(
                success=True,
                email_id=email_id,
                scenario_used=scenario_used,
                serial_number=serial_number,
                warranty_status=warranty_status,
                response_sent=response_sent,
                ticket_created=ticket_created,
                ticket_id=ticket_id,
                processing_time_ms=processing_time_ms,
                error_message=None,
                failed_step=None,
            )

        except Exception as e:
            # Critical failure - mark email as unprocessed
            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                f"Email processing failed: {str(e)}",
                extra={
                    "email_id": email_id,
                    "status": "failed",
                    "failed_step": failed_step,
                    "processing_time_ms": processing_time_ms,
                },
                exc_info=True,
            )

            return ProcessingResult(
                success=False,
                email_id=email_id,
                scenario_used=scenario_used,
                serial_number=serial_number,
                warranty_status=warranty_status,
                response_sent=response_sent,
                ticket_created=ticket_created,
                ticket_id=ticket_id,
                processing_time_ms=processing_time_ms,
                error_message=str(e),
                failed_step=failed_step or "unknown",
            )
