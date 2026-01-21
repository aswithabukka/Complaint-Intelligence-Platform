import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class ComplaintStatus(str, PyEnum):
    PENDING = "pending"              # Initial state
    PROCESSING = "processing"        # Documents being processed
    SUMMARIZING = "summarizing"      # AI generating summary
    PENDING_ACTION = "pending_action"  # Summary complete, awaiting action
    IN_PROGRESS = "in_progress"      # Team is working on it
    RESOLVED = "resolved"            # Issue resolved
    COMPLETED = "completed"          # Fully completed/closed
    FAILED = "failed"                # Processing failed


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref = Column(String(100), unique=True, index=True, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(ComplaintStatus, values_callable=lambda x: [e.value for e in x]),
        default=ComplaintStatus.PENDING,
        nullable=False
    )
    overall_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    documents = relationship(
        "Document",
        back_populates="complaint",
        cascade="all, delete-orphan"
    )
    summaries = relationship(
        "Summary",
        back_populates="complaint",
        cascade="all, delete-orphan",
        foreign_keys="Summary.complaint_id"
    )
