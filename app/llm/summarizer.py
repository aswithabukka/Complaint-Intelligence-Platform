from typing import List, Optional
from app.llm.client import openai_client
from app.llm.prompts import (
    DOCUMENT_SUMMARY_SYSTEM_PROMPT,
    DOCUMENT_SUMMARY_USER_PROMPT,
    OVERALL_SUMMARY_SYSTEM_PROMPT,
    OVERALL_SUMMARY_USER_PROMPT,
)
from app.core.config import settings


class Summarizer:
    """Service for generating summaries using LLM."""

    def __init__(self):
        self.client = openai_client
        self.max_content_length = settings.MAX_CONTENT_LENGTH  # e.g., 15000 chars

    def summarize_document(
        self,
        content: str,
        filename: str,
        file_type: str
    ) -> dict:
        """
        Generate a summary for a single document.
        Synchronous method for use in Celery tasks.
        """
        # Truncate content if too long
        truncated_content = self._truncate_content(content)

        prompt = DOCUMENT_SUMMARY_USER_PROMPT.format(
            filename=filename,
            file_type=file_type,
            content=truncated_content
        )

        result = self.client.complete(
            prompt=prompt,
            system_prompt=DOCUMENT_SUMMARY_SYSTEM_PROMPT,
            max_tokens=1500,
            temperature=0.3
        )

        return {
            "summary": result["content"],
            "tokens_used": result["tokens_used"],
            "model_used": result["model"],
            "was_truncated": len(content) > self.max_content_length
        }

    def generate_overall_summary(
        self,
        complaint_title: str,
        complaint_description: Optional[str],
        document_summaries: List[dict]
    ) -> dict:
        """
        Generate an overall summary combining all document summaries.
        Synchronous method for use in Celery tasks.
        """
        # Format document summaries
        summaries_text = "\n\n".join([
            f"### Document: {ds['filename']}\n{ds['summary']}"
            for ds in document_summaries
        ])

        prompt = OVERALL_SUMMARY_USER_PROMPT.format(
            complaint_title=complaint_title,
            complaint_description=complaint_description or "Not provided",
            document_count=len(document_summaries),
            document_summaries=summaries_text
        )

        result = self.client.complete(
            prompt=prompt,
            system_prompt=OVERALL_SUMMARY_SYSTEM_PROMPT,
            max_tokens=2000,
            temperature=0.3
        )

        return {
            "summary": result["content"],
            "tokens_used": result["tokens_used"],
            "model_used": result["model"]
        }

    async def summarize_document_async(
        self,
        content: str,
        filename: str,
        file_type: str
    ) -> dict:
        """
        Generate a summary for a single document.
        Asynchronous method for FastAPI endpoints.
        """
        truncated_content = self._truncate_content(content)

        prompt = DOCUMENT_SUMMARY_USER_PROMPT.format(
            filename=filename,
            file_type=file_type,
            content=truncated_content
        )

        result = await self.client.complete_async(
            prompt=prompt,
            system_prompt=DOCUMENT_SUMMARY_SYSTEM_PROMPT,
            max_tokens=1500,
            temperature=0.3
        )

        return {
            "summary": result["content"],
            "tokens_used": result["tokens_used"],
            "model_used": result["model"],
            "was_truncated": len(content) > self.max_content_length
        }

    def _truncate_content(self, content: str) -> str:
        """Truncate content to fit within model context limits."""
        if len(content) <= self.max_content_length:
            return content

        # Truncate and add indicator
        truncated = content[:self.max_content_length]
        return truncated + "\n\n[... content truncated due to length ...]"


# Singleton instance
summarizer = Summarizer()
