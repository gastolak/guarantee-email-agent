# Story 3.3: Email Parser and Serial Number Extraction

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want to parse incoming warranty emails and extract serial numbers using LLM-guided reasoning,
So that the agent has all necessary context for processing.

## Acceptance Criteria

**Given** The Gmail MCP client from Epic 2 and instruction engine from Stories 3.1-3.2 exist
**When** The agent receives warranty inquiry emails

**Then - Email Content Parser:**
**And** Email parser in `src/guarantee_email_agent/email/parser.py` extracts metadata
**And** Extracted fields: subject, body, from (sender), received timestamp
**And** Parser handles plain text email bodies
**And** Parser extracts email thread ID for future use
**And** Email content parsed into structured EmailMessage object
**And** Parser logs email receipt with subject and sender
**And** Email content remains in memory only (NFR16 - stateless)
**And** Email content never written to disk or database (NFR16)
**And** Customer email data logged only at DEBUG level (NFR14)
**And** INFO logs show only metadata: subject, from address (no body content)

**Then - Serial Number Extraction:**
**And** Serial extractor in `src/guarantee_email_agent/email/serial_extractor.py` uses LLM
**And** Extraction follows main instruction guidance for serial number patterns
**And** Handles various formats: "SN12345", "Serial: ABC-123", "S/N: XYZ789"
**And** Multiple serial numbers in one email detected and logged
**And** If no serial found, returns None with confidence score
**And** Ambiguous cases flagged for graceful degradation
**And** Extractor logs results: "Serial extracted: SN12345" or "extraction failed"
**And** Failed extraction triggers missing-info scenario instruction
**And** Extraction errors handled gracefully without crashing

## Tasks / Subtasks

### Email Data Structures

- [ ] Create EmailMessage dataclass (AC: email content parsed into structured object)
  - [ ] Create `src/guarantee_email_agent/email/models.py`
  - [ ] Define `EmailMessage` dataclass with @dataclass decorator
  - [ ] Fields: subject (str), body (str), from_address (str), received_timestamp (datetime)
  - [ ] Field: thread_id (Optional[str]) for future thread tracking
  - [ ] Field: message_id (Optional[str]) for unique identification
  - [ ] Add type hints to all fields
  - [ ] Implement __str__ for logging (exclude body per NFR14)
  - [ ] Make EmailMessage immutable with frozen=True

- [ ] Create SerialExtractionResult dataclass (AC: extraction returns structured result)
  - [ ] Define `SerialExtractionResult` dataclass in models.py
  - [ ] Fields: serial_number (Optional[str]), confidence (float 0.0-1.0)
  - [ ] Field: multiple_serials_detected (bool)
  - [ ] Field: all_detected_serials (List[str]) for multi-serial logging
  - [ ] Field: extraction_method (str) - "pattern" or "llm"
  - [ ] Field: ambiguous (bool) flag for graceful degradation routing
  - [ ] Add helper method: is_successful() -> bool
  - [ ] Add helper method: should_use_graceful_degradation() -> bool

### Email Content Parser

- [ ] Create email parser module (AC: parser extracts metadata)
  - [ ] Create `src/guarantee_email_agent/email/parser.py`
  - [ ] Import EmailMessage dataclass from models
  - [ ] Import logging and datetime utilities
  - [ ] Create `EmailParser` class
  - [ ] Initialize parser with config if needed
  - [ ] Add logger with __name__

- [ ] Implement parse_email method (AC: extracts subject, body, from, timestamp)
  - [ ] Create `parse_email(raw_email: Dict[str, Any]) -> EmailMessage` method
  - [ ] Extract subject from raw_email['subject']
  - [ ] Extract body from raw_email['body'] or raw_email['text_body']
  - [ ] Handle HTML emails by stripping to plain text
  - [ ] Extract from_address from raw_email['from']
  - [ ] Parse received timestamp to datetime object
  - [ ] Extract thread_id if present in raw_email
  - [ ] Extract message_id if present
  - [ ] Return EmailMessage dataclass instance

- [ ] Implement plain text email handling (AC: handles plain text email bodies)
  - [ ] Check if email has text_body field first (preferred)
  - [ ] Fall back to html_body if no text_body
  - [ ] Use html2text or similar to convert HTML → plain text
  - [ ] Strip excessive whitespace and normalize line breaks
  - [ ] Preserve customer's original formatting where reasonable
  - [ ] Handle encoding issues (UTF-8, latin1, etc.)
  - [ ] Log warning if email format is unsupported

