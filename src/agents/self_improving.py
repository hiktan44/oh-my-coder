from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Aktif öğrenme modülü - Self-Improving Agent

Yürütme geri bildirimlerini toplayın, hata modlarını analiz edin ve stratejileri otomatik olarak optimize edin.
Kişisel gelişimi destekleyin: deneyimi otomatik olarak özetleyin ve optimize edin prompt,Depolamanın evrimsel tarihi.

Ana işlevler:
1. Görev tamamlandıktan sonra yürütme günlüklerini otomatik olarak analiz edin
2. Çıkarma başarılı/arıza modu
3. Optimizasyon önerileri oluşturma ve güncelleme Agent ile ilgili system prompt
4. Evrimsel geçmişi şuraya saklayın: .omc/state/agents/{agent_name}/
"""

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .base import (
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)
from .evolution import (
    DecisionMemory,
    EvolutionConfig,
    EvolutionRecord,
    EvolutionStore,
    SuccessPattern,
)


@dataclass
class ExecutionFeedback:
    """Yürütme geri bildirim kaydı"""

    id: Optional[int] = None
    timestamp: str = ""
    agent_type: str = ""  # executor, planner, debugger, etc.
    task_description: str = ""
    context_hash: str = ""  # Görev bağlamının basit bir karması
    success: bool = False
    execution_time: float = 0.0
    error_type: Optional[str] = None  # syntax_error, logic_error, timeout, etc.
    error_message: Optional[str] = None
    user_correction: Optional[str] = None  # Kullanıcı tarafından sağlanan düzeltmeler
    retry_count: int = 0
    final_success: bool = False  # Tekrar denedikten sonra başarılı oluyor mu?


@dataclass
class StrategyAdjustment:
    """Strateji ayarlama kaydı"""

    id: Optional[int] = None
    timestamp: str = ""
    agent_type: str = ""
    pattern_detected: str = ""  # Algılanan desen
    adjustment_type: str = ""  # prompt_update, parameter_tune, workflow_change
    adjustment_content: str = ""  # Özel ayarlamalar
    effectiveness_score: float = 0.0  # 1.0 = tamamen geçerli
    applied_count: int = 0  # Başvuru sayısı


class LearningStore:
    """Veri depolamayı öğrenme (SQLite)"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Veritabanı tablosunu başlat"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    task_description TEXT,
                    context_hash TEXT,
                    success BOOLEAN,
                    execution_time REAL,
                    error_type TEXT,
                    error_message TEXT,
                    user_correction TEXT,
                    retry_count INTEGER DEFAULT 0,
                    final_success BOOLEAN DEFAULT 0
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    pattern_detected TEXT NOT NULL,
                    adjustment_type TEXT NOT NULL,
                    adjustment_content TEXT NOT NULL,
                    effectiveness_score REAL DEFAULT 0.0,
                    applied_count INTEGER DEFAULT 0
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_agent_type
                ON execution_feedback(agent_type)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_error_type
                ON execution_feedback(error_type)
            """
            )

    def record_feedback(self, feedback: ExecutionFeedback) -> Optional[int]:
        """Yürütme geri bildirimini kaydedin"""
        feedback.timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO execution_feedback
                (timestamp, agent_type, task_description, context_hash, success,
                 execution_time, error_type, error_message, user_correction,
                 retry_count, final_success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback.timestamp,
                    feedback.agent_type,
                    feedback.task_description,
                    feedback.context_hash,
                    feedback.success,
                    feedback.execution_time,
                    feedback.error_type,
                    feedback.error_message,
                    feedback.user_correction,
                    feedback.retry_count,
                    feedback.final_success,
                ),
            )
            return cursor.lastrowid

    def record_adjustment(self, adjustment: StrategyAdjustment) -> Optional[int]:
        """Politika düzenlemelerini kaydedin"""
        adjustment.timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO strategy_adjustments
                (timestamp, agent_type, pattern_detected, adjustment_type,
                 adjustment_content, effectiveness_score, applied_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    adjustment.timestamp,
                    adjustment.agent_type,
                    adjustment.pattern_detected,
                    adjustment.adjustment_type,
                    adjustment.adjustment_content,
                    adjustment.effectiveness_score,
                    adjustment.applied_count,
                ),
            )
            return cursor.lastrowid

    def get_recent_failures(
        self, agent_type: str, limit: int = 10
    ) -> list[ExecutionFeedback]:
        """En son arıza kaydını alın"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM execution_feedback
                WHERE agent_type = ? AND success = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (agent_type, limit),
            ).fetchall()
            return [ExecutionFeedback(**dict(row)) for row in rows]

    def get_error_patterns(self, agent_type: str, min_count: int = 3) -> list[dict]:
        """Hata modellerini analiz edin"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT error_type, COUNT(*) as count,
                       AVG(execution_time) as avg_time,
                       AVG(retry_count) as avg_retries
                FROM execution_feedback
                WHERE agent_type = ? AND error_type IS NOT NULL
                GROUP BY error_type
                HAVING count >= ?
                ORDER BY count DESC
                """,
                (agent_type, min_count),
            ).fetchall()
            return [
                {
                    "error_type": row[0],
                    "count": row[1],
                    "avg_execution_time": row[2],
                    "avg_retries": row[3],
                }
                for row in rows
            ]

    def get_success_rate(self, agent_type: str, days: int = 7) -> float:
        """Başarı oranını hesaplayın"""
        with sqlite3.connect(self.db_path) as conn:
            # Use integer days directly in query (int, not user input)
            days_int = int(days)
            row = conn.execute(
                """
                SELECT
                    COUNT(CASE WHEN success = 1 THEN 1 END) * 1.0 / COUNT(*)
                FROM execution_feedback
                WHERE agent_type = ?
                AND timestamp > datetime('now', '-' || ? || ' days')
                """,
                (agent_type, str(days_int)),
            ).fetchone()
            return row[0] if row and row[0] else 0.0

    def get_adjustments(self, agent_type: str) -> list[StrategyAdjustment]:
        """Politika düzenleme kayıtlarını alın"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM strategy_adjustments
                WHERE agent_type = ?
                ORDER BY effectiveness_score DESC, applied_count DESC
                """,
                (agent_type,),
            ).fetchall()
            return [StrategyAdjustment(**dict(row)) for row in rows]


