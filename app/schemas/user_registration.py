from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime


class UserBranchCreate(BaseModel):
    """Schema for user branch in Perdix API"""
    branchId: int = Field(..., alias="branch_id")
    titleExpr: str = Field(..., alias="title_expr")
    
    model_config = {"populate_by_name": True}


class PerdixUserCreatePayload(BaseModel):
    """Schema for Perdix API user creation payload"""
    roleCode: str = Field(default="A", alias="role_code")
    activated: bool = Field(default=True)
    userState: str = Field(default="ACTIVE", alias="user_state")
    userType: str = Field(default="A", alias="user_type")
    bankName: Optional[str] = Field(None, alias="bank_name")
    validUntil: str = Field(..., alias="valid_until")
    accessType: str = Field(default="BRANCH", alias="access_type")
    imeiNumber: Optional[str] = Field(default="", alias="imei_number")
    langKey: str = Field(default="en", alias="lang_key")
    userRoles: List[Dict[str, Any]] = Field(default_factory=list, alias="user_roles")
    userBranches: List[UserBranchCreate] = Field(..., alias="user_branches")
    userName: str = Field(..., alias="user_name")
    login: str
    password: str
    confirmPassword: str = Field(..., alias="confirm_password")
    email: EmailStr
    mobileNumber: int = Field(..., alias="mobile_number")
    branchId: int = Field(..., alias="branch_id")
    branchName: str = Field(..., alias="branch_name")
    changePasswordOnLogin: bool = Field(default=True, alias="change_password_on_login")
    
    model_config = {"populate_by_name": True}
    
    def model_dump_for_perdix(self) -> dict:
        """Convert to dict format expected by Perdix API"""
        return {
            "roleCode": self.roleCode,
            "activated": self.activated,
            "userState": self.userState,
            "userType": self.userType,
            "bankName": self.bankName or "",
            "validUntil": self.validUntil,
            "accessType": self.accessType,
            "imeiNumber": self.imeiNumber or "",
            "langKey": self.langKey,
            "userRoles": self.userRoles,
            "userBranches": [{"branchId": branch.branchId, "titleExpr": branch.titleExpr} for branch in self.userBranches],
            "userName": self.userName,
            "login": self.login,
            "password": self.password,
            "confirmPassword": self.confirmPassword,
            "email": self.email,
            "mobileNumber": self.mobileNumber,
            "branchId": self.branchId,
            "branchName": self.branchName,
            "changePasswordOnLogin": self.changePasswordOnLogin,
        }


class OrganizationInfo(BaseModel):
    """Organization information from frontend"""
    id: int
    orgName: str  # Frontend sends camelCase: orgName


class OrgTypeInfo(BaseModel):
    """Organization type information from frontend"""
    id: int
    orgTypeName: str  # Frontend sends camelCase: orgTypeName


class UserRoleInfo(BaseModel):
    """User role information (ignored for now)"""
    userId: Optional[str] = None
    userName: Optional[str] = None
    roleId: Optional[int] = None
    roleName: Optional[str] = None
    userRoleId: Optional[int] = None
    id: Optional[int] = None


class UserRegistrationCreate(BaseModel):
    """Schema matching frontend payload structure"""
    # User basic info
    fullName: str = Field(..., alias="fullName")
    login: str
    password: str
    confirmPassword: str = Field(..., alias="confirmPassword")
    email: EmailStr
    mobileNumber: int = Field(..., alias="mobileNumber")
    
    # Organization info
    organization: OrganizationInfo
    orgtypeObj: OrgTypeInfo = Field(..., alias="orgtypeObj")
    
    # Optional fields
    designation: Optional[str] = None
    regulatoryRegistrationNo: Optional[str] = Field(None, alias="regulatoryRegistrationNo")
    
    # User roles (ignored for now, will be handled in next phase)
    userRoles: Optional[List[UserRoleInfo]] = Field(default_factory=list, alias="userRoles")
    
    model_config = {"populate_by_name": True}
    
    def get_organization_name(self) -> str:
        """Get organization name"""
        return self.organization.orgName
    
    def get_organization_type(self) -> str:
        """Get organization type name"""
        return self.orgtypeObj.orgTypeName
    
    def get_organization_id(self) -> int:
        """Get organization ID (used as branchId)"""
        return self.organization.id
    
    def get_user_role_id(self) -> Optional[int]:
        """Get user role ID from userRoles array (first role)"""
        if self.userRoles and len(self.userRoles) > 0:
            return self.userRoles[0].roleId
        return None


class UserRegistrationResponse(BaseModel):
    """Response schema for user registration"""
    id: int
    organization_name: str
    organization_type: str
    user_id: str
    user_role: int
    user_name: Optional[str]
    user_email: str
    user_mobile_number: Optional[str]
    designation: Optional[str]
    registration_number: Optional[str]
    is_tc_accepted: bool
    state: Optional[str]
    district: Optional[str]
    gstn_ulb_code: Optional[str]
    annual_budget_size: Optional[Decimal]
    status: Optional[str]
    is_mobile_verified: bool
    mobile_verified_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]
    file_id: Optional[int]
    
    model_config = {"from_attributes": True}

