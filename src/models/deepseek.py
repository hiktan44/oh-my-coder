from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
DeepSeek modeladaptor

DeepSeek API Dokumantasyon:https://platform.deepseek.com/api-docs/

Ozellikler:
1. tamamtumuyumlu OpenAI API format
2. ucretsizkotaderece: hergun 4000 10 bin token
3. destekicindemetin, kalitemiktarbaglanyakin GPT-4
4. degerasiridusuk (ucretsizkotadereceicinde) 

model: 
- deepseek-chat: kullanicinkonusmamodel (karsilik gelen sonnet) 
- deepseek-coder: kodozelkullanmodel (kodgorevilksec) 
"""

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

# DeepSeek modelyapilandirma
DEEPSEEK_MODELS = {
    ModelTier.LOW: {
        "name": "deepseek-chat",
        "cost_per_1k_prompt": 0.0,  # ucretsizkotadereceicinde
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.MEDIUM: {
        "name": "deepseek-chat",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.HIGH: {
        "name": "deepseek-chat",  # DeepSeek V4
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
}

# DeepSeek Coder model (kodozelkullan) 
DEEPSEEK_CODER = {
    "name": "deepseek-coder",
    "cost_per_1k_prompt": 0.0,
    "cost_per_1k_completion": 0.0,
}


class DeepSeekModel(BaseModel):
    """
    DeepSeek modeladaptor

    API uyumlu OpenAI format, kullan httpx yapicin HTTP istemci
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        use_coder: bool = False,
    ):
        """
        Args:
            config: modelyapilandirma
            tier: performanskatmanseviye
            use_coder: olup olmadigikullankodozelkullanmodel
        """
        # ayarlaayar DeepSeek ozelyapilandirma
        if config.base_url is None:
            config.base_url = "https://api.deepseek.com/v1"

        # ayarlaayarol
        if use_coder:
            config.cost_per_1k_prompt = DEEPSEEK_CODER["cost_per_1k_prompt"]
            config.cost_per_1k_completion = DEEPSEEK_CODER["cost_per_1k_completion"]
            self._use_coder = True
        else:
            model_info = DEEPSEEK_MODELS[tier]
            config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
            config.cost_per_1k_completion = model_info["cost_per_1k_completion"]
            self._use_coder = False

        super().__init__(config, tier)

        # HTTP istemci (gecikmebaslat) 
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.DEEPSEEK

    @property
    def model_name(self) -> str:
        if self._use_coder:
            return DEEPSEEK_CODER["name"]
        return DEEPSEEK_MODELS[self.tier]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        """alveyaolustur HTTP istemci"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
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
        """birmesajformatdonusturicin DeepSeek API format"""
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
        # araccagri (function calling) 
        if "tools" in kwargs and kwargs["tools"]:
            request_body["tools"] = kwargs["tools"]
            request_body["tool_choice"] = kwargs.get("tool_choice", "auto")

        start_time = time.time()

        async def _do_request():
            """çekirdek istek mantığı, saglaryeniden denemekanizmacagri"""
            response = await client.post(
                "/chat/completions",
                json=request_body,
            )
            response.raise_for_status()
            return response

        try:
            # temel sınıfın yeniden deneme mekanizmasını kullan
            response = await self._execute_with_retry(_do_request)

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # ayristiryanit
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content") or ""
            finish_reason = choice.get("finish_reason", "stop")

            # araccagri
            tool_calls = message.get("tool_calls", [])

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
                },
                tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            # isle API hata
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", str(error_body))
                # yazdirtamhata mesajikullandehata ayikla
                print("\n🔴 DeepSeek API hatadetay:")
                print(f"   durumkod: {e.response.status_code}")
                print(f"   hataicerik: {error_body}")
                print(f"   istek: {json.dumps(request_body, ensure_ascii=False, indent=2)[:500]}...")
            except Exception as parse_err:
                error_detail = f"HTTP {e.response.status_code} (yokyontemayristirhatadetay: {parse_err})"
                print(f"\n🔴 DeepSeek API hata (yokyontemayristir): {e.response.text[:500]}")

            raise DeepSeekAPIError(
                f"DeepSeek API hata ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise DeepSeekAPIError(f"ag istegibasarisiz: {type(e).__name__}")

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
                error_detail = error_body.get("error", {}).get("message", str(error_body))
                # yazdirtamhata mesajikullandehata ayikla
                print("\n🔴 DeepSeek API hatadetay (stream):")
                print(f"   durumkod: {e.response.status_code}")
                print(f"   hataicerik: {error_body}")
            except Exception as parse_err:
                error_detail = f"HTTP {e.response.status_code} (yokyontemayristirhatadetay: {parse_err})"
                print(f"\n🔴 DeepSeek API hata (stream, yokyontemayristir): {e.response.text[:500]}")

            raise DeepSeekAPIError(
                f"DeepSeek API hata ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise DeepSeekAPIError(f"ag istegibasarisiz: {type(e).__name__}")


class DeepSeekAPIError(Exception):
    """DeepSeek API hata"""

    pass
