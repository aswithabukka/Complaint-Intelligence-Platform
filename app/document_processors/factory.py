from typing import Dict, Type
from app.db.models.document import DocumentType
from app.document_processors.base import BaseDocumentProcessor
from app.document_processors.pdf_processor import PDFProcessor
from app.document_processors.image_processor import ImageProcessor
from app.document_processors.docx_processor import DocxProcessor
from app.document_processors.excel_processor import ExcelProcessor


class ProcessorFactory:
    """Factory for creating document processors based on file type."""

    _processors: Dict[DocumentType, Type[BaseDocumentProcessor]] = {
        DocumentType.PDF: PDFProcessor,
        DocumentType.IMAGE: ImageProcessor,
        DocumentType.DOC: DocxProcessor,
        DocumentType.DOCX: DocxProcessor,
        DocumentType.XLS: ExcelProcessor,
        DocumentType.XLSX: ExcelProcessor,
    }

    @classmethod
    def get_processor(cls, file_type: DocumentType) -> BaseDocumentProcessor:
        """Get the appropriate processor for a file type."""
        processor_class = cls._processors.get(file_type)
        if not processor_class:
            raise ValueError(f"No processor available for file type: {file_type}")
        return processor_class()

    @classmethod
    def register_processor(
        cls,
        file_type: DocumentType,
        processor_class: Type[BaseDocumentProcessor]
    ):
        """Register a new processor for a file type."""
        cls._processors[file_type] = processor_class
