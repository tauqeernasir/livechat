"""This file contains the authentication utilities for the application."""

import re
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Optional

from jose import (
    JWTError,
    jwt,
)

from app.core.config import settings
from app.core.logging import logger
from app.schemas.auth import Token
from app.utils.sanitization import sanitize_string


def create_access_token(
    subject: str, token_type: str = "session", expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> Token:
    """Create a new access token.

    Args:
        subject: The unique subject ID (user ID or session ID).
        token_type: The type of token ("user", "session", or "widget_session").
        expires_delta: Optional expiration time delta.
        extra_claims: Optional additional claims to embed in the JWT.

    Returns:
        Token: The generated access token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": sanitize_string(f"{subject}-{datetime.now(UTC).timestamp()}"),  # Add unique token identifier
    }

    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    logger.info("token_created", subject=subject, token_type=token_type, expires_at=expire.isoformat())

    return Token(access_token=encoded_jwt, expires_at=expire)


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload.

    Args:
        token: The JWT token to verify.

    Returns:
        Optional[dict]: The token payload (containing 'sub' and 'type') if token is valid, None otherwise.

    Raises:
        ValueError: If the token format is invalid
    """
    if not token or not isinstance(token, str):
        logger.warning("token_invalid_format")
        raise ValueError("Token must be a non-empty string")

    # Basic format validation before attempting decode
    # JWT tokens consist of 3 base64url-encoded segments separated by dots
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning("token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        subject: str = payload.get("sub")
        token_type: str = payload.get("type", "session")  # Default to session for backward compatibility

        if subject is None:
            logger.warning("token_missing_subject")
            return None

        logger.info("token_verified", subject=subject, token_type=token_type)
        return {"sub": subject, "type": token_type}

    except JWTError as e:
        logger.error("token_verification_failed", error=str(e))
        return None
