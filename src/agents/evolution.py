from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Agent kendini geliştiren modül - Evolution System

izin vermek Agent Biyolojik genler gibi miras alın, mutasyona uğrayın ve evrimleşin.
Evrimsel geçmişi saklayın, başarılı desen kütüphanesi, optimize edilmiş system prompt, sürüm yineleme karar verme.

Dizin yapısı:
.omc/state/agents/{agent_name}/
├── evolution_history.json  # evrimsel kayıt
├── success_patterns.json   # Başarı Modeli Kitaplığı
└── optimized_prompt.md     # Optimize edilmiş prompt

.omc/state/decisions/
└── {yyyy-MM-dd}-{slug}.md  # Her önemli kararın kaydı
"""


import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class EvolutionRecord:
    """evrimsel kayıt"""

    id: str = ""  # Zaman damgası-based ID
    timestamp: str = ""
    agent_type: str = ""
    generation: int = 1  # Evrimsel cebir
    trigger: str = ""  # Tetikleyici sebep:success_rate_low, user_correction, error_pattern
    before_state: dict[str, Any] = field(default_factory=dict)  # evrim öncesi durum
    after_state: dict[str, Any] = field(default_factory=dict)  # gelişmiş durum
    changes: list[str] = field(default_factory=list)  # listeyi değiştir
    effectiveness: Optional[float] = None  # Performans puanı (sonraki doğrulama)


@dataclass
class SuccessPattern:
    """başarı modeli"""

    id: str = ""
    pattern_type: str = ""  # strategy, workflow, prompt_technique
    description: str = ""
    context: str = ""  # uygulanabilir bağlam
    effectiveness_score: float = 0.0
    occurrences: int = 0  # Oluşum sayısı
    last_seen: str = ""
    examples: list[str] = field(default_factory=list)  # Başarı Hikayeleri


@dataclass
class EvolutionConfig:
    """kendi kendine gelişen konfigürasyon"""

    enabled: bool = True  # Kişisel gelişimin etkinleştirilip etkinleştirilmeyeceği
    improvement_threshold: float = 0.8  # Optimizasyonun tetiklendiği başarı oranı eşiği
    min_samples: int = 5  # Minimum örnek sayısı, bundan daha azı evrimsel analizi tetiklemez
    max_evolution_history: int = 100  # Maksimum evrimsel tarih kaydı sayısı
    pattern_confidence_threshold: float = 0.7  # Desen güven eşiği
    evolution_cooldown_hours: int = 24  # Evolution soğuma süresi (saat)


class EvolutionStore:
    """Evrim durumu depolaması"""

    def __init__(self, state_dir: Path):
        """
        Args:
            state_dir: .omc/state İçindekiler
        """
        self.state_dir = Path(state_dir)
        self.agents_dir = self.state_dir / "agents"

    def _agent_dir(self, agent_name: str) -> Path:
        """Elde etmek Agent Evrim Kataloğu"""
        agent_dir = self.agents_dir / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    # ------------------------------------------------------------------
    # evrim tarihi
    # ------------------------------------------------------------------

    def load_evolution_history(
        self, agent_name: str, limit: int = 50
    ) -> list[EvolutionRecord]:
        """Evrimsel geçmişi yükle"""
        history_file = self._agent_dir(agent_name) / "evolution_history.json"
        if not history_file.exists():
            return []

        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
            records = [EvolutionRecord(**r) for r in data.get("records", [])]
            return records[:limit]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_evolution_record(self, record: EvolutionRecord) -> str:
        """Evrim kaydını kaydet"""
        agent_name = record.agent_type
        history_file = self._agent_dir(agent_name) / "evolution_history.json"

        # Mevcut geçmişi oku
        existing = []
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text(encoding="utf-8"))
                existing = data.get("records", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        # Yeni kayıt ekle
        record_dict = {
            "id": record.id or f"evo-{int(time.time())}",
            "timestamp": record.timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_type": record.agent_type,
            "generation": record.generation,
            "trigger": record.trigger,
            "before_state": record.before_state,
            "after_state": record.after_state,
            "changes": record.changes,
            "effectiveness": record.effectiveness,
        }
        existing.append(record_dict)

        # Geçmiş uzunluğunu sınırla
        max_records = 100
        if len(existing) > max_records:
            existing = existing[-max_records:]

        # kaydetmek
        history_file.write_text(
            json.dumps({"records": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record_dict["id"]

    def get_current_generation(self, agent_name: str) -> int:
        """Mevcut evrimsel nesli edinin"""
        history = self.load_evolution_history(agent_name, limit=1)
        if not history:
            return 1
        return max(1, history[0].generation + 1)

    # ------------------------------------------------------------------
    # Başarı Modeli Kitaplığı
    # ------------------------------------------------------------------

    def load_success_patterns(self, agent_name: str) -> list[SuccessPattern]:
        """Başarılı desen kitaplığı yükleniyor"""
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"
        if not patterns_file.exists():
            return []

        try:
            data = json.loads(patterns_file.read_text(encoding="utf-8"))
            return [SuccessPattern(**p) for p in data.get("patterns", [])]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_success_pattern(self, pattern: SuccessPattern) -> str:
        """Başarılı modu kaydet"""
        # Kaydetmek için doğrudan dahili yöntemi çağırın
        return self._save_pattern_internal(pattern)

    def _save_pattern_internal(self, pattern: SuccessPattern) -> str:
        """Dahili yöntem: başarılı deseni kaydedin"""
        # itibaren pattern.id çıkarmak agent_name(Biçimi varsayarsak:agentname-patternid)
        agent_name = pattern.id.split("-")[0] if "-" in pattern.id else "default"
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"

        existing = []
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                existing = data.get("patterns", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        pattern_dict = {
            "id": pattern.id or f"pattern-{int(time.time())}",
            "pattern_type": pattern.pattern_type,
            "description": pattern.description,
            "context": pattern.context,
            "effectiveness_score": pattern.effectiveness_score,
            "occurrences": pattern.occurrences,
            "last_seen": pattern.last_seen or time.strftime("%Y-%m-%d %H:%M:%S"),
            "examples": pattern.examples,
        }

        # Zaten mevcut olup olmadığını bulun, varsa güncelleyin
        found = False
        for i, p in enumerate(existing):
            if p.get("id") == pattern_dict["id"]:
                existing[i] = pattern_dict
                found = True
                break

        if not found:
            existing.append(pattern_dict)

        patterns_file.write_text(
            json.dumps({"patterns": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pattern_dict["id"]

    def add_success_pattern(
        self,
        agent_name: str,
        pattern_type: str,
        description: str,
        context: str = "",
        example: str = "",
    ) -> str:
        """Başarı modeli ekle"""
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"

        existing = []
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                existing = data.get("patterns", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        # Benzer bir modelin zaten mevcut olup olmadığını kontrol edin
        pattern_id = f"{agent_name}-{pattern_type}-{int(time.time())}"

        pattern_dict = {
            "id": pattern_id,
            "pattern_type": pattern_type,
            "description": description,
            "context": context,
            "effectiveness_score": 0.7,  # İlk güven
            "occurrences": 1,
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
            "examples": [example] if example else [],
        }

        existing.append(pattern_dict)

        patterns_file.write_text(
            json.dumps({"patterns": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pattern_id

    # ------------------------------------------------------------------
    # optimizasyon Prompt
    # ------------------------------------------------------------------

    def load_optimized_prompt(self, agent_name: str) -> Optional[str]:
        """Optimize edilmiş yük system prompt"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        if not prompt_file.exists():
            return None
        return prompt_file.read_text(encoding="utf-8")

    def save_optimized_prompt(self, agent_name: str, prompt: str) -> None:
        """Optimize edilmiş olanı kaydet system prompt"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")

    def get_prompt_version(self, agent_name: str) -> int:
        """Elde etmek prompt sürüm numarası"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        if not prompt_file.exists():
            return 0
        content = prompt_file.read_text(encoding="utf-8")
        # Sürüm numarasını dosyadan çıkarın
        for line in content.split("\n")[:5]:
            if "version:" in line.lower():
                try:
                    return int(line.split(":")[-1].strip())
                except ValueError:
                    pass
        return 1

    # ------------------------------------------------------------------
    # İstatistikler
    # ------------------------------------------------------------------

    def get_evolution_stats(self, agent_name: str) -> dict[str, Any]:
        """Evrim istatistiklerini alın"""
        history = self.load_evolution_history(agent_name)
        patterns = self.load_success_patterns(agent_name)
        prompt_version = self.get_prompt_version(agent_name)

        return {
            "agent_name": agent_name,
            "current_generation": self.get_current_generation(agent_name),
            "total_evolutions": len(history),
            "total_patterns": len(patterns),
            "prompt_version": prompt_version,
            "last_evolution": history[0].timestamp if history else None,
        }


