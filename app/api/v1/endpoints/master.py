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


@router.get("/funding-types", response_model=MasterListResponse, status_code=status.HTTP_200_OK)
def get_funding_types(db: Session = Depends(get_db)):
    """Get all funding types from master table"""
    service = MasterService(db)
    funding_types = service.get_all_funding_types()
    return {
        "status": "success",
        "message": "Funding types fetched successfully",
        "data": funding_types
    }


@router.get("/mode-of-implementations", response_model=MasterListResponse, status_code=status.HTTP_200_OK)
def get_mode_of_implementations(db: Session = Depends(get_db)):
    """Get all modes of implementation from master table"""
    service = MasterService(db)
    modes = service.get_all_mode_of_implementations()
    return {
        "status": "success",
        "message": "Modes of implementation fetched successfully",
        "data": modes
    }


@router.get("/ownerships", response_model=MasterListResponse, status_code=status.HTTP_200_OK)
def get_ownerships(db: Session = Depends(get_db)):
    """Get all ownership types from master table"""
    service = MasterService(db)
    ownerships = service.get_all_ownerships()
    return {
        "status": "success",
        "message": "Ownership types fetched successfully",
        "data": ownerships
    }
