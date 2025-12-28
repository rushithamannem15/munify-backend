from fastapi import APIRouter
from app.api.v1.endpoints import (
    master,
    master_common,
    auth,
    invitations,
    user_roles,
    organizations,
    projects,
    users,
    project_drafts,
    project_favorites,
    commitments,
    questions,
    project_notes,
    perdix,
    files,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
api_router.include_router(user_roles.router, prefix="/user-roles", tags=["user-roles"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(master.router, prefix="/master", tags=["master"])
api_router.include_router(master_common.router, prefix="/master/common", tags=["master-common"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(project_drafts.router, prefix="/project-drafts", tags=["project-drafts"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(project_favorites.router, prefix="/project-favorites", tags=["project-favorites"])
api_router.include_router(commitments.router, prefix="/commitments", tags=["commitments"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(project_notes.router, prefix="/project-notes", tags=["project-notes"])
api_router.include_router(perdix.router, prefix="/perdix", tags=["perdix"])
api_router.include_router(files.router, prefix="/files", tags=["files"])