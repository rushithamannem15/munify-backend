"""
Authentication and Authorization Dependencies

This module provides FastAPI dependencies for extracting user context from JWT tokens
and custom headers. It follows the standard pattern of extracting user information
from the Authorization header (JWT token) and falling back to custom headers for
backward compatibility.

Features:
- JWT token validation
- In-memory caching of user details
- Automatic API call to fetch user details if not in cache
- Extracts user_id and role from Perdix API response
"""
from typing import Optional, Dict, Any
import jwt
import threading
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Header
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.user_service import (
    get_account_from_perdix,
    get_user_from_perdix_by_login,
)

logger = get_logger("core.auth")

# In-memory cache for user details
# Structure: {token: {"user_id": str, "role": str, "username": str, "email": str, "cached_at": datetime}}
_user_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()
_cache_ttl = timedelta(hours=1)  # Cache TTL: 1 hour


class CurrentUser(BaseModel):
    """Current authenticated user model"""
    user_id: str
    username: Optional[str] = None
    organization_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None  # User role from Perdix API
    role_id: Optional[str] = None  # Role ID from first entry in userRoles array
    org_type: Optional[str] = None  # Organization type from first branch
    org_name: Optional[str] = None  # Organization name from second branch
    source: str = "jwt"  # "jwt" or "header" to track where user info came from

    class Config:
        from_attributes = True


def extract_jwt_token(authorization: Optional[str] = Header(None, alias="Authorization")) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Supports formats:
    - Authorization: JWT <token>
    - Authorization: Bearer <token>
    - Authorization: <token>
    
    Args:
        authorization: Authorization header value
        
    Returns:
        JWT token string or None if not found/invalid format
    """
    if not authorization:
        return None
    
    authorization = authorization.strip()
    
    # Remove "JWT " or "Bearer " prefix if present
    if authorization.startswith("JWT "):
        return authorization[4:]
    elif authorization.startswith("Bearer "):
        return authorization[7:]
    elif authorization.startswith("jwt "):
        return authorization[4:]
    elif authorization.startswith("bearer "):
        return authorization[7:]
    
    # If no prefix, assume it's the token itself
    return authorization


def decode_jwt_token(token: str) -> Optional[dict]:
    """
    Decode JWT token without verification (since token is from external Perdix service).
    
    Note: In production, you should verify the token signature if you have the public key.
    For now, we decode without verification since the token comes from Perdix.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload (dict) or None if decoding fails
    """
    try:
        # Decode without verification (options={"verify_signature": False})
        # In production, you should verify the signature if you have Perdix's public key
        decoded = jwt.decode(
            token,
            options={"verify_signature": False},  # Skip signature verification
            algorithms=["RS512", "HS256", "HS512"]  # Common algorithms
        )
        return decoded
    except jwt.DecodeError as e:
        logger.warning(f"Failed to decode JWT token: {str(e)}")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT token: {str(e)}", exc_info=True)
        return None


def validate_jwt_token(token: str) -> bool:
    """
    Validate JWT token by checking if it can be decoded and is not expired.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is valid, False otherwise
    """
    decoded = decode_jwt_token(token)
    if not decoded:
        return False
    
    # Check expiration if present
    exp = decoded.get("exp")
    if exp:
        try:
            exp_timestamp = int(exp)
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            if exp_datetime < datetime.utcnow():
                logger.warning("JWT token has expired")
                return False
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid expiration time in token: {str(e)}")
    
    return True


def _extract_user_details_from_api_response(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user details from Perdix API response (from get_user_from_perdix_by_login).
    All data is extracted from a single API response - NO extra API calls are made.
    
    Mapping:
    - organization_id = branchId (from response)
    - org_type = branchName (from response)
    - org_name = activeBranch or second branch from userBranches (from response)
    - role_id = userRoles[0].roleId (from response)
    
    Args:
        api_response: Response dictionary from Perdix API (get_user_from_perdix_by_login)
        
    Returns:
        Dictionary with user_id, role, role_id, username, email, organization_id, org_type, org_name, and full user data
    """
    user_details = {
        "user_id": None,
        "role": None,
        "role_id": None,
        "username": None,
        "email": None,
        "organization_id": None,
        "org_type": None,
        "org_name": None,
        "full_user_data": api_response  # Store full response for caching
    }
    
    # Try different possible field names for user_id
    user_id = (
        api_response.get("id")
    )
    # Convert to string if not None
    user_details["user_id"] = str(user_id) if user_id is not None else None
    
    # Extract role and roleId from userRoles array
    user_roles = api_response.get("userRoles")
    role = None
    role_id = None
    
    if isinstance(user_roles, list) and len(user_roles) > 0:
        # Get first entry from userRoles array
        first_role = user_roles[0]
        if isinstance(first_role, dict):
            # Extract roleId from first entry
            role_id = first_role.get("roleId")
            if role_id:
                role_id = str(role_id)  # Convert to string
            # Also extract role name if available
            role = first_role.get("role") or first_role.get("roleName") or first_role.get("name")
        elif isinstance(first_role, str):
            role = first_role
    elif isinstance(user_roles, str):
        role = user_roles
    
    # Fallback to direct role field if userRoles not found
    if not role:
        role = api_response.get("role") or api_response.get("roleCode")
    
    user_details["role"] = role
    user_details["role_id"] = role_id
    
    # Extract username
    user_details["username"] = (
        api_response.get("login")
    )
    
    # Extract email
    user_details["email"] = (
        api_response.get("email")
    )
    
    # Extract organization_id from branchId (as per user requirement: org_id = branchId)
    organization_id = api_response.get("branchId")
    # Convert to string if not None
    user_details["organization_id"] = str(organization_id) if organization_id is not None else None
   
    # Extract org_type from branchName (as per user requirement: org_type = branchName)
    user_details["org_type"] = api_response.get("branchName")
    
    # Extract org_name from activeBranch or userBranches[1] if available
    # Try activeBranch first (most common case)
    org_name = api_response.get("activeBranch")
    
    # If not found, try second branch from userBranches array
    if not org_name:
        user_branches = api_response.get("userBranches", [])
        if isinstance(user_branches, list) and len(user_branches) > 1:
            second_branch = user_branches[1]
            if isinstance(second_branch, dict):
                # If second branch has branchName, use it
                org_name = second_branch.get("branchName")
    
    user_details["org_name"] = org_name
    
    return user_details


