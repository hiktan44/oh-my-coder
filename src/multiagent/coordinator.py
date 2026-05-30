from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
cok Agent isbirligiyapayarderece

Islev:
- olusturveayarderecealt Agent
- vesatirgorevpuangonder
- otomatiktoplatoplamsonuc
- omc multiagent status goruntuleisbirligiyapdurum
"""


import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────
# sayigoremodel
# ─────────────────────────────────────────────────────────────


class AgentRole(Enum):
    """Agent rol"""

    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    PLANNER = "planner"
    EXPLORER = "explorer"
    EXECUTOR = "executor"
    CUSTOM = "custom"


class SubAgentStatus(Enum):
    """alt Agent durum"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubAgent:
    """alt Agent"""

    agent_id: str
    name: str
    role: str
    status: SubAgentStatus = SubAgentStatus.IDLE
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class TaskResult:
    """gorevyurutme sonucu"""

    agent_id: str
    role: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: Optional[float] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "success": self.success,
            "output": str(self.output) if self.output is not None else None,
            "error": self.error,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }


@dataclass
class CoordinationResult:
    """isbirligiyapgorevsonuc"""

    task_id: str
    results: list[TaskResult]
    summary: str
    started_at: str
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ─────────────────────────────────────────────────────────────
# ayarderece
# ─────────────────────────────────────────────────────────────


AgentRunner = Callable[[SubAgent, str], Any]


class MultiAgentCoordinator:
    """cok Agent isbirligiyapayarderece"""

    def __init__(self) -> None:
        self.agents: dict[str, SubAgent] = {}
        self.tasks: dict[str, list[str]] = {}  # task_id -> agent_ids
        self._runner: Optional[AgentRunner] = None
        self._history: list[CoordinationResult] = []

    def set_runner(self, runner: AgentRunner) -> None:
        """
        ayarlaayar Agent yurut

        Args:
            runner: asenkronfonksiyon (agent: SubAgent, task: str) -> Any
        """
        self._runner = runner

    def spawn(
        self,
        role: str,
        name: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SubAgent:
        """
        olusturalt Agent

        Args:
            role: rol (coder/reviewer/tester/...) 
            name: Agent ad
            metadata: ogresayigore

        Returns:
            SubAgent ornek
        """
        agent = SubAgent(
            agent_id=str(uuid.uuid4())[:8],
            name=name,
            role=role,
            status=SubAgentStatus.IDLE,
            metadata=metadata or {},
        )
        self.agents[agent.agent_id] = agent
        return agent

    async def dispatch(
        self,
        task: str,
        agents: list[SubAgent],
        task_id: Optional[str] = None,
    ) -> CoordinationResult:
        """
        puangondergorevvercok Agent (vesatiryurut) 

        Args:
            task: gorev aciklamasi
            agents: hedefisaret Agent liste
            task_id: gorev ID (olabilirsec, otomatikolustur) 

        Returns:
            isbirligiyapsonuc
        """
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        started_at = datetime.now().isoformat()
        self.tasks[task_id] = [a.agent_id for a in agents]

        # vesatiryurut
        results: list[TaskResult] = []
        coroutines = [self._run_agent(agent, task) for agent in agents]
        task_results = await asyncio.gather(*coroutines, return_exceptions=True)

        for agent, result in zip(agents, task_results):
            if isinstance(result, Exception):
                results.append(
                    TaskResult(
                        agent_id=agent.agent_id,
                        role=agent.role,
                        success=False,
                        output=None,
                        error=str(result),
                    )
                )
            else:
                results.append(result)

        coordination = CoordinationResult(
            task_id=task_id,
            results=results,
            summary=self._summarize(results),
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
        )
        self._history.append(coordination)
        return coordination

    async def dispatch_sequential(
        self,
        task: str,
        agents: list[SubAgent],
        task_id: Optional[str] = None,
    ) -> CoordinationResult:
        """
        puangondergorevvercok Agent (sirayurut) 

        Args:
            task: gorev aciklamasi
            agents: hedefisaret Agent liste
            task_id: gorev ID (olabilirsec, otomatikolustur) 

        Returns:
            isbirligiyapsonuc
        """
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        started_at = datetime.now().isoformat()
        self.tasks[task_id] = [a.agent_id for a in agents]

        results: list[TaskResult] = []
        context = task

        for agent in agents:
            result = await self._run_agent(agent, context)
            results.append(result)
            if not result.success:
                break
            # oncebir Agent ciktiyapicinaltbir Agent girdi
            if result.output:
                context = f"{context}\n\nustbirAgentcikti:\n{result.output}"

        coordination = CoordinationResult(
            task_id=task_id,
            results=results,
            summary=self._summarize(results),
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
        )
        self._history.append(coordination)
        return coordination

    async def _run_agent(self, agent: SubAgent, task: str) -> TaskResult:
        """satirtekil Agent"""
        import time

        agent.status = SubAgentStatus.RUNNING
        start = time.time()

        try:
            if self._runner is not None:
                output = await self._runner(agent, task)
            else:
                output = f"[simule] {agent.name} yurutgorev: {task[:50]}..."

            agent.status = SubAgentStatus.COMPLETED
            return TaskResult(
                agent_id=agent.agent_id,
                role=agent.role,
                success=True,
                output=output,
                duration=time.time() - start,
            )
        except Exception as e:
            agent.status = SubAgentStatus.FAILED
            return TaskResult(
                agent_id=agent.agent_id,
                role=agent.role,
                success=False,
                output=None,
                error=type(e).__name__,
                duration=time.time() - start,
            )

    def get_status(self) -> dict[str, Any]:
        """tumunu al Agent durum"""
        return {
            "agents": [a.to_dict() for a in self.agents.values()],
            "active_tasks": len(self.tasks),
            "total_agents": len(self.agents),
            "running": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.RUNNING
            ),
            "completed": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.COMPLETED
            ),
            "failed": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.FAILED
            ),
            "idle": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.IDLE
            ),
        }

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """albelirt Agent"""
        return self.agents.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        """kaldir Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def clear_agents(self) -> None:
        """temizlebosvar Agent"""
        self.agents.clear()
        self.tasks.clear()

    def _summarize(self, results: list[TaskResult]) -> str:
        """toplatoplamsonuc"""
        total = len(results)
        success = sum(1 for r in results if r.success)
        failed = total - success

        role_summary = {}
        for r in results:
            role_summary.setdefault(r.role, {"success": 0, "failed": 0})
            if r.success:
                role_summary[r.role]["success"] += 1
            else:
                role_summary[r.role]["failed"] += 1

        lines = [f"toplamgorev: {total}, basarili: {success}, basarisiz: {failed}"]
        for role, counts in role_summary.items():
            lines.append(f"  {role}: basarili {counts['success']}, basarisiz {counts['failed']}")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# globaltekilornek
# ─────────────────────────────────────────────────────────────


_coordinator: Optional[MultiAgentCoordinator] = None


def get_coordinator() -> MultiAgentCoordinator:
    """alglobalisbirligiayarornek"""
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator
