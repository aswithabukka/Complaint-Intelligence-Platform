from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.db.models.complaint import ComplaintStatus


class ComplaintBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    external_ref: Optional[str] = Field(None, max_length=100)


class ComplaintCreate(ComplaintBase):
    pass


class ComplaintUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    external_ref: Optional[str] = Field(None, max_length=100)


class ComplaintInDB(ComplaintBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ComplaintStatus
    overall_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ComplaintResponse(ComplaintInDB):
    documents_count: int = 0
    processed_documents_count: int = 0


class ComplaintListResponse(BaseModel):
    items: List[ComplaintResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DocumentStatusBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    processing_status: str
    processing_progress: Optional[str] = None


class ComplaintStatusResponse(BaseModel):
    id: UUID
    status: ComplaintStatus
    overall_progress: str
    documents: List[DocumentStatusBrief]
