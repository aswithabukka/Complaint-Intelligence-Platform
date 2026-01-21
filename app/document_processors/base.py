from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    text: str
    page_count: Optional[int] = None
    metadata: Optional[dict] = None
    warnings: Optional[list] = None


class BaseDocumentProcessor(ABC):
    """Abstract base class for document processors."""

    @abstractmethod
    def extract_text(self, file_path: str) -> ExtractionResult:
        """Extract text content from a document."""
        pass

    @abstractmethod
    def supports_file_type(self, file_type: str) -> bool:
        """Check if this processor supports the given file type."""
        pass

    def preprocess(self, file_path: str) -> str:
        """Optional preprocessing step. Returns the path to process."""
        return file_path

    def postprocess(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = [' '.join(line.split()) for line in lines]
        text = '\n'.join(line for line in cleaned_lines if line)
        return text
