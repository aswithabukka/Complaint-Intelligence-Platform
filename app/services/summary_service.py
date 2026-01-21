from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.document import Document
from app.db.models.summary import Summary, SummaryType
from app.db.models.complaint import Complaint
from app.api.v1.schemas.summary import (
    SummaryResponse,
    DocumentSummaryResponse,
    OverallSummaryResponse,
)


class SummaryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_document_summary(self, document_id: UUID) -> Optional[DocumentSummaryResponse]:
        """Get summary for a specific document."""
        query = (
            select(Summary)
            .where(
                Summary.document_id == document_id,
                Summary.summary_type == SummaryType.DOCUMENT
            )
        )
        result = await self.db.execute(query)
        summary = result.scalar_one_or_none()

        if not summary:
            return None

        # Get document info
        document = await self.db.get(Document, document_id)

        return DocumentSummaryResponse(
            id=summary.id,
            summary_type=summary.summary_type,
            content=summary.content,
            tokens_used=summary.tokens_used,
            model_used=summary.model_used,
            created_at=summary.created_at,
            document_id=document_id,
            document_filename=document.original_filename if document else "Unknown"
        )

    async def get_complaint_summary(self, complaint_id: UUID) -> Optional[OverallSummaryResponse]:
        """Get overall summary for a complaint with all document summaries."""
        # Get complaint
        complaint = await self.db.get(Complaint, complaint_id)
        if not complaint:
            return None

        # Get all document summaries
        query = (
            select(Summary, Document)
            .join(Document, Summary.document_id == Document.id)
            .where(
                Document.complaint_id == complaint_id,
                Summary.summary_type == SummaryType.DOCUMENT
            )
        )
        result = await self.db.execute(query)
        doc_summaries = result.all()

        document_summaries = [
            DocumentSummaryResponse(
                id=summary.id,
                summary_type=summary.summary_type,
                content=summary.content,
                tokens_used=summary.tokens_used,
                model_used=summary.model_used,
                created_at=summary.created_at,
                document_id=doc.id,
                document_filename=doc.original_filename
            )
            for summary, doc in doc_summaries
        ]

        # Get total document count
        doc_count_query = select(Document).where(Document.complaint_id == complaint_id)
        doc_result = await self.db.execute(doc_count_query)
        total_docs = len(doc_result.scalars().all())

        # Get overall summary creation time
        overall_query = select(Summary).where(
            Summary.complaint_id == complaint_id,
            Summary.summary_type == SummaryType.OVERALL
        )
        overall_result = await self.db.execute(overall_query)
        overall_summary = overall_result.scalar_one_or_none()

        return OverallSummaryResponse(
            complaint_id=complaint_id,
            complaint_title=complaint.title,
            overall_summary=complaint.overall_summary,
            document_summaries=document_summaries,
            total_documents=total_docs,
            summarized_documents=len(document_summaries),
            generated_at=overall_summary.created_at if overall_summary else None
        )

    async def regenerate_summaries(self, complaint_id: UUID) -> str:
        """Trigger regeneration of all summaries for a complaint."""
        from app.workers.tasks.summary_tasks import regenerate_complaint_summaries_task

        task = regenerate_complaint_summaries_task.delay(str(complaint_id))
        return task.id
