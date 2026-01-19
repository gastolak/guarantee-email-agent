"""LLM response generator for email responses."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.instructions.loader import InstructionFile
from guarantee_email_agent.instructions.router import ScenarioRouter
from guarantee_email_agent.llm.provider import create_llm_provider, LLMProvider, GeminiProvider
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

    def __init__(self, config: AgentConfig, main_instruction: InstructionFile):
        """Initialize response generator.

        Args:
            config: Agent configuration
            main_instruction: Main orchestration instruction

        Raises:
            ValueError: If required API key not configured
        """
        self.config = config
        self.main_instruction = main_instruction

        # Initialize LLM provider (Anthropic or Gemini based on config)
        self.llm_provider = create_llm_provider(config)

        # Initialize scenario router
        self.router = ScenarioRouter(config)

        logger.info("Response generator initialized")

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
