"""LLM service with retries, circular fallback, and optional structured output."""

import asyncio
import logging
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from langchain_core.messages import BaseMessage
from openai import (
    APIError,
    APITimeoutError,
    OpenAIError,
    RateLimitError,
)
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import logger
from app.services.llm.registry import LLMRegistry

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Service for managing LLM calls with retries and circular fallback.

    Two distinct execution paths:

    - **Default path** (no model_name / response_format / model_kwargs): uses
      ``self._llm`` which is the tool-bound agent model. Circular fallback
      updates ``self._llm`` so tool bindings are preserved across retries.

    - **One-off path** (any override provided): resolves a fresh, local
      ``Runnable`` for the call without ever touching ``self._llm``, so
      concurrent default-path calls are never affected.
    """

    def __init__(self):
        """Initialize the LLM service with the configured default model."""
        self._llm: Any = None  # BaseChatModel pre-bind_tools, Runnable after
        self._current_model_index: int = 0
        self._bound_tools: List = []

        all_names = LLMRegistry.get_all_names()
        try:
            self._current_model_index = all_names.index(settings.DEFAULT_LLM_MODEL)
            self._llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
            logger.info(
                "llm_service_initialized",
                default_model=settings.DEFAULT_LLM_MODEL,
                model_index=self._current_model_index,
                total_models=len(all_names),
                environment=settings.ENVIRONMENT.value,
            )
        except Exception as e:
            self._current_model_index = 0
            self._llm = LLMRegistry.LLMS[0]["llm"]
            logger.warning(
                "default_model_not_found_using_first",
                requested=settings.DEFAULT_LLM_MODEL,
                using=all_names[0] if all_names else "none",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @overload
    async def call(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = ...,
        response_format: None = ...,
        **model_kwargs: Any,
    ) -> BaseMessage: ...

    @overload
    async def call(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = ...,
        response_format: Type[T] = ...,
        **model_kwargs: Any,
    ) -> T: ...

    async def call(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        response_format: Optional[Type[BaseModel]] = None,
        **model_kwargs: Any,
    ) -> Union[BaseMessage, BaseModel]:
        """Call the LLM with retries and circular fallback.

        Args:
            messages: Conversation messages to send.
            model_name: Override the model. ``None`` uses the current default.
            response_format: Pydantic schema for structured output. When
                provided the call chains ``.with_structured_output(schema)``
                and returns a validated instance of that schema instead of a
                raw ``BaseMessage``.
            **model_kwargs: Extra kwargs forwarded to ``LLMRegistry.get`` when
                constructing a one-off model instance (e.g. ``temperature``,
                ``max_tokens``, ``reasoning``).

        Returns:
            ``BaseMessage`` when ``response_format`` is ``None``, otherwise a
            validated instance of ``response_format``.

        Raises:
            RuntimeError: When all models fail after retries or the total
                timeout budget is exceeded.
        """
        try:
            return await asyncio.wait_for(
                self._call_with_fallback(messages, model_name, response_format, model_kwargs),
                timeout=settings.LLM_TOTAL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.exception(
                "llm_total_timeout_exceeded",
                timeout_seconds=settings.LLM_TOTAL_TIMEOUT,
            )
            raise RuntimeError(f"llm call timed out after {settings.LLM_TOTAL_TIMEOUT}s total budget")

    def get_llm(self) -> Any:
        """Return the current tool-bound default LLM instance.

        Returns:
            Current ``BaseChatModel`` instance or ``None`` if not initialised.
        """
        return self._llm

    async def call_with_tools(
        self,
        messages: List[BaseMessage],
        tools: List,
    ) -> BaseMessage:
        """Call the LLM with a per-request tool set (no shared state mutation).

        This creates a fresh tool-bound model for the call so workspace-specific
        tool lists don't interfere with each other or the default agent path.

        Args:
            messages: Conversation messages.
            tools: LangChain tools to bind for this call only.

        Returns:
            BaseMessage from the LLM.
        """
        try:
            return await asyncio.wait_for(
                self._call_with_tools_impl(messages, tools),
                timeout=settings.LLM_TOTAL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.exception("llm_call_with_tools_timeout")
            raise RuntimeError(f"LLM call with tools timed out after {settings.LLM_TOTAL_TIMEOUT}s")

    async def _call_with_tools_impl(
        self,
        messages: List[BaseMessage],
        tools: List,
    ) -> BaseMessage:
        """Internal: one-off tool-bound call with fallback loop."""
        total = len(LLMRegistry.LLMS)
        start = self._current_model_index

        def get_target(idx: int) -> Any:
            base = LLMRegistry.get(LLMRegistry.LLMS[idx]["name"])
            return base.bind_tools(tools)

        def advance(idx: int) -> Optional[int]:
            return (idx + 1) % total

        return await self._fallback_loop(messages, start, get_target, advance)

    def bind_tools(self, tools: List) -> "LLMService":
        """Bind tools to the default LLM instance.

        Args:
            tools: List of tools to bind.

        Returns:
            Self for method chaining.
        """
        if self._llm:
            self._bound_tools = tools
            self._llm = self._llm.bind_tools(tools)
            logger.debug("tools_bound_to_llm", tool_count=len(tools))
        return self

    def get_tool_bound_llm(self, tools: List) -> Any:
        """Return a *new* tool-bound LLM without mutating the shared default instance.

        Use this for per-workspace dynamic tool sets so concurrent requests
        with different tool lists don't interfere.

        Args:
            tools: List of LangChain tools to bind.

        Returns:
            A tool-bound Runnable (same type as self._llm after bind_tools).
        """
        base = LLMRegistry.get(
            LLMRegistry.LLMS[self._current_model_index]["name"]
        )
        return base.bind_tools(tools)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(settings.MAX_LLM_CALL_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _invoke_with_retry(self, llm: Any, messages: List[BaseMessage]) -> Any:
        """Invoke an LLM runnable with automatic per-model retry logic.

        Args:
            llm: Any LangChain ``Runnable`` (plain model or structured-output chain).
            messages: Messages to send.

        Returns:
            The runnable's response (``BaseMessage`` or a ``BaseModel`` instance).

        Raises:
            OpenAIError: Propagated after all retry attempts are exhausted.
        """
        try:
            # We use astream and manually aggregate to prevent LangChain's AIMessageChunk.__add__
            # from dropping custom structured blocks (like reasoning/text lists) returned by llama-server
            # during streaming.
            final_response = None
            text_content = ""
            
            if hasattr(llm, "astream"):
                try:
                    async for chunk in llm.astream(messages):
                        if final_response is None:
                            final_response = chunk
                        else:
                            # Let LangChain handle tool_call_chunks merging and parsing
                            final_response += chunk
                                
                        # Extract text safely from various chunk formats to bypass LangChain dropping them
                        if isinstance(chunk.content, str):
                            text_content += chunk.content
                        elif isinstance(chunk.content, list):
                            for block in chunk.content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text_content += block.get("text", "")
                                elif isinstance(block, str):
                                    text_content += block
                                    
                    if final_response is not None:
                        # Overwrite the broken aggregated content with our pristine manual text
                        final_response.content = text_content
                        response = final_response
                    else:
                        response = await llm.ainvoke(messages)
                except Exception as stream_err:
                    if final_response is not None:
                        logger.warning("astream_failed_mid_stream", error=str(stream_err))
                        raise
                    logger.debug("astream_failed_falling_back_to_ainvoke", error=str(stream_err))
                    response = await llm.ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)
                
            logger.debug("llm_call_successful", message_count=len(messages))
            return response
        except (RateLimitError, APITimeoutError, APIError) as e:
            logger.warning(
                "llm_call_failed_retrying",
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True,
            )
            raise
        except OpenAIError as e:
            logger.error(
                "llm_call_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    def _switch_to_next_model(self) -> bool:
        """Advance the default model to the next entry in the registry (circular).

        Mutates ``self._llm`` and ``self._current_model_index`` so tool bindings
        survive model switches on the default agent path.

        Returns:
            ``True`` on success, ``False`` if the switch failed.
        """
        try:
            next_index = (self._current_model_index + 1) % len(LLMRegistry.LLMS)
            next_entry = LLMRegistry.get_model_at_index(next_index)
            logger.warning(
                "switching_to_next_model",
                from_index=self._current_model_index,
                to_index=next_index,
                to_model=next_entry["name"],
            )
            self._current_model_index = next_index
            self._llm = next_entry["llm"]
            if self._bound_tools:
                self._llm = self._llm.bind_tools(self._bound_tools)
            logger.info("model_switched", new_model=next_entry["name"], new_index=next_index)
            return True
        except Exception as e:
            logger.error("model_switch_failed", error=str(e))
            return False

    async def _call_with_fallback(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str],
        response_format: Optional[Type[BaseModel]],
        model_kwargs: dict,
    ) -> Union[BaseMessage, BaseModel]:
        """Build path-specific strategies and delegate to the shared fallback loop.

        One-off path (any override set):
            ``get_target`` builds a fresh registry instance each attempt.
            ``advance`` increments a local index — ``self._llm`` is never touched.

        Default path (no overrides):
            ``get_target`` returns ``self._llm`` (tool-bound).
            ``advance`` calls ``_switch_to_next_model`` so bindings persist.
        """
        if model_name or response_format or model_kwargs:
            all_names = LLMRegistry.get_all_names()
            if model_name and model_name not in all_names:
                logger.error("requested_model_not_found", model_name=model_name)
                raise ValueError(
                    f"model '{model_name}' not found in registry. available models: {', '.join(all_names)}"
                )

            start = all_names.index(model_name) if model_name else self._current_model_index
            total = len(LLMRegistry.LLMS)

            def get_target(idx: int) -> Any:
                base = LLMRegistry.get(LLMRegistry.LLMS[idx]["name"], **model_kwargs)
                return base.with_structured_output(response_format) if response_format else base

            def advance(idx: int) -> Optional[int]:
                return (idx + 1) % total
        else:
            start = self._current_model_index

            def get_target(_: int) -> Any:
                return self._llm

            def advance(_: int) -> Optional[int]:
                return self._current_model_index if self._switch_to_next_model() else None

        return await self._fallback_loop(messages, start, get_target, advance)

    async def _fallback_loop(
        self,
        messages: List[BaseMessage],
        start: int,
        get_target: Callable[[int], Any],
        advance: Callable[[int], Optional[int]],
    ) -> Any:
        """Shared fallback loop — try each model in turn until one succeeds.

        Args:
            messages: Messages to send.
            start: Registry index to begin from.
            get_target: Returns the ``Runnable`` to invoke for a given index.
            advance: Returns the next index to try, or ``None`` to stop.

        Returns:
            The first successful response.

        Raises:
            RuntimeError: When all models have been exhausted.
        """
        total = len(LLMRegistry.LLMS)
        current = start
        models_tried = 0
        last_error: Optional[Exception] = None

        for models_tried in range(1, total + 1):
            current_name = LLMRegistry.LLMS[current]["name"]
            try:
                return await self._invoke_with_retry(get_target(current), messages)
            except OpenAIError as e:
                last_error = e
                logger.error(
                    "llm_call_failed_after_retries",
                    model=current_name,
                    models_tried=models_tried,
                    total_models=total,
                    error=str(e),
                )
                if models_tried >= total:
                    logger.error(
                        "all_models_failed", models_tried=models_tried, starting_model=LLMRegistry.LLMS[start]["name"]
                    )
                    break
                next_idx = advance(current)
                if next_idx is None:
                    logger.error("failed_to_switch_to_next_model")
                    break
                current = next_idx

        raise RuntimeError(
            f"failed to get response from llm after trying {models_tried} models. last error: {str(last_error)}"
        )


llm_service = LLMService()
