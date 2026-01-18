# Story 2.1: All MCP Clients with Retry Logic and Circuit Breaker

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a CTO,
I want to integrate with Gmail, Warranty API, and Ticketing system via MCP with comprehensive error handling,
So that the agent can reliably interact with all external systems despite transient failures.

## Acceptance Criteria

**Given** The configuration system from Epic 1 is complete
**When** I configure all three MCP connections in config.yaml

**Then - Gmail MCP Client:**
**And** The Gmail client connects to community Gmail MCP server via stdio transport
**And** Uses MCP Python SDK v1.25.0 (pinned to v1.x: `mcp>=1.25,<2`)
**And** `monitor_inbox()` method reads emails from designated inbox label
**And** `send_email()` method sends email responses via Gmail API
**And** All calls use @retry decorator with exponential backoff (max 3 attempts)
**And** Transient errors (network, timeout, rate limit) are retried
**And** Non-transient errors (auth failures) are NOT retried
**And** Each MCP call has a 30-second timeout
**And** Rate limiting is handled gracefully without data loss (NFR19)

**Then - Warranty API Custom MCP Server:**
**And** Custom MCP server in `mcp_servers/warranty_mcp_server/` wraps warranty API
**And** Server exposes `check_warranty` tool via stdio transport
**And** Warranty client connects to this MCP server
**And** `check_warranty(serial_number)` method queries warranty status via MCP
**And** Uses @retry decorator with max 3 attempts and exponential backoff
**And** Each warranty API call has a 10-second timeout (NFR20)
**And** API responses parsed correctly: valid, expired, not_found status
**And** Returns warranty data: {serial_number, status, expiration_date}

**Then - Ticketing System Custom MCP Server:**
**And** Custom MCP server in `mcp_servers/ticketing_mcp_server/` wraps ticketing API
**And** Server exposes `create_ticket` tool via stdio transport
**And** Ticketing client connects to this MCP server
**And** `create_ticket(ticket_data)` method creates tickets via MCP
**And** Ticket data includes: serial_number, warranty_status, customer_email, priority, category
**And** Uses @retry decorator with max 3 attempts
**And** Validates ticket creation success before marking email processed (NFR21)
**And** Returns ticket ID and confirmation

**Then - Circuit Breaker for All Integrations:**
**And** Circuit breaker in `src/guarantee_email_agent/utils/circuit_breaker.py` tracks failures
**And** Circuit breaker opens after 5 consecutive failures per integration (NFR18)
**And** When circuit is OPEN, calls fail fast without retries
**And** Circuit remains OPEN for 60 seconds before attempting to HALF_OPEN
**And** In HALF_OPEN state, single success closes circuit, single failure reopens
**And** Circuit state transitions log clearly
**And** Each MCP client (Gmail, Warranty API, Ticketing) has independent circuit breaker
**And** Agent continues processing other emails when one integration's circuit is open (NFR22)

**Then - Shared Error Handling:**
**And** All MCP failures log error with context: service, attempt count, error type
**And** Failed operations after retries are logged at ERROR level
**And** Transient failures during retry are logged at WARN level
**And** All three integrations follow consistent error patterns
**And** Integration failures don't crash the agent
**And** Emails are marked unprocessed when critical integrations fail

## Tasks / Subtasks

### Gmail MCP Client Implementation

- [ ] Install and configure MCP Python SDK (AC: Uses MCP SDK v1.25.0)
  - [ ] Add `mcp>=1.25,<2` to pyproject.toml dependencies
  - [ ] Pin to v1.x explicitly to avoid v2 pre-alpha
  - [ ] Run `uv add "mcp>=1.25,<2"` to update uv.lock
  - [ ] Verify MCP SDK installation: `uv pip list | grep mcp`
  - [ ] Document SDK version pinning in project-context.md

- [ ] Create Gmail MCP client module (AC: Gmail client connects to MCP server)
  - [ ] Create `src/guarantee_email_agent/integrations/mcp/gmail_client.py`
  - [ ] Import MCP SDK: `from mcp import Client, StdioServerParameters`
  - [ ] Create `GmailMCPClient` class with stdio transport
  - [ ] Load Gmail MCP server path from config.mcp.gmail.server_path
  - [ ] Initialize client with StdioServerParameters for stdio transport
  - [ ] Implement `connect()` async method with 30-second timeout
  - [ ] Implement `disconnect()` async method for cleanup
  - [ ] Add connection state tracking (connected/disconnected)

- [ ] Implement monitor_inbox() method (AC: reads emails from inbox)
  - [ ] Create `monitor_inbox(label: str = "INBOX") -> List[EmailMessage]` async method
  - [ ] Use MCP client to call Gmail API list_messages tool
  - [ ] Filter by label parameter (default "INBOX")
  - [ ] Parse email metadata: subject, from, body, received timestamp, thread_id
  - [ ] Return list of EmailMessage objects (from `email.parser` module)
  - [ ] Handle empty inbox gracefully (return empty list)
  - [ ] Apply 30-second timeout per AC
  - [ ] Log: "Gmail inbox monitored: {count} emails found"

- [ ] Implement send_email() method (AC: sends email responses)
  - [ ] Create `send_email(to: str, subject: str, body: str, thread_id: Optional[str] = None) -> str` async method
  - [ ] Use MCP client to call Gmail API send_message tool
  - [ ] Pass recipient, subject, body as parameters
  - [ ] Include thread_id for email threading (reply to original)
  - [ ] Return message ID from Gmail API response
  - [ ] Apply 30-second timeout per AC
  - [ ] Log: "Email sent to {to}: subject={subject}, message_id={message_id}"

