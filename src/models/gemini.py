"""Google Gemini sağlayıcı adaptörü.

Google'ın OpenAI uyumlu uç noktasını kullanır:
  https://generativelanguage.googleapis.com/v1beta/openai/chat/completions

Kayıt: https://aistudio.google.com/apikey  (GEMINI_API_KEY)
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)

GEMINI_MODELS = {
    "low": {
        "name": "gemini-2.5-flash",
        "cost_per_1k_prompt": 0.00035,
        "cost_per_1k_completion": 0.00105,
    },
    "medium": {
        "name": "gemini-2.5-flash",
        "cost_per_1k_prompt": 0.00035,
        "cost_per_1k_completion": 0.00105,
    },
    "high": {
        "name": "gemini-2.5-pro",
        "cost_per_1k_prompt": 0.00125,
        "cost_per_1k_completion": 0.01,
    },
}


class GeminiAPIError(Exception):
    """Gemini API hatası."""


class GeminiModel(BaseModel):
    """Google Gemini model adaptörü (OpenAI uyumlu uç nokta)."""

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
    ):
        if config.base_url is None:
            config.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

        tier_key = tier.value
        info = GEMINI_MODELS.get(tier_key, GEMINI_MODELS["medium"])
        config.cost_per_1k_prompt = info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = info["cost_per_1k_completion"]

        super().__init__(config, tier)

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.GEMINI

    @property
    def model_name(self) -> str:
        return GEMINI_MODELS[self.tier.value]["name"]

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        client = await self._get_client()
        request_body = self._build_request_body(messages, **kwargs)

        start_time = time.time()

        async def _do_request():
            response = await client.post("/chat/completions", json=request_body)
            response.raise_for_status()
            return response

        try:
            response = await self._execute_with_retry(_do_request)
            response.raise_for_status()
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            choice = data["choices"][0]
            msg = choice["message"]
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls", [])

            usage_data = data.get("usage", {})
            usage = Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            self.update_usage(usage)

            return ModelResponse(
                content=content,
                model=self.model_name,
                provider=self.provider,
                tier=self.tier,
                usage=usage,
                finish_reason=choice.get("finish_reason", "stop"),
                latency_ms=latency_ms,
                metadata={"response_id": data.get("id")},
                tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            raise GeminiAPIError(
                f"Gemini API hatası ({e.response.status_code}): {e.response.text[:300]}"
            )
        except httpx.RequestError as e:
            raise GeminiAPIError(f"Ağ isteği başarısız: {e}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        client = await self._get_client()
        request_body = self._build_request_body(messages, **kwargs)
        request_body["stream"] = True

        try:
            async with client.stream(
                "POST", "/chat/completions", json=request_body
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPStatusError as e:
            raise GeminiAPIError(
                f"Gemini stream hatası ({e.response.status_code}): {e}"
            )
        except httpx.RequestError as e:
            raise GeminiAPIError(f"Ağ isteği başarısız: {e}")
