from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==================== Menu Schemas ====================

class MenuCreate(BaseModel):
    """Schema for creating a menu"""
    menu_name: str = Field(..., max_length=255, description="Menu name")
    menu_icon: Optional[str] = Field(None, max_length=255, description="Menu icon name or path")
    description: Optional[str] = Field(None, description="Menu description")
    display_order: Optional[int] = Field(None, description="Display order for menu sorting")
    status: str = Field("A", max_length=50, description="Status: 'A' = Active, 'I' = Inactive")
    
    model_config = ConfigDict(from_attributes=True)


class MenuUpdate(BaseModel):
    """Schema for updating a menu"""
    menu_name: Optional[str] = Field(None, max_length=255)
    menu_icon: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = None
    status: Optional[str] = Field(None, max_length=50)
    
    model_config = ConfigDict(from_attributes=True)


class MenuResponse(BaseModel):
    """Schema for menu response"""
    id: int
    menu_name: str
    menu_icon: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    status: str
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Submenu Schemas ====================

class SubmenuCreate(BaseModel):
    """Schema for creating a submenu"""
    submenu_name: str = Field(..., max_length=255, description="Submenu name")
    submenu_icon: Optional[str] = Field(None, max_length=255, description="Submenu icon name or path")
    route: str = Field(..., max_length=500, description="Frontend route path")
    menu_id: int = Field(..., description="Parent menu ID")
    display_order: Optional[int] = Field(None, description="Display order for submenu sorting")
    status: str = Field("A", max_length=50, description="Status: 'A' = Active, 'I' = Inactive")
    
    model_config = ConfigDict(from_attributes=True)


class SubmenuUpdate(BaseModel):
    """Schema for updating a submenu"""
    submenu_name: Optional[str] = Field(None, max_length=255)
    submenu_icon: Optional[str] = Field(None, max_length=255)
    route: Optional[str] = Field(None, max_length=500)
    menu_id: Optional[int] = None
    display_order: Optional[int] = None
    status: Optional[str] = Field(None, max_length=50)
    
    model_config = ConfigDict(from_attributes=True)


class SubmenuResponse(BaseModel):
    """Schema for submenu response"""
    id: int
    submenu_name: str
    submenu_icon: Optional[str] = None
    route: str
    menu_id: int
    display_order: Optional[int] = None
    status: str
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Role-Org-Submenu Mapping Schemas ====================

class RoleOrgSubmenuMappingCreate(BaseModel):
    """Schema for creating a role-org-submenu mapping"""
    role_id: int = Field(..., description="Role ID from perdix_mp_roles_master")
    org_type: str = Field(..., max_length=50, description="Organization type: 'municipality', 'lender', 'admin', 'government'")
    submenu_id: int = Field(..., description="Submenu ID")
    status: str = Field("A", max_length=50, description="Status: 'A' = Active, 'I' = Inactive")
    
    model_config = ConfigDict(from_attributes=True)


class RoleOrgSubmenuMappingUpdate(BaseModel):
    """Schema for updating a role-org-submenu mapping"""
    role_id: Optional[int] = None
    org_type: Optional[str] = Field(None, max_length=50)
    submenu_id: Optional[int] = None
    status: Optional[str] = Field(None, max_length=50)
    
    model_config = ConfigDict(from_attributes=True)


class RoleOrgSubmenuMappingResponse(BaseModel):
    """Schema for role-org-submenu mapping response"""
    id: int
    role_id: int
    org_type: str
    submenu_id: int
    status: str
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Combined Response Schemas ====================

class UserMenuResponse(BaseModel):
    """Menu structure for a specific user (role + org_type)"""
    menu_id: int
    menu_name: str
    menu_icon: Optional[str] = None
    submenus: List[SubmenuResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class UserMenuListResponse(BaseModel):
    """Response for user menu endpoint"""
    status: str
    message: str
    data: List[UserMenuResponse]