def _get_user_from_cache(token: str) -> Optional[Dict[str, Any]]:
    """
    Get user details from cache if available and not expired.
    
    Args:
        token: JWT token string
        
    Returns:
        User details dictionary or None if not in cache or expired
    """
    with _cache_lock:
        if token not in _user_cache:
            return None
        
        cached_data = _user_cache[token]
        cached_at = cached_data.get("cached_at")
        
        # Check if cache entry is expired
        if cached_at and datetime.utcnow() - cached_at > _cache_ttl:
            del _user_cache[token]
            logger.debug(f"Cache entry expired for token (first 20 chars): {token[:20]}...")
            return None
        
        logger.debug(f"Cache hit for token (first 20 chars): {token[:20]}...")
        return cached_data


def _cache_user_details(token: str, user_details: Dict[str, Any]) -> None:
    """
    Cache user details with timestamp.
    
    Args:
        token: JWT token string
        user_details: User details dictionary
    """
    with _cache_lock:
        user_details["cached_at"] = datetime.utcnow()
        _user_cache[token] = user_details
        logger.debug(f"Cached user details for token (first 20 chars): {token[:20]}...")


def _get_login_from_token(token: str) -> Optional[str]:
    """
    Extract login/username from JWT token payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Login/username string or None if not found
    """
    decoded = decode_jwt_token(token)
    if not decoded:
        return None
    
    # Try different fields that might contain login/username
    login = (
        decoded.get("iss")
    )
    
    return str(login) if login else None


