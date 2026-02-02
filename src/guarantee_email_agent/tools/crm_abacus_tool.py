"""CRM Abacus tool for warranty checks and ticket creation."""
import httpx
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from guarantee_email_agent.utils.circuit_breaker import CircuitBreaker
from guarantee_email_agent.utils.errors import IntegrationError

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
        ticket_info_endpoint: str,
        task_info_endpoint: str,
        task_feature_check_endpoint: str,
        ticket_defaults: Dict[str, int],
        agent_disable_feature_name: str = "Wyłącz agenta AI",
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
            ticket_info_endpoint: Ticket info endpoint path with {zadanie_id} placeholder
            task_info_endpoint: Task info endpoint path with {zadanie_id} placeholder
            task_feature_check_endpoint: Task feature check endpoint with {zadanie_id} placeholder
            ticket_defaults: Default IDs for ticket creation (dzial_id, typ_zadania_id, etc.)
            agent_disable_feature_name: Feature name to check for agent disable flag
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token_endpoint = token_endpoint
        self.warranty_endpoint = warranty_endpoint
        self.ticketing_endpoint = ticketing_endpoint
        self.ticket_info_endpoint = ticket_info_endpoint
        self.task_info_endpoint = task_info_endpoint
        self.task_feature_check_endpoint = task_feature_check_endpoint
        self.ticket_defaults = ticket_defaults
        self.agent_disable_feature_name = agent_disable_feature_name
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(name="crm_abacus", failure_threshold=5)
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
            # Assume 1-hour expiry (adjust based on API response if expires_in provided)
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

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
            raise IntegrationError(f"CRM Abacus token error: {e}", code="integration_error") from e

    async def _get_valid_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if not self._access_token or not self._token_expires_at:
            return await self._acquire_token()

        # Refresh 5 minutes before expiry
        if datetime.now() >= self._token_expires_at - timedelta(minutes=5):
            return await self._acquire_token()

        return self._access_token

    async def _request_with_auth(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Helper method: make authenticated request with token refresh.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request kwargs

        Returns:
            HTTP response

        Raises:
            IntegrationError: If request fails after token refresh
        """
        token = await self._get_valid_token()

        # Add Authorization header
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        try:
            response = await self.client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            # If 401, refresh token and retry once
            if e.response.status_code == 401:
                logger.warning("Token expired, refreshing...")
                token = await self._acquire_token()
                headers["Authorization"] = f"Bearer {token}"
                response = await self.client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response
            raise

    async def find_device_by_serial(self, serial_number: str) -> Dict[str, Any]:
        """Find device by serial number.

        Args:
            serial_number: Device serial number

        Returns:
            Raw SerialKlient response with fields: urzadzenie_id, klient_id, nazwa, serial,
            data_stop, producent_gwarancja_stop, typ_gwarancji, etc.

        Raises:
            IntegrationError: If API call fails or device not found
        """
        try:
            logger.info(
                "Finding device by serial",
                extra={"tool": "crm_abacus", "operation": "find_device_by_serial", "serial": serial_number}
            )

            response = await self._request_with_auth(
                "GET",
                f"{self.base_url}{self.warranty_endpoint}",
                params={"serial": serial_number}
            )
            device_data = response.json()

            logger.info(
                "Device found",
                extra={"tool": "crm_abacus", "operation": "find_device_by_serial", "device_id": device_data.get("urzadzenie_id")}
            )
            return device_data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Device not found: {serial_number}")
                raise IntegrationError(f"Device not found: {serial_number}", code="integration_error") from e
            logger.error(
                f"Find device failed: {e}",
                extra={"tool": "crm_abacus", "operation": "find_device_by_serial", "error": str(e)}
            )
            raise IntegrationError(f"CRM Abacus find device error: {e}", code="integration_error") from e
        except httpx.HTTPError as e:
            logger.error(
                f"Find device failed: {e}",
                extra={"tool": "crm_abacus", "operation": "find_device_by_serial", "error": str(e)}
            )
            raise IntegrationError(f"CRM Abacus find device error: {e}", code="integration_error") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def check_warranty(self, serial_number: str) -> Dict[str, Any]:
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
        # Circuit breaker tracked in self.circuit_breaker (retry handles resilience)
        try:
                logger.info(
                    "Checking warranty",
                    extra={"tool": "crm_abacus", "operation": "check_warranty", "serial": serial_number}
                )

                # Find device first
                try:
                    device_data = await self.find_device_by_serial(serial_number)
                except IntegrationError as e:
                    if "not found" in str(e).lower():
                        return {
                            "status": "not_found",
                            "warranty_type": None,
                            "expires": None,
                            "device_name": None,
                            "serial": serial_number,
                            "klient_id": None
                        }
                    raise

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

        except IntegrationError:
                raise
        except Exception as e:
                logger.error(
                    f"Warranty check failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "check_warranty", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus warranty error: {e}", code="integration_error") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def create_ticket(
        self,
        subject: str,
        description: str,
        customer_email: str = None,
        priority: str = None
    ) -> str:
        """Create support ticket.

        Args:
            subject: Ticket subject (format: "{device_name}:{serial}")
            description: Ticket description
            customer_email: Customer email (ignored for LLM compatibility)
            priority: Priority level (ignored for LLM compatibility)

        Returns:
            Ticket ID as string

        Raises:
            IntegrationError: If API call fails after retries
        """
        # Circuit breaker tracked in self.circuit_breaker (retry handles resilience)
        try:
                logger.info(
                    "Creating ticket",
                    extra={"tool": "crm_abacus", "operation": "create_ticket", "subject": subject}
                )

                # Parse serial from subject (format: "{device_name}:{serial}")
                serial_number = None
                if ":" in subject:
                    parts = subject.split(":", 1)
                    if len(parts) == 2:
                        serial_number = parts[1].strip()

                # Try to find klient_id from serial
                klient_id = self.ticket_defaults.get("unrecognized_klient_id", 702)
                if serial_number:
                    try:
                        device_data = await self.find_device_by_serial(serial_number)
                        if device_data.get("klient_id"):
                            klient_id = device_data["klient_id"]
                    except IntegrationError:
                        logger.warning(f"Could not find klient_id for serial {serial_number}, using default")

                # Create ticket with defaults
                payload = {
                    "dzial_id": self.ticket_defaults["dzial_id"],
                    "typ_zadania_id": self.ticket_defaults["typ_zadania_id"],
                    "typ_wykonania_id": self.ticket_defaults["typ_wykonania_id"],
                    "organizacja_id": self.ticket_defaults["organizacja_id"],
                    "klient_id": klient_id,
                    "temat": subject,
                    "opis": description
                }

                response = await self._request_with_auth(
                    "POST",
                    f"{self.base_url}{self.ticketing_endpoint}",
                    json=payload
                )
                result = response.json()

                # Extract ticket ID (try multiple fields)
                ticket_id = result.get("nowe_zadanie_id") or result.get("zadanie_id") or result.get("id")

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
                raise IntegrationError(f"CRM Abacus ticketing error: {e}", code="integration_error") from e
        except Exception as e:
                logger.error(
                    f"Ticket creation failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "create_ticket", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus ticketing error: {e}", code="integration_error") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def add_ticket_info(self, zadanie_id: int, info_text: str) -> None:
        """Add information to existing ticket.

        Args:
            zadanie_id: Task/ticket ID
            info_text: Information text to add

        Raises:
            IntegrationError: If API call fails after retries
        """
        # Circuit breaker tracked in self.circuit_breaker (retry handles resilience)
        try:
                logger.info(
                    "Adding ticket info",
                    extra={"tool": "crm_abacus", "operation": "add_ticket_info", "zadanie_id": zadanie_id}
                )

                endpoint = self.ticket_info_endpoint.format(zadanie_id=zadanie_id)
                payload = {
                    "opis": info_text,
                    "publiczne": False,
                    "operacja_id": 0
                }

                await self._request_with_auth(
                    "POST",
                    f"{self.base_url}{endpoint}",
                    json=payload
                )

                logger.info(
                    "Ticket info added",
                    extra={"tool": "crm_abacus", "operation": "add_ticket_info", "zadanie_id": zadanie_id}
                )

        except httpx.HTTPError as e:
                logger.error(
                    f"Add ticket info failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "add_ticket_info", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus add info error: {e}", code="integration_error") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_task_info(self, zadanie_id: int) -> Dict[str, Any]:
        """Get full task/ticket information by ID.

        Args:
            zadanie_id: Task ID

        Returns:
            Full Zadanie response dict

        Raises:
            IntegrationError: If API call fails after retries
        """
        # Circuit breaker tracked in self.circuit_breaker (retry handles resilience)
        try:
                logger.info(
                    "Fetching task info",
                    extra={"tool": "crm_abacus", "operation": "get_task_info", "zadanie_id": zadanie_id}
                )

                endpoint = self.task_info_endpoint.format(zadanie_id=zadanie_id)
                response = await self._request_with_auth(
                    "GET",
                    f"{self.base_url}{endpoint}"
                )
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
                raise IntegrationError(f"CRM Abacus task info error: {e}", code="integration_error") from e

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
        # Circuit breaker tracked in self.circuit_breaker (retry handles resilience)
        try:
                logger.info(
                    "Checking agent disabled flag",
                    extra={"tool": "crm_abacus", "operation": "check_agent_disabled", "zadanie_id": zadanie_id}
                )

                endpoint = self.task_feature_check_endpoint.format(zadanie_id=zadanie_id)
                response = await self._request_with_auth(
                    "GET",
                    f"{self.base_url}{endpoint}",
                    params={"nazwa_cechy": self.agent_disable_feature_name}
                )
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
                raise IntegrationError(f"CRM Abacus agent check error: {e}", code="integration_error") from e
        except httpx.HTTPError as e:
                logger.error(
                    f"Agent disabled check failed: {e}",
                    extra={"tool": "crm_abacus", "operation": "check_agent_disabled", "error": str(e)}
                )
                raise IntegrationError(f"CRM Abacus agent check error: {e}", code="integration_error") from e

    async def close(self) -> None:
        """Close HTTP client connection pool."""
        await self.client.aclose()
