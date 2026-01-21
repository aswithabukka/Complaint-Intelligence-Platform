from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
    ComplaintListResponse,
    ComplaintStatusResponse,
)
from app.api.v1.schemas.common import SuccessResponse
from app.services.complaint_service import ComplaintService
from app.services.document_service import DocumentService

router = APIRouter()


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new complaint"
)
async def create_complaint(
    complaint_in: ComplaintCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new complaint record."""
    service = ComplaintService(db)
    complaint = await service.create(complaint_in)
    return await service.get_response(complaint)


@router.get(
    "",
    response_model=ComplaintListResponse,
    summary="List all complaints"
)
async def list_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db)
):
    """List complaints with pagination and optional status filter."""
    service = ComplaintService(db)
    return await service.list_paginated(page, page_size, status_filter)


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Get complaint details"
)
async def get_complaint(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific complaint."""
    service = ComplaintService(db)
    complaint = await service.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )
    return await service.get_response(complaint)


@router.put(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Update a complaint"
)
async def update_complaint(
    complaint_id: UUID,
    complaint_in: ComplaintUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a complaint's details."""
    service = ComplaintService(db)
    complaint = await service.update(complaint_id, complaint_in)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )
    return await service.get_response(complaint)


@router.delete(
    "/{complaint_id}",
    response_model=SuccessResponse,
    summary="Delete a complaint"
)
async def delete_complaint(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a complaint and all its associated documents."""
    service = ComplaintService(db)
    deleted = await service.delete(complaint_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )
    return SuccessResponse(message=f"Complaint {complaint_id} deleted successfully")


@router.post(
    "/{complaint_id}/process",
    response_model=ComplaintStatusResponse,
    summary="Trigger complaint processing"
)
async def process_complaint(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger the document processing pipeline for a complaint.
    This will:
    1. Extract text from all uploaded documents
    2. Generate individual document summaries
    3. Create an overall complaint summary
    """
    complaint_service = ComplaintService(db)
    doc_service = DocumentService(db)

    complaint = await complaint_service.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )

    # Check if there are documents to process
    documents = await doc_service.get_documents_by_complaint(complaint_id)
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents uploaded for this complaint"
        )

    # Start async processing
    await doc_service.start_processing(complaint_id)

    # Return current status
    return await complaint_service.get_processing_status(complaint_id)


@router.get(
    "/{complaint_id}/status",
    response_model=ComplaintStatusResponse,
    summary="Get complaint processing status"
)
async def get_complaint_status(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the current processing status of a complaint and its documents."""
    service = ComplaintService(db)
    status_response = await service.get_processing_status(complaint_id)
    if not status_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )
    return status_response
