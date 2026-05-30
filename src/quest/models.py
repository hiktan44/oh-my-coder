from __future__ import annotations

"""
Quest Mode sayigoremodel

Quest = asenkronkendianaduzenlesurecgorev
bir Quest icerir: aciklama, olustur SPEC, yurutdurum, sonuc
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class QuestStatus(str, Enum):
    """gorevdurum"""

    PENDING = "pending"  # vb.bekleolustur SPEC
    SPEC_GENERATING = "spec_generating"  # olustur SPEC
    SPEC_READY = "spec_ready"  # SPEC iseipucu, vb.beklekullanicionayla
    EXECUTING = "executing"  # sonraplatformyuruticinde
    PENDING_REVIEW = "pending_review"  # adimyuruttamam, vb.beklekullanicidogrulaal
    COMPLETED = "completed"  # tamamla
    FAILED = "failed"  # basarisiz
    CANCELLED = "cancelled"  # iptal
    PAUSED = "paused"  # duraklat (vb.beklekullanicigirdi) 


class QuestPriority(str, Enum):
    """oncelikseviye"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# Pydantic model (kullande CLI gosterve API) 
# ============================================================


class SpecSection(BaseModel):
    """SPEC dokumantasyonbolum"""

    title: str = Field(..., description="bolumbaslik")
    content: str = Field(..., description="bolumicerik")
    order: int = Field(default=0, description="sira")


class AcceptanceCriteria(BaseModel):
    """kabul kriterleri"""

    id: str = Field(..., description="standart ID, format AC1, AC2...")
    description: str = Field(..., description="kabul kriterleriaciklama")
    testable: bool = Field(default=True, description="olup olmadigiolabilirotomatiktest")


class QuestSpec(BaseModel):
    """gorevkuraldokumantasyon"""

    title: str = Field(..., description="gorev basligi")
    overview: str = Field(..., description="gorevgenel bakis")
    motivation: str = Field(..., description="icinneisteryapbugorev")
    scope: list[str] = Field(default_factory=list, description="kapsam ici")
    out_of_scope: list[str] = Field(default_factory=list, description="kapsam disi")
    acceptance_criteria: list[AcceptanceCriteria] = Field(
        default_factory=list, description="kabul kriterleri"
    )
    risks: list[str] = Field(default_factory=list, description="riskipucu")
    estimated_time: str = Field(default="1h", description="ontahmintuketzaman")
    sections: list[SpecSection] = Field(default_factory=list, description="kotadisindabolum")

    def to_markdown(self) -> str:
        """donusturicin Markdown format"""
        lines = [
            f"# {self.title}",
            "",
            "## genel bakis",
            self.overview,
            "",
            "## motivasyon",
            self.motivation,
            "",
        ]

        if self.scope:
            lines.extend(["## kapsam ici", *[f"- {s}" for s in self.scope], ""])

        if self.out_of_scope:
            lines.extend(["## kapsam disi", *[f"- {s}" for s in self.out_of_scope], ""])

        if self.acceptance_criteria:
            lines.append("## kabul kriterleri")
            lines.extend(
                [
                    f"- [ ] **[{ac.id}]** {ac.description}"
                    for ac in self.acceptance_criteria
                ]
            )
            lines.append("")

        if self.risks:
            lines.extend(["## riskipucu", *[f"- ⚠️ {r}" for r in self.risks], ""])

        for section in sorted(self.sections, key=lambda s: s.order):
            lines.extend([f"## {section.title}", section.content, ""])

        lines.extend(
            [
                "---",
                f"*olusturzamanarasinda: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ]
        )

        return "\n".join(lines)


class QuestStep(BaseModel):
    """Quest yurutadim"""

    step_id: str = Field(..., description="adim ID")
    title: str = Field(..., description="adimbaslik")
    description: str = Field(..., description="adimaciklama")
    agent: str = Field(..., description="yurut Agent")
    status: QuestStatus = Field(default=QuestStatus.PENDING)
    result: Optional[str] = Field(None, description="adimsonuc")
    error: Optional[str] = Field(None, description="hata mesaji")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Quest(BaseModel):
    """Quest gorev"""

    id: str = Field(..., description="Quest ID (UUID) ")
    title: str = Field(..., description="gorev basligi")
    description: str = Field(..., description="kullanicihamgerekisteaciklama")
    project_path: str = Field(..., description="proje yolu")
    status: QuestStatus = Field(default=QuestStatus.PENDING)
    priority: QuestPriority = Field(default=QuestPriority.MEDIUM)
    spec: Optional[QuestSpec] = Field(None, description="olustur SPEC")
    spec_path: Optional[str] = Field(None, description="SPEC dosyayol")
    steps: list[QuestStep] = Field(default_factory=list, description="yurutadim")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_summary: Optional[str] = None
    output_dir: str = Field(default=".omc/quests", description="ciktidizin")

    def duration(self) -> Optional[float]:
        """donusyurutzamanuzunluk (saniye) """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        if self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    def progress(self) -> float:
        """donustamamlailerlederece 0.0 - 1.0"""
        if not self.steps:
            if self.status == QuestStatus.SPEC_READY:
                return 0.0
            if self.status in (
                QuestStatus.COMPLETED,
                QuestStatus.FAILED,
                QuestStatus.CANCELLED,
            ):
                return 1.0
            return 0.0
        completed = sum(1 for s in self.steps if s.status == QuestStatus.COMPLETED)
        return completed / len(self.steps)

    def to_summary(self) -> str:
        """donusturicinalintiisterkarakter dizisi"""
        duration = self.duration()
        duration_str = f"{duration:.0f}s" if duration else "ilerlesatiricinde"
        progress = int(self.progress() * 100)
        return (
            f"[{self.status.value:16}] [{self.priority.value:8}] "
            f"{self.title[:40]} | {progress}% | {duration_str}"
        )


# ============================================================
# CLI cikti formati
# ============================================================


@dataclass
class QuestDisplay:
    """Quest CLI gosterformat"""

    id: str
    title: str
    status: QuestStatus
    priority: QuestPriority
    progress_bar: str  # e.g. "██░░░░░░░░" 50%
    duration: str
    created_at: str

    @classmethod
    def from_quest(cls, quest: Quest) -> QuestDisplay:
        progress = int(quest.progress() * 10)
        bar = "█" * progress + "░" * (10 - progress)
        duration = quest.duration()
        duration_str = f"{duration:.0f}s" if duration else "ilerlesatiricinde"
        return cls(
            id=quest.id[:8],
            title=quest.title[:45],
            status=quest.status,
            priority=quest.priority,
            progress_bar=f"{bar} {int(quest.progress() * 100)}%",
            duration=duration_str,
            created_at=quest.created_at.strftime("%m-%d %H:%M"),
        )


# ============================================================
# bildirimmodel
# ============================================================


@dataclass
class QuestNotification:
    """Quest bildirim"""

    quest_id: str
    title: str
    event: str  # "started" | "spec_ready" | "step_completed" | "completed" | "failed"
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
