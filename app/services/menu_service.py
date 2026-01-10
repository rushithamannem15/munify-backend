from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from app.core.logging import get_logger
from app.models.menu_master import MenuMaster
from app.models.submenu_master import SubmenuMaster
from app.models.role_org_submenu_mapping import RoleOrgSubmenuMapping
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
    UserMenuResponse,
)

logger = get_logger("services.menu")


class MenuService:
    """Service for menu management operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Menu Operations ====================
    
    def create_menu(self, menu_data: MenuCreate, user_id: str) -> MenuResponse:
        """Create a new menu"""
        try:
            # Check if menu name already exists
            existing = self.db.query(MenuMaster).filter(
                MenuMaster.menu_name == menu_data.menu_name
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Menu with name '{menu_data.menu_name}' already exists"
                )
            
            # Create menu
            menu = MenuMaster(
                menu_name=menu_data.menu_name,
                menu_icon=menu_data.menu_icon,
                description=menu_data.description,
                display_order=menu_data.display_order,
                status=menu_data.status,
                created_by=user_id,
                updated_by=user_id
            )
            
            self.db.add(menu)
            self.db.commit()
            self.db.refresh(menu)
            
            logger.info(f"Menu created: {menu.id} - {menu.menu_name}")
            return MenuResponse.model_validate(menu)
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating menu: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create menu: {str(e)}"
            )
    
    def get_all_menus(self, status_filter: Optional[str] = None) -> List[MenuResponse]:
        """Get all menus, optionally filtered by status"""
        query = self.db.query(MenuMaster)
        
        if status_filter:
            query = query.filter(MenuMaster.status == status_filter)
        
        menus = query.order_by(
            MenuMaster.display_order.asc().nullslast(),
            MenuMaster.menu_name.asc()
        ).all()
        
        return [MenuResponse.model_validate(menu) for menu in menus]
    
    def get_menu_by_id(self, menu_id: int) -> MenuResponse:
        """Get menu by ID"""
        menu = self.db.query(MenuMaster).filter(MenuMaster.id == menu_id).first()
        
        if not menu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu with ID {menu_id} not found"
            )
        
        return MenuResponse.model_validate(menu)
    
    def update_menu(self, menu_id: int, menu_data: MenuUpdate, user_id: str) -> MenuResponse:
        """Update a menu"""
        menu = self.db.query(MenuMaster).filter(MenuMaster.id == menu_id).first()
        
        if not menu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu with ID {menu_id} not found"
            )
        
        # Check if menu_name is being changed and if new name already exists
        if menu_data.menu_name and menu_data.menu_name != menu.menu_name:
            existing = self.db.query(MenuMaster).filter(
                and_(
                    MenuMaster.menu_name == menu_data.menu_name,
                    MenuMaster.id != menu_id
                )
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Menu with name '{menu_data.menu_name}' already exists"
                )
        
        # Update fields
        update_data = menu_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(menu, field, value)
        
        menu.updated_by = user_id
        self.db.commit()
        self.db.refresh(menu)
        
        logger.info(f"Menu updated: {menu.id} - {menu.menu_name}")
        return MenuResponse.model_validate(menu)
    
    def delete_menu(self, menu_id: int) -> None:
        """Delete a menu (cascade will delete submenus)"""
        menu = self.db.query(MenuMaster).filter(MenuMaster.id == menu_id).first()
        
        if not menu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu with ID {menu_id} not found"
            )
        
        self.db.delete(menu)
        self.db.commit()
        
        logger.info(f"Menu deleted: {menu_id}")
    
    # ==================== Submenu Operations ====================
    
    def create_submenu(self, submenu_data: SubmenuCreate, user_id: str) -> SubmenuResponse:
        """Create a new submenu"""
        try:
            # Verify menu exists
            menu = self.db.query(MenuMaster).filter(MenuMaster.id == submenu_data.menu_id).first()
            if not menu:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu with ID {submenu_data.menu_id} not found"
                )
            
            # Check if submenu name already exists
            existing = self.db.query(SubmenuMaster).filter(
                SubmenuMaster.submenu_name == submenu_data.submenu_name
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Submenu with name '{submenu_data.submenu_name}' already exists"
                )
            
            # Create submenu
            submenu = SubmenuMaster(
                submenu_name=submenu_data.submenu_name,
                submenu_icon=submenu_data.submenu_icon,
                route=submenu_data.route,
                menu_id=submenu_data.menu_id,
                display_order=submenu_data.display_order,
                status=submenu_data.status,
                created_by=user_id,
                updated_by=user_id
            )
            
            self.db.add(submenu)
            self.db.commit()
            self.db.refresh(submenu)
            
            logger.info(f"Submenu created: {submenu.id} - {submenu.submenu_name}")
            return SubmenuResponse.model_validate(submenu)
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating submenu: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create submenu: {str(e)}"
            )
    
    def get_all_submenus(self, menu_id: Optional[int] = None, status_filter: Optional[str] = None) -> List[SubmenuResponse]:
        """Get all submenus, optionally filtered by menu_id and status"""
        query = self.db.query(SubmenuMaster)
        
        if menu_id:
            query = query.filter(SubmenuMaster.menu_id == menu_id)
        
        if status_filter:
            query = query.filter(SubmenuMaster.status == status_filter)
        
        submenus = query.order_by(
            SubmenuMaster.display_order.asc().nullslast(),
            SubmenuMaster.submenu_name.asc()
        ).all()
        
        return [SubmenuResponse.model_validate(submenu) for submenu in submenus]
    
    def get_submenu_by_id(self, submenu_id: int) -> SubmenuResponse:
        """Get submenu by ID"""
        submenu = self.db.query(SubmenuMaster).filter(SubmenuMaster.id == submenu_id).first()
        
        if not submenu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submenu with ID {submenu_id} not found"
            )
        
        return SubmenuResponse.model_validate(submenu)
    
    def update_submenu(self, submenu_id: int, submenu_data: SubmenuUpdate, user_id: str) -> SubmenuResponse:
        """Update a submenu"""
        submenu = self.db.query(SubmenuMaster).filter(SubmenuMaster.id == submenu_id).first()
        
        if not submenu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submenu with ID {submenu_id} not found"
            )
        
        # Verify menu exists if menu_id is being updated
        if submenu_data.menu_id and submenu_data.menu_id != submenu.menu_id:
            menu = self.db.query(MenuMaster).filter(MenuMaster.id == submenu_data.menu_id).first()
            if not menu:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu with ID {submenu_data.menu_id} not found"
                )
        
        # Check if submenu name is being changed and if new name already exists
        if submenu_data.submenu_name and submenu_data.submenu_name != submenu.submenu_name:
            existing = self.db.query(SubmenuMaster).filter(
                SubmenuMaster.submenu_name == submenu_data.submenu_name
            ).first()
            
            if existing and existing.id != submenu_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Submenu with name '{submenu_data.submenu_name}' already exists"
                )
        
        # Update fields
        update_data = submenu_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(submenu, field, value)
        
        submenu.updated_by = user_id
        self.db.commit()
        self.db.refresh(submenu)
        
        logger.info(f"Submenu updated: {submenu.id} - {submenu.submenu_name}")
        return SubmenuResponse.model_validate(submenu)
    
    def delete_submenu(self, submenu_id: int) -> None:
        """Delete a submenu"""
        submenu = self.db.query(SubmenuMaster).filter(SubmenuMaster.id == submenu_id).first()
        
        if not submenu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submenu with ID {submenu_id} not found"
            )
        
        self.db.delete(submenu)
        self.db.commit()
        
        logger.info(f"Submenu deleted: {submenu_id}")
    
    # ==================== Role-Org-Submenu Mapping Operations ====================
    
    def create_mapping(self, mapping_data: RoleOrgSubmenuMappingCreate, user_id: str) -> RoleOrgSubmenuMappingResponse:
        """Create a new role-org-submenu mapping"""
        try:
            # Verify submenu exists
            submenu = self.db.query(SubmenuMaster).filter(
                SubmenuMaster.id == mapping_data.submenu_id
            ).first()
            
            if not submenu:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Submenu with ID {mapping_data.submenu_id} not found"
                )
            
            # Check if mapping already exists
            existing = self.db.query(RoleOrgSubmenuMapping).filter(
                and_(
                    RoleOrgSubmenuMapping.role_id == mapping_data.role_id,
                    RoleOrgSubmenuMapping.org_type == mapping_data.org_type,
                    RoleOrgSubmenuMapping.submenu_id == mapping_data.submenu_id
                )
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Mapping already exists for this role, org_type, and submenu combination"
                )
            
            # Create mapping
            mapping = RoleOrgSubmenuMapping(
                role_id=mapping_data.role_id,
                org_type=mapping_data.org_type,
                submenu_id=mapping_data.submenu_id,
                status=mapping_data.status,
                created_by=user_id,
                updated_by=user_id
            )
            
            self.db.add(mapping)
            self.db.commit()
            self.db.refresh(mapping)
            
            logger.info(f"Mapping created: role_id={mapping.role_id}, org_type={mapping.org_type}, submenu_id={mapping.submenu_id}")
            return RoleOrgSubmenuMappingResponse.model_validate(mapping)
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating mapping: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create mapping: {str(e)}"
            )
    
    def get_user_menus(self, role_id: int, org_type: str) -> List[UserMenuResponse]:
        """
        Get menus and submenus accessible to a user based on their role and organization type.
        This is the main endpoint for frontend menu rendering.
        """
        # Get all active mappings for this role and org_type
        mappings = self.db.query(RoleOrgSubmenuMapping).filter(
            and_(
                RoleOrgSubmenuMapping.role_id == role_id,
                RoleOrgSubmenuMapping.org_type == org_type,
                RoleOrgSubmenuMapping.status == 'A'
            )
        ).all()
        
        if not mappings:
            return []
        
        # Get unique submenu IDs
        submenu_ids = [mapping.submenu_id for mapping in mappings]
        
        # Get all submenus with their menus
        submenus = self.db.query(SubmenuMaster).filter(
            and_(
                SubmenuMaster.id.in_(submenu_ids),
                SubmenuMaster.status == 'A'
            )
        ).all()
        
        # Group submenus by menu
        menu_dict = {}
        for submenu in submenus:
            menu_id = submenu.menu_id
            
            if menu_id not in menu_dict:
                # Get menu details
                menu = self.db.query(MenuMaster).filter(
                    and_(
                        MenuMaster.id == menu_id,
                        MenuMaster.status == 'A'
                    )
                ).first()
                
                if menu:
                    menu_dict[menu_id] = {
                        'menu_id': menu.id,
                        'menu_name': menu.menu_name,
                        'menu_icon': menu.menu_icon,
                        'submenus': []
                    }
            
            if menu_id in menu_dict:
                menu_dict[menu_id]['submenus'].append(SubmenuResponse.model_validate(submenu))
        
        # Convert to response format and sort
        result = []
        for menu_data in menu_dict.values():
            # Sort submenus by display_order
            menu_data['submenus'].sort(key=lambda x: (x.display_order if x.display_order is not None else 999, x.submenu_name))
            result.append(UserMenuResponse(**menu_data))
        
        # Sort menus by display_order (we need to get menu display_order)
        menus_with_order = []
        for item in result:
            menu = self.db.query(MenuMaster).filter(MenuMaster.id == item.menu_id).first()
            if menu:
                menus_with_order.append((menu.display_order if menu.display_order is not None else 999, item))
        
        menus_with_order.sort(key=lambda x: (x[0], x[1].menu_name))
        result = [item[1] for item in menus_with_order]
        
        return result
    
    def get_mappings(
        self,
        role_id: Optional[int] = None,
        org_type: Optional[str] = None,
        submenu_id: Optional[int] = None
    ) -> List[RoleOrgSubmenuMappingResponse]:
        """Get mappings with optional filters"""
        query = self.db.query(RoleOrgSubmenuMapping)
        
        if role_id:
            query = query.filter(RoleOrgSubmenuMapping.role_id == role_id)
        
        if org_type:
            query = query.filter(RoleOrgSubmenuMapping.org_type == org_type)
        
        if submenu_id:
            query = query.filter(RoleOrgSubmenuMapping.submenu_id == submenu_id)
        
        mappings = query.all()
        return [RoleOrgSubmenuMappingResponse.model_validate(mapping) for mapping in mappings]
    
    def delete_mapping(self, mapping_id: int) -> None:
        """Delete a mapping"""
        mapping = self.db.query(RoleOrgSubmenuMapping).filter(
            RoleOrgSubmenuMapping.id == mapping_id
        ).first()
        
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping with ID {mapping_id} not found"
            )
        
        self.db.delete(mapping)
        self.db.commit()
        
        logger.info(f"Mapping deleted: {mapping_id}")

