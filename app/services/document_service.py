import os
import uuid
from typing import Optional, List
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.document import Document, DocumentType, ProcessingStatus
from app.db.models.complaint import Complaint, ComplaintStatus
from app.db.models.summary import Summary
from app.services.storage_service import StorageService
from app.api.v1.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentStatusResponse,
)


class DocumentService:
    MIME_TYPE_MAPPING = {
        'application/pdf': DocumentType.PDF,
        'image/png': DocumentType.IMAGE,
        'image/jpeg': DocumentType.IMAGE,
        'image/tiff': DocumentType.IMAGE,
        'application/msword': DocumentType.DOC,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocumentType.DOCX,
        'application/vnd.ms-excel': DocumentType.XLS,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': DocumentType.XLSX,
    }

    EXTENSION_MAPPING = {
        '.pdf': DocumentType.PDF,
        '.png': DocumentType.IMAGE,
        '.jpg': DocumentType.IMAGE,
        '.jpeg': DocumentType.IMAGE,
        '.tiff': DocumentType.IMAGE,
        '.tif': DocumentType.IMAGE,
        '.doc': DocumentType.DOC,
        '.docx': DocumentType.DOCX,
        '.xls': DocumentType.XLS,
        '.xlsx': DocumentType.XLSX,
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageService()

    async def upload_document(
        self,
        complaint_id: UUID,
        file: UploadFile,
        content: bytes
    ) -> DocumentUploadResponse:
        # Verify complaint exists
        complaint = await self.db.get(Complaint, complaint_id)
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found")

        # Determine file type
        file_type = self._get_file_type(file.content_type, file.filename)

        # Generate unique filename
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"

        # Save file
        file_path = await self.storage.save_file(
            content,
            unique_filename,
            str(complaint_id)
        )

        # Create document record
        document = Document(
            complaint_id=complaint_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_type=file_type,
            mime_type=file.content_type,
            file_size=len(content),
            processing_status=ProcessingStatus.PENDING
        )

        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            file_type=document.file_type,
            file_size=document.file_size,
            processing_status=document.processing_status,
            celery_task_id=document.celery_task_id
        )

    def _get_file_type(self, mime_type: str, filename: str) -> DocumentType:
        # Try MIME type first
        if mime_type and mime_type in self.MIME_TYPE_MAPPING:
            return self.MIME_TYPE_MAPPING[mime_type]

        # Fall back to extension
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.EXTENSION_MAPPING:
            return self.EXTENSION_MAPPING[ext]

        raise ValueError(f"Unsupported file type: {ext}")

    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        query = (
            select(Document)
            .options(selectinload(Document.summary))
            .where(Document.id == document_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_documents_by_complaint(self, complaint_id: UUID) -> List[Document]:
        query = (
            select(Document)
            .options(selectinload(Document.summary))
            .where(Document.complaint_id == complaint_id)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete(self, document_id: UUID) -> bool:
        document = await self.get_by_id(document_id)
        if not document:
            return False

        # Delete file from storage
        await self.storage.delete_file(document.file_path)

        await self.db.delete(document)
        await self.db.commit()
        return True

    async def get_processing_status(self, document_id: UUID) -> Optional[DocumentStatusResponse]:
        document = await self.get_by_id(document_id)
        if not document:
            return None

        return DocumentStatusResponse(
            id=document.id,
            processing_status=document.processing_status,
            processing_progress=document.processing_progress,
            error_message=document.error_message,
            celery_task_id=document.celery_task_id
        )

    async def get_response(self, document: Document) -> DocumentResponse:
        """Convert a Document model to DocumentResponse."""
        return DocumentResponse(
            id=document.id,
            complaint_id=document.complaint_id,
            filename=document.filename,
            original_filename=document.original_filename,
            file_type=document.file_type,
            mime_type=document.mime_type,
            file_size=document.file_size,
            processing_status=document.processing_status,
            processing_progress=document.processing_progress,
            error_message=document.error_message,
            has_extracted_text=document.extracted_text is not None,
            has_summary=document.summary is not None,
            created_at=document.created_at,
            updated_at=document.updated_at
        )

    async def start_processing(self, complaint_id: UUID):
        """Start async processing for all documents in a complaint."""
        from app.workers.tasks.document_tasks import process_complaint_documents

        # Trigger the Celery task
        task = process_complaint_documents.delay(str(complaint_id))

        return task.id
