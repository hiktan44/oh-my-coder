from __future__ import annotations

"""
yerelmodelkesfetmodul

otomatikkesfetyerel Ollama kisimyerlestirmodel, destekdinamikalmodellistevedetay. 

kullanyontem: 
    from src.core.local_model_discovery import (
        discover_ollama_models,
        get_model_info,
        is_ollama_running,
    )

    # algilama Ollama olup olmadigisatir
    if is_ollama_running():
        # alkurulummodelliste
        models = discover_ollama_models()
        for m in models:
            print(m.model_name, m.size, m.quantization)

        # altekilmodeldetay
        info = get_model_info("qwen2:7b")
        print(info.parameter_size, info.quantization, info.template)
"""


from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from src.models.ollama import OLLAMA_DEFAULT_URL

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class OllamaModelInfo:
    """
    tekil Ollama modelyapibilgi

    Attributes:
        model_name: model adi, ornegin qwen2:7b, llama3:8b
        size: modelbuyukkucuk (byte) , olabilirkendisatirdonusturicin GB/MB
        quantization: miktaryontem, ornegin q4_K_M, q5_K_M, q8_0, fp16
        modified_at: modeldosyaensonradegistirzamanarasinda
        parameter_size: parametremiktar, ornegin 7B, 13B, 72B (sadece /api/show olabiliral) 
        template: sohbetgunsablon (sadece /api/show olabiliral) 
        license: modelizinolabilirkanit (sadece /api/show olabiliral) 
        system: sistemipucu (sadece /api/show olabiliral) 
        raw: ham API yanit (saglarhata ayiklakullan) 
    """

    model_name: str
    size: int = 0
    quantization: Optional[str] = None
    modified_at: Optional[str] = None
    parameter_size: Optional[str] = field(default=None, repr=False)
    template: Optional[str] = field(default=None, repr=False)
    license: Optional[str] = field(default=None, repr=False)
    system: Optional[str] = field(default=None, repr=False)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def size_gb(self) -> float:
        """donusmodelbuyukkucuk (GB) """
        if self.size <= 0:
            return 0.0
        return round(self.size / (1024**3), 2)

    @property
    def size_mb(self) -> float:
        """donusmodelbuyukkucuk (MB) """
        if self.size <= 0:
            return 0.0
        return round(self.size / (1024**2), 2)

    def to_dict(self) -> dict[str, Any]:
        """disa aktaricinsozluk (hayiricerir raw alan) """
        return {
            "model_name": self.model_name,
            "size": self.size,
            "size_gb": self.size_gb,
            "quantization": self.quantization,
            "modified_at": self.modified_at,
            "parameter_size": self.parameter_size,
            "template": self.template,
            "license": self.license,
            "system": self.system,
        }


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

# esitle httpx client tekrarkullan timeout yapilandirma
_OLLAMA_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


def _make_client() -> httpx.Client:
    """olusturesitle httpx client, tekrarkullanbaglabaglan"""
    return httpx.Client(timeout=_OLLAMA_TIMEOUT)


def is_ollama_running(base_url: str = OLLAMA_DEFAULT_URL) -> bool:
    """
    algilama Ollama servisolup olmadigisatir

    araciligiylacagri /api/tags uc noktakarar verservisolabilirkullan. 
    Ollama henuzsatirzamandonus False, hayiryapacakfirlatfarklisik. 

    Args:
        base_url: Ollama API adres, varsayilan http://localhost:11434

    Returns:
        bool: True tablogoster Ollama servisolabilirkullan

    Example:
        >>> is_ollama_running()
        True
    """
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        with _make_client() as client:
            response = client.get(url)
            return response.status_code == 200
    except Exception:
        return False


def discover_ollama_models(
    base_url: str = OLLAMA_DEFAULT_URL,
) -> list[OllamaModelInfo]:
    """
    kesfetvaryerelkurulum Ollama model

    cagri GET /api/tags almodelliste, donusyapimodelbilgi. 
    Ollama henuzsatirzamandonusbosliste, hayiryapacakfirlatfarklisik. 

    Args:
        base_url: Ollama API adres, varsayilan http://localhost:11434

    Returns:
        List[OllamaModelInfo]: kurulummodelliste, gore modified_at dusursirasiralaliste (enyeniicindeonce) 

    Example:
        >>> models = discover_ollama_models()
        >>> for m in models:
        ...     print(f"{m.model_name} ({m.size_gb} GB)")
        qwen2:7b (4.4 GB)
        llama3:8b (4.7 GB)
    """
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        with _make_client() as client:
            response = client.get(url)
            if response.status_code != 200:
                return []
            data = response.json()

        raw_models: list[dict[str, Any]] = data.get("models", [])
        result: list[OllamaModelInfo] = []

        for raw in raw_models:
            model = OllamaModelInfo(
                model_name=raw.get("name", ""),
                size=raw.get("size", 0),
                quantization=raw.get("quantization"),
                modified_at=raw.get("modified_at"),
                raw=raw,
            )
            # filtreledusbosad
            if model.model_name:
                result.append(model)

        # gore modified_at dusursirasiralaliste
        result.sort(
            key=lambda m: m.modified_at or "",
            reverse=True,
        )
        return result

    except Exception:
        return []


