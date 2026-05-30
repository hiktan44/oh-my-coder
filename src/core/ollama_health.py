from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Ollama saglikkontrolmodul

saglar Ollama servisgenelbirlestirsaglikkontrol, modelolabilirkullanalgilamavedurumsorgu. 
icindeayaronbellekmekanizma (30 saniye) , kacinsik ping etkiperformans. 

kullanyontem: 
    from src.core.ollama_health import OllamaHealthChecker, OllamaHealthStatus

    checker = OllamaHealthChecker()
    status = checker.check_ollama()
    print(status.running, status.version, status.model_count)

    # kontrolozelmodel
    if checker.check_model_available("qwen2:7b"):
        print("modelolabilirkullan")

    # altamdurum
    info = checker.get_ollama_status()
    print(info["running"], info["models"])
"""


import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from src.core.local_model_discovery import (
    discover_ollama_models,
    is_ollama_running,
)
from src.models.ollama import OLLAMA_DEFAULT_URL

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class OllamaHealthStatus:
    """
    Ollama saglikkontrolsonuc

    Attributes:
        running: Ollama servisolup olmadigisatir
        version: Ollama surumno (ornegin 0.1.45) , servishenuzsatirzamanicin None
        model_count: altyuklemodelsayimiktar
        available_models: altyuklemodel adiliste
        latency_ms: saglikkontrolyanitgecikme (saniye) 
        last_check_time: ensonrakontrolzamanarasinda
    """

    running: bool = False
    version: Optional[str] = None
    model_count: int = 0
    available_models: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    last_check_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        """disa aktaricinsozluk, kolaydesiraveyalogkayit"""
        return {
            "running": self.running,
            "version": self.version,
            "model_count": self.model_count,
            "available_models": self.available_models,
            "latency_ms": round(self.latency_ms, 2),
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# onbellekvaretkidonem (saniye) 
_CACHE_TTL_SECONDS = 30.0

# HTTP asirizamanyapilandirma
_CONNECT_TIMEOUT = 2.0
_READ_TIMEOUT = 5.0


# ---------------------------------------------------------------------------
# Health checker
# ---------------------------------------------------------------------------


class OllamaHealthChecker:
    """
    Ollama servissaglikkontrol

    saglar: 
    - genelbirlestirsaglikkontrol (servisdurum + surum + modelliste) 
    - tekilmodelolabilirkullankontrol
    - hamdurumsozluksorgu

    ozellik: 
    - icindeayar 30 saniyesonuconbellek, kacinsikag istegi
    - olabiliryapilandirmabaglabaglanasirizaman (varsayilan 2 saniye) veokuasirizaman (varsayilan 5 saniye) 
    - tekrarkullan local_model_discovery icindekesfetmantik

    Example:
        >>> checker = OllamaHealthChecker()
        >>> status = checker.check_ollama()
        >>> print(status.running)
        True
        >>> checker.check_model_available("qwen2:7b")
        True
    """

    def __init__(
        self,
        base_url: str = OLLAMA_DEFAULT_URL,
        cache_ttl: float = _CACHE_TTL_SECONDS,
        connect_timeout: float = _CONNECT_TIMEOUT,
        read_timeout: float = _READ_TIMEOUT,
    ) -> None:
        """
        baslatsaglikkontrol

        Args:
            base_url: Ollama API adres
            cache_ttl: onbellekvaretkidonem (saniye) , varsayilan 30 saniye
            connect_timeout: baglabaglanasirizaman (saniye) , varsayilan 2 saniye
            read_timeout: okuasirizaman (saniye) , varsayilan 5 saniye
        """
        self.base_url = base_url.rstrip("/")
        self.cache_ttl = cache_ttl
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

        # onbellek
        self._cached_status: Optional[OllamaHealthStatus] = None
        self._cache_timestamp: float = 0.0

        # httpx client tekrarkullan
        self._client: Optional[httpx.Client] = None

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def check_ollama(self) -> OllamaHealthStatus:
        """
        genelbirlestirsaglikkontrol

        kontrol Ollama servisolup olmadigisatir, alsurumnovealtyuklemodelliste. 
        sonuconbellek 30 saniye, donemarasindacokkezcagridogrubaglandonusonbellekdeger. 

        Returns:
            OllamaHealthStatus: saglikkontrolsonuc
        """
        now = time.monotonic()

        # onbellekkomuticinde
        if (
            self._cached_status is not None
            and (now - self._cache_timestamp) < self.cache_ttl
        ):
            return self._cached_status

        # yurutkontrol
        status = self._do_check(now)
        self._cached_status = status
        self._cache_timestamp = now
        return status

    def check_model_available(self, model_name: str) -> bool:
        """
        kontrolozelmodelolup olmadigialtyukleolabilirkullan

        Args:
            model_name: model adi, ornegin qwen2:7b, llama3:8b

        Returns:
            bool: modelolup olmadigiolabilirkullan (altyukle) 
        """
        if not model_name or not model_name.strip():
            return False

        # oncekullanonbellekkontroltamdurum, kacinherkeztumgonderag istegi
        status = self.check_ollama()
        if not status.running:
            return False

        return model_name.strip() in status.available_models

    def get_ollama_status(self) -> dict:
        """
        al Ollama durumsozluk

        Returns:
            dict: icerir running(bool), version(Optional[str]), model_count(int), models(List[str])
        """
        status = self.check_ollama()
        return {
            "running": status.running,
            "version": status.version,
            "model_count": status.model_count,
            "models": status.available_models,
        }

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _do_check(self, timestamp: float) -> OllamaHealthStatus:
        """yurutgerceksaglikkontrol (yokonbellek) """
        start = time.perf_counter()

        # 1. kontrolservisolup olmadigisatir
        running = is_ollama_running(self.base_url)

        if not running:
            return OllamaHealthStatus(
                running=False,
                version=None,
                model_count=0,
                available_models=[],
                latency_ms=(time.perf_counter() - start) * 1000,
                last_check_time=datetime.now(),
            )

        # 2. vesatiralsurumvemodelliste
        version = self._fetch_version()
        models = discover_ollama_models(self.base_url)

        return OllamaHealthStatus(
            running=True,
            version=version,
            model_count=len(models),
            available_models=[m.model_name for m in models],
            latency_ms=(time.perf_counter() - start) * 1000,
            last_check_time=datetime.now(),
        )

    def _fetch_version(self) -> Optional[str]:
        """
        al Ollama surumno

        cagri GET /api/version uc nokta. basarisizzamandonus None. 
        """
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/version")
            if response.status_code == 200:
                data = response.json()
                return data.get("version")
            return None
        except Exception:
            return None

    def _get_client(self) -> httpx.Client:
        """al/olusturtekrarkullan httpx client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=self.connect_timeout + self.read_timeout,
            )
        return self._client

    def clear_cache(self) -> None:
        """manueltemizlehariconbellek, zorunlualtkezkontrolzamantekraryeniistek"""
        self._cached_status = None
        self._cache_timestamp = 0.0

    def close(self) -> None:
        """kapaticindekisim httpx client"""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self) -> OllamaHealthChecker:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
