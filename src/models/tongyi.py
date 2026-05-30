from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Tongyi (Tongyi) modeladaptor

AlibulutTongyi API Dokumantasyon:https://help.aliyun.com/zh/dashscope/

Ozellikler:
1. Alibuluturun, icindemetinyetenekguclu
2. destekcokturicinkonusma
3. cokturmodelolabilirsec (qwen-max, qwen-plus, qwen-turbo) 

model: 
- qwen-max: enguclumodel (karsilik gelen HIGH tier) 
- qwen-plus: kullanmodel (karsilik gelen MEDIUM tier) 
- qwen-turbo: hizlihizmodel (karsilik gelen LOW tier) 
"""

import json
import time
from collections.abc import AsyncIterator

import httpx

from src.utils.safe_executor import safe_execute

from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)

# Tongyimodelyapilandirma
TONGYI_MODELS = {
    ModelTier.LOW: {
        "name": "qwen-turbo",
        "cost_per_1k_prompt": 0.004,
        "cost_per_1k_completion": 0.012,
    },
    ModelTier.MEDIUM: {
        "name": "qwen-plus",
        "cost_per_1k_prompt": 0.008,
        "cost_per_1k_completion": 0.02,
    },
    ModelTier.HIGH: {
        "name": "qwen-max",
        "cost_per_1k_prompt": 0.04,
        "cost_per_1k_completion": 0.12,
    },
}

# Tongyi API uc nokta
TONGYI_API_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
)


class TongyiModel(BaseModel):
    """
    Tongyimodeladaptor

    API uyumlu OpenAI format, kullan DashScope API
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
    ):
        """
        Args:
            config: modelyapilandirma (api_key icin DashScope API Key) 
            tier: performanskatmanseviye
        """
        # ayarlaayarTongyiozelyapilandirma
        model_info = TONGYI_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)

        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.TONGYI

    @property
    def model_name(self) -> str:
        return TONGYI_MODELS[self.tier]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        """alveyaolustur HTTP istemci"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        """kapat HTTP istemci"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """birmesajformatdonusturicinTongyi API format"""
        formatted = []
        for msg in messages:
            item = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            formatted.append(item)
        return formatted

    @safe_execute(max_attempts=3, timeout=30.0)
    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        """olmayanakisolustur"""
        client = await self._get_client()

        # olusturistek
        request_body = {
            "model": self.model_name,
            "input": {
                "messages": self._format_messages(messages),
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }
        # enjektearactanim (function calling) 
        if "tools" in kwargs and kwargs["tools"]:
            request_body["tools"] = kwargs["tools"]
            request_body["tool_choice"] = kwargs.get("tool_choice", "auto")

        start_time = time.time()

        try:
            response = await client.post(
                TONGYI_API_URL,
                json=request_body,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # ayristiryanit
            output = data.get("output", {})
            content = output.get("text", "")
            finish_reason = output.get("finish_reason", "stop")
            tool_calls = []

            # kullanistatistik
            usage_data = data.get("usage", {})
            usage = Usage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            self.update_usage(usage)

            return ModelResponse(
                content=content,
                model=self.model_name,
                provider=self.provider,
                tier=self.tier,
                usage=usage,
                finish_reason=finish_reason,
                latency_ms=latency_ms,
                metadata={
                    "request_id": data.get("request_id"),
                },
            tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise TongyiAPIError(f"Tongyi API hata: {error_detail}")
        except httpx.RequestError as e:
            raise TongyiAPIError(f"ag istegibasarisiz: {type(e).__name__}")

    @safe_execute(max_attempts=3, timeout=30.0)
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """akisolustur"""
        client = await self._get_client()

        request_body = {
            "model": self.model_name,
            "input": {
                "messages": self._format_messages(messages),
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "incremental_output": True,  # artmiktarcikti
            },
        }

        try:
            async with client.stream(
                "POST",
                TONGYI_API_URL,
                json=request_body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        output = data.get("output", {})
                        content = output.get("text", "")

                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise TongyiAPIError(f"Tongyi API hata: {error_detail}")
        except httpx.RequestError as e:
            raise TongyiAPIError(f"ag istegibasarisiz: {type(e).__name__}")


class TongyiAPIError(Exception):
    """Tongyi API hata"""

    pass