- [ ] Implement email receipt logging (AC: logs receipt with subject and sender)
  - [ ] Log at INFO level when email received
  - [ ] Include subject and from_address in log
  - [ ] DO NOT include email body at INFO level (NFR14)
  - [ ] Format: "Email received: subject='...' from='...'"
  - [ ] Include message_id if available
  - [ ] Include received timestamp
  - [ ] Use structured logging with extra dict

- [ ] Implement DEBUG-level body logging (AC: customer data logged only at DEBUG)
  - [ ] Log full email body ONLY at DEBUG level
  - [ ] Use logger.debug() with extra={'email_body': body}
  - [ ] Include in DEBUG log: subject, from, body, all metadata
  - [ ] Ensure production config uses INFO level (body not visible)
  - [ ] Document in code comments: NFR14 customer data protection
  - [ ] Add unit test verifying INFO logs exclude body

- [ ] Implement stateless parsing (AC: email content remains in memory only)
  - [ ] Parse email directly from input to EmailMessage
  - [ ] NEVER write email content to disk
  - [ ] NEVER store in database
  - [ ] Return EmailMessage object for in-memory processing
  - [ ] Ensure parser has no file I/O operations
  - [ ] Document NFR16 stateless requirement in code

- [ ] Add error handling for malformed emails
  - [ ] Catch parsing exceptions gracefully
  - [ ] Log parsing errors with email metadata (not body)
  - [ ] Return partial EmailMessage if some fields parseable
  - [ ] Raise EmailParseError for completely unparseable emails
  - [ ] Include error details in structured logs
  - [ ] Don't crash on missing optional fields (thread_id, message_id)

### Serial Number Extraction with LLM

- [ ] Create serial extractor module (AC: extractor uses LLM)
  - [ ] Create `src/guarantee_email_agent/email/serial_extractor.py`
  - [ ] Import EmailMessage and SerialExtractionResult from models
  - [ ] Import Anthropic SDK for LLM calls
  - [ ] Import tenacity for retry logic
  - [ ] Create `SerialNumberExtractor` class
  - [ ] Initialize with config (API key, main instruction)
  - [ ] Store reference to Anthropic client

- [ ] Implement pattern-based extraction (fast path) (AC: handles various formats)
  - [ ] Create `extract_with_patterns(email_body: str) -> SerialExtractionResult`
  - [ ] Define regex patterns for common serial formats:
    - [ ] Pattern: "SN12345", "SN-12345", "SN 12345"
    - [ ] Pattern: "Serial: ABC-123", "Serial Number: XYZ789"
    - [ ] Pattern: "S/N: 12345", "Serial#: ABC123"
    - [ ] Pattern: Standalone alphanumeric 6-15 chars after "serial"
  - [ ] Search email body with all patterns
  - [ ] If single match found, return high confidence (0.95)
  - [ ] If multiple matches, set multiple_serials_detected=True
  - [ ] If no matches, return None (will fallback to LLM)
  - [ ] Log pattern extraction results

- [ ] Implement LLM-based extraction (fallback) (AC: extraction follows main instruction guidance)
  - [ ] Create `extract_with_llm(email_body: str) -> SerialExtractionResult` async method
  - [ ] Build system message from main instruction + serial extraction guidance
  - [ ] Build user message with email body
  - [ ] Prompt: "Extract the product serial number from this email. Return ONLY the serial number, or 'NONE' if not found."
  - [ ] Call Anthropic API with temperature=0, claude-sonnet-4-5
  - [ ] Parse LLM response for serial number
  - [ ] Apply 15-second timeout (same as other LLM calls)
  - [ ] Return SerialExtractionResult with confidence based on response clarity
  - [ ] Handle "NONE" response → returns None serial_number

- [ ] Implement main extraction method (AC: extractor extracts serial numbers)
  - [ ] Create `extract_serial_number(email: EmailMessage) -> SerialExtractionResult` async method
  - [ ] Try pattern-based extraction first (fast path)
  - [ ] If pattern extraction succeeds with high confidence, return immediately
  - [ ] If pattern extraction fails or low confidence, fallback to LLM extraction
  - [ ] Log which method was used: pattern or llm
  - [ ] Return SerialExtractionResult with all fields populated
  - [ ] Log extraction time for performance monitoring

- [ ] Handle multiple serial numbers (AC: multiple serials detected and logged)
  - [ ] When pattern matching finds >1 serial, populate all_detected_serials list
  - [ ] Set multiple_serials_detected=True flag
  - [ ] Log warning: "Multiple serial numbers detected: {serials}"
  - [ ] Choose first serial as primary (serial_number field)
  - [ ] Set confidence lower (0.7) due to ambiguity
  - [ ] Set ambiguous=True for potential graceful degradation routing
  - [ ] Document in logs which serial was selected

- [ ] Handle no serial found (AC: returns None with confidence score)
  - [ ] If pattern extraction finds nothing, try LLM
  - [ ] If LLM also finds nothing, return SerialExtractionResult with:
    - [ ] serial_number=None
    - [ ] confidence=0.0
    - [ ] extraction_method="none"
  - [ ] Log: "Serial number extraction failed: not found in email"
  - [ ] Caller should route to missing-info scenario
  - [ ] Don't raise exception (None is valid result)

- [ ] Implement ambiguous case handling (AC: ambiguous cases flagged)
  - [ ] Set ambiguous=True when:
    - [ ] Multiple serials detected
    - [ ] LLM confidence is low (<0.5)
    - [ ] Pattern extraction finds unconventional format
  - [ ] Log ambiguous cases clearly
  - [ ] Return result with ambiguous flag set
  - [ ] Let caller decide if graceful degradation needed
  - [ ] Document ambiguity criteria in code comments

- [ ] Add extraction logging (AC: logs results or failure)
  - [ ] Log at INFO level: "Serial extracted: {serial}" when successful
  - [ ] Include extraction method (pattern or llm)
  - [ ] Include confidence score in logs
  - [ ] Log at WARN level if extraction failed
  - [ ] Log at DEBUG level: full email body + extraction details (NFR14)
  - [ ] Use structured logging with extra dict
  - [ ] Include email subject and from_address for context

- [ ] Implement retry logic for LLM extraction (AC: extraction errors handled gracefully)
  - [ ] Apply @retry decorator to extract_with_llm()
  - [ ] Max 3 attempts with exponential backoff
  - [ ] Retry on transient errors: network, timeout, 5xx
  - [ ] Don't retry on: auth errors, invalid requests
  - [ ] Log retry attempts at WARN level
  - [ ] After retries exhausted, return extraction failure (not crash)
  - [ ] Wrap in try/except to prevent propagation

