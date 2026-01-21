from docx import Document
from app.document_processors.base import BaseDocumentProcessor, ExtractionResult
from app.db.models.document import DocumentType


class DocxProcessor(BaseDocumentProcessor):
    """Processor for Word documents (.doc, .docx)."""

    SUPPORTED_TYPES = {DocumentType.DOC, DocumentType.DOCX, "doc", "docx"}

    def supports_file_type(self, file_type: str) -> bool:
        return file_type in self.SUPPORTED_TYPES

    def extract_text(self, file_path: str) -> ExtractionResult:
        doc = Document(file_path)
        text_parts = []

        # Extract paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        # Extract tables
        for table in doc.tables:
            table_text = self._extract_table(table)
            if table_text:
                text_parts.append("\n[TABLE]\n" + table_text + "\n[/TABLE]")

        full_text = '\n\n'.join(text_parts)
        cleaned_text = self.postprocess(full_text)

        return ExtractionResult(
            text=cleaned_text,
            page_count=None,  # DOCX doesn't have page concept
            metadata={
                "extraction_method": "python-docx",
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(doc.tables)
            }
        )

    def _extract_table(self, table) -> str:
        """Extract text from a table."""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(' | '.join(cells))
        return '\n'.join(rows)
