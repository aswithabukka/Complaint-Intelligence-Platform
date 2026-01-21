from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.schemas.document import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentTextResponse,
    BulkUploadResponse,
    DocumentListResponse,
)
from app.api.v1.schemas.common import SuccessResponse
from app.services.document_service import DocumentService
from app.services.complaint_service import ComplaintService
from app.core.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.doc', '.docx', '.xls', '.xlsx'}


@router.post(
    "/complaints/{complaint_id}/documents",
    response_model=BulkUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload documents to a complaint"
)
async def upload_documents(
    complaint_id: UUID,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload one or more documents to a complaint.

    Supported formats:
    - PDF (.pdf)
    - Images (.png, .jpg, .jpeg, .tiff)
    - Word documents (.doc, .docx)
    - Excel spreadsheets (.xls, .xlsx)

    Max file size: 50MB per file
    """
    # Verify complaint exists
    complaint_service = ComplaintService(db)
    complaint = await complaint_service.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )

    doc_service = DocumentService(db)

    uploaded = []
    failed = []

    for file in files:
        try:
            # Validate file extension
            ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            if ext not in ALLOWED_EXTENSIONS:
                failed.append({
                    "filename": file.filename,
                    "error": f"Unsupported file type: {ext}"
                })
                continue

            # Read and validate file size
            content = await file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE:
                failed.append({
                    "filename": file.filename,
                    "error": f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
                })
                continue

            # Process upload
            doc = await doc_service.upload_document(complaint_id, file, content)
            uploaded.append(doc)

        except ValueError as e:
            failed.append({
                "filename": file.filename,
                "error": str(e)
            })
        except Exception as e:
            failed.append({
                "filename": file.filename,
                "error": f"Upload failed: {str(e)}"
            })

    return BulkUploadResponse(
        uploaded=uploaded,
        failed=failed,
        total_uploaded=len(uploaded),
        total_failed=len(failed)
    )


@router.get(
    "/complaints/{complaint_id}/documents",
    response_model=DocumentListResponse,
    summary="List complaint documents"
)
async def list_complaint_documents(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all documents for a specific complaint."""
    # Verify complaint exists
    complaint_service = ComplaintService(db)
    complaint = await complaint_service.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )

    doc_service = DocumentService(db)
    documents = await doc_service.get_documents_by_complaint(complaint_id)

    items = [await doc_service.get_response(doc) for doc in documents]

    return DocumentListResponse(
        items=items,
        total=len(items)
    )


@router.get(
    "/complaints/{complaint_id}/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details"
)
async def get_document(
    complaint_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific document."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id)
    if not document or document.complaint_id != complaint_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    return await service.get_response(document)


@router.delete(
    "/complaints/{complaint_id}/documents/{document_id}",
    response_model=SuccessResponse,
    summary="Delete a document"
)
async def delete_document(
    complaint_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id)
    if not document or document.complaint_id != complaint_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    deleted = await service.delete(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    return SuccessResponse(message=f"Document {document_id} deleted successfully")


@router.get(
    "/complaints/{complaint_id}/documents/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document processing status"
)
async def get_document_status(
    complaint_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the current processing status of a document."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id)
    if not document or document.complaint_id != complaint_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    status_response = await service.get_processing_status(document_id)
    if not status_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    return status_response


@router.get(
    "/complaints/{complaint_id}/documents/{document_id}/text",
    response_model=DocumentTextResponse,
    summary="Get extracted text"
)
async def get_document_text(
    complaint_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the extracted text content from a document."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id)
    if not document or document.complaint_id != complaint_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    return DocumentTextResponse(
        id=document.id,
        filename=document.original_filename,
        extracted_text=document.extracted_text,
        character_count=len(document.extracted_text) if document.extracted_text else 0
    )


@router.get(
    "/complaints/{complaint_id}/documents/{document_id}/download",
    summary="Download original document"
)
async def download_document(
    complaint_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download the original uploaded document."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id)
    if not document or document.complaint_id != complaint_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    if not service.storage.file_exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage"
        )

    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type or "application/octet-stream"
    )
