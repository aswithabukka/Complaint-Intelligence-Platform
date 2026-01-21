from celery import chain, group, chord
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.document import Document, ProcessingStatus
from app.db.models.complaint import Complaint, ComplaintStatus
from app.document_processors.factory import ProcessorFactory
from app.workers.tasks.summary_tasks import summarize_document_task, generate_overall_summary_task
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, document_id: str):
    """
    Extract text from a document.

    Flow:
    1. Extract text from document using appropriate processor
    2. Update document record with extracted text
    3. Return result for chaining to summarization
    """
    logger.info(f"Processing document: {document_id}")

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Update status
        document.processing_status = ProcessingStatus.EXTRACTING
        document.processing_progress = "10%"
        db.commit()

        # Get appropriate processor
        processor = ProcessorFactory.get_processor(document.file_type)

        # Extract text
        document.processing_progress = "30%"
        db.commit()

        result = processor.extract_text(document.file_path)

        # Store extracted text
        document.extracted_text = result.text
        document.processing_status = ProcessingStatus.EXTRACTED
        document.processing_progress = "50%"
        db.commit()

        logger.info(f"Text extraction complete for document: {document_id}")

        return {
            "document_id": document_id,
            "text_length": len(result.text),
            "page_count": result.page_count,
            "status": "extracted"
        }

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = ProcessingStatus.FAILED
            document.error_message = str(e)
            db.commit()

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(bind=True)
def process_complaint_documents(self, complaint_id: str):
    """
    Process all documents for a complaint.

    This task orchestrates the entire processing pipeline:
    1. Get all pending documents
    2. Process each document (extract + summarize)
    3. Generate overall summary when all complete
    """
    logger.info(f"Starting complaint processing: {complaint_id}")

    db = SessionLocal()
    try:
        # Get complaint and documents
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found")

        documents = db.query(Document).filter(
            Document.complaint_id == complaint_id,
            Document.processing_status.in_([ProcessingStatus.PENDING, ProcessingStatus.FAILED])
        ).all()

        if not documents:
            logger.warning(f"No documents to process for complaint: {complaint_id}")
            return {"status": "no_documents"}

        # Update complaint status
        complaint.status = ComplaintStatus.PROCESSING
        db.commit()

        # Create a chain of tasks for each document
        # process_document -> summarize_document
        document_chains = []
        for doc in documents:
            doc.processing_status = ProcessingStatus.PENDING
            doc.error_message = None
            db.commit()

            doc_chain = chain(
                process_document_task.s(str(doc.id)),
                summarize_document_task.s()
            )
            document_chains.append(doc_chain)

        db.commit()

        # Execute document chains in parallel, then generate overall summary
        workflow = chord(
            group(document_chains),
            generate_overall_summary_task.s(complaint_id)
        )

        workflow.apply_async()

        return {"status": "processing_started", "document_count": len(documents)}

    except Exception as e:
        logger.error(f"Error starting complaint processing: {str(e)}")
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint.status = ComplaintStatus.FAILED
            db.commit()
        raise

    finally:
        db.close()


@celery_app.task(bind=True)
def reprocess_document_task(self, document_id: str):
    """
    Reprocess a single document (extract and summarize).
    """
    logger.info(f"Reprocessing document: {document_id}")

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Reset status
        document.processing_status = ProcessingStatus.PENDING
        document.error_message = None
        document.extracted_text = None
        db.commit()

        # Chain extract -> summarize
        workflow = chain(
            process_document_task.s(document_id),
            summarize_document_task.s()
        )

        workflow.apply_async()

        return {"status": "reprocessing_started", "document_id": document_id}

    finally:
        db.close()
