"""JWT token validation middleware."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """Authentication configuration."""

    jwt_secret: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: int | None = None


security = HTTPBearer()
_settings: AuthSettings | None = None


def get_auth_settings() -> AuthSettings:
    """Get auth settings singleton."""
    global _settings
    if _settings is None:
        _settings = AuthSettings()
    return _settings


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UUID:
    """Extract and validate user ID from JWT token."""
    settings = get_auth_settings()

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        return UUID(user_id)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


def validate_ws_token(token: str) -> UUID | None:
    """Validate WebSocket token and return user ID."""
    settings = get_auth_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if user_id:
            return UUID(user_id)
    except JWTError:
        pass
    return None


# Type alias for dependency injection
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
