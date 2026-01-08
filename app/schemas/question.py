from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict
from app.schemas.file import FileResponse


class QuestionCreate(BaseModel):
    project_id: str = Field(..., description="Project reference ID this question is associated with")
    asked_by: str = Field(..., max_length=255, description="Identifier of the user (lender) asking the question")
    question_text: str = Field(..., description="Question text")
    category: Optional[str] = Field(None, max_length=100, description="Category of the question (financial, compliance, timeline, etc.)")
    priority: Optional[str] = Field("normal", max_length=20, description="Priority of the question: low, normal, high, urgent")
    attachments: Optional[List] = Field(default_factory=list, description="List of attachment metadata or file identifiers")

    model_config = ConfigDict(from_attributes=True)


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = Field(None, description="Updated question text")
    category: Optional[str] = Field(None, max_length=100, description="Updated category")
    priority: Optional[str] = Field(None, max_length=20, description="Updated priority")
    attachments: Optional[List] = Field(None, description="Updated list of attachments")
    status: Optional[str] = Field(None, description="Updated status: draft, open, answered, closed")

    model_config = ConfigDict(from_attributes=True)


class QuestionReplyDocumentResponse(BaseModel):
    """Response schema for question reply document"""
    id: int
    question_reply_id: int
    file_id: int
    uploaded_by: str
    file: Optional[FileResponse] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class QuestionAnswerResponse(BaseModel):
    id: int
    question_id: int
    replied_by_user_id: str
    reply_text: str
    documents: List[QuestionReplyDocumentResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class QuestionResponse(BaseModel):
    id: int
    project_id: str
    asked_by: str
    question_text: str
    category: Optional[str] = None
    attachments: List = Field(default_factory=list)
    status: str
    is_public: bool
    priority: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    answer: Optional[QuestionAnswerResponse] = Field(
        None, description="Answer to this question if provided"
    )

    model_config = ConfigDict(from_attributes=True)


class QuestionListResponse(BaseModel):
    status: str
    message: str
    data: List[QuestionResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


