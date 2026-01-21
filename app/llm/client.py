from openai import OpenAI, AsyncOpenAI
from typing import Optional
from app.core.config import settings


class OpenAIClient:
    """Wrapper for OpenAI API client."""

    def __init__(self):
        self._client = None
        self._async_client = None
        self.default_model = settings.OPENAI_MODEL

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of sync client."""
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    @property
    def async_client(self) -> AsyncOpenAI:
        """Lazy initialization of async client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._async_client

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> dict:
        """Synchronous completion (for Celery tasks)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        return {
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "model": response.model
        }

    async def complete_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> dict:
        """Asynchronous completion (for FastAPI endpoints)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.async_client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        return {
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "model": response.model
        }


# Singleton instance
openai_client = OpenAIClient()
