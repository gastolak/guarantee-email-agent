# Story 4.6: Refactor MCP Clients to Simple Tool Architecture

Status: ready-for-dev

## Story

As a warranty email agent developer,
I want to remove the MCP client abstraction layer and replace it with simple direct API tool implementations,
so that the architecture is simpler, has fewer dependencies, and eliminates unnecessary MCP protocol overhead.

## Acceptance Criteria

**Given** The current MCP-based architecture with function calling (Story 4.5 complete)
**When** I refactor to simple tools
**Then** The following criteria are met:

**AC1 - Remove MCP Dependencies:**
**And** MCP SDK package removed from `pyproject.toml`
**And** All MCP imports deleted from codebase
**And** `src/guarantee_email_agent/integrations/mcp/` directory deleted (8 files)
**And** `tests/integrations/mcp/` directory deleted (4 files)
**And** No references to "mcp" remain in code (except historical docs/comments)

**AC2 - Simple Tool Implementations Created:**
**And** New module `src/guarantee_email_agent/tools/` exists with:
**And** `gmail_tool.py`: Direct Gmail API integration (fetch unread, send email, mark as read)
**And** `crm_abacus_tool.py`: Direct CRM Abacus integration with:
  - Token acquisition via POST `/token` with username/password form data
  - Token caching and automatic refresh
  - Warranty check via GET `/klienci/znajdz_po_numerze_seryjnym/?serial={serial}`
  - Ticket creation via POST `/zadania/dodaj_zadanie/` with JSON body
  - Bearer token authentication for all protected endpoints
**And** Each tool uses `httpx.AsyncClient` for async HTTP
**And** Each tool has `@retry` decorator with exponential backoff (3 attempts, 1-10s wait)
**And** Each tool has built-in `CircuitBreaker` (threshold=5 failures)
**And** Each tool has structured logging with `extra={"tool": name, "operation": op}`
**And** Each tool raises `AgentError` subclasses on failures

**AC3 - Simplified Config Structure:**
**And** `config.yaml` has new `tools` section replacing `mcp` section:
```yaml
tools:
  gmail:
    api_endpoint: "https://gmail.googleapis.com/gmail/v1"
    timeout_seconds: 10
  crm_abacus:
    base_url: "http://crmabacus.suntar.pl:43451"
    token_endpoint: "/token"
    warranty_endpoint: "/klienci/znajdz_po_numerze_seryjnym/"
    ticketing_endpoint: "/zadania/dodaj_zadanie/"
    ticket_info_endpoint: "/zadania/{zadanie_id}/info/"
    task_info_endpoint: "/zadania/{zadanie_id}"
    task_feature_check_endpoint: "/zadania/{zadanie_id}/cechy/check"
    timeout_seconds: 10
    # Default IDs for ticket creation (per API spec)
    ticket_defaults:
      dzial_id: 2                    # Customer Service Department
      typ_zadania_id: 156            # Service Request
      typ_wykonania_id: 184          # Awaiting Review
      organizacja_id: 1              # Suntar
      unrecognized_klient_id: 702    # Default when client not found
    # Feature flag for disabling agent responses
    agent_disable_feature_name: "Wyłącz agenta AI"
```
**And** `src/guarantee_email_agent/config/schema.py` updated with `ToolConfig` classes
**And** Config validation updated for new structure
**And** `.env.example` updated with:
  - `GMAIL_OAUTH_TOKEN` (Gmail API requires OAuth2)
  - `CRM_ABACUS_USERNAME` (for token acquisition)
  - `CRM_ABACUS_PASSWORD` (for token acquisition)

**AC4 - FunctionDispatcher Simplified:**
**And** `src/guarantee_email_agent/llm/function_dispatcher.py` routes to tools instead of MCP clients
**And** Constructor takes tool instances: `FunctionDispatcher(gmail_tool, crm_abacus_tool)`
**And** Function name mapping unchanged: `check_warranty`, `create_ticket`, `send_email`
**And** Routes `check_warranty` and `create_ticket` to `crm_abacus_tool` methods
**And** Routes `send_email` to `gmail_tool` method
**And** Method signatures unchanged (backward compatible with Story 4.5)
**And** Logging messages updated to reference "tool" instead of "mcp_client"

**AC5 - Startup Validation Simplified:**
**And** `src/guarantee_email_agent/agent/startup.py` removes MCP connection testing
**And** Replaces with simple HTTP endpoint reachability checks (HEAD request)
**And** Validates API keys are present in environment
**And** Fails fast with clear error messages: "WARRANTY_API_KEY not found in environment"
**And** Exit code 2 (config error) for missing API keys
**And** Exit code 3 (integration error) for unreachable endpoints

**AC6 - EmailProcessor Updated:**
**And** `src/guarantee_email_agent/email/processor.py` initializes tools instead of MCP clients
**And** Passes tools to `FunctionDispatcher`
**And** No other logic changes (function calling flow unchanged)
**And** Logging context updated

