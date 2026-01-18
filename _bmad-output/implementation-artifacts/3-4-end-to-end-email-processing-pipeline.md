# Story 3.4: End-to-End Email Processing Pipeline

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want to process warranty emails end-to-end from inbox monitoring through response sending,
So that customers receive automated warranty status responses without manual intervention.

## Acceptance Criteria

**Given** All previous Epic 3 stories complete and MCP integrations from Epic 2 available
**When** The agent processes warranty emails

**Then - Scenario Detection:**
**And** Scenario detector in `src/guarantee_email_agent/email/scenario_detector.py` uses LLM
**And** Detection identifies: valid inquiry, invalid/expired, missing serial, out-of-scope
**And** Scenario classification logged with scenario name
**And** Detector triggers scenario instruction router from Story 3.2
**And** Ambiguous scenarios default to graceful-degradation
**And** Detection happens before warranty API calls to optimize API usage
**And** Detection results include confidence score for monitoring
**And** Handles edge cases: empty emails, spam, non-warranty inquiries

**Then - Complete Processing Pipeline:**
**And** Email processor in `src/guarantee_email_agent/email/processor.py` orchestrates pipeline
**And** Pipeline: monitor inbox → parse → extract serial → detect scenario → validate warranty → generate response → send email → create ticket (if valid)
**And** Each email processed independently and asynchronously
**And** Processing completes within 60 seconds (NFR7 - 95th percentile)
**And** Uses warranty API client to validate serial numbers
**And** Warranty results (valid, expired, not_found) determine response content
**And** Uses LLM response generator to draft contextually appropriate responses
**And** Responses sent via Gmail MCP client
**And** For valid warranties, tickets created via ticketing MCP client
**And** Ticket creation includes: serial_number, warranty_status, customer details, priority
**And** Each step logs progress with email ID and processing status
**And** Failed steps logged with sufficient detail (FR44, NFR25)
**And** Emails marked unprocessed if critical steps fail (FR45, NFR5)

## Tasks / Subtasks

### Processing Result Data Structures

- [ ] Create ProcessingResult dataclass (AC: emails marked unprocessed if critical steps fail)
  - [ ] Create `src/guarantee_email_agent/email/processor_models.py`
  - [ ] Define `ProcessingResult` dataclass with @dataclass decorator
  - [ ] Fields: success (bool), email_id (str), scenario_used (str)
  - [ ] Field: serial_number (Optional[str])
  - [ ] Field: warranty_status (Optional[str]) - "valid", "expired", "not_found"
  - [ ] Field: response_sent (bool), ticket_created (bool)
  - [ ] Field: ticket_id (Optional[str])
  - [ ] Field: processing_time_ms (int) for performance monitoring
  - [ ] Field: error_message (Optional[str]) if failed
  - [ ] Field: failed_step (Optional[str]) for debugging
  - [ ] Add helper method: is_successful() -> bool
  - [ ] Add helper method: requires_retry() -> bool

- [ ] Create ScenarioDetectionResult dataclass (AC: detection includes confidence score)
  - [ ] Define `ScenarioDetectionResult` in processor_models.py
  - [ ] Fields: scenario_name (str), confidence (float 0.0-1.0)
  - [ ] Field: is_warranty_inquiry (bool)
  - [ ] Field: detected_intent (str) - "warranty_check", "non_warranty", "spam"
  - [ ] Field: detection_method (str) - "llm" or "heuristic"
  - [ ] Field: ambiguous (bool) for graceful degradation flag
  - [ ] Add helper method: should_process() -> bool
  - [ ] Add helper method: get_scenario_for_routing() -> str

### Scenario Detection

- [ ] Create scenario detector module (AC: detector uses LLM)
  - [ ] Create `src/guarantee_email_agent/email/scenario_detector.py`
  - [ ] Import EmailMessage and SerialExtractionResult from models
  - [ ] Import ScenarioDetectionResult from processor_models
  - [ ] Import Anthropic SDK for LLM calls
  - [ ] Import tenacity for retry logic
  - [ ] Create `ScenarioDetector` class
  - [ ] Initialize with config and main instruction
  - [ ] Store reference to Anthropic client

- [ ] Implement heuristic-based detection (fast path) (AC: optimizes API usage)
  - [ ] Create `detect_with_heuristics(email: EmailMessage, serial_result: SerialExtractionResult) -> ScenarioDetectionResult`
  - [ ] If serial_result.serial_number is None → "missing-info" scenario
  - [ ] If email.subject contains "warranty" → likely warranty inquiry
  - [ ] If email.body is very short (<20 chars) → potentially spam/invalid
  - [ ] If common spam keywords detected → "out-of-scope"
  - [ ] Return ScenarioDetectionResult with detection_method="heuristic"
  - [ ] High confidence (0.9) if clear heuristic match
  - [ ] Low confidence (0.5) if ambiguous → fallback to LLM

- [ ] Implement LLM-based detection (fallback) (AC: identifies all scenario types)
  - [ ] Create `detect_with_llm(email: EmailMessage, serial_result: SerialExtractionResult) -> ScenarioDetectionResult` async method
  - [ ] Build system message from main instruction + scenario detection guidance
  - [ ] Prompt: "Classify this email as: valid_warranty_inquiry, invalid_warranty_inquiry, missing_information, out_of_scope, spam"
  - [ ] Include email content and serial extraction result in user message
  - [ ] Call Anthropic API with temperature=0, claude-sonnet-4-5
  - [ ] Parse LLM response for scenario classification
  - [ ] Apply 15-second timeout
  - [ ] Return ScenarioDetectionResult with confidence from LLM

