"""
Commitment Document Schemas - Request/Response models for commitment document operations
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.file import FileResponse


class CommitmentDocumentResponse(BaseModel):
    """Response schema for commitment document with file details"""
    id: int
    commitment_id: int
    file_id: int
    document_type: str
    is_required: bool
    uploaded_by: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    # File details from perdix_mp_files
    file: Optional['FileResponse'] = None
    
    model_config = ConfigDict(from_attributes=True)


class CommitmentFileUploadResponse(BaseModel):
    """Response schema for commitment file upload"""
    status: str
    message: str
    data: dict
    
    class CommitmentFileUploadData(BaseModel):
        file_id: int
        commitment_document_id: int
        document_type: str
        commitment_id: int
    
    model_config = ConfigDict(from_attributes=True)


class CommitmentFileDeleteResponse(BaseModel):
    """Response schema for commitment file deletion"""
    status: str
    message: str

