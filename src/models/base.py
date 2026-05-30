from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
modeltemel sinif - tanimvar LLM saglayicibirbaglanagiz

tasarimasilkural: 
1. asenkrononcelik - var API cagritumdirasenkron
2. akisdestek - destekakiscikti, yukseltyukseltkullanicidogrula
3. birhata isleme - yakalahersaglayicifarkfarkli
4. Token hesapsayi - standart token kullanistatistik
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx


class ModelTier(Enum):
    """modelperformanskatmanseviye - karsilik gelenasilproje haiku/sonnet/opus uckatman"""

    LOW = "low"  # hizlihiz, kolayuygun - karsilik gelen haiku
    MEDIUM = "medium"  # denge - karsilik gelen sonnet
    HIGH = "high"  # enyuksekkalitemiktar - karsilik gelen opus


class ModelProvider(Enum):
    """destekmodelsaglayici"""

    DEEPSEEK = "deepseek"
    WENXIN = "wenxin"  # Wenxin
    TONGYI = "tongyi"  # Tongyi
    GLM = "glm"  # Zhipu ChatGLM
    OPENAI = "openai"  # OpenAI GPT
    CLAUDE = "claude"  # Anthropic Claude
    MINIMAX = "minimax"  # MiniMax
    KIMI = "kimi"  # Kimi
    HUNYUAN = "hunyuan"  # Tencent Hunyuan
    DOUBAO = "doubao"  # bytepaket
    TIANGONG = "tiangong"  # TiangongAI
    SPARK = "spark"  # iFlytek Spark
    BAICHUAN = "baichuan"  # Baichuanedebilir
    MIMO = "mimo"  # kucukmetre MiMo
    OLLAMA = "ollama"  # Ollama yerelmodel (sifirol) 


@dataclass
class Message:
    """birmesajformat"""

    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None  # kullandecokturicinkonusmaicinderolisarettani
    tool_calls: Optional[list[dict[str, Any]]] = None  # assistant mesajicindearaccagri
    tool_call_id: Optional[str] = None  # tool mesajicindearaccagri ID