- [ ] Implement main detection method (AC: detector identifies scenarios)
  - [ ] Create `detect_scenario(email: EmailMessage, serial_result: SerialExtractionResult) -> ScenarioDetectionResult` async method
  - [ ] Try heuristic detection first (fast path)
  - [ ] If heuristic confidence >= 0.8, return immediately
  - [ ] If heuristic confidence < 0.8, fallback to LLM detection
  - [ ] Log which detection method was used
  - [ ] Return ScenarioDetectionResult with scenario_name for routing
  - [ ] Handle detection errors gracefully (default to graceful-degradation)

- [ ] Handle edge cases (AC: handles empty emails, spam, non-warranty)
  - [ ] Empty email body → "out-of-scope" with low confidence
  - [ ] Very short emails (<20 chars) → potential spam, use LLM to verify
  - [ ] Common spam patterns → "out-of-scope" immediately
  - [ ] Non-warranty inquiries (billing, support) → "out-of-scope"
  - [ ] Ambiguous cases → set ambiguous=True, use graceful-degradation
  - [ ] Log edge case handling clearly

- [ ] Implement ambiguous scenario handling (AC: defaults to graceful-degradation)
  - [ ] If LLM detection confidence < 0.6 → set ambiguous=True
  - [ ] If multiple scenarios could apply → set ambiguous=True
  - [ ] If detection fails after retries → graceful-degradation
  - [ ] Log: "Ambiguous scenario detection, using graceful-degradation"
  - [ ] Return scenario_name="graceful-degradation"
  - [ ] Include original detection attempt in logs

- [ ] Add scenario detection logging (AC: classification logged with scenario name)
  - [ ] Log at INFO level: "Scenario detected: {scenario_name} (confidence={confidence})"
  - [ ] Include detection method (heuristic or llm)
  - [ ] Include email subject for context (not body per NFR14)
  - [ ] Log at DEBUG level: full detection reasoning
  - [ ] Use structured logging with extra dict
  - [ ] Include serial number if found

- [ ] Optimize API usage (AC: detection before warranty API calls)
  - [ ] Detect scenario BEFORE calling warranty API
  - [ ] If scenario is "missing-info" or "out-of-scope" → skip warranty API call
  - [ ] Only call warranty API for "valid_warranty_inquiry" scenarios
  - [ ] Log API call savings: "Skipped warranty API call for {scenario}"
  - [ ] Track API usage in metrics for optimization

### Email Processing Pipeline Orchestrator

- [ ] Create email processor module (AC: orchestrates complete pipeline)
  - [ ] Create `src/guarantee_email_agent/email/processor.py`
  - [ ] Import all components: EmailParser, SerialNumberExtractor, ScenarioDetector
  - [ ] Import MCP clients: GmailClient, WarrantyAPIClient, TicketingClient
  - [ ] Import ResponseGenerator from Story 3.2
  - [ ] Create `EmailProcessor` class
  - [ ] Initialize with config and all dependencies (DI pattern)
  - [ ] Store references to all clients and processors

- [ ] Implement main processing method (AC: pipeline monitors inbox → sends email)
  - [ ] Create `process_email(raw_email: Dict[str, Any]) -> ProcessingResult` async method
  - [ ] Start timer for processing time tracking (NFR7)
  - [ ] Step 1: Parse email using EmailParser
  - [ ] Step 2: Extract serial number using SerialNumberExtractor
  - [ ] Step 3: Detect scenario using ScenarioDetector
  - [ ] Step 4: Validate warranty (if applicable scenario)
  - [ ] Step 5: Generate response using ResponseGenerator
  - [ ] Step 6: Send email response via Gmail MCP
  - [ ] Step 7: Create ticket (if valid warranty)
  - [ ] Stop timer and calculate processing_time_ms
  - [ ] Return ProcessingResult with all details

- [ ] Implement email parsing step (AC: pipeline parses emails)
  - [ ] Call parser.parse_email(raw_email)
  - [ ] Catch EmailParseError and handle gracefully
  - [ ] If parsing fails, log error and return failed ProcessingResult
  - [ ] Include failed_step="parse" in result
  - [ ] Log: "Email parsing step: success/failed"
  - [ ] Continue to next step if successful

- [ ] Implement serial extraction step (AC: pipeline extracts serial)
  - [ ] Call extractor.extract_serial_number(email_message) async
  - [ ] Handle SerialExtractionResult
  - [ ] If extraction fails (None), continue (will route to missing-info)
  - [ ] If extraction errors, catch and log but continue
  - [ ] Log: "Serial extraction step: {result.serial_number or 'not found'}"
  - [ ] Store result for scenario detection

- [ ] Implement scenario detection step (AC: pipeline detects scenario)
  - [ ] Call detector.detect_scenario(email, serial_result) async
  - [ ] Get scenario_name from ScenarioDetectionResult
  - [ ] Log: "Scenario detection step: {scenario_name} (confidence={confidence})"
  - [ ] Store scenario for response generation
  - [ ] Handle detection errors gracefully (default to graceful-degradation)

- [ ] Implement warranty validation step (AC: uses warranty API client)
  - [ ] Check if scenario requires warranty validation
  - [ ] Skip if scenario is "missing-info", "out-of-scope", "spam"
  - [ ] Only call warranty API if serial_number exists and scenario is warranty-related
  - [ ] Call warranty_client.check_warranty(serial_number) async
  - [ ] Parse warranty response: status (valid, expired, not_found), expiration_date
  - [ ] Log: "Warranty validation step: status={status}, expiration={date}"
  - [ ] Handle warranty API errors with retry logic
  - [ ] If warranty API fails after retries, use graceful-degradation scenario

