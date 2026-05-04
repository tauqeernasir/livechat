"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
and token verification.
"""

import uuid
from typing import (
    List,
    Optional,
)

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Header,
    Request,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import (
    bind_context,
    logger,
)
from app.models import Workspace
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.database import DatabaseService, database_service
from app.utils.auth import (
    create_access_token,
    verify_token,
)
from app.utils.sanitization import (
    sanitize_email,
    sanitize_string,
    validate_password_strength,
)

router = APIRouter()
security = HTTPBearer()
db_service = DatabaseService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get the current user from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        User: The user extracted from the token.

    Raises:
        HTTPException: If the token is invalid, missing, or has the wrong type.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        payload = verify_token(token)
        if payload is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        token_type = payload.get("type")

        # Verify token type
        if token_type != "user":
            logger.error("invalid_token_type", expected="user", actual=token_type)
            raise HTTPException(
                status_code=401,
                detail="Invalid token type for this endpoint. Expected user token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user exists in database
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)
        if user is None:
            logger.error("user_not_found", user_id=user_id_int)
            raise HTTPException(
                status_code=401,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Bind user_id to logging context for all subsequent logs in this request
        bind_context(user_id=user_id_int)

        return user
    except ValueError as ve:
        logger.exception("token_validation_failed", error=str(ve))
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
) -> Session:
    """Get the current session from the token.

    Supports two modes:
    1. Direct Session Token: Token where 'sub' is the session_id and 'type' is 'session'.
    2. User Token + Header: Token where 'type' is 'user' and 'X-Session-Id' header is provided.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.
        x_session_id: Optional session ID provided in the header.

    Returns:
        Session: The session extracted or matched.

    Raises:
        HTTPException: If the token is invalid, missing, or unauthorized.
    """
    try:
        token = sanitize_string(credentials.credentials)
        payload = verify_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        token_type = payload.get("type")
        
        # Mode 1: Direct Session Token
        if token_type == "session":
            session_id = sanitize_string(payload.get("sub"))
            session = await db_service.get_session(session_id)
            if session is None:
                raise HTTPException(status_code=401, detail="Session not found")
            bind_context(user_id=session.user_id)
            return session

        # Mode 2: User Token + X-Session-Id Header
        if token_type == "user" and x_session_id:
            user_id = int(payload.get("sub"))
            session_id = sanitize_string(x_session_id)
            session = await db_service.get_session(session_id)
            
            if session is None:
                raise HTTPException(status_code=401, detail="Session not found")
                
            if session.user_id != user_id:
                logger.warning("unauthorized_session_access", user_id=user_id, session_id=session_id)
                raise HTTPException(status_code=403, detail="Unauthorized access to this session")
                
            bind_context(user_id=user_id)
            return session

        # Fallback error
        if token_type == "user" and not x_session_id:
            raise HTTPException(status_code=401, detail="Session ID header required for user tokens")
            
        raise HTTPException(status_code=401, detail="Invalid token type or missing session context")

    except (ValueError, TypeError) as e:
        logger.exception("session_auth_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed")
    except ValueError as ve:
        logger.exception("token_validation_failed", error=str(ve))
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user.

    Args:
        request: The FastAPI request object for rate limiting.
        user_data: User registration data

    Returns:
        UserResponse: The created user info
    """
    try:
        # Sanitize email
        sanitized_email = sanitize_email(user_data.email)

        # Extract and validate password
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        # Check if user exists
        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Sanitize optional username
        sanitized_username = sanitize_string(user_data.username) if user_data.username else None

        # Create user
        user = await db_service.create_user(
            email=sanitized_email,
            password=User.hash_password(password),
            username=sanitized_username,
        )

        # Create access token
        token = create_access_token(str(user.id), token_type="user")

        return UserResponse(id=user.id, email=user.email, username=user.username, token=token)
    except ValueError as ve:
        logger.exception("user_registration_validation_failed", error=str(ve))
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(
    request: Request, email: str = Form(...), password: str = Form(...), grant_type: str = Form(default="password")
):
    """Login a user.

    Args:
        request: The FastAPI request object for rate limiting.
        email: User's email
        password: User's password
        grant_type: Must be "password"

    Returns:
        TokenResponse: Access token information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Sanitize inputs
        email = sanitize_string(email)
        password = sanitize_string(password)
        grant_type = sanitize_string(grant_type)

        # Verify grant type
        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="Unsupported grant type. Must be 'password'",
            )

        user = await db_service.get_user_by_email(email)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(str(user.id), token_type="user")
        return TokenResponse(access_token=token.access_token, token_type="bearer", expires_at=token.expires_at)
    except ValueError as ve:
        logger.exception("login_validation_failed", error=str(ve))
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Get the current authenticated user's information.

    Args:
        user: The authenticated user from the token.
        session: Database session.

    Returns:
        UserResponse: The user's profile information.
    """
    logger.info("get_me_called", user_id=user.id)
    
    workspace_id = None
    if user.organization_id:
        result = await session.execute(
            select(Workspace.id).where(Workspace.org_id == user.organization_id).limit(1)
        )
        workspace_row = result.first()
        if workspace_row:
            workspace_id = workspace_row[0]

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        onboarding_completed=user.onboarding_completed,
        organization_id=user.organization_id,
        workspace_id=workspace_id,
    )


