import httpx
from fastapi import HTTPException, status
from app.core.config import settings


def obtain_jwt_from_perdix(login_data: dict, skip_relogin: str = "yes") -> tuple:
    base = settings.PERDIX_ORIGIN.rstrip("/")
    url = f"{base}/gateway/jwt/token"
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/plain, */*",
        "origin": settings.PERDIX_ORIGIN,
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
    }
    payload = {"loginData": login_data, "skip_relogin": skip_relogin}
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def change_password_with_otp(otp: str, user_id: str, new_password: str, confirm_password: str) -> tuple:
    """Change password using OTP verification via Perdix.

    Returns (body, status_code, is_json)
    """
    base_url = settings.PERDIX_BASE_URL.rstrip("/")
    url = f"{base_url}/api/account/otpVerifiedForChangedPassword"

    if not settings.PERDIX_JWT:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Perdix JWT is not configured")

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "authorization": f"JWT {settings.PERDIX_JWT}",
        "origin": settings.PERDIX_ORIGIN,
        "x-auth-provider": "ssoProvider",
        "x-user-id": user_id,
    }

    payload = {
        "otp": otp,
        "userId": user_id,
        "newPassword": new_password,
        "confirmPassword": confirm_password,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def request_password_otp_from_perdix(user_id: str) -> tuple:
    """Request OTP for password change/forgot password via Perdix.

    Returns a tuple: (body, status_code, is_json)
    """
    base_url = settings.PERDIX_BASE_URL.rstrip("/")
    url = f"{base_url}/api/account/otpChangedPassword"

    if not settings.PERDIX_JWT:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Perdix JWT is not configured")

    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"JWT {settings.PERDIX_JWT}",
        "origin": settings.PERDIX_ORIGIN,
        # Some Perdix endpoints expect these hints; include minimally
        "x-auth-provider": "ssoProvider",
        "x-user-id": user_id,
    }

    params = {"userId": user_id}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def validate_user_with_perdix(access_token: str, _unused=None) -> tuple:
    # Placeholder: implement with the actual Perdix validation endpoint used by your frontend
    base = settings.PERDIX_ORIGIN.rstrip("/")
    url = f"{base}/perdix-server/api/users/current"  # adjust to real endpoint if different
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"JWT {access_token}",
        "origin": settings.PERDIX_ORIGIN,
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


def get_redirect_url(branch_name: str) -> dict:
    # Placeholder: mirror Next.js helper; customize as needed
    # Here we just echo a static path; replace with your logic
    return {"redirectURL": "/dashboard"}


def logout_user_from_perdix(authorization_header: str) -> tuple:
    """Logout user from Perdix using the provided JWT token.
    
    Args:
        authorization_header: Authorization header value (can be "JWT <token>", "Bearer <token>", or just "<token>")
    
    Returns:
        tuple: (response_body, status_code, is_json)
    """
    base_url = settings.PERDIX_ORIGIN.rstrip("/")
    url = f"{base_url}/gateway/jwt/logout"
    
    if not authorization_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )
    
    # Normalize authorization header
    # If it doesn't start with "JWT " or "Bearer ", assume it's just the token and prepend "JWT "
    auth_header = authorization_header.strip()
    if not (auth_header.startswith("JWT ") or auth_header.startswith("Bearer ") or 
            auth_header.startswith("jwt ") or auth_header.startswith("bearer ")):
        auth_header = f"JWT {auth_header}"
    
    headers = {
        "authorization": auth_header,
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Perdix logout API: {str(exc)}"
        )
    
    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


