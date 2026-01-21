from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.document import Document, ProcessingStatus
from app.db.models.summary import Summary, SummaryType
from app.db.models.complaint import Complaint, ComplaintStatus
from app.llm.summarizer import summarizer
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def summarize_document_task(self, extraction_result: dict):
    """
    Generate a summary for a single document.
    Receives result from process_document_task.
    """
    document_id = extraction_result.get("document_id")
    if not document_id:
        logger.error("No document_id in extraction result")
        return None

    logger.info(f"Summarizing document: {document_id}")

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if not document.extracted_text:
            raise ValueError(f"Document {document_id} has no extracted text")

        # Update status
        document.processing_status = ProcessingStatus.SUMMARIZING
        document.processing_progress = "70%"
        db.commit()

        # Generate summary
        result = summarizer.summarize_document(
            content=document.extracted_text,
            filename=document.original_filename,
            file_type=document.file_type.value
        )

        # Check if summary already exists and update or create
        existing_summary = db.query(Summary).filter(
            Summary.document_id == document.id
        ).first()

        if existing_summary:
            existing_summary.content = result["summary"]
            existing_summary.tokens_used = result["tokens_used"]
            existing_summary.model_used = result["model_used"]
        else:
            summary = Summary(
                document_id=document.id,
                summary_type=SummaryType.DOCUMENT,
                content=result["summary"],
                tokens_used=result["tokens_used"],
                model_used=result["model_used"]
            )
            db.add(summary)

        # Update document status
        document.processing_status = ProcessingStatus.COMPLETED
        document.processing_progress = "100%"
        db.commit()

        logger.info(f"Document summarization complete: {document_id}")

        return {
            "document_id": document_id,
            "filename": document.original_filename,
            "summary": result["summary"],
            "tokens_used": result["tokens_used"]
        }

    except Exception as e:
        logger.error(f"Error summarizing document {document_id}: {str(e)}")
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = ProcessingStatus.FAILED
            document.error_message = f"Summarization failed: {str(e)}"
            db.commit()

        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def generate_overall_summary_task(self, document_results: list, complaint_id: str):
    """
    Generate an overall summary combining all document summaries.
    This is the final task in the chord.
    """
    logger.info(f"Generating overall summary for complaint: {complaint_id}")

    db = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found")

        # Update status
        complaint.status = ComplaintStatus.SUMMARIZING
        db.commit()

        # Filter successful results
        successful_summaries = [
            r for r in document_results
            if r and isinstance(r, dict) and "summary" in r
        ]

        if not successful_summaries:
            logger.warning(f"No successful document summaries for complaint: {complaint_id}")
            complaint.status = ComplaintStatus.PENDING_ACTION
            complaint.overall_summary = "No documents were successfully summarized."
            db.commit()
            return {
                "complaint_id": complaint_id,
                "status": "pending_action_no_summaries",
                "documents_summarized": 0
            }

        # Generate overall summary
        result = summarizer.generate_overall_summary(
            complaint_title=complaint.title,
            complaint_description=complaint.description,
            document_summaries=successful_summaries
        )

        # Store overall summary in complaint
        complaint.overall_summary = result["summary"]
        complaint.status = ComplaintStatus.PENDING_ACTION

        # Also store as Summary record (delete old one first)
        existing_overall = db.query(Summary).filter(
            Summary.complaint_id == complaint.id,
            Summary.summary_type == SummaryType.OVERALL
        ).first()

        if existing_overall:
            existing_overall.content = result["summary"]
            existing_overall.tokens_used = result["tokens_used"]
            existing_overall.model_used = result["model_used"]
        else:
            overall_summary = Summary(
                complaint_id=complaint.id,
                summary_type=SummaryType.OVERALL,
                content=result["summary"],
                tokens_used=result["tokens_used"],
                model_used=result["model_used"]
            )
            db.add(overall_summary)

        db.commit()

        logger.info(f"Overall summary complete for complaint: {complaint_id}")

        return {
            "complaint_id": complaint_id,
            "status": "completed",
            "documents_summarized": len(successful_summaries),
            "tokens_used": result["tokens_used"]
        }

    except Exception as e:
        logger.error(f"Error generating overall summary: {str(e)}")
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint.status = ComplaintStatus.FAILED
            db.commit()

        raise self.retry(exc=e, countdown=120)

    finally:
        db.close()


@celery_app.task(bind=True)
def regenerate_complaint_summaries_task(self, complaint_id: str):
    """
    Regenerate all summaries for a complaint.
    """
    logger.info(f"Regenerating summaries for complaint: {complaint_id}")

    db = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found")

        # Get all documents with extracted text
        documents = db.query(Document).filter(
            Document.complaint_id == complaint_id,
            Document.extracted_text.isnot(None)
        ).all()

        if not documents:
            return {"status": "no_documents_with_text", "complaint_id": complaint_id}

        # Update complaint status
        complaint.status = ComplaintStatus.SUMMARIZING
        db.commit()

        # Create summarization tasks for each document
        from celery import group, chord

        doc_tasks = group([
            summarize_document_task.s({
                "document_id": str(doc.id),
                "text_length": len(doc.extracted_text) if doc.extracted_text else 0,
                "status": "extracted"
            })
            for doc in documents
        ])

        # Chain with overall summary generation
        workflow = chord(
            doc_tasks,
            generate_overall_summary_task.s(complaint_id)
        )

        workflow.apply_async()

        return {
            "status": "regeneration_started",
            "complaint_id": complaint_id,
            "document_count": len(documents)
        }

    finally:
        db.close()
