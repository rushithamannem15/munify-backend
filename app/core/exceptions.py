from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.logging import get_logger

logger = get_logger("exceptions")


def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    # Handle Perdix error response format (dict with errorId and error)
    if isinstance(exc.detail, dict):
        # Return Perdix error response as-is
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                **exc.detail  # Spread the Perdix error response (errorId, error, etc.)
            },
        )
    elif isinstance(exc.detail, str):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.detail,
            },
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": str(exc.detail),
            },
        )


def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": exc.errors(),
        },
    )


def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "errors": str(exc.detail.error),
        },
    )


def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity violations like unique constraint errors."""
    error_msg = str(getattr(exc, "orig", exc))
    logger.error(f"Integrity Error: {error_msg}")
    if "Duplicate entry" in error_msg or "UNIQUE" in error_msg or "unique" in error_msg:
        return JSONResponse(
            status_code=409,
            content={
                "status": "error",
                "message": "Duplicate value violates a unique constraint.",
                "errors": error_msg,
            },
        )
    return JSONResponse(
        status_code=409,
        content={
            "status": "error",
            "message": "Data integrity violation.",
            "errors": error_msg
        },
    )


def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Catch-all for other SQLAlchemy errors."""
    logger.error(f"SQLAlchemy Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Database error occurred.",
            "errors": str(exc),
        },
    )


