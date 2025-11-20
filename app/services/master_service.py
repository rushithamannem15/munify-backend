import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.project_category_master import ProjectCategoryMaster
from app.models.project_stage_master import ProjectStageMaster
from app.schemas.master import ProjectCategoryMasterResponse, ProjectStageMasterResponse


class MasterService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_project_categories(self):
        """Get all project categories from master table"""
        categories = self.db.query(ProjectCategoryMaster).order_by(ProjectCategoryMaster.id).all()
        # Convert SQLAlchemy models to Pydantic schemas
        return [ProjectCategoryMasterResponse.model_validate(category) for category in categories]
    
    def get_all_project_stages(self):
        """Get all project stages from master table"""
        stages = self.db.query(ProjectStageMaster).order_by(ProjectStageMaster.id).all()
        # Convert SQLAlchemy models to Pydantic schemas
        return [ProjectStageMasterResponse.model_validate(stage) for stage in stages]


def fetch_roles_from_perdix() -> tuple:
    base = settings.PERDIX_ORIGIN.rstrip("/")
    path = "/management/user-management/allRoles.php"
    url = f"{base}{path}"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": settings.PERDIX_JWT,
        "origin": settings.PERDIX_ORIGIN,
        "referer": f"{settings.PERDIX_ORIGIN}/perdix-client/",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            # Debug: log the response for troubleshooting
            print(f"Perdix API Response Status: {response.status_code}")
            print(f"Perdix API Response Headers: {dict(response.headers)}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    try:
        return response.json(), response.status_code, True
    except ValueError:
        return response.text, response.status_code, False


