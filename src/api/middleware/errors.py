"""Error handling and logging middleware."""

import logging
import sys
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class LogSettings(BaseSettings):
    """Logging configuration."""

    log_level: str = "INFO"

    class Config:
        env_file = ".env"


class ErrorResponse(BaseModel):
    """Standard error response."""

    code: str
    message: str


def setup_logging() -> logging.Logger:
    """Configure application logging."""
    settings = LogSettings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("chat")
    return logger


logger = setup_logging()


class ChatException(Exception):
    """Base exception for chat application."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(ChatException):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code="not_found",
            message=f"{resource} with id {resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class RateLimitError(ChatException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(
            code="rate_limited",
            message="Rate limit exceeded. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class UnauthorizedError(ChatException):
    """User not authorized."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            code="unauthorized",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the app."""

    @app.exception_handler(ChatException)
    async def chat_exception_handler(request: Request, exc: ChatException):
        logger.warning(f"ChatException: {exc.code} - {exc.message}")
        response = JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code=exc.code, message=exc.message).model_dump(),
        )
        if isinstance(exc, RateLimitError):
            response.headers["Retry-After"] = str(exc.retry_after)
        return response

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                code="internal_error",
                message="An unexpected error occurred",
            ).model_dump(),
        )
