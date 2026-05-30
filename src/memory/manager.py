from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
import json

"""
hafizayonet - birgiris

tambirlestiruckatmanhafiza: 
- ShortTermMemory (kisadonemyapacakkonusma) 
- LongTermMemory (projeegilimiyi) 
- LearningsMemory (ogrenogrenkayit) 

puankatmanvarsinirhafizatasarim (ilham Hermes Agent) : 
- Tier 0 (Tiny) : < 500 token, entekraristercekirdekhafiza
- Tier 1 (incesec) : < 2000 token, yuksekdegerdegerogrehedef
- Tier 2 (Archive) : tamkaydetbelge, yoksinirdepolama
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .auto_compact import AutoCompact, CompactResult
from .learnings import LearningEntry, LearningsMemory
from .long_term import LongTermMemory, ProjectPreference, UserPreference
from .short_term import SessionContext, ShortTermMemory

# olabilirsec: tiktoken kullandekesin token hesapla
try:
    import tiktoken

    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False


@dataclass
class MemoryConfig:
    """hafizayapilandirma"""

    storage_dir: Path
    short_term_max_messages: int = 100
    short_term_max_age_hours: int = 24
    auto_save_interval: int = 300  # 5 puandakika
    # puankatmanhafizasinir (token sayi) 
    tier0_max_tokens: int = 500
    tier1_max_tokens: int = 2000
    # otomatiksikistiryapilandirma
    compact_threshold: float = 0.95
    warning_threshold: float = 0.70


class MemoryManager:
    """birhafizayonet"""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.short_term = ShortTermMemory(
            config.storage_dir, config.short_term_max_messages
        )
        self.long_term = LongTermMemory(config.storage_dir)
        self.learnings = LearningsMemory(config.storage_dir)
        self._enc = self._get_encoder()
        self.auto_compact = AutoCompact(
            self,
            compact_threshold=config.compact_threshold,
            warning_threshold=config.warning_threshold,
        )
        self._stats_file = config.storage_dir / "compact_stats.json"

    @property
    def compact_stats(self) -> dict:
        """donusmevcutyapacakkonusmasikistiristatistik (kalici) """
        if not self._stats_file.exists():
            return self._empty_stats()
        try:
            with open(self._stats_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return self._empty_stats()

    def record_compact(self, result) -> None:
        """kayitbirkezsikistirolaykadarkalicidepolama"""
        stats = self.compact_stats
        stats["total_compact_count"] += 1
        stats["total_tokens_saved"] += result.tokens_saved
        stats["total_messages_removed"] += result.messages_removed
        stats["total_deduplicated"] += getattr(result, "deduplicated_count", 0)
        stats["total_errors_removed"] += getattr(result, "error_removed_count", 0)
        try:
            self._stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "total_compact_count": 0,
            "total_tokens_saved": 0,
            "total_messages_removed": 0,
            "total_deduplicated": 0,
            "total_errors_removed": 0,
        }

    @staticmethod
    def _get_encoder() -> Optional[str]:
        """al tokenizer, basarisizdonus None"""
        if not _HAS_TIKTOKEN:
            return None
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None

    def count_tokens(self, text: str) -> int:
        """hesapla token sayi"""
        if self._enc:
            return len(self._enc.encode(text))
        return int(len(text) / 2.5)  # gerigeritahmin: Ingilizmetin~0.4 token/kelime

    def auto_compact_check(
        self,
        session: SessionContext,
        provider: str = "",
        model: str = "",
        force: bool = False,
        since_last_user: bool = False,
    ) -> CompactResult:
        """kontrolveyurutotomatiksikistir

        Args:
            session: mevcutyapacakkonusmabaglam
            provider: modelsaglayici
            model: model adi
            force: zorunlusikistir (yoksayesikdegerkontrol, varsayilan False) 
            since_last_user: ensonrakullanicimesajbaslattemizle (varsayilan False) 

        Returns:
            CompactResult: sikistirsonuc
        """
        result = self.auto_compact.check_and_compact(
            session, provider, model, force=force, since_last_user=since_last_user
        )
        if result.compacted:
            self.record_compact(result)
        return result

    def get_latest_session(self):
        """alenyeniaktifyapacakkonusma"""
        return self.short_term.get_latest_session()

    def save_session(self, session):
        """kaydetyapacakkonusma"""
        self.short_term.save_session(session)

    @classmethod
    def from_project(cls, project_path: Path) -> MemoryManager:
        """proje yoluolustur"""
        storage_dir = project_path / ".omc" / "memory"
        return cls(MemoryConfig(storage_dir=storage_dir))

    @classmethod
    def from_home(cls) -> MemoryManager:
        """kullanici home dizinolustur (globalhafiza) """
        storage_dir = Path.home() / ".oh-my-coder" / "memory"
        return cls(MemoryConfig(storage_dir=storage_dir))

    # ========== Short Term ==========

    def create_session(
        self, project_path: Optional[Path] = None, task: Optional[str] = None
    ) -> SessionContext:
        """olusturyeniyapacakkonusma"""
        return self.short_term.create_session(project_path, task)

    def get_current_session(self) -> Optional[SessionContext]:
        """almevcutyapacakkonusma"""
        return self.short_term.get_current_session()

    def save_current_session(self):
        """kaydetmevcutyapacakkonusma"""
        session = self.short_term.get_current_session()
        if session:
            self.short_term.save_session(session)

    # ========== Long Term ==========

    def get_user_prefs(self) -> UserPreference:
        """alkullaniciegilimiyi"""
        return self.long_term.get_user_prefs()

    def update_user_prefs(self, **kwargs):
        """guncellekullaniciegilimiyi"""
        self.long_term.update_user_prefs(**kwargs)

    def get_project_prefs(self, project_path: Path) -> ProjectPreference:
        """alprojeegilimiyi"""
        return self.long_term.get_project_prefs(project_path)

    def update_project_prefs(self, project_path: Path, **kwargs):
        """guncelleprojeegilimiyi"""
        self.long_term.update_project_prefs(project_path, **kwargs)

    def add_recent_project(self, project_path: Path):
        """ekleenyakinproje"""
        self.long_term.add_recent_project(project_path)

    def get_recent_projects(self, limit: int = 5) -> list[Path]:
        """alenyakinproje"""
        return self.long_term.get_recent_projects(limit)

    # ========== Learnings ==========

    def add_learning(
        self,
        title: str,
        content: str,
        category: str = "note",
        tags: Optional[list[str]] = None,
        context: str = "",
    ) -> LearningEntry:
        """ekleogrenogrenogrehedef"""
        return self.learnings.add(title, content, category, tags, context)

    def search_learnings(
        self, query: str, category: Optional[str] = None
    ) -> list[LearningEntry]:
        """araogrenogrenkayit"""
        return self.learnings.search(query, category)

    def get_learnings_by_category(self, category: str) -> list[LearningEntry]:
        """goresinifayrialogrenogrenkayit"""
        return self.learnings.get_by_category(category)

    def get_recent_learnings(self, limit: int = 10) -> list[LearningEntry]:
        """alenyakinogrenogrenkayit"""
        return self.learnings.get_recent(limit)

    # ========== genelbirlestir ==========

    def recall(self, query: str) -> dict[str, Any]:
        """genelbirlestircagirgeri: aravarhafizakatman"""
        results = {
            "short_term": [],
            "long_term": [],
            "learnings": self.search_learnings(query),
        }

        # araprojeegilimiyi
        project_prefs = list(self.long_term._projects.values())
        for prefs in project_prefs:
            if (
                query.lower() in prefs.name.lower()
                or query.lower() in prefs.notes.lower()
            ):
                results["long_term"].append(prefs.to_dict())

        return results

    # ========== puankatmanvarsinirhafiza (ilham Hermes Agent) ==========

    def get_tier0_summary(self) -> str:
        """
        al Tier 0 hafiza (< 500 token) . 

        cekirdekhafiza: mevcutproje, enyakingorev, anahtaregilimiyi. 
        kullandesistem Prompt enjekte. 
        """
        lines = []

        # projebilgi
        projects = self.long_term.get_recent_projects(limit=3)
        if projects:
            lines.append("## enyakinproje")
            for p in projects:
                prefs = self.long_term.get_project_prefs(p)
                lines.append(
                    f"- {prefs.name or p.name}: {prefs.framework or prefs.language}"
                )

        # kullaniciegilimiyi
        prefs = self.long_term.get_user_prefs()
        lines.append("\n## kullaniciegilimiyi")
        lines.append(f"- model: {prefs.default_model}")
        lines.append(f"- is akisi: {prefs.default_workflow}")

        # enyakinogrenogren
        recent = self.learnings.get_recent(limit=3)
        if recent:
            lines.append("\n## enyakingecdogrula")
            lines.extend([f"- {entry.title}: {entry.content[:80]}" for entry in recent])

        # birlestirbaglanvekes
        summary = "\n".join(lines)
        tokens = self.count_tokens(summary)
        if tokens > self.config.tier0_max_tokens:
            # keskadar token sinir
            if self._enc:
                return self._enc.decode(
                    self._enc.encode(summary)[: self.config.tier0_max_tokens]
                )
            return summary[: self.config.tier0_max_tokens * 4]
        return summary

    def get_tier1_summary(self, max_tokens: int = 2000) -> str:
        """
        al Tier 1 hafiza (< 2000 token) . 

        incesechafiza: projeozelbiltani, sikkullankomut, tekraristergecdogrula. 
        kullandebaglamek. 
        """
        lines = []

        # projedetay
        projects = self.long_term.get_recent_projects(limit=5)
        for p in projects:
            prefs = self.long_term.get_project_prefs(p)
            if prefs.notes:
                lines.append(f"## {prefs.name or p.name}")
                lines.append(prefs.notes[:200])

            if prefs.custom_commands:
                lines.append("### sikkullankomut")
                for alias, cmd in prefs.custom_commands.items():
                    lines.append(f"- {alias}: {cmd}")

        # dahacokogrenogrenkayit
        recent = self.learnings.get_recent(limit=10)
        for entry in recent:
            lines.append(f"## {entry.title}")
            lines.append(entry.content[:300])

        summary = "\n".join(lines)
        tokens = self.count_tokens(summary)
        if tokens > max_tokens:
            if self._enc:
                return self._enc.decode(self._enc.encode(summary)[:max_tokens])
            return summary[: max_tokens * 4]
        return summary

    def get_tier2_archive(self) -> str:
        """
        al Tier 2 tamkaydetbelge (yok token sinir) . 

        tamhafiza: varproje, varogrenogrenkayit, varegilimiyi. 
        kullandedisa aktar, ara, incelehesap. 
        """
        lines = []

        # kullaniciegilimiyi
        prefs = self.long_term.get_user_prefs()
        lines.append("## kullaniciegilimiyi")
        lines.append(f"- model: {prefs.default_model}")
        lines.append(f"- is akisi: {prefs.default_workflow}")
        lines.append(f"- anakonu: {prefs.theme}")
        lines.append(f"- duzenleduzenle: {prefs.editor}")
        lines.append(f"- Shell: {prefs.shell}")
        lines.append("")

        # varproje
        projects = self.long_term.get_recent_projects(limit=20)
        if projects:
            lines.append("## projeliste")
            for p in projects:
                prefs_p = self.long_term.get_project_prefs(p)
                lines.append(f"### {prefs_p.name or p.name}")
                lines.append(f"- yol: {p}")
                lines.append(f"- iskelet: {prefs_p.framework or '-'}")
                lines.append(f"- dil: {prefs_p.language or '-'}")
                if prefs_p.notes:
                    lines.append(f"- hazirlayorum: {prefs_p.notes[:300]}")
                if prefs_p.custom_commands:
                    lines.append("- sikkullankomut:")
                    for alias, cmd in prefs_p.custom_commands.items():
                        lines.append(f"  - {alias}: {cmd}")
                lines.append("")

        # varogrenogrenkayit
        all_learnings = self.learnings.get_recent(limit=50)
        if all_learnings:
            lines.append("## ogrenogrenkayit")
            for entry in all_learnings:
                lines.append(f"### {entry.title} [{entry.category}]")
                lines.append(entry.content[:500])
                if entry.tags:
                    lines.append(f"etiket: {', '.join(entry.tags)}")
                lines.append("")

        return "\n".join(lines)

    def get_memory_stats(self) -> dict[str, Any]:
        """alhafizaistatistikbilgi"""
        projects = self.long_term.get_recent_projects(limit=100)
        all_learnings = self.learnings.get_recent(limit=1000)

        tier0 = self.get_tier0_summary()
        tier1 = self.get_tier1_summary()

        return {
            "projects_count": len(projects),
            "learnings_count": len(all_learnings),
            "tier0_tokens": self.count_tokens(tier0),
            "tier1_tokens": self.count_tokens(tier1),
            "categories": list(set(e.category for e in all_learnings)),
        }
