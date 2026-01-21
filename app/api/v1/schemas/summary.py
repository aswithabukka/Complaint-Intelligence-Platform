from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.db.models.summary import SummaryType


class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    summary_type: SummaryType
    content: str
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    created_at: datetime


class DocumentSummaryResponse(SummaryResponse):
    document_id: UUID
    document_filename: str


class OverallSummaryResponse(BaseModel):
    complaint_id: UUID
    complaint_title: str
    overall_summary: Optional[str] = None
    document_summaries: List[DocumentSummaryResponse]
    total_documents: int
    summarized_documents: int
    generated_at: Optional[datetime] = None