- [ ] Implement response generation step (AC: drafts contextually appropriate responses)
  - [ ] Determine final scenario based on warranty validation result
  - [ ] If warranty status is "valid" → use "valid-warranty" scenario
  - [ ] If warranty status is "expired" → use "invalid-warranty" scenario
  - [ ] If warranty status is "not_found" → use "invalid-warranty" scenario
  - [ ] Call response_generator.generate_response(scenario, email, serial, warranty_data) async
  - [ ] Log: "Response generation step: {len(response)} chars generated"
  - [ ] Handle LLM errors with retry logic
  - [ ] If generation fails, use fallback template response

- [ ] Implement email sending step (AC: responses sent via Gmail MCP)
  - [ ] Prepare email response data: to, subject, body
  - [ ] Reply to original email (preserve thread_id if available)
  - [ ] Subject: "Re: {original_subject}"
  - [ ] Call gmail_client.send_email(to, subject, body, thread_id) async
  - [ ] Verify email sent successfully
  - [ ] Log: "Email sending step: sent to {to}"
  - [ ] Handle send errors with retry logic
  - [ ] If send fails after retries, mark processing as failed

- [ ] Implement ticket creation step (AC: tickets created for valid warranties)
  - [ ] Check if warranty status is "valid"
  - [ ] Skip ticket creation for invalid/expired/missing warranties
  - [ ] Prepare ticket data: serial_number, warranty_status, customer_email, priority, category
  - [ ] Set priority based on warranty urgency (normal for most cases)
  - [ ] Set category: "warranty_claim"
  - [ ] Call ticketing_client.create_ticket(ticket_data) async
  - [ ] Get ticket_id from response
  - [ ] Log: "Ticket creation step: ticket_id={ticket_id}"
  - [ ] Handle ticket creation errors with retry logic

- [ ] Implement independent async processing (AC: emails processed independently and asynchronously)
  - [ ] Each email processed in separate async task
  - [ ] Use asyncio.create_task() for concurrent processing
  - [ ] Ensure no shared state between email processing
  - [ ] Each ProcessingResult is independent
  - [ ] Log processing start/end for each email
  - [ ] Support concurrent processing when volume >1 email/min (NFR10)

- [ ] Implement performance tracking (AC: processing completes within 60 seconds)
  - [ ] Start timer at beginning of process_email()
  - [ ] Track time for each processing step
  - [ ] Calculate total processing_time_ms
  - [ ] Log if processing exceeds 60 seconds (p95 target per NFR7)
  - [ ] Include processing time in ProcessingResult
  - [ ] Log: "Email processing complete: {processing_time_ms}ms"
  - [ ] Track p95 latency for monitoring

- [ ] Implement comprehensive logging (AC: each step logs progress)
  - [ ] Log at INFO level for each major step
  - [ ] Include email_id (message_id or generated ID) in all logs
  - [ ] Include processing status: "in_progress", "completed", "failed"
  - [ ] Log format: "Step {step_name}: {status} - {details}"
  - [ ] Use structured logging with extra dict
  - [ ] Include serial_number and scenario in context
  - [ ] Log sufficient detail for troubleshooting (NFR25)

- [ ] Implement error handling and failure marking (AC: failed steps logged, emails marked unprocessed)
  - [ ] Catch exceptions at each processing step
  - [ ] Log errors with full context (step, email_id, error message)
  - [ ] Determine if error is retryable or fatal
  - [ ] Mark email as "unprocessed" if critical step fails
  - [ ] Include failed_step and error_message in ProcessingResult
  - [ ] Don't crash on individual email failures (continue processing others)
  - [ ] Log at ERROR level with exc_info=True for stack traces
  - [ ] Ensure no silent failures (NFR5, FR45)

### Pipeline Integration Points

- [ ] Integrate with Gmail MCP client (AC: monitors inbox, sends responses)
  - [ ] Import GmailClient from integrations/gmail.py (Story 2.1)
  - [ ] Use gmail_client.monitor_inbox() to get new emails
  - [ ] Pass raw email data to process_email()
  - [ ] Use gmail_client.send_email() to send responses
  - [ ] Handle Gmail API rate limiting gracefully
  - [ ] Verify emails marked as processed after successful handling

- [ ] Integrate with Warranty API MCP client (AC: validates serial numbers)
  - [ ] Import WarrantyAPIClient from integrations/warranty_api.py (Story 2.1)
  - [ ] Call warranty_client.check_warranty(serial_number)
  - [ ] Parse warranty API response
  - [ ] Handle warranty API errors with circuit breaker
  - [ ] Log warranty validation results
  - [ ] Skip warranty call for non-warranty scenarios (optimization)

- [ ] Integrate with Ticketing MCP client (AC: creates tickets for valid warranties)
  - [ ] Import TicketingClient from integrations/ticketing.py (Story 2.1)
  - [ ] Call ticketing_client.create_ticket(ticket_data)
  - [ ] Verify ticket creation success (NFR21)
  - [ ] Include ticket_id in email response
  - [ ] Handle ticketing API errors with retry
  - [ ] Only create tickets for valid warranty status

- [ ] Integrate with Response Generator (AC: generates contextually appropriate responses)
  - [ ] Import ResponseGenerator from llm/response_generator.py (Story 3.2)
  - [ ] Pass scenario_name, email, serial, warranty_data
  - [ ] Get generated response text
  - [ ] Use response as email body for sending
  - [ ] Handle LLM generation errors gracefully

- [ ] Integrate with Scenario Router (AC: triggers scenario instruction router)
  - [ ] ScenarioDetector returns scenario_name
  - [ ] ResponseGenerator uses ScenarioRouter internally (Story 3.2)
  - [ ] Scenario routing happens automatically in response generation
  - [ ] Log scenario routing decisions
  - [ ] Fallback to graceful-degradation if scenario not found

### Processing Workflow Coordination

- [ ] Create high-level email processing workflow (AC: complete end-to-end pipeline)
  - [ ] Create `process_email_workflow(raw_email: Dict) -> ProcessingResult` method
  - [ ] Orchestrate all steps in correct order
  - [ ] Handle errors at each step gracefully
  - [ ] Ensure each step completes before next step
  - [ ] Log workflow progress clearly
  - [ ] Return comprehensive ProcessingResult

- [ ] Implement conditional workflow logic (AC: warranty results determine response content)
  - [ ] If serial not found → skip warranty validation, use missing-info scenario
  - [ ] If scenario is out-of-scope → skip warranty validation, use graceful-degradation
  - [ ] If warranty validation fails → use graceful-degradation scenario
  - [ ] If warranty valid → create ticket + send confirmation
  - [ ] If warranty expired → send empathetic response, no ticket
  - [ ] Document decision tree in code comments

- [ ] Implement retry strategies for transient failures
  - [ ] Apply retry logic to all MCP calls (inherited from Story 2.1)
  - [ ] Apply retry logic to LLM calls (inherited from Stories 3.1, 3.2)
  - [ ] Max 3 retries with exponential backoff
  - [ ] Distinguish transient vs permanent errors
  - [ ] Log retry attempts at WARN level
  - [ ] After retries exhausted, mark step as failed

### Email Processor Module Initialization

- [ ] Create email processor factory (AC: processor orchestrates pipeline)
  - [ ] Create factory function: `create_email_processor(config: AgentConfig) -> EmailProcessor`
  - [ ] Initialize all dependencies: parser, extractor, detector, clients, generator
  - [ ] Inject dependencies into EmailProcessor
  - [ ] Validate all dependencies initialized correctly
  - [ ] Return configured EmailProcessor instance
  - [ ] Log: "Email processor initialized with all dependencies"

- [ ] Update email module exports
  - [ ] Update `src/guarantee_email_agent/email/__init__.py`
  - [ ] Export EmailProcessor, ProcessingResult
  - [ ] Export ScenarioDetector, ScenarioDetectionResult
  - [ ] Export create_email_processor factory
  - [ ] Provide clean public API for email processing

### Testing

- [ ] Create scenario detector tests
  - [ ] Create `tests/email/test_scenario_detector.py`
  - [ ] Test heuristic detection with clear cases
  - [ ] Test LLM detection (mock Anthropic API)
  - [ ] Test all scenario types: valid, invalid, missing, out-of-scope
  - [ ] Test edge cases: empty emails, spam, ambiguous
  - [ ] Test confidence scoring
  - [ ] Test graceful degradation fallback
  - [ ] Use pytest fixtures for test emails

- [ ] Create email processor tests
  - [ ] Create `tests/email/test_processor.py`
  - [ ] Test complete pipeline with successful processing
  - [ ] Test each step individually (parse, extract, detect, validate, generate, send, ticket)
  - [ ] Test error handling at each step
  - [ ] Test conditional logic (valid vs invalid warranty)
  - [ ] Test retry logic on transient failures
  - [ ] Test performance tracking (processing time)
  - [ ] Mock all external dependencies (MCP clients, LLM)

- [ ] Create pipeline integration tests
  - [ ] Create `tests/email/test_pipeline_integration.py`
  - [ ] Test end-to-end: raw email → ProcessingResult
  - [ ] Test valid warranty flow: parse → extract → detect → validate → respond → ticket
  - [ ] Test invalid warranty flow: parse → extract → detect → validate → respond (no ticket)
  - [ ] Test missing serial flow: parse → extract (fail) → detect (missing-info) → respond
  - [ ] Test out-of-scope flow: parse → detect (spam) → respond
  - [ ] Mock all MCP servers and LLM API
  - [ ] Verify processing time within 60s target

- [ ] Create performance tests
  - [ ] Test processing time for various email types
  - [ ] Verify p95 latency < 60 seconds (NFR7)
  - [ ] Test concurrent email processing (NFR10)
  - [ ] Test with high volume (>1 email/min)
  - [ ] Measure time for each processing step
  - [ ] Identify bottlenecks for optimization

- [ ] Create error handling tests
  - [ ] Test handling of parsing errors
  - [ ] Test handling of extraction errors
  - [ ] Test handling of warranty API errors
  - [ ] Test handling of LLM errors
  - [ ] Test handling of email sending errors
  - [ ] Test handling of ticket creation errors
  - [ ] Verify no silent failures (all errors logged)
  - [ ] Verify emails marked unprocessed on critical failures

## Dev Notes

### Architecture Context

This story implements **End-to-End Email Processing Pipeline** (consolidates old stories 4.3 and 4.4), bringing together all Epic 3 components into a cohesive workflow. This is the heart of the agent's automation capability.

**Key Architectural Principles:**
- FR2-5: Complete email analysis workflow
- FR6-9: Warranty validation integration
- FR15-18: Contextual response generation
- FR19-21: Automated ticket creation
- FR44: Failed steps logged with sufficient detail
- FR45: Emails marked unprocessed if critical steps fail
- NFR5: No silent failures
- NFR7: 60-second processing time (p95)
- NFR10: Concurrent processing above 1 email/min
- NFR25: Logs include sufficient context for troubleshooting