- [ ] Add retry decorator to Gmail methods (AC: exponential backoff with max 3 attempts)
  - [ ] Import tenacity: `from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type`
  - [ ] Apply @retry to monitor_inbox() and send_email()
  - [ ] Configure stop condition: `stop=stop_after_attempt(3)`
  - [ ] Configure wait strategy: `wait=wait_exponential(multiplier=1, min=1, max=10)`
  - [ ] Retry only transient errors: network, timeout, rate limit
  - [ ] Do NOT retry auth failures (non-transient)
  - [ ] Use `retry_if_exception_type(TransientError)` to filter retryable errors

- [ ] Implement rate limiting handling (AC: graceful rate limit handling per NFR19)
  - [ ] Detect Gmail API rate limit errors (HTTP 429)
  - [ ] Extract retry-after header from response
  - [ ] Wait for retry-after duration before retry
  - [ ] Log: "Gmail rate limit hit, waiting {retry_after}s before retry"
  - [ ] Ensure no email data is lost during rate limiting
  - [ ] Mark rate limit as transient error for retry logic

### Warranty API Custom MCP Server

- [ ] Create warranty API MCP server directory structure (AC: server in mcp_servers/)
  - [ ] Create `mcp_servers/warranty_mcp_server/` directory
  - [ ] Create `mcp_servers/warranty_mcp_server/server.py`
  - [ ] Create `mcp_servers/warranty_mcp_server/pyproject.toml`
  - [ ] Create `mcp_servers/warranty_mcp_server/README.md`
  - [ ] Add .gitignore for Python artifacts

- [ ] Implement warranty MCP server (AC: exposes check_warranty tool)
  - [ ] Import MCP SDK server: `from mcp.server import Server, stdio_server`
  - [ ] Create `WarrantyMCPServer` class
  - [ ] Register `check_warranty` tool with server
  - [ ] Tool signature: `check_warranty(serial_number: str) -> Dict[str, Any]`
  - [ ] Implement stdio transport using `stdio_server()`
  - [ ] Add server startup logging

- [ ] Integrate warranty API backend (AC: queries warranty status)
  - [ ] Load warranty API endpoint from environment variable: `WARRANTY_API_URL`
  - [ ] Load API key from environment: `WARRANTY_API_KEY`
  - [ ] Use httpx for async HTTP requests: `import httpx`
  - [ ] Implement API call: `GET /api/warranty/{serial_number}`
  - [ ] Add API key to headers: `Authorization: Bearer {api_key}`
  - [ ] Apply 10-second timeout per NFR20
  - [ ] Parse JSON response: {serial_number, status, expiration_date}

- [ ] Parse warranty API responses (AC: parses valid, expired, not_found)
  - [ ] Handle status: "valid" → {serial_number, status: "valid", expiration_date: ISO8601}
  - [ ] Handle status: "expired" → {serial_number, status: "expired", expiration_date: ISO8601}
  - [ ] Handle 404 → {serial_number, status: "not_found", expiration_date: null}
  - [ ] Handle API errors → raise exception for retry logic
  - [ ] Log: "Warranty checked: serial={serial_number}, status={status}"

- [ ] Create warranty MCP client (AC: client connects to warranty MCP server)
  - [ ] Create `src/guarantee_email_agent/integrations/mcp/warranty_client.py`
  - [ ] Create `WarrantyMCPClient` class
  - [ ] Load server path from config.mcp.warranty_api.server_path
  - [ ] Initialize MCP client with stdio transport to warranty server
  - [ ] Implement `connect()` and `disconnect()` methods
  - [ ] Add connection state tracking

- [ ] Implement check_warranty() client method (AC: queries via MCP)
  - [ ] Create `check_warranty(serial_number: str) -> WarrantyStatus` async method
  - [ ] Call warranty MCP server's check_warranty tool via MCP client
  - [ ] Pass serial_number as parameter
  - [ ] Parse response into WarrantyStatus dataclass
  - [ ] Apply 10-second timeout per NFR20
  - [ ] Apply @retry decorator with max 3 attempts and exponential backoff
  - [ ] Log: "Warranty status retrieved: {serial_number} = {status}"

### Ticketing System Custom MCP Server

- [ ] Create ticketing MCP server directory structure (AC: server in mcp_servers/)
  - [ ] Create `mcp_servers/ticketing_mcp_server/` directory
  - [ ] Create `mcp_servers/ticketing_mcp_server/server.py`
  - [ ] Create `mcp_servers/ticketing_mcp_server/pyproject.toml`
  - [ ] Create `mcp_servers/ticketing_mcp_server/README.md`
  - [ ] Add .gitignore for Python artifacts

- [ ] Implement ticketing MCP server (AC: exposes create_ticket tool)
  - [ ] Import MCP SDK server components
  - [ ] Create `TicketingMCPServer` class
  - [ ] Register `create_ticket` tool with server
  - [ ] Tool signature: `create_ticket(ticket_data: Dict[str, Any]) -> Dict[str, str]`
  - [ ] Implement stdio transport
  - [ ] Add server startup logging

- [ ] Integrate ticketing API backend (AC: creates tickets)
  - [ ] Load ticketing API endpoint: `TICKETING_API_URL`
  - [ ] Load API credentials: `TICKETING_API_KEY`
  - [ ] Use httpx for async HTTP requests
  - [ ] Implement API call: `POST /api/tickets`
  - [ ] Add authentication header
  - [ ] Apply reasonable timeout (30 seconds)

- [ ] Implement ticket creation logic (AC: includes all required fields)
  - [ ] Build ticket payload with required fields:
    - serial_number: str
    - warranty_status: str (valid/expired/not_found)
    - customer_email: str
    - priority: str (high/medium/low)
    - category: str (warranty_inquiry)
  - [ ] POST ticket data to ticketing API
  - [ ] Handle API response: extract ticket_id and confirmation
  - [ ] Validate ticket creation success before returning (NFR21)
  - [ ] Return {ticket_id: str, confirmation: str}
  - [ ] Log: "Ticket created: ticket_id={ticket_id}, customer={customer_email}"

