import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, DateTime, Enum, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class DocumentType(str, PyEnum):
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
    DOC = "doc"
    XLS = "xls"
    XLSX = "xlsx"


class ProcessingStatus(str, PyEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(Enum(DocumentType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=False)  # In bytes
    extracted_text = Column(Text, nullable=True)
    processing_status = Column(
        Enum(ProcessingStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProcessingStatus.PENDING,
        nullable=False
    )
    processing_progress = Column(String(50), default="0%", nullable=True)
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    complaint = relationship("Complaint", back_populates="documents")
    summary = relationship(
        "Summary",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan"
    )
