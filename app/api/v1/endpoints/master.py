from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.master_service import fetch_roles_from_perdix, MasterService
from app.schemas.master import ProjectCategoryMasterResponse, ProjectStageMasterResponse, MasterListResponse


router = APIRouter()


@router.get("/roles")
def get_roles():
    body, status_code, is_json = fetch_roles_from_perdix()
    return JSONResponse(content=body if is_json else {"raw": body}, status_code=status_code)


@router.get("/project-categories", response_model=MasterListResponse, status_code=status.HTTP_200_OK)
def get_project_categories(db: Session = Depends(get_db)):
    """Get all project categories from master table"""
    service = MasterService(db)
    categories = service.get_all_project_categories()
    return {
        "status": "success",
        "message": "Project categories fetched successfully",
        "data": categories
    }


@router.get("/project-stages", response_model=MasterListResponse, status_code=status.HTTP_200_OK)
def get_project_stages(db: Session = Depends(get_db)):
    """Get all project stages from master table"""
    service = MasterService(db)
    stages = service.get_all_project_stages()
    return {
        "status": "success",
        "message": "Project stages fetched successfully",
        "data": stages
    }

