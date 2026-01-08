"""
File Service - Business logic for file operations

Handles file upload, download, metadata management, and access control.
"""
import uuid
import os
from typing import Tuple, Optional
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.perdix_file import PerdixFile
from app.services.storage import get_storage_service, StorageServiceInterface
from app.utils.path_builder import (
    PathBuilder,
    FileCategory,
    KYCDocumentType,
    ProjectDocumentType,
    AdditionalDocumentType
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("services.file")


class FileService:
    """Service for file operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage_service: StorageServiceInterface = get_storage_service()
        self.max_file_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = [
            ext.strip().lower() 
            for ext in settings.ALLOWED_EXTENSIONS.split(",")
        ]
    
    def _validate_file(self, file: UploadFile) -> None:
        """Validate file size and extension"""
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Check file extension
        if file.filename:
            file_ext = os.path.splitext(file.filename)[1].lstrip('.').lower()
            if file_ext not in self.allowed_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}"
                )
    
    def _generate_filename(self, original_filename: str) -> str:
        """Generate unique filename"""
        # Extract extension
        _, ext = os.path.splitext(original_filename)
        
        # Generate unique filename: UUID + timestamp
        unique_id = str(uuid.uuid4()).replace('-', '')
        timestamp = int(datetime.now().timestamp())
        filename = f"{unique_id}_{timestamp}{ext}"
        
        return filename
    
    def _build_storage_path(
        self,
        org_id: str,
        file_category: str,
        document_type: str,
        filename: str,
        project_reference_id: Optional[str] = None,
        question_reply_id: Optional[int] = None
    ) -> str:
        """Build storage path using PathBuilder"""
        try:
            category_enum = FileCategory(file_category)
            # For Additional category with QANDA document type, use build_additional_path directly
            if category_enum == FileCategory.ADDITIONAL and document_type == "QandA" and question_reply_id is not None:
                return PathBuilder.build_additional_path(
                    org_id=org_id,
                    project_reference_id=project_reference_id,
                    document_type=AdditionalDocumentType.QANDA,
                    filename=filename,
                    question_reply_id=question_reply_id
                )
            return PathBuilder.build_path(
                org_id=org_id,
                file_category=category_enum,
                filename=filename,
                document_type=document_type,
                project_reference_id=project_reference_id
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    def upload_file(
        self,
        file: UploadFile,
        organization_id: str,
        uploaded_by: str,
        file_category: str,
        document_type: str,
        access_level: str = 'private',
        project_reference_id: Optional[str] = None,
        question_reply_id: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> PerdixFile:
        """
        Upload file to storage and create database record.
        
        Args:
            file: UploadFile object
            organization_id: Organization ID
            uploaded_by: User ID who uploaded the file
            file_category: File category (KYC, Project, Additional)
            document_type: Document type
            access_level: Access level (public, restricted, private)
            project_reference_id: Project reference ID (required for Project/Additional)
            created_by: User ID for audit trail
            
        Returns:
            PerdixFile model instance
        """
        # Validate file
        self._validate_file(file)
        
        # Read file content
        file_bytes = file.file.read()
        
        # Generate filename
        generated_filename = self._generate_filename(file.filename or "file")
        
        # Build storage path
        storage_path = self._build_storage_path(
            org_id=organization_id,
            file_category=file_category,
            document_type=document_type,
            filename=generated_filename,
            project_reference_id=project_reference_id,
            question_reply_id=question_reply_id
        )
        
        # Upload to storage
        try:
            storage_path, checksum = self.storage_service.upload_file(
                file_bytes=file_bytes,
                storage_path=storage_path,
                content_type=file.content_type or "application/octet-stream"
            )
        except Exception as e:
            logger.error(f"Storage upload failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )
        
        # Create database record
        try:
            perdix_file = PerdixFile(
                organization_id=organization_id,
                uploaded_by=uploaded_by,
                filename=generated_filename,
                original_filename=file.filename or "file",
                mime_type=file.content_type or "application/octet-stream",
                file_size=len(file_bytes),
                storage_path=storage_path,
                checksum=checksum,
                access_level=access_level,
                download_count=0,
                is_deleted=False,
                created_by=created_by or uploaded_by,
                updated_by=created_by or uploaded_by
            )
            
            self.db.add(perdix_file)
            self.db.commit()
            self.db.refresh(perdix_file)
            
            logger.info(f"File uploaded successfully: {perdix_file.id}")
            return perdix_file
            
        except Exception as e:
            self.db.rollback()
            # Try to delete from storage if DB insert fails
            try:
                self.storage_service.delete_file(storage_path)
            except:
                pass
            
            logger.error(f"Database insert failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file metadata: {str(e)}"
            )
    
    def download_file(
        self,
        file_id: int,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Tuple[bytes, PerdixFile]:
        """
        Download file from storage.
        
        Args:
            file_id: File ID
            user_id: User ID for access control
            organization_id: Organization ID for access control
            
        Returns:
            Tuple of (file_bytes, PerdixFile)
        """
        # Get file metadata
        file_record = self.get_file_metadata(file_id)
        
        # Check if file is deleted
        if file_record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Access control check
        self._check_access(file_record, user_id, organization_id)
        
        # Download from storage
        try:
            file_bytes = self.storage_service.download_file(file_record.storage_path)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage"
            )
        except Exception as e:
            logger.error(f"Storage download failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}"
            )
        
        # Increment download count
        self.increment_download_count(file_id)
        
        return file_bytes, file_record
    
    def get_file_metadata(self, file_id: int) -> PerdixFile:
        """Get file metadata by ID"""
        file_record = self.db.query(PerdixFile).filter(
            PerdixFile.id == file_id,
            PerdixFile.is_deleted == False
        ).first()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID {file_id} not found"
            )
        
        return file_record
    
    def delete_file(self, file_id: int, user_id: str) -> bool:
        """
        Soft delete file (mark as deleted, don't remove from storage).
        
        Args:
            file_id: File ID
            user_id: User ID performing the deletion
            
        Returns:
            True if deleted successfully
        """
        file_record = self.get_file_metadata(file_id)
        
        # Check access (user must be uploader or org admin)
        if file_record.uploaded_by != user_id:
            # TODO: Add organization admin check
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this file"
            )
        
        try:
            file_record.is_deleted = True
            file_record.deleted_at = datetime.now()
            file_record.updated_by = user_id
            
            self.db.commit()
            logger.info(f"File soft deleted: {file_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}"
            )
    
    def update_access_level(
        self,
        file_id: int,
        access_level: str,
        user_id: str
    ) -> PerdixFile:
        """Update file access level"""
        file_record = self.get_file_metadata(file_id)
        
        # Validate access level
        if access_level not in ['public', 'restricted', 'private']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid access level. Must be: public, restricted, or private"
            )
        
        # Check permission (user must be uploader or org admin)
        if file_record.uploaded_by != user_id:
            # TODO: Add organization admin check
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this file"
            )
        
        try:
            file_record.access_level = access_level
            file_record.updated_by = user_id
            
            self.db.commit()
            self.db.refresh(file_record)
            
            logger.info(f"File access level updated: {file_id} -> {access_level}")
            return file_record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update access level: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update access level: {str(e)}"
            )
    
    def increment_download_count(self, file_id: int) -> None:
        """Increment download count for file"""
        try:
            file_record = self.db.query(PerdixFile).filter(
                PerdixFile.id == file_id
            ).first()
            
            if file_record:
                file_record.download_count += 1
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Failed to increment download count: {str(e)}")
            # Don't raise exception, this is not critical
    
    def _check_access(
        self,
        file_record: PerdixFile,
        user_id: Optional[str],
        organization_id: Optional[str]
    ) -> None:
        """Check if user has access to file"""
        # Public files are accessible to everyone
        if file_record.access_level == 'public':
            return
        
        # Private files: only uploader or org admin
        if file_record.access_level == 'private':
            if user_id and file_record.uploaded_by == user_id:
                return
            if organization_id and file_record.organization_id == organization_id:
                # TODO: Add org admin check
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this file"
            )
        
        # Restricted files: organization members
        if file_record.access_level == 'restricted':
            if organization_id and file_record.organization_id == organization_id:
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this file"
            )
    
    def generate_presigned_url(
        self,
        file_id: int,
        expiration: int = 3600
    ) -> Optional[str]:
        """Generate presigned URL for direct S3 access"""
        file_record = self.get_file_metadata(file_id)
        
        if file_record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        url = self.storage_service.generate_presigned_url(
            file_record.storage_path,
            expiration=expiration
        )
        
        return url