- [ ] Handle extraction errors gracefully (AC: errors don't crash agent)
  - [ ] Catch all exceptions in extract_serial_number()
  - [ ] Log error with context: email subject, error message
  - [ ] Return SerialExtractionResult indicating failure
  - [ ] Don't crash or raise exception to caller
  - [ ] Mark email for graceful degradation
  - [ ] Include error details in logs but not customer-facing

### Integration with Scenario Routing

- [ ] Connect extraction to missing-info scenario (AC: failed extraction triggers missing-info)
  - [ ] Import SerialExtractionResult in email processor
  - [ ] After extraction, check if result.serial_number is None
  - [ ] If None, route to "missing-info" scenario
  - [ ] Pass email and extraction result to scenario router
  - [ ] Log: "No serial found, routing to missing-info scenario"
  - [ ] Ensure missing-info scenario instruction exists (from Story 3.2)

- [ ] Connect extraction to graceful degradation (AC: ambiguous cases flagged)
  - [ ] Check result.should_use_graceful_degradation()
  - [ ] If True (ambiguous or multiple serials), consider graceful degradation
  - [ ] Log: "Ambiguous serial extraction, considering graceful degradation"
  - [ ] Let orchestrator decide based on context
  - [ ] Document decision criteria in orchestrator

### Email Parser Module Initialization

- [ ] Update email module exports
  - [ ] Create/update `src/guarantee_email_agent/email/__init__.py`
  - [ ] Export EmailMessage, SerialExtractionResult from models
  - [ ] Export EmailParser from parser
  - [ ] Export SerialNumberExtractor from serial_extractor
  - [ ] Provide clean public API for email processing

### Testing

- [ ] Create email models tests
  - [ ] Create `tests/email/test_models.py`
  - [ ] Test EmailMessage dataclass creation
  - [ ] Test EmailMessage __str__ excludes body (NFR14)
  - [ ] Test SerialExtractionResult helper methods
  - [ ] Test is_successful() returns True when serial found
  - [ ] Test should_use_graceful_degradation() logic
  - [ ] Test immutability if frozen=True used

- [ ] Create email parser tests
  - [ ] Create `tests/email/test_parser.py`
  - [ ] Test parse_email() with valid plain text email
  - [ ] Test parse_email() with HTML email (converted to text)
  - [ ] Test extraction of all metadata fields
  - [ ] Test handling missing optional fields (thread_id)
  - [ ] Test malformed email error handling
  - [ ] Test encoding issues (UTF-8, special characters)
  - [ ] Mock raw email data for tests

- [ ] Create serial extractor tests
  - [ ] Create `tests/email/test_serial_extractor.py`
  - [ ] Test pattern extraction with various formats
  - [ ] Test LLM extraction (mock Anthropic API)
  - [ ] Test multiple serial number detection
  - [ ] Test no serial found returns None
  - [ ] Test ambiguous case flagging
  - [ ] Test retry logic on LLM failures
  - [ ] Test graceful error handling
  - [ ] Use pytest fixtures for test emails

- [ ] Create integration tests
  - [ ] Create `tests/email/test_email_integration.py`
  - [ ] Test end-to-end: raw email → parsed → serial extracted
  - [ ] Test various real-world email formats
  - [ ] Test edge cases: empty emails, very long emails
  - [ ] Test stateless processing (no disk I/O)
  - [ ] Verify DEBUG vs INFO logging levels
  - [ ] Mock LLM API for deterministic tests

- [ ] Create scenario routing integration tests
  - [ ] Test extraction failure → missing-info scenario
  - [ ] Test ambiguous extraction → graceful degradation consideration
  - [ ] Test successful extraction → warranty validation flow
  - [ ] Verify correct scenario selection based on extraction result
  - [ ] Test with scenario router from Story 3.2

## Dev Notes

### Architecture Context

This story implements **Email Parser and Serial Number Extraction** (consolidates old stories 4.1 and 4.2), building on the Gmail MCP client from Epic 2 and the instruction engine from Stories 3.1-3.2. This provides the critical input processing layer that feeds warranty validation and response generation.

**Key Architectural Principles:**
- FR1: Monitor designated Gmail inbox for incoming emails
- FR2: Parse email content, metadata, subject, sender
- FR3: Extract serial numbers from varied email formats
- FR4: Detect scenarios (missing serial triggers missing-info)
- FR5: Identify when serial extraction fails or ambiguous
- NFR14: Customer email data logged ONLY at DEBUG level (not INFO)
- NFR16: Stateless email handling (no persistence beyond processing)

### Critical Implementation Rules from Project Context

**Stateless Processing (MANDATORY - NFR16):**

NEVER persist email content to disk or database:

```python
# ❌ WRONG - Persisting email content
with open("emails.log", "a") as f:
    f.write(email.body)

db.save_email(email.body)

# ✅ CORRECT - In-memory only
email_message = parser.parse_email(raw_email)  # Returns dataclass
result = await extractor.extract_serial_number(email_message)
# Email content lives only in memory, never persisted
```

**Customer Data Logging Protection (MANDATORY - NFR14):**

Email body content logged ONLY at DEBUG level:

```python
# ❌ WRONG - Customer data at INFO level
logger.info(f"Processing email: {email.body}")

# ✅ CORRECT - Body only at DEBUG, metadata at INFO
logger.info("Email received", extra={
    "subject": email.subject,
    "from": email.from_address
})

logger.debug("Email content", extra={
    "subject": email.subject,
    "from": email.from_address,
    "body": email.body  # Only visible at DEBUG level
})
```

**Email Parser Implementation Pattern:**

```python
# src/guarantee_email_agent/email/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass(frozen=True)
class EmailMessage:
    """Structured email message (immutable, in-memory only)"""
    subject: str
    body: str
    from_address: str
    received_timestamp: datetime
    thread_id: Optional[str] = None
    message_id: Optional[str] = None

    def __str__(self) -> str:
        """String representation excluding body per NFR14"""
        return (
            f"EmailMessage(subject='{self.subject}', "
            f"from='{self.from_address}', "
            f"received={self.received_timestamp})"
        )

@dataclass(frozen=True)
class SerialExtractionResult:
    """Result of serial number extraction"""
    serial_number: Optional[str]
    confidence: float  # 0.0 to 1.0
    multiple_serials_detected: bool
    all_detected_serials: List[str]
    extraction_method: str  # "pattern", "llm", or "none"
    ambiguous: bool

    def is_successful(self) -> bool:
        """Check if extraction succeeded"""
        return self.serial_number is not None

    def should_use_graceful_degradation(self) -> bool:
        """Check if graceful degradation recommended"""
        return self.ambiguous or (
            self.multiple_serials_detected and self.confidence < 0.8
        )
```

```python
# src/guarantee_email_agent/email/parser.py
import logging
from datetime import datetime
from typing import Dict, Any
from guarantee_email_agent.email.models import EmailMessage
from guarantee_email_agent.utils.errors import EmailParseError

logger = logging.getLogger(__name__)

class EmailParser:
    """Parse raw email data into structured EmailMessage"""

    def parse_email(self, raw_email: Dict[str, Any]) -> EmailMessage:
        """Parse raw email to EmailMessage dataclass

        Args:
            raw_email: Raw email data from Gmail MCP
                Expected fields: subject, body (or text_body), from, received

        Returns:
            Parsed EmailMessage object

        Raises:
            EmailParseError: If email cannot be parsed
        """
        try:
            # Extract required fields
            subject = raw_email.get('subject', '(No Subject)')
            from_address = raw_email['from']  # Required
            received = raw_email.get('received', datetime.now())

            # Extract body (prefer text_body, fall back to body)
            body = raw_email.get('text_body') or raw_email.get('body', '')

            # Handle HTML emails (convert to plain text)
            if raw_email.get('content_type', '').startswith('text/html'):
                body = self._html_to_text(body)

            # Extract optional fields
            thread_id = raw_email.get('thread_id')
            message_id = raw_email.get('message_id')

            # Parse timestamp
            if isinstance(received, str):
                received_timestamp = datetime.fromisoformat(received)
            else:
                received_timestamp = received

            # Create EmailMessage
            email = EmailMessage(
                subject=subject,
                body=body,
                from_address=from_address,
                received_timestamp=received_timestamp,
                thread_id=thread_id,
                message_id=message_id
            )

            # Log email receipt (INFO level - NO body per NFR14)
            logger.info(
                "Email received",
                extra={
                    "subject": email.subject,
                    "from": email.from_address,
                    "received": email.received_timestamp.isoformat(),
                    "message_id": email.message_id
                }
            )

            # Log full content at DEBUG level only (NFR14)
            logger.debug(
                "Email content",
                extra={
                    "subject": email.subject,
                    "from": email.from_address,
                    "body": email.body,  # ONLY visible at DEBUG level
                    "thread_id": email.thread_id,
                    "message_id": email.message_id
                }
            )

            return email

        except KeyError as e:
            raise EmailParseError(
                message=f"Missing required email field: {e}",
                code="email_missing_field",
                details={"field": str(e), "available_fields": list(raw_email.keys())}
            )
        except Exception as e:
            raise EmailParseError(
                message=f"Email parsing failed: {str(e)}",
                code="email_parse_failed",
                details={"error": str(e)}
            )

    def _html_to_text(self, html: str) -> str:
        """Convert HTML email body to plain text

        Args:
            html: HTML content

        Returns:
            Plain text version
        """
        # Simple HTML stripping (use html2text library in real implementation)
        import re
        text = re.sub('<[^<]+?>', '', html)
        text = text.strip()
        return text
```

**Serial Number Extractor Implementation Pattern:**

```python
# src/guarantee_email_agent/email/serial_extractor.py
import asyncio
import logging
import re
from typing import List, Optional
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.models import EmailMessage, SerialExtractionResult
from guarantee_email_agent.utils.errors import TransientError, LLMError

logger = logging.getLogger(__name__)

# Serial number regex patterns
SERIAL_PATTERNS = [
    r'SN[-\s]?(\w{5,15})',  # SN12345, SN-12345, SN 12345
    r'Serial\s*(?:Number)?[:\s]+(\w{5,15})',  # Serial: ABC-123
    r'S/N[:\s]+(\w{5,15})',  # S/N: XYZ789
    r'Serial#[:\s]*(\w{5,15})',  # Serial#: ABC123
    r'(?i)(?:serial|s/n|sn)(?:\s*number)?[:\s]+([A-Z0-9-]{5,15})'  # Flexible pattern
]

class SerialNumberExtractor:
    """Extract serial numbers from emails using patterns and LLM fallback"""

    def __init__(self, config: AgentConfig, main_instruction_body: str):
        """Initialize serial number extractor

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

        logger.info("Serial number extractor initialized")

    def extract_with_patterns(self, email_body: str) -> SerialExtractionResult:
        """Try pattern-based extraction (fast path)

        Args:
            email_body: Email body text

        Returns:
            SerialExtractionResult with pattern extraction results
        """
        all_matches = []

        # Try all patterns
        for pattern in SERIAL_PATTERNS:
            matches = re.findall(pattern, email_body, re.IGNORECASE)
            all_matches.extend(matches)

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
        """Extract serial number using LLM (fallback method)

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

            # Call Anthropic API with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-sonnet-4-5",
                    max_tokens=100,
                    temperature=0,
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
        """Extract serial number from email (tries patterns then LLM)

        Args:
            email: Parsed email message

        Returns:
            SerialExtractionResult with extraction outcome
        """
        logger.info(
            f"Extracting serial number from email: subject='{email.subject}'"
        )

        try:
            # Try pattern-based extraction first (fast path)
            pattern_result = self.extract_with_patterns(email.body)

            # If pattern extraction succeeded with high confidence, return
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

            # Both methods failed
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
            # Graceful error handling - don't crash
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
            return SerialExtractionResult(
                serial_number=None,
                confidence=0.0,
                multiple_serials_detected=False,
                all_detected_serials=[],
                extraction_method="error",
                ambiguous=True  # Route to graceful degradation
            )
```

### Testing Strategy

**Unit Tests:**

```python
# tests/email/test_parser.py
import pytest
from datetime import datetime
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.models import EmailMessage

def test_parse_email_plain_text():
    parser = EmailParser()
    raw_email = {
        'subject': 'Warranty check',
        'body': 'Hi, I need warranty info for SN12345',
        'from': 'customer@example.com',
        'received': '2026-01-18T10:00:00Z'
    }

    email = parser.parse_email(raw_email)

    assert email.subject == 'Warranty check'
    assert email.body == 'Hi, I need warranty info for SN12345'
    assert email.from_address == 'customer@example.com'
    assert isinstance(email.received_timestamp, datetime)

def test_parse_email_excludes_body_from_str(caplog):
    """Verify __str__ excludes body per NFR14"""
    email = EmailMessage(
        subject='Test',
        body='Secret customer data',
        from_address='test@example.com',
        received_timestamp=datetime.now()
    )

    email_str = str(email)
    assert 'Secret customer data' not in email_str
    assert 'Test' in email_str
    assert 'test@example.com' in email_str
```

```python
# tests/email/test_serial_extractor.py
import pytest
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.email.models import EmailMessage

@pytest.mark.asyncio
async def test_pattern_extraction_simple_format():
    extractor = SerialNumberExtractor(config=mock_config, main_instruction_body="")

    email = EmailMessage(
        subject='Warranty inquiry',
        body='Hi, my serial number is SN12345',
        from_address='test@example.com',
        received_timestamp=datetime.now()
    )

    result = await extractor.extract_serial_number(email)

    assert result.is_successful()
    assert result.serial_number == '12345'
    assert result.extraction_method == 'pattern'
    assert result.confidence >= 0.9

@pytest.mark.asyncio
async def test_extraction_multiple_serials_detected():
    extractor = SerialNumberExtractor(config=mock_config, main_instruction_body="")

    email = EmailMessage(
        subject='Multiple devices',
        body='I have two devices: SN12345 and SN67890',
        from_address='test@example.com',
        received_timestamp=datetime.now()
    )

    result = await extractor.extract_serial_number(email)

    assert result.multiple_serials_detected
    assert len(result.all_detected_serials) == 2
    assert result.ambiguous  # Should flag for graceful degradation
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Persisting email content (NFR16 violation):**
   ```python
   # WRONG - Writing email to disk
   with open("emails.log", "a") as f:
       f.write(email.body)

   # CORRECT - In-memory only
   email = parser.parse_email(raw_email)  # Stays in memory
   ```

2. **Logging customer data at INFO level (NFR14 violation):**
   ```python
   # WRONG - Email body at INFO level
   logger.info(f"Email: {email.body}")

   # CORRECT - Body only at DEBUG
   logger.debug("Email content", extra={"body": email.body})
   logger.info("Email received", extra={"subject": email.subject})
   ```

3. **Crashing on extraction failure:**
   ```python
   # WRONG - Unhandled exception crashes agent
   serial = extract_serial(email)  # Raises exception

   # CORRECT - Return None, log error, continue
   result = await extractor.extract_serial_number(email)
   if not result.is_successful():
       logger.warning("Serial extraction failed, routing to missing-info")
       return route_to_scenario("missing-info")
   ```

4. **Not handling multiple serial numbers:**
   ```python
   # WRONG - Only detect first serial
   serial = re.search(PATTERN, email.body).group(1)

   # CORRECT - Detect all serials, flag ambiguity
   all_serials = re.findall(PATTERN, email.body)
   if len(all_serials) > 1:
       result.multiple_serials_detected = True
       result.ambiguous = True
   ```

5. **Forgetting LLM timeout:**
   ```python
   # WRONG - No timeout on LLM call
   response = await self.client.messages.create(...)

   # CORRECT - 15-second timeout
   response = await asyncio.wait_for(
       self.client.messages.create(...),
       timeout=15
   )
   ```

### Verification Commands

```bash
# 1. Create email module directory
mkdir -p src/guarantee_email_agent/email

# 2. Test email parsing
uv run python -c "
from guarantee_email_agent.email.parser import EmailParser

parser = EmailParser()
raw_email = {
    'subject': 'Warranty check',
    'body': 'Hi, my serial is SN12345',
    'from': 'test@example.com',
    'received': '2026-01-18T10:00:00Z'
}

email = parser.parse_email(raw_email)
print(f'Parsed: {email}')
"

# 3. Test serial extraction patterns
uv run python -c "
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.email.models import EmailMessage
from datetime import datetime
import asyncio

async def test():
    # Mock config and instruction
    class MockConfig:
        class Secrets:
            anthropic_api_key = 'test'
        secrets = Secrets()

    extractor = SerialNumberExtractor(MockConfig(), 'test instruction')

    # Test pattern extraction
    email = EmailMessage(
        subject='Test',
        body='Serial number: SN12345',
        from_address='test@example.com',
        received_timestamp=datetime.now()
    )

    result = extractor.extract_with_patterns(email.body)
    print(f'Pattern result: {result.serial_number}, confidence={result.confidence}')

asyncio.run(test())
"

# 4. Verify logging levels (INFO excludes body)
uv run python -c "
import logging
from guarantee_email_agent.email.parser import EmailParser

# Set to INFO level
logging.basicConfig(level=logging.INFO)

parser = EmailParser()
raw_email = {
    'subject': 'Test',
    'body': 'SENSITIVE CUSTOMER DATA',
    'from': 'test@example.com',
    'received': '2026-01-18T10:00:00Z'
}

# This should NOT show body at INFO level
email = parser.parse_email(raw_email)
"

# 5. Run unit tests
uv run pytest tests/email/test_parser.py -v
uv run pytest tests/email/test_serial_extractor.py -v

# 6. Run integration tests
uv run pytest tests/email/test_email_integration.py -v

# 7. Test stateless processing (no disk I/O)
uv run python -c "
import os
from guarantee_email_agent.email.parser import EmailParser

# Verify no files created
initial_files = set(os.listdir('.'))

parser = EmailParser()
email = parser.parse_email({
    'subject': 'Test',
    'body': 'Test body',
    'from': 'test@example.com',
    'received': '2026-01-18T10:00:00Z'
})

final_files = set(os.listdir('.'))
new_files = final_files - initial_files

if new_files:
    print(f'ERROR: Files created: {new_files}')
else:
    print('✓ Stateless: No files created')
"
```

### Dependency Notes

**Depends on:**
- Story 2.1: Gmail MCP client provides raw email data
- Story 3.1: Main instruction for LLM serial extraction guidance
- Story 3.2: Scenario router for missing-info scenario routing
- Story 1.2: Configuration schema
- Story 1.3: Environment variables (ANTHROPIC_API_KEY)

**Blocks:**
- Story 3.4: Complete email processing pipeline needs parsed emails
- Story 3.4: Warranty validation needs extracted serial numbers
- All subsequent Epic 3 stories depend on email parsing

**Integration Points:**
- Gmail MCP client → EmailParser → EmailMessage
- EmailMessage → SerialNumberExtractor → SerialExtractionResult
- SerialExtractionResult → Scenario Router (missing-info if None)
- Scenario Router → Response Generator (graceful degradation if ambiguous)

### Previous Story Intelligence

From Story 3.2 (Scenario Routing and LLM Response Generation):
- Scenario router with graceful-degradation fallback
- LLM configuration: claude-sonnet-4-5, temperature=0, 15s timeout
- Retry pattern: max 3 attempts with exponential backoff
- Structured logging with scenario context
- Missing-info scenario instruction exists for failed serial extraction

From Story 3.1 (Instruction Parser and Main Orchestration):
- Main instruction includes serial number extraction guidance
- Temperature=0 for determinism
- 15-second timeout on all LLM calls
- Retry with tenacity decorator
- Instruction caching for performance

From Story 2.1 (MCP Integration):
- Gmail MCP client provides raw email data
- Retry pattern established: @retry decorator
- Timeout enforcement: asyncio.wait_for()
- Error hierarchy: TransientError vs Non-Transient
- Structured logging with extra dict

**Learnings to Apply:**
- Reuse LLM configuration from previous stories
- Apply same retry and timeout patterns
- Use structured logging throughout
- Follow dataclass pattern for data structures
- Use async/await for LLM calls
- Log extraction method and confidence for debugging

### Git Intelligence Summary

Recent commits show:
- Story 3.2 fully implemented scenario routing and LLM response generation
- Story 3.1 implemented instruction parser with caching
- Comprehensive Dev Notes with complete code examples
- Dataclasses for structured data (InstructionFile, etc.)
- Async patterns throughout
- Configuration-driven behavior
- Complete testing examples

**Code Patterns to Continue:**
- `@dataclass(frozen=True)` for immutable data
- Async methods: `async def` with `await`
- Structured logging: `logger.info("msg", extra={...})`
- Error codes: `{component}_{error_type}`
- Type hints on all signatures
- Comprehensive docstrings

### References

**Architecture Document Sections:**
- [Source: architecture.md#Email Processing] - Email parser architecture
- [Source: architecture.md#LLM Integration] - Serial extraction with LLM
- [Source: project-context.md#Stateless Processing] - NFR16 no persistence
- [Source: project-context.md#Customer Data Logging] - NFR14 DEBUG only
- [Source: architecture.md#Data Flow] - Email → Parser → Extractor flow

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 3: Instruction Engine & Email Processing] - Parent epic
- [Source: epics-optimized.md#Story 3.3] - Complete acceptance criteria
- [Source: prd.md#FR1-FR5] - Email processing requirements
- [Source: prd.md#NFR14] - Customer data logging protection
- [Source: prd.md#NFR16] - Stateless email handling
- [Source: prd.md#NFR11] - LLM timeout requirement

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context analysis from PRD, Architecture, Stories 3.1 and 3.2
- Story consolidates 2 original stories (4.1 Email Parser + 4.2 Serial Extraction)
- EmailMessage and SerialExtractionResult dataclasses designed
- EmailParser with stateless in-memory processing (NFR16)
- Customer data protection: body logged ONLY at DEBUG level (NFR14)
- SerialNumberExtractor with pattern-based + LLM fallback
- Pattern extraction handles multiple formats: SN12345, Serial: ABC-123, S/N: XYZ789
- Multiple serial number detection with ambiguity flagging
- LLM extraction with 15-second timeout and retry logic
- Graceful error handling (no crashes on extraction failure)
- Missing serial triggers missing-info scenario routing
- Ambiguous cases flagged for graceful degradation consideration
- Complete implementation patterns with full code examples
- Testing strategy with unit and integration tests
- Verification commands for stateless processing validation

### File List

**Email Data Models:**
- `src/guarantee_email_agent/email/models.py` - EmailMessage and SerialExtractionResult dataclasses

**Email Parser:**
- `src/guarantee_email_agent/email/parser.py` - EmailParser class

**Serial Number Extractor:**
- `src/guarantee_email_agent/email/serial_extractor.py` - SerialNumberExtractor with pattern + LLM

**Module Exports:**
- `src/guarantee_email_agent/email/__init__.py` - Public API exports

**Error Definitions:**
- `src/guarantee_email_agent/utils/errors.py` - EmailParseError (if not exists)

**Tests:**
- `tests/email/test_models.py` - Data model tests
- `tests/email/test_parser.py` - Email parser tests
- `tests/email/test_serial_extractor.py` - Serial extractor tests
- `tests/email/test_email_integration.py` - End-to-end integration tests
