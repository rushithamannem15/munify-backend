from pydantic import BaseModel, ConfigDict
from decimal import Decimal


class StatisticsResponse(BaseModel):
    """Statistics response schema for dashboard metrics"""
    total_municipal_corporations: int
    total_projects_funded: Decimal
    total_active_lenders: int
    total_approved_commitment: int
    
    model_config = ConfigDict(from_attributes=True)

