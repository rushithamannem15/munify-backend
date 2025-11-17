"""
Models package - imports all models to ensure SQLAlchemy can resolve relationships.
This ensures all models are loaded before SQLAlchemy initializes mappers.
"""

# Import all models to ensure they're registered with SQLAlchemy
# Order matters to avoid circular import issues, but string-based relationships help

# Standalone models
from app.models.invitation import Invitation
from app.models.project import Project

# Export all models for convenience
__all__ = [
    "Invitation",
    "Project",
]

