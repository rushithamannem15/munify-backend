from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class InvitationCreate(BaseModel):
    organization_id: int = Field(..., alias="organizationId")
    organization_type_id: int = Field(..., alias="organizationTypeId")
    full_name: str = Field(..., alias="fullName")
    user_id: str = Field(..., alias="userId")
    invited_by: str = Field(..., alias="invitedBy")
    email: EmailStr
    mobile_number: int = Field(..., alias="mobileNumber")
    role_id: int = Field(..., alias="roleId")
    role_name: str = Field(..., alias="roleName")

    class Config:
        populate_by_name = True


class InvitationResponse(BaseModel):
    id: int
    organization_id: int
    organization_type_id: int
    full_name: str
    user_id: str
    email: str
    mobile_number: str
    role_id: int
    role_name: str
    token: str
    expiry: datetime
    is_used: bool
    status: str
    invited_by: str
    accepted_at: Optional[datetime] = None
    resend_count: int
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[str] = None
    invite_link: str

    class Config:
        from_attributes = True


class InvitationValidate(BaseModel):
    token: str


class InvitationListResponse(BaseModel):
    status: str
    message: str
    data: list[InvitationResponse]
    total: int

    class Config:
        from_attributes = True
