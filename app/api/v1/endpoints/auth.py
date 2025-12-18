from fastapi import APIRouter, HTTPException, status, Header
from fastapi.responses import JSONResponse
from app.services.auth_service import obtain_jwt_from_perdix, request_password_otp_from_perdix, change_password_with_otp, logout_user_from_perdix
from app.schemas.auth import ChangePasswordWithOTP


router = APIRouter()


@router.post("/login")
def login(body: dict):
    login_data = body.get("loginData")
    skip_relogin = body.get("skip_relogin", "yes")

    auth_data, auth_status, auth_is_json = obtain_jwt_from_perdix(login_data, skip_relogin)
    if auth_status != 200:
        message = (auth_data or {}).get("error") if isinstance(auth_data, dict) else auth_data
        return JSONResponse({"message": message}, status_code=401)

    return JSONResponse({"authData": auth_data}, status_code=200)


@router.post("/forgot-password/otp")
def request_forgot_password_otp(body: dict):
    user_id = body.get("userId") or body.get("login")
    if not user_id:
        return JSONResponse({"status": "error", "message": "userId is required"}, status_code=422)

    body, status_code, is_json = request_password_otp_from_perdix(user_id)
    content = body if is_json else {"raw": body}
    # normalize success message
    if 200 <= status_code < 300:
        return JSONResponse({"status": "success", "message": "OTP sent if user exists", "data": content}, status_code=status_code)
    return JSONResponse({"status": "error", "message": content if isinstance(content, str) else content}, status_code=status_code)


@router.post("/change-password/otp")
def change_password_with_otp_endpoint(password_data: ChangePasswordWithOTP):
    """Change password using OTP verification"""
    if password_data.newPassword != password_data.confirmPassword:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New password and confirm password do not match")

    body, status_code, is_json = change_password_with_otp(
        otp=password_data.otp,
        user_id=password_data.userId,
        new_password=password_data.newPassword,
        confirm_password=password_data.confirmPassword,
    )

    content = body if is_json else {"raw": body}
    if 200 <= status_code < 300:
        return JSONResponse({"status": "success", "message": "Password changed successfully", "data": content}, status_code=status_code)
    error_message = content if isinstance(content, str) else (content.get("message") or "Password change failed")
    return JSONResponse({"status": "error", "message": error_message, "data": content if not isinstance(content, str) else None}, status_code=status_code)


@router.post("/logout")
def logout(
    authorization: str = Header(..., description="Authorization header with JWT token (format: 'JWT <token>' or 'Bearer <token>')")
):
    """
    Logout user from Perdix using JWT token from Authorization header.
    
    The frontend should pass the JWT token in the Authorization header.
    The token can be prefixed with 'JWT ' or 'Bearer ' or sent as-is.
    
    Returns the response directly from Perdix.
    """
    body, status_code, is_json = logout_user_from_perdix(authorization)
    content = body if is_json else {"raw": body}
    return JSONResponse(content=content, status_code=status_code)