**AC7 - Agent Runner Updated:**
**And** `src/guarantee_email_agent/agent/runner.py` initializes tools from config
**And** Removes MCP client initialization and connection logic
**And** Tool cleanup on shutdown: `await tool.close()` for each tool
**And** No disconnect logic needed (tools don't maintain persistent connections)

**AC8 - CLI Updated:**
**And** `src/guarantee_email_agent/cli.py` removes MCP validation commands
**And** Config loading updated for new schema
**And** Help text updated
**And** No functional changes to `agent run` or `agent eval` commands

**AC9 - Eval Framework Updated:**
**And** `src/guarantee_email_agent/eval/mocks.py` provides mock tool implementations
**And** Mock tools return same responses as old MCP mocks (backward compatible)
**And** `src/guarantee_email_agent/eval/runner.py` uses mock tools
**And** Eval scenarios unchanged (zero modifications to YAML files)
**And** Function call validation unchanged (backward compatible with Story 4.5)

**AC10 - Complete Test Coverage:**
**And** New tests created in `tests/tools/` for all three tools
**And** Tests use `pytest-httpx` for HTTP mocking
**And** All existing tests updated to use tools instead of MCP clients:
  - `tests/agent/test_startup.py`
  - `tests/agent/test_runner.py`
  - `tests/email/test_processor.py`
  - `tests/llm/test_function_dispatcher.py`
  - `tests/config/test_loader.py`
**And** Test coverage maintained at current level (≥90%)
**And** All tests pass: `uv run pytest` returns 0

**AC11 - NFRs Maintained:**
**And** **NFR1**: Eval pass rate ≥99% (run `uv run guarantee-email-agent eval`)
**And** **NFR7**: Processing time <60s per email (measured in eval)
**And** **NFR5**: All tool calls logged with structured context
**And** **NFR17-21**: Retry with exponential backoff, circuit breaker pattern maintained
**And** **NFR29**: Exit codes unchanged (0=success, 2=config, 3=integration, 4=eval)
**And** Error handling patterns unchanged (AgentError hierarchy)

**AC12 - Documentation Updated:**
**And** `_bmad-output/planning-artifacts/architecture.md` updated with tool architecture
**And** `RUNNING.md` updated with new config structure
**And** `docs/deployment.md` references tools instead of MCP
**And** Inline code comments updated
**And** `config.yaml` has clear comments explaining tool configuration

## Tasks / Subtasks

- [ ] **Task 1: Add httpx dependencies** (AC: 1, 2)
  - [ ] Add `httpx` to `pyproject.toml` dependencies
  - [ ] Add `pytest-httpx` to dev dependencies
  - [ ] Run `uv sync` to update lock file

- [ ] **Task 2: Create tool module structure** (AC: 2)
  - [ ] Create `src/guarantee_email_agent/tools/__init__.py`
  - [ ] Create `tests/tools/__init__.py`

- [ ] **Task 3: Implement GmailTool** (AC: 2)
  - [ ] Create `src/guarantee_email_agent/tools/gmail_tool.py`
  - [ ] Implement `__init__(api_endpoint, oauth_token, timeout)`
  - [ ] Implement `async def fetch_unread_emails() -> List[EmailMessage]`
  - [ ] Implement `async def send_email(to, subject, body, thread_id) -> str`
  - [ ] Implement `async def mark_as_read(message_id) -> None`
  - [ ] Add retry decorator with exponential backoff
  - [ ] Add circuit breaker
  - [ ] Add structured logging
  - [ ] Implement `async def close()`

- [ ] **Task 4: Implement CrmAbacusTool** (AC: 2) [See 4-6-crm-abacus-api-spec.md for complete API details]
  - [ ] Create `src/guarantee_email_agent/tools/crm_abacus_tool.py`
  - [ ] Implement `__init__(base_url, username, password, endpoints, defaults, timeout)`
    - Store config: base_url, credentials, endpoint paths, default IDs
    - Initialize httpx.AsyncClient (no auth header yet - token acquired dynamically)
    - Initialize CircuitBreaker (threshold=5)
    - Initialize token cache: `self._token = None`
  - [ ] Implement `async def _acquire_token() -> str`
    - POST `/token` with `application/x-www-form-urlencoded`
    - Body: `username={username}&password={password}`
    - Extract `access_token` from response
    - Cache in `self._token`
    - Return token string
  - [ ] Implement `async def _request_with_auth(method, url, **kwargs) -> httpx.Response`
    - Helper method: adds Bearer token to requests
    - If no token cached, call `_acquire_token()`
    - Add `Authorization: Bearer {token}` header
    - Make request, if 401 response: refresh token and retry once
    - Return response
  - [ ] Implement `async def find_device_by_serial(serial_number: str) -> dict`
    - GET `/klienci/znajdz_po_numerze_seryjnym/?serial={serial}`
    - Use `_request_with_auth()` helper
    - Return raw SerialKlient response with fields: `urzadzenie_id`, `klient_id`, `nazwa`, `serial`, `data_stop`, `producent_gwarancja_stop`, `typ_gwarancji`, etc.
    - Raise IntegrationError on 404 or network errors
  - [ ] Implement `async def check_warranty(serial_number: str) -> dict`
    - Call `find_device_by_serial(serial_number)`
    - Determine warranty status using **date-based validation** (see 4-6-crm-abacus-api-spec.md):
      1. Check `data_stop` (service contract end date) - if exists and >= today → "valid" (type: "service_contract")
      2. Check `producent_gwarancja_stop` (manufacturer warranty end) - if exists and >= today → "valid" (type: "manufacturer")
      3. If both null → "not_found"
      4. If both expired → "expired"
    - Return dict: `{"status": "valid"|"expired"|"not_found", "warranty_type": "service_contract"|"manufacturer"|null, "expires": "YYYY-MM-DD"|null, "device_name": str, "serial": str, "klient_id": int|null}`
    - Handle 404 → return `{"status": "not_found"}`
  - [ ] Implement `async def create_ticket(subject: str, description: str, customer_email=None, priority=None) -> str`
    - Parse subject to extract device_name and serial (format: "{device_name}:{serial}")
    - Call `find_device_by_serial(serial)` to get klient_id
    - POST `/zadania/dodaj_zadanie/` with JSON body:
      - `dzial_id`: 2 (from defaults)
      - `typ_zadania_id`: 156 (from defaults)
      - `typ_wykonania_id`: 184 (from defaults)
      - `organizacja_id`: 1 (from defaults)
      - `klient_id`: from find_device response
      - `temat`: subject (already formatted as "{device_name}:{serial}")
      - `opis`: description
    - Extract `nowe_zadanie_id` from response
    - Return task ID as string
    - Note: customer_email and priority params ignored (for LLM compatibility)
  - [ ] Implement `async def add_ticket_info(zadanie_id: int, info_text: str) -> None`
    - POST `/zadania/{zadanie_id}/info/` with JSON body (note trailing slash):
      - `opis`: info_text
      - `publiczne`: false
      - `operacja_id`: 0
    - No return value (fire and forget)
  - [ ] Implement `async def get_task_info(zadanie_id: int) -> dict`
    - GET `/zadania/{zadanie_id}` with Bearer auth
    - Return full Zadanie response with fields: `zadanie_id`, `klient_id`, `temat`, `opis`, `data_dodania`, etc.
    - Raise IntegrationError on 404 or network errors
    - Use case: Retrieve task details before processing
  - [ ] Implement `async def check_agent_disabled(zadanie_id: int) -> bool`
    - GET `/zadania/{zadanie_id}/cechy/check?nazwa_cechy=Wyłącz agenta AI`
    - Parse response field `posiada_ceche` (boolean)
    - Return True if agent should be disabled for this task, False otherwise
    - Handle 404 → return False (task not found, safe to proceed)
    - **CRITICAL**: This check must be called before generating AI responses
    - Log result: "Agent disabled for task {zadanie_id}: {result}"
  - [ ] Add `@retry` decorator to all public methods (3 attempts, exponential backoff 1-10s)
  - [ ] Add circuit breaker to all API methods
  - [ ] Add structured logging: log all requests/responses with `extra={"tool": "crm_abacus", "operation": name, ...}`
  - [ ] Implement `async def close()` - close httpx client

- [ ] **Task 5: Write tool tests** (AC: 2, 10)
  - [ ] Create `tests/tools/test_gmail_tool.py`
  - [ ] Create `tests/tools/test_crm_abacus_tool.py`
  - [ ] Use `pytest-httpx` for HTTP mocking
  - [ ] Test success cases (including token acquisition and caching)
  - [ ] Test token refresh logic
  - [ ] Test retry logic
  - [ ] Test circuit breaker
  - [ ] Test error handling (401 unauthorized, 404 not found, etc.)
  - [ ] Verify all tool tests pass

- [ ] **Task 6: Update config schema** (AC: 3)
  - [ ] Modify `src/guarantee_email_agent/config/schema.py`
  - [ ] Remove `McpConnectionConfig` and related classes
  - [ ] Add `GmailToolConfig` with fields: `api_endpoint`, `timeout_seconds`
  - [ ] Add `TicketDefaults` dataclass with fields: `dzial_id`, `typ_zadania_id`, `typ_wykonania_id`, `organizacja_id`, `unrecognized_klient_id`
  - [ ] Add `CrmAbacusToolConfig` with fields:
    - `base_url`, `token_endpoint`, `warranty_endpoint`, `ticketing_endpoint`
    - `ticket_info_endpoint`, `task_info_endpoint`, `task_feature_check_endpoint`
    - `timeout_seconds`, `ticket_defaults: TicketDefaults`
    - `agent_disable_feature_name` (default: "Wyłącz agenta AI")
  - [ ] Add `ToolsConfig` container class with `gmail: GmailToolConfig` and `crm_abacus: CrmAbacusToolConfig` fields
  - [ ] Update `AgentConfig` to have `tools: ToolsConfig` field
  - [ ] Update validation logic

- [ ] **Task 7: Update config.yaml** (AC: 3)
  - [ ] Replace `mcp:` section with `tools:` section
  - [ ] Add Gmail tool configuration
  - [ ] Add CRM Abacus tool configuration with all endpoints
  - [ ] Add clear comments explaining each field
  - [ ] Remove MCP-related comments

- [ ] **Task 8: Update .env.example** (AC: 3)
  - [ ] Replace MCP-related variables with tool variables
  - [ ] Add `GMAIL_OAUTH_TOKEN` with comment on OAuth2 setup
  - [ ] Add `CRM_ABACUS_USERNAME` (for token acquisition)
  - [ ] Add `CRM_ABACUS_PASSWORD` (for token acquisition)
  - [ ] Add comments explaining each variable and token acquisition flow

- [ ] **Task 9: Update FunctionDispatcher** (AC: 4)
  - [ ] Modify `src/guarantee_email_agent/llm/function_dispatcher.py`
  - [ ] Change constructor: `__init__(gmail_tool, crm_abacus_tool)`
  - [ ] Route `check_warranty` to `crm_abacus_tool.check_warranty()`
  - [ ] Route `create_ticket` to `crm_abacus_tool.create_ticket()`
  - [ ] Route `send_email` to `gmail_tool.send_email()`
  - [ ] Update logging messages (replace "mcp_client" with "tool")
  - [ ] Verify method signatures unchanged
  - [ ] Update unit tests in `tests/llm/test_function_dispatcher.py`

- [ ] **Task 10: Update startup validation** (AC: 5)
  - [ ] Modify `src/guarantee_email_agent/agent/startup.py`
  - [ ] Remove MCP connection testing functions
  - [ ] Add `validate_api_keys()` function (check GMAIL_OAUTH_TOKEN, CRM_ABACUS_USERNAME, CRM_ABACUS_PASSWORD)
  - [ ] Add `check_endpoint_reachability()` function (HTTP HEAD to CRM Abacus base URL)
  - [ ] Update error messages
  - [ ] Update exit codes (2 for config, 3 for integration)
  - [ ] Update tests in `tests/agent/test_startup.py`

- [ ] **Task 11: Update EmailProcessor** (AC: 6)
  - [ ] Modify `src/guarantee_email_agent/email/processor.py`
  - [ ] Change tool initialization from MCP clients to tools (gmail_tool, crm_abacus_tool)
  - [ ] Update `FunctionDispatcher` initialization with new tool instances
  - [ ] Update logging context
  - [ ] Verify no other logic changes
  - [ ] Update tests in `tests/email/test_processor.py`

- [ ] **Task 12: Update agent runner** (AC: 7)
  - [ ] Modify `src/guarantee_email_agent/agent/runner.py`
  - [ ] Remove MCP client initialization
  - [ ] Add gmail_tool and crm_abacus_tool initialization from config
  - [ ] Update shutdown logic: call `await tool.close()` for each tool
  - [ ] Remove MCP disconnect logic
  - [ ] Update tests in `tests/agent/test_runner.py`

- [ ] **Task 13: Update CLI** (AC: 8)
  - [ ] Modify `src/guarantee_email_agent/cli.py`
  - [ ] Remove MCP validation commands
  - [ ] Update config loading
  - [ ] Update help text
  - [ ] Update tests in `tests/test_cli.py`

- [ ] **Task 14: Create eval mock tools** (AC: 9)
  - [ ] Modify `src/guarantee_email_agent/eval/mocks.py`
  - [ ] Create `MockGmailTool` class
  - [ ] Create `MockCrmAbacusTool` class (combines warranty + ticketing)
  - [ ] Ensure return values match old MCP mocks (backward compatible)

- [ ] **Task 15: Update eval runner** (AC: 9)
  - [ ] Modify `src/guarantee_email_agent/eval/runner.py`
  - [ ] Use mock tools instead of mock MCP clients
  - [ ] Verify function call validation unchanged
  - [ ] Verify no changes needed to eval scenarios

- [ ] **Task 16: Update remaining tests** (AC: 10)
  - [ ] Update `tests/config/test_loader.py`
  - [ ] Remove `tests/config/test_mcp_tester.py`
  - [ ] Update any integration tests
  - [ ] Run full test suite: `uv run pytest`
  - [ ] Verify all tests pass

- [ ] **Task 17: Remove MCP code** (AC: 1)
  - [ ] Delete `src/guarantee_email_agent/integrations/mcp/` (4 files)
  - [ ] Delete `tests/integrations/mcp/` (4 files)
  - [ ] Remove MCP SDK from `pyproject.toml`
  - [ ] Run `uv sync` to update lock file
  - [ ] Search codebase for "mcp" references (except docs)

- [ ] **Task 18: Update architecture.md** (AC: 12)
  - [ ] Modify `_bmad-output/planning-artifacts/architecture.md`
  - [ ] Replace MCP architecture section with tool architecture
  - [ ] Document CRM Abacus token acquisition flow
  - [ ] Update integration patterns
  - [ ] Update sequence diagrams if present

- [ ] **Task 19: Update RUNNING.md** (AC: 12)
  - [ ] Update config structure documentation
  - [ ] Update environment variable setup (CRM_ABACUS_USERNAME/PASSWORD)
  - [ ] Document token acquisition and caching mechanism
  - [ ] Update startup instructions
  - [ ] Remove MCP setup steps

- [ ] **Task 20: Update deployment docs** (AC: 12)
  - [ ] Modify `docs/deployment.md`
  - [ ] Replace MCP references with tool references
  - [ ] Update Docker configuration if needed
  - [ ] Update systemd/launchd examples

- [ ] **Task 21: Update inline comments** (AC: 12)
  - [ ] Search for MCP-related comments in code
  - [ ] Update to reference tools
  - [ ] Update `config.yaml` comments

- [ ] **Task 22: Run full validation** (AC: 11)
  - [ ] Run full test suite: `uv run pytest`
  - [ ] Verify 100% test pass
  - [ ] Run eval suite: `uv run guarantee-email-agent eval`
  - [ ] Verify ≥99% eval pass rate
  - [ ] Measure processing time (verify <60s)
  - [ ] Test `agent run` command manually
  - [ ] Test graceful shutdown (Ctrl+C)
  - [ ] Verify structured logging output format

## Dev Notes

### Architecture Transformation

**Before (MCP-based):**
```
EmailProcessor → FunctionDispatcher → MCP Clients → MCP Protocol → External APIs
                                        ↓
                                   - Connection management
                                   - Protocol serialization
                                   - MCP SDK dependency
```

**After (Simple tools):**
```
EmailProcessor → FunctionDispatcher → Tools → httpx → External APIs
                                        ↓
                                   - Direct HTTP calls
                                   - Built-in retry
                                   - Built-in circuit breaker
                                   - Standard HTTP client
```

### Tool Implementation Template

**CRM Abacus Tool (with token management):**

```python
"""CRM Abacus tool for warranty checks and ticket creation."""
import httpx
from datetime import datetime, timedelta
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from guarantee_email_agent.utils.circuit_breaker import CircuitBreaker
from guarantee_email_agent.utils.errors import AgentError, IntegrationError
import logging

logger = logging.getLogger(__name__)


class CrmAbacusTool:
    """Direct CRM Abacus API integration with token management."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        token_endpoint: str,
        warranty_endpoint: str,
        ticketing_endpoint: str,
        timeout: int = 10
    ):
        """Initialize CRM Abacus tool.

        Args:
            base_url: Base URL (e.g., "http://crmabacus.suntar.pl:43451")
            username: Username for token acquisition
            password: Password for token acquisition
            token_endpoint: Token endpoint path (e.g., "/token")
            warranty_endpoint: Warranty check endpoint path
            ticketing_endpoint: Ticket creation endpoint path
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token_endpoint = token_endpoint
        self.warranty_endpoint = warranty_endpoint
        self.ticketing_endpoint = ticketing_endpoint
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(failure_threshold=5)
        self.client = httpx.AsyncClient(timeout=timeout)

        # Token caching
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _acquire_token(self) -> str:
        """Acquire access token via form-encoded POST.

        Returns:
            Access token string

        Raises:
            IntegrationError: If token acquisition fails
        """
        try:
            logger.info(
                "Acquiring CRM Abacus access token",
                extra={"tool": "crm_abacus", "operation": "acquire_token"}
            )

            response = await self.client.post(
                f"{self.base_url}{self.token_endpoint}",
                data={
                    "username": self.username,
                    "password": self.password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()

            self._access_token = token_data["access_token"]
            # Assume 1-hour expiry (adjust based on API response)
            self._token_expires_at = datetime.now() + timedelta(hours=1)

            logger.info(
                "Token acquired successfully",
                extra={"tool": "crm_abacus", "operation": "acquire_token"}
            )
            return self._access_token

        except httpx.HTTPError as e:
            logger.error(
                f"Token acquisition failed: {e}",
                extra={"tool": "crm_abacus", "operation": "acquire_token", "error": str(e)}
            )
            raise IntegrationError(f"CRM Abacus token error: {e}") from e

    async def _get_valid_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if not self._access_token or not self._token_expires_at:
            return await self._acquire_token()

        # Refresh 5 minutes before expiry
        if datetime.now() >= self._token_expires_at - timedelta(minutes=5):
            return await self._acquire_token()

        return self._access_token

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def check_warranty(self, serial_number: str) -> dict:
        """Check warranty status by serial number using date-based validation.

        Args:
            serial_number: Device serial number

        Returns:
            Simplified warranty status dict:
            {
                "status": "valid"|"expired"|"not_found",
                "warranty_type": "service_contract"|"manufacturer"|null,
                "expires": "YYYY-MM-DD"|null,
                "device_name": str,
                "serial": str,
                "klient_id": int|null
            }

        Raises:
            IntegrationError: If API call fails after retries
        """
        from datetime import date

        async with self.circuit_breaker:
            try:
                token = await self._get_valid_token()

                logger.info(
                    "Checking warranty",
                    extra={"tool": "crm_abacus", "operation": "check_warranty", "serial": serial_number}
                )

                response = await self.client.get(
                    f"{self.base_url}{self.warranty_endpoint}",
                    params={"serial": serial_number},
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                device_data = response.json()

                # Date-based warranty validation (see 4-6-crm-abacus-api-spec.md)
                today = date.today()
                status_info = {
                    "status": "not_found",
                    "warranty_type": None,
                    "expires": None,
                    "device_name": device_data.get("nazwa"),
                    "serial": device_data.get("serial"),
                    "klient_id": device_data.get("klient_id")
                }

                # Check service contract first (higher priority)
                if device_data.get("data_stop"):
                    contract_end = date.fromisoformat(device_data["data_stop"])
                    if contract_end >= today:
                        status_info.update({
                            "status": "valid",
                            "warranty_type": "service_contract",
                            "expires": device_data["data_stop"]
                        })
                        logger.info("Valid service contract", extra={"expires": device_data["data_stop"]})
                        return status_info
                    else:
                        status_info["status"] = "expired"

                # Check manufacturer warranty
                if device_data.get("producent_gwarancja_stop"):
                    mfg_end = date.fromisoformat(device_data["producent_gwarancja_stop"])
                    if mfg_end >= today:
                        status_info.update({
                            "status": "valid",
                            "warranty_type": "manufacturer",
                            "expires": device_data["producent_gwarancja_stop"]
                        })
                        logger.info("Valid manufacturer warranty", extra={"expires": device_data["producent_gwarancja_stop"]})
                        return status_info
                    elif status_info["status"] != "expired":
                        status_info["status"] = "expired"

                logger.info(
                    f"Warranty status: {status_info['status']}",
                    extra={"tool": "crm_abacus", "operation": "check_warranty", "status": status_info}
                )
                return status_info

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Device not found: {serial_number}")
                    return {
                        "status": "not_found",
                        "warranty_type": None,
                        "expires": None,
                        "device_name": None,
                        "serial": serial_number,
                        "klient_id": None
                    }
                logger.error(
                    f"Warranty check failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "check_warranty", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus warranty error: {e}") from e
            except httpx.HTTPError as e:
                logger.error(
                    f"Warranty check failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "check_warranty", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus warranty error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def create_ticket(
        self,
        subject: str,
        description: str,
        customer_email: str,
        priority: str
    ) -> str:
        """Create support ticket.

        Args:
            subject: Ticket subject
            description: Ticket description
            customer_email: Customer email
            priority: Priority level

        Returns:
            Ticket ID

        Raises:
            IntegrationError: If API call fails after retries
        """
        async with self.circuit_breaker:
            try:
                token = await self._get_valid_token()

                logger.info(
                    "Creating ticket",
                    extra={"tool": "crm_abacus", "operation": "create_ticket", "subject": subject}
                )

                response = await self.client.post(
                    f"{self.base_url}{self.ticketing_endpoint}",
                    json={
                        "dzial_id": 2,
                        "typ_zadania_id": 156,
                        "typ_wykonania_id": 184,
                        "organizacja_id": 1,
                        "temat": subject,
                        "opis": description
                    },
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()
                ticket_id = result.get("zadanie_id", result.get("id"))

                logger.info(
                    "Ticket created successfully",
                    extra={"tool": "crm_abacus", "operation": "create_ticket", "ticket_id": ticket_id}
                )
                return str(ticket_id)

            except httpx.HTTPError as e:
                logger.error(
                    f"Ticket creation failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "create_ticket", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus ticketing error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_task_info(self, zadanie_id: int) -> dict:
        """Get full task/ticket information by ID.

        Args:
            zadanie_id: Task ID

        Returns:
            Full Zadanie response dict

        Raises:
            IntegrationError: If API call fails after retries
        """
        async with self.circuit_breaker:
            try:
                token = await self._get_valid_token()

                logger.info(
                    "Fetching task info",
                    extra={"tool": "crm_abacus", "operation": "get_task_info", "zadanie_id": zadanie_id}
                )

                response = await self.client.get(
                    f"{self.base_url}/zadania/{zadanie_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    "Task info retrieved",
                    extra={"tool": "crm_abacus", "operation": "get_task_info", "zadanie_id": zadanie_id}
                )
                return result

            except httpx.HTTPError as e:
                logger.error(
                    f"Task info fetch failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "get_task_info", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus task info error: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def check_agent_disabled(self, zadanie_id: int) -> bool:
        """Check if AI agent is disabled for this task via feature flag.

        Args:
            zadanie_id: Task ID to check

        Returns:
            True if agent should NOT respond (disabled), False if agent can respond

        Raises:
            IntegrationError: If API call fails after retries
        """
        async with self.circuit_breaker:
            try:
                token = await self._get_valid_token()

                logger.info(
                    "Checking agent disabled flag",
                    extra={"tool": "crm_abacus", "operation": "check_agent_disabled", "zadanie_id": zadanie_id}
                )

                response = await self.client.get(
                    f"{self.base_url}/zadania/{zadanie_id}/cechy/check",
                    params={"nazwa_cechy": "Wyłącz agenta AI"},
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()

                agent_disabled = result.get("posiada_ceche", False)

                logger.warning(
                    f"Agent disabled for task {zadanie_id}: {agent_disabled}",
                    extra={"tool": "crm_abacus", "operation": "check_agent_disabled", "disabled": agent_disabled}
                )
                return agent_disabled

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.info(f"Task {zadanie_id} not found, agent can respond")
                    return False  # Task not found, safe to proceed
                logger.error(
                    f"Agent disabled check failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "check_agent_disabled", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus agent check error: {e}") from e
            except httpx.HTTPError as e:
                logger.error(
                    f"Agent disabled check failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "check_agent_disabled", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus agent check error: {e}") from e

    async def close(self):
        """Close HTTP client connection pool."""
        await self.client.aclose()
```

### Config Migration Example

**Old config.yaml (MCP-based):**
```yaml
mcp:
  gmail:
    connection_string: "mcp://gmail"
  ticketing_system:
    connection_string: "mcp://ticketing"
    endpoint: "https://tickets.example.com/api/v1"
  warranty_api:
    connection_string: "mcp://warranty-api"
    endpoint: "https://api.example.com/warranty/check"
```

**New config.yaml (Tool-based):**
```yaml
tools:
  gmail:
    api_endpoint: "https://gmail.googleapis.com/gmail/v1"
    timeout_seconds: 10
  crm_abacus:
    base_url: "http://crmabacus.suntar.pl:43451"
    token_endpoint: "/token"
    warranty_endpoint: "/klienci/znajdz_po_numerze_seryjnym/"
    ticketing_endpoint: "/zadania/dodaj_zadanie/"
    ticket_info_endpoint: "/zadania/{zadanie_id}/info/"
    task_info_endpoint: "/zadania/{zadanie_id}"
    task_feature_check_endpoint: "/zadania/{zadanie_id}/cechy/check"
    timeout_seconds: 10
    ticket_defaults:
      dzial_id: 2
      typ_zadania_id: 156
      typ_wykonania_id: 184
      organizacja_id: 1
      unrecognized_klient_id: 702
    agent_disable_feature_name: "Wyłącz agenta AI"
```

### Test Migration Example

**Before (MCP mock):**
```python
@pytest.fixture
def mock_warranty_client():
    """Mock MCP warranty client."""
    client = AsyncMock()
    client.call_tool.return_value = {
        "status": "valid",
        "expires": "2025-12-31"
    }
    return client

async def test_warranty_check(mock_warranty_client):
    result = await mock_warranty_client.call_tool("check_warranty", {"serial_number": "ABC123"})
    assert result["status"] == "valid"
```

**After (HTTP mock with token flow):**
```python
@pytest.mark.asyncio
async def test_warranty_check(httpx_mock):
    """Test CRM Abacus warranty check with token acquisition."""
    # Mock token acquisition
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/token",
        json={"access_token": "test-token-123", "expires_in": 3600}
    )

    # Mock warranty check
    httpx_mock.add_response(
        url="http://crmabacus.suntar.pl:43451/klienci/znajdz_po_numerze_seryjnym/?serial=ABC123",
        json={"status": "valid", "expires": "2025-12-31", "klient_id": 456}
    )

    tool = CrmAbacusTool(
        base_url="http://crmabacus.suntar.pl:43451",
        username="testowy",
        password="test-password",
        token_endpoint="/token",
        warranty_endpoint="/klienci/znajdz_po_numerze_seryjnym/",
        ticketing_endpoint="/zadania/dodaj_zadanie/",
        timeout=10
    )
    result = await tool.check_warranty("ABC123")
    assert result["status"] == "valid"
    await tool.close()
```

### Files to Delete (12 files total)

**MCP Integration Layer (8 files):**
- `src/guarantee_email_agent/integrations/mcp/__init__.py`
- `src/guarantee_email_agent/integrations/mcp/gmail_client.py`
- `src/guarantee_email_agent/integrations/mcp/ticketing_client.py`
- `src/guarantee_email_agent/integrations/mcp/warranty_client.py`
- `tests/integrations/mcp/__init__.py`
- `tests/integrations/mcp/test_gmail_client.py`
- `tests/integrations/mcp/test_ticketing_client.py`
- `tests/integrations/mcp/test_warranty_client.py`

**MCP Config Testing (1 file):**
- `tests/config/test_mcp_tester.py`

**Parent directories (if empty after deletion):**
- `src/guarantee_email_agent/integrations/` (check if empty)
- `tests/integrations/` (check if empty)

### Files to Create (5 files)

**Tool Implementations (3 files):**
- `src/guarantee_email_agent/tools/__init__.py`
- `src/guarantee_email_agent/tools/gmail_tool.py`
- `src/guarantee_email_agent/tools/crm_abacus_tool.py`

**Tool Tests (3 files):**
- `tests/tools/__init__.py`
- `tests/tools/test_gmail_tool.py`
- `tests/tools/test_crm_abacus_tool.py`

### Files to Modify (15 files)

**Core Logic:**
- `src/guarantee_email_agent/llm/function_dispatcher.py`
- `src/guarantee_email_agent/email/processor.py`
- `src/guarantee_email_agent/agent/runner.py`
- `src/guarantee_email_agent/agent/startup.py`
- `src/guarantee_email_agent/cli.py`

**Config:**
- `src/guarantee_email_agent/config/schema.py`
- `src/guarantee_email_agent/config/loader.py`
- `config.yaml`
- `.env.example`

**Eval:**
- `src/guarantee_email_agent/eval/mocks.py`
- `src/guarantee_email_agent/eval/runner.py`

**Tests:**
- `tests/llm/test_function_dispatcher.py`
- `tests/email/test_processor.py`
- `tests/agent/test_runner.py`
- `tests/agent/test_startup.py`
- `tests/config/test_loader.py`
- `tests/test_cli.py`

**Docs:**
- `_bmad-output/planning-artifacts/architecture.md`
- `RUNNING.md`
- `docs/deployment.md`

### Dependencies to Add

**Production:**
- `httpx` - Modern async HTTP client (likely already present)

**Development:**
- `pytest-httpx` - HTTP mocking for pytest

### Critical Constraints

- **NFR1**: Must maintain ≥99% eval pass rate
- **NFR7**: Processing must complete in <60s
- **NFR5**: All tool calls must be logged with structured context
- **Backward compatibility**: Function calling flow (Story 4.5) unchanged
- **Eval compatibility**: No changes to eval scenario YAML files
- **Error handling**: Preserve AgentError hierarchy and error codes
- **Retry/Circuit breaker**: Must maintain same resilience patterns
- **Zero downtime refactor**: All tests must pass after each task
- **Token management**: CRM Abacus tool must cache tokens and refresh automatically
- **API compatibility**: Tool must match actual CRM Abacus API contract (form-encoded token, Bearer auth)

### Benefits of This Refactor

1. **Architectural simplicity** - Remove entire MCP protocol layer (~500 LOC)
2. **Fewer dependencies** - Drop MCP SDK (potentially large dependency tree)
3. **Standard tooling** - Use httpx (well-known, well-documented HTTP client)
4. **Easier testing** - Mock HTTP responses (simpler than MCP protocol)
5. **Better debugging** - Standard HTTP logging, browser dev tools, curl testing
6. **Performance** - Remove protocol serialization overhead
7. **Maintainability** - Less abstraction, more straightforward code
8. **Industry standard** - Direct HTTP clients are universal pattern

### Risk Mitigation

**Low Risk Areas:**
- Tools are mocked in eval framework (no real API calls)
- MCP clients are thin wrappers (minimal business logic)
- Config schema change is isolated to loader module

**Medium Risk Areas:**
- 26+ files need updating (coordination required)
- Test coverage must be maintained
- Eval scenarios must continue passing

**Mitigation Strategy:**
1. Create tools first with 100% test coverage
2. Update one component at a time (FunctionDispatcher → EmailProcessor → etc.)
3. Run tests after each component update
4. Keep eval scenarios unchanged as integration smoke tests
5. Use feature branch, squash commit when complete

### Validation Checklist

Before marking story complete:

- [ ] All MCP code deleted (grep for "mcp" returns only docs)
- [ ] All tests passing (`pytest` exit code 0)
- [ ] Eval suite passing (≥99% pass rate)
- [ ] `agent run` works end-to-end
- [ ] `agent eval` works end-to-end
- [ ] Config.yaml uses `tools` section
- [ ] .env.example updated
- [ ] Documentation updated (architecture, RUNNING, deployment)
- [ ] No performance regression (<60s processing)
- [ ] Structured logging format unchanged
- [ ] Error messages clear and actionable

## References

- [Source: Story 4.5] - LLM function calling architecture (must remain compatible)
- [Source: _bmad-output/project-context.md#Technology Stack] - Gemini, async patterns
- [Source: _bmad-output/project-context.md#Error Handling] - AgentError hierarchy
- [Source: _bmad-output/planning-artifacts/architecture.md] - Current MCP architecture
- [httpx documentation](https://www.python-httpx.org/) - Async HTTP client
- [pytest-httpx documentation](https://colin-b.github.io/pytest_httpx/) - HTTP mocking

## Dev Agent Record

### Agent Model Used

(To be filled by dev agent)

### Completion Notes

(To be filled by dev agent during implementation)

### File List

(To be generated by dev agent after completion)
