"""
OpenRouter LLM client — shared by TaskSuggestionService and DailyRoutineService.
Uses httpx (already in project) with an OpenAI-compatible API.
"""

import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Raised when the LLM call fails for any reason (timeout, rate-limit, parse error)."""

    pass


class LLMClient:
    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = settings.openrouter_base_url
        self.max_tokens = settings.llm_max_tokens
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "json",
    ) -> dict[str, Any]:
        """
        Send a chat request to OpenRouter and return parsed JSON.

        response_format="json" appends a JSON-only instruction to the system prompt.
        On parse failure, retries once with temperature=0 (more deterministic).
        Raises LLMServiceError on any failure.
        """
        if not self.api_key:
            raise LLMServiceError("OPENROUTER_API_KEY is not configured")

        system = system_prompt
        if response_format == "json":
            system += "\n\nRespond with valid JSON only. No markdown, no explanation."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://smartattend.in",
        }

        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.7,
        }

        client = await self._get_client()

        for attempt in [0, 1]:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )

                if response.status_code == 429:
                    raise LLMServiceError("Rate limited by LLM provider (429)")
                if response.status_code >= 500:
                    raise LLMServiceError(f"LLM provider error: {response.status_code}")
                response.raise_for_status()

                content = response.json()["choices"][0]["message"]["content"]
                return json.loads(content)

            except (json.JSONDecodeError, KeyError, httpx.HTTPStatusError) as exc:
                if attempt == 0:
                    # Retry with temperature=0 for more deterministic output
                    body["temperature"] = 0
                    logger.warning(
                        "LLM response parse failed on first attempt (%s), retrying with temp=0",
                        exc,
                    )
                    continue
                raise LLMServiceError(f"LLM response parse failed after retry: {exc}") from exc
            except httpx.TimeoutException as exc:
                raise LLMServiceError(f"LLM request timed out: {exc}") from exc

        # Should not reach here, but satisfy type checker
        raise LLMServiceError("LLM call failed after retries")