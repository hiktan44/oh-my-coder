from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Maliyet optimizasyonu öneri modülü - Cost Optimization

Maliyetlerden tasarruf etmek için görev karmaşıklığına dayalı en uygun modeli önerin.

Model sınıflandırması:
- yerel Ollama Modeli (ollama/)
- Yurtiçi bulut modeli (deepseek/, qwen/, glm/, moonshot/)
- üst model (openai/, anthropic/)

Karmaşıklık değerlendirmesi:
- Düşük:<3 Basit dosya değişikliği
- orta:3-10 Dosya değişiklikleri
- yüksek:>10 belge / yeni mimari / Yeniden düzenleme
"""


from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Complexity(Enum):
    """görev karmaşıklığı"""

    LOW = "low"  # Basit görevler için yerel modeller yeterlidir
    MEDIUM = "medium"  # Orta karmaşıklıkta, yerli maliyetli model
    HIGH = "high"  # Karmaşık görevler en iyi modelleri gerektirir


@dataclass
class ModelRecommendation:
    """Model öneri sonuçları"""

    model: str
    provider: str  # ollama/deepseek/openai/anthropic
    complexity: Complexity

    # sebep
    reason: str

    # Tahmini maliyet (göreceli değer)
    estimated_cost: float  # 1-10, 10 En pahalı

    # alternatif model
    alternatives: list[dict[str, str]]


class CostOptimizer:
    """maliyet optimize edici

    Görev özelliklerine göre karmaşıklığı değerlendirin ve en uygun modeli önerin.
    """

    # Model tanımı
    MODELS = {
        # yerel model
        "ollama/qwen2.5:7b": {
            "provider": "ollama",
            "cost": 1,
            "strengths": ["Basit değişiklik", "kod tamamlama", "Hafif görevler"],
        },
        "ollama/qwen2.5:14b": {
            "provider": "ollama",
            "cost": 2,
            "strengths": ["orta karmaşıklık", "kod anlayışı", "yerel öncelik"],
        },
        "ollama/llama3:8b": {
            "provider": "ollama",
            "cost": 2,
            "strengths": ["Ağırlıklı olarak İngilizce", "Ortak görevler"],
        },
        # Yurtiçi bulut modeli
        "deepseek-chat": {
            "provider": "deepseek",
            "cost": 4,
            "strengths": ["Güçlü kodlama yeteneği", "Yüksek maliyet performansı", "Çin optimizasyonu"],
        },
        "qwen-turbo": {
            "provider": "qwen",
            "cost": 3,
            "strengths": ["Ali sistemi", "İyi Çince", "hızlı"],
        },
        "glm-4": {
            "provider": "glm",
            "cost": 4,
            "strengths": ["Bilgeliğin açık sözleri", "Çin optimizasyonu"],
        },
        "moonshot-v1": {
            "provider": "moonshot",
            "cost": 4,
            "strengths": [" Kimi ", "Uzun metin işleme"],
        },
        # üst model
        "gpt-4o": {
            "provider": "openai",
            "cost": 10,
            "strengths": ["üst düzey yetenek", "karmaşık akıl yürütme", "Mimari tasarım"],
        },
        "gpt-4o-mini": {
            "provider": "openai",
            "cost": 6,
            "strengths": ["Maliyet etkinliği", "Hızlı görevler"],
        },
        "claude-3-opus": {
            "provider": "anthropic",
            "cost": 10,
            "strengths": ["En güçlü muhakeme", "uzun metin", "analiz etmek"],
        },
        "claude-3-sonnet": {
            "provider": "anthropic",
            "cost": 7,
            "strengths": ["denge", "Güçlü yazma becerileri"],
        },
    }

    # karmaşıklık anahtar kelimesi
    COMPLEXITY_KEYWORDS = {
        Complexity.HIGH: [
            "Yeniden düzenleme",
            "refactor",
            "Mimarlık",
            "architecture",
            "tasarım",
            "design",
            "yeni proje",
            "new project",
            "göç etmek",
            "migrate",
            "Bölmek",
            "split",
            "yeniden yazmak",
            "rewrite",
            "karmaşık",
            "complex",
            "sistem",
            "system",
            "mikro hizmetler",
            "microservice",
            "dağıtılmış",
            "distributed",
        ],
        Complexity.MEDIUM: [
            "api",
            "arayüz",
            "veritabanı",
            "database",
            "Sertifikasyon",
            "auth",
            "Giriş yapmak",
            "login",
            "ödemek",
            "payment",
            "Emir",
            "order",
            "kullanıcı",
            "user",
            "üstesinden gelmek",
            "admin",
            "CRUD",
            "birden fazla dosya",
            "multiple files",
            "Çoklu modüller",
        ],
    }

    def __init__(self, prefer_local: bool = True):
        """
        Args:
            prefer_local: Yerel modellerin tavsiye edilmesine öncelik verilip verilmeyeceği
        """
        self.prefer_local = prefer_local

    def analyze_task(
        self,
        task_description: str,
        file_count: Optional[int] = None,
        new_files: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Görev özelliklerini analiz edin

        Args:
            task_description: Görev açıklaması
            file_count: İlgili dosya sayısı
            new_files: Dosya listesi ekle

        Returns:
            Görev analizi sonuçları
        """
        task_lower = task_description.lower()

        # 1. Anahtar kelimelere dayalı değerlendirme
        high_keywords = self.COMPLEXITY_KEYWORDS[Complexity.HIGH]
        medium_keywords = self.COMPLEXITY_KEYWORDS[Complexity.MEDIUM]

        high_score = sum(1 for kw in high_keywords if kw in task_lower)
        medium_score = sum(1 for kw in medium_keywords if kw in task_lower)

        # 2. Dosya sayısına göre
        if file_count is not None:
            if file_count > 10:
                high_score += 3
            elif file_count > 5:
                medium_score += 2
            elif file_count > 2:
                medium_score += 1

        # 3. Yeni dosyalara dayalı
        if new_files:
            for f in new_files:
                if any(x in f.lower() for x in ["api", "service", "model"]):
                    medium_score += 1
                if any(x in f.lower() for x in ["app", "main", "server"]):
                    high_score += 1

        # 4. Karmaşıklığı belirleyin
        if high_score >= 2:
            complexity = Complexity.HIGH
        elif medium_score >= 2:
            complexity = Complexity.MEDIUM
        else:
            complexity = Complexity.LOW

        return {
            "complexity": complexity,
            "high_score": high_score,
            "medium_score": medium_score,
            "file_count": file_count,
            "new_files_count": len(new_files) if new_files else 0,
        }

    def recommend(
        self,
        task_description: str,
        file_count: Optional[int] = None,
        new_files: Optional[list[str]] = None,
    ) -> ModelRecommendation:
        """
        En iyi modeli önerin

        Args:
            task_description: Görev açıklaması
            file_count: İlgili dosya sayısı
            new_files: Dosya listesi ekle

        Returns:
            Model öneri sonuçları
        """
        # Analiz görevleri
        analysis = self.analyze_task(task_description, file_count, new_files)
        complexity = analysis["complexity"]

        # Karmaşıklık ve tercihe göre önerilir
        if complexity == Complexity.LOW:
            return self._recommend_low(analysis)
        if complexity == Complexity.MEDIUM:
            return self._recommend_medium(analysis)
        return self._recommend_high(analysis)

    def _recommend_low(self, analysis: dict[str, Any]) -> ModelRecommendation:
        """Düşük karmaşıklıktaki görevler için modeller önerin"""
        if self.prefer_local:
            model = "ollama/qwen2.5:7b"
            reason = "Basit değişiklik görevi, yerel 7B Modeller yeterli, hızlı ve ücretsizdir"
        else:
            model = "qwen-turbo"
            reason = "Basit görevler, yerli modeller uygun maliyetlidir"

        return ModelRecommendation(
            model=model,
            provider=self.MODELS[model]["provider"],
            complexity=Complexity.LOW,
            reason=reason,
            estimated_cost=self.MODELS[model]["cost"],
            alternatives=[
                {"model": "ollama/qwen2.5:14b", "reason": "daha güçlü yetenek"},
                {"model": "gpt-4o-mini", "reason": "Bulutalternatif"},
            ],
        )

    def _recommend_medium(self, analysis: dict[str, Any]) -> ModelRecommendation:
        """tavsiye etmekorta karmaşıklıkGörevile ilgiliModeli"""
        if self.prefer_local:
            model = "ollama/qwen2.5:14b"
            reason = "Orta karmaşıklıktaki görevler, yerel 14B Model yeteneği yeterlidir"
        else:
            model = "deepseek-chat"
            reason = "DeepSeek Güçlü kodlama yeteneği, yerli maliyet etkinliği ilk tercihtir"

        return ModelRecommendation(
            model=model,
            provider=self.MODELS[model]["provider"],
            complexity=Complexity.MEDIUM,
            reason=reason,
            estimated_cost=self.MODELS[model]["cost"],
            alternatives=[
                {"model": "qwen-turbo", "reason": "Ali sistemi alternatifi"},
                {"model": "gpt-4o-mini", "reason": "OpenAI alternatif"},
            ],
        )

    def _recommend_high(self, analysis: dict[str, Any]) -> ModelRecommendation:
        """Son derece karmaşık görevler için modeller önerin"""
        if self.prefer_local:
            model = "ollama/qwen2.5:14b"
            reason = "Karmaşık görevlerde, fikri hızlı bir şekilde doğrulamak için yerel modelin kullanılması ve ardından darboğazlarla karşılaşırsanız üst düzey modele geçiş yapılması önerilir."
            cost = 2
        else:
            model = "gpt-4o"
            reason = "Karmaşık mimari tasarım/Yeniden inşa görevleri üst düzey model yetenekleri gerektirir"
            cost = 10

        return ModelRecommendation(
            model=model,
            provider=self.MODELS[model]["provider"],
            complexity=Complexity.HIGH,
            reason=reason,
            estimated_cost=cost,
            alternatives=[
                {"model": "gpt-4o", "reason": "OpenAI Tepe"},
                {"model": "claude-3-opus", "reason": "Claude en güçlü"},
                {"model": "deepseek-chat", "reason": "Yurtiçi maliyet etkinliği"},
            ],
        )

    def get_all_models(self) -> list[dict[str, Any]]:
        """Mevcut tüm modelleri edinin"""
        result = []
        for model, info in self.MODELS.items():
            result.append(
                {
                    "model": model,
                    "provider": info["provider"],
                    "cost": info["cost"],
                    "strengths": info["strengths"],
                }
            )
        return sorted(result, key=lambda x: x["cost"])


# ------------------------------------------------------------------
# Token Maliyet hesaplaması
# ------------------------------------------------------------------


# Model Fiyatlandırma Tablosu (USD / 1M tokens)
# Veri kaynağı: Her modelin resmi fiyatlandırma sayfası (2025-01)
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    # Anthropic
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3.5-opus": {"input": 18.00, "output": 90.00},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    # Qwen
    "qwen-turbo": {"input": 0.30, "output": 0.60},
    "qwen-plus": {"input": 0.80, "output": 2.00},
    # GLM
    "glm-4": {"input": 0.50, "output": 0.50},
    # Moonshot
    "moonshot-v1-8k": {"input": 0.50, "output": 0.50},
    "moonshot-v1-32k": {"input": 0.50, "output": 0.50},
    # Ollama (Yerel olarak ücretsiz)
    "ollama/qwen2.5:7b": {"input": 0.0, "output": 0.0},
    "ollama/qwen2.5:14b": {"input": 0.0, "output": 0.0},
    "ollama/llama3:8b": {"input": 0.0, "output": 0.0},
}


@dataclass
class CostEstimate:
    """Maliyet tahmini sonuçları"""

    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float  # Dolar
    output_cost: float  # Dolar
    total_cost: float  # Dolar


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> CostEstimate:
    """Belirtilen modeli hesapla token maliyet

    Args:
        model: Model adı (ör. "gpt-4o-mini", "claude-3.5-opus")
        input_tokens: girmek token sayı
        output_tokens: çıktı token sayı

    Returns:
        CostEstimate: Maliyet tahmini sonuçları

    Raises:
        ValueError: Model fiyatlandırma tablosunda yok
    """
    if model not in MODEL_PRICING:
        raise ValueError(
            f"Modeli {model} Fiyat tablosunda yok, mevcut modeller: {list(MODEL_PRICING.keys())}"
        )

    pricing = MODEL_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return CostEstimate(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
    )


