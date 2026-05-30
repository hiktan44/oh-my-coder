from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
gorevdurumesitlemodul

uygulacokkisiortakpaylasgorevdurum, destekzamanguncelleveabone. 
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, cast

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class TaskStatus(str, Enum):
    """gorevdurum"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MemberRole(str, Enum):
    """oluyerol"""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


@dataclass
class TeamTask:
    """takimgorev"""

    task_id: str
    team_id: str
    creator_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assignee_id: Optional[str] = None
    workflow: str = "build"
    model: str = "deepseek"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0
    subscribers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """donusturicinsozluk"""
        return {
            "task_id": self.task_id,
            "team_id": self.team_id,
            "creator_id": self.creator_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "assignee_id": self.assignee_id,
            "workflow": self.workflow,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "result": self.result,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "subscribers": self.subscribers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamTask:
        """sozlukolustur"""
        return cls(
            task_id=data["task_id"],
            team_id=data["team_id"],
            creator_id=data["creator_id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus(data["status"]),
            assignee_id=data.get("assignee_id"),
            workflow=data.get("workflow", "build"),
            model=data.get("model", "deepseek"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            result=data.get("result"),
            error=data.get("error"),
            tokens_used=data.get("tokens_used", 0),
            cost=data.get("cost", 0.0),
            subscribers=data.get("subscribers", []),
        )


class TaskSync:
    """
    gorevdurumesitle

    destek: 
    - olustur/guncelle/silgorev
    - abonegorevguncelle
    - altakimgorevliste
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        baslat

        Args:
            redis_url: Redis baglabaglanadres
        """
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscribers: dict[str, list[Callable]] = {}
        self._tasks_cache: dict[str, TeamTask] = {}
        self._use_memory = not REDIS_AVAILABLE

    async def connect(self) -> None:
        """baglabaglan Redis"""
        if self._use_memory:
            return

        try:
            self._redis = await redis.from_url(self.redis_url)
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe("task_updates")
        except Exception as e:
            print(f"⚠️ Redis baglabaglanbasarisiz, kullanicindekaydetmod: {e}")
            self._use_memory = True

    async def disconnect(self) -> None:
        """kesacbaglabaglan"""
        if self._redis:
            await self._redis.close()

    def _get_task_key(self, task_id: str) -> str:
        """algorev Redis anahtar"""
        return f"task:{task_id}"

    def _get_team_tasks_key(self, team_id: str) -> str:
        """altakimgorevliste Redis anahtar"""
        return f"team:{team_id}:tasks"

    async def create_task(
        self,
        task_id: str,
        team_id: str,
        creator_id: str,
        title: str,
        description: str = "",
        workflow: str = "build",
        model: str = "deepseek",
    ) -> TeamTask:
        """
        olusturgorev

        Args:
            task_id: gorev ID
            team_id: takim ID
            creator_id: olustur ID
            title: gorev basligi
            description: gorev aciklamasi
            workflow: is akisitip
            model: kullanmodel

        Returns:
            TeamTask: olusturgorev
        """
        now = datetime.now()
        task = TeamTask(
            task_id=task_id,
            team_id=team_id,
            creator_id=creator_id,
            title=title,
            description=description,
            workflow=workflow,
            model=model,
            created_at=now,
            updated_at=now,
            subscribers=[creator_id],
        )

        if self._use_memory:
            self._tasks_cache[task_id] = task
        else:
            # depolamagorev
            assert self._redis is not None, "Redis client not initialized"
            # redis-py returns Union[Awaitable[int], int]; cast to satisfy mypy
            _hset_result: int = await cast(Any, self._redis).hset(
                self._get_task_key(task_id),
                mapping={"data": json.dumps(task.to_dict())},
            )
            # eklekadartakimgorevliste
            _sadd_result: int = await cast(Any, self._redis).sadd(
                self._get_team_tasks_key(team_id), task_id
            )

        # gonderolusturolay
        await self._publish_event("task_created", task.to_dict())

        return task

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> Optional[TeamTask]:
        """
        guncellegorevdurum

        Args:
            task_id: gorev ID
            status: yenidurum
            result: yurutme sonucu
            error: hata mesaji
            tokens_used: tuket Token sayi
            cost: ol

        Returns:
            TeamTask: guncellesonragorev
        """
        task = await self.get_task(task_id)
        if not task:
            return None

        task.status = status
        task.updated_at = datetime.now()
        task.result = result
        task.error = error
        task.tokens_used = tokens_used
        task.cost = cost

        if status == TaskStatus.RUNNING:
            task.started_at = datetime.now()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = datetime.now()

        if self._use_memory:
            self._tasks_cache[task_id] = task
        else:
            assert self._redis is not None, "Redis client not initialized"
            _hset_result: int = await cast(Any, self._redis).hset(
                self._get_task_key(task_id),
                mapping={"data": json.dumps(task.to_dict())},
            )

        # gonderguncelleolay
        await self._publish_event("task_updated", task.to_dict())

        return task

    async def get_task(self, task_id: str) -> Optional[TeamTask]:
        """
        algorev

        Args:
            task_id: gorev ID

        Returns:
            TeamTask: gorevicinnesne
        """
        if self._use_memory:
            return self._tasks_cache.get(task_id)

        assert self._redis is not None, "Redis client not initialized"
        _hget_result: Any = await cast(Any, self._redis).hget(
            self._get_task_key(task_id), "data"
        )
        if _hget_result:
            return TeamTask.from_dict(json.loads(_hget_result))
        return None

    async def get_team_tasks(self, team_id: str) -> list[TeamTask]:
        """
        altakimvargorev

        Args:
            team_id: takim ID

        Returns:
            List[TeamTask]: gorevliste
        """
        if self._use_memory:
            return [t for t in self._tasks_cache.values() if t.team_id == team_id]

        assert self._redis is not None, "Redis client not initialized"
        _smembers_result: Any = await cast(Any, self._redis).smembers(
            self._get_team_tasks_key(team_id)
        )
        # _smembers_result is a set of bytes (from Redis)
        task_ids: set[Any] = set(_smembers_result)
        tasks = []
        for tid in task_ids:
            task = await self.get_task(
                tid.decode() if isinstance(tid, bytes) else str(tid)
            )
            if task:
                tasks.append(task)
        return tasks

    async def subscribe_task(self, task_id: str, user_id: str) -> bool:
        """
        abonegorevguncelle

        Args:
            task_id: gorev ID
            user_id: kullanici ID

        Returns:
            bool: basarili mi
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        if user_id not in task.subscribers:
            task.subscribers.append(user_id)
            if self._use_memory:
                self._tasks_cache[task_id] = task
            else:
                assert self._redis is not None, "Redis client not initialized"
                _hset_result: int = await cast(Any, self._redis).hset(
                    self._get_task_key(task_id),
                    mapping={"data": json.dumps(task.to_dict())},
                )

        return True

    async def unsubscribe_task(self, task_id: str, user_id: str) -> bool:
        """
        iptalabonegorev

        Args:
            task_id: gorev ID
            user_id: kullanici ID

        Returns:
            bool: basarili mi
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        if user_id in task.subscribers:
            task.subscribers.remove(user_id)
            if self._use_memory:
                self._tasks_cache[task_id] = task
            else:
                assert self._redis is not None, "Redis client not initialized"
                _hset_result: int = await cast(Any, self._redis).hset(
                    self._get_task_key(task_id),
                    mapping={"data": json.dumps(task.to_dict())},
                )

        return True

    async def delete_task(self, task_id: str) -> bool:
        """
        silgorev

        Args:
            task_id: gorev ID

        Returns:
            bool: basarili mi
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        if self._use_memory:
            del self._tasks_cache[task_id]
        else:
            assert self._redis is not None, "Redis client not initialized"
            _delete_result: int = await cast(Any, self._redis).delete(
                self._get_task_key(task_id)
            )
            _srem_result: int = await cast(Any, self._redis).srem(
                self._get_team_tasks_key(task.team_id), task_id
            )

        await self._publish_event("task_deleted", {"task_id": task_id})

        return True

    async def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """gonderolay"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        if not self._use_memory and self._redis:
            assert self._redis is not None
            await self._redis.publish("task_updates", json.dumps(event))

    async def listen_updates(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        dinlegorevguncelle

        Args:
            callback: geri aramafonksiyon
        """
        if self._use_memory or not self._pubsub:
            return

        async for message in self._pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    await callback(event)
                except Exception as e:
                    print(f"islemesajbasarisiz: {e}")
        return None


# globalornek
task_sync = TaskSync()
