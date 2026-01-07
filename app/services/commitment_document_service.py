"""
Commitment Document Service - Business logic for commitment document operations

Handles file upload and deletion for commitment documents, linking files
to commitments via the perdix_mp_commitment_documents table.
"""
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.models.commitment_document import CommitmentDocument
from app.models.commitment import Commitment
from app.services.file_service import FileService
from app.core.logging import get_logger

logger = get_logger("services.commitment_document")


class CommitmentDocumentService:
    """Service for commitment document operations"""
    
    # Valid document types for commitments
    VALID_DOCUMENT_TYPES = [
        "sanction_letter",
        "approval_note",
        "kyc",
        "terms_sheet",
        "due_diligence"
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService(db)
    
    def _validate_document_type(self, document_type: str):
        """Validate document type"""
        if document_type not in self.VALID_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid document type. Must be one of: {', '.join(self.VALID_DOCUMENT_TYPES)}"
            )
    
    def _get_commitment_or_404(self, commitment_id: int) -> Commitment:
        """Get commitment by ID or raise 404"""
        commitment = self.db.query(Commitment).filter(Commitment.id == commitment_id).first()
        if not commitment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Commitment with ID {commitment_id} not found"
            )
        return commitment
    
    # Note: _map_document_type_for_file_service removed as we now use
    # "commitment" as the document_type for FileService (Additional category)
    # The actual commitment document type (sanction_letter, etc.) is stored
    # in the commitment_documents table, not in the file path
    
    def upload_commitment_file(
        self,
        file: UploadFile,
        commitment_id: int,
        document_type: str,
        uploaded_by: str,
        organization_id: Optional[str] = None,
        access_level: str = "private",
        is_required: bool = True,
        created_by: Optional[str] = None,
        version: int = 1
    ) -> CommitmentDocument:
        """
        Upload a file for a commitment.
        
        Args:
            file: File to upload
            commitment_id: Commitment ID
            document_type: Document type (sanction_letter, approval_note, kyc, terms_sheet, due_diligence)
            uploaded_by: User ID who uploaded the file
            organization_id: Organization ID
            access_level: Access level (public, restricted, private)
            is_required: Whether this document is required
            created_by: User who created the record (defaults to uploaded_by)
            version: Document version (default: 1)
            
        Returns:
            CommitmentDocument model instance
        """
        logger.info(f"Uploading commitment file: {document_type} for commitment {commitment_id}")
        
        try:
            # Validate document type
            self._validate_document_type(document_type)
            
            # Verify commitment exists
            commitment = self._get_commitment_or_404(commitment_id)
            
            # Get organization_id from commitment if not provided
            if not organization_id:
                organization_id = commitment.organization_id
            
            # Get project_reference_id from commitment
            # commitment.project_id is the project_reference_id (string)
            project_reference_id = commitment.project_id
            
            # For commitment documents, use "Additional" category with "commitment" as document_type
            # Path structure: {org_id}/Additional/{project_reference_id}/commitment/{filename}
            perdix_file = self.file_service.upload_file(
                file=file,
                organization_id=organization_id,
                uploaded_by=uploaded_by,
                file_category="Additional",  # Using Additional category for commitment documents
                document_type="commitment",  # This maps to AdditionalDocumentType.COMMITMENT
                access_level=access_level,
                project_reference_id=project_reference_id,  # Required for Additional category
                created_by=created_by or uploaded_by
            )
            
            # Create commitment document record
            commitment_document = CommitmentDocument(
                commitment_id=commitment_id,
                file_id=perdix_file.id,
                document_type=document_type,
                is_required=is_required,
                uploaded_by=uploaded_by,
                created_by=created_by or uploaded_by,
                updated_by=created_by or uploaded_by
            )
            
            self.db.add(commitment_document)
            self.db.commit()
            self.db.refresh(commitment_document)
            
            logger.info(f"Commitment document {commitment_document.id} created successfully for commitment {commitment_id}")
            return commitment_document
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error uploading commitment file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload commitment file: {str(e)}"
            )
    
    def delete_commitment_file(
        self,
        file_id: int,
        user_id: str,
        commitment_id: Optional[int] = None
    ) -> bool:
        """
        Delete a commitment file by file_id.
        
        This method:
        1. Finds the commitment document record by file_id
        2. Optionally validates it belongs to the specified commitment
        3. Deletes the commitment document record
        4. Soft deletes the file using FileService
        
        Args:
            file_id: File ID to delete
            user_id: User ID performing the deletion
            commitment_id: Optional commitment ID for validation
            
        Returns:
            True if deleted successfully
        """
        logger.info(f"Deleting commitment file: {file_id}")
        
        try:
            # Find commitment document by file_id
            commitment_document = self.db.query(CommitmentDocument).filter(
                CommitmentDocument.file_id == file_id
            ).first()
            
            if not commitment_document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Commitment document with file_id {file_id} not found"
                )
            
            # Validate it belongs to the specified commitment if provided
            if commitment_id and commitment_document.commitment_id != commitment_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"File {file_id} does not belong to commitment {commitment_id}"
                )
            
            # Check if user has permission (uploaded_by or admin)
            if commitment_document.uploaded_by != user_id:
                # TODO: Add admin check here if needed
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the user who uploaded the file can delete it"
                )
            
            # Delete commitment document record
            commitment_doc_id = commitment_document.id
            self.db.delete(commitment_document)
            
            # Soft delete file using FileService
            self.file_service.delete_file(file_id, user_id)
            
            self.db.commit()
            logger.info(f"Commitment document {commitment_doc_id} and file {file_id} deleted successfully")
            return True
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting commitment file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete commitment file: {str(e)}"
            )
    
    def get_commitment_documents(
        self,
        commitment_id: int,
        document_type: Optional[str] = None
    ) -> list[CommitmentDocument]:
        """
        Get all commitment documents for a commitment with file details.
        
        Args:
            commitment_id: Commitment ID
            document_type: Optional document type filter
            
        Returns:
            List of CommitmentDocument instances with file relationship loaded
        """
        from app.models.perdix_file import PerdixFile
        
        # Join with perdix_mp_files to get file details
        query = (
            self.db.query(CommitmentDocument)
            .join(PerdixFile, CommitmentDocument.file_id == PerdixFile.id)
            .filter(
                CommitmentDocument.commitment_id == commitment_id,
                PerdixFile.is_deleted == False  # Only include non-deleted files
            )
        )
        
        if document_type:
            self._validate_document_type(document_type)
            query = query.filter(CommitmentDocument.document_type == document_type)
        
        # Eager load file relationship
        documents = query.options(
            joinedload(CommitmentDocument.file)
        ).order_by(CommitmentDocument.created_at.desc()).all()
        
        return documents