### Critical Implementation Rules from Project Context

**Pipeline Orchestration Pattern:**

The email processor coordinates all components into a cohesive workflow:

```python
# src/guarantee_email_agent/email/processor.py
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.email.scenario_detector import ScenarioDetector
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.email.processor_models import ProcessingResult, ScenarioDetectionResult
from guarantee_email_agent.integrations.gmail import GmailClient
from guarantee_email_agent.integrations.warranty_api import WarrantyAPIClient
from guarantee_email_agent.integrations.ticketing import TicketingClient
from guarantee_email_agent.llm.response_generator import ResponseGenerator
from guarantee_email_agent.utils.errors import AgentError

logger = logging.getLogger(__name__)

class EmailProcessor:
    """Orchestrates complete email processing pipeline"""

    def __init__(
        self,
        config: AgentConfig,
        parser: EmailParser,
        extractor: SerialNumberExtractor,
        detector: ScenarioDetector,
        gmail_client: GmailClient,
        warranty_client: WarrantyAPIClient,
        ticketing_client: TicketingClient,
        response_generator: ResponseGenerator
    ):
        """Initialize email processor with all dependencies

        Args:
            config: Agent configuration
            parser: Email parser
            extractor: Serial number extractor
            detector: Scenario detector
            gmail_client: Gmail MCP client
            warranty_client: Warranty API MCP client
            ticketing_client: Ticketing MCP client
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
        """Process email end-to-end through complete pipeline

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
        email_id = raw_email.get('message_id', f"temp-{int(time.time())}")

        logger.info(
            f"Starting email processing: email_id={email_id}",
            extra={"email_id": email_id, "status": "in_progress"}
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
                    extra={"email_id": email_id, "step": "parse", "status": "success"}
                )
            except Exception as e:
                failed_step = "parse"
                error_message = f"Email parsing failed: {str(e)}"
                logger.error(
                    error_message,
                    extra={"email_id": email_id, "step": "parse", "status": "failed"},
                    exc_info=True
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
                        "serial_number": serial_number
                    }
                )
            except Exception as e:
                # Serial extraction failure is not critical - can route to missing-info
                logger.warning(
                    f"Serial extraction error: {str(e)} - will route to missing-info",
                    extra={"email_id": email_id, "step": "extract_serial", "status": "error"}
                )
                serial_result = SerialExtractionResult(
                    serial_number=None,
                    confidence=0.0,
                    multiple_serials_detected=False,
                    all_detected_serials=[],
                    extraction_method="error",
                    ambiguous=True
                )

            # Step 3: Detect scenario
            logger.info(f"Step 3/7: Detecting scenario: {email_id}")
            try:
                detection_result = await self.detector.detect_scenario(email, serial_result)
                scenario_used = detection_result.scenario_name
                logger.info(
                    f"Scenario detected: {scenario_used} (confidence={detection_result.confidence})",
                    extra={
                        "email_id": email_id,
                        "step": "detect_scenario",
                        "status": "success",
                        "scenario": scenario_used,
                        "confidence": detection_result.confidence
                    }
                )
            except Exception as e:
                # Scenario detection failure → use graceful degradation
                logger.warning(
                    f"Scenario detection error: {str(e)} - using graceful-degradation",
                    extra={"email_id": email_id, "step": "detect_scenario", "status": "error"}
                )
                scenario_used = "graceful-degradation"
                detection_result = ScenarioDetectionResult(
                    scenario_name="graceful-degradation",
                    confidence=0.5,
                    is_warranty_inquiry=False,
                    detected_intent="unknown",
                    detection_method="fallback",
                    ambiguous=True
                )

            # Step 4: Validate warranty (if applicable)
            warranty_data = None
            if serial_number and detection_result.is_warranty_inquiry:
                logger.info(f"Step 4/7: Validating warranty: {email_id}")
                try:
                    warranty_response = await self.warranty_client.check_warranty(serial_number)
                    warranty_status = warranty_response.get('status')
                    warranty_data = warranty_response
                    logger.info(
                        f"Warranty validated: status={warranty_status}",
                        extra={
                            "email_id": email_id,
                            "step": "validate_warranty",
                            "status": "success",
                            "warranty_status": warranty_status,
                            "serial_number": serial_number
                        }
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
                            "serial_number": serial_number
                        },
                        exc_info=True
                    )
                    scenario_used = "graceful-degradation"
            else:
                logger.info(
                    f"Step 4/7: Skipping warranty validation (scenario={scenario_used}, serial={serial_number})",
                    extra={"email_id": email_id, "step": "validate_warranty", "status": "skipped"}
                )

            # Step 5: Generate response
            logger.info(f"Step 5/7: Generating response: {email_id}")
            try:
                response_text = await self.response_generator.generate_response(
                    scenario_name=scenario_used,
                    email_content=email.body,
                    serial_number=serial_number,
                    warranty_data=warranty_data
                )
                logger.info(
                    f"Response generated: {len(response_text)} chars",
                    extra={
                        "email_id": email_id,
                        "step": "generate_response",
                        "status": "success",
                        "scenario": scenario_used,
                        "response_length": len(response_text)
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
                        "scenario": scenario_used
                    },
                    exc_info=True
                )
                raise

            # Step 6: Send email response
            logger.info(f"Step 6/7: Sending email response: {email_id}")
            try:
                await self.gmail_client.send_email(
                    to=email.from_address,
                    subject=f"Re: {email.subject}",
                    body=response_text,
                    thread_id=email.thread_id
                )
                response_sent = True
                logger.info(
                    f"Email sent to {email.from_address}",
                    extra={
                        "email_id": email_id,
                        "step": "send_email",
                        "status": "success",
                        "to": email.from_address
                    }
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
                        "to": email.from_address
                    },
                    exc_info=True
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
                        "customer_name": email.from_address.split('@')[0],  # Simple extraction
                        "priority": "normal",
                        "category": "warranty_claim",
                        "subject": email.subject,
                        "warranty_expiration": warranty_data.get('expiration_date'),
                        "email_thread_id": email.thread_id
                    }

                    ticket_response = await self.ticketing_client.create_ticket(ticket_data)
                    ticket_id = ticket_response.get('ticket_id')
                    ticket_created = True

                    logger.info(
                        f"Ticket created: {ticket_id}",
                        extra={
                            "email_id": email_id,
                            "step": "create_ticket",
                            "status": "success",
                            "ticket_id": ticket_id,
                            "serial_number": serial_number
                        }
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
                            "serial_number": serial_number
                        },
                        exc_info=True
                    )
                    raise
            else:
                logger.info(
                    f"Step 7/7: Skipping ticket creation (warranty_status={warranty_status})",
                    extra={
                        "email_id": email_id,
                        "step": "create_ticket",
                        "status": "skipped",
                        "warranty_status": warranty_status
                    }
                )

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Log performance warning if >60s (p95 target)
            if processing_time_ms > 60000:
                logger.warning(
                    f"Processing time exceeded 60s target: {processing_time_ms}ms",
                    extra={"email_id": email_id, "processing_time_ms": processing_time_ms}
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
                    "ticket_created": ticket_created
                }
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
                failed_step=None
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
                    "processing_time_ms": processing_time_ms
                },
                exc_info=True
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
                failed_step=failed_step or "unknown"
            )
```

