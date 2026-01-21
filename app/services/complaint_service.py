from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.complaint import Complaint, ComplaintStatus
from app.db.models.document import Document, ProcessingStatus
from app.api.v1.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
    ComplaintListResponse,
    ComplaintStatusResponse,
    DocumentStatusBrief,
)


class ComplaintService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, complaint_in: ComplaintCreate) -> Complaint:
        complaint = Complaint(**complaint_in.model_dump())
        self.db.add(complaint)
        await self.db.commit()
        await self.db.refresh(complaint)
        return complaint

    async def get_by_id(self, complaint_id: UUID) -> Optional[Complaint]:
        query = (
            select(Complaint)
            .options(selectinload(Complaint.documents))
            .where(Complaint.id == complaint_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        page: int,
        page_size: int,
        status_filter: Optional[str] = None
    ) -> ComplaintListResponse:
        # Base query
        query = select(Complaint)
        count_query = select(func.count(Complaint.id))

        # Apply filter
        if status_filter:
            query = query.where(Complaint.status == status_filter)
            count_query = count_query.where(Complaint.status == status_filter)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Complaint.created_at.desc())

        result = await self.db.execute(query)
        complaints = result.scalars().all()

        # Build response with document counts
        items = []
        for complaint in complaints:
            doc_count_query = select(func.count(Document.id)).where(
                Document.complaint_id == complaint.id
            )
            processed_count_query = select(func.count(Document.id)).where(
                Document.complaint_id == complaint.id,
                Document.processing_status == ProcessingStatus.COMPLETED
            )

            doc_count = (await self.db.execute(doc_count_query)).scalar()
            processed_count = (await self.db.execute(processed_count_query)).scalar()

            items.append(ComplaintResponse(
                id=complaint.id,
                title=complaint.title,
                description=complaint.description,
                external_ref=complaint.external_ref,
                status=complaint.status,
                overall_summary=complaint.overall_summary,
                created_at=complaint.created_at,
                updated_at=complaint.updated_at,
                documents_count=doc_count,
                processed_documents_count=processed_count
            ))

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        return ComplaintListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )

    async def update(self, complaint_id: UUID, complaint_in: ComplaintUpdate) -> Optional[Complaint]:
        complaint = await self.get_by_id(complaint_id)
        if not complaint:
            return None

        update_data = complaint_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(complaint, field, value)

        await self.db.commit()
        await self.db.refresh(complaint)
        return complaint

    async def delete(self, complaint_id: UUID) -> bool:
        complaint = await self.get_by_id(complaint_id)
        if not complaint:
            return False

        await self.db.delete(complaint)
        await self.db.commit()
        return True

    async def update_status(self, complaint_id: UUID, status: ComplaintStatus):
        complaint = await self.get_by_id(complaint_id)
        if complaint:
            complaint.status = status
            await self.db.commit()

    async def set_overall_summary(self, complaint_id: UUID, summary: str):
        complaint = await self.get_by_id(complaint_id)
        if complaint:
            complaint.overall_summary = summary
            complaint.status = ComplaintStatus.COMPLETED
            await self.db.commit()

    async def get_processing_status(self, complaint_id: UUID) -> Optional[ComplaintStatusResponse]:
        complaint = await self.get_by_id(complaint_id)
        if not complaint:
            return None

        documents = complaint.documents
        total = len(documents)
        completed = sum(1 for d in documents if d.processing_status == ProcessingStatus.COMPLETED)

        progress = f"{completed}/{total} documents processed" if total > 0 else "No documents"

        doc_statuses = [
            DocumentStatusBrief(
                id=d.id,
                filename=d.original_filename,
                processing_status=d.processing_status.value,
                processing_progress=d.processing_progress
            )
            for d in documents
        ]

        return ComplaintStatusResponse(
            id=complaint.id,
            status=complaint.status,
            overall_progress=progress,
            documents=doc_statuses
        )

    async def get_response(self, complaint: Complaint) -> ComplaintResponse:
        """Convert a Complaint model to ComplaintResponse with counts."""
        doc_count_query = select(func.count(Document.id)).where(
            Document.complaint_id == complaint.id
        )
        processed_count_query = select(func.count(Document.id)).where(
            Document.complaint_id == complaint.id,
            Document.processing_status == ProcessingStatus.COMPLETED
        )

        doc_count = (await self.db.execute(doc_count_query)).scalar()
        processed_count = (await self.db.execute(processed_count_query)).scalar()

        return ComplaintResponse(
            id=complaint.id,
            title=complaint.title,
            description=complaint.description,
            external_ref=complaint.external_ref,
            status=complaint.status,
            overall_summary=complaint.overall_summary,
            created_at=complaint.created_at,
            updated_at=complaint.updated_at,
            documents_count=doc_count,
            processed_documents_count=processed_count
        )
