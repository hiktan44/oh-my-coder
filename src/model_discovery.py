from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Model Discovery - dinamikmodelkesfetsistem

heruretici API cekolabilirkullanmodelliste, algilamayenimodel
"""


import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx


class ModelDiscovery:
    """dinamikmodelkesfet: heruretici API cekolabilirkullanmodelliste"""

    # heruretici /models uc noktayapilandirma
    PROVIDER_APIS = {
        "deepseek": {
            "url": "https://api.deepseek.com/models",
            "key_env": "DEEPSEEK_API_KEY",
            "format": "openai",  # OpenAI uyumluformat
        },
        "glm": {
            "url": "https://open.bigmodel.cn/api/paas/v4/models",
            "key_env": "ZHIPUAI_API_KEY",
            "format": "openai",
        },
        "tongyi": {
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
            "key_env": "DASHSCOPE_API_KEY",
            "format": "openai",
        },
        "kimi": {
            "url": "https://api.moonshot.cn/v1/models",
            "key_env": "KIMI_API_KEY",
            "format": "openai",
        },
        "doubao": {
            "url": "https://ark.cn-beijing.volces.com/api/v3/models",
            "key_env": "DOUBAO_API_KEY",
            "format": "openai",
        },
        "wenxin": {
            # yuzderecemetinkalpyokvarstandart /models uc nokta, atladinamikkesfet
            "skip": True,
            "reason": "yuzderecemetinkalpyokvarstandart /models uc nokta",
        },
        "hunyuan": {
            # Tencent Hunyuanyokvarstandart /models uc nokta, atla
            "skip": True,
            "reason": "Tencent Hunyuanyokvarstandart /models uc nokta",
        },
        "minimax": {
            "url": "https://api.minimax.chat/v1/models",
            "key_env": "MINIMAX_API_KEY",
            "format": "openai",
        },
        "tiangong": {
            # Tiangongyokvarstandart /models uc nokta, atla
            "skip": True,
            "reason": "Tiangongyokvarstandart /models uc nokta",
        },
        "spark": {
            # iFlytek Sparkyokvarstandart /models uc nokta, atla
            "skip": True,
            "reason": "iFlytek Sparkyokvarstandart /models uc nokta",
        },
        "baichuan": {
            "url": "https://api.baichuan-ai.com/v1/models",
            "key_env": "BAICHUAN_API_KEY",
            "format": "openai",
        },
        "openai": {
            "url": "https://api.openai.com/v1/models",
            "key_env": "OPENAI_API_KEY",
            "format": "openai",
        },
        "anthropic": {
            # Anthropic yokvar /models uc nokta, atla
            "skip": True,
            "reason": "Anthropic yokvarstandart /models uc nokta",
        },
        "google": {
            # Google kullanhayirayni API format, geçicizamanatla
            "skip": True,
            "reason": "Google API formathayiruyumlu",
        },
        "mimo": {
            # kucukmetre MiMo yokvarstandart /models uc nokta, atla
            "skip": True,
            "reason": "kucukmetre MiMo yokvarstandart /models uc nokta",
        },
    }

    # onbellekdosyayol
    CACHE_FILE = Path.home() / ".omc" / "discovered_models.json"
    CACHE_TTL_HOURS = 24

    def __init__(self):
        self.cache_file = self.CACHE_FILE

    def _fetch_provider_models(
        self, provider: str, config: dict, timeout: int = 5
    ) -> list[dict]:
        """
        altekilureticimodelliste

        Args:
            provider: uretici ID
            config: ureticiyapilandirma
            timeout: istekasirizamanzamanarasinda (saniye) 

        Returns:
            modelliste, basarisizdonusbosliste
        """
        # kontrololup olmadigiatla
        if config.get("skip"):
            return []

        url = config.get("url")
        key_env = config.get("key_env")
        api_format = config.get("format", "openai")

        if not url or not key_env:
            return []

        # kontrol API Key
        api_key = os.getenv(key_env)
        if not api_key:
            return []

        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = httpx.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()


            # ayristir OpenAI uyumluformat
            if api_format == "openai":
                models = data.get("data", [])
                # filtreledusolmayanicinkonusmamodel (ornegin embedding, tts vb.) 
                chat_models = []
                for m in models:
                    model_id = m.get("id", "")
                    # basittekilbaslatgondertarz: harir tutbelirginolmayanicinkonusmamodel
                    skip_keywords = [
                        "embedding",
                        "tts",
                        "whisper",
                        "dall-e",
                        "image",
                        "audio",
                        "moderation",
                    ]
                    if any(kw in model_id.lower() for kw in skip_keywords):
                        continue
                    chat_models.append(
                        {
                            "id": model_id,
                            "created": m.get("created"),
                            "object": m.get("object"),
                            "owned_by": m.get("owned_by"),
                        }
                    )
                return chat_models

            return []

        except httpx.TimeoutException:
            return []
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []
        except Exception:
            return []

    def discover_all(self, timeout: int = 5) -> dict[str, list[dict]]:
        """
        vegondercagrivardestekdinamikkesfeturetici API

        Args:
            timeout: heristekasirizamanzamanarasinda (saniye) 

        Returns:
            {provider: [model_info, ...]}
            asirizaman/yok key/raporyanlis  provider donusbosliste, hayiretkionuno
        """
        results = {}

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_provider = {
                executor.submit(
                    self._fetch_provider_models, provider, config, timeout
                ): provider
                for provider, config in self.PROVIDER_APIS.items()
                if not config.get("skip")
            }

            for future in as_completed(future_to_provider):
                provider = future_to_provider[future]
                try:
                    models = future.result()
                    results[provider] = models
                except Exception:
                    results[provider] = []

        return results

    def get_cached(self) -> Optional[dict]:
        """
        okuyerelonbellek

        Returns:
            onbelleksayigoreveya None (egeronbellekmevcut degilveyadonem) 
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            cached_at = data.get("cached_at")
            if not cached_at:
                return None

            # ayristironbellekzamanarasinda
            try:
                cache_time = datetime.fromisoformat(cached_at)
                expiry_time = cache_time + timedelta(hours=self.CACHE_TTL_HOURS)

                if datetime.now() > expiry_time:
                    return None  # onbellekdonem

                return data
            except (ValueError, TypeError):
                return None

        except (OSError, json.JSONDecodeError):
            return None

    def save_cache(self, data: dict) -> None:
        """
        kaydetkadaryerelonbellek

        Args:
            data: isteronbelleksayigore
        """
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "providers": data,
        }

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def compare_with_builtin(
        self,
        discovered: dict[str, list[dict]],
        builtin_models: list[dict],
    ) -> dict[str, Any]:
        """
        icinkiyaskesfetmodel vs icindeayarmodel

        Args:
            discovered: discover_all() donussonuc
            builtin_models: icindeayarmodelliste (ornegin BUILTIN_CATWALK_MODELS) 

        Returns:
            {
                "new_models": [...],      # ureticivarancakicindeayaryokvar (yenimodel! ) 
                "removed_models": [...],  # icindeayarvarancakureticiyokdonus (olabiliredebiliraltsatir) 
                "unchanged": [...],       # bir
            }
        """
        # olusturicindeayarmodel ID setbirlestir
        builtin_model_ids = set()
        builtin_by_provider: dict[str, set[str]] = {}

        for m in builtin_models:
            provider = m.get("provider", "")
            model_id = m.get("model", "")
            if provider and model_id:
                builtin_model_ids.add(f"{provider}:{model_id}")
                if provider not in builtin_by_provider:
                    builtin_by_provider[provider] = set()
                builtin_by_provider[provider].add(model_id)

        # icinkiyassonuc
        new_models = []
        removed_models = []
        unchanged = []

        for provider, models in discovered.items():
            builtin_ids = builtin_by_provider.get(provider, set())

            for m in models:
                model_id = m.get("id", "")
                full_id = f"{provider}:{model_id}"

                if model_id in builtin_ids or full_id in builtin_model_ids:
                    unchanged.append(
                        {
                            "provider": provider,
                            "model_id": model_id,
                            "source": "discovery",
                        }
                    )
                else:
                    new_models.append(
                        {
                            "provider": provider,
                            "model_id": model_id,
                            "created": m.get("created"),
                            "owned_by": m.get("owned_by"),
                        }
                    )

        # kontrololabiliredebiliraltsatirmodel (icindeayarvarancakureticiyokdonus) 
        discovered_ids = set()
        for provider, models in discovered.items():
            for m in models:
                model_id = m.get("id", "")
                discovered_ids.add(f"{provider}:{model_id}")

        for m in builtin_models:
            provider = m.get("provider", "")
            model_id = m.get("model", "")
            full_id = f"{provider}:{model_id}"

            # egerbuureticivardonussayigore, ancakicindeayarmodelhayiricindedonuslisteicinde
            if discovered.get(provider):
                if full_id not in discovered_ids and model_id not in {
                    mm.get("id", "") for mm in discovered.get(provider, [])
                }:
                    removed_models.append(
                        {
                            "provider": provider,
                            "model_id": model_id,
                            "name": m.get("name", ""),
                        }
                    )

        return {
            "new_models": new_models,
            "removed_models": removed_models,
            "unchanged": unchanged,
        }

    def sync(self, force: bool = False, timeout: int = 5) -> dict[str, Any]:
        """
        yurutesitlekontrol

        Args:
            force: olup olmadigizorunluyenileyeni (yoksayonbellek) 
            timeout: istekasirizamanzamanarasinda

        Returns:
            esitlesonuc, icerirdurumbilgi
        """
        if not force:
            cached = self.get_cached()
            if cached:
                return {
                    "status": "cached",
                    "message": "kullanonbelleksayigore",
                    "data": cached.get("providers", {}),
                    "cached_at": cached.get("cached_at"),
                }

        # yurutkesfet
        discovered = self.discover_all(timeout=timeout)

        # kaydetonbellek
        self.save_cache(discovered)

        # istatistiksonuc
        total_models = sum(len(models) for models in discovered.values())
        active_providers = [p for p, m in discovered.items() if m]

        return {
            "status": "success",
            "message": f"kesfet {total_models} modelgelkendi {len(active_providers)} uretici",
            "data": discovered,
            "providers": {
                provider: len(models) for provider, models in discovered.items()
            },
        }


