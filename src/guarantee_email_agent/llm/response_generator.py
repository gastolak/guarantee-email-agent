"""LLM response generator for email responses."""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.instructions.loader import InstructionFile, load_step_instruction
from guarantee_email_agent.instructions.router import ScenarioRouter
from guarantee_email_agent.llm.provider import create_llm_provider, LLMProvider, GeminiProvider
from guarantee_email_agent.orchestrator.models import StepContext, StepExecutionResult
from guarantee_email_agent.utils.errors import (
    LLMError,
    LLMTimeoutError,
    TransientError,
)

if TYPE_CHECKING:
    from guarantee_email_agent.llm.function_calling import FunctionCallingResult, FunctionDefinition
    from guarantee_email_agent.llm.function_dispatcher import FunctionDispatcher

logger = logging.getLogger(__name__)

# Model constants (CRITICAL: Use Claude Sonnet 4.5, NOT deprecated 3.5)
MODEL_CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
DEFAULT_TEMPERATURE = 0  # Determinism per NFR
DEFAULT_MAX_TOKENS = 2048
LLM_TIMEOUT = 15  # seconds per NFR11


class ResponseGenerator:
    """Generate email responses using LLM with scenario-specific instructions.

    Combines main instruction with scenario-specific instruction to generate
    contextually appropriate responses for warranty inquiries.
    """

    def __init__(self, config: AgentConfig, main_instruction: InstructionFile, gmail_tool=None):
        """Initialize response generator.

        Args:
            config: Agent configuration
            main_instruction: Main orchestration instruction
            gmail_tool: Optional Gmail tool for email operations

        Raises:
            ValueError: If required API key not configured
        """
        self.config = config
        self.main_instruction = main_instruction
        self.gmail_tool = gmail_tool

        # Initialize LLM provider (Anthropic or Gemini based on config)
        self.llm_provider = create_llm_provider(config)

        # Initialize scenario router
        self.router = ScenarioRouter(config)

        # Function dispatcher is initialized on-demand or passed by caller
        # (eval tests pass their own mock dispatcher)
        self._function_dispatcher: Optional["FunctionDispatcher"] = None

        logger.info("Response generator initialized")

    def set_function_dispatcher(self, dispatcher: "FunctionDispatcher") -> None:
        """Set function dispatcher (for test mocking).

        Args:
            dispatcher: FunctionDispatcher instance (can be mock)
        """
        self._function_dispatcher = dispatcher

    def _get_function_dispatcher(self) -> "FunctionDispatcher":
        """Get function dispatcher, creating it if needed.

        Returns:
            FunctionDispatcher instance

        Raises:
            LLMError: If dispatcher creation fails
        """
        if self._function_dispatcher is None:
            # Create real dispatcher for production use
            from guarantee_email_agent.llm.function_dispatcher import FunctionDispatcher
            from guarantee_email_agent.tools.crm_abacus_tool import CrmAbacusTool

            try:
                crm_tool = CrmAbacusTool(
                    base_url=self.config.tools.crm_abacus.base_url,
                    username=self.config.secrets.crm_abacus_username,
                    password=self.config.secrets.crm_abacus_password,
                    token_endpoint=self.config.tools.crm_abacus.token_endpoint,
                    warranty_endpoint=self.config.tools.crm_abacus.warranty_endpoint,
                    ticketing_endpoint=self.config.tools.crm_abacus.ticketing_endpoint,
                    ticket_info_endpoint=self.config.tools.crm_abacus.ticket_info_endpoint,
                    task_info_endpoint=self.config.tools.crm_abacus.task_info_endpoint,
                    task_feature_check_endpoint=self.config.tools.crm_abacus.task_feature_check_endpoint,
                    ticket_defaults=self.config.tools.crm_abacus.ticket_defaults,
                    agent_disable_feature_name=self.config.tools.crm_abacus.agent_disable_feature_name,
                    timeout=self.config.tools.crm_abacus.timeout_seconds
                )
                self._function_dispatcher = FunctionDispatcher(
                    gmail_tool=self.gmail_tool,
                    crm_abacus_tool=crm_tool
                )
                logger.info("Function dispatcher created")
            except Exception as e:
                raise LLMError(
                    message=f"Failed to create function dispatcher: {e}",
                    code="function_dispatcher_init_failed",
                    details={"error": str(e)}
                )

        return self._function_dispatcher

    def build_response_system_message(
        self,
        main_instruction: InstructionFile,
        scenario_instruction: InstructionFile
    ) -> str:
        """Build system message combining main and scenario instructions.

        Args:
            main_instruction: Main orchestration instruction
            scenario_instruction: Scenario-specific instruction

        Returns:
            Complete system message for LLM
        """
        system_message = (
            f"You are a professional warranty email response agent. "
            f"Follow the guidelines and instructions below.\n\n"
            f"## Main Instruction:\n{main_instruction.body}\n\n"
            f"## Scenario-Specific Instruction ({scenario_instruction.name}):\n"
            f"{scenario_instruction.body}"
        )

        logger.debug(
            f"System message built: main={main_instruction.name}, "
            f"scenario={scenario_instruction.name}, "
            f"length={len(system_message)} chars"
        )

        return system_message

    def build_response_user_message(
        self,
        email_content: str,
        serial_number: Optional[str],
        warranty_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build user message with email content and warranty data.

        Args:
            email_content: Original customer email
            serial_number: Extracted serial number (if found)
            warranty_data: Warranty API response data (if available)

        Returns:
            Formatted user message for LLM
        """
        user_message_parts = [
            "Generate an appropriate email response based on the following information:",
            "",
            f"## Customer Email:\n{email_content}",
            ""
        ]

        if serial_number:
            user_message_parts.append(f"## Serial Number: {serial_number}")
            user_message_parts.append("")

        if warranty_data:
            user_message_parts.append("## Warranty Status:")
            user_message_parts.append(f"- Status: {warranty_data.get('status', 'unknown')}")
            if warranty_data.get('expiration_date'):
                user_message_parts.append(f"- Expiration Date: {warranty_data['expiration_date']}")
            if warranty_data.get('coverage'):
                user_message_parts.append(f"- Coverage: {warranty_data['coverage']}")
            user_message_parts.append("")

        user_message_parts.append("Generate the response email now:")

        user_message = "\n".join(user_message_parts)

        logger.debug(f"User message built: length={len(user_message)} chars")

        return user_message

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def generate_response(
        self,
        scenario_name: str,
        email_content: str,
        serial_number: Optional[str] = None,
        warranty_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate email response using LLM with scenario instruction.

        Args:
            scenario_name: Scenario identifier (e.g., "valid-warranty")
            email_content: Original customer email
            serial_number: Extracted serial number (optional)
            warranty_data: Warranty API response (optional)

        Returns:
            Generated email response text

        Raises:
            LLMTimeoutError: On LLM timeout (transient, will retry)
            LLMError: On LLM call failure after retries
        """
        logger.info(
            f"Generating response: scenario={scenario_name}, "
            f"serial={serial_number}, "
            f"warranty_status={warranty_data.get('status') if warranty_data else None}",
            extra={
                "scenario": scenario_name,
                "serial_number": serial_number,
                "warranty_status": warranty_data.get("status") if warranty_data else None
            }
        )

        try:
            # Load scenario instruction
            scenario_instruction = self.router.select_scenario(scenario_name)

            # Build messages
            system_message = self.build_response_system_message(
                self.main_instruction,
                scenario_instruction
            )
            user_message = self.build_response_user_message(
                email_content,
                serial_number,
                warranty_data
            )

            # Call LLM provider with timeout
            response_text = await asyncio.wait_for(
                asyncio.to_thread(
                    self.llm_provider.create_message,
                    system_prompt=system_message,
                    user_prompt=user_message,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    temperature=DEFAULT_TEMPERATURE
                ),
                timeout=self.config.llm.timeout_seconds
            )

            # Basic validation
            if not response_text or not response_text.strip():
                raise LLMError(
                    message="LLM returned empty response",
                    code="llm_empty_response",
                    details={"scenario": scenario_name}
                )

            logger.info(
                f"Response generated: scenario={scenario_name}, "
                f"length={len(response_text)} chars, "
                f"model={self.config.llm.model}, "
                f"temp={DEFAULT_TEMPERATURE}",
                extra={
                    "scenario": scenario_name,
                    "response_length": len(response_text),
                    "model": self.config.llm.model,
                    "temperature": DEFAULT_TEMPERATURE
                }
            )

            return response_text

        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                message=f"LLM response generation timeout ({self.config.llm.timeout_seconds}s)",
                code="llm_response_timeout",
                details={"scenario": scenario_name, "timeout": self.config.llm.timeout_seconds}
            )
        except LLMError:
            # Re-raise LLM errors as-is
            raise
        except Exception as e:
            # Classify exception for retry logic
            error_msg = str(e).lower()

            if "rate limit" in error_msg or "429" in error_msg:
                # Transient - will retry
                from guarantee_email_agent.utils.errors import LLMRateLimitError
                raise LLMRateLimitError(
                    message=f"LLM rate limit: {str(e)}",
                    code="llm_rate_limit",
                    details={"scenario": scenario_name, "error": str(e)}
                )
            elif "connection" in error_msg or "network" in error_msg:
                # Transient - will retry
                from guarantee_email_agent.utils.errors import LLMConnectionError
                raise LLMConnectionError(
                    message=f"LLM connection error: {str(e)}",
                    code="llm_connection_error",
                    details={"scenario": scenario_name, "error": str(e)}
                )
            else:
                # Non-transient - won't retry
                raise LLMError(
                    message=f"LLM response generation failed: {str(e)}",
                    code="llm_response_generation_failed",
                    details={"scenario": scenario_name, "error": str(e)}
                )

    def build_function_calling_system_message(
        self,
        main_instruction: InstructionFile,
        scenario_instruction: InstructionFile
    ) -> str:
        """Build system message for function-calling mode.

        NOTE: For function calling, we only use the scenario instruction body.
        The main instruction is for scenario/serial detection and contains JSON
        output format that conflicts with function calling.

        Args:
            main_instruction: Main orchestration instruction (unused for function calling)
            scenario_instruction: Scenario-specific instruction with functions

        Returns:
            Complete system message for LLM function calling
        """
        # Only use scenario instruction body - main instruction's JSON output format
        # conflicts with function calling mode
        system_message = scenario_instruction.body

        logger.debug(
            f"Function calling system message built: scenario={scenario_instruction.name}, "
            f"length={len(system_message)} chars"
        )

        return system_message

    def build_function_calling_user_message(
        self,
        email_content: str,
        serial_number: Optional[str],
        customer_email: Optional[str] = None
    ) -> str:
        """Build user message for function-calling mode.

        Args:
            email_content: Original customer email
            serial_number: Extracted serial number (if found)
            customer_email: Customer email address for reply

        Returns:
            Formatted user message for LLM
        """
        user_message_parts = [
            "Process the following customer email and take appropriate action:",
            "",
            f"## Customer Email Content:\n{email_content}",
            ""
        ]

        if serial_number:
            user_message_parts.append(f"## Extracted Serial Number: {serial_number}")
            user_message_parts.append("")

        if customer_email:
            user_message_parts.append(f"## Customer Email Address: {customer_email}")
            user_message_parts.append("")

        user_message_parts.append(
            "Use the available functions to process this request. "
            "Always call send_email as your final action to respond to the customer."
        )

        user_message = "\n".join(user_message_parts)

        logger.debug(f"Function calling user message built: length={len(user_message)} chars")

        return user_message

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def generate_with_functions(
        self,
        scenario_name: str,
        email_content: str,
        function_dispatcher: "FunctionDispatcher",
        serial_number: Optional[str] = None,
        customer_email: Optional[str] = None
    ) -> "FunctionCallingResult":
        """Generate response using LLM function calling.

        Uses the LLM to decide which functions to call (check_warranty,
        create_ticket, send_email) and executes them via the dispatcher.

        Args:
            scenario_name: Scenario identifier (e.g., "valid-warranty")
            email_content: Original customer email
            function_dispatcher: Dispatcher to execute function calls
            serial_number: Extracted serial number (optional)
            customer_email: Customer email address for reply (optional)

        Returns:
            FunctionCallingResult with function calls and metadata

        Raises:
            LLMTimeoutError: On LLM timeout (transient, will retry)
            LLMError: On LLM call failure after retries
            ValueError: If provider doesn't support function calling
        """
        from guarantee_email_agent.llm.function_calling import FunctionCallingResult

        logger.info(
            f"Generating with functions: scenario={scenario_name}, "
            f"serial={serial_number}",
            extra={
                "scenario": scenario_name,
                "serial_number": serial_number,
                "customer_email": customer_email
            }
        )

        # Verify provider supports function calling
        if not isinstance(self.llm_provider, GeminiProvider):
            raise LLMError(
                message="Function calling requires GeminiProvider",
                code="llm_function_calling_not_supported",
                details={"provider": type(self.llm_provider).__name__}
            )

        try:
            # Load scenario instruction
            scenario_instruction = self.router.select_scenario(scenario_name)

            # Print which step is being executed (for debugging workflow)
            print(f"\n{'='*60}")
            print(f"📋 EXECUTING STEP: {scenario_name}")
            print(f"   Instruction file: {scenario_instruction.name}")
            print(f"{'='*60}\n")

            # Check if scenario has functions defined
            if not scenario_instruction.has_functions():
                raise LLMError(
                    message=f"Scenario '{scenario_name}' has no functions defined",
                    code="llm_no_functions_defined",
                    details={"scenario": scenario_name}
                )

            # Get function definitions
            available_functions = scenario_instruction.get_available_functions()

            # Build messages
            system_message = self.build_function_calling_system_message(
                self.main_instruction,
                scenario_instruction
            )
            user_message = self.build_function_calling_user_message(
                email_content,
                serial_number,
                customer_email
            )

            # Call LLM provider with function calling
            result = await asyncio.wait_for(
                self.llm_provider.create_message_with_functions(
                    system_prompt=system_message,
                    user_prompt=user_message,
                    available_functions=available_functions,
                    function_dispatcher=function_dispatcher,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    temperature=DEFAULT_TEMPERATURE
                ),
                timeout=self.config.llm.timeout_seconds * 4  # Allow more time for multi-turn
            )

            logger.info(
                f"Function calling completed: scenario={scenario_name}, "
                f"function_calls={len(result.function_calls)}, "
                f"email_sent={result.email_sent}, "
                f"total_turns={result.total_turns}",
                extra={
                    "scenario": scenario_name,
                    "function_calls_count": len(result.function_calls),
                    "email_sent": result.email_sent,
                    "total_turns": result.total_turns
                }
            )

            return result

        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                message=f"LLM function calling timeout",
                code="llm_function_calling_timeout",
                details={"scenario": scenario_name}
            )
        except LLMError:
            raise
        except Exception as e:
            error_msg = str(e).lower()

            if "rate limit" in error_msg or "429" in error_msg:
                from guarantee_email_agent.utils.errors import LLMRateLimitError
                raise LLMRateLimitError(
                    message=f"LLM rate limit: {str(e)}",
                    code="llm_rate_limit",
                    details={"scenario": scenario_name, "error": str(e)}
                )
            elif "connection" in error_msg or "network" in error_msg:
                from guarantee_email_agent.utils.errors import LLMConnectionError
                raise LLMConnectionError(
                    message=f"LLM connection error: {str(e)}",
                    code="llm_connection_error",
                    details={"scenario": scenario_name, "error": str(e)}
                )
            else:
                raise LLMError(
                    message=f"LLM function calling failed: {str(e)}",
                    code="llm_function_calling_failed",
                    details={"scenario": scenario_name, "error": str(e)}
                )

    def _parse_step_response(
        self,
        response_text: str,
        step_name: str
    ) -> StepExecutionResult:
        """Parse LLM response for step execution result.

        Extracts structured data from LLM response:
        - NEXT_STEP: <step-name> or DONE
        - SERIAL: <serial-number>
        - REASON: <routing-reason>
        - Other metadata fields

        Args:
            response_text: Raw LLM response
            step_name: Current step name

        Returns:
            StepExecutionResult with parsed routing decision and metadata
        """
        metadata: Dict[str, Any] = {}

        # Extract NEXT_STEP (required)
        next_step_match = re.search(r'NEXT_STEP:\s*(\S+)', response_text, re.IGNORECASE)
        if next_step_match:
            next_step = next_step_match.group(1).strip()
        else:
            # Default to DONE if not specified (graceful fallback)
            logger.warning(
                f"No NEXT_STEP found in response for {step_name}, defaulting to DONE",
                extra={"step_name": step_name, "response_preview": response_text[:200]}
            )
            next_step = "DONE"

        # Extract SERIAL (optional)
        serial_match = re.search(r'SERIAL:\s*(\S+)', response_text, re.IGNORECASE)
        if serial_match:
            metadata["serial"] = serial_match.group(1).strip()

        # Extract REASON (optional)
        reason_match = re.search(r'REASON:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE)
        if reason_match:
            metadata["reason"] = reason_match.group(1).strip()

        logger.debug(
            f"Parsed step response: next_step={next_step}, metadata={metadata}",
            extra={"step_name": step_name, "next_step": next_step, "metadata": metadata}
        )

        return StepExecutionResult(
            next_step=next_step,
            response_text=response_text,
            metadata=metadata,
            step_name=step_name
        )

    def _build_step_user_message(self, step_name: str, context: StepContext) -> str:
        """Build user message for step execution with only relevant data.

        Each step receives only the data it needs to minimize token usage
        and reduce confusion. The step instruction tells the LLM what to do,
        and the user message provides only the required input data.

        Args:
            step_name: Current step name (e.g., "extract-serial", "check-warranty")
            context: Current workflow context

        Returns:
            Formatted user message for LLM with step-specific data
        """
        message_parts = []

        # Step 1: extract-serial - needs full email to read and understand
        if step_name == "extract-serial":
            message_parts = [
                "<email>",
                f"<subject>{context.email_subject}</subject>",
                f"<from>{context.from_address}</from>",
                f"<body>{context.email_body}</body>",
                "</email>"
            ]

        # Step 2: check-warranty - only needs serial number
        elif step_name == "check-warranty":
            message_parts = [
                f"Serial Number: {context.serial_number}"
            ]

        # Step 3a: valid-warranty (create_ticket) - needs serial, email, issue description, czas_naprawy
        elif step_name == "valid-warranty":
            message_parts = [
                f"Serial Number: {context.serial_number}",
                f"Customer Email: {context.from_address}",
                f"Issue Description: {context.email_body}"
            ]
            if context.warranty_data:
                expiry = context.warranty_data.get('expiration_date') or context.warranty_data.get('expires')
                if expiry:
                    message_parts.append(f"Warranty Expiration: {expiry}")
                # Add czas_naprawy for VIP warranty detection
                czas_naprawy = context.warranty_data.get('czas_naprawy')
                if czas_naprawy is not None:
                    message_parts.append(f"Czas Naprawy: {czas_naprawy}")

        # Step 3b: device-not-found - needs customer email, serial, and original subject
        elif step_name == "device-not-found":
            message_parts = [
                f"Customer Email: {context.from_address}",
                f"Serial Number: {context.serial_number}",
                f"Original Subject: {context.email_subject}"
            ]

        # Step 3c: expired-warranty - needs customer email, serial, expiration, and original subject
        elif step_name == "expired-warranty":
            message_parts = [
                f"Customer Email: {context.from_address}",
                f"Serial Number: {context.serial_number}",
                f"Original Subject: {context.email_subject}"
            ]
            if context.warranty_data:
                expiry = context.warranty_data.get('expiration_date') or context.warranty_data.get('expires')
                if expiry:
                    message_parts.append(f"Expiration Date: {expiry}")

        # Step 3d: request-serial - needs customer email, original subject, thread/message IDs for reply
        elif step_name == "request-serial":
            message_parts = [
                f"Customer Email: {context.from_address}",
                f"Original Subject: {context.email_subject}",
                f"Thread ID: {context.thread_id}" if context.thread_id else "Thread ID: None",
                f"Message ID: {context.message_id}" if context.message_id else "Message ID: None"
            ]

        # Step 4: out-of-scope - needs customer email, original subject, thread/message IDs for reply
        elif step_name == "out-of-scope":
            message_parts = [
                f"Customer Email: {context.from_address}",
                f"Original Subject: {context.email_subject}",
                f"Thread ID: {context.thread_id}" if context.thread_id else "Thread ID: None",
                f"Message ID: {context.message_id}" if context.message_id else "Message ID: None"
            ]

        # Step 5: send-confirmation - needs email, serial, ticket_id, warranty expiry, original subject, email body, and thread/message IDs
        elif step_name == "send-confirmation":
            message_parts = [
                f"Customer Email: {context.from_address}",
                f"Serial Number: {context.serial_number}",
                f"Ticket ID: {context.ticket_id}",
                f"Original Subject: {context.email_subject}",
                f"Original Email Body: {context.email_body}",
                f"Thread ID: {context.thread_id}" if context.thread_id else "Thread ID: None",
                f"Message ID: {context.message_id}" if context.message_id else "Message ID: None"
            ]
            if context.warranty_data:
                expiry = context.warranty_data.get('expiration_date') or context.warranty_data.get('expires')
                if expiry:
                    message_parts.append(f"Warranty Expiration: {expiry}")

        # Step 6: alert-admin-vip - needs admin email, customer email, serial, ticket_id, czas_naprawy, issue
        elif step_name == "alert-admin-vip":
            # Load admin_email from config
            from guarantee_email_agent.config import load_config
            config = load_config()
            admin_email = config.agent.admin_email

            message_parts = [
                f"Admin Email: {admin_email}",
                f"Customer Email: {context.from_address}",
                f"Serial Number: {context.serial_number}",
                f"Issue Description: {context.email_body}",
                f"Ticket ID: {context.ticket_id}"
            ]
            if context.warranty_data:
                czas_naprawy = context.warranty_data.get('czas_naprawy')
                if czas_naprawy is not None:
                    message_parts.append(f"Czas Naprawy: {czas_naprawy}")
                expiry = context.warranty_data.get('expiration_date') or context.warranty_data.get('expires')
                if expiry:
                    message_parts.append(f"Warranty Expiration Date: {expiry}")

        # Step 7a: store-client-message - needs ticket_id and original email body
        elif step_name == "store-client-message":
            message_parts = [
                f"Ticket ID: {context.ticket_id}",
                f"Original Email Body: {context.email_body}"
            ]

        # Step 7b: store-agent-message - needs ticket_id and agent response
        elif step_name == "store-agent-message":
            # Agent response body - construct the confirmation message that was sent
            agent_response = f"""Dzień dobry,

Potwierdzamy przyjęcie zgłoszenia RMA dla urządzenia o numerze seryjnym "{context.serial_number}".

Status gwarancji: AKTYWNA (ważna do {context.warranty_data.get('expiration_date') or context.warranty_data.get('expires') if context.warranty_data else 'N/A'})
Numer zgłoszenia: {context.ticket_id}

Nasz zespół techniczny skontaktuje się z Państwem w ciągu 2 dni roboczych w celu dalszych instrukcji.

Pozdrawiamy,
Dział Serwisu"""
            message_parts = [
                f"Ticket ID: {context.ticket_id}",
                f"Agent Response Body: {agent_response}"
            ]

        # Step 8a: escalate-customer-ack - needs customer email, original subject, and thread/message IDs
        elif step_name == "escalate-customer-ack":
            message_parts = [
                f"Customer Email: {context.from_address}",
                f"Original Subject: {context.email_subject}",
                f"Thread ID: {context.thread_id}" if context.thread_id else "Thread ID: None",
                f"Message ID: {context.message_id}" if context.message_id else "Message ID: None"
            ]

        # Step 8b: escalate-supervisor-alert - needs supervisor email, customer context, escalation reason
        elif step_name == "escalate-supervisor-alert":
            # Load supervisor_email from config
            from guarantee_email_agent.config import load_config
            config = load_config()
            supervisor_email = config.agent.supervisor_email

            message_parts = [
                f"Supervisor Email: {supervisor_email}",
                f"Customer Email: {context.from_address}",
                f"Email Subject: {context.email_subject}",
                f"Email Body: {context.email_body}",
                f"Serial Number: {context.serial_number if context.serial_number else 'Not provided'}",
                f"Escalation Reason: Customer expressed frustration or requested human contact"
            ]

        # Fallback: if unknown step, provide full context (shouldn't happen)
        else:
            logger.warning(f"Unknown step name '{step_name}', providing full context")
            message_parts = [
                "<email>",
                f"<subject>{context.email_subject}</subject>",
                f"<from>{context.from_address}</from>",
                f"<body>{context.email_body}</body>",
                "</email>",
                ""
            ]
            if context.serial_number:
                message_parts.append(f"Serial Number: {context.serial_number}")
            if context.warranty_data:
                message_parts.append(f"Warranty Data: {context.warranty_data}")
            if context.ticket_id:
                message_parts.append(f"Ticket ID: {context.ticket_id}")

        return "\n".join(message_parts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def generate_step_response(
        self,
        step_name: str,
        context: StepContext
    ) -> StepExecutionResult:
        """Generate response for a single step in the workflow.

        Loads step instruction, calls LLM, parses NEXT_STEP routing decision.

        Args:
            step_name: Name of step to execute (e.g., "01-extract-serial")
            context: Current workflow context

        Returns:
            StepExecutionResult with routing decision and metadata

        Raises:
            LLMTimeoutError: On LLM timeout (transient, will retry)
            LLMError: On LLM call failure after retries
        """
        logger.info(
            f"Generating step response: step={step_name}",
            extra={
                "step_name": step_name,
                "has_serial": context.serial_number is not None,
                "has_warranty_data": context.warranty_data is not None
            }
        )

        try:
            # Load step instruction
            step_instruction = load_step_instruction(step_name)

            # Build system message from ONLY step instruction (not main instruction)
            # Main instruction contains full workflow which confuses LLM for individual steps
            system_message = (
                f"## Current Step: {step_instruction.name}\n"
                f"{step_instruction.body}"
            )

            # Build user message from context (step-specific data only)
            user_message = self._build_step_user_message(step_name, context)

            # Check if step has function definitions
            available_functions = step_instruction.get_available_functions()

            # Debug: Show context state before this step
            print(f"\n📊 CONTEXT STATE FOR STEP {step_name}:")
            print(f"  - Serial: {context.serial_number}")
            print(f"  - Warranty Data: {context.warranty_data}")
            print(f"  - Ticket ID: {context.ticket_id}")
            print()

            if available_functions:
                # Step requires function calling
                print(f"🔧 Step {step_name} has {len(available_functions)} available functions:")
                for func in available_functions:
                    print(f"  - {func.name}")
                print()

                # Debug: Show what prompt is being sent to LLM
                print(f"📝 FULL SYSTEM MESSAGE BEING SENT TO LLM:")
                print(f"{'='*80}")
                print(system_message)  # FULL system message
                print(f"{'='*80}\n")

                print(f"👤 FULL USER MESSAGE:")
                print(f"{'='*80}")
                print(user_message)
                print(f"{'='*80}\n")

                # Get or create function dispatcher
                function_dispatcher = self._get_function_dispatcher()

                # Use function calling mode
                function_result = await asyncio.wait_for(
                    self.llm_provider.create_message_with_functions(
                        system_prompt=system_message,
                        user_prompt=user_message,
                        available_functions=available_functions,
                        function_dispatcher=function_dispatcher,
                        max_tokens=DEFAULT_MAX_TOKENS,
                        temperature=DEFAULT_TEMPERATURE
                    ),
                    timeout=self.config.llm.timeout_seconds
                )

                # Extract response text and function calls from result
                response_text = function_result.response_text

                # function_result.function_calls contains ONLY the calls from THIS step
                # (create_message_with_functions returns a fresh list each time)
                new_calls = function_result.function_calls

                print(f"📞 Function calls in this step: {len(new_calls)}")
                for call in new_calls:
                    args_str = ', '.join(f'{k}={str(v)[:50]}...' if len(str(v)) > 50 else f'{k}={v}' for k, v in call.arguments.items())
                    print(f"  - {call.function_name}({args_str})")

                context.function_calls.extend(new_calls)

            else:
                # Step does not require function calling, use text-only mode
                logger.info(
                    f"Step {step_name} has no functions, using text-only mode",
                    extra={"step_name": step_name}
                )

                # Debug: Show what prompt is being sent to LLM (text-only mode)
                print(f"📝 FULL SYSTEM MESSAGE BEING SENT TO LLM:")
                print(f"{'='*80}")
                print(system_message)
                print(f"{'='*80}\n")

                print(f"👤 FULL USER MESSAGE:")
                print(f"{'='*80}")
                print(user_message)
                print(f"{'='*80}\n")

                response_text = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.llm_provider.create_message,
                        system_prompt=system_message,
                        user_prompt=user_message,
                        max_tokens=DEFAULT_MAX_TOKENS,
                        temperature=DEFAULT_TEMPERATURE
                    ),
                    timeout=self.config.llm.timeout_seconds
                )

            # Validate response
            if not response_text or not response_text.strip():
                raise LLMError(
                    message="LLM returned empty response",
                    code="llm_empty_response",
                    details={"step_name": step_name}
                )

            # Log the full LLM response for debugging
            print(f"\n{'='*80}")
            print(f"STEP: {step_name}")
            print(f"LLM RESPONSE:")
            print(response_text)
            print(f"{'='*80}\n")

            # Parse response for NEXT_STEP and metadata
            result = self._parse_step_response(response_text, step_name)

            # Add function call results to metadata if this step had functions
            if available_functions and new_calls:
                for call in new_calls:
                    # Special handling for check_warranty - add warranty data to metadata
                    if call.function_name == "check_warranty" and call.success and call.result:
                        result.metadata["warranty_data"] = call.result
                        logger.debug(f"Added warranty_data to metadata: {call.result}")

                    # Special handling for create_ticket - add ticket_id to metadata
                    elif call.function_name == "create_ticket" and call.success and call.result:
                        # Result might be a dict with ticket_id or just the ticket_id string
                        if isinstance(call.result, dict) and "ticket_id" in call.result:
                            result.metadata["ticket_id"] = call.result["ticket_id"]
                        elif isinstance(call.result, str):
                            result.metadata["ticket_id"] = call.result
                        logger.debug(f"Added ticket_id to metadata: {result.metadata.get('ticket_id')}")

            logger.info(
                f"Step response generated: {step_name} → {result.next_step}",
                extra={
                    "step_name": step_name,
                    "next_step": result.next_step,
                    "response_length": len(response_text)
                }
            )

            return result

        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                message=f"LLM step response timeout ({self.config.llm.timeout_seconds}s)",
                code="llm_step_response_timeout",
                details={"step_name": step_name, "timeout": self.config.llm.timeout_seconds}
            )
        except LLMError:
            raise
        except Exception as e:
            error_msg = str(e).lower()

            if "rate limit" in error_msg or "429" in error_msg:
                from guarantee_email_agent.utils.errors import LLMRateLimitError
                raise LLMRateLimitError(
                    message=f"LLM rate limit: {str(e)}",
                    code="llm_rate_limit",
                    details={"step_name": step_name, "error": str(e)}
                )
            elif "connection" in error_msg or "network" in error_msg:
                from guarantee_email_agent.utils.errors import LLMConnectionError
                raise LLMConnectionError(
                    message=f"LLM connection error: {str(e)}",
                    code="llm_connection_error",
                    details={"step_name": step_name, "error": str(e)}
                )
            else:
                raise LLMError(
                    message=f"LLM step response generation failed: {str(e)}",
                    code="llm_step_response_failed",
                    details={"step_name": step_name, "error": str(e)}
                )