**Scenario Detector Implementation Pattern:**

```python
# src/guarantee_email_agent/email/scenario_detector.py
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

# Spam/junk keywords
SPAM_KEYWORDS = [
    'unsubscribe', 'viagra', 'casino', 'lottery', 'click here',
    'free money', 'congratulations you won'
]

class ScenarioDetector:
    """Detect warranty inquiry scenarios using heuristics and LLM fallback"""

    def __init__(self, config: AgentConfig, main_instruction_body: str):
        """Initialize scenario detector

        Args:
            config: Agent configuration
            main_instruction_body: Main instruction for LLM guidance
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
        """Fast heuristic-based scenario detection

        Args:
            email: Parsed email message
            serial_result: Serial number extraction result

        Returns:
            ScenarioDetectionResult with heuristic detection
        """
        # Heuristic 1: No serial found → missing-info
        if not serial_result.is_successful():
            logger.info("Heuristic: No serial found → missing-info scenario")
            return ScenarioDetectionResult(
                scenario_name="missing-info",
                confidence=0.9,
                is_warranty_inquiry=True,
                detected_intent="missing_information",
                detection_method="heuristic",
                ambiguous=False
            )

        # Heuristic 2: Spam detection
        email_text = f"{email.subject} {email.body}".lower()
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

        # Heuristic 3: Very short email (likely spam or incomplete)
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

        # Heuristic 4: "warranty" keyword present with serial → warranty inquiry
        if re.search(r'\bwarranty\b', email_text, re.IGNORECASE):
            logger.info("Heuristic: Warranty keyword + serial found → warranty inquiry")
            return ScenarioDetectionResult(
                scenario_name="valid-warranty",  # Will be refined after API call
                confidence=0.85,
                is_warranty_inquiry=True,
                detected_intent="warranty_check",
                detection_method="heuristic",
                ambiguous=False
            )

        # Default: Low confidence → trigger LLM fallback
        logger.info("Heuristic: Ambiguous case → low confidence (will use LLM)")
        return ScenarioDetectionResult(
            scenario_name="valid-warranty",  # Tentative
            confidence=0.5,  # Low confidence
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
        """LLM-based scenario detection (fallback)

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

            # Call Anthropic API with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-sonnet-4-5",
                    max_tokens=50,
                    temperature=0,
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
        """Detect email scenario (tries heuristics then LLM)

        Args:
            email: Parsed email message
            serial_result: Serial number extraction result

        Returns:
            ScenarioDetectionResult with detected scenario
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
            # Detection failure → graceful degradation
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
```

**Processing Result Data Structure:**

```python
# src/guarantee_email_agent/email/processor_models.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ScenarioDetectionResult:
    """Result of scenario detection"""
    scenario_name: str
    confidence: float  # 0.0 to 1.0
    is_warranty_inquiry: bool
    detected_intent: str
    detection_method: str  # "heuristic", "llm", "fallback"
    ambiguous: bool

    def should_process(self) -> bool:
        """Check if email should be processed"""
        return self.scenario_name != "out-of-scope" and self.scenario_name != "spam"

    def get_scenario_for_routing(self) -> str:
        """Get scenario name for instruction routing"""
        return self.scenario_name

@dataclass(frozen=True)
class ProcessingResult:
    """Result of complete email processing pipeline"""
    success: bool
    email_id: str
    scenario_used: Optional[str]
    serial_number: Optional[str]
    warranty_status: Optional[str]
    response_sent: bool
    ticket_created: bool
    ticket_id: Optional[str]
    processing_time_ms: int
    error_message: Optional[str]
    failed_step: Optional[str]

    def is_successful(self) -> bool:
        """Check if processing completed successfully"""
        return self.success

    def requires_retry(self) -> bool:
        """Check if processing should be retried"""
        # Retry if failed at transient steps (warranty API, LLM, etc.)
        transient_steps = ["validate_warranty", "generate_response", "send_email"]
        return not self.success and self.failed_step in transient_steps
```

