"""
File API Endpoints

Handles file upload, download, and management operations.
"""
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, CurrentUser
from app.services.file_service import FileService
from app.schemas.file import (
    FileUploadRequest,
    FileResponse,
    FileUploadResponse,
    FileMetadataResponse,
    FileDeleteResponse,
    FileAccessUpdate,
    FileAccessUpdateResponse,
    PresignedUrlResponse
)
from app.core.logging import get_logger

logger = get_logger("api.files")

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    organization_id: str = Form(..., description="Organization ID"),
    file_category: str = Form(..., description="File category: KYC, Project, or Additional"),
    document_type: str = Form(..., description="Document type"),
    project_reference_id: Optional[str] = Form(None, description="Project reference ID (required for Project/Additional)"),
    access_level: str = Form("private", description="Access level: public, restricted, or private"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Upload a file to S3 storage.
    
    The file will be organized in S3 based on:
    - Organization ID
    - File category (KYC, Project, Additional)
    - Document type
    - Project reference ID (if applicable)
    
    **File Categories:**
    - **KYC**: KYC documents (PAN, GST)
    - **Project**: Project-related documents (DPR, Project Image, Project videos)
    - **Additional**: Additional documents (commitment, Requested document)
    
    **Document Types:**
    - KYC: PAN, GST
    - Project: DPR, Project Image, Project videos
    - Additional: commitment, Requested document
    
    **Note**: project_reference_id is required for Project and Additional categories.
    """
    try:
        # Validate project_reference_id for Project/Additional categories
        if file_category in ["Project", "Additional"] and not project_reference_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"project_reference_id is required for {file_category} category"
            )
        
        # Validate file category
        if file_category not in ["KYC", "Project", "Additional"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file_category. Must be: KYC, Project, or Additional"
            )
        
        # Validate access level
        if access_level not in ["public", "restricted", "private"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid access_level. Must be: public, restricted, or private"
            )
        
        file_service = FileService(db)
        file_record = file_service.upload_file(
            file=file,
            organization_id=organization_id,
            uploaded_by=current_user.user_id,
            file_category=file_category,
            document_type=document_type,
            access_level=access_level,
            project_reference_id=project_reference_id,
            created_by=current_user.user_id
        )
        
        file_response = FileResponse.model_validate(file_record)
        
        return FileUploadResponse(
            status="success",
            message="File uploaded successfully",
            data=file_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/{file_id}", response_model=FileMetadataResponse, status_code=status.HTTP_200_OK)
def get_file_metadata(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    Get file metadata by file ID.
    
    Returns file information including:
    - File details (name, size, type)
    - Storage path
    - Access level
    - Download count
    - Timestamps
    """
    try:
        file_service = FileService(db)
        file_record = file_service.get_file_metadata(file_id)
        
        file_response = FileResponse.model_validate(file_record)
        
        return FileMetadataResponse(
            status="success",
            data=file_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get file metadata error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file metadata: {str(e)}"
        )


@router.get("/{file_id}/download", status_code=status.HTTP_200_OK)
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(None, alias="user_id"),
    organization_id: Optional[str] = Header(None, alias="organization_id")
):
    """
    Download a file by file ID.
    
    The file will be streamed to the client with appropriate headers.
    Access control is enforced based on file access level.
    """
    try:
        file_service = FileService(db)
        file_bytes, file_record = file_service.download_file(
            file_id=file_id,
            user_id=user_id,
            organization_id=organization_id
        )
        
        return StreamingResponse(
            iter([file_bytes]),
            media_type=file_record.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_record.original_filename}"',
                "Content-Length": str(file_record.file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.delete("/{file_id}", response_model=FileDeleteResponse, status_code=status.HTTP_200_OK)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Soft delete a file (marks as deleted, doesn't remove from storage).
    
    Only the file uploader or organization admin can delete files.
    """
    try:
        file_service = FileService(db)
        file_service.delete_file(file_id, current_user.user_id)
        
        return FileDeleteResponse(
            status="success",
            message="File deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File delete error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.patch("/{file_id}/access", response_model=FileAccessUpdateResponse, status_code=status.HTTP_200_OK)
def update_access_level(
    file_id: int,
    access_data: FileAccessUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update file access level.
    
    Only the file uploader or organization admin can update access level.
    """
    try:
        file_service = FileService(db)
        file_record = file_service.update_access_level(
            file_id=file_id,
            access_level=access_data.access_level,
            user_id=current_user.user_id
        )
        
        file_response = FileResponse.model_validate(file_record)
        
        return FileAccessUpdateResponse(
            status="success",
            message="Access level updated successfully",
            data=file_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update access level error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update access level: {str(e)}"
        )


@router.get("/{file_id}/url", response_model=PresignedUrlResponse, status_code=status.HTTP_200_OK)
def get_presigned_url(
    file_id: int,
    expires_in: int = 3600,
    db: Session = Depends(get_db)
):
    """
    Get presigned URL for direct S3 access.
    
    This allows direct access to the file from S3 without going through the API.
    Useful for large files or direct browser downloads.
    
    **Note**: Only works with S3 storage. Returns None for local storage.
    """
    try:
        file_service = FileService(db)
        url = file_service.generate_presigned_url(file_id, expiration=expires_in)
        
        if not url:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Presigned URLs are not supported for local storage"
            )
        
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        return PresignedUrlResponse(
            status="success",
            data={
                "url": url,
                "expires_at": expires_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate presigned URL error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )

