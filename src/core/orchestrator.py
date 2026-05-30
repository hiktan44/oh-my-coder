from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Agent orkestrasyon - ajanayardereceveorkestrasyonmotor

cekirdekIslev:
1. Agent is akisiorkestrasyon
2. gorevpuancozvepuanyapilandirma
3. durumizleizlevekalici
4. vesatiryurutdestek

tasarimdusunceyol: 
asilprojearaciligiyla Skills sistemorkestrasyoncok Agent isbirligiyap. 
benleruygulabirhafifmiktarseviyeorkestrasyonmotor, destek: 
- sirayurut: explore → analyst → planner → executor
- vesatiryurut: cok Agent aynizamanis
- kosulyurut: goreoncesirasonuckararayarlasonradevamadim
"""

import asyncio
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..agents.health_check import HealthChecker

# Workflow loader
try:
    from src.config.workflow_loader import WorkflowLoader
except ImportError:
    WorkflowLoader = None  # type: ignore


def _get_trace_context_cls():
    try:
        from ..agents.transparency import TraceContext

        return TraceContext
    except ImportError:
        return None


class WorkflowStatus(Enum):
    """is akisidurum"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionMode(Enum):
    """yurutmod"""

    SEQUENTIAL = "sequential"  # sirayurut
    PARALLEL = "parallel"  # vesatiryurut
    CONDITIONAL = "conditional"  # kosulyurut


@dataclass
class WorkflowStep:
    """is akisiadim"""

    agent_name: str
    description: str
    dependencies: list[str] = field(default_factory=list)  # bagimlilikoncesiraadim
    condition: Optional[Callable[[dict], bool]] = None  # yurutkosul
    retry_count: int = 0
    timeout: float = 300.0  # 5puandakikavarsayilanasirizaman
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """is akisiyurutme sonucu"""

    workflow_id: str
    status: WorkflowStatus
    steps_completed: list[str]
    steps_failed: list[str]
    outputs: dict[str, Any]  # agent_name -> output
    total_tokens: int
    total_cost: float
    execution_time: float
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agent_names: list[str] = field(
        default_factory=list
    )  # buis akisiilgilive Agent adliste


# ontanimis akisisablon
WORKFLOW_TEMPLATES = {
    "build": [
        WorkflowStep("explore", "kesfetkodkutuphane"),
        WorkflowStep("analyst", "analizgerekiste", dependencies=["explore"]),
        WorkflowStep("planner", "olusturplan", dependencies=["analyst"]),
        WorkflowStep("architect", "tasarimmimari", dependencies=["planner"]),
        WorkflowStep("executor", "uygulakod", dependencies=["architect"]),
        WorkflowStep("verifier", "dogrulamatamamla", dependencies=["executor"]),
    ],
    "review": [
        WorkflowStep("explore", "kesfetkodkutuphane"),
        WorkflowStep("code-reviewer", "kodinceleme", dependencies=["explore"]),
        WorkflowStep("security-reviewer", "guvenlikinceleme", dependencies=["explore"]),
    ],
    "debug": [
        WorkflowStep("explore", "kesfetkodkutuphane"),
        WorkflowStep("debugger", "hata ayiklasorun", dependencies=["explore"]),
        WorkflowStep("verifier", "dogrulamaduzeltme", dependencies=["debugger"]),
    ],
    "test": [
        WorkflowStep("explore", "kesfetkodkutuphane"),
        WorkflowStep("test-engineer", "tasarimtest", dependencies=["explore"]),
        WorkflowStep("executor", "uygulatest", dependencies=["test-engineer"]),
        WorkflowStep("verifier", "satirtest", dependencies=["executor"]),
    ],
    # ---- yeniartis akisi (2026-04-11) ----
    # tumotomatikyoltarafindan: goregorev aciklamasiotomatiktanitip, secsecenbirlestiruygunis akisi
    "autopilot": [
        WorkflowStep("analyst", "gorevtiptani + secsecenbirlestiruygunis akisi"),
    ],
    # ---- dokumantasyonolusturmod (2026-04-12) ----
    # mimariuzman → yazel → dokumantasyonozelev, ucasamablokboru hatti, ozelyorumuzunlukyaziyapidokumantasyon
    "doc": [
        WorkflowStep("architect", "mimari tasarimiledokumantasyoniskelet", dependencies=[]),
        WorkflowStep("writer", "icerikilk taslak yazyaz", dependencies=["architect"]),
        WorkflowStep("document", "uzunlukyazidokumantasyonince ayarileformat", dependencies=["writer"]),
        WorkflowStep("verifier", "dokumantasyontamkontroldogrula", dependencies=["document"]),
    ],
    # ---- sirayurutorkestrasyon (2026-04-12) ----
    # kullansirayurut: kullanicitanimher Agent, goresirabaglikezyurut, heradimuretyapicinaltbiradimgirdi
    "sequential": [
        WorkflowStep("explore", "kod tabani yapisini kesfet", dependencies=[]),
        WorkflowStep("analyst", "derinlikanalizgerekisteilemevcut durum", dependencies=["explore"]),
        WorkflowStep("planner", "olusturdetayliyurutplan", dependencies=["analyst"]),
        WorkflowStep("executor", "yurutuygula", dependencies=["planner"]),
        WorkflowStep("verifier", "dogrulama sonucudogru", dependencies=["executor"]),
    ],
    # icinduzenlesurec: zamanicinkonusmatarz Code Review, Explorer + Critic almasikisbirligiyap
    "pair": [
        WorkflowStep("explore", "kesfetkodkutuphane"),
        WorkflowStep("critic", "kodinceleme (icin) ", dependencies=["explore"]),
        WorkflowStep("explorer", "sorunberraktemizle (kesfet) ", dependencies=["critic"]),
        WorkflowStep("critic", "onayladuzeltme (inceleme) ", dependencies=["explorer"]),
    ],
    # yeniden duzenlememod: analizsicaknokta → olusturyeniden duzenlemeplan → yurut → dogrulama
    "refactor": [
        WorkflowStep("analyst", "analizkodsicaknoktavekotutat"),
        WorkflowStep("planner", "olusturyeniden duzenlemeplan", dependencies=["analyst"]),
        WorkflowStep("code-simplifier", "yurutyeniden duzenleme", dependencies=["planner"]),
        WorkflowStep("verifier", "dogrulamayeniden duzenlemedogru", dependencies=["code-simplifier"]),
        WorkflowStep("test-engineer", "satirtestsaglaryokgerigeri", dependencies=["verifier"]),
    ],
}


