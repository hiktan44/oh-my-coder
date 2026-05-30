# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""
Ajanlar modülü

Tüm Ajanların dışa aktarım girişi.
@register_agent dekoratörü kullanılarak otomatik kaydedilir.
"""

from .analyst import AnalystAgent
from .api_agent import APIAgent
from .architect import ArchitectAgent
from .auth_agent import AuthAgent
from .base import BaseAgent, get_agent, list_agents, register_agent
from .code_research import CodeResearchAgent
from .code_reviewer import CodeReviewerAgent
from .code_simplifier import CodeSimplifierAgent
from .critic import CriticAgent
from .data_agent import DataAgent

# ---- Yeni eklenen Ajanlar (2026-04-12) ----
from .database import DatabaseAgent
from .debugger import DebuggerAgent
from .designer import DesignerAgent
from .devops import DevOpsAgent
from .document import DocumentAgent
from .executor import ExecutorAgent
from .explore import ExploreAgent
from .git_master import GitMasterAgent
from .migration import MigrationAgent
from .performance import PerformanceAgent
from .planner import PlannerAgent
from .prompt_agent import PromptAgent
from .qa_tester import QATesterAgent
from .scientist import ScientistAgent
from .security import SecurityReviewerAgent
from .self_improving import LearningStore, SelfImprovingAgent
from .skill_manage import SkillManageAgent
from .test_engineer import TestEngineerAgent
from .tracer import TracerAgent
from .uml import UMLAgent
from .verifier import VerifierAgent
from .vision import VisionAgent
from .writer import WriterAgent

# Tüm Ajanları dışa aktar (gruplama docs/guide/agents.md ile birebir uyumlu)
__all__ = [
    "BaseAgent",
    "register_agent",
    "get_agent",
    "list_agents",
    # ========================
    # Yapım / Analiz kanalı (9)
    # ========================
    "ExploreAgent",
    "AnalystAgent",
    "PlannerAgent",
    "ArchitectAgent",
    "ExecutorAgent",
    "VerifierAgent",
    "DebuggerAgent",
    "TracerAgent",
    "PerformanceAgent",
    "CodeResearchAgent",
    # ========================
    # İnceleme kanalı (2)
    # ========================
    "CodeReviewerAgent",
    "SecurityReviewerAgent",
    # ========================
    # Alan kanalı (16)
    # ========================
    "TestEngineerAgent",
    "DesignerAgent",
    "VisionAgent",
    "DocumentAgent",
    "WriterAgent",
    "ScientistAgent",
    "GitMasterAgent",
    "CodeSimplifierAgent",
    "QATesterAgent",
    "DatabaseAgent",
    "APIAgent",
    "DevOpsAgent",
    "UMLAgent",
    "MigrationAgent",
    "AuthAgent",
    "DataAgent",
    # ========================
    # Koordinasyon kanalı (4)
    # ========================
    "PromptAgent",
    "SelfImprovingAgent",
    "SkillManageAgent",
    "CriticAgent",
    # Self-Improving altyapısı
    "LearningStore",
]