### Factory Function for Dependency Injection

```python
# src/guarantee_email_agent/email/__init__.py
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.email.scenario_detector import ScenarioDetector
from guarantee_email_agent.email.processor import EmailProcessor
from guarantee_email_agent.integrations.gmail import GmailClient
from guarantee_email_agent.integrations.warranty_api import WarrantyAPIClient
from guarantee_email_agent.integrations.ticketing import TicketingClient
from guarantee_email_agent.llm.response_generator import ResponseGenerator
from guarantee_email_agent.instructions.loader import load_instruction_cached

def create_email_processor(config: AgentConfig) -> EmailProcessor:
    """Factory function to create EmailProcessor with all dependencies

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
    gmail_client = GmailClient(config)
    warranty_client = WarrantyAPIClient(config)
    ticketing_client = TicketingClient(config)

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
        response_generator=response_generator
    )

    return processor
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Processing emails without error handling:**
   ```python
   # WRONG - No try/except, crashes on error
   async def process_email(raw_email):
       email = parser.parse_email(raw_email)
       serial = await extractor.extract_serial_number(email)
       # ... continues without error handling

   # CORRECT - Comprehensive error handling at each step
   async def process_email(raw_email):
       try:
           email = parser.parse_email(raw_email)
       except Exception as e:
           logger.error(f"Parse failed: {e}", exc_info=True)
           return ProcessingResult(success=False, failed_step="parse", ...)
   ```

2. **Silent failures (NFR5 violation):**
   ```python
   # WRONG - Swallowing exception silently
   try:
       ticket_id = await create_ticket(data)
   except:
       pass  # Email marked as processed but ticket not created!

   # CORRECT - Log error, mark as failed
   try:
       ticket_id = await create_ticket(data)
   except Exception as e:
       logger.error(f"Ticket creation failed: {e}", exc_info=True)
       raise  # Propagate to mark email as unprocessed
   ```

3. **Not tracking processing time:**
   ```python
   # WRONG - No performance tracking
   async def process_email(raw_email):
       # ... process email ...
       return ProcessingResult(...)

   # CORRECT - Track processing time
   async def process_email(raw_email):
       start_time = time.time()
       # ... process email ...
       processing_time_ms = int((time.time() - start_time) * 1000)
       return ProcessingResult(..., processing_time_ms=processing_time_ms)
   ```

4. **Calling warranty API for non-warranty scenarios:**
   ```python
   # WRONG - Always calling warranty API (wasted calls)
   warranty_data = await warranty_client.check_warranty(serial)

   # CORRECT - Only call if scenario requires it
   if serial_number and detection_result.is_warranty_inquiry:
       warranty_data = await warranty_client.check_warranty(serial)
   else:
       logger.info("Skipping warranty API call for non-warranty scenario")
   ```

5. **Not creating tickets for valid warranties (NFR21 violation):**
   ```python
   # WRONG - Forgetting ticket creation
   response = await generate_response(...)
   await send_email(response)
   # Forgot to create ticket!

   # CORRECT - Create ticket for valid warranties
   if warranty_status == "valid":
       ticket_id = await ticketing_client.create_ticket(ticket_data)
       logger.info(f"Ticket created: {ticket_id}")
   ```

### Verification Commands

```bash
# 1. Test scenario detector
uv run python -c "
import asyncio
from guarantee_email_agent.email.scenario_detector import ScenarioDetector
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.config.loader import load_config
from datetime import datetime

async def test():
    config = load_config()
    detector = ScenarioDetector(config, 'test instruction')

    # Test missing serial
    email = EmailMessage(
        subject='Warranty inquiry',
        body='I need warranty info but forgot serial',
        from_address='test@example.com',
        received_timestamp=datetime.now()
    )

    serial_result = SerialExtractionResult(
        serial_number=None,
        confidence=0.0,
        multiple_serials_detected=False,
        all_detected_serials=[],
        extraction_method='none',
        ambiguous=False
    )

    result = detector.detect_with_heuristics(email, serial_result)
    print(f'Scenario: {result.scenario_name}, confidence={result.confidence}')

asyncio.run(test())
"

# 2. Test complete pipeline (mock MCP clients)
uv run python -c "
import asyncio
from guarantee_email_agent.email import create_email_processor
from guarantee_email_agent.config.loader import load_config

async def test():
    config = load_config()
    processor = create_email_processor(config)

    raw_email = {
        'message_id': 'test-123',
        'subject': 'Warranty check',
        'body': 'Hi, my serial is SN12345',
        'from': 'customer@example.com',
        'received': '2026-01-18T10:00:00Z'
    }

    # This will fail with actual MCP calls unless mocked
    # Use for integration testing with mocks
    print('Processor initialized successfully')
    print(f'Dependencies: parser, extractor, detector, clients, generator')

asyncio.run(test())
"

# 3. Run unit tests
uv run pytest tests/email/test_scenario_detector.py -v
uv run pytest tests/email/test_processor.py -v

# 4. Run integration tests
uv run pytest tests/email/test_pipeline_integration.py -v

# 5. Run performance tests
uv run pytest tests/email/test_pipeline_integration.py::test_processing_time_within_60s -v

