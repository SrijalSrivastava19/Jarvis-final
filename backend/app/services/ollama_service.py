"""
Ollama service — talks to a local Ollama server for LLM completions.

This is the only place in the codebase that knows about Ollama's HTTP API.
Routes and other services call `generate_reply()` and never touch httpx or
Ollama-specific payloads directly, so swapping in OpenAI/Claude/Gemini later
(per the multi-provider roadmap) means adding a sibling service with the
same function signature, not rewriting call sites.
"""
from typing import List, TypedDict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.exceptions import OllamaUnavailableError
from app.logger import get_logger

logger = get_logger(__name__)


class ChatMessage(TypedDict):
    role: str
    content: str


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def generate_reply(self, messages: List[ChatMessage]) -> str:
        """
        Send the full conversation (system + history + new user message) to
        Ollama's /api/chat endpoint and return the assistant's reply text.

        Retries transient network errors up to 3 times with exponential
        backoff before surfacing OllamaUnavailableError to the caller.
        """
        url = f"{self.base_url}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": False}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.error("Ollama request failed: %s", exc)
            raise OllamaUnavailableError(
                f"Could not reach Ollama at {self.base_url}. "
                "Is `ollama serve` running and is the model pulled?"
            ) from exc

        reply = data.get("message", {}).get("content", "").strip()
        if not reply:
            raise OllamaUnavailableError("Ollama returned an empty response.")

        logger.info("Ollama reply generated (%d chars)", len(reply))
        return reply

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False


ollama_service = OllamaService()
