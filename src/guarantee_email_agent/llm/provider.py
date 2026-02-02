"""LLM provider abstraction layer for multiple LLM backends."""

import asyncio
import logging
import re
import time
import warnings
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

from anthropic import Anthropic

if TYPE_CHECKING:
    from guarantee_email_agent.llm.function_calling import (
        FunctionDefinition,
        FunctionCallingResult,
    )
    from guarantee_email_agent.llm.function_dispatcher import FunctionDispatcher

# Suppress FutureWarnings from Google packages during import
# These warnings don't affect functionality and clutter eval output
with warnings.catch_warnings():
    warnings.simplefilter('ignore', FutureWarning)
    import google.generativeai as genai

from guarantee_email_agent.config.schema import AgentConfig, LLMConfig
from guarantee_email_agent.utils.errors import LLMError

logger = logging.getLogger(__name__)


def clean_markdown_response(text: str) -> str:
    """Clean markdown formatting from LLM responses.

    Removes common markdown artifacts that some LLMs (especially Gemini)
    add to their responses, such as code blocks, bold/italic markers, etc.

    Args:
        text: Raw LLM response text

    Returns:
        Cleaned text with markdown removed
    """
    if not text:
        return text

    # Remove markdown code blocks (```language and ```)
    text = re.sub(r'^```[\w]*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```$', '', text, flags=re.MULTILINE)

    # Remove inline code blocks (single backticks) if they wrap the entire response
    text = text.strip()
    if text.startswith('`') and text.endswith('`') and text.count('`') == 2:
        text = text[1:-1]

    return text.strip()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        """Initialize LLM provider with configuration.

        Args:
            config: LLM configuration (provider, model, temperature, etc.)
        """
        self.config = config

    @abstractmethod
    def create_message(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate a text response from the LLM.

        Args:
            system_prompt: System instruction for the LLM
            user_prompt: User message/query
            max_tokens: Maximum tokens in response (uses config default if None)
            temperature: Sampling temperature (uses config default if None)

        Returns:
            Generated text response

        Raises:
            LLMError: If LLM request fails
        """
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    def __init__(self, config: LLMConfig, api_key: str):
        """Initialize Anthropic provider.

        Args:
            config: LLM configuration
            api_key: Anthropic API key
        """
        super().__init__(config)
        self.client = Anthropic(api_key=api_key)
        logger.info(f"Anthropic provider initialized: model={config.model}")

    def create_message(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate response using Anthropic Claude API.

        Args:
            system_prompt: System instruction
            user_prompt: User message
            max_tokens: Max tokens (default from config)
            temperature: Temperature (default from config)

        Returns:
            Generated text

        Raises:
            LLMError: If API request fails
        """
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature or self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            raise LLMError(
                message=f"Anthropic API error: {e}",
                code="anthropic_api_error",
                details={"error": str(e)}
            )


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, config: LLMConfig, api_key: str):
        """Initialize Gemini provider.

        Args:
            config: LLM configuration
            api_key: Gemini API key
        """
        super().__init__(config)
        genai.configure(api_key=api_key)

        # Configure safety settings to be less restrictive
        # Warranty emails should not trigger safety filters
        # Must use proper HarmCategory and HarmBlockThreshold enums
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        self.model = genai.GenerativeModel(config.model)
        logger.info(f"Gemini provider initialized: model={config.model} with BLOCK_NONE safety filters")

    def create_message(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate response using Google Gemini API.

        Args:
            system_prompt: System instruction
            user_prompt: User message
            max_tokens: Max tokens (default from config)
            temperature: Temperature (default from config)

        Returns:
            Generated text

        Raises:
            LLMError: If API request fails
        """
        try:
            # Gemini combines system and user prompts differently
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"

            # Configure generation parameters
            generation_config = genai.GenerationConfig(
                temperature=temperature or self.config.temperature,
                max_output_tokens=max_tokens or self.config.max_tokens,
            )

            response = self.model.generate_content(
                combined_prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )

            # Log response details for debugging safety issues
            logger.debug(f"Gemini response candidates: {len(response.candidates) if response.candidates else 0}")
            if response.candidates:
                candidate = response.candidates[0]
                logger.debug(f"Finish reason: {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    logger.debug(f"Safety ratings: {candidate.safety_ratings}")

            # Check if response was blocked by safety filters
            if response.prompt_feedback:
                logger.debug(f"Prompt feedback: {response.prompt_feedback}")

            # Check finish_reason before accessing response.text
            # finish_reason=10 (OTHER) means invalid function call or malformed response
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.finish_reason == 10:  # OTHER - typically invalid function call
                    logger.warning(
                        f"Gemini returned finish_reason=10 (invalid function call). "
                        f"Parts: {len(candidate.content.parts) if candidate.content and candidate.content.parts else 0}"
                    )
                    # Check if it tried to make a function call
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                logger.warning(f"Invalid function call: {part.function_call.name}")
                    # Return error response for orchestrator to handle
                    return (
                        f"NEXT_STEP: DONE\n"
                        f"ERROR: Gemini attempted invalid function call. "
                        f"Step-based workflow should not trigger function calls."
                    )

            # Clean markdown formatting from response (Gemini often adds ``` blocks)
            raw_text = response.text
            cleaned_text = clean_markdown_response(raw_text)

            # Log if cleaning was needed
            if cleaned_text != raw_text:
                logger.debug(f"Cleaned Gemini response: '{raw_text}' -> '{cleaned_text}'")

            return cleaned_text
        except ValueError as e:
            # Handle finish_reason issues (safety blocks, max tokens, etc.)
            error_msg = str(e)
            if "finish_reason" in error_msg:
                # Extract finish_reason value from error message
                logger.error(
                    f"Gemini response blocked: {error_msg}",
                    extra={
                        "error_type": "finish_reason_block",
                        "prompt_length": len(combined_prompt),
                        "max_tokens": max_tokens or self.config.max_tokens
                    }
                )
            raise LLMError(
                message=f"Gemini API error: {e}",
                code="gemini_api_error",
                details={"error": str(e)}
            )
        except Exception as e:
            raise LLMError(
                message=f"Gemini API error: {e}",
                code="gemini_api_error",
                details={"error": str(e)}
            )

    async def create_message_with_functions(
        self,
        system_prompt: str,
        user_prompt: str,
        available_functions: List["FunctionDefinition"],
        function_dispatcher: "FunctionDispatcher",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> "FunctionCallingResult":
        """Generate response with function calling support.

        Implements multi-turn conversation where the LLM can call functions
        and receive their results before generating the final response.

        Args:
            system_prompt: System instruction for the LLM
            user_prompt: User message/query
            available_functions: List of functions the LLM can call
            function_dispatcher: Dispatcher to execute function calls
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (default 0 for determinism)

        Returns:
            FunctionCallingResult with response text, function calls, and metadata

        Raises:
            LLMError: If LLM request fails
        """
        # Import here to avoid circular imports
        from guarantee_email_agent.llm.function_calling import (
            FunctionCall,
            FunctionCallingResult,
        )

        try:
            # Convert functions to Gemini Tool format
            function_declarations = []
            for func in available_functions:
                # Use genai.protos for proper function declaration
                func_decl = genai.protos.FunctionDeclaration(
                    name=func.name,
                    description=func.description,
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            prop_name: genai.protos.Schema(
                                type=self._map_json_type_to_proto(prop_def.get("type", "string")),
                                description=prop_def.get("description", ""),
                                enum=prop_def.get("enum") if "enum" in prop_def else None
                            )
                            for prop_name, prop_def in func.parameters.get("properties", {}).items()
                        },
                        required=func.parameters.get("required", [])
                    )
                )
                function_declarations.append(func_decl)

            # Create tool with function declarations
            tool = genai.protos.Tool(function_declarations=function_declarations)

            # Create model with tools and system instruction
            model_with_tools = genai.GenerativeModel(
                self.config.model,
                tools=[tool],
                system_instruction=system_prompt
            )

            # Configure generation parameters - use temperature 0 for determinism
            generation_config = genai.GenerationConfig(
                temperature=temperature if temperature is not None else 0,
                max_output_tokens=max_tokens or self.config.max_tokens,
            )

            # Start chat for multi-turn conversation
            chat = model_with_tools.start_chat()
            function_calls: List[FunctionCall] = []
            total_turns = 0
            max_iterations = 10

            # Initial message
            logger.debug(
                "Sending initial message to Gemini",
                extra={"prompt_length": len(user_prompt)}
            )
            response = chat.send_message(
                user_prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            total_turns += 1

            # Function calling loop
            while total_turns < max_iterations:
                # Check if response has candidates and parts
                if not response.candidates or not response.candidates[0].content.parts:
                    logger.debug("No content parts in response, ending loop")
                    break

                part = response.candidates[0].content.parts[0]

                # Check for function call
                if hasattr(part, 'function_call') and part.function_call.name:
                    fc = part.function_call
                    function_name = fc.name
                    # Convert MapComposite to dict
                    arguments = dict(fc.args) if fc.args else {}

                    logger.info(
                        "LLM requested function call",
                        extra={
                            "function": function_name,
                            "arguments": arguments,
                            "turn": total_turns
                        }
                    )

                    # Execute function via dispatcher
                    function_result = await function_dispatcher.execute(
                        function_name=function_name,
                        arguments=arguments
                    )
                    function_calls.append(function_result)

                    # Prepare response to send back to LLM
                    if function_result.success:
                        response_data = function_result.result
                    else:
                        response_data = {"error": function_result.error_message}

                    # Send function result back to LLM
                    function_response = genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={"result": response_data}
                        )
                    )

                    try:
                        response = chat.send_message(
                            genai.protos.Content(parts=[function_response]),
                            generation_config=generation_config,
                            safety_settings=self.safety_settings
                        )
                    except IndexError:
                        # Gemini sometimes returns empty response after function calls
                        # Check if send_email was already called
                        email_already_sent = any(
                            fc.function_name == "send_email" and fc.success
                            for fc in function_calls
                        )
                        if email_already_sent:
                            logger.debug(
                                "Empty response after send_email, task complete",
                                extra={"function": function_name, "turn": total_turns}
                            )
                        else:
                            logger.warning(
                                "Empty response before send_email was called",
                                extra={
                                    "function": function_name,
                                    "turn": total_turns,
                                    "function_calls": [fc.function_name for fc in function_calls]
                                }
                            )
                        break
                    total_turns += 1

                else:
                    # No function call - LLM has finished
                    logger.debug(
                        "No function call in response, ending loop",
                        extra={"turn": total_turns}
                    )
                    break

            # Extract final text response
            final_text = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_value = part.text
                        # Ensure we have a string (not a Mock or other object)
                        if isinstance(text_value, str):
                            final_text = clean_markdown_response(text_value)
                            break

            # Check if email was sent via send_email function
            email_sent = any(
                fc.function_name == "send_email" and fc.success
                for fc in function_calls
            )

            logger.info(
                "Function calling completed",
                extra={
                    "total_turns": total_turns,
                    "function_calls_count": len(function_calls),
                    "email_sent": email_sent,
                    "response_length": len(final_text)
                }
            )

            return FunctionCallingResult(
                response_text=final_text,
                function_calls=function_calls,
                total_turns=total_turns,
                email_sent=email_sent
            )

        except Exception as e:
            logger.error(
                "Function calling failed",
                extra={"error": str(e)},
                exc_info=True
            )
            raise LLMError(
                message=f"Gemini function calling error: {e}",
                code="gemini_function_calling_error",
                details={"error": str(e)}
            )

    def _map_json_type_to_proto(self, json_type: str) -> "genai.protos.Type":
        """Map JSON Schema type to Gemini Proto type.

        Args:
            json_type: JSON Schema type string

        Returns:
            Corresponding genai.protos.Type enum value
        """
        type_mapping = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT,
        }
        return type_mapping.get(json_type, genai.protos.Type.STRING)


def create_llm_provider(config: AgentConfig) -> LLMProvider:
    """Factory function to create the appropriate LLM provider.

    Args:
        config: Complete agent configuration

    Returns:
        Initialized LLM provider instance

    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    llm_config = config.llm
    provider = llm_config.provider.lower()

    if provider == "anthropic":
        if not config.secrets.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required for anthropic provider")
        return AnthropicProvider(llm_config, config.secrets.anthropic_api_key)

    elif provider == "gemini":
        if not config.secrets.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for gemini provider")
        return GeminiProvider(llm_config, config.secrets.gemini_api_key)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Supported: anthropic, gemini")
