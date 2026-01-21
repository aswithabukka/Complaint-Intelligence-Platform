from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.schemas.summary import (
    DocumentSummaryResponse,
    OverallSummaryResponse,
)
from app.api.v1.schemas.common import SuccessResponse
from app.services.summary_service import SummaryService
from app.services.complaint_service import ComplaintService
from app.services.document_service import DocumentService

router = APIRouter()


@router.get(
    "/complaints/{complaint_id}/summary",
    response_model=OverallSummaryResponse,
    summary="Get overall complaint summary"
)
async def get_complaint_summary(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the overall summary for a complaint.
    Includes the combined summary and all individual document summaries.
    """
    # Verify complaint exists
    complaint_service = ComplaintService(db)
    complaint = await complaint_service.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )

    summary_service = SummaryService(db)
    summary_response = await summary_service.get_complaint_summary(complaint_id)

    return summary_response


@router.get(
    "/documents/{document_id}/summary",
    response_model=DocumentSummaryResponse,
    summary="Get document summary"
)
async def get_document_summary(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the summary for a specific document."""
    # Verify document exists
    doc_service = DocumentService(db)
    document = await doc_service.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    summary_service = SummaryService(db)
    summary = await summary_service.get_document_summary(document_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No summary found for document {document_id}"
        )

    return summary


@router.post(
    "/complaints/{complaint_id}/regenerate-summary",
    response_model=SuccessResponse,
    summary="Regenerate summaries"
)
async def regenerate_summaries(
    complaint_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate all summaries for a complaint.
    This will re-run the LLM summarization on all documents
    and generate a new overall summary.
    """
    # Verify complaint exists
    complaint_service = ComplaintService(db)
    complaint = await complaint_service.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint {complaint_id} not found"
        )

    # Check if there are documents with extracted text
    doc_service = DocumentService(db)
    documents = await doc_service.get_documents_by_complaint(complaint_id)
    docs_with_text = [d for d in documents if d.extracted_text]

    if not docs_with_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents with extracted text to summarize"
        )

    # Trigger regeneration
    summary_service = SummaryService(db)
    task_id = await summary_service.regenerate_summaries(complaint_id)

    return SuccessResponse(
        message=f"Summary regeneration started for complaint {complaint_id}",
        data={"task_id": task_id, "documents_to_summarize": len(docs_with_text)}
    )
