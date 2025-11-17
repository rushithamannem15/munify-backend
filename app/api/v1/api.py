from fastapi import APIRouter
from app.api.v1.endpoints import master, auth, invitations, user_roles, organizations, projects

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
api_router.include_router(user_roles.router, prefix="/user-roles", tags=["user-roles"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(master.router, prefix="/master", tags=["master"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
