from __future__ import annotations

"""
Yerel model API

Ollama yerel modellerinin yönetim ve sorgulama işlevlerini sağlar.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/local-models", tags=["local-models"])


class LocalModelInfo(BaseModel):
    """Yerel model bilgisi"""

    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None
    tier: Optional[str] = None
    description: Optional[str] = None
    available: bool = True


class OllamaStatus(BaseModel):
    """Ollama servis durumu"""

    available: bool
    base_url: str
    models: list[LocalModelInfo] = []
    error: Optional[str] = None


@router.get("/status", response_model=OllamaStatus)
async def get_ollama_status() -> OllamaStatus:
    """
    Ollama servis durumunu ve kullanılabilir model listesini al

    Returns:
        OllamaStatus: Servis durumu ve model listesi
    """
    import os

    from ..models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    try:
        is_available = OllamaModel.is_available(base_url)

        if not is_available:
            return OllamaStatus(
                available=False,
                base_url=base_url,
                models=[],
                error="Ollama servisi çalışmıyor, lütfen şunu çalıştırın: ollama serve",
            )

        # Yerel model listesini al
        raw_models = OllamaModel.list_models(base_url)

        # LocalModelInfo'ya dönüştür
        models = []
        for m in raw_models:
            # tier çıkarımı yap
            name = m.get("name", "")
            tier = "medium"  # varsayılan
            if ":1.5b" in name or ":7b" in name:
                tier = "low"
            elif ":70b" in name or ":72b" in name or ":33b" in name:
                tier = "high"

            # Boyutu biçimlendir
            size_bytes = m.get("size", 0)
            if size_bytes:
                if size_bytes > 1e9:
                    size = f"{size_bytes / 1e9:.1f} GB"
                else:
                    size = f"{size_bytes / 1e6:.0f} MB"
            else:
                size = None

            models.append(
                LocalModelInfo(
                    name=name,
                    size=size,
                    modified_at=m.get("modified_at"),
                    tier=tier,
                    description=_get_model_description(name),
                    available=True,
                )
            )

        return OllamaStatus(
            available=True,
            base_url=base_url,
            models=models,
        )

    except Exception as e:
        return OllamaStatus(
            available=False, base_url=base_url, models=[], error=type(e).__name__
        )


@router.get("/models", response_model=list[LocalModelInfo])
async def list_local_models() -> list[LocalModelInfo]:
    """
    Yerel olarak kullanılabilen tüm modelleri listele

    Returns:
        List[LocalModelInfo]: Model listesi
    """
    import os

    from ..models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    if not OllamaModel.is_available(base_url):
        return []

    raw_models = OllamaModel.list_models(base_url)
    models = []

    for m in raw_models:
        name = m.get("name", "")
        tier = "medium"
        if ":1.5b" in name or ":7b" in name:
            tier = "low"
        elif ":70b" in name or ":72b" in name or ":33b" in name:
            tier = "high"

        # Boyutu biçimlendir
        size_bytes = m.get("size", 0)
        if size_bytes:
            if size_bytes > 1e9:
                size = f"{size_bytes / 1e9:.1f} GB"
            else:
                size = f"{size_bytes / 1e6:.0f} MB"
        else:
            size = None

        models.append(
            LocalModelInfo(
                name=name,
                size=size,
                modified_at=m.get("modified_at"),
                tier=tier,
                description=_get_model_description(name),
                available=True,
            )
        )

    return models


@router.post("/pull/{model_name}")
async def pull_model(model_name: str) -> dict[str, Any]:
    """
    Modeli yerel sisteme indir

    Args:
        model_name: Model adı (örn. qwen2:7b)

    Returns:
        İndirme durumu
    """
    from ..models.ollama import OllamaModel

    try:
        success = OllamaModel.pull_model(model_name)
        if success:
            return {
                "status": "success",
                "message": f"Model {model_name} başarıyla indirildi",
            }
        return {
            "status": "failed",
            "message": f"Model {model_name} indirilemedi",
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/recommended")
async def get_recommended_models() -> list[dict[str, Any]]:
    """
    Önerilen yerel model listesini al

    Returns:
        Önerilen model listesi (yetenek seviyesine göre)
    """
    from ..models.ollama import OLLAMA_MODELS

    result = []
    for tier, models in OLLAMA_MODELS.items():
        for m in models:
            result.append(
                {
                    "name": m["name"],
                    "tier": tier.value,
                    "description": m["desc"],
                    "context_length": m["context"],
                    "installed": False,  # Gerçek kontrol gerekir
                }
            )

    return result


def _get_model_description(model_name: str) -> str:
    """Model açıklamasını al"""
    descriptions = {
        "qwen2": "Alibaba Tongyi 2 - Güçlü Çince yetenekleri",
        "llama3": "Meta Llama 3 - Genel amaçlı sohbet modeli",
        "mistral": "Mistral AI - İyi dengelenmiş",
        "codellama": "Meta Code Llama - Kod üretimine özel",
        "deepseek-coder": "DeepSeek Coder - Kod üretimi",
        "gemma": "Google Gemma - Hafif model",
        "mixtral": "Mixtral MoE - Yüksek kaliteli çıktı",
        "phi3": "Microsoft Phi-3 - Küçük ama güçlü",
    }

    for key, desc in descriptions.items():
        if key in model_name.lower():
            return desc

    return "Açık kaynak büyük dil modeli"
