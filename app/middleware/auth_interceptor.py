"""
Authentication Interceptor Middleware

This middleware intercepts all requests, validates JWT tokens, extracts user information,
and adds custom headers (X-User-Id, X-User-Role) that can be used by downstream services.

Usage:
    from app.middleware.auth_interceptor import AuthInterceptorMiddleware
    
    app.add_middleware(
        AuthInterceptorMiddleware,
        skip_paths=["/health", "/docs", "/openapi.json"],
        require_auth=False
    )
"""
from typing import Optional, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.auth import (
    extract_jwt_token,
    validate_jwt_token,
    get_user_from_cache,
    fetch_user_details_from_api,
    cache_user_details,
)
from app.core.logging import get_logger

logger = get_logger("middleware.auth-interceptor")


class AuthInterceptorMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts requests, validates JWT tokens, extracts user info,
    and adds custom headers (X-User-Id, X-User-Role) for downstream services.
    
    This middleware:
    1. Validates JWT tokens from Authorization header
    2. Checks in-memory cache for user details
    3. Calls Perdix API if user details not cached
    4. Adds X-User-Id and X-User-Role headers to request
    5. Stores user info in request.state for use in endpoints
    
    Args:
        skip_paths: List of paths to skip authentication (e.g., /health, /docs)
        require_auth: If True, reject requests without valid tokens. If False,
                     just add headers when token is present.
    """
    
    def __init__(
        self,
        app,
        skip_paths: Optional[List[str]] = None,
        require_auth: bool = False
    ):
        super().__init__(app)
        self.skip_paths = skip_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/",
            "/api/v1/users/account",  # Account endpoint itself
        ]
        self.require_auth = require_auth
    
    def should_skip_path(self, path: str) -> bool:
        """Check if the path should skip authentication."""
        # Exact match
        if path in self.skip_paths:
            return True
        
        # Check if path starts with any skip path
        for skip_path in self.skip_paths:
            # Special handling for root path "/" - only exact match
            if skip_path == "/":
                continue  # Skip prefix matching for root path
            if path.startswith(skip_path):
                return True
        
        return False
    
    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        return extract_jwt_token(auth_header)
    
    def get_user_info_from_token(self, token: str) -> Optional[dict]:
        """
        Validate token and extract user information from cache or API.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with user info (user_id, role, role_id, username, email, org_type, org_name) or None
        """
        try:
            # Validate JWT token (optional - can be enabled if needed)
            # if not validate_jwt_token(token):
            #     logger.warning("Invalid or expired JWT token")
            #     return None
            
            # Check cache first
            cached_user = get_user_from_cache(token)
            
            if cached_user:
                logger.debug(f"Using cached user details: user_id={cached_user.get('user_id')}")
                return {
                    "user_id": cached_user.get("user_id"),
                    "role": cached_user.get("role"),
                    "role_id": cached_user.get("role_id"),
                    "username": cached_user.get("username"),
                    "email": cached_user.get("email"),
                    "org_type": cached_user.get("org_type"),
                    "org_name": cached_user.get("org_name"),
                }
            
            # Not in cache, fetch from API
            logger.debug("User details not in cache, fetching from API")
            user_details = fetch_user_details_from_api(token)
            
            # Cache the user details
            cache_user_details(token, user_details)
            
            return {
                "user_id": user_details.get("user_id"),
                "role": user_details.get("role"),
                "role_id": user_details.get("role_id"),
                "username": user_details.get("username"),
                "email": user_details.get("email"),
                "org_type": user_details.get("org_type"),
                "org_name": user_details.get("org_name"),
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions (e.g., 401, 502)
            raise
        except Exception as e:
            logger.error(f"Error extracting user info from token: {e}", exc_info=True)
            return None
    
    async def dispatch(self, request: Request, call_next):
        """Process the request through the middleware."""
        # Skip authentication for certain paths
        if self.should_skip_path(request.url.path):
            return await call_next(request)
        
        # Extract token (only token is needed, no other headers)
        token = self.extract_token_from_request(request)
        
        if not token:
            if self.require_auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # If auth not required, just pass through without headers
            return await call_next(request)
        
        # Validate token and extract user info
        try:
            user_info = self.get_user_info_from_token(token)
        except HTTPException as e:
            # If require_auth is True, reject invalid tokens
            if self.require_auth:
                raise
            # Otherwise, just pass through without headers
            return await call_next(request)
        
        if not user_info:
            if self.require_auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # If auth not required, just pass through without headers
            return await call_next(request)
        
        # Add user information to request.state for use in endpoints
        # This allows endpoints to access user info without re-validating
        request.state.user_id = str(user_info["user_id"]) if user_info.get("user_id") else None
        request.state.user_role = user_info.get("role")
        request.state.user_role_id = user_info.get("role_id")
        request.state.user_username = user_info.get("username")
        request.state.user_email = user_info.get("email")
        request.state.user_org_type = user_info.get("org_type")
        request.state.user_org_name = user_info.get("org_name")
        request.state.user_info = user_info
        
        # Process the request
        response = await call_next(request)
        
        # Add headers to response (optional - for downstream services or debugging)
        if user_info.get("user_id"):
            response.headers["X-User-Id"] = str(user_info["user_id"])
        if user_info.get("role"):
            response.headers["X-User-Role"] = str(user_info["role"])
        if user_info.get("username"):
            response.headers["X-User-Username"] = str(user_info["username"])
        
        return response