@register_agent
class SelfImprovingAgent(BaseAgent):
    """
    Aktif öğrenme Agent

    İşlev:
    1. Yürütme geribildirimini toplayın
    2. Arıza modlarını analiz edin
    3. Politika düzenleme önerileri oluşturma
    4. Ayar efektlerini izle
    """

    name = "self-improving"
    description = "Aktif öğrenme aracısı - Geri bildirim toplayın, kalıpları analiz edin, stratejileri optimize edin"
    lane = AgentLane.COORDINATION
    default_tier = "low"
    icon = "🧠"
    tools = ["file_read", "file_write"]

    def __init__(
        self,
        model_router=None,
        config: Optional[dict[str, Any]] = None,
        store: Optional[LearningStore] = None,
        skill_manager: Optional[Any] = None,
        evolution_config: Optional[EvolutionConfig] = None,
    ):
        super().__init__(model_router, config)
        db_path = Path.home() / ".omc" / "learning.db"
        self.store = store or LearningStore(str(db_path))
        # LearningsMemory için kullanılır best-practice → Skill Yükseltme (tembel içe aktarma döngüleri önler)
        from ..memory.learnings import LearningsMemory

        self._memory = LearningsMemory(Path.home() / ".omc")
        # SkillManager İsteğe bağlı enjeksiyon (test sırasında geçici dizini enjekte edin)
        self._skill_manager: Optional[Any] = skill_manager
        # evrim sistemi
        state_dir = Path.home() / ".omc" / "state"
        self._evolution_store = EvolutionStore(state_dir)
        self._decision_memory = DecisionMemory(state_dir)  # Sürüm yineleme belleği
        self._evolution_config = evolution_config or EvolutionConfig()

    @property
    def system_prompt(self) -> str:
        return """Aktif bir öğrenme optimizasyonu asistanısınız.
Yürütme geri bildirimlerini analiz edin, hata modlarını belirleyin ve politika ayarlama önerileri oluşturun.
Şunlara dikkat edin: hata türü dağılımı, başarı oranı eğilimi, yeniden deneme etkisi,prompt Optimizasyon yönü."""

    def record_execution(
        self,
        agent_type: str,
        task_description: str,
        success: bool,
        execution_time: float = 0.0,
        error: Optional[Exception] = None,
        user_correction: Optional[str] = None,
        retry_count: int = 0,
    ) -> Optional[int]:
        """Yürütme sonuçlarını kaydedin"""
        error_type = None
        error_message = None

        if error:
            error_type = self._classify_error(error)
            error_message = str(error)[:500]  # Sınır uzunluğu

        feedback = ExecutionFeedback(
            agent_type=agent_type,
            task_description=task_description[:200],
            context_hash=self._hash_context(task_description),
            success=success,
            execution_time=execution_time,
            error_type=error_type,
            error_message=error_message,
            user_correction=user_correction,
            retry_count=retry_count,
            final_success=success or (retry_count > 0),
        )
        return self.store.record_feedback(feedback)

    def analyze_and_improve(self, agent_type: str) -> list[StrategyAdjustment]:
        """İyileştirme önerilerini analiz edin ve oluşturun"""
        patterns = self.store.get_error_patterns(agent_type, min_count=2)
        adjustments = []

        for pattern in patterns:
            adjustment = self._generate_adjustment(agent_type, pattern)
            if adjustment:
                adjustment_id = self.store.record_adjustment(adjustment)
                adjustment.id = adjustment_id
                adjustments.append(adjustment)

        return adjustments

    def get_improved_prompt(self, agent_type: str, base_prompt: str) -> str:
        """Geliştirilmiş istem sözcükleri alın"""
        adjustments = self.store.get_adjustments(agent_type)

        # En etkili olanı filtreleyin prompt Ayarlama
        prompt_adjustments = [
            a
            for a in adjustments
            if a.adjustment_type == "prompt_update" and a.effectiveness_score > 0.5
        ]

        if not prompt_adjustments:
            return base_prompt

        # En etkili ayarlamaları uygulayın
        improved = base_prompt
        for adj in prompt_adjustments[:3]:  # Daha önce en çok uygulanan3bireysel
            improved += (
                f"\n\n[Optimize etmeyi öğrenme] {adj.pattern_detected}:\n{adj.adjustment_content}"
            )

        return improved

    def _classify_error(self, error: Exception) -> str:
        """Sınıflandırma hatası türü"""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()

        if "syntax" in error_msg or "syntax" in error_type:
            return "syntax_error"
        if "timeout" in error_msg or "timeout" in error_type:
            return "timeout"
        if "memory" in error_msg or "memory" in error_type:
            return "memory_error"
        if "permission" in error_msg or "access" in error_msg:
            return "permission_error"
        if "network" in error_msg or "connection" in error_msg:
            return "network_error"
        if "api" in error_msg or "rate limit" in error_msg:
            return "api_error"
        return f"{error_type}_error"

    def _hash_context(self, context: str) -> str:
        """Basit bağlamsal karma (önbelleğe alma, kriptografik olmayan amaçlar için)"""
        import hashlib

        return hashlib.sha256(context.encode()).hexdigest()[:16]

    def _generate_adjustment(
        self, agent_type: str, pattern: dict
    ) -> Optional[StrategyAdjustment]:
        """Hata kalıplarına dayalı ayarlama önerileri oluşturun"""
        error_type = pattern["error_type"]

        # Önceden tanımlanmış ayarlama stratejileri
        adjustments_map = {
            "syntax_error": (
                "prompt_update",
                "Kod oluşturmadan önce sözdiziminin doğruluğunu doğrulayın. kullanmak ast.parse incelemek Python kod.",
            ),
            "timeout": (
                "parameter_tune",
                "Zaman aşımı sınırını artırın veya görevi daha küçük adımlara bölün.",
            ),
            "memory_error": (
                "parameter_tune",
                "Akış veya toplu işlemeyi kullanarak aynı anda işlenen veri miktarını sınırlayın.",
            ),
            "api_error": (
                "workflow_change",
                "İşleme için üstel geri çekilme yeniden deneme mekanizması ekleyin API Akım sınırlaması.",
            ),
            "network_error": (
                "workflow_change",
                "Ağ bağlantısı kontrolü ve otomatik yeniden deneme mantığı ekleyin.",
            ),
        }

        if error_type not in adjustments_map:
            return None

        adj_type, adj_content = adjustments_map[error_type]

        return StrategyAdjustment(
            agent_type=agent_type,
            pattern_detected=f"{error_type} (Belli olmak {pattern['count']} İkinci sınıf)",
            adjustment_type=adj_type,
            adjustment_content=adj_content,
            effectiveness_score=0.5,  # Başlangıç ​​puanı, performansa dayalı sonraki ayarlamalar
        )

    def report(self, agent_type: Optional[str] = None) -> dict[str, Any]:
        """Öğrenim raporu oluştur"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "agents": {},
        }

        # belirtilmemişse agent_type, hepsini analiz et
        agent_types = [agent_type] if agent_type else self._get_all_agent_types()

        for at in agent_types:
            report["agents"][at] = {
                "success_rate_7d": self.store.get_success_rate(at, days=7),
                "success_rate_30d": self.store.get_success_rate(at, days=30),
                "error_patterns": self.store.get_error_patterns(at, min_count=2),
                "active_adjustments": len(self.store.get_adjustments(at)),
            }

        return report

    def _get_all_agent_types(self) -> list[str]:
        """Tüm kayıtları al agent tip"""
        with sqlite3.connect(self.store.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT agent_type FROM execution_feedback"
            ).fetchall()
            return [row[0] for row in rows]

    async def _run(self, task: str) -> AgentOutput:
        """Kişisel gelişim görevlerini gerçekleştirin"""
        import json

        parts = task.lower().split()
        if "report" in parts or "Rapor" in parts:
            data = self.report()
        elif "analyze" in parts or "analiz etmek" in parts:
            agent_type = parts[-1] if len(parts) > 1 else None
            if agent_type:
                data = self.analyze_task_logs(agent_type)
            else:
                adjustments = self.analyze_and_improve(agent_type) if agent_type else []
                data = {"adjustments": [str(a) for a in adjustments]}
        elif "promote" in parts or "güncelleme" in parts or "skill" in parts:
            # İrade best-practice Giriş şuna yükseltildi: Skill belge
            data = self.promote_best_practices_to_skills()
        elif "evolve" in parts or "evrim" in parts:
            # Kişisel gelişimi gerçekleştirin
            agent_type = parts[-1] if len(parts) > 1 else "executor"
            record = self.evolve(agent_type, trigger="manual")
            if record:
                data = {
                    "evolution_id": record.id,
                    "generation": record.generation,
                    "changes": record.changes,
                    "before": record.before_state,
                    "after": record.after_state,
                }
            else:
                data = {"message": "Evrim tetiklenmiyor (yetersiz örnek veya optimizasyona gerek yok)"}
        elif "stats" in parts or "istatistikler" in parts:
            # Evrimsel istatistikleri alın
            agent_type = parts[-1] if len(parts) > 1 else "executor"
            data = self.get_evolution_stats(agent_type)
        else:
            data = self.report()

        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=json.dumps(data, ensure_ascii=False, indent=2),
        )

    def auto_create_skill(
        self,
        task_context: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Otomatik olarak oluşturuldu Skill belge.

        itibaren task_context çıkarmak:
        - görev türü (category)
        - Temel adımlar (key_steps)
        - önemli karar (judgments)
        - potansiyel tuzaklar (gotchas)

        Yalnızca aşağıdaki koşullardan herhangi biri karşılanırsa oluşturun:
        1. Araç çağrısı ≥5 zamanlar ve başarı
        2. hata → çözmek
        3. Kullanıcı düzeltmesi
        4. Önemsiz olmayan iş akışı (çok adımlı)

        Args:
            task_context: Aşağıdaki anahtarları içeren bir sözlük:
                - agent_name: str
                - task: str(Görev açıklaması)
                - workflow: str(iş akışı adı)
                - result: str(Nihai sonuçların özeti)
                - steps: List[str](adımların listesi)
                - error: Optional[str](hata mesajı)
                - had_fix: bool(hatalardan kurtarılıp kurtarılmayacağı)
                - had_user_correction: bool
                - tool_call_count: int(araç çağrılarının sayısı)

        Returns:
            Skill bilgi dict;Koşullar karşılanmazsa geri dön None
        """
        from ..memory.skill_manager import SkillManager

        # ---- Yerleşmeye değer olup olmadığını değerlendirin ----
        tool_call_count = task_context.get("tool_call_count", 0)
        had_error = bool(task_context.get("error"))
        had_fix = task_context.get("had_fix", False)
        had_user_correction = task_context.get("had_user_correction", False)
        is_nontrivial = len(task_context.get("steps", [])) >= 3

        if not SkillManager.evaluate_skill_worthy(
            tool_call_count=tool_call_count,
            had_error=had_error,
            had_fix=had_fix,
            had_user_correction=had_user_correction,
            is_nontrivial_workflow=is_nontrivial,
        ):
            return None

        # ---- oluşturmak Skill içerik ----
        agent_name = task_context.get("agent_name", "unknown")
        task = task_context.get("task", "")
        workflow = task_context.get("workflow", "general")
        result_summary = task_context.get("result", "")[:300]
        steps = task_context.get("steps", [])
        error_msg = task_context.get("error", "")
        judgments = task_context.get("judgments", [])
        gotchas = task_context.get("gotchas", [])

        # yargıç category
        if error_msg:
            category = "debugging"
        elif had_user_correction:
            category = "corrections"
        elif workflow in {"build", "refactor", "test", "doc"}:
            category = "workflow"
        else:
            category = "best-practices"

        # oluşturmak skill_id(kopyalamayı önleyin)
        skill_id = SkillManager._slugify(f"{workflow}-{agent_name}-{task[:20]}")
        if len(skill_id) > 40:
            skill_id = skill_id[:40]

        # çıkarmak triggers
        triggers = []
        skip_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "this",
            "that",
            "into",
            "your",
            "some",
            "any",
            "all",
            "but",
            "not",
            "are",
            "was",
            "were",
            "been",
            "have",
            "has",
            "had",
            "will",
            "would",
        }
        for word in task.split():
            w = word.strip(".,!?;:()[]{}").lower()
            if len(w) >= 3 and w not in skip_words:
                triggers.append(w)

        # oluşturmak tags
        tags = list({workflow, agent_name})
        tags.extend(triggers[:3])

        # ---- inşa etmek body ----
        body_lines = [
            f"# {workflow.title()} with {agent_name.title()}",
            "",
            f"**Görev**: {task}",
            f"**İş akışı**: {workflow}",
            f"**Agent**: {agent_name}",
            "",
        ]

        # Anahtar adımlar
        if steps:
            body_lines.append("## Anahtar adımlar")
            for i, step in enumerate(steps, 1):
                body_lines.append(f"{i}. {step}")
            body_lines.append("")

        # önemli karar
        if judgments:
            body_lines.append("## önemli karar")
            body_lines.extend([f"- {j}" for j in judgments])
            body_lines.append("")

        # Yürütme sonucu
        body_lines.append("## Yürütme sonucu")
        body_lines.append(result_summary if result_summary else "(hiçbiri)")
        body_lines.append("")

        # Hata işleme
        if error_msg:
            body_lines.append("## Hata işleme")
            body_lines.append(error_msg[:200])
            body_lines.append("")

        # Potansiyel tuzaklar
        if gotchas:
            body_lines.append("## Potansiyel tuzaklar")
            body_lines.extend([f"- ⚠️ {g}" for g in gotchas])
            body_lines.append("")

        # Geçerli koşullar
        body_lines.append("## Geçerli koşullar")
        body_lines.append(f"- Görev türü: {workflow}")
        if triggers:
            body_lines.append(f"- kelimeleri tetiklemek: {', '.join(triggers[:5])}")

        body = "\n".join(body_lines)
        description = task[:120].strip()

        # ---- yazmak Skill belge(patch öncelik)----
        sm = self._skill_manager or SkillManager()
        try:
            skill_info = sm.patch(
                skill_id=skill_id,
                body=body,
                category=category,
                description=description,
                tags=tags,
                triggers=triggers[:5],
            )
        except Exception:
            try:
                skill_info = sm.create(
                    name=skill_id,
                    body=body,
                    category=category,
                    description=description,
                    tags=tags,
                    triggers=triggers[:5],
                )
            except Exception:
                return None

        # ---- aynı anda kaydedildi LearningsMemory ----
        try:
            self._memory.add(
                title=f"[Auto] {workflow}: {task[:40]}",
                content=body,
                category="best-practice",
                tags=tags,
                context=", ".join(triggers[:3]),
            )
        except Exception:
            pass  # Ana süreci etkilemez

        return skill_info

    def promote_best_practices_to_skills(
        self,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        İrade LearningsMemory İşaret şu: best-practice giriş
        otomatik olarak yükseltildi .omc/skills/best-practices/*.md Skill belge.

        Şunun için kullanılır:LearningsMemory.best_practices → SkillManager → .omc/skills/

        Args:
            dry_run: True = Yalnızca raporlar, gerçekte oluşturmaz

        Returns:
            Operasyon sonuçlarının özeti
        """
        from ..memory.skill_manager import SkillManager

        sm = SkillManager()
        best_practices = self._memory.get_by_category("best-practice")
        results: dict[str, Any] = {"created": [], "skipped": [], "errors": []}

        for entry in best_practices:
            skill_id = entry.id
            if not dry_run:
                try:
                    sm.patch(
                        skill_id=skill_id,
                        body=entry.content,
                        description=entry.title,
                        tags=entry.tags,
                        triggers=[entry.context] if entry.context else [],
                        category="best-practices",
                    )
                    results["created"].append(skill_id)
                except Exception as e:
                    results["errors"].append(
                        {"skill_id": skill_id, "error": type(e).__name__}
                    )
            else:
                results["skipped"].append(skill_id)

        results["total_best_practices"] = len(best_practices)
        results["total_skills"] = len(sm.list_skills())
        return results

    # ------------------------------------------------------------------
    # kendini geliştirme yöntemi (P0 Geliştirilmiş)
    # ------------------------------------------------------------------

    def analyze_task_logs(
        self,
        agent_type: str,
        recent_count: int = 10,
    ) -> dict[str, Any]:
        """
        Görev yürütme günlüklerini analiz edin ve öğrenilen dersleri çıkarın

        Son yürütme kayıtlarını analiz etmek için görev tamamlandıktan sonra otomatik olarak çağrılır.
        Tanıma başarılı/Başarısızlık modları evrimin temelini oluşturur.

        Args:
            agent_type: Agent tip
            recent_count: Son zamanları analiz et N kayıtlar

        Returns:
            Analiz sonuçları şunları içerir: success_patterns, failure_patterns, recommendations
        """
        analysis = {
            "agent_type": agent_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "success_patterns": [],
            "failure_patterns": [],
            "recommendations": [],
            "success_rate": 0.0,
            "sample_size": 0,
        }

        # En son yürütme kaydını alın
        with sqlite3.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM execution_feedback
                WHERE agent_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (agent_type, recent_count),
            ).fetchall()

            if not rows:
                return analysis

            records = [dict(row) for row in rows]
            analysis["sample_size"] = len(records)

            # Başarı oranını hesaplayın
            success_count = sum(1 for r in records if r.get("success"))
            analysis["success_rate"] = success_count / len(records) if records else 0.0

            # Başarı modelini çıkarın
            successful = [r for r in records if r.get("success")]
            if successful:
                # Başarılı kayıtların ortak özelliklerini analiz edin
                avg_time = sum(r.get("execution_time", 0) for r in successful) / len(
                    successful
                )
                analysis["success_patterns"].append(
                    {
                        "pattern": "successful_execution",
                        "avg_time": avg_time,
                        "count": len(successful),
                        "characteristics": self._extract_success_characteristics(
                            successful
                        ),
                    }
                )

            # Arıza modunu çıkart
            failed = [r for r in records if not r.get("success")]
            if failed:
                # Hata türüne göre gruplandır
                error_groups: dict[str, list[dict]] = {}
                for r in failed:
                    et = r.get("error_type") or "unknown"
                    if et not in error_groups:
                        error_groups[et] = []
                    error_groups[et].append(r)

                for error_type, group in error_groups.items():
                    analysis["failure_patterns"].append(
                        {
                            "pattern": error_type,
                            "count": len(group),
                            "examples": [
                                g.get("error_message", "")[:100] for g in group[:3]
                            ],
                        }
                    )

            # Öneriler oluştur
            threshold = self._evolution_config.improvement_threshold
            if analysis["success_rate"] < threshold:
                rate = analysis["success_rate"]
                analysis["recommendations"].append(
                    {
                        "type": "trigger_evolution",
                        "reason": f"başarı oranı {rate:.1%} eşiğin altında {threshold:.1%}",
                        "priority": "high",
                    }
                )

            if failed:
                analysis["recommendations"].append(
                    {
                        "type": "analyze_failures",
                        "reason": f"Keşfetmek {len(failed)} Arıza kayıtları, kök nedenin analiz edilmesi önerilir",
                        "priority": "medium",
                    }
                )

        return analysis

    def _extract_success_characteristics(
        self, successful_records: list[dict]
    ) -> list[str]:
        """Başarılı kayıtlardan ortak özellikleri çıkarın"""
        characteristics = []

        # analiz etmekYürütme süresi
        times = [
            r.get("execution_time", 0)
            for r in successful_records
            if r.get("execution_time")
        ]
        if times:
            avg = sum(times) / len(times)
            characteristics.append(f"ortalama yürütme süresi: {avg:.1f}s")

        # Yeniden denemeleri analiz edin
        retries = [r.get("retry_count", 0) for r in successful_records]
        if retries and sum(retries) == 0:
            characteristics.append("Tekrar denemeden başarı")
        elif retries:
            avg_retry = sum(retries) / len(retries)
            characteristics.append(f"Ortalama yeniden deneme sayısı: {avg_retry:.1f}")

        return characteristics

    def extract_patterns(
        self,
        agent_type: str,
        pattern_type: str = "all",
    ) -> list[SuccessPattern]:
        """
        Çıkarma başarılı/Arıza modelleri ve model kitaplığında saklanan

        Aşağıdakiler de dahil olmak üzere yürütme geçmişinden yeniden kullanılabilir kalıpları çıkarın:
        - Strateji Kalıbı (Başarılı İş Akışı)
        - Prompt Teknikler (Etkili İpucu Kelime Teknikleri)
        - Hata kurtarma kalıpları (hatalardan kurtulma yöntemleri)

        Args:
            agent_type: Agent tip
            pattern_type: desen türü (all/strategy/prompt/recovery)

        Returns:
            Çıkarılan desen listesi
        """
        patterns = []

        # Düzenleme kayıtlarını alın (strateji modu)
        if pattern_type in ("all", "strategy"):
            adjustments = self.store.get_adjustments(agent_type)
            for adj in adjustments:
                if (
                    adj.effectiveness_score
                    >= self._evolution_config.pattern_confidence_threshold
                ):
                    pattern = SuccessPattern(
                        id=f"{agent_type}-strategy-{adj.id}",
                        pattern_type="strategy",
                        description=(
                            f"{adj.pattern_detected}: {adj.adjustment_content[:100]}"
                        ),
                        context=adj.adjustment_type,
                        effectiveness_score=adj.effectiveness_score,
                        occurrences=adj.applied_count,
                    )
                    patterns.append(pattern)

                    # Evrim sistemine kaydet
                    self._evolution_store.add_success_pattern(
                        agent_name=agent_type,
                        pattern_type="strategy",
                        description=pattern.description,
                        context=pattern.context,
                    )

        # Başarılı yürütmenin ortak özelliklerini edinin (workflow modeli)
        if pattern_type in ("all", "workflow"):
            analysis = self.analyze_task_logs(agent_type, recent_count=20)
            for sp in analysis.get("success_patterns", []):
                for char in sp.get("characteristics", []):
                    pattern = SuccessPattern(
                        id=f"{agent_type}-workflow-{int(time.time())}",
                        pattern_type="workflow",
                        description=char,
                        context=sp.get("pattern", ""),
                        effectiveness_score=0.8,
                    )
                    patterns.append(pattern)

        return patterns

    def update_system_prompt(
        self,
        agent_type: str,
        base_prompt: str,
        analysis: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Evrimsel analize dayalı olarak güncellendi system prompt

        Çıkarılan başarılı modeller, stratejik ayarlamalar ve öğrenilen dersler
        İçine enjekte et Agent ile ilgili system prompt orta.

        Args:
            agent_type: Agent tip
            base_prompt: orijinal system prompt
            analysis: İsteğe bağlı analiz sonuçları (sağlanmadıysa otomatik olarak analiz edilir)

        Returns:
            güncellendi system prompt
        """
        if not self._evolution_config.enabled:
            return base_prompt

        # Hiçbir analiz sonucu sağlanmadıysa, önce analizi gerçekleştirin
        if analysis is None:
            analysis = self.analyze_task_logs(agent_type)

        # Sürüm bilgisini al
        prompt_version = self._evolution_store.get_prompt_version(agent_type)

        # Politika düzenlemelerini alın
        adjustments = self.store.get_adjustments(agent_type)
        prompt_adjustments = [
            a
            for a in adjustments
            if a.adjustment_type == "prompt_update" and a.effectiveness_score > 0.5
        ]

        # Başarı modelini edinin
        success_patterns = self._evolution_store.load_success_patterns(agent_type)

        # Optimize edilmiş içerik oluşturun
        optimization_parts = []

        # Politika düzenlemeleri ekleyin
        if prompt_adjustments:
            optimization_parts.append("## öğrenilen stratejiler")
            for adj in prompt_adjustments[:3]:
                optimization_parts.append(
                    f"- {adj.pattern_detected}: {adj.adjustment_content[:80]}"
                )

        # Başarı modeli ekle
        if success_patterns:
            optimization_parts.append("\n## Başarılı deneyim")
            for pattern in success_patterns[:5]:
                optimization_parts.append(f"- {pattern.description[:100]}")

        # Optimizasyon içeriği varsa yeni oluştur prompt
        if optimization_parts:
            new_prompt = f"""{base_prompt}

---
## 🧠 Kendi kendini geliştirme optimizasyonu (versiyon {prompt_version + 1})

{chr(10).join(optimization_parts)}

> Yukarıdaki içerik, kendi kendini geliştiren sistem tarafından otomatik olarak oluşturulmuştur ve geçmiş uygulama deneyimine dayanmaktadır.
"""
        else:
            new_prompt = base_prompt

        # Optimize edilmiş olanı kaydet prompt
        if new_prompt != base_prompt:
            self._evolution_store.save_optimized_prompt(agent_type, new_prompt)

        return new_prompt

    def evolve(
        self,
        agent_type: str,
        trigger: str = "manual",
    ) -> Optional[EvolutionRecord]:
        """
        Kişisel gelişimi gerçekleştirin

        Kişisel gelişim sürecini tamamlayın:
        1. Yürütme günlüklerini analiz edin
        2. Çıkarma başarılı/arıza modu
        3. İlke ayarlamaları oluştur
        4. yenilemek system prompt
        5. Evrimsel tarihi kaydedin

        Args:
            agent_type: Agent tip
            trigger: Tetikleme nedeni (manual/success_rate_low/user_correction/error_pattern)

        Returns:
            Evrim kaydı, eğer evrim tetiklenmezse döndürülür None
        """
        if not self._evolution_config.enabled:
            return None

        # Örnek sayısının yeterli olup olmadığını kontrol edin
        with sqlite3.connect(self.store.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM execution_feedback WHERE agent_type = ?",
                (agent_type,),
            ).fetchone()[0]

        if count < self._evolution_config.min_samples:
            return None

        # Evrim öncesi durumu kaydedin
        before_state = {
            "success_rate": self.store.get_success_rate(agent_type, days=7),
            "total_executions": count,
            "active_adjustments": len(self.store.get_adjustments(agent_type)),
        }

        # Analiz gerçekleştirin
        analysis = self.analyze_task_logs(agent_type, recent_count=20)

        # Çıkarma modu
        patterns = self.extract_patterns(agent_type)

        # İlke ayarlamaları oluştur
        adjustments = self.analyze_and_improve(agent_type)

        # yenilemek system prompt(gerekirse)
        base_prompt = self._evolution_store.load_optimized_prompt(agent_type) or ""
        if not base_prompt:
            base_prompt = f"sen bir profesyonelsin {agent_type} Agent."

        new_prompt = self.update_system_prompt(agent_type, base_prompt, analysis)

        # Evrimleşmiş durumu kaydedin
        after_state = {
            "success_rate": analysis["success_rate"],
            "patterns_extracted": len(patterns),
            "adjustments_generated": len(adjustments),
            "prompt_updated": new_prompt != base_prompt,
        }

        # Değişiklik listesi oluştur
        changes = []
        if adjustments:
            changes.append(f"oluşturmak {len(adjustments)} strateji ayarlaması")
        if patterns:
            changes.append(f"çıkarmak {len(patterns)} başarılı bir model")
        if new_prompt != base_prompt:
            changes.append("yenilemek system prompt")

        if not changes:
            return None  # gerçek değişiklik yok

        # Geçerli cebiri edinin
        generation = self._evolution_store.get_current_generation(agent_type)

        # Bir evrim kaydı oluşturun
        record = EvolutionRecord(
            id=f"evo-{agent_type}-{int(time.time())}",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            agent_type=agent_type,
            generation=generation,
            trigger=trigger,
            before_state=before_state,
            after_state=after_state,
            changes=changes,
        )

        # Evrim kaydını kaydet
        self._evolution_store.save_evolution_record(record)

        return record

    # ------------------------------------------------------------------
    # Sürüm yineleme belleği - Hayaletlerin duvara çarpması problemini çözme
    # ------------------------------------------------------------------

    def retrieve_past_decisions(
        self,
        problem_description: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Tekrarlanan hatalardan kaçınmak için geçmiş kararları alın

        Ne zaman Agent Bir sorunla karşılaştığınızda benzer sorunlara ilişkin geçmiş kararları almak için bu yöntemi çağırın.
        Elde etmek"Geçen sefer bu sorun nasıl çözüldü?"deneyim.

        Args:
            problem_description: Sorun açıklaması
            limit: Maksimum miktarı iade edin

        Returns:
            Karar listesi, her öğe içerir title, problem, chosen_solution, reusable_for Beklemek
        """
        decisions = self._decision_memory.retrieve(problem_description, limit=limit)

        return [
            {
                "id": d.id,
                "title": d.title,
                "problem": d.problem,
                "chosen_solution": d.chosen_solution,
                "result": d.result,
                "outcome": d.outcome,
                "reusable_for": d.reusable_for,
                "keywords": d.keywords,
            }
            for d in decisions
        ]

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
        related_files: Optional[list[str]] = None,
    ) -> str:
        """
        Önemli kararları kaydedin

        Args:
            title: Karar başlığı
            problem: Karşılaşılan sorunlar
            chosen_solution: Seçilen plan
            agent_type: Agent tip
            category: Karar Kategorisi (bug_fix/solution_choice/rejection/architecture)
            rejected_alternatives: Terk edilmiş plan
            result: sonuç (success/failure)
            outcome: Efekt açıklaması
            reusable_for: Uygulanabilir senaryolar
            related_files: İlgili belgeler

        Returns:
            decision_id
        """
        # Anahtar kelimeleri otomatik olarak çıkar
        keywords = self._decision_memory._extract_keywords(problem, chosen_solution)

        return self._decision_memory.record_decision(
            title=title,
            problem=problem,
            chosen_solution=chosen_solution,
            agent_type=agent_type,
            category=category,
            rejected_alternatives=rejected_alternatives,
            result=result,
            outcome=outcome,
            reusable_for=reusable_for,
            keywords=keywords,
            related_files=related_files,
        )

    def list_decisions(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Karar kayıtlarını listeleyin"""
        decisions = self._decision_memory.list_decisions(category=category, limit=limit)
        return [
            {
                "id": d.id,
                "title": d.title,
                "category": d.category,
                "result": d.result,
                "problem": (
                    d.problem[:100] + "..." if len(d.problem) > 100 else d.problem
                ),
            }
            for d in decisions
        ]

    def get_decision_stats(self) -> dict[str, Any]:
        """Karar hafızası istatistiklerini alın"""
        return self._decision_memory.get_stats()

    def get_evolution_stats(self, agent_type: str) -> dict[str, Any]:
        """Elde etmek Agent Evrim istatistikleri"""
        stats = self._evolution_store.get_evolution_stats(agent_type)
        stats["config"] = {
            "enabled": self._evolution_config.enabled,
            "improvement_threshold": self._evolution_config.improvement_threshold,
            "min_samples": self._evolution_config.min_samples,
        }
        return stats
