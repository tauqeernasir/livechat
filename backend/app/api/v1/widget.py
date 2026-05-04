"""Widget public API endpoints for embeddable chat widget.

These endpoints are called by the widget embed script from third-party websites.
Authentication uses widget keys (for config/session creation) and widget session
JWTs (for chat).
"""

import json
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select

from app.core.cache import cache_service
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.lead import Lead
from app.models.session import Session
from app.models.widget_config import WidgetConfig
from app.schemas.chat import ChatRequest, Message, StreamResponse
from app.schemas.widget import (
    LeadCreateRequest,
    WidgetConfigPublicResponse,
    WidgetMessageResponse,
    WidgetSessionResponse,
)
from app.services.database import database_service
from app.utils.auth import create_access_token, verify_token
from app.utils.sanitization import sanitize_string

router = APIRouter()
security = HTTPBearer()
agent = LangGraphAgent()

WIDGET_SESSION_EXPIRY_HOURS = 4
WIDGET_KEY_CACHE_TTL = 60  # seconds


async def get_widget_config(
    x_widget_key: str = Header(..., alias="X-Widget-Key"),
    request: Request = None,
) -> WidgetConfig:
    """Validate widget key and return the associated WidgetConfig.

    Checks cache first, then DB. Validates is_active and optionally
    checks Origin header against allowed_origins.

    Args:
        x_widget_key: The publishable widget key from the request header.
        request: The FastAPI request (for Origin header check).

    Returns:
        WidgetConfig: The validated widget configuration.

    Raises:
        HTTPException: If the key is invalid, inactive, or origin is not allowed.
    """
    cache_key = f"widget_config:{x_widget_key}"

    # Try cache first
    cached = await cache_service.get(cache_key)
    if cached:
        import json as _json

        data = _json.loads(cached)
        config = WidgetConfig.model_validate(data)
    else:
        # Look up in DB
        async with database_service.async_session_maker() as session:
            stmt = select(WidgetConfig).where(WidgetConfig.widget_key == x_widget_key)
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()

        if config is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid widget key",
            )

        # Cache for future lookups
        await cache_service.set(
            cache_key,
            config.model_dump_json(),
            ttl=WIDGET_KEY_CACHE_TTL,
        )

    if not config.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Widget is disabled",
        )

    # Check origin restrictions if configured
    if config.allowed_origins and request:
        origin = request.headers.get("origin")
        if origin and origin not in config.allowed_origins:
            logger.warning(
                "widget_origin_rejected",
                origin=origin,
                widget_key=x_widget_key,
                allowed=config.allowed_origins,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin not allowed",
            )

    return config


async def get_widget_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """Validate a widget session JWT and return the Session.

    Verifies:
    1. The JWT type is 'widget_session'.
    2. The session exists and has source='widget'.
    3. The workspace_id in the JWT matches the session record.

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        Session: The validated widget session.

    Raises:
        HTTPException: If the token is invalid or session validation fails.
    """
    try:
        token = sanitize_string(credentials.credentials)
        payload = verify_token(token)

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid widget session token",
            )

        token_type = payload.get("type")
        if token_type != "widget_session":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for widget endpoint",
            )

        session_id = payload.get("sub")
        workspace_id = payload.get("workspace_id")

        # Load the session record
        session = await database_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Widget session not found",
            )

        # Verify isolation constraints
        if session.source != "widget":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session is not a widget session",
            )

        if workspace_id and session.workspace_id != int(workspace_id):
            logger.warning(
                "widget_session_workspace_mismatch",
                session_id=session_id,
                jwt_workspace=workspace_id,
                session_workspace=session.workspace_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session workspace mismatch",
            )

        return session

    except (ValueError, TypeError) as e:
        logger.exception("widget_session_auth_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Widget authentication failed",
        )


# ── Public Widget Endpoints ──────────────────────────────────────────────


@router.get("/config", response_model=WidgetConfigPublicResponse)
@limiter.limit("30/minute")
async def get_public_widget_config(
    request: Request,
    key: str = Query(..., description="Widget key"),
):
    """Fetch public widget configuration for the embed script.

    No auth required — the widget key identifies the workspace.
    Returns visual settings and lead capture config.
    """
    async with database_service.async_session_maker() as session:
        stmt = select(WidgetConfig).where(WidgetConfig.widget_key == key)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

    if config is None or not config.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or inactive",
        )

    return WidgetConfigPublicResponse(
        position=config.position,
        primary_color=config.primary_color,
        welcome_message=config.welcome_message,
        placeholder_text=config.placeholder_text,
        icon_url=config.icon_url,
        lead_capture_enabled=config.lead_capture_enabled,
        lead_capture_fields=config.lead_capture_fields,
    )


