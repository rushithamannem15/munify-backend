"""
Models package - imports all models to ensure SQLAlchemy can resolve relationships.
This ensures all models are loaded before SQLAlchemy initializes mappers.
"""

# Import all models to ensure they're registered with SQLAlchemy
# Order matters to avoid circular import issues, but string-based relationships help

from app.models.invitation import Invitation
from app.models.project import Project
from app.models.project_draft import ProjectDraft
from app.models.project_category_master import ProjectCategoryMaster
from app.models.project_stage_master import ProjectStageMaster
from app.models.project_favorite import ProjectFavorite
from app.models.project_rejection_history import ProjectRejectionHistory
from app.models.commitment import Commitment
from app.models.commitment_history import CommitmentHistory

# Export all models for convenience
__all__ = [
    "Invitation",
    "Project",
    "ProjectDraft",
    "ProjectCategoryMaster",
    "ProjectStageMaster",
    "ProjectFavorite",
    "ProjectRejectionHistory",
    "Commitment",
    "CommitmentHistory",
]