# ------------------------------------------------------------------
# Sürüm yineleme belleği - DecisionMemory(Hayaletlerin duvara çarpması probleminin çözümü)
# ------------------------------------------------------------------


@dataclass
class DecisionRecord:
    """Önemli karar kayıtları - Hayaletlerin duvara çarpması problemini çözme

    Her önemli kararı kaydedin, böylece Agent Unutma:
    - Geçen sefer bu sorun neydi? Nasıl düzeltilir?
    - Gelecekte benzer tuzaklarla nasıl başa çıkılır?
    - Sürümler arasındaki önemli kararlar nelerdir?
    """

    id: str = ""  # {yyyy-MM-dd}-{slug}
    title: str = ""  # Karar başlığı
    timestamp: str = ""  # karar zamanı
    agent_type: str = ""  # kararlar vermek Agent tip
    category: str = ""  # Karar Kategorisi: bug_fix, solution_choice, rejection, architecture

    # Sorun geçmişi
    problem: str = ""  # Karşılaşılan sorunların açıklaması
    context: str = ""  # Bağlam (dosya, işlev, hata mesajı vb.)

    # Karar içeriği
    chosen_solution: str = ""  # Seçilen plan
    rejected_alternatives: list[str] = field(default_factory=list)  # Terk edilen planlar ve nedenleri

    # sonuç
    result: str = ""  # başarı/hata
    outcome: str = ""  # Efekt açıklaması

    # Yeniden kullanılabilirlik
    reusable_for: str = ""  # Benzer sahne açıklaması
    keywords: list[str] = field(default_factory=list)  # Anahtar kelimeleri arayın

    # meta veri
    related_files: list[str] = field(default_factory=list)  # İlgili belgeler
    version_tag: str = ""  # sürüm etiketi (ör. v1.2.3)


