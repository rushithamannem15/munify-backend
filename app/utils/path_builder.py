"""
Path Builder Utility for generating hierarchical S3 paths.

This module provides type-safe enums and builder methods for generating
consistent S3 folder structures based on file category and document type.
"""
from enum import Enum
from typing import Optional


class FileCategory(str, Enum):
    """File category types"""
    KYC = "KYC"
    PROJECT = "Project"
    ADDITIONAL = "Additional"


class KYCDocumentType(str, Enum):
    """KYC document types"""
    PAN = "PAN"
    GST = "GST"


class ProjectDocumentType(str, Enum):
    """Project document types"""
    DPR = "DPR"
    PROJECT_IMAGE = "Project Image"
    PROJECT_VIDEOS = "Project videos"


class AdditionalDocumentType(str, Enum):
    """Additional document types"""
    COMMITMENT = "commitment"
    REQUESTED_DOCUMENT = "Requested document"
    QANDA = "QandA"


class PathBuilder:
    """Builder class for generating hierarchical S3 paths"""
    
    @staticmethod
    def build_kyc_path(
        org_id: str,
        document_type: KYCDocumentType,
        filename: str
    ) -> str:
        """
        Build path for KYC documents.
        
        Structure: {org_id}/KYC/{document_type}/{filename}
        
        Args:
            org_id: Organization ID
            document_type: KYC document type (PAN or GST)
            filename: Generated filename
            
        Returns:
            S3 path string
        """
        return f"{org_id}/KYC/{document_type.value}/{filename}"
    
    @staticmethod
    def build_project_path(
        org_id: str,
        project_reference_id: str,
        document_type: ProjectDocumentType,
        filename: str
    ) -> str:
        """
        Build path for project documents.
        
        Structure: {org_id}/Project/{project_reference_id}/{document_type}/{filename}
        
        Args:
            org_id: Organization ID
            project_reference_id: Project reference ID
            document_type: Project document type
            filename: Generated filename
            
        Returns:
            S3 path string
        """
        return f"{org_id}/Project/{project_reference_id}/{document_type.value}/{filename}"
    
    @staticmethod
    def build_additional_path(
        org_id: str,
        project_reference_id: str,
        document_type: AdditionalDocumentType,
        filename: str,
        question_reply_id: Optional[int] = None
    ) -> str:
        """
        Build path for additional documents.
        
        Structure: {org_id}/Additional/{project_reference_id}/{document_type}/{filename}
        For QandA: {org_id}/Additional/{project_reference_id}/QandA/{question_reply_id}/{filename}
        
        Args:
            org_id: Organization ID
            project_reference_id: Project reference ID
            document_type: Additional document type
            filename: Generated filename
            question_reply_id: Optional Question Reply ID (for QandA documents)
            
        Returns:
            S3 path string
        """
        if document_type == AdditionalDocumentType.QANDA and question_reply_id is not None:
            return f"{org_id}/Additional/{project_reference_id}/{document_type.value}/{question_reply_id}/{filename}"
        return f"{org_id}/Additional/{project_reference_id}/{document_type.value}/{filename}"
    
    @staticmethod
    def build_path(
        org_id: str,
        file_category: FileCategory,
        filename: str,
        document_type: str,
        project_reference_id: Optional[str] = None
    ) -> str:
        """
        Generic path builder that routes to appropriate builder method.
        
        Args:
            org_id: Organization ID
            file_category: File category (KYC, Project, Additional)
            filename: Generated filename
            document_type: Document type as string
            project_reference_id: Project reference ID (required for Project/Additional)
            
        Returns:
            S3 path string
            
        Raises:
            ValueError: If invalid category or missing required parameters
        """
        if file_category == FileCategory.KYC:
            try:
                kyc_type = KYCDocumentType(document_type)
                return PathBuilder.build_kyc_path(org_id, kyc_type, filename)
            except ValueError:
                raise ValueError(f"Invalid KYC document type: {document_type}")
        
        elif file_category == FileCategory.PROJECT:
            if not project_reference_id:
                raise ValueError("project_reference_id is required for Project category")
            try:
                project_type = ProjectDocumentType(document_type)
                return PathBuilder.build_project_path(
                    org_id, project_reference_id, project_type, filename
                )
            except ValueError:
                raise ValueError(f"Invalid Project document type: {document_type}")
        
        elif file_category == FileCategory.ADDITIONAL:
            if not project_reference_id:
                raise ValueError("project_reference_id is required for Additional category")
            try:
                additional_type = AdditionalDocumentType(document_type)
                return PathBuilder.build_additional_path(
                    org_id, project_reference_id, additional_type, filename
                )
            except ValueError:
                raise ValueError(f"Invalid Additional document type: {document_type}")
        
        else:
            raise ValueError(f"Invalid file category: {file_category}")

