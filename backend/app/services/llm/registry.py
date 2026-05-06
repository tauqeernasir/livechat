"""LLM model registry with provider-aware model initialization."""

import os
from typing import (
    Any,
    Dict,
    List,
)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_qwq import ChatQwen

from app.core.config import (
    settings,
)
from app.core.logging import logger


class LLMRegistry:
    """Registry of available LLM models with pre-initialized instances.

    This class maintains a list of LLM configurations and provides
    methods to retrieve them by name with optional argument overrides.
    """

    LLMS: List[Dict[str, Any]] = []

    @classmethod
    def _normalize_provider(cls) -> str:
        provider = (settings.MODEL_PROVIDER or "openai").strip().lower()
        if provider not in {"openai", "qwen"}:
            logger.warning("invalid_model_provider_using_openai", model_provider=provider)
            return "openai"
        return provider

    @classmethod
    def _build_model(cls, model_name: str, **kwargs: Any) -> BaseChatModel:
        """Build a chat model instance for the configured provider."""
        provider = cls._normalize_provider()

        if provider == "qwen":
            # The official Qwen integration reads DashScope env vars.
            # Map existing project settings so qwen/openai can share config.
            dashscope_key = settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
            dashscope_base = settings.DASHSCOPE_API_BASE or settings.LLM_BASE_URL

            if dashscope_key and not os.getenv("DASHSCOPE_API_KEY"):
                os.environ["DASHSCOPE_API_KEY"] = dashscope_key
            if dashscope_base and not os.getenv("DASHSCOPE_API_BASE"):
                os.environ["DASHSCOPE_API_BASE"] = dashscope_base

            cleaned_kwargs = dict(kwargs)
            if "reasoning" in cleaned_kwargs:
                logger.debug("dropping_unsupported_qwen_kwarg", kwarg="reasoning")
                cleaned_kwargs.pop("reasoning", None)

            model_kwargs = {
                "model": model_name,
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0,
                "max_retries": settings.MAX_LLM_CALL_RETRIES,
            }
            model_kwargs.update(cleaned_kwargs)
            return ChatQwen(**model_kwargs)

        return ChatOpenAI(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.LLM_BASE_URL,
            max_tokens=settings.MAX_TOKENS,
            temperature=0,
            **kwargs,
        )

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Lazily initialize the registry so provider env is respected."""
        if cls.LLMS:
            return

        cls.LLMS = [
            {
                "name": settings.DEFAULT_LLM_MODEL,
                "llm": cls._build_model(settings.DEFAULT_LLM_MODEL),
            }
        ]

        logger.info(
            "llm_registry_initialized",
            model_provider=cls._normalize_provider(),
            default_model=settings.DEFAULT_LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
        )

    @classmethod
    def get(cls, model_name: str, **kwargs) -> BaseChatModel:
        """Get an LLM by name with optional argument overrides.

        When kwargs are provided a fresh ChatOpenAI instance is returned with
        those overrides applied, leaving the shared registry entry untouched.

        Args:
            model_name: Name of the model to retrieve.
            **kwargs: Optional arguments to override default model configuration.

        Returns:
            BaseChatModel instance.

        Raises:
            ValueError: If model_name is not found in LLMS.
        """
        cls._ensure_initialized()
        model_entry = next((e for e in cls.LLMS if e["name"] == model_name), None)

        if not model_entry:
            available = ", ".join(e["name"] for e in cls.LLMS)
            raise ValueError(f"model '{model_name}' not found in registry. available models: {available}")

        if kwargs:
            logger.debug("creating_llm_with_custom_args", model_name=model_name, custom_args=list(kwargs.keys()))
            return cls._build_model(model_name, **kwargs)

        logger.debug("using_default_llm_instance", model_name=model_name)
        return model_entry["llm"]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Return all registered model names in order.

        Returns:
            List of model name strings.
        """
        cls._ensure_initialized()
        return [e["name"] for e in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> Dict[str, Any]:
        """Return the model entry at a specific index, wrapping to 0 if out of range.

        Args:
            index: Index into LLMS.

        Returns:
            Model entry dict.
        """
        cls._ensure_initialized()
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]
