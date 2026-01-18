"""LLM orchestrator for main instruction processing."""

import asyncio
import json
import logging
from typing import Any, Dict

from anthropic import Anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.instructions.loader import (
    InstructionFile,
    load_instruction_cached,
)
from guarantee_email_agent.utils.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    TransientError,
)

logger = logging.getLogger(__name__)

# Model constants (CRITICAL: Use Claude Sonnet 4.5, NOT deprecated 3.5)
MODEL_CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
DEFAULT_TEMPERATURE = 0  # Determinism per NFR
DEFAULT_MAX_TOKENS = 4096
LLM_TIMEOUT = 15  # seconds per NFR11


class Orchestrator:
    """LLM orchestrator for main instruction processing.

    Loads main instruction file and orchestrates email processing
    by constructing system messages and calling Claude Sonnet 4.5.
    """

    def __init__(self, config: AgentConfig):
        """Initialize orchestrator with configuration.

        Args:
            config: Agent configuration with API keys and paths

        Raises:
            ValueError: If ANTHROPIC_API_KEY not configured
            InstructionError: If main instruction file invalid
        """
        self.config = config

        # Initialize Anthropic client
        api_key = config.secrets.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=api_key)

        # Load main instruction
        main_instruction_path = config.instructions.main
        self.main_instruction = load_instruction_cached(main_instruction_path)

        logger.info(
            f"Main instruction loaded: {self.main_instruction.name} v{self.main_instruction.version}",
            extra={
                "instruction_name": self.main_instruction.name,
                "instruction_version": self.main_instruction.version,
                "file_path": main_instruction_path
            }
        )

    def build_system_message(self, instruction: InstructionFile) -> str:
        """Build LLM system message from instruction.

        Args:
            instruction: Instruction file with XML body

        Returns:
            Complete system message for LLM
        """
        system_message = (
            f"You are a warranty email processing agent. "
            f"Follow the workflow and patterns defined below.\n\n"
            f"{instruction.body}"
        )
        return system_message

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(TransientError)
    )
    async def orchestrate(self, email_content: str) -> Dict[str, Any]:
        """Orchestrate email processing using main instruction.

        Args:
            email_content: Raw email content to process

        Returns:
            Orchestration result: {scenario, serial_number, confidence}

        Raises:
            LLMTimeoutError: On LLM timeout (transient, will retry)
            LLMRateLimitError: On rate limit (transient, will retry)
            LLMConnectionError: On connection error (transient, will retry)
            LLMAuthenticationError: On auth error (non-transient, no retry)
            LLMError: On other LLM failures
        """
        # Build messages
        system_message = self.build_system_message(self.main_instruction)
        user_message = f"Analyze this warranty inquiry email:\n\n{email_content}"

        try:
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

            # Parse response
            result_text = response.content[0].text

            # Parse JSON response
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError as e:
                raise LLMError(
                    message=f"LLM returned invalid JSON: {str(e)}",
                    code="llm_invalid_json_response",
                    details={"response": result_text[:200], "error": str(e)}
                )

            # Validate result structure
            if not isinstance(result, dict):
                raise LLMError(
                    message="LLM response is not a JSON object",
                    code="llm_invalid_response_structure",
                    details={"response": result_text[:200]}
                )

            if "scenario" not in result:
                raise LLMError(
                    message="LLM response missing 'scenario' field",
                    code="llm_missing_scenario",
                    details={"response": result}
                )

            logger.info(
                f"LLM orchestration: scenario={result.get('scenario')}, "
                f"serial={result.get('serial_number')}, "
                f"confidence={result.get('confidence')}",
                extra={
                    "scenario": result.get("scenario"),
                    "serial_number": result.get("serial_number"),
                    "confidence": result.get("confidence")
                }
            )

            return result

        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                message=f"LLM call timeout ({LLM_TIMEOUT}s)",
                code="llm_timeout",
                details={"timeout": LLM_TIMEOUT}
            )
        except Exception as e:
            # Classify exceptions for retry logic
            error_msg = str(e).lower()

            if "authentication" in error_msg or "api key" in error_msg:
                raise LLMAuthenticationError(
                    message=f"LLM authentication failed: {str(e)}",
                    code="llm_authentication_failed",
                    details={"error": str(e)}
                )
            elif "rate limit" in error_msg or "429" in error_msg:
                raise LLMRateLimitError(
                    message=f"LLM rate limit exceeded: {str(e)}",
                    code="llm_rate_limit",
                    details={"error": str(e)}
                )
            elif "connection" in error_msg or "network" in error_msg:
                raise LLMConnectionError(
                    message=f"LLM connection error: {str(e)}",
                    code="llm_connection_error",
                    details={"error": str(e)}
                )
            elif isinstance(e, (LLMTimeoutError, LLMError)):
                raise
            else:
                raise LLMError(
                    message=f"LLM orchestration failed: {str(e)}",
                    code="llm_orchestration_failed",
                    details={"error": str(e)}
                )
