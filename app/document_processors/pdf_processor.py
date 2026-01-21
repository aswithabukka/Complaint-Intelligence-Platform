import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from app.document_processors.base import BaseDocumentProcessor, ExtractionResult
from app.db.models.document import DocumentType


class PDFProcessor(BaseDocumentProcessor):
    """Processor for PDF documents using PyMuPDF with OCR fallback."""

    def supports_file_type(self, file_type: str) -> bool:
        return file_type == DocumentType.PDF or file_type == "pdf"

    def extract_text(self, file_path: str) -> ExtractionResult:
        doc = fitz.open(file_path)
        text_parts = []
        warnings = []
        page_count = len(doc)

        for page_num, page in enumerate(doc, 1):
            # Try direct text extraction first
            page_text = page.get_text()

            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
            else:
                # Fall back to OCR for scanned pages
                try:
                    ocr_text = self._ocr_page(page)
                    if ocr_text.strip():
                        text_parts.append(f"--- Page {page_num} (OCR) ---\n{ocr_text}")
                        warnings.append(f"Page {page_num} required OCR processing")
                    else:
                        warnings.append(f"Page {page_num} could not be processed")
                except Exception as e:
                    warnings.append(f"OCR failed for page {page_num}: {str(e)}")

        doc.close()

        full_text = '\n\n'.join(text_parts)
        cleaned_text = self.postprocess(full_text)

        return ExtractionResult(
            text=cleaned_text,
            page_count=page_count,
            metadata={"extraction_method": "pymupdf+tesseract"},
            warnings=warnings if warnings else None
        )

    def _ocr_page(self, page) -> str:
        """Perform OCR on a PDF page."""
        # Render page to image
        mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))

        # Perform OCR
        text = pytesseract.image_to_string(image, lang='eng')
        return text