- [ ] Create ticketing MCP client (AC: client connects to ticketing server)
  - [ ] Create `src/guarantee_email_agent/integrations/mcp/ticketing_client.py`
  - [ ] Create `TicketingMCPClient` class
  - [ ] Load server path from config.mcp.ticketing_system.server_path
  - [ ] Initialize MCP client with stdio transport
  - [ ] Implement `connect()` and `disconnect()` methods
  - [ ] Add connection state tracking

- [ ] Implement create_ticket() client method (AC: creates tickets via MCP)
  - [ ] Create `create_ticket(ticket_data: TicketData) -> TicketConfirmation` async method
  - [ ] Convert TicketData dataclass to dict for MCP call
  - [ ] Call ticketing MCP server's create_ticket tool
  - [ ] Parse response into TicketConfirmation dataclass
  - [ ] Apply @retry decorator with max 3 attempts
  - [ ] Validate success before returning per NFR21
  - [ ] Log: "Ticket creation requested: customer={customer_email}"

### Circuit Breaker Implementation

- [ ] Create circuit breaker module (AC: tracks failures per integration)
  - [ ] Create `src/guarantee_email_agent/utils/circuit_breaker.py`
  - [ ] Define CircuitState enum: CLOSED, OPEN, HALF_OPEN
  - [ ] Create `CircuitBreaker` class with state tracking
  - [ ] Track failure count, success count, last failure time
  - [ ] Support configurable thresholds (default 5 failures)
  - [ ] Support configurable timeout (default 60 seconds)

- [ ] Implement circuit breaker state machine (AC: state transitions)
  - [ ] CLOSED state: Allow all calls, track consecutive failures
  - [ ] Transition CLOSED → OPEN: After 5 consecutive failures (NFR18)
  - [ ] OPEN state: Fail fast without calling service
  - [ ] OPEN timeout: 60 seconds before trying HALF_OPEN
  - [ ] HALF_OPEN state: Allow single test call
  - [ ] Transition HALF_OPEN → CLOSED: Single success
  - [ ] Transition HALF_OPEN → OPEN: Single failure
  - [ ] Reset failure count on success in CLOSED state

- [ ] Implement circuit breaker logging (AC: clear state transition logs)
  - [ ] Log CLOSED → OPEN: "Circuit breaker opened for {service} after 5 failures"
  - [ ] Log OPEN → HALF_OPEN: "Circuit breaker half-open for {service}, attempting test call"
  - [ ] Log HALF_OPEN → CLOSED: "Circuit breaker closed for {service} after successful test"
  - [ ] Log HALF_OPEN → OPEN: "Circuit breaker reopened for {service} after failed test"
  - [ ] Log fail-fast: "Circuit breaker OPEN for {service}, failing fast"
  - [ ] Use INFO level for state transitions
  - [ ] Use WARN level for fail-fast rejections

- [ ] Create circuit breaker decorator (AC: easy integration with MCP clients)
  - [ ] Create `@with_circuit_breaker(name: str)` decorator
  - [ ] Lookup or create circuit breaker instance by name
  - [ ] Check circuit state before calling function
  - [ ] If OPEN: raise CircuitBreakerOpenError immediately (fail fast)
  - [ ] If CLOSED or HALF_OPEN: execute function
  - [ ] On success: record success, potentially close circuit
  - [ ] On failure: record failure, potentially open circuit
  - [ ] Return result or raise exception accordingly

- [ ] Integrate circuit breaker with MCP clients (AC: independent breakers per integration)
  - [ ] Add @with_circuit_breaker("gmail") to Gmail MCP methods
  - [ ] Add @with_circuit_breaker("warranty_api") to warranty MCP methods
  - [ ] Add @with_circuit_breaker("ticketing") to ticketing MCP methods
  - [ ] Each integration has independent circuit breaker instance
  - [ ] Circuit breaker wraps retry logic (outer decorator)
  - [ ] Ensure agent continues with other emails when one circuit is OPEN (NFR22)

### Shared Error Handling

- [ ] Define transient vs non-transient errors (AC: retry only transient errors)
  - [ ] Create `src/guarantee_email_agent/utils/errors.py` extensions
  - [ ] TransientError base class: network errors, timeouts, rate limits, 5xx responses
  - [ ] NonTransientError base class: auth failures, 4xx errors (except 429), invalid data
  - [ ] MCPConnectionError (transient): connection failures, stdio errors
  - [ ] MCPTimeoutError (transient): MCP call timeouts
  - [ ] MCPRateLimitError (transient): rate limiting (429)
  - [ ] MCPAuthenticationError (non-transient): auth failures (401, 403)
  - [ ] MCPValidationError (non-transient): invalid requests (400)

- [ ] Implement consistent retry logic (AC: exponential backoff, max 3 attempts)
  - [ ] Use tenacity library for all retries
  - [ ] Standard retry decorator configuration:
    - stop=stop_after_attempt(3)
    - wait=wait_exponential(multiplier=1, min=1, max=10)
    - retry=retry_if_exception_type(TransientError)
  - [ ] Apply to all MCP client methods
  - [ ] Do NOT retry NonTransientError exceptions
  - [ ] Log retry attempts at WARN level

- [ ] Implement contextual error logging (AC: log service, attempt, error type)
  - [ ] On transient error during retry: WARN level
    - "MCP call failed (attempt {n}/3): service={service}, error={error_type}, will retry"
  - [ ] On final failure after retries: ERROR level
    - "MCP call failed after 3 attempts: service={service}, error={error_type}, details={details}"
  - [ ] Include structured context: service name, attempt count, error type, error message
  - [ ] Include stack trace for ERROR level logs (exc_info=True)
  - [ ] Never log sensitive data (API keys, passwords)

