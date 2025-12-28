import uuid
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate


def _is_invitation_used(invitation: Invitation) -> bool:
    """
    Backward-compatible notion of "used" based on the new status field.

    Previously this was a simple boolean `is_used`. With the Perdix schema we
    treat an invitation as "used" when it has been accepted (status == 'A').
    """
    return invitation.status == "A"


def _build_invitation_response(invitation: Invitation) -> dict:
    """Build complete invitation response dictionary with all necessary fields."""
    invite_link = f"{settings.FRONTEND_ORIGIN}/register?token={invitation.token}"
    return {
        "id": invitation.id,
        "organization_id": int(invitation.organization_id),
        "organization_type_id": int(invitation.organization_type_id),
        "full_name": invitation.full_name,
        "user_id": invitation.user_id,
        "email": invitation.email,
        "mobile_number": invitation.mobile_number,
        "role_id": int(invitation.role_id),
        "role_name": invitation.role_name,
        "token": invitation.token,
        "expiry": invitation.expiry,
        "is_used": _is_invitation_used(invitation),
        "status": invitation.status,
        "invited_by": invitation.invited_by,
        "accepted_at": invitation.accepted_at,
        "resend_count": invitation.resend_count or 0,
        "created_at": invitation.created_at,
        "created_by": invitation.created_by,
        "updated_at": invitation.updated_at,
        "updated_by": invitation.updated_by,
        "invite_link": invite_link,
    }


def generate_invitation_token(db: Session, length_bytes: int = 9, max_attempts: int = 5) -> str:
    """Generate a short, URL-safe unique token (~12 chars with 9 bytes entropy).

    Ensures uniqueness by checking the database and retrying on collisions.
    """
    for _ in range(max_attempts):
        token = secrets.token_urlsafe(length_bytes)
        exists = db.query(Invitation.id).filter(Invitation.token == token).first()
        if not exists:
            return token
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not generate unique invitation token. Please try again.",
    )


def create_invitation(payload: InvitationCreate, db: Session) -> dict:
    """Create a new invitation and return invitation details.

    Behavioural parity with the old implementation:
    - Reject if there is already an active invitation for the same email
      (extended here to also match mobile_number to better reflect the new schema).
    - Generate a token and 7-day expiry.
    """

    # Check if invitation already exists for this email & mobile number and is still pending
    existing_invitation = (
        db.query(Invitation)
        .filter(
            Invitation.email == payload.email,
            Invitation.mobile_number == str(payload.mobile_number),
            Invitation.status == "P",
        )
        .first()
    )
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation already exists for this email and mobile number",
        )

    # Generate token and expiry (7 days from now)
    token = generate_invitation_token(db)
    expiry = datetime.now(timezone.utc) + timedelta(days=7)

    # Create invitation record
    invitation = Invitation(
        organization_id=str(payload.organization_id),
        organization_type_id=str(payload.organization_type_id),
        full_name=payload.full_name,
        user_id=str(payload.user_id),
        email=payload.email,
        mobile_number=str(payload.mobile_number),
        role_id=str(payload.role_id),
        role_name=payload.role_name,
        invited_by=payload.invited_by,
        token=token,
        expiry=expiry,
        status="P",
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return _build_invitation_response(invitation)


def validate_invitation_token(token: str, db: Session) -> dict:
    """Validate invitation token and return invitation details."""

    invitation = db.query(Invitation).filter(Invitation.token == token).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )

    if _is_invitation_used(invitation):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been used",
        )

    if datetime.now(timezone.utc) > invitation.expiry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    return _build_invitation_response(invitation)


def mark_invitation_used(token: str, db: Session) -> bool:
    """Mark invitation as used after successful registration.

    With the new schema, this corresponds to setting status='A' and accepted_at.
    """

    invitation = db.query(Invitation).filter(Invitation.token == token).first()

    if not invitation:
        return False

    invitation.status = "A"
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.updated_at = datetime.now(timezone.utc)
    db.commit()

    return True


def get_invitations(skip: int = 0, limit: int = 100, db: Session = None) -> dict:
    """Get list of invitations with pagination, ordered by most recent first."""

    query = db.query(Invitation)
    total = query.count()
    invitations = query.order_by(Invitation.created_at.desc(), Invitation.id.desc()).offset(skip).limit(limit).all()

    invitation_list = []
    for invitation in invitations:
        invitation_list.append(_build_invitation_response(invitation))

    return {
        "status": "success",
        "message": "Invitations fetched successfully",
        "data": invitation_list,
        "total": total,
    }


def resend_invitation(invitation_id: int, db: Session) -> dict:
    """Resend invitation by generating new token and extending expiry."""

    invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if _is_invitation_used(invitation):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resend used invitation",
        )

    # Generate new token and extend expiry
    invitation.token = generate_invitation_token(db)
    invitation.expiry = datetime.now(timezone.utc) + timedelta(days=7)
    invitation.updated_at = datetime.now(timezone.utc)
    invitation.resend_count = (invitation.resend_count or 0) + 1

    db.commit()
    db.refresh(invitation)

    return _build_invitation_response(invitation)
