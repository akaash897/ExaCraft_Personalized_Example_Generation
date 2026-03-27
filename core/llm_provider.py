"""
LLM Provider Factory
Handles creation and configuration of different LLM providers (OpenAI, OpenRouter).

Supported providers:
  openai     — OpenAI API (gpt-* models)
  openrouter — OpenRouter API (any model, e.g. deepseek/deepseek-v3.2)
               Pass model as the full OpenRouter model ID.
               Reasoning is disabled by default for generation providers to
               prevent <think> traces from corrupting example output.
"""

from enum import Enum
from typing import Optional


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI      = "openai"
    OPENROUTER  = "openrouter"


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class LLMProviderFactory:
    """Factory for creating LLM instances based on provider selection"""

    @staticmethod
    def create_llm(
        provider: str = "openai",
        api_key: str = None,
        model: str = None,
        temperature: float = 0.3,
        **kwargs
    ):
        """
        Create LLM instance based on provider.

        Args:
            provider:    "openai" or "openrouter"
            api_key:     API key for the provider
            model:       Model name (uses provider default if None).
                         For openrouter, pass the full model ID,
                         e.g. "deepseek/deepseek-v3.2".
            temperature: Temperature for generation (default: 0.3)
            **kwargs:    Additional provider-specific parameters

        Returns:
            LangChain ChatModel instance

        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        if not api_key:
            raise ValueError(f"API key is required for provider: {provider}")

        provider = provider.lower()

        if not model:
            model = LLMProviderFactory.get_default_model(provider)

        if provider == LLMProvider.OPENAI.value:
            return LLMProviderFactory._create_openai_llm(api_key, model, temperature, **kwargs)
        elif provider == LLMProvider.OPENROUTER.value:
            return LLMProviderFactory._create_openrouter_llm(api_key, model, temperature, **kwargs)
        else:
            supported = [p.value for p in LLMProvider]
            raise ValueError(
                f"Provider '{provider}' is not supported. "
                f"Supported providers: {', '.join(supported)}"
            )

    @staticmethod
    def _create_openai_llm(api_key: str, model: str, temperature: float, **kwargs):
        """Create OpenAI LLM instance"""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenAI provider. "
                "Install it with: pip install langchain-openai"
            )

        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            temperature=temperature,
            **kwargs
        )

    @staticmethod
    def _create_openrouter_llm(api_key: str, model: str, temperature: float, **kwargs):
        """
        Create an OpenRouter LLM instance via the OpenAI-compatible API.

        Reasoning is disabled by default so that thinking models (e.g.
        DeepSeek V3.2) do not emit <think> traces into generated examples.
        Pass disable_reasoning=False in kwargs to override.
        """
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenRouter provider. "
                "Install it with: pip install langchain-openai"
            )

        disable_reasoning = kwargs.pop("disable_reasoning", True)

        model_kwargs = {}
        if disable_reasoning:
            model_kwargs["reasoning"] = {"enabled": False}

        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=OPENROUTER_BASE_URL,
            temperature=temperature,
            model_kwargs=model_kwargs,
            default_headers={
                "HTTP-Referer": "https://agicraft.local",
                "X-Title": "AgiCraft",
            },
            **kwargs
        )

    @staticmethod
    def get_default_model(provider: str) -> str:
        """
        Get default model name for provider.

        Args:
            provider: "openai" or "openrouter"

        Returns:
            Default model name string
        """
        provider = provider.lower()

        defaults = {
            LLMProvider.OPENAI.value:      "gpt-5-nano",
            LLMProvider.OPENROUTER.value:  "deepseek/deepseek-v3.2",
        }

        if provider not in defaults:
            supported = list(defaults.keys())
            raise ValueError(
                f"Provider '{provider}' is not supported. "
                f"Supported providers: {', '.join(supported)}"
            )

        return defaults[provider]

    @staticmethod
    def validate_api_key(provider: str, api_key: str) -> bool:
        """
        Validate API key format for provider.

        Args:
            provider: Provider name
            api_key:  API key to validate

        Returns:
            True if API key format is valid, False otherwise
        """
        if not api_key or not isinstance(api_key, str):
            return False

        provider = provider.lower()

        if provider == LLMProvider.OPENAI.value:
            return api_key.startswith("sk-") and len(api_key) > 20
        elif provider == LLMProvider.OPENROUTER.value:
            # OpenRouter keys start with "sk-or-"
            return api_key.startswith("sk-or-") and len(api_key) > 20

        return False

    @staticmethod
    def get_supported_providers() -> list:
        """Return list of supported provider names."""
        return [p.value for p in LLMProvider]