def get_model_info(
    model_name: str,
    base_url: str = OLLAMA_DEFAULT_URL,
) -> Optional[OllamaModelInfo]:
    """
    altekilmodeldetaylibilgi

    cagri POST /api/show almodeldetay, icerirparametremiktar, miktaryontem, sablonvb.. 
    modelmevcut degilveya Ollama henuzsatirzamandonus None, hayiryapacakfirlatfarklisik. 

    Args:
        model_name: model adi, ornegin qwen2:7b, llama3:8b
        base_url: Ollama API adres, varsayilan http://localhost:11434

    Returns:
        Optional[OllamaModelInfo]: modeldetay, basarisizzamandonus None

    Example:
        >>> info = get_model_info("qwen2:7b")
        >>> if info:
        ...     print(info.parameter_size)
        ...     print(info.quantization)
        ...     print(info.template[:80])
        7B
        q4_K_M
        {{ if .System }}...
    """
    if not model_name or not model_name.strip():
        return None

    try:
        url = f"{base_url.rstrip('/')}/api/show"
        with _make_client() as client:
            response = client.post(
                url,
                json={"name": model_name.strip()},
            )
            if response.status_code != 200:
                return None
            data: dict[str, Any] = response.json()

        # /api/tags kisimpuan (modeldosyabilgi) 
        tags_data: dict[str, Any] = data.get("model_info", {})
        # /api/show ozelkullanalan
        parameter_size: Optional[str] = tags_data.get("parameter_size")
        # license / template / system olabiliredebiliricinde model_info ayricaolabiliredebiliricindeustkatman
        license_val = data.get("license") or tags_data.get("license")
        template_val = data.get("template") or tags_data.get("template")
        system_val = data.get("system") or tags_data.get("system")

        # /api/tags alan (egerolabilirkullan) 
        try:
            size = tags_data.get("size", 0)
        except Exception:
            size = 0

        return OllamaModelInfo(
            model_name=model_name.strip(),
            size=size,
            quantization=tags_data.get("quantization"),
            modified_at=tags_data.get("modified_at"),
            parameter_size=parameter_size,
            template=template_val,
            license=license_val,
            system=system_val,
            raw=data,
        )

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Async variants (for consistency with rest of codebase)
# ---------------------------------------------------------------------------

_async_client: Optional[httpx.AsyncClient] = None


async def _get_async_client() -> httpx.AsyncClient:
    """al/olusturglobalasenkron httpx client"""
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT)
    return _async_client


async def is_ollama_running_async(
    base_url: str = OLLAMA_DEFAULT_URL,
) -> bool:
    """asenkronsurum: algilama Ollama olup olmadigisatir"""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        client = await _get_async_client()
        response = await client.get(url)
        return response.status_code == 200
    except Exception:
        return False


async def discover_ollama_models_async(
    base_url: str = OLLAMA_DEFAULT_URL,
) -> list[OllamaModelInfo]:
    """asenkronsurum: kesfetvaryerelmodel"""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        client = await _get_async_client()
        response = await client.get(url)
        if response.status_code != 200:
            return []
        data = response.json()

        raw_models: list[dict[str, Any]] = data.get("models", [])
        result: list[OllamaModelInfo] = [
            OllamaModelInfo(
                model_name=raw.get("name", ""),
                size=raw.get("size", 0),
                quantization=raw.get("quantization"),
                modified_at=raw.get("modified_at"),
                raw=raw,
            )
            for raw in raw_models
            if raw.get("name")
        ]

        result.sort(key=lambda m: m.modified_at or "", reverse=True)
        return result

    except Exception:
        return []


async def get_model_info_async(
    model_name: str,
    base_url: str = OLLAMA_DEFAULT_URL,
) -> Optional[OllamaModelInfo]:
    """asenkronsurum: altekilmodeldetay"""
    if not model_name or not model_name.strip():
        return None

    try:
        url = f"{base_url.rstrip('/')}/api/show"
        client = await _get_async_client()
        response = await client.post(
            url,
            json={"name": model_name.strip()},
        )
        if response.status_code != 200:
            return None
        data: dict[str, Any] = response.json()

        model_info: dict[str, Any] = data.get("model_info", {})
        parameter_size: Optional[str] = model_info.get("parameter_size")
        license_val = data.get("license") or model_info.get("license")
        template_val = data.get("template") or model_info.get("template")
        system_val = data.get("system") or model_info.get("system")

        try:
            size = model_info.get("size", 0)
        except Exception:
            size = 0

        return OllamaModelInfo(
            model_name=model_name.strip(),
            size=size,
            quantization=model_info.get("quantization"),
            modified_at=model_info.get("modified_at"),
            parameter_size=parameter_size,
            template=template_val,
            license=license_val,
            system=system_val,
            raw=data,
        )

    except Exception:
        return None