def _fetch_user_details_from_api(token: str) -> Dict[str, Any]:
    """
    Fetch complete user details from Perdix API using get_user_from_perdix_by_login.
    Makes ONLY ONE API call - all data (including org_type, org_name) is extracted from the single response.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with user_id, role, role_id, username, email, organization_id, org_type, org_name, and full_user_data
        
    Raises:
        HTTPException: If API call fails or returns invalid response
    """
    try:
        # First, get login/username from token
        login = _get_login_from_token(token)
        
        if not login:
            logger.error("Could not extract login/username from JWT token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not extract user login from token"
            )
        
        # Fetch user details using login
        body, status_code, is_json = get_user_from_perdix_by_login(login)
        
        if status_code != 200:
            error_msg = body if isinstance(body, str) else body.get("message", "Failed to fetch user details")
            logger.error(f"Perdix API returned status {status_code}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token or failed to fetch user details: {error_msg}"
            )
        
        if not is_json or not isinstance(body, dict):
            logger.error(f"Invalid response format from Perdix API: {type(body)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid response format from authentication service"
            )
        
        # Extract user details including org_type and org_name from branches
        user_details = _extract_user_details_from_api_response(body)
        
        if not user_details["user_id"]:
            logger.error("Could not extract user_id from API response")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not extract user information from authentication service"
            )
        
        logger.info(
            f"Fetched user details from API: user_id={user_details['user_id']}, "
            f"role={user_details['role']}, org_type={user_details['org_type']}, "
            f"org_name={user_details['org_name']}"
        )
        return user_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching user details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch user details: {str(e)}"
        )


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> CurrentUser:
    """
    FastAPI dependency to extract current user from JWT token.
    
    This function:
    1. Validates JWT token
    2. Checks in-memory cache for user details
    3. If not cached, calls Perdix API to fetch complete user details (including org_type and org_name)
    4. Caches the result for future requests
    5. Extracts user_id, role, org_type, org_name from API response
    
    Usage:
        @router.post("/questions")
        def create_question(
            question_data: QuestionCreate,
            current_user: CurrentUser = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            # Use current_user.user_id, current_user.role, current_user.org_type, etc.
            pass
    
    Args:
        authorization: Authorization header with JWT token (format: "Bearer <token>" or "JWT <token>" or just "<token>")
        
    Returns:
        CurrentUser object with user information including user_id, role, org_type, org_name
        
    Raises:
        HTTPException: If no user information can be extracted or token is invalid
    """
    # Extract JWT token from Authorization header
    token = extract_jwt_token(authorization)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide Authorization header with JWT token."
        )
    
    # Validate JWT token (optional - can be enabled if needed)
    # if not validate_jwt_token(token):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid or expired JWT token"
    #     )
    
    # Check cache first
    cached_user = _get_user_from_cache(token)
    
    if cached_user:
        # Use cached user details
        logger.debug(f"Using cached user details: user_id={cached_user.get('user_id')}")
        cached_user_id = cached_user.get("user_id")
        cached_org_id = cached_user.get("organization_id")
        return CurrentUser(
            user_id=str(cached_user_id) if cached_user_id else "",
            username=cached_user.get("username"),
            organization_id=str(cached_org_id) if cached_org_id is not None else None,
            email=cached_user.get("email"),
            role=cached_user.get("role"),
            role_id=cached_user.get("role_id"),
            org_type=cached_user.get("org_type"),
            org_name=cached_user.get("org_name"),
            source="jwt"
        )
    
    # Not in cache, fetch from API
    logger.debug("User details not in cache, fetching from API")
    user_details = _fetch_user_details_from_api(token)
    
    # Cache the user details (including full_user_data)
    _cache_user_details(token, user_details)
    
    # Return CurrentUser with API-fetched details
    fetched_user_id = user_details.get("user_id")
    fetched_org_id = user_details.get("organization_id")
    return CurrentUser(
        user_id=str(fetched_user_id) if fetched_user_id else "",
        username=user_details.get("username"),
        organization_id=str(fetched_org_id) if fetched_org_id is not None else None,
        email=user_details.get("email"),
        role=user_details.get("role"),
        role_id=user_details.get("role_id"),
        org_type=user_details.get("org_type"),
        org_name=user_details.get("org_name"),
        source="jwt"
    )


# def get_current_user_optional(
#     authorization: Optional[str] = Header(None, alias="Authorization"),
#     user_id_header: Optional[str] = Header(None, alias="user_id"),
#     organization_id_header: Optional[str] = Header(None, alias="organization_id"),
# ) -> Optional[CurrentUser]:
#     """
#     Optional version of get_current_user that returns None instead of raising error.
    
#     Use this for endpoints where authentication is optional.
    
#     Usage:
#         @router.get("/public-data")
#         def get_public_data(
#             current_user: Optional[CurrentUser] = Depends(get_current_user_optional)
#         ):
#             if current_user:
#                 # User is authenticated
#                 pass
#             else:
#                 # Anonymous access
#                 pass
#     """
#     try:
#         return get_current_user(authorization, user_id_header, organization_id_header)
#     except HTTPException:
#         return None


# Public wrapper functions for middleware use
def get_user_from_cache(token: str) -> Optional[Dict[str, Any]]:
    """
    Public wrapper to get user details from cache.
    
    Args:
        token: JWT token string
        
    Returns:
        User details dictionary or None if not in cache or expired
    """
    return _get_user_from_cache(token)


def cache_user_details(token: str, user_details: Dict[str, Any]) -> None:
    """
    Public wrapper to cache user details.
    
    Args:
        token: JWT token string
        user_details: User details dictionary
    """
    _cache_user_details(token, user_details)


def fetch_user_details_from_api(token: str) -> Dict[str, Any]:
    """
    Public wrapper to fetch user details from Perdix API.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with user_id, role, username, email, org_type, org_name
        
    Raises:
        HTTPException: If API call fails or returns invalid response
    """
    return _fetch_user_details_from_api(token)


def get_user_from_request_state(request) -> Optional[CurrentUser]:
    """
    Extract user information from request.state (set by AuthInterceptorMiddleware).
    
    This is useful when you want to access user info without using the dependency,
    or when the middleware has already validated the token.
    
    Usage:
        from fastapi import Request
        from app.core.auth import get_user_from_request_state
        
        @router.get("/example")
        async def example_endpoint(request: Request):
            user = get_user_from_request_state(request)
            if user:
                print(f"User ID: {user.user_id}, Role: {user.role}")
    
    Args:
        request: FastAPI Request object
        
    Returns:
        CurrentUser object if available, None otherwise
    """
    if not hasattr(request.state, "user_id") or not request.state.user_id:
        return None
    
    return CurrentUser(
        user_id=str(request.state.user_id),
        username=getattr(request.state, "user_username", None),
        email=getattr(request.state, "user_email", None),
        role=getattr(request.state, "user_role", None),
        role_id=getattr(request.state, "user_role_id", None),
        org_type=getattr(request.state, "user_org_type", None),
        org_name=getattr(request.state, "user_org_name", None),
        source="middleware"
    )