@router.get("/workspaces", response_model=List[dict])
async def get_user_workspaces(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(database_service.get_async_session),
):
    """Get all workspaces for the current user's organization.

    Args:
        user: The authenticated user.
        session: Database session.

    Returns:
        List[dict]: List of workspace objects (id and name).
    """
    if not user.organization_id:
        return []

    result = await session.execute(
        select(Workspace).where(Workspace.org_id == user.organization_id)
    )
    workspaces = result.scalars().all()
    
    return [
        {"id": ws.id, "name": ws.name}
        for ws in workspaces
    ]


@router.post("/session", response_model=SessionResponse)
async def create_session(
    user: User = Depends(get_current_user), session_db: AsyncSession = Depends(database_service.get_async_session)
):
    """Create a new chat session for the authenticated user.

    Args:
        user: The authenticated user
        session_db: Database session

    Returns:
        SessionResponse: The session ID, name, and access token
    """
    try:
        # Resolve workspace_id from user's organization
        workspace_id = None
        if user.organization_id:
            result = await session_db.execute(
                select(Workspace.id).where(Workspace.org_id == user.organization_id).limit(1)
            )
            workspace_row = result.first()
            if workspace_row:
                workspace_id = workspace_row[0]

        if not workspace_id:
            logger.error("workspace_not_found_for_session", user_id=user.id)
            raise HTTPException(status_code=400, detail="User must belong to an organization with a workspace")

        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create session in database, copying username for LLM personalization
        session = await db_service.create_session(
            session_id, user.id, workspace_id=workspace_id, username=user.username
        )

        # Create access token for the session
        token = create_access_token(session_id, token_type="session")

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            workspace_id=workspace_id,
            name=session.name,
            expires_at=token.expires_at.isoformat(),
        )

        return SessionResponse(session_id=session_id, name=session.name, token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("session_creation_failed", error=str(e), user_id=user.id)
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.patch("/session/{session_id}/name", response_model=SessionResponse)
async def update_session_name(
    session_id: str, name: str = Form(...), current_session: Session = Depends(get_current_session)
):
    """Update a session's name.

    Args:
        session_id: The ID of the session to update
        name: The new name for the session
        current_session: The current session from auth

    Returns:
        SessionResponse: The updated session information
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        # Update the session name
        session = await db_service.update_session_name(sanitized_session_id, sanitized_name)

        # Create a new token (not strictly necessary but maintains consistency)
        token = create_access_token(sanitized_session_id, token_type="session")

        return SessionResponse(session_id=sanitized_session_id, name=session.name, token=token)
    except ValueError as ve:
        logger.exception("session_update_validation_failed", error=str(ve), session_id=session_id)
        raise HTTPException(status_code=422, detail=str(ve))


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, current_session: Session = Depends(get_current_session)):
    """Delete a session for the authenticated user.

    Args:
        session_id: The ID of the session to delete
        current_session: The current session from auth

    Returns:
        None
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        # Delete the session
        await db_service.delete_session(sanitized_session_id)

        logger.info("session_deleted", session_id=session_id, user_id=current_session.user_id)
    except ValueError as ve:
        logger.exception("session_deletion_validation_failed", error=str(ve), session_id=session_id)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(user: User = Depends(get_current_user)):
    """Get all session IDs for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        List[SessionResponse]: List of session IDs
    """
    try:
        sessions = await db_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
                token=create_access_token(session.id, token_type="session"),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.exception("get_sessions_validation_failed", user_id=user.id, error=str(ve))
        raise HTTPException(status_code=422, detail=str(ve))
