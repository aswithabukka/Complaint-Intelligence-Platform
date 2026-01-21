from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.db.models.document import DocumentType, ProcessingStatus


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_type: DocumentType
    file_size: int
    processing_status: ProcessingStatus
    celery_task_id: Optional[str] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    complaint_id: UUID
    filename: str
    original_filename: str
    file_type: DocumentType
    mime_type: Optional[str] = None
    file_size: int
    processing_status: ProcessingStatus
    processing_progress: Optional[str] = None
    error_message: Optional[str] = None
    has_extracted_text: bool = False
    has_summary: bool = False
    created_at: datetime
    updated_at: datetime


class DocumentStatusResponse(BaseModel):
    id: UUID
    processing_status: ProcessingStatus
    processing_progress: Optional[str] = None
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None


class DocumentTextResponse(BaseModel):
    id: UUID
    filename: str
    extracted_text: Optional[str] = None
    character_count: int = 0


class BulkUploadResponse(BaseModel):
    uploaded: List[DocumentUploadResponse]
    failed: List[dict]  # Contains filename and error
    total_uploaded: int
    total_failed: int


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
