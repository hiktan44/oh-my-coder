from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Ollama yerelmodeladaptor

destek Ollama yerelkisimyerlestirackaynakmodel (ornegin Qwen2, Llama3, Mistral vb.) . 
sifirol, gizlilikkoru, ayrilsatirolabilirkullan. 

kullanyontem: 
1. kurulum Ollama: https://ollama.ai/
2. cekmodel: ollama pull qwen2:7b
3. satir: ollama serve (varsayilan http://localhost:11434)
4. yapilandirma: export OLLAMA_BASE_URL=http://localhost:11434

destekmodel: 
- qwen2:7b / qwen2:72b - AliTongyi2
- llama3:8b / llama3:70b - Meta Llama 3
- mistral:7b - Mistral AI
- codellama:7b - Meta Code Llama
- deepseek-coder:6.7b - DeepSeek kodmodel
"""

import json
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Any, Optional

import httpx

from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelResponse,
    ModelTier,
    Usage,
)

# Ollama varsayilanyapilandirma
OLLAMA_DEFAULT_URL = "http://localhost:11434"

# sikkullanyerelmodelliste (goreyetenekpuanseviye) 
OLLAMA_MODELS = {
    # LOW tier - hizlihiz, hafifmiktar
    ModelTier.LOW: [
        {"name": "qwen2:1.5b", "desc": "Tongyi 1.5B", "context": 32768},
        {"name": "llama3:8b", "desc": "Llama 3 8B", "context": 8192},
        {"name": "mistral:7b", "desc": "Mistral 7B", "context": 32768},
        {"name": "gemma:7b", "desc": "Google Gemma 7B", "context": 8192},
    ],
    # MEDIUM tier - denge
    ModelTier.MEDIUM: [
        {"name": "qwen2:7b", "desc": "Tongyi 7B", "context": 32768},
        {"name": "llama3:8b-instruct", "desc": "Llama 3 8B Instruct", "context": 8192},
        {
            "name": "deepseek-coder:6.7b",
            "desc": "DeepSeek Coder 6.7B",
            "context": 16384,
        },
        {"name": "codellama:7b", "desc": "Code Llama 7B", "context": 16384},
    ],
    # HIGH tier - yuksekkalitemiktar (gerekisterdahacokgosterkaydet) 
    ModelTier.HIGH: [
        {"name": "qwen2:72b", "desc": "Tongyi 72B", "context": 32768},
        {"name": "llama3:70b", "desc": "Llama 3 70B", "context": 8192},
        {"name": "deepseek-coder:33b", "desc": "DeepSeek Coder 33B", "context": 16384},
        {"name": "mixtral:8x7b", "desc": "Mixtral 8x7B MoE", "context": 32768},
    ],
}

# modelkadarkatmanseviyeesle (dinamikolustur) 
_MODEL_TIER_MAP: dict[str, ModelTier] = {}
for tier, models in OLLAMA_MODELS.items():
    for m in models:
        _MODEL_TIER_MAP[m["name"]] = tier


class OllamaModel(BaseModel):
    """
    Ollama yerelmodeladaptor

    Ozellikler:
    - sifirol: tamamtumyerelsatir, yok API ucretkullan
    - gizlilikkoru: sayigorehayiryerel
    - ayrilsatirolabilirkullan: yokgerekagbaglabaglan
    - destekcokturackaynakmodel
    """

    provider = "ollama"

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        model_name: str = "qwen2:7b",
    ):
        """
        Args:
            config: modelyapilandirma
            tier: performanskatmanseviye
            model_name: Ollama model adi (ornegin qwen2:7b) 
        """
        # ayarlaayar Ollama ozelyapilandirma
        config.provider = "ollama"
        if config.base_url is None:
            config.base_url = OLLAMA_DEFAULT_URL

        self._model_name = model_name
        self.base_url = config.base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

        # cikarim tier (sadecene zamaniletgirisdirvarsayilan MEDIUM vemodelicindeesleicindezamanyetenekuzerine yaz) 
        if tier == ModelTier.MEDIUM and model_name in _MODEL_TIER_MAP:
            tier = _MODEL_TIER_MAP[model_name]

        super().__init__(config, tier)

    @property
    def model_name(self) -> str:
        """donusgercekkullanmodel adi"""
        return self._model_name

    async def _get_client(self) -> httpx.AsyncClient:
        """al HTTP istemci"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client

    async def _generate(
        self,
        messages: list[Message],
        stream: bool = False,
        **kwargs,
    ) -> ModelResponse:
        """
        cagri Ollama API olusturyanit

        Ollama API dokumantasyon: https://github.com/ollama/ollama/blob/main/docs/api.md
        """
        client = await self._get_client()
        start_time = time.time()

        # donusturmesajformat
        ollama_messages = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            ollama_messages.append(item)

        # olustur Ollama API istek
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
                "num_ctx": kwargs.get("max_tokens", 4096),
            },
        }
        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]

        try:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # ayristiryanit
            content = data.get("message", {}).get("content", "")
            tool_calls = data.get("message", {}).get("tool_calls", [])
            model = data.get("model", self.model_name)

            # Ollama donus token istatistik
            eval_count = data.get("eval_count", 0)  # olustur token sayi
            prompt_eval_count = data.get("prompt_eval_count", 0)  # girdi token sayi

            usage = Usage(
                prompt_tokens=prompt_eval_count,
                completion_tokens=eval_count,
                total_tokens=prompt_eval_count + eval_count,
            )

            latency_ms = (time.time() - start_time) * 1000

            return ModelResponse(
                content=content,
                model=model,
                provider=self.provider,
                tier=self.tier,
                usage=usage,
                finish_reason="stop",
                latency_ms=latency_ms,
                metadata={
                    "local": True,
                    "base_url": self.base_url,
                },
            tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama API hata: {e.response.status_code} - {e.response.text}"
            )
        except httpx.ConnectError:
            raise RuntimeError(
                f"yokyontembaglabaglankadar Ollama servis ({self.base_url}), "
                "lutfensaglar Ollama baslat: ollama serve"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama cagribasarisiz: {e}")

    async def _generate_stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """akisolusturyanit"""
        client = await self._get_client()

        # donusturmesajformat
        ollama_messages = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                item["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            ollama_messages.append(item)

        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
            },
        }

        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.config.timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.ConnectError:
            raise RuntimeError(f"yokyontembaglabaglankadar Ollama servis ({self.base_url})")

    async def complete(
        self,
        messages: list[Message],
        **kwargs,
    ) -> ModelResponse:
        """tamamlaicinkonusma (olmayanakis) """
        return await self._generate(messages, stream=False, **kwargs)

    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """akistamamlaicinkonusma"""
        async for chunk in self._generate_stream(messages, **kwargs):
            yield chunk

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        """olmayanakisolustur (cagri complete) """
        return await self.complete(messages, **kwargs)

    @staticmethod
    def is_available(base_url: str = OLLAMA_DEFAULT_URL) -> bool:
        """
        kontrol Ollama servisolup olmadigiolabilirkullan

        Args:
            base_url: Ollama API adres

        Returns:
            bool: servisolup olmadigiolabilirkullan
        """
        try:
            import httpx

            response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def list_models(base_url: str = OLLAMA_DEFAULT_URL) -> list[dict[str, Any]]:
        """
        listeleyerelolabilirkullan Ollama model

        Args:
            base_url: Ollama API adres

        Returns:
            modelliste, hermodelicerir name, size, modified_at vb.bilgi
        """
        try:
            import httpx

            response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
        except Exception:
            return []

    @staticmethod
    def pull_model(model_name: str, base_url: str = OLLAMA_DEFAULT_URL) -> bool:
        """
        cekmodelkadaryerel

        Args:
            model_name: model adi (ornegin qwen2:7b) 
            base_url: Ollama API adres

        Returns:
            bool: basarili mi
        """
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600,  # 10 puandakikaasirizaman
            )
            return result.returncode == 0
        except Exception:
            return False

    def __repr__(self) -> str:
        return (
            f"OllamaModel(model={self.model_name}, "
            f"tier={self.tier.value}, "
            f"base_url={self.base_url})"
        )


# Ollama Provider isarettanisembol
OLLAMA_PROVIDER = "ollama"


def create_ollama_model(
    model_name: str = "qwen2:7b",
    base_url: str = OLLAMA_DEFAULT_URL,
    tier: Optional[ModelTier] = None,
) -> OllamaModel:
    """
    olustur Ollama modelornekkullanislifonksiyon

    Args:
        model_name: model adi
        base_url: Ollama API adres
        tier: performanskatmanseviye (hayirbelirtkuralotomatikcikarim) 

    Returns:
        OllamaModel ornek
    """
    config = ModelConfig(
        api_key="",  # Ollama hayirgerekister API Key
        base_url=base_url,
    )

    # otomatikcikarim tier
    if tier is None:
        tier = _MODEL_TIER_MAP.get(model_name, ModelTier.MEDIUM)

    return OllamaModel(config, tier=tier, model_name=model_name)
