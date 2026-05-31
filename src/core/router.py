from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
modelyoltarafindan - akilliedebilirsecseceniyimodel

cekirdekIslev:
1. goregorevtipsecsecbirlestiruygunmodelkatmanseviye
2. goreolonhesaplasecsecsaglayici
3. destekarizadonusturhareket (fallback) 
4. kayityoltarafindankararkullandeiyi
5. yanitonbellek (kacintekrartekraristek) 
6. artguclulogvehata isleme

tasarimdusunceyol: 
asilprojekullan haiku/sonnet/opus uckatmanmodelyoltarafindan, bolumatla 30-50% token. 
benlergenisleticincoksaglayiciyoltarafindan, oncelikkullan DeepSeek (ucretsiz) , gerekliisterzamanyetenekcagriucretlimodel. 
"""

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# yukle .env dosya, saglar DEFAULT_MODEL vb.yapilandirmaedebilirdogruoku
load_dotenv(Path.home() / ".omc" / ".env", override=False)
load_dotenv(Path(".env"), override=False)

from typing import Any, Optional

import httpx
import yaml

from ..models.base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelResponse,
    ModelTier,
    Usage,
)
from ..models.deepseek import DeepSeekModel
from ..utils.api_key_mask import mask_api_key

# ============================================================
# kullaniciozelmodeldizin
# ============================================================
USER_MODELS_DIR = Path.home() / ".omc" / "models"

# ============================================================
# Logger
# ============================================================
logger = logging.getLogger("omc.router")


# ============================================================
# Task Type Enum
# ============================================================
class TaskType:
    """gorevtip - kullandeyoltarafindankarar (kullansinifkacin Enum sirasorun) """

    EXPLORE = "explore"
    SIMPLE_QA = "simple_qa"
    FORMATTING = "formatting"
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    TESTING = "testing"
    REFACTORING = "refactoring"
    ARCHITECTURE = "architecture"
    SECURITY_REVIEW = "security_review"
    CODE_REVIEW = "code_review"
    PLANNING = "planning"

    @classmethod
    def all(cls) -> list[str]:
        return [
            cls.EXPLORE,
            cls.SIMPLE_QA,
            cls.FORMATTING,
            cls.CODE_GENERATION,
            cls.DEBUGGING,
            cls.TESTING,
            cls.REFACTORING,
            cls.ARCHITECTURE,
            cls.SECURITY_REVIEW,
            cls.CODE_REVIEW,
            cls.PLANNING,
        ]


# ============================================================
# gorevtipkadarmodelkatmanseviyeesle
# ============================================================
_TASK_TIER_MAPPING: dict[str, str] = {
    # LOW tier - hizlihizkolayuygun
    TaskType.EXPLORE: "low",
    TaskType.SIMPLE_QA: "low",
    TaskType.FORMATTING: "low",
    # MEDIUM tier - denge
    TaskType.CODE_GENERATION: "medium",
    TaskType.DEBUGGING: "medium",
    TaskType.TESTING: "medium",
    TaskType.REFACTORING: "medium",
    # HIGH tier - enyuksekkalitemiktar
    TaskType.ARCHITECTURE: "high",
    TaskType.SECURITY_REVIEW: "high",
    TaskType.CODE_REVIEW: "high",
    TaskType.PLANNING: "high",
}


# ============================================================
# Router Config
# ============================================================
@dataclass
class RouterConfig:
    """yoltarafindanyapilandirma"""

    # API Keys (ortam degiskenmiktaroku) 
    deepseek_api_key: Optional[str] = None
    wenxin_api_key: Optional[str] = None
    tongyi_api_key: Optional[str] = None
    glm_api_key: Optional[str] = None
    minimax_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None
    hunyuan_api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # Google Gemini (ücretli)
    mimo_api_key: Optional[str] = None  # Xiaomi MiMo (Token Plan: tp-... key prefix)
    mimo_base_url: Optional[str] = None  # MiMo Plan URL override (ör. token-plan-sgp.xiaomimimo.com/v1)

    # Ollama yerel model yapılandırması
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None  # ornegin qwen2:7b
    prefer_local: bool = True  # oncelikkullanyerelmodel

    # olonhesapla (ogre) 
    daily_budget: float = 10.0

    # arizadonusturhareketsira
    fallback_order: list[str] = field(default_factory=list)

    # onbellekyapilandirma
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 puandakikaonbellek
    cache_max_entries: int = 100

    def __post_init__(self):
        # 1)  ~/.omc/config.json yukle API Keys (Web UI ayarlaayarsayfayazgiris) 
        self._load_from_config_file()

        # 2) ortam değişkeni üzerine yaz (öncelik en yüksek)
        # Placeholder değerleri (your_api_key vb.) gerçek anahtar sayılmasın
        def _env(name: str) -> Optional[str]:
            v = os.getenv(name, "").strip()
            if not v or v.lower().startswith("your_") or v in ("xxx", "changeme"):
                return None
            return v

        self.deepseek_api_key = self.deepseek_api_key or _env("DEEPSEEK_API_KEY")
        self.wenxin_api_key = self.wenxin_api_key or _env("WENXIN_API_KEY")
        self.tongyi_api_key = self.tongyi_api_key or _env("TONGYI_API_KEY")
        self.glm_api_key = self.glm_api_key or _env("GLM_API_KEY") or _env("ZHIPUAI_API_KEY")
        self.minimax_api_key = self.minimax_api_key or _env("MINIMAX_API_KEY")
        self.kimi_api_key = self.kimi_api_key or _env("KIMI_API_KEY")
        self.hunyuan_api_key = self.hunyuan_api_key or _env("HUNYUAN_API_KEY")
        self.doubao_api_key = self.doubao_api_key or _env("DOUBAO_API_KEY")
        self.gemini_api_key = self.gemini_api_key or _env("GEMINI_API_KEY")
        self.mimo_api_key = self.mimo_api_key or _env("MIMO_API_KEY") or _env("XIAOMI_MIMO_API_KEY")
        self.mimo_base_url = self.mimo_base_url or _env("MIMO_BASE_URL")

        # 3) Ollama yapilandirma
        self.ollama_base_url = self.ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.ollama_model = self.ollama_model or os.getenv("OLLAMA_MODEL", "qwen2:7b")
        self.prefer_local = os.getenv("PREFER_LOCAL_MODEL", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        # 3b) okukullaniciyapilandirmavarsayilanmodel (oncelikseviye: ortam degiskenmiktar > config.json) 
        # uyumlu OMC_DEFAULT_MODEL (ortam degiskenmiktar) , DEFAULT_MODEL (.env) ve defaults.model (config.json) 
        default_model = os.getenv("OMC_DEFAULT_MODEL") or os.getenv("DEFAULT_MODEL", "")
        if not default_model:
            # dene ~/.omc/config.json oku defaults.model
            try:
                config_path = Path.home() / ".omc" / "config.json"
                if config_path.exists():
                    import json
                    with open(config_path, encoding="utf-8") as f:
                        data = json.load(f)
                    default_model = data.get("defaults", {}).get("model", "")
            except Exception:
                pass

        # 4) varsayilanarizadonusturhareketsira (oncelikyerelmodel, sonraucretsiz/kolayuygunbulutuc) 
        # kullaniciyapilandirmavarsayilanmodelkaliciuzaksiralaicindeincibirkonum, vehayirdirsertduzenlekod deepseek
        if not self.fallback_order:
            prefer_local = self.prefer_local

            # kullanbulutuchazirlasecliste (hayiricerirollamavekullanicivarsayilanmodel) 
            cloud_fallback = [
                "deepseek",  # ücretsiz kota yüksek
                "kimi",  # uzun bağlam
                "doubao",  # fiyat/performans yüksek
                "minimax",  # MiniMax
                "glm",  # Zhipu
                "tongyi",  # Tongyi
                "wenxin",  # Wenxin
                "hunyuan",  # Hunyuan
                "gemini",  # Google Gemini (ücretli, premium fallback)
            ]

            if default_model and default_model != "ollama":
                # model ID → provider isimesle (frontend glm-4-flash vb.model ID) 
                _MODEL_ID_TO_PROVIDER = {
                    "deepseek-chat": "deepseek",
                    "glm-4-flash": "glm",
                    "glm-4": "glm",
                    "glm-4-plus": "glm",
                    "MiniMax-Text-01": "minimax",
                    "moonshot-v1-128k": "kimi",
                    "moonshot-v1-8k": "kimi",
                    "moonshot-v1-32k": "kimi",
                    "doubao-pro-32k": "doubao",
                    "ernie-4.0-8k-latest": "wenxin",
                    "qwen-plus": "tongyi",
                    "qwen-turbo": "tongyi",
                    "qwen-max": "tongyi",
                    "hunyuan-turbo": "hunyuan",
                    "hunyuan-pro": "hunyuan",
                }
                # eger default_model dirmodel ID, donusturicin provider isim
                default_provider = _MODEL_ID_TO_PROVIDER.get(
                    default_model, default_model
                )
                # kullaniciyapilandirmavarsayilanmodel (ornegin glm, kimi vb.) takgiriskadarincibirkonum
                if default_provider in cloud_fallback:
                    cloud_fallback.remove(default_provider)
                cloud_fallback.insert(0, default_provider)

            if prefer_local:
                self.fallback_order = ["ollama"] + cloud_fallback
            else:
                self.fallback_order = cloud_fallback + ["ollama"]  # yerel model son seçenek

    def _load_from_config_file(self) -> None:
        """ ~/.omc/config.json oku API Keys (Web UI ayarlaayarkaydethedefisaretdosya) """
        config_path = Path.home() / ".omc" / "config.json"
        if not config_path.exists():
            return
        try:
            import json

            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            models = data.get("models", {})
            if not isinstance(models, dict):
                return
            # provider name → RouterConfig field esle
            _key_map = {
                "deepseek": "deepseek_api_key",
                "glm": "glm_api_key",
                "minimax": "minimax_api_key",
                "mimo": "mimo_api_key",
                "kimi": "kimi_api_key",
                "doubao": "doubao_api_key",
                "tongyi": "tongyi_api_key",
                "wenxin": "wenxin_api_key",
                "hunyuan": "hunyuan_api_key",
                "gemini": "gemini_api_key",
                "tiangong": None,  # henüz karşılık gelen alan yok
                "baichuan": None,  # henüz karşılık gelen alan yok
            }
            for provider, field_name in _key_map.items():
                if not field_name:
                    continue
                entry = models.get(provider, {})
                if not isinstance(entry, dict):
                    continue
                key_val = entry.get("api_key", "")
                if key_val and isinstance(key_val, str) and not key_val.startswith("*"):
                    current = getattr(self, field_name, None)
                    if not current:
                        setattr(self, field_name, key_val)
                        logger.debug(f" config.json yukle {provider} API Key")
        except Exception as e:
            logger.warning(f"oku ~/.omc/config.json basarisiz: {e}")


# ============================================================
# Routing Decision
# ============================================================
@dataclass
class RoutingDecision:
    """yoltarafindankararkayit"""

    task_type: str
    selected_provider: str
    selected_tier: str  # "low" | "medium" | "high"
    reason: str
    estimated_cost: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# Response Cache
# ============================================================
class ResponseCache:
    """
    basittekil LRU onbellek, goremesajicerikhashdepolamayanit

    uygunkullansenaryo: 
    - tekrartekrarkesfetistek
    - aynianalizistek (proje yapisihenuzdegiszaman) 
    - aynisorunbasittekil QA
    """

    def __init__(self, max_entries: int = 100, ttl_seconds: int = 300):
        self._cache: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []  # basittekil FIFO (olmayangercek LRU, ancakyeterlikullan) 
        self._max_entries = max_entries
        self._ttl = ttl_seconds

    def _make_key(self, messages: list[Message]) -> str:
        """goremesajicerikolusturonbellek key"""
        content = "".join(m.content for m in messages)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, messages: list[Message]) -> Optional[ModelResponse]:
        """alonbellekyanit"""
        key = self._make_key(messages)
        entry = self._cache.get(key)

        if entry is None:
            return None

        # kontrololup olmadigidonem
        age = (datetime.now() - entry["cached_at"]).total_seconds()
        if age > self._ttl:
            del self._cache[key]
            self._order.remove(key)
            return None

        logger.debug(f"Cache hit: {key[:8]}... (age={age:.1f}s)")
        return entry["response"]

    def set(self, messages: list[Message], response: ModelResponse) -> None:
        """onbellekyanit"""
        key = self._make_key(messages)

        # LRU ele
        if len(self._cache) >= self._max_entries and key not in self._cache:
            oldest = self._order.pop(0)
            del self._cache[oldest]

        self._cache[key] = {
            "response": response,
            "cached_at": datetime.now(),
        }
        if key not in self._order:
            self._order.append(key)

    def clear(self) -> None:
        """temizlebosonbellek"""
        self._cache.clear()
        self._order.clear()

    def stats(self) -> dict[str, int]:
        """onbellekistatistik"""
        total = len(self._cache)
        expired = sum(
            1
            for e in self._cache.values()
            if (datetime.now() - e["cached_at"]).total_seconds() > self._ttl
        )
        return {
            "total": total,
            "active": total - expired,
            "max": self._max_entries,
            "ttl_seconds": self._ttl,
        }


# ============================================================
# Model Router
# ============================================================
class ModelRouter:
    """
    modelyoltarafindan

    cekirdekyontem: 
    - select():       secseceniyimodel
    - route_and_call(): yoltarafindanveyurut (kemerarizadonusturhareket + onbellek) 
    - get_stats():    alyoltarafindanistatistik
    """

    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig()
        self._models: dict[str, dict[str, BaseModel]] = {}
        self._decision_history: list[RoutingDecision] = []
        self._total_cost = 0.0
        self._cache = (
            ResponseCache(
                max_entries=self.config.cache_max_entries,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            if self.config.cache_enabled
            else None
        )

        self._initialize_models()

    def _initialize_models(self) -> None:
        """baslatvarolabilirkullanmodel (tembelbaslat) """
        # Ollama yerelmodel (oncelikalgilama) 
        try:
            from ..models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

            base_url = self.config.ollama_base_url or OLLAMA_DEFAULT_URL
            if OllamaModel.is_available(base_url):
                model_name = self.config.ollama_model or "qwen2:7b"
                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key="", base_url=base_url)
                    self._models.setdefault("ollama", {})[tier] = OllamaModel(
                        cfg, ModelTier(tier), model_name=model_name
                    )
                logger.info(f"Ollama yerelmodel başlatıldı ({model_name})")

                # listeleolabilirkullanmodel
                available = OllamaModel.list_models(base_url)
                if available:
                    logger.info(f"yerelolabilirkullanmodel: {[m['name'] for m in available[:5]]}")
            else:
                logger.debug(f"Ollama servishayirolabilirkullan ({base_url})")
        except Exception as e:
            logger.debug(f"Ollama baslatatla: {e}")

        # DeepSeek
        if self.config.deepseek_api_key:
            try:
                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.deepseek_api_key)
                    self._models.setdefault("deepseek", {})[tier] = DeepSeekModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("DeepSeek model başlatıldı")
            except Exception as e:
                logger.warning(f"DeepSeek başlatma başarısız: {mask_api_key(str(e))}")

        # Wenxin
        wenxin_secret = os.getenv("WENXIN_SECRET_KEY")
        if self.config.wenxin_api_key and wenxin_secret:
            try:
                from ..models.wenxin import WenxinModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.wenxin_api_key)
                    self._models.setdefault("wenxin", {})[tier] = WenxinModel(
                        cfg, ModelTier(tier), secret_key=wenxin_secret
                    )
                logger.info("Wenxinmodel başlatıldı")
            except Exception as e:
                logger.warning(f"Wenxinbaşlatma başarısız: {mask_api_key(str(e))}")

        # Tongyi
        if self.config.tongyi_api_key:
            try:
                from ..models.tongyi import TongyiModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.tongyi_api_key)
                    self._models.setdefault("tongyi", {})[tier] = TongyiModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("Tongyimodel başlatıldı")
            except Exception as e:
                logger.warning(f"Tongyibaşlatma başarısız: {mask_api_key(str(e))}")

        # Zhipu GLM
        if self.config.glm_api_key:
            try:
                from ..models.glm import GLMModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.glm_api_key)
                    self._models.setdefault("glm", {})[tier] = GLMModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("Zhipu GLM model başlatıldı")
            except Exception as e:
                logger.warning(f"Zhipu GLM başlatma başarısız: {mask_api_key(str(e))}")

        # Xiaomi MiMo (Token Plan veya standart)
        if self.config.mimo_api_key:
            try:
                from ..models.mimo import MimoModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(
                        api_key=self.config.mimo_api_key,
                        base_url=self.config.mimo_base_url,
                    )
                    self._models.setdefault("mimo", {})[tier] = MimoModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("Xiaomi MiMo modeli başlatıldı")
            except Exception as e:
                logger.warning(f"MiMo başlatma hatası: {mask_api_key(str(e))}")

        # Google Gemini (ücretli)
        if self.config.gemini_api_key:
            try:
                from ..models.gemini import GeminiModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.gemini_api_key)
                    self._models.setdefault("gemini", {})[tier] = GeminiModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("Google Gemini modeli başlatıldı")
            except Exception as e:
                logger.warning(f"Gemini başlatma hatası: {mask_api_key(str(e))}")

        # MiniMax
        if self.config.minimax_api_key:
            try:
                from ..models.minimax import MiniMaxModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.minimax_api_key)
                    self._models.setdefault("minimax", {})[tier] = MiniMaxModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("MiniMax model başlatıldı")
            except Exception as e:
                logger.warning(f"MiniMax başlatma başarısız: {mask_api_key(str(e))}")

        # Kimi
        if self.config.kimi_api_key:
            try:
                from ..models.kimi import KimiModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.kimi_api_key)
                    self._models.setdefault("kimi", {})[tier] = KimiModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("Kimi model başlatıldı")
            except Exception as e:
                logger.warning(f"Kimi başlatma başarısız: {mask_api_key(str(e))}")

        # Tencent Hunyuan
        if self.config.hunyuan_api_key:
            try:
                from ..models.hunyuan import HunyuanModel

                hunyuan_secret = os.getenv("HUNYUAN_SECRET_KEY")
                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.hunyuan_api_key)
                    self._models.setdefault("hunyuan", {})[tier] = HunyuanModel(
                        cfg, ModelTier(tier), secret_key=hunyuan_secret
                    )
                logger.info("Tencent Hunyuanmodel başlatıldı")
            except Exception as e:
                logger.warning(f"Tencent Hunyuanbaşlatma başarısız: {mask_api_key(str(e))}")

        # bytepaket
        if self.config.doubao_api_key:
            try:
                from ..models.doubao import DoubaoModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.doubao_api_key)
                    self._models.setdefault("doubao", {})[tier] = DoubaoModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("bytepaketmodel başlatıldı")
            except Exception as e:
                logger.warning(f"bytepaketbaşlatma başarısız: {mask_api_key(str(e))}")

        # ============================================================
        # yuklekullaniciozelmodelyapilandirma (~/.omc/models/*.yaml)
        # ============================================================
        if USER_MODELS_DIR.exists():
            self._load_user_models()

        # kayitolabilirkullansaglayici
        available = list(self._models.keys())
        logger.info(f"olabilirkullanmodelsaglayici: {available or 'yok'}")

    def _load_user_models(self) -> None:
        """
        yuklekullaniciozelmodelyapilandirma (~/.omc/models/*.yaml)

        destekkullaniciekleherhangi OpenAI uyumlumodelsaglayici. 
        yapilandirma dosyasiformatgor: examples/model-config.yaml
        """
        if not USER_MODELS_DIR.exists():
            return

        loaded_count = 0
        for yaml_file in USER_MODELS_DIR.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)

                if not cfg or not isinstance(cfg, dict):
                    continue

                # kontroldogrulagerekliisteralan
                required = ["provider", "model"]
                if not all(k in cfg for k in required):
                    logger.warning(f"atla {yaml_file.name}: eksikazgerekliisteralan")
                    continue

                provider = cfg["provider"]
                model_name = cfg["model"]

                # egerbu provider varicindeayarmodel, atla
                if provider in self._models:
                    logger.debug(f"atla {provider}: varicindeayarmodel")
                    continue

                # al API Key
                api_key_env = cfg.get("api_key_env", f"{provider.upper()}_API_KEY")
                api_key = os.getenv(api_key_env)

                if not api_key:
                    logger.debug(f"atla {provider}: ortam degiskenmiktar {api_key_env} henuzayarlaayar")
                    continue

                # kullan OpenAI uyumlubaglanagiz (DeepSeekModel) baslat
                base_url = cfg.get("endpoint")

                for tier in ["low", "medium", "high"]:
                    model_cfg = ModelConfig(
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model_name,
                    )
                    # tekrarkullan DeepSeek model (OpenAI uyumlu) 
                    self._models.setdefault(provider, {})[tier] = DeepSeekModel(
                        model_cfg, ModelTier(tier)
                    )

                loaded_count += 1
                logger.info(f"kullanicimodelyukle: {provider}/{model_name}")

            except Exception as e:
                logger.warning(f"yukle {yaml_file.name} basarisiz: {mask_api_key(str(e))}")

        if loaded_count > 0:
            logger.info(f"yukle {loaded_count} kullaniciozelmodel")

    def select(
        self,
        task_type: str,
        complexity: str = "medium",
        budget_remaining: Optional[float] = None,
    ) -> RoutingDecision:
        """
        secseceniyimodel

        Args:
            task_type: gorevtip
            complexity: gorevtekrarkarisikderece (low/medium/high, olabiliruzerine yazvarsayilankatmanseviye) 
            budget_remaining: kalankalanonhesapla (ogre) 

        Returns:
            RoutingDecision: yoltarafindankarar
        """
        # kesinmodelkatmanseviye
        base_tier = _TASK_TIER_MAPPING.get(task_type, "medium")

        tier = base_tier
        # katmanseviyeyukseltdusur
        if complexity == "low" and base_tier == "high":
            tier = "medium"
        elif complexity == "low" and base_tier == "medium":
            tier = "low"
        elif complexity == "high" and base_tier == "low":
            tier = "medium"
        elif complexity == "high" and base_tier == "medium":
            tier = "high"

        # onhesaplakontrol (egerayarlaayaronhesaplavehayiryeterli, dusurseviyekadarkolayuygunmodel) 
        if budget_remaining is not None and budget_remaining < 0.01 and tier == "high":
            tier = "medium"
            logger.info("onhesaplahayiryeterli, dusurseviyekadar MEDIUM tier")

        # secsecsaglayici (oncelik DeepSeek) 
        selected_provider = None
        reason = ""

        for provider in self.config.fallback_order:
            provider_models = self._models.get(provider, {})
            if tier in provider_models:
                selected_provider = provider
                reason = (
                    "DeepSeek ucretsizkotadereceoncelik"
                    if provider == "deepseek"
                    else f"{provider} hazirlakullan"
                )
                break

        if selected_provider is None:
            raise NoModelAvailableError(
                f"yokvarolabilirkullanmodelisle {task_type} gorev (tier={tier}, "
                f"olabilirkullansaglayici={list(self._models.keys())}"
            )

        # tahminol
        model = self._models[selected_provider][tier]
        estimated_cost = model.get_cost(
            Usage(prompt_tokens=1000, completion_tokens=500)
        )

        decision = RoutingDecision(
            task_type=task_type,
            selected_provider=selected_provider,
            selected_tier=tier,
            reason=reason,
            estimated_cost=estimated_cost,
        )

        self._decision_history.append(decision)
        logger.debug(
            f"yoltarafindankarar: {task_type} → {selected_provider}/{tier} "
            f"(reason={reason}, cost≈{estimated_cost:.4f})"
        )

        return decision

    async def route_and_call(
        self,
        task_type: str,
        messages: list[Message],
        complexity: str = "medium",
        use_cache: bool = True,
        override_model: Optional[str] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        yoltarafindanveyurut (kemerarizadonusturhareket + onbellek) 

        iyinokta: 
        1. onbellekaynimesajyanit
        2. arizadonusturhareket: anamodelbasarisizotomatikgecishazirlakullan
        3. gorevtiptani: otomatikdusurseviye/yukseltseviye tier
        4. override_model: kullanicibelirtmodelzamandogrubaglankullan, yoksayotomatiksecsec
        """
        # 0. uyumlu dict mesajformat (otomatikdonusturicin Message icinnesne) 
        if messages and isinstance(messages[0], dict):
            from ..models.base import Message
            messages = [Message(**m) if isinstance(m, dict) else m for m in messages]

        # 0b. islekullanicibelirtmodeluzerine yaz
        forced_provider: Optional[str] = None
        forced_tier: Optional[str] = None
        if override_model:
            mapped = self._MODEL_ID_TO_PROVIDER.get(override_model)
            if mapped:
                # ozelmodelveyabilmodel ID → eslekadar provider
                forced_provider = mapped
                forced_tier = "high"  # ozel/belirtmodelbirkullan high tier
                logger.info(f"kullankullanicibelirtmodel: {override_model} → {forced_provider}")
            else:
                # tamamtumhenuzbilmodel ID → denedogrubaglanyapicin provider isim
                if override_model in self._models:
                    forced_provider = override_model
                    forced_tier = "high"
                    logger.info(f"kullankullanicibelirt provider: {override_model}")
                else:
                    logger.warning(f"henuzbil override_model: {override_model}, yoksay")

        # 1. kontrolonbellek (hayirbolgepuan override, aynimesajdonusayniyanit) 
        if use_cache and self._cache:
            cached = self._cache.get(messages)
            if cached:
                logger.info(f"kullanonbellekyanit (task={task_type}) ")
                return cached

        # 2. secsecmodel (kullanicibelirtzamanatlaotomatiksecsec) 
        if forced_provider and forced_tier:
            decision = RoutingDecision(
                task_type=task_type,
                selected_provider=forced_provider,
                selected_tier=forced_tier,
                reason=f"kullanicibelirtmodel: {override_model}",
                estimated_cost=0.0,
            )
        else:
            decision = self.select(task_type, complexity)

        # 3. arizadonusturhareket: gore fallback siradene (sadecebaslat provider) 
        # kullanicibelirtmodelzaman, oncelikkullanbumodel, basarisizsonraotomatikdusurseviyekadarvarsayilan fallback
        if forced_provider:
            fallback_order = (
                [forced_provider] if forced_provider in self._models else []
            )
            # eklevarsayilan fallback yapicindusurseviyesecogre (harir tutekle) 
            for p in self.config.fallback_order:
                if (
                    p not in fallback_order
                    and p in self._models
                    and decision.selected_tier in self._models[p]
                ):
                    fallback_order.append(p)
        else:
            fallback_order = [
                p
                for p in self.config.fallback_order
                if p in self._models and decision.selected_tier in self._models[p]
            ]
            # saglarmevcutsecsecicindeenonce
            if decision.selected_provider not in fallback_order:
                fallback_order.insert(0, decision.selected_provider)

        last_error: Optional[Exception] = None
        rate_limited_providers: list[str] = []
        attempted_providers: list[str] = []

        for provider in fallback_order:
            m = self._models[provider][decision.selected_tier]
            attempted_providers.append(provider)
            for attempt in range(3):
                try:
                    start = datetime.now()
                    response = await m.generate(messages, **kwargs)
                    elapsed = (datetime.now() - start).total_seconds() * 1000

                    # guncelleolistatistik
                    actual_cost = m.get_cost(response.usage)
                    self._total_cost += actual_cost
                    response.latency_ms = elapsed

                    logger.info(
                        f"istekbasarili: {provider}/{decision.selected_tier} "
                        f"(tokens={response.usage.total_tokens}, "
                        f"latency={elapsed:.0f}ms, cost={actual_cost:.6f})"
                    )

                    # onbellekyanit
                    if use_cache and self._cache:
                        self._cache.set(messages, response)

                    return response

                except Exception as e:
                    last_error = e
                    # 429 sinirakis: hayiryeniden denemevcut provider, failover kadaraltbir
                    if (
                        isinstance(e, httpx.HTTPStatusError)
                        and e.response.status_code == 429
                    ):
                        logger.warning(
                            f"429 sinirakis ({provider}/{decision.selected_tier}) , "
                            f"atlabu provider, denealtbir"
                        )
                        rate_limited_providers.append(provider)
                        break  # hayiryeniden denemevcut provider, gecisaltbir

                    logger.warning(
                        f"istek başarısız ({provider}/{decision.selected_tier}, "
                        f"attempt={attempt + 1}/3) : {mask_api_key(str(e))}"
                    )
                    if attempt < 2:
                        await asyncio.sleep(2 * (attempt + 1))  # iletartvb.bekle

        # vardenetumbasarisiz
        # sadecevarne zamanvargercekdene provider tumdir 429 zamanyetenekfirlat RateLimitError
        if rate_limited_providers and set(rate_limited_providers) == set(
            attempted_providers
        ):
            logger.error("var provider ortalama 429 sinirakis")
            raise RateLimitError(
                f"varmodelortalamatetikgondersinirakis (429) : {rate_limited_providers}. "
                f"oneribirazsonrayeniden deneveyayapilandirmadahacok API Key. "
            ) from last_error

        logger.error(f"sağlayıcı başarısız: {mask_api_key(str(last_error))}")
        raise NoModelAvailableError(
            f"kullanılabilir model bulunamadı (task={task_type}) : {mask_api_key(str(last_error))}"
        ) from last_error

    def get_model(
        self,
        provider: str,
        tier: str,
    ) -> Optional[BaseModel]:
        """dogrubaglanalbelirtmodel"""
        return self._models.get(provider, {}).get(tier)

    def get_stats(self) -> dict[str, Any]:
        """alyoltarafindanistatistik"""
        return {
            "total_requests": len(self._decision_history),
            "total_cost": self._total_cost,
            "provider_distribution": self._count_by("selected_provider"),
            "tier_distribution": self._count_by("selected_tier"),
            "cache": self._cache.stats() if self._cache else None,
        }

    def _count_by(self, field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in self._decision_history:
            key = getattr(d, field)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def clear_cache(self) -> None:
        """temizlebosyanitonbellek"""
        if self._cache:
            self._cache.clear()
            logger.info("yanitonbellektemizlebos")

    def reset_stats(self) -> None:
        """tekrarayaristatistikbilgi"""
        self._decision_history.clear()
        self._total_cost = 0.0

    # model ID → yoltarafindanicindekisim provider adesle
    # onceucaltmenutekililetdirmodel ID (ornegin "glm-4-flash") , gerekistereslekadar provider (ornegin "glm") 
    _MODEL_ID_TO_PROVIDER: dict[str, str] = {
        # DeepSeek
        "deepseek-chat": "deepseek",
        # Zhipu GLM
        "glm-4-flash": "glm",
        # MiniMax / MiMo
        "MiniMax-Text-01": "minimax",
        # Kimi / Moonshot
        "moonshot-v1-128k": "kimi",
        # paket / Volcengine
        "doubao-pro-32k": "doubao",
        # Tiangong
        "tiangong-3": None,  # yoltarafindangeçicihayirdestek tiangong provider
        # yuz
        "Baichuan4": None,  # yoltarafindangeçicihayirdestek baichuan provider
        # metinkalp
        "ernie-4.0-8k-latest": "wenxin",
        # anlam
        "qwen-plus": "tongyi",
        # Hunyuan
        "hunyuan-turbo": "hunyuan",
    }


class RateLimitError(Exception):
    """429 sinirakishata, hayiryeniden dene"""

    pass


class NoModelAvailableError(Exception):
    """yokvarolabilirkullanmodel"""

    pass