def _detect_workflow_for_autopilot(task: str) -> str:
    """
    goregorev aciklamasiotomatiktaniolmalikullanis akisi
    Keyword → Workflow esle
    """
    task_lower = task.lower()
    if any(
        k in task_lower for k in ["bug", "cokme", "raporyanlis", "fix", "duzeltme", "hata", "crash"]
    ):
        return "debug"
    if any(k in task_lower for k in ["test", "test", "kullanornek", "coverage"]):
        return "test"
    if any(k in task_lower for k in ["refactor", "yeniden duzenleme", "iyi", "basit", "cleanup"]):
        return "refactor"
    if any(k in task_lower for k in ["review", "inceleme", "cr", "review"]):
        return "review"
    return "build"  # varsayilangit build akis


class Orchestrator:
    """
    Agent orkestrasyon

    cekirdekyontem: 
    - execute_workflow(): yuruttamis akisi
    - execute_step(): yuruttekiladim
    - save_state(): kaydetdurum
    - load_state(): yukledurum

    Tier 0 otomatikenjekte (2026-04-12) : 
    - herkezis akisitamamlasonra, otomatikoku .omc/skills/index.json
    - var Skill isimharf+aciklamaizleeklekadarsistem Prompt altkisim
    - izin ver Agent bilyolvarhangilerigecdogrulaolabilirkullan

    otomatikbiriktir (2026-04-12) : 
    - is akisitamamlasonracagri evaluate_skill_worthy karar verolup olmadigidegerbiriktir
    - doluyeterlikosulzamanotomatikolustur SKILL.md
    """

    def __init__(
        self,
        model_router,
        state_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ):
        """
        Args:
            model_router: modelyoltarafindan
            state_dir: durumkalicidizin
            skills_dir: Skill dosyakokdizin (varsayilan .omc/skills) 
            project_path: proje yolu (kullandepuankatmanhafizaenjekte) 
        """
        self.model_router = model_router
        self.state_dir = state_dir or Path(".omc/state")
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Skill kendiilerleyonet
        from ..memory.skill_manager import SkillManager

        self.skills_dir = skills_dir or self.state_dir.parent / "skills"
        self._skill_manager: Optional[SkillManager] = None

        # Checkpoint yonet (tembelyukle) 
        self._checkpoint_manager = None  # type: ignore

        # HealthChecker yonet (tembelyukle) 
        self._health_checker: Optional[HealthChecker] = None

        # Agent ornekonbellek
        self._agents: dict[str, Any] = {}

        # is akisidurum
        self._active_workflows: dict[str, WorkflowResult] = {}

        # puankatmanhafizayonet (tembelyukle) 
        self._memory_manager = None  # type: ignore
        self._project_path = project_path

        # Workflow yukle (YAML surucuhareket) 
        if WorkflowLoader is not None:
            self.workflow_loader = WorkflowLoader()
        else:
            self.workflow_loader = None  # type: ignore

    # ------------------------------------------------------------------
    # Skill kendiilerle (Tier 0 otomatikenjekte) 
    # ------------------------------------------------------------------

    @property
    def skill_manager(self):
        """tembelyukle SkillManager"""
        if self._skill_manager is None:
            from ..memory.skill_manager import SkillManager

            self._skill_manager = SkillManager(skills_dir=self.skills_dir)
        return self._skill_manager

    @property
    def checkpoint_manager(self):
        """tembelyukle CheckpointManager"""
        if self._checkpoint_manager is None:
            from .checkpoint import CheckpointManager

            self._checkpoint_manager = CheckpointManager(
                project_path=self.state_dir.parent
            )
        return self._checkpoint_manager

    @property
    def memory_manager(self):
        """tembelyukle MemoryManager (puankatmanvarsinirhafiza) """
        if self._memory_manager is None:
            from ..memory.manager import MemoryManager

            base = self._project_path or self.state_dir.parent
            self._memory_manager = MemoryManager.from_project(base)
        return self._memory_manager

    @property
    def health_checker(self) -> HealthChecker:
        """tembelyukle HealthChecker"""
        if self._health_checker is None:
            from ..agents.health_check import HealthChecker

            self._health_checker = HealthChecker(
                orchestrator=self,
                check_interval=60.0,
                stale_threshold=300.0,
                max_retries=3,
                state_dir=self.state_dir / "health",
            )
        return self._health_checker

    def inject_memory_context(self) -> str:
        """
        al Tier 0 cekirdekhafizaenjektemetin. 

        izleeklekadar AgentContext.skill_context, koyicinde Skill gecdogrulasonra. 
        """
        tier0 = self.memory_manager.get_tier0_summary()
        if not tier0 or not tier0.strip():
            return ""
        return f"\n\n{'=' * 50}\n## 🧠 cekirdekhafiza (Tier 0) \n{tier0}\n{'=' * 50}"

    def get_skill_inventory(self, max_tokens: int = 500) -> str:
        """
        tumunu al Skill isimharf+bircumlekonusmaaciklama. 
        saglar Tier 0 enjektekadar Agent sistem Prompt altkisim. 
        """
        return self.skill_manager.get_skill_inventory(max_tokens=max_tokens)

    def inject_skill_context(self, agent_class: str, max_tokens: int = 500) -> str:
        """
        icinbelirt Agent olustur Skill baglamenjektemetin. 

        izleeklekadar agent.system_prompt altkisim, uygula Tier 0 otomatikenjekte. 
        """
        inventory = self.get_skill_inventory(max_tokens=max_tokens)
        if not inventory or "(none)" in inventory:
            return ""
        return (
            f"\n\n{'=' * 50}\n"
            f"## 📚 olabilirkullangecdogrula (gelkendigecmisbiriktir) \n"
            f"{inventory}\n"
            f"orneginmevcutgorevileustanlatgecdogrulailgili, lutfenoncelikreferansveyacagri skill-manage arac. \n"
            f"{'=' * 50}"
        )

    # ------------------------------------------------------------------
    # otomatikbiriktir
    # ------------------------------------------------------------------

    async def _maybe_learn_from_workflow(
        self,
        workflow_name: str,
        context: dict[str, Any],
        result: WorkflowResult,
    ) -> None:
        """
        is akisitamamlasonradegerlendirolup olmadigidegerbiriktiricin Skill. 

        doluyeterliasagidakigorevbirkosulzamanotomatikolustur SKILL.md: 
        1. araccagri ≥5 kezvebasarili
        2. hata → coz
        3. kullaniciduzelt
        4. olmayansiradanis akisi (≥3 adim) 

        sonucyazgiris .omc/skills/<category>/<name>/SKILL.md. 
        """
        from ..memory.skill_manager import SkillManager

        # istatistikaraccagrikezsayi ( outputs tahmin) 
        tool_call_count = sum(
            len(getattr(o, "artifacts", {}).get("tool_calls", []))
            for o in result.outputs.values()
        )
        # egeryokyontemkesinistatistik, kadarazgoreadimsayitahmin
        if tool_call_count == 0:
            tool_call_count = len(result.steps_completed)

        had_error = result.status == WorkflowStatus.FAILED
        had_fix = context.get("_had_fix", False)
        had_user_correction = context.get("_had_user_correction", False)
        is_nontrivial = len(result.steps_completed) >= 3

        if not SkillManager.evaluate_skill_worthy(
            tool_call_count=tool_call_count,
            had_error=had_error,
            had_fix=had_fix,
            had_user_correction=had_user_correction,
            is_nontrivial_workflow=is_nontrivial,
        ):
            return

        # olustur Skill taslak
        final_result = ""
        if result.outputs:
            last = list(result.outputs.values())[-1]
            final_result = getattr(last, "result", "")[:300] or str(last)[:300]

        # olustur task_context saglar auto_create_skill kullan
        task_context = {
            "agent_name": (
                result.steps_completed[-1] if result.steps_completed else "orchestrator"
            ),
            "task": context.get("task", ""),
            "workflow": workflow_name,
            "result": final_result,
            "steps": result.steps_completed,
            "error": str(result.error) if result.error else None,
            "had_fix": context.get("_had_fix", False),
            "had_user_correction": context.get("_had_user_correction", False),
            "tool_call_count": tool_call_count,
            "judgments": context.get("_judgments", []),
            "gotchas": context.get("_gotchas", []),
        }

        # araciligiyla SelfImprovingAgent.auto_create_skill tamamlabiriktir
        from ..agents.self_improving import SelfImprovingAgent

        try:
            sia = SelfImprovingAgent(skill_manager=self.skill_manager)
            sia.auto_create_skill(task_context)
        except Exception:
            pass  # sessiz, hayirbloklais akisi

    async def _maybe_evolve_agents(
        self,
        result: WorkflowResult,
    ) -> None:
        """
        is akisitamamlasonratetikgonder Agent kendiilerle. 

        icinkatilileis akisivar Agent yurutilerleanaliz: 
        1. analizyurutlog
        2. cikarbasarili/basarisizmod
        3. guncelle system prompt (ornegingerekister) 

        sadecene zamanbaslatkullankendiilerleveorneksayiyeterliyeterlizamanyurut. 
        """
        from ..agents.self_improving import EvolutionConfig, SelfImprovingAgent

        config = EvolutionConfig()
        if not config.enabled:
            return

        try:
            sia = SelfImprovingAgent(evolution_config=config)

            # icinherkatilile Agent yurutilerle
            for agent_name in result.steps_completed:
                try:
                    record = sia.evolve(
                        agent_type=agent_name,
                        trigger="workflow_completion",
                    )
                    if record:
                        # ilerlebasarili, kayitkadarbaglam
                        result.outputs[f"_evolution_{agent_name}"] = {
                            "evolution_id": record.id,
                            "generation": record.generation,
                            "changes": record.changes,
                        }
                except Exception:
                    pass  # tekil Agent ilerlebasarisizhayiretkionuno
        except Exception:
            pass  # sessiz, hayirbloklais akisi

    # ------------------------------------------------------------------
    # baglamolustur
    # ------------------------------------------------------------------

    def _build_agent_context(
        self,
        agent_name: str,
        context: dict[str, Any],
    ):
        """olusturbir AgentContext (icerir Skill enjekte + Tier 0 hafizaenjekte) """
        from ..agents.base import AgentContext

        skill_ctx = self.inject_skill_context(agent_name)
        memory_ctx = self.inject_memory_context()

        return AgentContext(
            project_path=Path(context.get("project_path", ".")),
            task_description=context.get("task", ""),
            previous_outputs=context.get("_result_outputs", {}),
            skill_context=skill_ctx + memory_ctx,
        )

    # ------------------------------------------------------------------
    # Agent kayitileal
    # ------------------------------------------------------------------

    def register_agent(self, agent):
        """kayit Agent ornek"""
        self._agents[agent.name] = agent

    def get_agent(self, name: str, **override_attrs):
        """al Agent ornek, **override_attrs izin verkaplayazornekozellik (ornegin use_sourcegraph) """
        if name not in self._agents:
            # dinamikyukle
            from ..agents.base import get_agent

            agent_class = get_agent(name)
            if agent_class:
                # enjekte orchestrator, izin agent olabilircagri call_subagent()
                agent = agent_class(self.model_router, orchestrator=self)
                self._agents[name] = agent
            else:
                raise ValueError(f"henuzbil Agent: {name}")

        agent = self._agents[name]
        # kaplayazornekozellik (ornegin use_sourcegraph) 
        for attr, val in override_attrs.items():
            if hasattr(agent, attr):
                setattr(agent, attr, val)
            else:
                # Agent hayirdestekbuozellik, sessizatla (orneginonuno agent alkadar sourcegraph parametre) 
                pass
        return agent

    async def invoke_subagent(
        self,
        agent_name: str,
        task: str,
        context: dict[str, Any],
        max_depth: int = 3,
    ):
        """
        cagrialt Agent (destekicicecagri, engelleyoksinirrekursif) 

        budir P1-6 Agent altsistemyeniden duzenleme Phase 1 cekirdekyeniartyontem. 
        izin verherhangi Agent araciligiyla Orchestrator ayarderecebaskabir Agent yapicinaltgorev. 

        tipiktipkullanyontem (tarafindan Agent icinde execute() icindecagri) : 
            sub_result = await self.invoke_subagent(
                agent_name="analyst",
                task="analizbublokkodperformanssorun",
                context={"project_path": "/path/to/project", ...},
            )

        Args:
            agent_name: alt Agent ad (gerekliicinde AGENT_REGISTRY icindekayit) 
            task: altgorev aciklamasi
            context: baglam (icerir project_path, override_model vb.) 
            max_depth: enbuyukcagriderinlik, varsayilan 3 katmanengellerekursif

        Returns:
            AgentOutput: alt Agent yurutme sonucu

        Raises:
            RecursionError: asiri max_depth zamanfirlat
            ValueError: agent_name mevcut degilzamanfirlat
        """
        current_depth = context.get("_subagent_depth", 0)
        if current_depth >= max_depth:
            raise RecursionError(
                f"alt Agent cagriasirienbuyukderinlik {max_depth} (engelleduryoksinirrekursif) "
            )

        # kuralt Agent baglam
        from ..agents.base import AgentContext, AgentOutput, AgentStatus

        sub_context = AgentContext(
            project_path=context.get("project_path", Path.cwd()),
            task_description=task,
            working_directory=context.get("working_directory"),
            relevant_files=[],
            previous_outputs=context.get("previous_outputs", {}),
            metadata={"parent_depth": current_depth},
            skill_context=context.get("skill_context", ""),
            override_model=context.get("override_model"),
        )
        sub_context._subagent_depth = current_depth + 1  # type: ignore

        # alalt Agent ornek
        agent = self.get_agent(agent_name)

        # yurutaltgorev (kemerasirizamankoru) 
        import asyncio

        try:
            output = await asyncio.wait_for(
                agent.execute(sub_context),
                timeout=context.get("subagent_timeout", 300),
            )
            return output
        except asyncio.TimeoutError:
            return AgentOutput(
                agent_name=agent_name,
                status=AgentStatus.FAILED,
                error=f"alt Agent yurutasirizaman (>{context.get('subagent_timeout', 300)}s) ",
            )

    def _sourcegraph_overrides(self, context: dict[str, Any]) -> dict[str, Any]:
        """ context icindecikar Sourcegraph yapilandirmaparametre, iletiletver Agent ornek"""
        overrides: dict[str, Any] = {}
        if context.get("use_sourcegraph"):
            overrides["use_sourcegraph"] = True
        if "sourcegraph_limit" in context:
            overrides["sourcegraph_limit"] = context["sourcegraph_limit"]
        return overrides

    async def execute_workflow(
        self,
        workflow_name: str,
        context: dict[str, Any],
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        skip_checkpoint: bool = False,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> WorkflowResult:
        """
        yurutis akisi

        Args:
            workflow_name: is akisi adiveyaadimliste
            context: yurutbaglam
            mode: yurutmod
            progress_callback: ilerlederecegeri aramafonksiyon, imzaisimicin (step_name, status) -> None
                              status olabilirsecdeger: "started", "completed", "failed"

        Returns:
            WorkflowResult: yurutme sonucu
        """
        import time
        import uuid

        workflow_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # alis akisisablon
        if isinstance(workflow_name, str):
            # autopilot ozelisle: otomatikalgilamagorevtipveyoltarafindan
            if workflow_name == "autopilot":
                actual = _detect_workflow_for_autopilot(context.get("task", ""))
                workflow_name = actual
                context["_autopilot_routed_to"] = actual

            # kullan YAML is akisiyukle (destekkullaniciozeluzerine yaz) 
            if self.workflow_loader is not None:
                steps = self.workflow_loader.load_workflow(workflow_name)
            else:
                steps = WORKFLOW_TEMPLATES.get(workflow_name, [])
        else:
            steps = workflow_name

        if not steps:
            raise ValueError(f"yoketkiis akisi: {workflow_name}")

        # baslatsonuc
        result = WorkflowResult(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            steps_completed=[],
            steps_failed=[],
            outputs={},
            total_tokens=0,
            total_cost=0.0,
            execution_time=0.0,
            agent_names=[s.agent_name for s in steps],
        )

        self._active_workflows[workflow_id] = result

        # ---- otomatikhizligore: gorevbaslatoncekayit checkpoint ----
        if not skip_checkpoint:
            try:
                task_id = context.get("task", "unknown").replace(" ", "-")[:30]
                task_desc = context.get("task", "")
                cp_id = self.checkpoint_manager.create(
                    task_id=task_id,
                    description=f"Workflow baslat: {workflow_name} | {task_desc}",
                )
                context["_checkpoint_id"] = cp_id
            except Exception:
                pass  # sessiz, hayirbloklais akisi

        # kaydet progress_callback kadar result, saglaricindekisimyontemkullan
        result._progress_callback = progress_callback  # type: ignore

        try:
            # goremodyurut
            if mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential(steps, context, result)
            elif mode == ExecutionMode.PARALLEL:
                await self._execute_parallel(steps, context, result)
            else:
                await self._execute_conditional(steps, context, result)

            result.status = WorkflowStatus.COMPLETED

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            import traceback as _tb

            _detail = f"{type(e).__name__}: {e}"
            if os.environ.get("OMC_DEBUG", "").lower() in ("1", "true", "yes"):
                _detail += f"\n\n{_tb.format_exc()}"
            result.error = _detail

        finally:
            result.execution_time = time.time() - start_time
            self._save_workflow_result(result)

        # ---- otomatikbiriktir: degerlendirolup olmadigidegerolustur Skill (Tier 0) ----
        try:
            await self._maybe_learn_from_workflow(workflow_name, context, result)
        except Exception:
            pass  # sessiz, hayirbloklais akisi

        # ---- kendiilerle: analizyurutlog, iyi Agent prompt----
        try:
            await self._maybe_evolve_agents(result)
        except Exception:
            pass  # sessiz, hayirbloklais akisi

        return result

    async def _execute_sequential(
        self,
        steps: list[WorkflowStep],
        context: dict[str, Any],
        result: WorkflowResult,
    ):
        """sirayurutadim (setolsaglikkontrolileotomatikyeniden dene) """

        # alilerlederecegeri arama
        progress_callback = getattr(result, '_progress_callback', None)

        for step in steps:
            # kontrolbagimlilik
            for dep in step.dependencies:
                if dep not in result.steps_completed:
                    raise ValueError(f"adim {step.agent_name} bagimlilik {dep} henuztamamla")

            agent_name = step.agent_name

            # raporilerlederece: adimbaslat
            if progress_callback:
                progress_callback(agent_name, "started")

            retry_count = 0
            max_retries = getattr(self, "_health_checker", None)
            max_retries = max_retries.max_retries if max_retries else 3

            while True:
                # ---- kayitsaglikkontrol: Agent baslatyurut ----
                hc = self.health_checker
                hc.register_agent(
                    agent_name=agent_name,
                    task_id=f"wf_{result.workflow_id}_step_{step.agent_name}",
                    workflow_id=result.workflow_id,
                    step_index=steps.index(step),
                )

                try:
                    agent = self.get_agent(
                        agent_name, **self._sourcegraph_overrides(context)
                    )
                    agent_context = self._build_agent_context(agent_name, context)

                    output = await asyncio.wait_for(
                        agent.execute(agent_context),
                        timeout=step.timeout,
                    )

                    # ---- kalpatlakayit: yurutbasarili, iptalkayit ----
                    hc.unregister_agent(agent_name)

                    if output.status.value == "completed":
                        result.steps_completed.append(agent_name)
                        result.outputs[agent_name] = output
                        result.total_tokens += output.usage.get("total_tokens", 0)

                        # raporilerlederece: adimtamamla
                        if progress_callback:
                            progress_callback(agent_name, "completed")

                        break  # ilerlegirisaltbiradim
                    else:
                        raise Exception(f"Agent {agent_name} yurutbasarisiz: {output.error}")

                except TimeoutError:
                    # raporilerlederece: adimbasarisiz
                    if progress_callback:
                        progress_callback(agent_name, "failed")

                    error = f"Agent {agent_name} yurutasirizaman (>{step.timeout}s) "
                    hc.unregister_agent(agent_name)

                    if hc.record_failure(agent_name, error):
                        # asiriyeniden deneustsinir
                        result.steps_failed.append(agent_name)
                        raise Exception(error)

                    # halaolabiliryeniden dene → bulbosbos Agent tekrarpuanyapilandirma
                    retry_count += 1
                    new_agent = hc.reassign_task(
                        agent_name=agent_name,
                        workflow_id=result.workflow_id,
                        step=step,
                    )
                    if new_agent:
                        agent_name = new_agent
                        hc.register_agent(agent_name, workflow_id=result.workflow_id)
                    else:
                        result.steps_failed.append(agent_name)
                        raise Exception(f"yokyontemtekrarpuanyapilandirmagorev: {error}")
                    # yeniden dene

                except Exception as step_err:
                    # raporilerlederece: adimbasarisiz
                    if progress_callback:
                        progress_callback(agent_name, "failed")

                    hc.unregister_agent(agent_name)
                    error_msg = str(step_err)

                    if hc.record_failure(agent_name, error_msg):
                        result.steps_failed.append(agent_name)
                        raise

                    retry_count += 1
                    new_agent = hc.reassign_task(
                        agent_name=agent_name,
                        workflow_id=result.workflow_id,
                        step=step,
                    )
                    if new_agent:
                        agent_name = new_agent
                        hc.register_agent(agent_name, workflow_id=result.workflow_id)
                    else:
                        result.steps_failed.append(agent_name)
                        raise
                    # yeniden dene

    async def _execute_parallel(
        self,
        steps: list[WorkflowStep],
        context: dict[str, Any],
        result: WorkflowResult,
    ):
        """
        vesatiryurutadim

        uyguladusunceyol: 
        1. icinadimgorebagimliliktopolojipuankatman
        2. aynibirkatmanvaradimvegonderyurut (asyncio.gather) 
        3. vb.bekletamkatmantamamlasonratekrarilerlegirisaltbirkatman
        buornek review is akisi code-reviewer + security-reviewer olabilirileaynizamankos, 
        kiyassirayuruthizliyaklasikbirkat. 
        """

        # olusturkuradimsozluk
        step_map: dict[str, WorkflowStep] = {s.agent_name: s for s in steps}

        # topolojipuankatman
        levels: list[list[WorkflowStep]] = []
        remaining = set(step_map.keys())

        while remaining:
            # bulkadarvarbagimliliktumtamamlaadim (yapicinmevcutkatman) 
            current_level = [
                step_map[name]
                for name in remaining
                if all(
                    dep in result.steps_completed for dep in step_map[name].dependencies
                )
            ]
            if not current_level:
                # vardongubagimlilikveyayoketkibagimlilik
                break

            levels.append(current_level)
            for step in current_level:
                remaining.remove(step.agent_name)

        # gorekatmanyurut: aynikatmanvesatir, katmanarasindasira
        for level in levels:
            tasks = []
            for step in level:
                agent = self.get_agent(
                    step.agent_name, **self._sourcegraph_overrides(context)
                )
                agent_context = self._build_agent_context(step.agent_name, context)
                tasks.append(
                    asyncio.wait_for(
                        agent.execute(agent_context),
                        timeout=step.timeout,
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, task_result in zip(level, results):
                if isinstance(task_result, Exception):
                    result.steps_failed.append(step.agent_name)
                    raise Exception(
                        f"Agent {step.agent_name} vesatiryurutbasarisiz: {task_result}"
                    )

                output = task_result
                if output.status.value == "completed":
                    result.steps_completed.append(step.agent_name)
                    result.outputs[step.agent_name] = output
                    result.total_tokens += output.usage.get("total_tokens", 0)
                else:
                    result.steps_failed.append(step.agent_name)
                    raise Exception(f"Agent {step.agent_name} yurutbasarisiz: {output.error}")

    async def _execute_conditional(
        self,
        steps: list[WorkflowStep],
        context: dict[str, Any],
        result: WorkflowResult,
    ):
        """
        kosulyurutadim

        uyguladusunceyol: 
        - icinheradim, yurutoncekontrol step.condition(result.outputs)
        - condition icin None → toplamdiryurut
        - condition donus True → yurut
        - condition donus False → atla (hayirhesapgiris completed, ancakayricahayirraporyanlis) 
        - condition firlatfarklisik → isaretbasarisiz
        """

        for step in steps:
            # kontrolbagimlilik
            for dep in step.dependencies:
                if dep not in result.steps_completed:
                    raise ValueError(f"adim {step.agent_name} bagimlilik {dep} henuztamamla")

            # yurutkosulkontrol
            if step.condition is not None:
                try:
                    should_run = step.condition(result.outputs)
                except Exception as cond_err:
                    result.steps_failed.append(step.agent_name)
                    raise Exception(f"adim {step.agent_name} kosulyurutfarklisik: {cond_err}")
                if not should_run:
                    # kosulhayirdoluyeterli, atlabuadim
                    continue

            try:
                agent = self.get_agent(
                    step.agent_name, **self._sourcegraph_overrides(context)
                )
                agent_context = self._build_agent_context(step.agent_name, context)

                output = await asyncio.wait_for(
                    agent.execute(agent_context),
                    timeout=step.timeout,
                )

                if output.status.value == "completed":
                    result.steps_completed.append(step.agent_name)
                    result.outputs[step.agent_name] = output
                    result.total_tokens += output.usage.get("total_tokens", 0)
                else:
                    result.steps_failed.append(step.agent_name)
                    raise Exception(f"Agent {step.agent_name} yurutbasarisiz: {output.error}")

            except TimeoutError:
                result.steps_failed.append(step.agent_name)
                raise Exception(f"Agent {step.agent_name} yurutasirizaman")

    async def execute_single_agent(
        self,
        agent_name: str,
        context: dict[str, Any],
        session_id: str = "",
    ):
        """
        yuruttekil Agent

        Args:
            agent_name: Agent ad
            context: yurutbaglam
            session_id: Trace session ID (tarafindancagriyoniletgiris) 

        Returns:
            AgentOutput: yurutme sonucu
        """
        TraceContext = _get_trace_context_cls()
        trace_ctx = None
        if TraceContext is not None:
            trace_ctx = TraceContext(
                agent_name=agent_name,
                session_id=session_id or "default",
                workflow_id="",
            )
            trace_ctx.start()

        try:
            agent = self.get_agent(agent_name)
            agent_context = self._build_agent_context(agent_name, context)
            output = await agent.execute(agent_context)
            if trace_ctx is not None:
                summary = ""
                if hasattr(output, "output"):
                    summary = str(output.output)[:200]
                trace_ctx.stop(
                    status="completed",
                    output_summary=summary,
                )
            return output
        except Exception as e:
            if trace_ctx is not None:
                error_name = type(e).__name__
                trace_ctx.log_error(error_name)
                trace_ctx.stop(status="failed", error=error_name)
            raise

    def _save_workflow_result(self, result: WorkflowResult):
        """kaydetis akisisonuc"""
        result_file = self.state_dir / f"workflow_{result.workflow_id}.json"

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "steps_completed": result.steps_completed,
                    "steps_failed": result.steps_failed,
                    "total_tokens": result.total_tokens,
                    "total_cost": result.total_cost,
                    "execution_time": result.execution_time,
                    "error": result.error,
                    "timestamp": result.timestamp,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load_workflow_result(self, workflow_id: str) -> Optional[WorkflowResult]:
        """yukleis akisisonuc"""
        result_file = self.state_dir / f"workflow_{workflow_id}.json"

        if not result_file.exists():
            return None

        with open(result_file, encoding="utf-8") as f:
            data = json.load(f)

        return WorkflowResult(
            workflow_id=data["workflow_id"],
            status=WorkflowStatus(data["status"]),
            steps_completed=data["steps_completed"],
            steps_failed=data["steps_failed"],
            outputs={},
            total_tokens=data["total_tokens"],
            total_cost=data["total_cost"],
            execution_time=data["execution_time"],
            error=data.get("error"),
            timestamp=data["timestamp"],
        )

    def list_active_workflows(self) -> list[str]:
        """listeleaktifis akisi"""
        return list(self._active_workflows.keys())

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """alis akisidurum"""
        return self._active_workflows.get(workflow_id)

    def get_current_state(self) -> dict[str, Any]:
        """almevcutvar Agent isbirligiyapdurum"""
        active_agents = []
        completed_agents = []
        pending_agents = []

        # dolasvaraktifis akisi
        for workflow_id, workflow_result in self._active_workflows.items():
            if workflow_result.status == WorkflowStatus.RUNNING:
                # aktif: agent_names icindehenuzhenuz completed 
                completed_set = set(workflow_result.steps_completed)
                for agent_name in workflow_result.agent_names:
                    if agent_name not in completed_set:
                        active_agents.append(
                            {
                                "name": agent_name,
                                "status": "working",
                                "task": f"yurutis akisi: {workflow_id}",
                                "started_at": workflow_result.timestamp,
                            }
                        )
                # tamamla
                for agent_name in workflow_result.steps_completed:
                    completed_agents.append(
                        {
                            "name": agent_name,
                            "status": "done",
                            "task": f"tamamlais akisi: {workflow_id}",
                            "duration": (
                                f"{workflow_result.execution_time:.0f}s"
                                if workflow_result.execution_time > 0
                                else "N/A"
                            ),
                        }
                    )

            elif workflow_result.status == WorkflowStatus.COMPLETED:
                # tummiktarisareticintamamla
                for agent_name in workflow_result.steps_completed:
                    completed_agents.append(
                        {
                            "name": agent_name,
                            "status": "done",
                            "task": f"tamamlais akisi: {workflow_id}",
                            "duration": (
                                f"{workflow_result.execution_time:.0f}s"
                                if workflow_result.execution_time > 0
                                else "N/A"
                            ),
                        }
                    )
            elif workflow_result.status == WorkflowStatus.FAILED:
                # basarisiz
                for agent_name in workflow_result.steps_failed:
                    pending_agents.append(agent_name)

        # bekleyurut = agent_names icindehayiricinde active/completed/failed 
        all_workflow_names: set = set()
        for wf in self._active_workflows.values():
            all_workflow_names.update(wf.agent_names)

        active_names = {a["name"] for a in active_agents}
        completed_names = {a["name"] for a in completed_agents}
        failed_names = set(pending_agents)

        for name in all_workflow_names:
            if (
                name not in active_names
                and name not in completed_names
                and name not in failed_names
            ):
                pending_agents.append(name)

        # yinelenenleri kaldir
        completed_names_unique = {}
        for c in completed_agents:
            completed_names_unique[c["name"]] = c
        completed_agents = list(completed_names_unique.values())

        active_names_unique = {}
        for a in active_agents:
            active_names_unique[a["name"]] = a
        active_agents = list(active_names_unique.values())

        total = len(all_workflow_names) if all_workflow_names else 0
        done_count = len(completed_agents)
        total_progress = f"{done_count}/{total}" if total > 0 else "0/0"

        current_workflow = ""
        if self._active_workflows:
            wf = list(self._active_workflows.values())[0]
            current_workflow = wf.agent_names[0] if wf.agent_names else "unknown"

        return {
            "active_agents": active_agents,
            "completed_agents": completed_agents,
            "pending_agents": pending_agents,
            "total_progress": total_progress,
            "workflow": current_workflow,
            "timestamp": datetime.now().isoformat(),
        }
