from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.auth_interceptor import AuthInterceptorMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.exceptions import (
    http_exception_handler,
    request_validation_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    unhandled_exception_handler,
)

# Import all models to ensure SQLAlchemy can resolve relationships
# This must happen before any database operations
import app.models  # noqa: F401

# Setup logging
setup_logging()
logger = get_logger("main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Munify Phase-1: Commitment-based municipal projects marketplace backend",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add middleware (order matters - first added is outermost)
# Auth interceptor should be early to validate tokens and add user headers
app.add_middleware(
    AuthInterceptorMiddleware,
    skip_paths=[
        # System endpoints
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/",  # Root landing page (exact match only - handled in should_skip_path)
        
        # Landing Page APIs
        "/api/v1/statistics/landing-page",
        
        # Login Page APIs
        "/api/v1/auth/login",
        
        # Register Page APIs
        "/api/v1/master/roles",
        "/api/v1/perdix/query",
        "/api/v1/invitations/validate",  # Matches /invitations/validate/{token}
        "/api/v1/users/register",
        
        # Forgot Password Page APIs
        "/api/v1/auth/forgot-password/otp",
        "/api/v1/auth/change-password/otp",
        
        # Account endpoint (used for token validation)
        "/api/v1/users/account",
    ],
    require_auth=False  # Set to True to require authentication on all endpoints
)
app.add_middleware(RequestLoggingMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Welcome to Munify API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