- [ ] Implement graceful failure handling (AC: integration failures don't crash agent)
  - [ ] Catch all MCP exceptions at email processing boundary
  - [ ] Log failure with full context
  - [ ] Mark email as unprocessed when critical integration fails
  - [ ] Move to next email without crashing agent
  - [ ] Track failed emails for retry or manual review
  - [ ] Ensure agent continues running (NFR22)

### Testing

- [ ] Create unit tests for Gmail MCP client
  - [ ] Create `tests/integrations/mcp/test_gmail_client.py`
  - [ ] Test monitor_inbox() with mock MCP server
  - [ ] Test send_email() with mock MCP server
  - [ ] Test connection/disconnection lifecycle
  - [ ] Test retry on transient errors
  - [ ] Test no retry on auth errors
  - [ ] Test 30-second timeout enforcement
  - [ ] Test rate limiting handling
  - [ ] Mock MCP SDK for isolated testing

- [ ] Create unit tests for warranty MCP server and client
  - [ ] Create `tests/integrations/mcp/test_warranty_client.py`
  - [ ] Test check_warranty() with valid serial
  - [ ] Test check_warranty() with expired warranty
  - [ ] Test check_warranty() with not found serial
  - [ ] Test 10-second timeout enforcement
  - [ ] Test retry on transient errors
  - [ ] Test warranty API integration (mocked)
  - [ ] Mock httpx for API call testing

- [ ] Create unit tests for ticketing MCP server and client
  - [ ] Create `tests/integrations/mcp/test_ticketing_client.py`
  - [ ] Test create_ticket() with all required fields
  - [ ] Test ticket creation validation (NFR21)
  - [ ] Test retry on transient errors
  - [ ] Test ticketing API integration (mocked)
  - [ ] Mock httpx for API call testing

- [ ] Create unit tests for circuit breaker
  - [ ] Create `tests/utils/test_circuit_breaker.py`
  - [ ] Test CLOSED → OPEN after 5 failures
  - [ ] Test OPEN → HALF_OPEN after 60 seconds
  - [ ] Test HALF_OPEN → CLOSED on success
  - [ ] Test HALF_OPEN → OPEN on failure
  - [ ] Test fail-fast in OPEN state
  - [ ] Test failure count reset on success
  - [ ] Test independent circuit breakers per service
  - [ ] Test state transition logging

- [ ] Create integration tests for end-to-end MCP flows
  - [ ] Create `tests/integration/test_mcp_integration.py`
  - [ ] Test complete email flow: Gmail → Warranty → Ticketing
  - [ ] Test circuit breaker integration with retries
  - [ ] Test partial failure scenarios (one integration down)
  - [ ] Test agent continues processing when one circuit is OPEN
  - [ ] Use test MCP servers for integration testing
  - [ ] Verify error logging and context

## Dev Notes

### Architecture Context

This story implements **MCP Integration Layer (Epic 2)** from the optimized epics, consolidating four original stories (2.1-2.4) into a single comprehensive implementation. This approach reduces context switching and ensures all MCP integrations follow consistent patterns.

**Key Architectural Principles:**
- FR1: Gmail MCP integration for email monitoring
- FR6: Warranty API MCP integration for status validation
- FR19: Ticketing system MCP integration for ticket creation
- FR42, FR43: Retry with exponential backoff and circuit breaker pattern
- NFR17-NFR22: Integration resilience requirements

### Critical Implementation Rules from Project Context

**MCP SDK Version Pinning (MANDATORY):**

The MCP Python SDK is currently at v1.25.0 (stable). v2 is in pre-alpha on main branch with stable release expected Q1 2026.

```python
# pyproject.toml
[project]
dependencies = [
    "mcp>=1.25,<2",  # Pin to v1.x, avoid v2 pre-alpha
    "tenacity>=8.2.0",
    "httpx>=0.25.0",
]
```

**Installation Command:**
```bash
uv add "mcp>=1.25,<2"
```

**Retry Pattern with Tenacity (MANDATORY):**

All MCP calls must use consistent retry logic with exponential backoff:

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from guarantee_email_agent.utils.errors import TransientError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(TransientError)
)
async def mcp_operation():
    # MCP call here
    pass
```

**Exponential Backoff Formula:**
- Wait time = min(initial * 2^n, maximum)
- Initial: 1 second, Multiplier: 1, Min: 1s, Max: 10s
- Retry sequence: 1s, 2s, 4s (capped at 10s)

**Circuit Breaker Pattern (MANDATORY - NFR18):**

```python
from guarantee_email_agent.utils.circuit_breaker import CircuitBreaker, CircuitState

class GmailMCPClient:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            name="gmail",
            failure_threshold=5,  # NFR18: Open after 5 consecutive failures
            timeout=60  # Seconds before attempting HALF_OPEN
        )

    @with_circuit_breaker("gmail")
    @retry(...)
    async def monitor_inbox(self):
        # Implementation
        pass
```

**Error Classification (MANDATORY):**

```python
# Transient Errors - RETRY these
class TransientError(MCPError):
    """Base for all transient errors that should be retried"""
    pass

class MCPConnectionError(TransientError):
    """Connection failures, network errors"""
    pass

class MCPTimeoutError(TransientError):
    """Operation timeouts"""
    pass

class MCPRateLimitError(TransientError):
    """Rate limiting (HTTP 429)"""
    pass

# Non-Transient Errors - DO NOT RETRY
class NonTransientError(MCPError):
    """Base for errors that should NOT be retried"""
    pass

class MCPAuthenticationError(NonTransientError):
    """Authentication failures (401, 403)"""
    pass