class DecisionMemory:
    """Sürüm yineleme belleği - çözmek Agent Hayalet duvar sorunu

    Temel işlevler:
    1. Önemli kararları belgeleyin (çözüm seçimi,bugOnarım önerileri, ret)
    2. Tekrarlanan hatalardan kaçınmak için geçmiş kararları alın
    3. Kolay erişim için anahtar kelimeleri otomatik olarak çıkarın

    Dizin yapısı:
    .omc/state/decisions/
    └── {yyyy-MM-dd}-{slug}.md  # Tek seferde tek karar Markdown Kayıt
    """

    def __init__(self, state_dir: Path):
        """
        Args:
            state_dir: .omc/state İçindekiler
        """
        self.state_dir = Path(state_dir)
        self.decisions_dir = self.state_dir / "decisions"
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, text: str) -> str:
        """Metni şuna dönüştür: URL-friendly slug"""
        # Basit uygulama: yalnızca harfleri, sayıları ve çizgileri saklayın
        s = text.lower()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s_]+", "-", s)
        s = re.sub(r"-+", "-", s)
        s = s.strip("-")
        # Sınır uzunluğu
        if len(s) > 40:
            s = s[:40].rstrip("-")
        return s

    def _decision_file(self, decision_id: str) -> Path:
        """Karar dosyası yolunu alın"""
        return self.decisions_dir / f"{decision_id}.md"

    def record_decision(
        self,
        title: str,
        problem: str,
        chosen_solution: str,
        agent_type: str = "",
        category: str = "solution_choice",
        rejected_alternatives: Optional[list[str]] = None,
        result: str = "",
        outcome: str = "",
        reusable_for: str = "",
        keywords: Optional[list[str]] = None,
        related_files: Optional[list[str]] = None,
        version_tag: str = "",
    ) -> str:
        """
        Önemli bir kararı kaydedin

        Args:
            title: Karar başlığı
            problem: Karşılaşılan sorunlar
            chosen_solution: Seçilen plan
            agent_type: Agent tip
            category: Karar Kategorisi (bug_fix/solution_choice/rejection/architecture)
            rejected_alternatives: Terk edilmiş planların listesi
            result: sonuç (success/failure)
            outcome: Efekt açıklaması
            reusable_for: Uygulanabilir senaryolar
            keywords: Anahtar kelimeleri arayın
            related_files: İlgili belgeler
            version_tag: sürüm etiketi

        Returns:
            decision_id: Karar kaydı ID
        """
        # kararlar üretmek ID
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = self._slugify(title)
        decision_id = f"{date_str}-{slug}"

        # Anahtar kelimeleri otomatik olarak çıkar
        if keywords is None:
            keywords = self._extract_keywords(problem, chosen_solution)

        # inşa etmek Markdown içerik
        content = self._build_decision_markdown(
            title=title,
            problem=problem,
            chosen_solution=chosen_solution,
            agent_type=agent_type,
            category=category,
            rejected_alternatives=rejected_alternatives or [],
            result=result,
            outcome=outcome,
            reusable_for=reusable_for,
            keywords=keywords,
            related_files=related_files or [],
            version_tag=version_tag,
        )

        # dosyayı kaydet
        decision_file = self._decision_file(decision_id)
        decision_file.write_text(content, encoding="utf-8")

        return decision_id

    def _extract_keywords(self, problem: str, solution: str) -> list[str]:
        """Sorunlardan ve çözümlerden anahtar kelimeleri otomatik olarak çıkarın"""
        text = f"{problem} {solution}".lower()
        # Teknik terimleri çıkartın (basitleştirilmiş versiyon)
        words = re.findall(r"\b[a-z_]+\b", text)
        # Yaygın kelimeleri filtrele
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "what",
            "which",
            "who",
            "whom",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "if",
            "then",
            "else",
            "also",
            "now",
            "here",
            "there",
        }
        keywords = [w for w in words if len(w) >= 3 and w not in stopwords]
        # Kopyaları kaldırın ve öncesine dönün10bireysel
        return list(dict.fromkeys(keywords))[:10]

    def _build_decision_markdown(
        self,
        title: str,
        problem: str,
        chosen_solution: str,
        agent_type: str,
        category: str,
        rejected_alternatives: list[str],
        result: str,
        outcome: str,
        reusable_for: str,
        keywords: list[str],
        related_files: list[str],
        version_tag: str,
    ) -> str:
        """Kararların kaydını oluşturmak Markdown içerik"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"# {timestamp} {title}",
            "",
            "---",
            f"**Agent**: {agent_type or 'unknown'}",
            f"**kategori**: {category}",
            f"**sonuç**: {result or 'pending'}",
            f"**Sürüm**: {version_tag or 'N/A'}",
            "---",
            "",
            "## Sorun geçmişi",
            problem,
            "",
            "## Seçilen plan",
            chosen_solution,
        ]

        if rejected_alternatives:
            lines.extend(
                [
                    "",
                    "## Terk edilmiş plan",
                ]
            )
            lines.extend([f"- {alt}" for alt in rejected_alternatives])

        if outcome:
            lines.extend(
                [
                    "",
                    "## Etki",
                    outcome,
                ]
            )

        if reusable_for:
            lines.extend(
                [
                    "",
                    "## Yeniden kullanılabilirlik",
                    "Gelecekte benzer senaryolarla karşılaşın → Bu çözümü kullanın",
                    "",
                    f"**Uygulanabilir senaryolar**: {reusable_for}",
                ]
            )

        if keywords:
            lines.extend(
                [
                    "",
                    "## anahtar kelimeler",
                    ", ".join(f"`{k}`" for k in keywords),
                ]
            )

        if related_files:
            lines.extend(
                [
                    "",
                    "## İlgili belgeler",
                    *[f"- {f}" for f in related_files],
                ]
            )

        return "\n".join(lines)

    def retrieve(
        self,
        query: str,
        limit: int = 5,
    ) -> list[DecisionRecord]:
        """
        Geçmiş kararları alın

        Yardımcı olacak anahtar kelimelere dayalı olarak ilgili kararları arayın Agent Tekrarlanan tuzaklardan kaçının.

        Args:
            query: Anahtar kelimeleri arayın
            limit: Maksimum miktarı iade edin

        Returns:
            Eşleşen karar kayıtlarının listesi
        """
        query_terms = set(query.lower().split())
        results: list[tuple[int, DecisionRecord]] = []

        # Tüm karar dosyalarını yineleyin
        for decision_file in self.decisions_dir.glob("*.md"):
            try:
                content = decision_file.read_text(encoding="utf-8")
                record = self._parse_decision_file(decision_file, content)
                if not record:
                    continue

                # Alaka puanını hesaplayın
                score = self._calculate_relevance(query_terms, record)
                if score > 0:
                    results.append((score, record))
            except Exception:
                continue

        # Alaka düzeyine göre sırala
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def _parse_decision_file(
        self, file_path: Path, content: str
    ) -> Optional[DecisionRecord]:
        """Karar dosyasını şu şekilde ayrıştırın: DecisionRecord"""
        # Dosya adından çıkar ID
        decision_id = file_path.stem

        # Ayrıştırma başlığı (ilk satır)
        lines = content.split("\n")
        title = ""
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            # Zaman damgası önekini kaldır
            title = re.sub(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+", "", title)

        # Meta verileri ayrıştır
        agent_type = ""
        category = "solution_choice"
        result = ""
        version_tag = ""

        for line in lines:
            if line.startswith("**Agent**:"):
                # Format: **Agent**: value
                parts = line.split(":", 1)
                if len(parts) > 1:
                    agent_type = parts[1].strip()
            elif line.startswith("**kategori**:"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    category = parts[1].strip()
            elif line.startswith("**sonuç**:"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    result = parts[1].strip()
            elif line.startswith("**Sürüm**:"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    version_tag = parts[1].strip()

        # Bölüm içeriğini analiz edin
        problem = self._extract_section(content, "Sorun geçmişi")
        chosen_solution = self._extract_section(content, "Seçilen plan")
        outcome = self._extract_section(content, "Etki")
        reusable_for = self._extract_section(content, "Yeniden kullanılabilirlik")

        # Terk edilmiş planı ayrıştırın (Markdown sırasız liste)
        rejected_raw = self._extract_section(content, "Terk edilmiş plan")
        rejected_alternatives = []
        if rejected_raw:
            rejected_alternatives = [
                line.strip("- ").strip()
                for line in rejected_raw.split("\n")
                if line.strip().startswith("- ")
            ]

        # İlgili dosyaları ayrıştır (Markdown sırasız liste)
        related_raw = self._extract_section(content, "İlgili belgeler")
        related_files = []
        if related_raw:
            related_files = [
                line.strip("- ").strip()
                for line in related_raw.split("\n")
                if line.strip().startswith("- ")
            ]

        # Anahtar kelimeleri ayrıştır
        keywords_str = self._extract_section(content, "anahtar kelimeler")
        keywords = (
            [k.strip("`,") for k in keywords_str.split(",")] if keywords_str else []
        )

        return DecisionRecord(
            id=decision_id,
            title=title,
            timestamp=file_path.stem[:10],  # tarih kısmı
            agent_type=agent_type,
            category=category,
            problem=problem,
            chosen_solution=chosen_solution,
            result=result,
            outcome=outcome,
            reusable_for=reusable_for,
            rejected_alternatives=rejected_alternatives,
            related_files=related_files,
            keywords=keywords,
            version_tag=version_tag,
        )

    def _extract_section(self, content: str, section_name: str) -> str:
        """çıkarmak Markdown Belgede belirtilen bölüm içeriği"""
        pattern = f"## {section_name}\\n(.*?)(?=\\n## |\\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _calculate_relevance(self, query_terms: set, record: DecisionRecord) -> int:
        """Sorgunun karar kaydıyla uygunluk puanını hesaplayın"""
        score = 0

        # başlık maçı
        if record.title:
            title_lower = record.title.lower()
            for term in query_terms:
                if term in title_lower:
                    score += 5

        # soru eşleştirme
        if record.problem:
            problem_lower = record.problem.lower()
            for term in query_terms:
                if term in problem_lower:
                    score += 3

        # anahtar kelime eşleme
        if record.keywords:
            for term in query_terms:
                if term in record.keywords:
                    score += 2

        # Yeniden kullanılabilir sahne eşleştirme
        if record.reusable_for:
            reusable_lower = record.reusable_for.lower()
            for term in query_terms:
                if term in reusable_lower:
                    score += 2

        return score

    def list_decisions(
        self,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> list[DecisionRecord]:
        """
        Karar kayıtlarını listeleyin

        Args:
            category: Kategoriye göre filtrele
            limit: Maksimum miktarı iade edin

        Returns:
            Karar kayıtlarının listesi (ters kronolojik sırayla)
        """
        results = []

        # Değişiklik zamanına göre ters sırada geçiş yapın
        files = sorted(
            self.decisions_dir.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        for decision_file in files:
            if limit and len(results) >= limit:
                break

            try:
                content = decision_file.read_text(encoding="utf-8")
                record = self._parse_decision_file(decision_file, content)
                if record and (category is None or record.category == category):
                    results.append(record)
            except Exception:
                continue

        return results

    def get_stats(self) -> dict[str, Any]:
        """Karar hafızası istatistiklerini alın"""
        decisions = self.list_decisions(limit=1000)

        # Kategoriye göre istatistikler
        category_counts: dict[str, int] = {}
        for d in decisions:
            category_counts[d.category] = category_counts.get(d.category, 0) + 1

        return {
            "total_decisions": len(decisions),
            "by_category": category_counts,
            "latest_decision": decisions[0].id if decisions else None,
        }
