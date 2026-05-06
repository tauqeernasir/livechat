"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

import asyncio
from typing import (
    AsyncGenerator,
    Optional,
)
from urllib.parse import quote_plus

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.errors import GraphInterrupt
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import (
    Command,
    CompiledStateGraph,
)
from sqlmodel import (
    select,
    Session as SQLModelSession,
)
from langgraph.types import (
    RunnableConfig,
    StateSnapshot,
)
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.policy import evaluate_query_policy
from app.core.langgraph.tools import tools
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.observability import langfuse_callback_handler
from app.core.prompts import (
    load_classifier_prompt,
    load_system_prompt,
)
from app.schemas import (
    GraphState,
    Message,
    QueryClassification,
)
from app.services.database import database_service
from app.services.knowledge.service import knowledge_service
from app.services.llm import llm_service
from app.services.integrations.service import integration_service
from app.services.integrations.openapi_tools import build_openapi_tools
from app.utils import (
    dump_messages,
    extract_text_content,
    prepare_messages,
    process_llm_response,
)
from app.models.agent_config import AgentConfiguration



class LangGraphAgent:
    """Manages the LangGraph Agent/workflow and interactions with the LLM.

    This class handles the creation and management of the LangGraph workflow,
    including LLM interactions, database connections, and response processing.
    """

    def __init__(self):
        """Initialize the LangGraph Agent with necessary components."""
        self.llm_service = llm_service
        # Bind base (built-in) tools for the default path
        self.base_tools = tools
        self.llm_service.bind_tools(self.base_tools)
        self.base_tools_by_name = {tool.name: tool for tool in self.base_tools}
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None
        logger.info(
            "langgraph_agent_initialized",
            model=settings.DEFAULT_LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    @staticmethod
    def _latest_user_message(messages: list) -> str:
        """Extract the latest user message content from graph state messages."""
        def _normalize_content(content: object) -> str:
            if content is None:
                return ""
            if isinstance(content, list):
                return extract_text_content(content).strip()
            return str(content).strip()

        for message in reversed(messages):
            role = getattr(message, "role", None)
            msg_type = getattr(message, "type", None)
            content = getattr(message, "content", None)

            if isinstance(message, dict):
                role = message.get("role")
                msg_type = message.get("type")
                content = message.get("content")

            is_user_message = role in {"user", "human"} or msg_type == "human"
            normalized_content = _normalize_content(content)

            if is_user_message and normalized_content:
                return normalized_content
        return ""

    async def _classify_query(self, state: GraphState, config: RunnableConfig) -> Command:
        """Classify latest user intent and relevance before entering chat flow."""
        latest_user_query = self._latest_user_message(state.messages)

        logger.info(
            "latest_user_query",
            session_id=config["configurable"]["thread_id"],
            latest_user_query=latest_user_query,
        )

        if not latest_user_query:
            return Command(
                update={
                    "intent": "support",
                    "is_relevant": True,
                    "relevance_confidence": 0.5,
                    "classifier_reason": "no_user_message_found",
                    "needs_clarification": False,
                    "kb_required": False,
                    "kb_used": False,
                    "kb_result_count": 0,
                    "kb_context": "",
                    "guardrail_status": "clear",
                },
                goto="retrieve_kb",
            )

        try:
            # Load persona from agent configuration for this workspace
            persona = None
            metadata = config.get("metadata", {})
            workspace_id = metadata.get("workspace_id")
            if workspace_id:
                try:
                    async with database_service.async_session_maker() as db_session:
                        statement = select(AgentConfiguration).where(
                            AgentConfiguration.workspace_id == int(workspace_id)
                        )
                        result = await db_session.execute(statement)
                        agent_config = result.scalar_one_or_none()
                        if agent_config and agent_config.persona:
                            import re as _re
                            persona = _re.sub(r"<[^>]*>", "", agent_config.persona)
                except Exception as e:
                    logger.warning("classifier_persona_load_failed", error=str(e))

            classifier_prompt = load_classifier_prompt(persona=persona)

            # Include last few messages for conversational context
            recent_messages = []
            for msg in state.messages[-4:]:
                msg_type = getattr(msg, "type", None)
                content = getattr(msg, "content", "")
                if isinstance(msg, dict):
                    msg_type = msg.get("type") or msg.get("role")
                    content = msg.get("content", "")
                if msg_type in ("human", "user"):
                    recent_messages.append(HumanMessage(content=str(content)))
                elif msg_type in ("ai", "assistant"):
                    recent_messages.append(AIMessage(content=str(content)))

            classification = await self.llm_service.call(
                [
                    SystemMessage(content=classifier_prompt),
                    *recent_messages,
                ],
                response_format=QueryClassification,
                use_streaming=False,
                max_tokens=160,
                reasoning={"effort": "low"},
            )

            intent = classification.intent
            is_relevant = classification.is_relevant
            if not is_relevant:
                intent = "irrelevant"

            policy_decision = evaluate_query_policy(
                intent=intent,
                is_relevant=is_relevant,
                confidence=classification.confidence,
                low_threshold=settings.CLASSIFIER_CONFIDENCE_LOW_THRESHOLD,
                medium_threshold=settings.CLASSIFIER_CONFIDENCE_MEDIUM_THRESHOLD,
            )

            logger.info(
                "query_classified",
                session_id=config["configurable"]["thread_id"],
                intent=intent,
                is_relevant=is_relevant,
                confidence=classification.confidence,
                needs_clarification=policy_decision.needs_clarification,
                kb_required=classification.kb_required,
                guardrail_status=policy_decision.guardrail_status,
            )

            return Command(
                update={
                    "intent": intent,
                    "is_relevant": is_relevant,
                    "relevance_confidence": classification.confidence,
                    "classifier_reason": classification.reason,
                    "needs_clarification": policy_decision.needs_clarification,
                    "kb_required": classification.kb_required and bool(is_relevant),
                    "kb_used": False,
                    "kb_result_count": 0,
                    "kb_context": "",
                    "guardrail_status": policy_decision.guardrail_status,
                },
                goto=(
                    "reject"
                    if policy_decision.route == "reject"
                    else "clarify_query"
                    if policy_decision.needs_clarification
                    else "retrieve_kb"
                    if classification.kb_required
                    else "chat"
                ),
            )
        except Exception as e:
            logger.exception(
                "query_classification_failed",
                session_id=config["configurable"]["thread_id"],
                error=str(e),
            )
            # Fail-open so valid user requests are not blocked if classifier fails.
            return Command(
                update={
                    "intent": "support",
                    "is_relevant": False,
                    "relevance_confidence": 0.0,
                    "classifier_reason": "classifier_failed_safe_fallback",
                    "needs_clarification": True,
                    "kb_required": False,
                    "kb_used": False,
                    "kb_result_count": 0,
                    "kb_context": "",
                    "guardrail_status": "classifier_failed",
                },
                goto="safe_fallback",
            )

    async def _clarify_query(self, state: GraphState) -> Command:
        """Ask a concise clarification when intent/relevance confidence is low."""
        del state
        response_message = AIMessage(
            content=(
                "I want to make sure I help accurately. Are you asking about our products, pricing, onboarding, "
                "or account/support services? If yes, share a little more detail so I can give a precise answer."
            )
        )
        return Command(update={"messages": [response_message]}, goto=END)

    async def _retrieve_kb(self, state: GraphState, config: RunnableConfig) -> Command:
        """Retrieve company-specific context deterministically before final answer synthesis."""
        latest_user_query = self._latest_user_message(state.messages)
        metadata = config.get("metadata", {})
        workspace_id = metadata.get("workspace_id")

        if not latest_user_query:
            return Command(
                update={
                    "kb_required": True,
                    "kb_used": True,
                    "kb_result_count": 0,
                    "kb_context": "",
                },
                goto="chat",
            )

        if not workspace_id:
            logger.warning("kb_retrieval_skipped_workspace_missing")
            return Command(
                update={
                    "kb_required": True,
                    "kb_used": False,
                    "kb_result_count": 0,
                    "kb_context": "",
                },
                goto="chat",
            )

        try:
            async with database_service.async_session_maker() as session:
                results = await knowledge_service.retrieve_relevant_chunks(
                    session=session,
                    workspace_id=int(workspace_id),
                    query=latest_user_query,
                    k=4,
                )

            formatted_results: list[str] = []
            for index, result in enumerate(results, 1):
                source = str(result.get("source", "unknown"))
                text = str(result.get("text", "")).strip()
                if text:
                    formatted_results.append(
                        f"--- Result {index} (Source: {source}) ---\n{text}"
                    )

            kb_context = "\n\n".join(formatted_results)

            logger.info(
                "kb_retrieval_completed",
                session_id=config["configurable"]["thread_id"],
                workspace_id=workspace_id,
                result_count=len(formatted_results),
            )

            return Command(
                update={
                    "kb_required": True,
                    "kb_used": True,
                    "kb_result_count": len(formatted_results),
                    "kb_context": kb_context,
                },
                goto="chat",
            )
        except Exception as e:
            logger.exception(
                "kb_retrieval_failed",
                session_id=config["configurable"]["thread_id"],
                workspace_id=workspace_id,
                error=str(e),
            )
            return Command(
                update={
                    "kb_required": True,
                    "kb_used": False,
                    "kb_result_count": 0,
                    "kb_context": "",
                    "guardrail_status": "classifier_failed",
                },
                goto="safe_fallback",
            )

    async def _reject_irrelevant(self, state: GraphState) -> Command:
        """Return a polite rejection for requests outside company domain."""
        del state
        response_message = AIMessage(
            content=(
                "I can only help with topics related to our company's products and services. "
                "Please share a question about our offerings, pricing, onboarding, account issues, or support needs."
            )
        )
        return Command(update={"messages": [response_message]}, goto=END)

    async def _safe_fallback(self, state: GraphState) -> Command:
        """Return a safe fallback when classification/tooling fails."""
        del state
        response_message = AIMessage(
            content=(
                "I could not confidently process that request right now. "
                "Please ask a company-related question about products, pricing, onboarding, or support, "
                "and include a bit more detail."
            )
        )
        return Command(update={"messages": [response_message]}, goto=END)

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        """Get a PostgreSQL connection pool using environment-specific settings.

        Returns:
            AsyncConnectionPool: A connection pool for PostgreSQL database.
        """
        if self._connection_pool is None:
            try:
                # Configure pool size based on environment
                max_size = settings.POSTGRES_POOL_SIZE

                connection_url = (
                    "postgresql://"
                    f"{quote_plus(settings.POSTGRES_USER)}:{quote_plus(settings.POSTGRES_PASSWORD)}"
                    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                )

                self._connection_pool = AsyncConnectionPool(
                    connection_url,
                    open=False,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,
                    },
                )
                await self._connection_pool.open()
                logger.info("connection_pool_created", max_size=max_size, environment=settings.ENVIRONMENT.value)
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we might want to degrade gracefully
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_connection_pool", environment=settings.ENVIRONMENT.value)
                    return None
                raise e
        return self._connection_pool

    async def _chat(self, state: GraphState, config: RunnableConfig) -> Command:
        """Process the chat state and generate a response.

        Args:
            state (GraphState): The current state of the conversation.
            config (RunnableConfig): The runnable configuration for this invocation.

        Returns:
            Command: Command object with updated state and next node to execute.
        """
        # Get the current LLM instance for metrics
        current_llm = self.llm_service.get_llm()
        model_name = (
            current_llm.model_name
            if current_llm and hasattr(current_llm, "model_name")
            else settings.DEFAULT_LLM_MODEL
        )

        metadata = config.get("metadata", {})
        username = metadata.get("username")
        workspace_id = metadata.get("workspace_id")

        # Load agent configuration for this workspace
        persona = None
        fallback_rule = None
        if workspace_id:
            try:
                async with database_service.async_session_maker() as db_session:
                    statement = select(AgentConfiguration).where(AgentConfiguration.workspace_id == int(workspace_id))
                    result = await db_session.execute(statement)
                    agent_config = result.scalar_one_or_none()
                    if agent_config:
                        import re
                        persona = re.sub(r"<[^>]*>", "", agent_config.persona) if agent_config.persona else None
                        fallback_rule = agent_config.fallback_rule
            except Exception as e:
                logger.error("failed_to_load_agent_config", workspace_id=workspace_id, error=str(e))

        SYSTEM_PROMPT = load_system_prompt(
            username=username, 
            persona=persona,
            fallback_rule=fallback_rule
        )

        # Inject deterministic KB retrieval context for in-scope answers.
        kb_context = (state.kb_context or "").strip()
        if kb_context:
            SYSTEM_PROMPT = (
                f"{SYSTEM_PROMPT}\n\n"
                "# Retrieved Knowledge Base Context\n"
                "Use only the context below for company/service factual claims.\n"
                "If the context is insufficient, say so and ask a concise follow-up question.\n\n"
                f"{kb_context}"
            )

        # Prepare messages with system prompt
        messages = prepare_messages(state.messages, SYSTEM_PROMPT)

        # Resolve workspace-specific integration tools
        workspace_tools = []
        if workspace_id:
            try:
                async with database_service.async_session_maker() as db_session:
                    enabled_ops = await integration_service.get_enabled_operations(
                        db_session, int(workspace_id)
                    )
                if enabled_ops:
                    workspace_tools = build_openapi_tools(enabled_ops)
                    logger.info(
                        "workspace_tools_resolved",
                        workspace_id=workspace_id,
                        tool_count=len(workspace_tools),
                    )
            except Exception as e:
                logger.error(
                    "failed_to_load_workspace_tools",
                    workspace_id=workspace_id,
                    error=str(e),
                )

        # Combine base + workspace tools
        all_tools = list(self.base_tools) + workspace_tools
        all_tools_by_name = {tool.name: tool for tool in all_tools}

        try:
            # Use per-request tool binding when workspace has extra tools
            with llm_inference_duration_seconds.labels(model=model_name).time():
                if workspace_tools:
                    response_message = await self.llm_service.call_with_tools(
                        dump_messages(messages), all_tools
                    )
                else:
                    response_message = await self.llm_service.call(dump_messages(messages))

            # Process response to handle structured content blocks
            response_message = process_llm_response(response_message)

            logger.info(
                "llm_response_generated",
                session_id=config["configurable"]["thread_id"],
                model=model_name,
                environment=settings.ENVIRONMENT.value,
            )

            # Determine next node based on whether there are tool calls
            if response_message.tool_calls:
                goto = "tool_call"
            else:
                goto = END

            return Command(update={"messages": [response_message]}, goto=goto)
        except Exception as e:
            logger.error(
                "llm_call_failed_all_models",
                session_id=config["configurable"]["thread_id"],
                error=str(e),
                environment=settings.ENVIRONMENT.value,
            )
            raise Exception(f"failed to get llm response after trying all models: {str(e)}")

    # Define our tool node
    async def _tool_call(self, state: GraphState, config: RunnableConfig) -> Command:
        """Process tool calls from the last message.

        Resolves workspace-specific integration tools dynamically so that
        both base tools and OpenAPI tools can be dispatched.

        Args:
            state: The current agent state containing messages and tool calls.
            config: The runnable configuration for this invocation.

        Returns:
            Command: Command object with updated messages and routing back to chat.
        """
        try:
            tool_calls = state.messages[-1].tool_calls

            # Build the combined tools map for this workspace
            tools_by_name = dict(self.base_tools_by_name)

            metadata = config.get("metadata", {})
            workspace_id = metadata.get("workspace_id")
            if workspace_id:
                try:
                    async with database_service.async_session_maker() as db_session:
                        enabled_ops = await integration_service.get_enabled_operations(
                            db_session, int(workspace_id)
                        )
                    if enabled_ops:
                        for t in build_openapi_tools(enabled_ops):
                            tools_by_name[t.name] = t
                except Exception as e:
                    logger.error(
                        "failed_to_load_workspace_tools_in_tool_call",
                        workspace_id=workspace_id,
                        error=str(e),
                    )

            async def _execute_tool(tool_call: dict) -> ToolMessage:
                tool_name = tool_call["name"]
                tool = tools_by_name.get(tool_name)
                if tool is None:
                    logger.warning("tool_not_found", tool_name=tool_name)
                    return ToolMessage(
                        content=f"Error: tool '{tool_name}' is not available.",
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                tool_result = await tool.ainvoke(tool_call["args"])
                return ToolMessage(
                    content=tool_result,
                    name=tool_name,
                    tool_call_id=tool_call["id"],
                )

            # Execute tool calls concurrently when multiple are requested
            if len(tool_calls) == 1:
                outputs = [await _execute_tool(tool_calls[0])]
            else:
                outputs = list(await asyncio.gather(*[_execute_tool(tc) for tc in tool_calls]))

            return Command(update={"messages": outputs}, goto="chat")
        except Exception as e:
            logger.exception(
                "tool_call_failed",
                session_id=config["configurable"]["thread_id"],
                error=str(e),
            )
            return Command(
                update={"guardrail_status": "classifier_failed"},
                goto="safe_fallback",
            )

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """Create and configure the LangGraph workflow.

        Returns:
            Optional[CompiledStateGraph]: The configured LangGraph instance or None if init fails
        """
        if self._graph is None:
            try:
                graph_builder = StateGraph(GraphState)
                graph_builder.add_node(
                    "classify_query",
                    self._classify_query,
                    ends=["clarify_query", "retrieve_kb", "reject", "safe_fallback"],
                )
                graph_builder.add_node("clarify_query", self._clarify_query, ends=[END])
                graph_builder.add_node("retrieve_kb", self._retrieve_kb, ends=["chat", "safe_fallback"])
                graph_builder.add_node("chat", self._chat, ends=["tool_call", END])
                graph_builder.add_node("tool_call", self._tool_call, ends=["chat"])
                graph_builder.add_node("reject", self._reject_irrelevant, ends=[END])
                graph_builder.add_node("safe_fallback", self._safe_fallback, ends=[END])
                graph_builder.set_entry_point("classify_query")

                # Get connection pool (may be None in production if DB unavailable)
                connection_pool = await self._get_connection_pool()
                if connection_pool:
                    checkpointer = AsyncPostgresSaver(connection_pool)
                    await checkpointer.setup()
                else:
                    # In production, proceed without checkpointer if needed
                    checkpointer = None
                    if settings.ENVIRONMENT != Environment.PRODUCTION:
                        raise Exception("Connection pool initialization failed")

                self._graph = graph_builder.compile(
                    checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})"
                )

                logger.info(
                    "graph_created",
                    graph_name=f"{settings.PROJECT_NAME} Agent",
                    environment=settings.ENVIRONMENT.value,
                    has_checkpointer=checkpointer is not None,
                )
            except Exception as e:
                logger.error("graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we don't want to crash the app
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_graph")
                    return None
                raise e

        return self._graph

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        workspace_id: int,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> list[dict]:
        """Get a response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.
            username (Optional[str]): The display name of the user.

        Returns:
            list[dict]: The response from the LLM.
        """
        if self._graph is None:
            self._graph = await self.create_graph()
        callbacks = [langfuse_callback_handler] if settings.LANGFUSE_TRACING_ENABLED else []
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": callbacks,
            "metadata": {
                "user_id": user_id,
                "username": username,
                "session_id": session_id,
                "workspace_id": workspace_id,
                "environment": settings.ENVIRONMENT.value,
                "debug": settings.DEBUG,
            },
        }

        try:
            state = await self._graph.aget_state(config)

            if state.next:
                logger.info("resuming_interrupted_graph", session_id=session_id, next_nodes=state.next)
                response = await self._graph.ainvoke(
                    Command(resume=messages[-1].content),
                    config=config,
                )
            else:
                response = await self._graph.ainvoke(
                    input={"messages": dump_messages(messages)},
                    config=config,
                )

            # Check if the graph was interrupted during this invocation
            state = await self._graph.aget_state(config)
            if state.next:
                interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
                logger.info("graph_interrupted", session_id=session_id, interrupt_value=str(interrupt_value))
                return [Message(role="assistant", content=str(interrupt_value))]

            return self.__process_messages(response["messages"])
        except GraphInterrupt:
            state = await self._graph.aget_state(config)
            interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
            logger.info("graph_interrupted", session_id=session_id, interrupt_value=str(interrupt_value))
            return [Message(role="assistant", content=str(interrupt_value))]
        except Exception as e:
            logger.exception("get_response_failed", error=str(e), session_id=session_id)
            raise

    async def get_stream_response(
        self,
        messages: list[Message],
        session_id: str,
        workspace_id: int,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Get a stream response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.
            username (Optional[str]): The display name of the user.

        Yields:
            str: Tokens of the LLM response.
        """
        callbacks = [langfuse_callback_handler] if settings.LANGFUSE_TRACING_ENABLED else []
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": callbacks,
            "metadata": {
                "user_id": user_id,
                "username": username,
                "session_id": session_id,
                "workspace_id": workspace_id,
                "environment": settings.ENVIRONMENT.value,
                "debug": settings.DEBUG,
            },
        }
        if self._graph is None:
            self._graph = await self.create_graph()

        try:
            state = await self._graph.aget_state(config)

            if state.next:
                logger.info("resuming_interrupted_graph_stream", session_id=session_id, next_nodes=state.next)
                graph_input = Command(resume=messages[-1].content)
            else:
                graph_input = {"messages": dump_messages(messages)}

            async for token, metadata in self._graph.astream(
                graph_input,
                config,
                stream_mode="messages",
            ):
                if not isinstance(token, (AIMessage, AIMessageChunk)):
                    continue

                # Avoid leaking internal classifier/tool-model emissions to clients.
                node_name = None
                if isinstance(metadata, dict):
                    node_name = metadata.get("langgraph_node") or metadata.get("node")
                if node_name and node_name not in {"chat", "reject", "clarify_query", "safe_fallback"}:
                    continue

                text = extract_text_content(token.content)
                if text:
                    yield text

            # After streaming completes, check for interrupt
            state = await self._graph.aget_state(config)
            if state.next:
                interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
                logger.info("graph_interrupted_stream", session_id=session_id, interrupt_value=str(interrupt_value))
                yield str(interrupt_value)
        except GraphInterrupt:
            state = await self._graph.aget_state(config)
            interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
            logger.info("graph_interrupted_stream", session_id=session_id, interrupt_value=str(interrupt_value))
            yield str(interrupt_value)
        except Exception as stream_error:
            logger.exception("stream_processing_failed", error=str(stream_error), session_id=session_id)
            raise stream_error

    async def get_chat_history(self, session_id: str) -> list[Message]:
        """Get the chat history for a given thread ID.

        Args:
            session_id (str): The session ID for the conversation.

        Returns:
            list[Message]: The chat history.
        """
        if self._graph is None:
            self._graph = await self.create_graph()

        state: StateSnapshot = await self._graph.aget_state(config={"configurable": {"thread_id": session_id}})
        return self.__process_messages(state.values["messages"]) if state.values else []

    def __process_messages(self, messages: list[BaseMessage]) -> list[Message]:
        openai_style_messages = convert_to_openai_messages(messages)
        # keep just assistant and user messages
        return [
            Message(role=message["role"], content=str(message["content"]))
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]

    async def clear_chat_history(self, session_id: str) -> None:
        """Clear all chat history for a given thread ID.

        Args:
            session_id: The ID of the session to clear history for.

        Raises:
            Exception: If there's an error clearing the chat history.
        """
        try:
            # Make sure the pool is initialized in the current event loop
            conn_pool = await self._get_connection_pool()

            # Batch all DELETEs in a single pipeline round-trip
            async with conn_pool.connection() as conn:
                async with conn.pipeline():
                    for table in settings.CHECKPOINT_TABLES:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                logger.info(
                    "checkpoint_tables_cleared_for_session",
                    tables=settings.CHECKPOINT_TABLES,
                    session_id=session_id,
                )

        except Exception as e:
            logger.error(
                "clear_chat_history_operation_failed",
                session_id=session_id,
                error=str(e),
            )
            raise
