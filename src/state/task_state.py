from __future__ import annotations

"""
gorevdurumyonetmodul

Islev:
- otomatikkayitgorevyurutadim
- destekduraklat/kurtar
- durumkalicikadar ~/.omc/tasks/
- omc task list goruntulevargorev
"""


import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────
# durumenum
# ─────────────────────────────────────────────────────────────


class TaskStatus(Enum):
    """gorevdurum"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# ─────────────────────────────────────────────────────────────
# sayigoremodel
# ─────────────────────────────────────────────────────────────


@dataclass
class StepRecord:
    """adimkayit"""

    step: str
    result: Optional[str] = None
    timestamp: str = ""
    duration: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "result": self.result,
            "timestamp": self.timestamp,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepRecord:
        return cls(
            step=data.get("step", ""),
            result=data.get("result"),
            timestamp=data.get("timestamp", ""),
            duration=data.get("duration"),
        )


@dataclass
class TaskState:
    """gorevdurum"""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    updated_at: str = ""
    progress: float = 0.0
    current_step: str = ""
    steps: list[StepRecord] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def add_step(self, step: str, result: Any = None) -> None:
        """kayityurutadim"""
        record = StepRecord(step=step, result=str(result) if result else None)
        self.steps.append(record)
        self.current_step = step
        self.updated_at = datetime.now().isoformat()

    def pause(self) -> None:
        """duraklatgorev (kaydetkesnokta) """
        self.status = TaskStatus.PAUSED
        self.updated_at = datetime.now().isoformat()

    def resume(self) -> None:
        """kurtargorev"""
        self.status = TaskStatus.RUNNING
        self.updated_at = datetime.now().isoformat()

    def complete(self, result: Any = None) -> None:
        """isaretgorevtamamla"""
        self.status = TaskStatus.COMPLETED
        self.progress = 1.0
        if result:
            self.artifacts["result"] = str(result)
        self.updated_at = datetime.now().isoformat()

    def fail(self, error: str) -> None:
        """isaretgorevbasarisiz"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.updated_at = datetime.now().isoformat()

    def set_progress(self, progress: float) -> None:
        """ayarlaayarilerlederece"""
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "current_step": self.current_step,
            "steps": [s.to_dict() for s in self.steps],
            "artifacts": self.artifacts,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskState:
        status_val = data.get("status", "pending")
        try:
            status = TaskStatus(status_val)
        except ValueError:
            status = TaskStatus.PENDING

        steps = [StepRecord.from_dict(s) for s in data.get("steps", [])]
        return cls(
            task_id=data["task_id"],
            status=status,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            progress=data.get("progress", 0.0),
            current_step=data.get("current_step", ""),
            steps=steps,
            artifacts=data.get("artifacts", {}),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


# ─────────────────────────────────────────────────────────────
# durumdepolama
# ─────────────────────────────────────────────────────────────


class TaskStore:
    """gorevdurumkalicidepolama"""

    _instance: Optional[TaskStore] = None

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".omc" / "tasks"
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> TaskStore:
        """tekilornekmod"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _task_path(self, task_id: str) -> Path:
        """algorevdosyayol"""
        return self.base_dir / f"{task_id}.json"

    def save(self, state: TaskState) -> None:
        """kaydetgorevdurum"""
        path = self._task_path(state.task_id)
        data = state.to_dict()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.rename(path)

    def load(self, task_id: str) -> Optional[TaskState]:
        """yuklegorevdurum"""
        path = self._task_path(task_id)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return TaskState.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def delete(self, task_id: str) -> bool:
        """silgorev"""
        path = self._task_path(task_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> list[TaskState]:
        """tumunu listelevargorev"""
        states: list[TaskState] = []
        for path in self.base_dir.glob("*.json"):
            state = self.load(path.stem)
            if state is not None:
                states.append(state)

        # goreolusturzamanarasindaters sira
        states.sort(key=lambda s: s.created_at, reverse=True)
        return states

    def list_by_status(self, status: TaskStatus) -> list[TaskState]:
        """goredurumfiltresecgorev"""
        return [s for s in self.list_all() if s.status == status]


# ─────────────────────────────────────────────────────────────
# kullanislifonksiyon
# ─────────────────────────────────────────────────────────────


def create_task(task_id: str, metadata: Optional[dict[str, Any]] = None) -> TaskState:
    """olusturyenigorev"""
    state = TaskState(
        task_id=task_id,
        status=TaskStatus.PENDING,
        metadata=metadata or {},
    )
    TaskStore.get_instance().save(state)
    return state


def get_task(task_id: str) -> Optional[TaskState]:
    """algorevdurum"""
    return TaskStore.get_instance().load(task_id)


def list_tasks(status: Optional[TaskStatus] = None) -> list[TaskState]:
    """listelegorev"""
    store = TaskStore.get_instance()
    if status is None:
        return store.list_all()
    return store.list_by_status(status)


def pause_task(task_id: str) -> bool:
    """duraklatgorev"""
    state = TaskStore.get_instance().load(task_id)
    if state is None:
        return False
    state.pause()
    TaskStore.get_instance().save(state)
    return True


def resume_task(task_id: str) -> bool:
    """kurtargorev"""
    state = TaskStore.get_instance().load(task_id)
    if state is None:
        return False
    state.resume()
    TaskStore.get_instance().save(state)
    return True


def delete_task(task_id: str) -> bool:
    """silgorev"""
    return TaskStore.get_instance().delete(task_id)
