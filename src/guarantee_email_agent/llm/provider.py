"""LLM provider abstraction layer for multiple LLM backends."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from anthropic import Anthropic
import google.generativeai as genai

from guarantee_email_agent.config.schema import AgentConfig, LLMConfig
from guarantee_email_agent.utils.errors import LLMError

logger = logging.getLogger(__name__)


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
        self.model = genai.GenerativeModel(config.model)
        logger.info(f"Gemini provider initialized: model={config.model}")

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
                generation_config=generation_config
            )

            return response.text
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
