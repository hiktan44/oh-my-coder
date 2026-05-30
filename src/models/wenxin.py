from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Wenxin (Wenxin) modeladaptor

yuzdereceWenxin API Dokumantasyon:https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html

Ozellikler:
1. yuzdereceurun, icindemetinyetenekguclu
2. destekcokturicinkonusma
3. cokturmodelolabilirsec (ERNIE-Bot-4, ERNIE-Bot, ERNIE-Bot-turbo) 

model: 
- ERNIE-Bot-4: enguclumodel (karsilik gelen HIGH tier) 
- ERNIE-Bot: kullanmodel (karsilik gelen MEDIUM tier) 
- ERNIE-Bot-turbo: hizlihizmodel (karsilik gelen LOW tier) 
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

# Wenxinmodelyapilandirma
WENXIN_MODELS = {
    ModelTier.LOW: {
        "name": "eb-instant",  # ERNIE-Bot-turbo
        "cost_per_1k_prompt": 0.004,
        "cost_per_1k_completion": 0.008,
    },
    ModelTier.MEDIUM: {
        "name": "completions_pro",  # ERNIE-Bot
        "cost_per_1k_prompt": 0.012,
        "cost_per_1k_completion": 0.012,
    },
    ModelTier.HIGH: {
        "name": "completions",  # ERNIE-Bot-4
        "cost_per_1k_prompt": 0.12,
        "cost_per_1k_completion": 0.12,
    },
}

# Wenxin API uc nokta
WENXIN_API_URL = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat"


class WenxinModel(BaseModel):
    """
    Wenxinmodeladaptor

    dikkat: Wenxin API gerekister Access Token, araciligiyla API Key ve Secret Key al
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        secret_key: Optional[str] = None,
    ):
        """
        Args:
            config: modelyapilandirma (api_key icin API Key) 
            tier: performanskatmanseviye
            secret_key: Secret Key (kullandeal Access Token) 
        """
        # ayarlaayarWenxinozelyapilandirma
        model_info = WENXIN_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)

        self.secret_key = secret_key
        self._access_token: Optional[str] = None
        self._token_expire_time: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.WENXIN

    @property
    def model_name(self) -> str:
        return WENXIN_MODELS[self.tier]["name"]

    async def _get_access_token(self) -> str:
        """al Access Token (varonbellek) """
        # kontrolonbellekolup olmadigivaretki
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token

        # alyeni Access Token
        client = await self._get_client()

        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.config.api_key}&client_secret={self.secret_key}"

        response = await client.post(url)
        response.raise_for_status()

        data = response.json()
        self._access_token = data["access_token"]
        self._token_expire_time = (
            time.time() + data["expires_in"] - 300
        )  # yukseltonce 5 puandakikadonem

        return self._access_token

    async def _get_client(self) -> httpx.AsyncClient:
        """alveyaolustur HTTP istemci"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        """kapat HTTP istemci"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """
        birmesajformatdonusturicinWenxin API format

        dikkat: Wenxinhayirdestek system role, gerekisterbirlestirvekadarincibirogre user mesaj
        """
        formatted = []
        system_content = ""

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                item = {"role": msg.role, "content": msg.content}
                if msg.tool_calls:
                    item["tool_calls"] = msg.tool_calls
                if msg.tool_call_id:
                    item["tool_call_id"] = msg.tool_call_id
                formatted.append(item)

        # egervar system icerik, birlestirvekadarincibirogre user mesaj
        if system_content and formatted and formatted[0]["role"] == "user":
            formatted[0]["content"] = f"{system_content}\n\n{formatted[0]['content']}"

        return formatted

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        """olmayanakisolustur"""
        client = await self._get_client()
        access_token = await self._get_access_token()

        # olusturistek
        request_body = {
            "messages": self._format_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        # ekleolabilirsecparametre
        if "max_tokens" in kwargs:
            request_body["max_output_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]
        if "tools" in kwargs and kwargs["tools"]:
            request_body["tools"] = kwargs["tools"]
            request_body["tool_choice"] = kwargs.get("tool_choice", "auto")

        url = f"{WENXIN_API_URL}/{self.model_name}?access_token={access_token}"

        start_time = time.time()

        try:
            response = await client.post(url, json=request_body)
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # ayristiryanit
            content = data.get("result", "")
            finish_reason = data.get("finish_reason", "stop")
            tool_calls = []

            # kullanistatistik
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
                finish_reason=finish_reason,
                latency_ms=latency_ms,
                metadata={
                    "id": data.get("id"),
                    "created": data.get("created"),
                },
            tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error_msg", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise WenxinAPIError(f"Wenxin API hata: {error_detail}")
        except httpx.RequestError as e:
            raise WenxinAPIError(f"ag istegibasarisiz: {type(e).__name__}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """akisolustur"""
        client = await self._get_client()
        access_token = await self._get_access_token()

        request_body = {
            "messages": self._format_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        url = f"{WENXIN_API_URL}/{self.model_name}?access_token={access_token}"

        try:
            async with client.stream("POST", url, json=request_body) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # ayristir SSE sayigore
                    if line.startswith("data: "):
                        line = line[6:]

                    try:
                        data = json.loads(line)
                        result = data.get("result", "")
                        if result:
                            yield result
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error_msg", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise WenxinAPIError(f"Wenxin API hata: {error_detail}")
        except httpx.RequestError as e:
            raise WenxinAPIError(f"ag istegibasarisiz: {type(e).__name__}")


class WenxinAPIError(Exception):
    """Wenxin API hata"""

    pass
