"""
Question Reply Document Model

Mapping table between QuestionReply and PerdixFile for Q&A documents.
"""
from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class QuestionReplyDocument(Base):
    """
    Model for perdix_mp_question_reply_documents
    
    Maps question replies to their associated documents (files).
    This creates a many-to-many relationship between QuestionReply and PerdixFile.
    """
    __tablename__ = "perdix_mp_question_reply_documents"
    
    id = Column(BigInteger, primary_key=True, index=True)
    question_reply_id = Column(
        BigInteger,
        ForeignKey("perdix_mp_question_replies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    file_id = Column(
        BigInteger,
        ForeignKey("perdix_mp_files.id", ondelete="CASCADE"),
        nullable=False
    )
    uploaded_by = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Relationships
    file = relationship("PerdixFile", foreign_keys=[file_id])
    question_reply = relationship(
        "QuestionReply",
        foreign_keys=[question_reply_id],
        back_populates="documents"
    )

