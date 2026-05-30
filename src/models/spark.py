from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
iFlytek Spark (Spark) modeladaptor

API adres: https://spark-api.xf-yun.com
Dokumantasyon:https://www.xfyun.cn/doc/spark/

Ozellikler:
- bilimbuyukiFlytek Spark
- dilsesetkilesimyetenekguclu
- icindemetinanlamsalanlaiyiiyi
- gerekuckimlik bilgisi: API Key / App ID / Secret Key
"""

import time
from collections.abc import AsyncIterator
from typing import Any, Optional

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

# iFlytek Sparkmodelyapilandirma
SPARK_MODELS = {
    ModelTier.LOW: {
        "name": "generalv3",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.MEDIUM: {
        "name": "generalv3.5",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.HIGH: {
        "name": "4.0Ultra",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
}

SPARK_API_BASE = "https://spark-api.xf-yun.com"


class SparkModel(BaseModel):
    """iFlytek Sparkmodeladaptor"""

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        app_id: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        if config.base_url is None:
            config.base_url = f"{SPARK_API_BASE}/v3.1/chat"
        model_info = SPARK_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]
        super().__init__(config, tier)
        self.app_id = app_id
        self.secret_key = secret_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.SPARK

    @property
    def model_name(self) -> str:
        return SPARK_MODELS[self.tier]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _format_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        formatted = []
        for msg in messages:
            if msg.role == "system":
                formatted.append({"role": "user", "content": msg.content})
            else:
                item = {"role": msg.role, "content": msg.content}
                if msg.tool_calls:
                    item["tool_calls"] = msg.tool_calls
                if msg.tool_call_id:
                    item["tool_call_id"] = msg.tool_call_id
                formatted.append(item)
        return formatted

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        client = await self._get_client()
        request_body = {
            "header": {"app_id": self.app_id},
            "parameter": {
                "chat": {
                    "domain": self.model_name,
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                    "top_k": 5,
                }
            },
            "payload": {
                "message": {"text": self._format_messages(messages)},
            },
        }
        if "tools" in kwargs and kwargs["tools"]:
            request_body["payload"]["tools"] = kwargs["tools"]
        url = f"{self.config.base_url}?host=spark-api.xf-yun.com"
        start_time = time.time()
        try:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000
            choices = data.get("payload", {}).get("choices", {}).get("text", [])
            content = choices[0]["content"] if choices else ""
            tool_calls = []
            usage_data = data.get("payload", {}).get("usage", {}).get("text", {})
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
                finish_reason="stop",
                latency_ms=latency_ms,
                metadata={"app_id": self.app_id},
            tool_calls=tool_calls,
            )
        except httpx.HTTPStatusError as e:
            raise SparkAPIError(f"iFlytek Spark API hata ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise SparkAPIError(f"ag istegibasarisiz: {e}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        result = await self.generate(messages, **kwargs)
        for char in result.content:
            yield char


class SparkAPIError(Exception):
    """iFlytek Spark API hata"""