def calculate_multi_model_cost(
    model_usages: list[dict[str, int]],
) -> list[CostEstimate]:
    """Çoklu model portföy maliyetlerini hesaplayın

    Args:
        model_usages: Model kullanım listesi, her öğe şunları içerir {"model": str, "input_tokens": int, "output_tokens": int}

    Returns:
        Her model için maliyet tahminlerinin listesi
    """
    results = []
    for usage in model_usages:
        estimate = calculate_cost(
            model=usage["model"],
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
        results.append(estimate)
    return results


# ------------------------------------------------------------------
# CLI Giriş
# ------------------------------------------------------------------


def main():
    """CLI Giriş"""
    import argparse

    parser = argparse.ArgumentParser(description="Maliyet Optimizasyonu Tavsiye Aracı")
    parser.add_argument("task", nargs="?", help="Görev açıklaması")
    parser.add_argument("--files", "-f", type=int, help="İlgili dosya sayısı")
    parser.add_argument("--list", "-l", action="store_true", help="tüm modelleri listele")
    parser.add_argument("--prefer-local", action="store_true", default=True)

    args = parser.parse_args()

    optimizer = CostOptimizer(prefer_local=args.prefer_local)

    if args.list:
        print("Mevcut modeller:")
        print("-" * 60)
        for m in optimizer.get_all_models():
            cost_bars = "💰" * m["cost"]
            print(f"{m['model']:30s} [{m['provider']:10s}] {cost_bars}")
            print(f"    Avantajları: {', '.join(m['strengths'])}")
            print()
        return

    if not args.task:
        parser.print_help()
        return

    # Önerilen model
    recommendation = optimizer.recommend(args.task, file_count=args.files)

    print("=" * 60)
    print(f"Görev: {args.task}")
    if args.files:
        print(f"Dosya sayısı: {args.files}")
    print("=" * 60)
    print()
    print(f"🎯 Önerilen model: {recommendation.model}")
    print(f"📦 sağlayıcı: {recommendation.provider}")
    print(f"📊 karmaşıklık: {recommendation.complexity.value}")
    print(f"💵 Maliyeti tahmin edin: {'$' * recommendation.estimated_cost}")
    print()
    print("💡 Tavsiye nedenleri:")
    print(f"   {recommendation.reason}")
    print()
    if recommendation.alternatives:
        print("🔄 Alternatifler:")
        for alt in recommendation.alternatives:
            print(f"   - {alt['model']}: {alt['reason']}")


if __name__ == "__main__":
    main()
