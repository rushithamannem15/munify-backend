"""
Authentication and Authorization Dependencies

This module provides FastAPI dependencies for extracting user context from JWT tokens
and custom headers. It follows the standard pattern of extracting user information
from the Authorization header (JWT token) and falling back to custom headers for
backward compatibility.
"""
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status, Header
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger("core.auth")


class CurrentUser(BaseModel):
    """Current authenticated user model"""
    user_id: str
    username: Optional[str] = None
    organization_id: Optional[str] = None
    email: Optional[str] = None
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


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user_id_header: Optional[str] = Header(None, alias="user_id"),
    organization_id_header: Optional[str] = Header(None, alias="organization_id"),
    org_type_header: Optional[str] = Header(None, alias="org_type"),
) -> CurrentUser:
    """
    FastAPI dependency to extract current user from JWT token or headers.
    
    Priority:
    1. Extract user from JWT token in Authorization header (preferred)
    2. Fall back to custom headers (user_id, organization_id) for backward compatibility
    
    Usage:
        @router.post("/questions")
        def create_question(
            question_data: QuestionCreate,
            current_user: CurrentUser = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            # Use current_user.user_id, current_user.organization_id, etc.
            pass
    
    Args:
        authorization: Authorization header with JWT token
        user_id_header: Custom user_id header (fallback)
        organization_id_header: Custom organization_id header (fallback)
        
    Returns:
        CurrentUser object with user information
        
    Raises:
        HTTPException: If no user information can be extracted
    """
    # Try to extract from JWT token first
    token = extract_jwt_token(authorization)
    
    if token:
        decoded = decode_jwt_token(token)
        if decoded:
            # Extract user info from JWT payload
            # JWT payload structure from your example:
            # {"iss": "nagpur20", "id": "768a11d6-574c-41fe-9168-d6ec5fdb3a9b", "source": "legacyPerdix", ...}
            user_id = decoded.get("iss")
            username = decoded.get("iss")
            org_id = str(organization_id_header)
            org_type = str(org_type_header)
            
            if user_id:
                logger.debug(f"User extracted from JWT: user_id={user_id}, username={username}")
                return CurrentUser(
                    user_id=username,
                    username=username,
                    organization_id=str(org_id) if org_id else None,
                    source="jwt"
                )
    
    # Fallback to custom headers for backward compatibility
    if user_id_header:
        logger.debug(f"User extracted from header: user_id={user_id_header}")
        return CurrentUser(
            user_id=user_id_header,
            username=user_id_header,
            organization_id=str(organization_id_header) if organization_id_header else None,
            source="header"
        )
    
    # If neither JWT nor headers provide user info, raise error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide Authorization header with JWT token or user_id header."
    )


def get_current_user_optional(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user_id_header: Optional[str] = Header(None, alias="user_id"),
    organization_id_header: Optional[str] = Header(None, alias="organization_id"),
) -> Optional[CurrentUser]:
    """
    Optional version of get_current_user that returns None instead of raising error.
    
    Use this for endpoints where authentication is optional.
    
    Usage:
        @router.get("/public-data")
        def get_public_data(
            current_user: Optional[CurrentUser] = Depends(get_current_user_optional)
        ):
            if current_user:
                # User is authenticated
                pass
            else:
                # Anonymous access
                pass
    """
    try:
        return get_current_user(authorization, user_id_header, organization_id_header)
    except HTTPException:
        return None