@router.post("/session", response_model=WidgetSessionResponse)
@limiter.limit("10/minute")
async def create_widget_session(
    request: Request,
    widget_config: WidgetConfig = Depends(get_widget_config),
):
    """Create an anonymous widget session.

    Creates a session with no user_id, scoped to the widget's workspace.
    Returns a short-lived JWT for subsequent chat requests.
    """
    session_id = str(uuid.uuid4())

    # Create anonymous session in DB
    async with database_service.async_session_maker() as db_session:
        chat_session = Session(
            id=session_id,
            user_id=None,
            workspace_id=widget_config.workspace_id,
            name="",
            source="widget",
        )
        db_session.add(chat_session)
        await db_session.commit()

    # Create a widget-specific JWT with workspace_id in claims
    token = create_access_token(
        subject=session_id,
        token_type="widget_session",
        expires_delta=timedelta(hours=WIDGET_SESSION_EXPIRY_HOURS),
        extra_claims={"workspace_id": widget_config.workspace_id},
    )

    logger.info(
        "widget_session_created",
        session_id=session_id,
        workspace_id=widget_config.workspace_id,
    )

    return WidgetSessionResponse(
        session_id=session_id,
        access_token=token.access_token,
        expires_at=token.expires_at,
    )


@router.post("/chat/stream")
@limiter.limit("15/minute")
async def widget_chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_widget_session),
):
    """Stream a chat response for the widget.

    Uses the same LangGraph agent as the dashboard, but authenticated
    via widget session JWT instead of user token.
    """
    logger.info(
        "widget_stream_chat_received",
        session_id=session.id,
        workspace_id=session.workspace_id,
        message_count=len(chat_request.messages),
    )

    async def event_generator():
        try:
            async for chunk in agent.get_stream_response(
                chat_request.messages,
                session.id,
                workspace_id=session.workspace_id,
                user_id=None,
                username=None,
            ):
                response = StreamResponse(content=chunk, done=False)
                yield f"data: {json.dumps(response.model_dump(mode='json'))}\n\n"

            final_response = StreamResponse(content="", done=True)
            yield f"data: {json.dumps(final_response.model_dump(mode='json'))}\n\n"

        except Exception as e:
            logger.exception(
                "widget_stream_failed",
                session_id=session.id,
                error=str(e),
            )
            error_response = StreamResponse(content="An error occurred. Please try again.", done=True)
            yield f"data: {json.dumps(error_response.model_dump(mode='json'))}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/messages", response_model=list[WidgetMessageResponse])
@limiter.limit("30/minute")
async def get_widget_messages(
    request: Request,
    session: Session = Depends(get_widget_session),
):
    """Get chat history for a widget session.

    Returns messages from the LangGraph checkpointer for this session.
    """
    try:
        graph = await agent.create_graph()
        if graph is None:
            return []

        config = {"configurable": {"thread_id": session.id}}
        state = await graph.aget_state(config)

        if not state or not state.values:
            return []

        messages = state.values.get("messages", [])
        result = []
        for msg in messages:
            msg_type = getattr(msg, "type", None)
            content = getattr(msg, "content", "")

            if msg_type == "human":
                result.append(WidgetMessageResponse(role="user", content=str(content)))
            elif msg_type == "ai" and content:
                result.append(WidgetMessageResponse(role="assistant", content=str(content)))

        return result

    except Exception as e:
        logger.exception("widget_messages_failed", session_id=session.id, error=str(e))
        return []


@router.post("/lead", response_model=WidgetSessionResponse)
@limiter.limit("5/minute")
async def capture_lead(
    request: Request,
    lead_data: LeadCreateRequest,
    widget_config: WidgetConfig = Depends(get_widget_config),
):
    """Capture a lead and create a widget session.

    When lead capture is enabled, this replaces the anonymous session
    creation flow. The lead is stored and a session is returned.
    """
    session_id = str(uuid.uuid4())

    async with database_service.async_session_maker() as db_session:
        # Create the session first (lead has FK to session)
        chat_session = Session(
            id=session_id,
            user_id=None,
            workspace_id=widget_config.workspace_id,
            name="",
            source="widget",
        )
        db_session.add(chat_session)
        await db_session.flush()

        # Store the lead
        lead = Lead(
            workspace_id=widget_config.workspace_id,
            session_id=session_id,
            email=lead_data.email,
            name=lead_data.name,
            metadata_=lead_data.metadata,
        )
        db_session.add(lead)
        await db_session.commit()

    token = create_access_token(
        subject=session_id,
        token_type="widget_session",
        expires_delta=timedelta(hours=WIDGET_SESSION_EXPIRY_HOURS),
        extra_claims={"workspace_id": widget_config.workspace_id},
    )

    logger.info(
        "widget_lead_captured",
        workspace_id=widget_config.workspace_id,
        session_id=session_id,
        email=lead_data.email,
    )

    return WidgetSessionResponse(
        session_id=session_id,
        access_token=token.access_token,
        expires_at=token.expires_at,
    )