class MCPValidationError(NonTransientError):
    """Invalid request data (400)"""
    pass
```

### Gmail MCP Client Implementation Pattern

**Complete Gmail Client Example:**

```python
# src/guarantee_email_agent/integrations/mcp/gmail_client.py
import asyncio
from typing import List, Optional
from mcp import Client, StdioServerParameters
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import TransientError, MCPConnectionError, MCPTimeoutError
from guarantee_email_agent.utils.circuit_breaker import with_circuit_breaker
import logging

logger = logging.getLogger(__name__)

class GmailMCPClient:
    """Gmail MCP client for email monitoring and sending"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client: Optional[Client] = None
        self.connected = False

        # Server parameters for stdio transport
        self.server_params = StdioServerParameters(
            command=config.mcp.gmail.server_path,
            args=config.mcp.gmail.server_args or [],
            env=config.mcp.gmail.server_env or {}
        )

    async def connect(self) -> None:
        """Connect to Gmail MCP server with 30-second timeout"""
        try:
            self.client = Client(self.server_params)
            await asyncio.wait_for(self.client.connect(), timeout=30)
            self.connected = True
            logger.info("Gmail MCP client connected")
        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                message="Gmail MCP connection timeout (30s)",
                code="mcp_connection_timeout",
                details={"service": "gmail", "timeout": 30}
            )
        except Exception as e:
            raise MCPConnectionError(
                message=f"Gmail MCP connection failed: {str(e)}",
                code="mcp_connection_failed",
                details={"service": "gmail", "error": str(e)}
            )

    async def disconnect(self) -> None:
        """Disconnect from Gmail MCP server"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
            logger.info("Gmail MCP client disconnected")

    @with_circuit_breaker("gmail")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def monitor_inbox(self, label: str = "INBOX") -> List[dict]:
        """Monitor Gmail inbox for new emails

        Args:
            label: Gmail label to monitor (default: INBOX)

        Returns:
            List of email messages with metadata

        Raises:
            TransientError: For retryable failures
            NonTransientError: For non-retryable failures
        """
        if not self.connected:
            raise MCPConnectionError(
                message="Gmail client not connected",
                code="mcp_not_connected",
                details={"service": "gmail"}
            )

        try:
            # Call Gmail MCP server's list_messages tool
            result = await asyncio.wait_for(
                self.client.call_tool("list_messages", {"label": label}),
                timeout=30
            )

            messages = result.get("messages", [])
            logger.info(f"Gmail inbox monitored: {len(messages)} emails found in {label}")
            return messages

        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                message="Gmail monitor_inbox timeout (30s)",
                code="mcp_timeout",
                details={"service": "gmail", "operation": "monitor_inbox"}
            )
        except Exception as e:
            # Check if rate limit error (HTTP 429)
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise MCPRateLimitError(
                    message=f"Gmail rate limit hit: {str(e)}",
                    code="mcp_rate_limit",
                    details={"service": "gmail", "error": str(e)}
                )
            raise MCPConnectionError(
                message=f"Gmail monitor_inbox failed: {str(e)}",
                code="mcp_operation_failed",
                details={"service": "gmail", "operation": "monitor_inbox", "error": str(e)}
            )

    @with_circuit_breaker("gmail")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Send email via Gmail

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            thread_id: Optional thread ID for threading replies

        Returns:
            Gmail message ID

        Raises:
            TransientError: For retryable failures
            NonTransientError: For non-retryable failures
        """
        if not self.connected:
            raise MCPConnectionError(
                message="Gmail client not connected",
                code="mcp_not_connected",
                details={"service": "gmail"}
            )

        try:
            # Call Gmail MCP server's send_message tool
            params = {
                "to": to,
                "subject": subject,
                "body": body
            }
            if thread_id:
                params["thread_id"] = thread_id

            result = await asyncio.wait_for(
                self.client.call_tool("send_message", params),
                timeout=30
            )

            message_id = result.get("message_id")
            logger.info(f"Email sent to {to}: subject={subject}, message_id={message_id}")
            return message_id

        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                message="Gmail send_email timeout (30s)",
                code="mcp_timeout",
                details={"service": "gmail", "operation": "send_email", "to": to}
            )
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise MCPRateLimitError(
                    message=f"Gmail rate limit hit: {str(e)}",
                    code="mcp_rate_limit",
                    details={"service": "gmail", "error": str(e)}
                )
            raise MCPConnectionError(
                message=f"Gmail send_email failed: {str(e)}",
                code="mcp_operation_failed",
                details={"service": "gmail", "operation": "send_email", "error": str(e)}
            )
```

### Warranty API MCP Server Implementation Pattern

**Custom MCP Server for Warranty API:**

```python
# mcp_servers/warranty_mcp_server/server.py
import asyncio
import os
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from environment
WARRANTY_API_URL = os.getenv("WARRANTY_API_URL", "https://api.warranty-service.example.com")
WARRANTY_API_KEY = os.getenv("WARRANTY_API_KEY")

if not WARRANTY_API_KEY:
    raise ValueError("WARRANTY_API_KEY environment variable required")

# Create MCP server instance
app = Server("warranty-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="check_warranty",
            description="Check warranty status for a given serial number",
            inputSchema={
                "type": "object",
                "properties": {
                    "serial_number": {
                        "type": "string",
                        "description": "Product serial number to check"
                    }
                },
                "required": ["serial_number"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    if name == "check_warranty":
        return await check_warranty(arguments["serial_number"])
    else:
        raise ValueError(f"Unknown tool: {name}")

async def check_warranty(serial_number: str) -> list[TextContent]:
    """Check warranty status via warranty API

    Args:
        serial_number: Product serial number

    Returns:
        Warranty status: {serial_number, status, expiration_date}
    """
    async with httpx.AsyncClient() as client:
        try:
            # Call warranty API with 10-second timeout (NFR20)
            response = await client.get(
                f"{WARRANTY_API_URL}/api/warranty/{serial_number}",
                headers={"Authorization": f"Bearer {WARRANTY_API_KEY}"},
                timeout=10.0
            )

            if response.status_code == 404:
                # Serial number not found
                result = {
                    "serial_number": serial_number,
                    "status": "not_found",
                    "expiration_date": None
                }
            elif response.status_code == 200:
                # Parse warranty data
                data = response.json()
                result = {
                    "serial_number": serial_number,
                    "status": data.get("status"),  # "valid" or "expired"
                    "expiration_date": data.get("expiration_date")
                }
            else:
                raise Exception(f"Warranty API error: {response.status_code} - {response.text}")

            logger.info(f"Warranty checked: serial={serial_number}, status={result['status']}")

            return [TextContent(
                type="text",
                text=str(result)
            )]

        except httpx.TimeoutException:
            logger.error(f"Warranty API timeout for serial {serial_number}")
            raise Exception("Warranty API timeout (10s)")
        except Exception as e:
            logger.error(f"Warranty API error: {str(e)}")
            raise

async def main():
    """Run warranty MCP server with stdio transport"""
    logger.info("Starting Warranty MCP Server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

**Warranty MCP Client:**

```python
# src/guarantee_email_agent/integrations/mcp/warranty_client.py
import asyncio
from typing import Optional
from dataclasses import dataclass
from mcp import Client, StdioServerParameters
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import TransientError, MCPConnectionError, MCPTimeoutError
from guarantee_email_agent.utils.circuit_breaker import with_circuit_breaker
import logging

logger = logging.getLogger(__name__)

@dataclass
class WarrantyStatus:
    """Warranty status result"""
    serial_number: str
    status: str  # "valid", "expired", "not_found"
    expiration_date: Optional[str]

class WarrantyMCPClient:
    """Warranty API MCP client"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client: Optional[Client] = None
        self.connected = False

        # Server parameters - points to our custom warranty MCP server
        self.server_params = StdioServerParameters(
            command="python",
            args=[config.mcp.warranty_api.server_path],
            env={
                "WARRANTY_API_URL": config.mcp.warranty_api.api_url,
                "WARRANTY_API_KEY": config.secrets.warranty_api_key
            }
        )

    async def connect(self) -> None:
        """Connect to warranty MCP server"""
        try:
            self.client = Client(self.server_params)
            await asyncio.wait_for(self.client.connect(), timeout=30)
            self.connected = True
            logger.info("Warranty MCP client connected")
        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                message="Warranty MCP connection timeout",
                code="mcp_connection_timeout",
                details={"service": "warranty_api"}
            )
        except Exception as e:
            raise MCPConnectionError(
                message=f"Warranty MCP connection failed: {str(e)}",
                code="mcp_connection_failed",
                details={"service": "warranty_api", "error": str(e)}
            )

    async def disconnect(self) -> None:
        """Disconnect from warranty MCP server"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
            logger.info("Warranty MCP client disconnected")

    @with_circuit_breaker("warranty_api")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def check_warranty(self, serial_number: str) -> WarrantyStatus:
        """Check warranty status for serial number

        Args:
            serial_number: Product serial number

        Returns:
            WarrantyStatus with status and expiration

        Raises:
            TransientError: For retryable failures
            NonTransientError: For non-retryable failures
        """
        if not self.connected:
            raise MCPConnectionError(
                message="Warranty client not connected",
                code="mcp_not_connected",
                details={"service": "warranty_api"}
            )

        try:
            # Call warranty MCP server's check_warranty tool with 10s timeout (NFR20)
            result = await asyncio.wait_for(
                self.client.call_tool("check_warranty", {"serial_number": serial_number}),
                timeout=10.0
            )

            # Parse result into WarrantyStatus
            data = eval(result[0].text)  # Convert string representation to dict
            warranty_status = WarrantyStatus(
                serial_number=data["serial_number"],
                status=data["status"],
                expiration_date=data.get("expiration_date")
            )

            logger.info(f"Warranty status retrieved: {serial_number} = {warranty_status.status}")
            return warranty_status

        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                message=f"Warranty check timeout for {serial_number} (10s)",
                code="mcp_timeout",
                details={"service": "warranty_api", "serial_number": serial_number}
            )
        except Exception as e:
            raise MCPConnectionError(
                message=f"Warranty check failed: {str(e)}",
                code="mcp_operation_failed",
                details={"service": "warranty_api", "serial_number": serial_number, "error": str(e)}
            )
```

### Circuit Breaker Implementation Pattern

**Complete Circuit Breaker:**

```python
# src/guarantee_email_agent/utils/circuit_breaker.py
import time
import logging
from enum import Enum
from typing import Callable, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN"""
    pass

