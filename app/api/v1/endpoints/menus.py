from typing import Optional, List
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.services.menu_service import MenuService
from app.schemas.menu import (
    MenuCreate,
    MenuUpdate,
    MenuResponse,
    SubmenuCreate,
    SubmenuUpdate,
    SubmenuResponse,
    RoleOrgSubmenuMappingCreate,
    RoleOrgSubmenuMappingUpdate,
    RoleOrgSubmenuMappingResponse,
    UserMenuListResponse,
)

router = APIRouter()


# ==================== Menu Endpoints ====================

@router.post("/", response_model=MenuResponse, status_code=status.HTTP_201_CREATED)
def create_menu(
    menu_data: MenuCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new menu"""
    service = MenuService(db)
    return service.create_menu(menu_data, current_user.user_id)


@router.get("/", response_model=List[MenuResponse], status_code=status.HTTP_200_OK)
def get_all_menus(
    status_filter: Optional[str] = Query(None, description="Filter by status: 'A' or 'I'"),
    db: Session = Depends(get_db)
):
    """Get all menus"""
    service = MenuService(db)
    return service.get_all_menus(status_filter)


# IMPORTANT: This route must be defined BEFORE /{menu_id} to avoid route conflicts
@router.get("/user-menus", response_model=UserMenuListResponse, status_code=status.HTTP_200_OK)
def get_user_menus(
    role_id: Optional[int] = Query(None, description="User role ID (optional if using auth)"),
    org_type: Optional[str] = Query(None, description="Organization type (optional if using auth)"),
    current_user: Optional[CurrentUser] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get menus and submenus accessible to a user based on their role and organization type.
    This is the main endpoint for frontend menu rendering.
    
    If role_id and org_type are not provided, they will be extracted from the authenticated user.
    """
    service = MenuService(db)
    
    # Use provided params or extract from authenticated user
    final_role_id = role_id
    final_org_type = org_type
    
    if current_user:
        # Try to get from current_user if not provided
        if not final_role_id and current_user.role_id:
            try:
                final_role_id = int(current_user.role_id)
            except (ValueError, TypeError):
                pass
        
        if not final_org_type and current_user.org_type:
            final_org_type = current_user.org_type
    
    if not final_role_id or not final_org_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_id and org_type are required. Provide them as query parameters or ensure user is authenticated with role_id and org_type."
        )
    
    menus = service.get_user_menus(final_role_id, final_org_type)
    
    return {
        "status": "success",
        "message": "User menus fetched successfully",
        "data": menus
    }


@router.get("/{menu_id}", response_model=MenuResponse, status_code=status.HTTP_200_OK)
def get_menu_by_id(menu_id: int, db: Session = Depends(get_db)):
    """Get menu by ID"""
    service = MenuService(db)
    return service.get_menu_by_id(menu_id)


@router.put("/{menu_id}", response_model=MenuResponse, status_code=status.HTTP_200_OK)
def update_menu(
    menu_id: int,
    menu_data: MenuUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a menu"""
    service = MenuService(db)
    return service.update_menu(menu_id, menu_data, current_user.user_id)


@router.delete("/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu(
    menu_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a menu"""
    service = MenuService(db)
    service.delete_menu(menu_id)
    return None


# ==================== Submenu Endpoints ====================

@router.post("/submenus", response_model=SubmenuResponse, status_code=status.HTTP_201_CREATED)
def create_submenu(
    submenu_data: SubmenuCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new submenu"""
    service = MenuService(db)
    return service.create_submenu(submenu_data, current_user.user_id)


@router.get("/submenus", response_model=List[SubmenuResponse], status_code=status.HTTP_200_OK)
def get_all_submenus(
    menu_id: Optional[int] = Query(None, description="Filter by menu ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status: 'A' or 'I'"),
    db: Session = Depends(get_db)
):
    """Get all submenus"""
    service = MenuService(db)
    return service.get_all_submenus(menu_id, status_filter)


@router.get("/submenus/{submenu_id}", response_model=SubmenuResponse, status_code=status.HTTP_200_OK)
def get_submenu_by_id(submenu_id: int, db: Session = Depends(get_db)):
    """Get submenu by ID"""
    service = MenuService(db)
    return service.get_submenu_by_id(submenu_id)


@router.put("/submenus/{submenu_id}", response_model=SubmenuResponse, status_code=status.HTTP_200_OK)
def update_submenu(
    submenu_id: int,
    submenu_data: SubmenuUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a submenu"""
    service = MenuService(db)
    return service.update_submenu(submenu_id, submenu_data, current_user.user_id)


@router.delete("/submenus/{submenu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submenu(
    submenu_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a submenu"""
    service = MenuService(db)
    service.delete_submenu(submenu_id)
    return None


# ==================== Role-Org-Submenu Mapping Endpoints ====================

@router.post("/mappings", response_model=RoleOrgSubmenuMappingResponse, status_code=status.HTTP_201_CREATED)
def create_mapping(
    mapping_data: RoleOrgSubmenuMappingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new role-org-submenu mapping"""
    service = MenuService(db)
    return service.create_mapping(mapping_data, current_user.user_id)


@router.get("/mappings", response_model=List[RoleOrgSubmenuMappingResponse], status_code=status.HTTP_200_OK)
def get_mappings(
    role_id: Optional[int] = Query(None, description="Filter by role ID"),
    org_type: Optional[str] = Query(None, description="Filter by organization type"),
    submenu_id: Optional[int] = Query(None, description="Filter by submenu ID"),
    db: Session = Depends(get_db)
):
    """Get mappings with optional filters"""
    service = MenuService(db)
    return service.get_mappings(role_id, org_type, submenu_id)


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(
    mapping_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a mapping"""
    service = MenuService(db)
    service.delete_mapping(mapping_id)
    return None



