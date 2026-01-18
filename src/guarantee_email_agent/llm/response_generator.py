"""LLM response generator for email responses."""

import asyncio
import logging
from typing import Any, Dict, Optional

from anthropic import Anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.instructions.loader import InstructionFile
from guarantee_email_agent.instructions.router import ScenarioRouter
from guarantee_email_agent.utils.errors import (
    LLMError,
    LLMTimeoutError,
    TransientError,
)

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
            ValueError: If ANTHROPIC_API_KEY not configured
        """
        self.config = config
        self.main_instruction = main_instruction

        # Initialize Anthropic client
        api_key = config.secrets.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=api_key)

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

            # Call Anthropic API with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.messages.create,
                    model=MODEL_CLAUDE_SONNET_4_5,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    temperature=DEFAULT_TEMPERATURE,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                ),
                timeout=LLM_TIMEOUT
            )

            # Extract response text
            response_text = response.content[0].text

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
                f"model={MODEL_CLAUDE_SONNET_4_5}, "
                f"temp={DEFAULT_TEMPERATURE}",
                extra={
                    "scenario": scenario_name,
                    "response_length": len(response_text),
                    "model": MODEL_CLAUDE_SONNET_4_5,
                    "temperature": DEFAULT_TEMPERATURE
                }
            )

            return response_text

        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                message=f"LLM response generation timeout ({LLM_TIMEOUT}s)",
                code="llm_response_timeout",
                details={"scenario": scenario_name, "timeout": LLM_TIMEOUT}
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