class CircuitBreaker:
    """Circuit breaker for service failure protection

    Implements the circuit breaker pattern:
    - CLOSED: Allow all calls, track failures
    - OPEN: Fail fast without calling service
    - HALF_OPEN: Allow test call after timeout
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60
    ):
        """Initialize circuit breaker

        Args:
            name: Circuit breaker name (service identifier)
            failure_threshold: Consecutive failures before opening (default 5 per NFR18)
            timeout: Seconds before attempting HALF_OPEN (default 60)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

        logger.info(f"Circuit breaker initialized: {name} (threshold={failure_threshold}, timeout={timeout}s)")

    def record_success(self) -> None:
        """Record successful call"""
        if self.state == CircuitState.HALF_OPEN:
            # Success in HALF_OPEN → Close circuit
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            logger.info(f"Circuit breaker closed for {self.name} after successful test")
        elif self.state == CircuitState.CLOSED:
            # Success in CLOSED → Reset failure count
            self.failure_count = 0
            self.success_count += 1

    def record_failure(self) -> None:
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failure in HALF_OPEN → Reopen circuit
            self.state = CircuitState.OPEN
            logger.warn(f"Circuit breaker reopened for {self.name} after failed test")
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            # Threshold reached in CLOSED → Open circuit
            self.state = CircuitState.OPEN
            logger.warn(f"Circuit breaker opened for {self.name} after {self.failure_count} failures")

    def can_execute(self) -> bool:
        """Check if call should be allowed

        Returns:
            True if call allowed, False if should fail fast
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.timeout:
                # Transition to HALF_OPEN
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker half-open for {self.name}, attempting test call")
                return True
            else:
                # Still OPEN, fail fast
                logger.warn(f"Circuit breaker OPEN for {self.name}, failing fast")
                return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow single test call
            return True

        return False

# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker instance

    Args:
        name: Circuit breaker name
        **kwargs: CircuitBreaker constructor arguments

    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
    return _circuit_breakers[name]

def with_circuit_breaker(name: str, **breaker_kwargs):
    """Decorator to protect function with circuit breaker

    Args:
        name: Circuit breaker name
        **breaker_kwargs: CircuitBreaker constructor arguments

    Usage:
        @with_circuit_breaker("gmail")
        async def call_gmail_api():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(name, **breaker_kwargs)

            if not breaker.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker OPEN for {name}, failing fast"
                )

            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise

        return wrapper
    return decorator
