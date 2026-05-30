from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
kucukmetre MiMo modeladaptor

MiMo API Dokumantasyon:https://platform.xiaomimimo.com

Ozellikler:
1. tamamtumuyumlu OpenAI API format
2. model: mimo-v2-flash (ucretsiz) , mimo-v2-pro
3. baglamuzunlukderece: mimo-v2-flash 256K, mimo-v2-pro 1M
4. destekderinlikdusuncesina, akiscikti, fonksiyoncagri, yapicikti
"""

import json
import os
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

# MiMo modelyapilandirma
MIMO_MODELS = {
    ModelTier.LOW: {
        "name": "mimo-v2-flash",
        "context_length": 256 * 1024,  # 256K
        "cost_per_1k_prompt": 0.0,  # sinirzamanucretsiz
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.MEDIUM: {
        "name": "mimo-v2-flash",
        "context_length": 256 * 1024,
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.HIGH: {
        "name": "mimo-v2-pro",
        "context_length": 1024 * 1024,  # 1M
        "cost_per_1k_prompt": 1.0,  # $1/M tokens
        "cost_per_1k_completion": 3.0,  # $3/M tokens
    },
}


class MimoModel(BaseModel):
    """
    kucukmetre MiMo modeladaptor

    API uyumlu OpenAI format, kullan httpx yapicin HTTP istemci
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
    ):
        """
        Args:
            config: modelyapilandirma
            tier: performanskatmanseviye
        """
        # ayarlaayar MiMo ozelyapilandirma
        if config.base_url is None:
            config.base_url = "https://api.xiaomimimo.com/v1"

        # ayarlaayarol
        model_info = MIMO_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)

        # HTTP istemci (gecikmebaslat) 
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.MIMO

    @property
    def model_name(self) -> str:
        return MIMO_MODELS[self.tier]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        """alveyaolustur HTTP istemci"""
        if self._client is None or self._client.is_closed:
            # oncelikkullanortam degiskenmiktar MIMOAPIKEY
            api_key = os.environ.get("MIMOAPIKEY") or self.config.api_key
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
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
        """birmesajformatdonusturicin MiMo API format"""
        formatted = []
        for msg in messages:
            item = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_calls:  # assistant mesaj aracligicagri
                item["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:  # tool mesaj aracligicagri ID
                item["tool_call_id"] = msg.tool_call_id
            formatted.append(item)
        return formatted

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        """
        olmayanakisolustur

        Args:
            messages: icinkonusmagecmis
            **kwargs: olabilirsecparametre
                - temperature: isiderece (0-2) 
                - max_tokens: enbuyukolustur token sayi
                - top_p: core samplornekparametre
                - stop: durdurkelimeliste
        """
        client = await self._get_client()

        # olusturistek
        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": False,
        }

        # ekleolabilirsecparametre
        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]

        # destekfonksiyoncagri
        if "tools" in kwargs:
            request_body["tools"] = kwargs["tools"]

        start_time = time.time()

        try:
            response = await client.post(
                "/chat/completions",
                json=request_body,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # ayristiryanit
            choice = data["choices"][0]
            content = choice["message"].get("content") or ""
            finish_reason = choice.get("finish_reason", "stop")

            # islefonksiyoncagri
            tool_calls = choice["message"].get("tool_calls")

            # kullanistatistik
            usage_data = data.get("usage", {})
            usage = Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # guncellebiriktirhesapkullanmiktar
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
                    "response_id": data.get("id"),
                    "created": data.get("created"),
                    "tool_calls": tool_calls,
                },
            tool_calls=tool_calls if "tool_calls" in dir() else [],
            )

        except httpx.HTTPStatusError as e:
            # isle API hata
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise MimoAPIError(
                f"MiMo API hata ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise MimoAPIError(f"ag istegibasarisiz: {type(e).__name__}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """
        akisolustur

        Yields:
            str: herkezolusturmetinparca
        """
        client = await self._get_client()

        # olusturistek
        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        # ekleolabilirsecparametre
        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]
        if "tools" in kwargs:
            request_body["tools"] = kwargs["tools"]

        try:
            async with client.stream(
                "POST",
                "/chat/completions",
                json=request_body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    # atlabossatirveyorum
                    if not line or line.startswith(":"):
                        continue

                    # kaldir "data: " onceek
                    if line.startswith("data: "):
                        line = line[6:]

                    # bitirisaret
                    if line == "[DONE]":
                        break

                    # ayristir JSON
                    try:
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise MimoAPIError(
                f"MiMo API hata ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise MimoAPIError(f"ag istegibasarisiz: {type(e).__name__}")


class MimoAPIError(Exception):
    """MiMo API hata"""
