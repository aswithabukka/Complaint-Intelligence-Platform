import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from app.document_processors.base import BaseDocumentProcessor, ExtractionResult
from app.db.models.document import DocumentType


class ImageProcessor(BaseDocumentProcessor):
    """Processor for image files using Tesseract OCR."""

    SUPPORTED_TYPES = {DocumentType.IMAGE, "image"}

    def supports_file_type(self, file_type: str) -> bool:
        return file_type in self.SUPPORTED_TYPES

    def extract_text(self, file_path: str) -> ExtractionResult:
        # Load and preprocess image
        image = Image.open(file_path)
        processed_image = self._preprocess_image(image)

        # Perform OCR with configuration
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(
            processed_image,
            lang='eng',
            config=custom_config
        )

        # Get OCR confidence data
        data = pytesseract.image_to_data(
            processed_image,
            output_type=pytesseract.Output.DICT
        )
        confidences = [int(c) for c in data['conf'] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        cleaned_text = self.postprocess(text)

        warnings = None
        if avg_confidence < 60:
            warnings = [f"Low OCR confidence: {avg_confidence:.1f}%"]

        return ExtractionResult(
            text=cleaned_text,
            page_count=1,
            metadata={
                "extraction_method": "tesseract_ocr",
                "image_size": image.size,
                "average_confidence": round(avg_confidence, 2)
            },
            warnings=warnings
        )

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert to grayscale
        image = image.convert('L')

        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)

        # Apply slight sharpening
        image = image.filter(ImageFilter.SHARPEN)

        # Binarization (thresholding)
        threshold = 128
        image = image.point(lambda p: 255 if p > threshold else 0)

        return image