```

### Configuration Updates

**Update config.yaml schema:**

```yaml
mcp:
  gmail:
    server_path: "path/to/gmail-mcp-server"  # Community Gmail MCP server
    server_args: []
    server_env: {}
    timeout: 30

  warranty_api:
    server_path: "mcp_servers/warranty_mcp_server/server.py"
    api_url: "${WARRANTY_API_URL}"
    timeout: 10

  ticketing_system:
    server_path: "mcp_servers/ticketing_mcp_server/server.py"
    api_url: "${TICKETING_API_URL}"
    timeout: 30
```

**Update .env.example:**

```bash
# Warranty API Configuration
WARRANTY_API_URL=https://api.warranty-service.example.com
WARRANTY_API_KEY=your_warranty_api_key_here

# Ticketing API Configuration
TICKETING_API_URL=https://api.ticketing-service.example.com
TICKETING_API_KEY=your_ticketing_api_key_here

# Gmail MCP Server (if requires credentials)
GMAIL_CREDENTIALS_PATH=/path/to/gmail/credentials.json
```

### Common Pitfalls to Avoid

**❌ NEVER DO THESE:**

1. **Using unstable MCP SDK v2:**
   ```python
   # WRONG - v2 is pre-alpha
   # requirements: mcp>=2.0.0

   # CORRECT - Pin to stable v1.x
   # requirements: mcp>=1.25,<2
   ```

2. **Retrying non-transient errors:**
   ```python
   # WRONG - Retries auth failures forever
   @retry(stop=stop_after_attempt(3))
   async def call_api():
       # Will retry 401 auth errors!

   # CORRECT - Only retry transient errors
   @retry(
       stop=stop_after_attempt(3),
       retry=retry_if_exception_type(TransientError)
   )
   async def call_api():
       # Won't retry 401, only network/timeout errors
   ```

3. **Circuit breaker inside retry decorator:**
   ```python
   # WRONG - Circuit breaker won't work correctly
   @retry(...)
   @with_circuit_breaker("service")
   async def call():
       pass

   # CORRECT - Circuit breaker outside retry
   @with_circuit_breaker("service")
   @retry(...)
   async def call():
       pass
   ```

4. **Blocking async operations:**
   ```python
   # WRONG - Blocks event loop
   def call_mcp():
       client.call_tool("check_warranty", {...})  # Sync call!

   # CORRECT - Async all the way
   async def call_mcp():
       await client.call_tool("check_warranty", {...})
   ```

5. **Forgetting timeout on MCP calls:**
   ```python
   # WRONG - No timeout, could hang forever
   await client.call_tool("send_email", {...})

   # CORRECT - Always timeout
   await asyncio.wait_for(
       client.call_tool("send_email", {...}),
       timeout=30
   )
   ```

6. **Sharing circuit breakers across services:**
   ```python
   # WRONG - All services share one circuit
   @with_circuit_breaker("shared")
   async def call_gmail():
       pass

   @with_circuit_breaker("shared")  # Same name!
   async def call_warranty():
       pass

   # CORRECT - Independent circuit per service
   @with_circuit_breaker("gmail")
   async def call_gmail():
       pass

   @with_circuit_breaker("warranty_api")
   async def call_warranty():
       pass
   ```

### Verification Commands

```bash
# 1. Install MCP SDK and dependencies
uv add "mcp>=1.25,<2" "tenacity>=8.2.0" "httpx>=0.25.0"

# 2. Verify MCP SDK version
uv pip list | grep mcp
# Expected: mcp 1.25.x (not 2.x)

# 3. Create custom MCP server directories
mkdir -p mcp_servers/warranty_mcp_server
mkdir -p mcp_servers/ticketing_mcp_server

# 4. Set up environment variables
cp .env.example .env
# Edit .env with actual API keys

# 5. Test warranty MCP server standalone
cd mcp_servers/warranty_mcp_server
python server.py
# Should start without errors

# 6. Run unit tests
uv run pytest tests/integrations/mcp/ -v
uv run pytest tests/utils/test_circuit_breaker.py -v

# 7. Run integration tests
uv run pytest tests/integration/test_mcp_integration.py -v

# 8. Test complete startup with MCP connection testing
uv run python -m guarantee_email_agent run
# Expected: All MCP connections tested successfully