def get_discovery_summary(
    builtin_models: list[dict],
    discovery: Optional[ModelDiscovery] = None,
) -> dict[str, Any]:
    """
    alkesfetalintiister (kullande omc model list sonipucu) 

    Args:
        builtin_models: icindeayarmodelliste
        discovery: ModelDiscovery ornek (olabilirsec) 

    Returns:
        alintiisterbilgi
    """
    if discovery is None:
        discovery = ModelDiscovery()

    # denealonbellekveyayurutkesfet
    cached = discovery.get_cached()

    if cached:
        discovered = cached.get("providers", {})
        is_cached = True
    else:
        # sonraplatformsessizkesfet (hayirblokla) 
        discovered = discovery.discover_all(timeout=3)
        if discovered:
            discovery.save_cache(discovered)
        is_cached = False

    if not discovered:
        return {"has_new": False, "new_models": [], "is_cached": False}

    # icinkiyas
    comparison = discovery.compare_with_builtin(discovered, builtin_models)
    new_models = comparison.get("new_models", [])

    return {
        "has_new": len(new_models) > 0,
        "new_models": new_models,
        "is_cached": is_cached,
        "total_discovered": sum(len(m) for m in discovered.values()),
    }


if __name__ == "__main__":
    # testkod
    discovery = ModelDiscovery()
    result = discovery.sync(force=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
