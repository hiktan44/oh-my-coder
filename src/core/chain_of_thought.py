"""
dusunce zinciriolabilirgor - kayitvegoster Agent akil yurutmesurec

Islev:
1. yakala Agent dusunce zinciri (akil yurutmeadim, kararbagligore) 
2. yapidepolamaakil yurutmesurec
3. olabilirgorgoster (metin/JSON/HTML) 
4. destekgeriizlevehata ayikla
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ReasoningStepType(Enum):
    """akil yurutmeadimtip"""

    ANALYSIS = "analysis"  # analizsorun
    PLANNING = "planning"  # olusturplan
    DECISION = "decision"  # yapkarar
    EXECUTION = "execution"  # yurutislem
    OBSERVATION = "observation"  # gozlemsonuc
    REFLECTION = "reflection"  # yansimatoplam
    CORRECTION = "correction"  # hataduzelt


class ConfidenceLevel(Enum):
    """ayarbilgidereceseviye"""

    HIGH = "high"  # yuksekayarbilgiderece
    MEDIUM = "medium"  # icindevb.ayarbilgiderece
    LOW = "low"  # dusukayarbilgiderece
    UNCERTAIN = "uncertain"  # hayirkesin


@dataclass
class ReasoningStep:
    """akil yurutmeadim"""

    step_id: str
    step_type: ReasoningStepType
    agent_name: str
    description: str
    reasoning: str  # akil yurutmesurec
    evidence: list[str]  # destekkanit
    conclusion: str  # tartis
    confidence: ConfidenceLevel
    timestamp: str
    duration_ms: int = 0
    parent_step_id: Optional[str] = None  # ustadim (kullandekatmanseviyeyapi) 
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "agent_name": self.agent_name,
            "description": self.description,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "conclusion": self.conclusion,
            "confidence": self.confidence.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "parent_step_id": self.parent_step_id,
            "metadata": self.metadata,
        }


@dataclass
class ChainOfThought:
    """dusunce zinciri"""

    chain_id: str
    task_description: str
    agent_name: str
    steps: list[ReasoningStep] = field(default_factory=list)
    start_time: str = ""
    end_time: Optional[str] = None
    status: str = "running"  # running / completed / failed
    final_conclusion: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "task_description": self.task_description,
            "agent_name": self.agent_name,
            "steps": [s.to_dict() for s in self.steps],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "final_conclusion": self.final_conclusion,
            "metadata": self.metadata,
        }

    def add_step(self, step: ReasoningStep) -> None:
        """ekleakil yurutmeadim"""
        self.steps.append(step)

    def complete(self, conclusion: str = "") -> None:
        """tamamladusunce zinciri"""
        self.status = "completed"
        self.end_time = datetime.now().isoformat()
        self.final_conclusion = conclusion

    def fail(self, error: str = "") -> None:
        """isareticinbasarisiz"""
        self.status = "failed"
        self.end_time = datetime.now().isoformat()
        self.final_conclusion = f"basarisiz: {error}"


class ChainOfThoughtRecorder:
    """dusunce zincirikayit"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".omc" / "chains"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_chains: dict[str, ChainOfThought] = {}

    def start_chain(
        self,
        task_description: str,
        agent_name: str,
        metadata: Optional[dict] = None,
    ) -> ChainOfThought:
        """baslatkayitdusunce zinciri"""
        chain = ChainOfThought(
            chain_id=f"chain-{uuid.uuid4().hex[:8]}",
            task_description=task_description,
            agent_name=agent_name,
            start_time=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        self.active_chains[chain.chain_id] = chain
        return chain

    def add_step(
        self,
        chain_id: str,
        step_type: ReasoningStepType,
        description: str,
        reasoning: str,
        evidence: Optional[list[str]] = None,
        conclusion: str = "",
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        parent_step_id: Optional[str] = None,
    ) -> Optional[ReasoningStep]:
        """ekleakil yurutmeadim"""
        chain = self.active_chains.get(chain_id)
        if not chain:
            return None

        step = ReasoningStep(
            step_id=f"step-{len(chain.steps) + 1:03d}",
            step_type=step_type,
            agent_name=chain.agent_name,
            description=description,
            reasoning=reasoning,
            evidence=evidence or [],
            conclusion=conclusion,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            parent_step_id=parent_step_id,
        )
        chain.add_step(step)
        return step

    def complete_chain(self, chain_id: str, conclusion: str = "") -> None:
        """tamamladusunce zinciri"""
        chain = self.active_chains.get(chain_id)
        if chain:
            chain.complete(conclusion)
            self._save_chain(chain)

    def fail_chain(self, chain_id: str, error: str = "") -> None:
        """isaretdusunce zinciribasarisiz"""
        chain = self.active_chains.get(chain_id)
        if chain:
            chain.fail(error)
            self._save_chain(chain)

    def get_chain(self, chain_id: str) -> Optional[ChainOfThought]:
        """aldusunce zinciri"""
        return self.active_chains.get(chain_id)

    def list_chains(self, agent_name: Optional[str] = None) -> list[ChainOfThought]:
        """listeledusunce zinciri"""
        chains = list(self.active_chains.values())
        if agent_name:
            chains = [c for c in chains if c.agent_name == agent_name]
        return chains

    def _save_chain(self, chain: ChainOfThought) -> None:
        """kaydetdusunce zincirikadardosya"""
        filepath = self.storage_dir / f"{chain.chain_id}.json"
        filepath.write_text(
            json.dumps(chain.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ChainVisualizer:
    """dusunce zinciriolabilirgor"""

    @staticmethod
    def to_text(chain: ChainOfThought) -> str:
        """donusturicinmetinformat"""
        lines = [
            "=" * 60,
            f"dusunce zinciri: {chain.chain_id}",
            f"gorev: {chain.task_description}",
            f"Agent: {chain.agent_name}",
            f"durum: {chain.status}",
            f"zamanarasinda: {chain.start_time} ~ {chain.end_time or 'ilerlesatiricinde'}",
            "=" * 60,
            "",
        ]

        for step in chain.steps:
            icon = {
                ReasoningStepType.ANALYSIS: "🔍",
                ReasoningStepType.PLANNING: "📋",
                ReasoningStepType.DECISION: "🎯",
                ReasoningStepType.EXECUTION: "⚡",
                ReasoningStepType.OBSERVATION: "👁️",
                ReasoningStepType.REFLECTION: "💭",
                ReasoningStepType.CORRECTION: "🔧",
            }.get(step.step_type, "•")

            confidence_icon = {
                ConfidenceLevel.HIGH: "✓",
                ConfidenceLevel.MEDIUM: "~",
                ConfidenceLevel.LOW: "?",
                ConfidenceLevel.UNCERTAIN: "!",
            }.get(step.confidence, "")

            lines.extend(
                [
                    f"{icon} [{step.step_id}] {step.step_type.value.upper()}",
                    f"   aciklama: {step.description}",
                    f"   akil yurutme: {step.reasoning[:100]}..."
                    if len(step.reasoning) > 100
                    else f"   akil yurutme: {step.reasoning}",
                ]
            )

            if step.evidence:
                lines.append(f"   kanit: {', '.join(step.evidence[:3])}")
            if step.conclusion:
                lines.append(f"   tartis: {step.conclusion}")

            lines.append(f"   ayarbilgiderece: {confidence_icon} {step.confidence.value}")
            lines.append("")

        if chain.final_conclusion:
            lines.extend(
                [
                    "-" * 60,
                    f"ensontartis: {chain.final_conclusion}",
                ]
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    @staticmethod
    def to_html(chain: ChainOfThought) -> str:
        """donusturicin HTML format"""
        steps_html = []
        for step in chain.steps:
            color = {
                ReasoningStepType.ANALYSIS: "#3b82f6",
                ReasoningStepType.PLANNING: "#8b5cf6",
                ReasoningStepType.DECISION: "#10b981",
                ReasoningStepType.EXECUTION: "#f59e0b",
                ReasoningStepType.OBSERVATION: "#06b6d4",
                ReasoningStepType.REFLECTION: "#ec4899",
                ReasoningStepType.CORRECTION: "#ef4444",
            }.get(step.step_type, "#6b7280")

            steps_html.append(f"""
            <div class="step" style="border-left: 4px solid {color}; padding-left: 12px; margin: 12px 0;">
                <div style="color: {color}; font-weight: bold;">
                    {step.step_type.value.upper()} [{step.step_id}]
                </div>
                <div style="margin: 4px 0;"><b>aciklama:</b> {step.description}</div>
                <div style="margin: 4px 0; color: #666;"><b>akil yurutme:</b> {step.reasoning[:200]}</div>
                {f'<div style="margin: 4px 0;"><b>tartis:</b> {step.conclusion}</div>' if step.conclusion else ""}
                <div style="font-size: 0.9em; color: #999;">
                    ayarbilgiderece: {step.confidence.value} | {step.timestamp}
                </div>
            </div>
            """)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>dusunce zinciri - {chain.chain_id}</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        .header {{ background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .step {{ background: #fafafa; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🧠 dusunce zinciriolabilirgor</h2>
        <p><b>gorev:</b> {chain.task_description}</p>
        <p><b>Agent:</b> {chain.agent_name} | <b>durum:</b> {chain.status}</p>
    </div>
    {"".join(steps_html)}
    {f'<div style="margin-top: 20px; padding: 16px; background: #e0f2fe; border-radius: 8px;"><b>ensontartis:</b> {chain.final_conclusion}</div>' if chain.final_conclusion else ""}
</body>
</html>"""

    @staticmethod
    def to_mermaid(chain: ChainOfThought) -> str:
        """donusturicin Mermaid akisresim"""
        lines = ["graph TD"]

        for step in chain.steps:
            node_id = step.step_id.replace("-", "_")
            label = f"{step.step_type.value[:3]}: {step.description[:30]}"
            lines.append(f"    {node_id}[{label}]")

            if step.parent_step_id:
                parent_id = step.parent_step_id.replace("-", "_")
                lines.append(f"    {parent_id} --> {node_id}")

        return "\n".join(lines)


# ===== kullanislifonksiyon =====


def create_recorder() -> ChainOfThoughtRecorder:
    """olusturdusunce zincirikayit"""
    return ChainOfThoughtRecorder()


def visualize_chain(chain: ChainOfThought, format: str = "text") -> str:
    """olabilirgordusunce zinciri

    Args:
        chain: dusunce zinciri
        format: cikti formati (text/html/mermaid)

    Returns:
        formatkarakter dizisi
    """
    if format == "html":
        return ChainVisualizer.to_html(chain)
    elif format == "mermaid":
        return ChainVisualizer.to_mermaid(chain)
    else:
        return ChainVisualizer.to_text(chain)
