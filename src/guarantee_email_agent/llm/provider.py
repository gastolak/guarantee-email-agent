"""LLM provider abstraction layer for multiple LLM backends."""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

from anthropic import Anthropic
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