# 9. Test circuit breaker behavior (manual)
# Disable warranty API temporarily to trigger circuit breaker
# Watch logs for circuit state transitions

# 10. Verify retry behavior
# Check logs for retry attempts on transient failures
# Verify exponential backoff timing (1s, 2s, 4s)
```

### Dependency Notes

**Depends on:**
- Story 1.1: Project structure, src-layout, CLI framework
- Story 1.2: Configuration schema, AgentConfig
- Story 1.3: Environment variable secrets management
- Story 1.4: MCP connection testing infrastructure

**Blocks:**
- Epic 3: Instruction engine needs MCP clients available
- Epic 4: Email processing requires Gmail, warranty, ticketing integrations
- Epic 5: Eval framework needs mocked MCP clients

**Integration Points:**
- Configuration system loads MCP connection strings
- Error hierarchy extends with MCP-specific errors
- Logging system captures MCP operation context
- Startup validation tests MCP connections (Story 1.4 updated)

### Previous Story Intelligence

From Story 1.4 (File Path Verification and MCP Connection Testing):
- Connection testing infrastructure already established
- Exit code 3 for MCP connection failures
- 5-second timeout for connection tests
- Connection testing happens during startup validation
- MCPError class already defined in utils/errors.py

**Learnings to Apply:**
- Story 1.4 implemented connection *testing*, this story implements actual *integration*
- Update Story 1.4's test_mcp_connections() to use real MCP clients from this story
- Reuse existing MCPError hierarchy and extend with specific error types
- Follow established logging patterns from previous stories
- Maintain consistent error message format with actionable details

### Git Intelligence Summary

Recent commits show:
- Stories 1.1-1.3 completed successfully
- Story 1.4 documented and ready for dev
- Consistent use of dataclasses for configuration (AgentConfig pattern)
- Environment variable pattern established (.env.example pattern)
- Testing pattern: tests/ mirrors src/ structure
- All stories use detailed Dev Notes with code examples

**Code Patterns to Continue:**
- Use dataclasses for data structures (WarrantyStatus, TicketData)
- Async/await throughout (asyncio event loop)
- Structured logging with logger.info/warn/error
- Error codes follow pattern: `{component}_{error_type}`
- Comprehensive docstrings with Args/Returns/Raises sections

### References

**Architecture Document Sections:**
- [Source: architecture.md#MCP Integration Architecture] - MCP client patterns
- [Source: architecture.md#Retry and Circuit Breaker Patterns] - Resilience requirements
- [Source: architecture.md#Error Handling] - Error classification
- [Source: project-context.md#MCP SDK Version] - Version pinning requirements
- [Source: project-context.md#Retry Pattern] - Tenacity configuration

**Epic/PRD Context:**
- [Source: epics-optimized.md#Epic 2: MCP Integration Layer] - Consolidated epic
- [Source: epics-optimized.md#Story 2.1] - Complete acceptance criteria
- [Source: prd.md#FR1, FR6, FR19] - MCP integration functional requirements
- [Source: prd.md#FR42, FR43] - Retry and circuit breaker requirements
- [Source: prd.md#NFR17-NFR22] - Integration resilience NFRs
- [Source: prd.md#NFR18] - Circuit breaker threshold (5 failures)
- [Source: prd.md#NFR20] - Warranty API timeout (10 seconds)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

- Comprehensive context analysis completed from PRD, Architecture, Optimized Epics, and previous stories
- Story consolidates 4 original stories (2.1-2.4) into single comprehensive implementation
- MCP Python SDK v1.25.0 research completed, version pinning documented
- Tenacity retry library patterns researched and documented
- Complete implementation patterns for all 3 MCP integrations provided
- Circuit breaker pattern with state machine fully documented
- Error classification (transient vs non-transient) clearly defined
- Integration with existing configuration and error handling established
- Previous story learnings incorporated (Story 1.4 connection testing)
- Git commit patterns analyzed and continued

### File List

**Core MCP Client Files:**
- `src/guarantee_email_agent/integrations/mcp/gmail_client.py` - Gmail MCP client
- `src/guarantee_email_agent/integrations/mcp/warranty_client.py` - Warranty MCP client
- `src/guarantee_email_agent/integrations/mcp/ticketing_client.py` - Ticketing MCP client
- `src/guarantee_email_agent/integrations/mcp/__init__.py` - MCP module exports

**Custom MCP Servers:**
- `mcp_servers/warranty_mcp_server/server.py` - Warranty API MCP server
- `mcp_servers/warranty_mcp_server/pyproject.toml` - Server dependencies
- `mcp_servers/warranty_mcp_server/README.md` - Server documentation
- `mcp_servers/ticketing_mcp_server/server.py` - Ticketing API MCP server
- `mcp_servers/ticketing_mcp_server/pyproject.toml` - Server dependencies
- `mcp_servers/ticketing_mcp_server/README.md` - Server documentation

**Circuit Breaker and Error Handling:**
- `src/guarantee_email_agent/utils/circuit_breaker.py` - Circuit breaker implementation
- `src/guarantee_email_agent/utils/errors.py` - Extended with MCP error types

**Data Models:**
- `src/guarantee_email_agent/integrations/mcp/models.py` - WarrantyStatus, TicketData, etc.

**Configuration Updates:**
- `config.yaml` - Add MCP connection configuration
- `.env.example` - Add WARRANTY_API_KEY, TICKETING_API_KEY

**Tests:**
- `tests/integrations/mcp/test_gmail_client.py` - Gmail client tests
- `tests/integrations/mcp/test_warranty_client.py` - Warranty client tests
- `tests/integrations/mcp/test_ticketing_client.py` - Ticketing client tests
- `tests/utils/test_circuit_breaker.py` - Circuit breaker tests
- `tests/integration/test_mcp_integration.py` - End-to-end MCP tests
