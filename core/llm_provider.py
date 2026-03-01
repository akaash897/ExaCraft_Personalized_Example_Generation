"""
LLM Provider Factory
Handles creation and configuration of different LLM providers (Gemini, OpenAI, etc.)
"""

from enum import Enum
from typing import Optional


class LLMProvider(Enum):
    """Supported LLM providers"""
    GEMINI = "gemini"
    OPENAI = "openai"


class LLMProviderFactory:
    """Factory for creating LLM instances based on provider selection"""

    @staticmethod
    def create_llm(
        provider: str = "gemini",
        api_key: str = None,
        model: str = None,
        temperature: float = 0.3,
        **kwargs
    ):
        """
        Create LLM instance based on provider

        Args:
            provider: "gemini" or "openai"
            api_key: API key for the provider
            model: Model name (uses provider default if None)
            temperature: Temperature for generation (default: 0.3)
            **kwargs: Additional provider-specific parameters

        Returns:
            LangChain ChatModel instance

        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        if not api_key:
            raise ValueError(f"API key is required for provider: {provider}")

        # Normalize provider name
        provider = provider.lower()

        # Get default model if not specified
        if not model:
            model = LLMProviderFactory.get_default_model(provider)

        # Create provider-specific LLM instance
        if provider == LLMProvider.GEMINI.value:
            return LLMProviderFactory._create_gemini_llm(api_key, model, temperature, **kwargs)
        elif provider == LLMProvider.OPENAI.value:
            return LLMProviderFactory._create_openai_llm(api_key, model, temperature, **kwargs)
        else:
            supported = [p.value for p in LLMProvider]
            raise ValueError(
                f"Provider '{provider}' is not supported. "
                f"Supported providers: {', '.join(supported)}"
            )

    @staticmethod
    def _create_gemini_llm(api_key: str, model: str, temperature: float, **kwargs):
        """Create Google Gemini LLM instance"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required for Gemini provider. "
                "Install it with: pip install langchain-google-genai"
            )

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            **kwargs
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
    def get_default_model(provider: str) -> str:
        """
        Get default model name for provider

        Args:
            provider: Provider name ("gemini" or "openai")

        Returns:
            Default model name

        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()

        defaults = {
            LLMProvider.GEMINI.value: "gemini-2.5-flash",
            LLMProvider.OPENAI.value: "gpt-4o-mini"
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
        Validate API key format for provider

        Args:
            provider: Provider name
            api_key: API key to validate

        Returns:
            True if API key format is valid, False otherwise
        """
        if not api_key or not isinstance(api_key, str):
            return False

        provider = provider.lower()

        # Basic format validation
        if provider == LLMProvider.GEMINI.value:
            # Gemini keys typically start with "AIza"
            return api_key.startswith("AIza") and len(api_key) > 20
        elif provider == LLMProvider.OPENAI.value:
            # OpenAI keys start with "sk-"
            return api_key.startswith("sk-") and len(api_key) > 20

        return False

    @staticmethod
    def get_supported_providers() -> list:
        """
        Get list of supported provider names

        Returns:
            List of supported provider names
        """
        return [p.value for p in LLMProvider]