@dataclass
class Usage:
    """Token kullanistatistik"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class ModelResponse:
    """biryanitformat"""

    content: str
    model: str
    provider: ModelProvider
    tier: ModelTier
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)  # araccagri (function calling) 


@dataclass
class ModelConfig:
    """modelyapilandirma"""

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 60.0

    # yeniden denestrateji
    max_retries: int = 5
    retry_delay: float = 2.0
    timeout: float = 120.0  # artekleasirizamanzamanarasindakadar 120 saniye

    # olkontrol
    cost_per_1k_prompt: float = 0.0  # her 1k prompt token ol (ogre) 
    cost_per_1k_completion: float = 0.0  # her 1k completion token ol (ogre) 


class BaseModel(ABC):
    """
    varmodeladaptortemel sinif

    Sorumluluk:
    1. tanimbir API baglanagiz
    2. saglarkullanhata islemeveyeniden denemantik
    3. destekakisveolmayanakisikiturcagriyontem
    """

    def __init__(self, config: ModelConfig, tier: ModelTier):
        self.config = config
        self.tier = tier
        self._total_usage = Usage()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        alveyaolustur HTTP istemci (gecikmebaslat) 

        altsinifolabilirileuzerine yazbuyontemilesaglarozelistemciyapilandirma. 
        varsayilanuygulakullan OpenAI uyumlu API format (base_url + Bearer token) . 
        """
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        """kapat HTTP istemci"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    @abstractmethod
    def provider(self) -> ModelProvider:
        """donussaglayiciisarettani"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """donusgercekkullanmodel adi"""
        pass

    @abstractmethod
    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        """
        olmayanakisolustur

        Args:
            messages: icinkonusmagecmis
            **kwargs: modelozelparametre

        Returns:
            ModelResponse: birformatyanit
        """
        pass

    @abstractmethod
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """
        akisolustur

        Args:
            messages: icinkonusmagecmis
            **kwargs: modelozelparametre

        Yields:
            str: herkezolusturmetinparca
        """
        pass

    async def count_tokens(self, text: str) -> int:
        """
        hesapla token sayimiktar (altsinifolabiliruzerine yazsaglardahakesinuygula) 

        varsayilanuygula: icindemetinkarakteryaklasik 1.5 token, Ingilizmetintekilkelimeyaklasik 1 token
        """
        # basittahmin
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars / 4)

    def get_cost(self, usage: Usage) -> float:
        """hesaplakezcagriol (ogre) """
        prompt_cost = (usage.prompt_tokens / 1000) * self.config.cost_per_1k_prompt
        completion_cost = (
            usage.completion_tokens / 1000
        ) * self.config.cost_per_1k_completion
        return prompt_cost + completion_cost

    def update_usage(self, usage: Usage):
        """guncellebiriktirhesapkullanmiktar"""
        self._total_usage = self._total_usage + usage

    def get_total_usage(self) -> Usage:
        """albiriktirhesapkullanmiktar"""
        return self._total_usage

    def reset_usage(self):
        """tekrarayarkullanistatistik"""
        self._total_usage = Usage()

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """
        birmesajformatdonusturicin OpenAI uyumlu API format

        altsinifolabilirileuzerine yazbuyontemilesaglarhayirayni API formatmesajdonustur. 
        """
        formatted = []
        for msg in messages:
            item: dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name  # type: ignore
            if msg.tool_calls:  # assistant mesaj aracligicagri
                item["tool_calls"] = msg.tool_calls  # type: ignore
            if msg.tool_call_id:  # tool mesaj aracligicagri ID
                item["tool_call_id"] = msg.tool_call_id
            formatted.append(item)
        return formatted

    def _build_system_prompt(self, system: Optional[str] = None) -> Optional[Message]:
        """olustursistemipucukelime"""
        if system:
            return Message(role="system", content=system)
        return None

    def _build_request_body(
        self, messages: list[Message], **kwargs
    ) -> dict[str, Any]:
        """
        olustur OpenAI uyumluistektemeltemelkisimpuan

        altsinifolabilirilecagribuyontemgelolusturtemeltemelistek, sonraeklemodelozelparametre. 
        """
        request_body: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        # ekleolabilirsecparametre
        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]
        if "tools" in kwargs and kwargs["tools"]:
            request_body["tools"] = kwargs["tools"]
            request_body["tool_choice"] = kwargs.get("tool_choice", "auto")

        return request_body

    async def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        ayristir HTTP yanit, birislehata

        Raises:
            httpx.HTTPStatusError: ne zaman API donushatadurumkodzaman
            httpx.RequestError: ne zamanag istegibasarisizzaman
        """
        response.raise_for_status()
        return response.json()

    async def _execute_with_retry(self, func, *args, **kwargs):
        """
        kemeryeniden deneyurut (kullan tenacity isaretsayigerikacin) 
        sadeceyeniden deneagasirizamansinifhata, onunofarklisikdogrubaglanfirlat. 
        """
        import httpx
        from tenacity import (
            AsyncRetrying,
            retry_if_exception,
            stop_after_attempt,
            wait_exponential,
        )

        # olabiliryeniden denefarklisiktip
        retryable_exceptions = (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.ConnectError,
            ConnectionError,
            TimeoutError,
            OSError,
        )

        def _should_retry(exc: Exception) -> bool:
            return isinstance(exc, retryable_exceptions)

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential(
                multiplier=self.config.retry_delay,
                max=self.config.retry_delay * 8,
            ),
            retry=retry_if_exception(_should_retry),
            reraise=True,
        ):
            with attempt:
                return await func(*args, **kwargs)

        return None  # unreachable

    async def _execute_with_retry(self, func, *args, **kwargs):
        """
        kemeryeniden deneyurut (kullan tenacity isaretsayigerikacin) 
        sadeceyeniden deneagasirizamansinifhata, onunofarklisikdogrubaglanfirlat. 
        """
        import httpx
        from tenacity import (
            AsyncRetrying,
            retry_if_exception,
            stop_after_attempt,
            wait_exponential,
        )

        # olabiliryeniden denefarklisiktip
        retryable_exceptions = (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.ConnectError,
            ConnectionError,
            TimeoutError,
            OSError,
        )

        def _should_retry(exc: Exception) -> bool:
            return isinstance(exc, retryable_exceptions)

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential(
                multiplier=self.config.retry_delay,
                max=self.config.retry_delay * 8,
            ),
            retry=retry_if_exception(_should_retry),
            reraise=True,
        ):
            with attempt:
                return await func(*args, **kwargs)

        return None  # unreachable