# 6. Test error handling
uv run pytest tests/email/test_processor.py::test_processing_failure_handling -v
uv run pytest tests/email/test_processor.py::test_no_silent_failures -v
```

### Dependency Notes

**Depends on:**
- Story 2.1: All MCP clients (Gmail, Warranty API, Ticketing)
- Story 3.1: Main instruction and orchestrator
- Story 3.2: Scenario router and response generator
- Story 3.3: Email parser and serial number extractor
- All previous Epic 1 stories for configuration and setup

**Blocks:**
- Story 3.5: CLI `agent run` command needs processor
- Story 3.6: Logging and graceful degradation uses processor
- All subsequent stories depend on complete pipeline

**Integration Points:**
- EmailParser → EmailMessage → SerialNumberExtractor
- SerialExtractionResult → ScenarioDetector → ScenarioDetectionResult
- ScenarioDetectionResult → WarrantyAPIClient → warranty_data
- warranty_data + scenario → ResponseGenerator → response_text
- response_text → GmailClient.send_email()
- valid warranty + ticket_data → TicketingClient.create_ticket()

### Previous Story Intelligence

From Story 3.3 (Email Parser and Serial Number Extraction):
- EmailMessage and SerialExtractionResult dataclasses
- EmailParser extracts metadata, handles plain text/HTML
- SerialNumberExtractor: pattern-based + LLM fallback
- Stateless processing (NFR16), customer data at DEBUG only (NFR14)
- 15s timeout on LLM calls, retry with exponential backoff

From Story 3.2 (Scenario Routing and LLM Response Generation):
- ScenarioRouter loads scenario instructions
- ResponseGenerator combines main + scenario instructions
- LLM configuration: claude-sonnet-4-5, temperature=0, 15s timeout
- Graceful-degradation fallback for missing/failed scenarios

From Story 3.1 (Instruction Parser and Main Orchestration):
- Main instruction provides guidance for all LLM operations
- Instruction caching for performance
- Retry pattern with tenacity (max 3 attempts)

From Story 2.1 (MCP Integration):
- Gmail, Warranty API, Ticketing clients with retry and circuit breaker
- Async operations throughout
- Timeout enforcement with asyncio.wait_for()

**Learnings to Apply:**
- Comprehensive error handling at each step (no silent failures)
- Track processing time and log performance
- Use dependency injection for testability
- Mock all external dependencies in tests
- Structured logging with email_id context throughout
- Conditional workflow logic based on scenario and warranty status

### Git Intelligence Summary

Recent commits show:
- Complete story implementations with full code examples
- Dataclasses for all data structures
- Comprehensive error handling patterns
- Testing strategies with mocked dependencies
- Performance tracking and logging
- Factory functions for dependency injection

**Code Patterns to Continue:**
- Dependency injection in __init__
- Try/except at each pipeline step
- Detailed logging with structured context
- Processing time tracking
- Conditional logic based on data
- Factory functions for object creation

### References

**Architecture Document Sections:**
- [Source: architecture.md#Email Processing Pipeline] - Complete workflow
- [Source: architecture.md#Data Flow] - Email → response flow
- [Source: project-context.md#Pipeline Orchestration] - Coordination patterns
- [Source: architecture.md#MCP Integration] - Client usage
- [Source: architecture.md#LLM Integration] - Response generation

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 3: Instruction Engine & Email Processing] - Parent epic
- [Source: epics-optimized.md#Story 3.4] - Complete acceptance criteria
- [Source: prd.md#FR2-21] - Email processing and integration requirements
- [Source: prd.md#FR44-45] - Error logging and failure marking
- [Source: prd.md#NFR5] - No silent failures
- [Source: prd.md#NFR7] - 60-second processing time (p95)
- [Source: prd.md#NFR10] - Concurrent processing
- [Source: prd.md#NFR21] - Ticket creation validation
- [Source: prd.md#NFR25] - Sufficient logging context

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context from all previous Epic 3 stories
- Story consolidates 2 original stories (4.3 Scenario Detection + 4.4 Complete Pipeline)
- ScenarioDetectionResult and ProcessingResult dataclasses designed
- ScenarioDetector with heuristic (fast) + LLM (fallback) detection
- EmailProcessor orchestrates complete 7-step pipeline
- Error handling at each step with no silent failures (NFR5)
- Processing time tracking with 60s target (NFR7)
- Conditional workflow: scenario → warranty validation → response → ticket
- API optimization: skip warranty calls for non-warranty scenarios
- Comprehensive logging with email_id context throughout
- Factory function (create_email_processor) for dependency injection
- Complete implementation patterns with full pipeline code
- Testing strategy: unit, integration, performance, error handling tests
- Verification commands for end-to-end pipeline validation

### File List

**Processing Data Models:**
- `src/guarantee_email_agent/email/processor_models.py` - ScenarioDetectionResult, ProcessingResult dataclasses

**Scenario Detection:**
- `src/guarantee_email_agent/email/scenario_detector.py` - ScenarioDetector with heuristic + LLM

**Email Processing Pipeline:**
- `src/guarantee_email_agent/email/processor.py` - EmailProcessor orchestrator

**Module Exports and Factory:**
- `src/guarantee_email_agent/email/__init__.py` - Updated exports, create_email_processor factory

**Tests:**
- `tests/email/test_scenario_detector.py` - Scenario detection tests
- `tests/email/test_processor.py` - Pipeline orchestrator tests
- `tests/email/test_pipeline_integration.py` - End-to-end integration tests
- `tests/email/test_performance.py` - Processing time and concurrent tests
- `tests/email/test_error_handling.py` - Error handling and failure marking tests
