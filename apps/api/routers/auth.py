"""Authentication utilities for FastAPI routes."""

from typing import Optional

from fastapi import Header, HTTPException

from utils.logging import get_logger

logger = get_logger(__name__)


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> str:
    """Extract user ID from Authorization header.

    For MVP, this accepts a simple Bearer token format where the token
    is the user ID or email. In production, this should validate JWT tokens
    from NextAuth.

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        User ID string, or "anonymous" if no auth provided
    """
    if not authorization:
        return "anonymous"

    try:
        # Expected format: "Bearer <user_id_or_email>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Invalid authorization header format")
            return "anonymous"

        token = parts[1]

        # For MVP: token is the user email/id directly
        # TODO: Implement proper JWT validation with NextAuth secret
        # from config import get_settings
        # import jwt
        # settings = get_settings()
        # decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        # return decoded.get("sub", "anonymous")

        # For now, use the token as the user identifier
        if "@" in token:
            # It's an email, use the part before @
            return token.split("@")[0]
        return token

    except Exception as e:
        logger.warning(f"Auth extraction failed: {e}")
        return "anonymous"


async def require_auth(
    authorization: Optional[str] = Header(None),
) -> str:
    """Require authentication - raises 401 if not authenticated.

    Use this dependency when authentication is required.
    """
    user_id = await get_current_user_id(authorization)
    if user_id == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
