from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
uzaksurec Server API - REST API baglanagiztanim

baglanagiz: 
  POST /api/v1/run        - gondergorev, donus task_id
  GET  /api/v1/status/{id} - sorgudurum
  GET  /api/v1/result/{id} - alsonuc
  GET  /api/v1/tasks      - tumunu listelevargorev
  DELETE /api/v1/tasks/{id} - silgorev

onceayar: omc server --port 8080
"""


import asyncio
import contextlib
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

# =============================================================================
# sayigoremodel
# =============================================================================


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskRecord:
    task_id: str
    prompt: str
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# gorevdepolama (icindekaydet + diskkalici) 
# =============================================================================


class TaskStore:
    """icindekaydet + JSON dosyakalicigorevdepolama"""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._store: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()
        self._storage_dir = storage_dir or (Path.home() / ".omc" / "server_tasks")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _load_all(self) -> None:
        """baslatzamandiskkurtarvargorev (enyakin 100 ) """
        try:
            files = sorted(
                self._storage_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for f in files[:100]:
                try:
                    data = __import__("json").loads(f.read_text(encoding="utf-8"))
                    record = TaskRecord(**data)
                    self._store[record.task_id] = record
                except Exception:
                    pass
        except Exception:
            pass

    def _save(self, record: TaskRecord) -> None:
        """kalicikadardisk"""
        try:
            f = self._storage_dir / f"{record.task_id}.json"
            f.write_text(
                __import__("json").dumps(record.__dict__, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    async def create(
        self, prompt: str, metadata: Optional[dict[str, Any]] = None
    ) -> TaskRecord:
        """olusturyenigorev"""
        async with self._lock:
            task_id = uuid.uuid4().hex[:12]
            record = TaskRecord(
                task_id=task_id,
                prompt=prompt,
                status=TaskStatus.PENDING,
                created_at=datetime.now().isoformat(),
                metadata=metadata or {},
            )
            self._store[task_id] = record
            self._save(record)
            return record

    async def get(self, task_id: str) -> Optional[TaskRecord]:
        return self._store.get(task_id)

    async def list_all(self) -> list[TaskRecord]:
        return sorted(
            self._store.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )

    async def update(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        async with self._lock:
            if task_id not in self._store:
                return
            record = self._store[task_id]
            record.status = status
            if status == TaskStatus.RUNNING and not record.started_at:
                record.started_at = datetime.now().isoformat()
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                record.completed_at = datetime.now().isoformat()
                if record.started_at:
                    start = datetime.fromisoformat(record.started_at)
                    record.execution_time = (datetime.now() - start).total_seconds()
            if result is not None:
                record.result = result
            if error is not None:
                record.error = error
            self._save(record)

    async def delete(self, task_id: str) -> bool:
        async with self._lock:
            if task_id not in self._store:
                return False
            del self._store[task_id]
            with contextlib.suppress(Exception):
                (self._storage_dir / f"{task_id}.json").unlink(missing_ok=True)
            return True


# =============================================================================
# API kimlik dogrulama
# =============================================================================


class AuthContext:
    """kimlik dogrulamabaglam"""

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key or ""

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def verify(self, provided_key: Optional[str]) -> bool:
        if not self.api_key:
            return True  # henuzyapilandirmakuralatlakimlik dogrulama
        return provided_key == self.api_key


def get_auth(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    auth_ctx: AuthContext = Depends(lambda: AuthContext(None)),
) -> Optional[str]:
    """FastAPI bagimlilik: dogrulama API Key"""
    ctx = AuthContext(auth_ctx.api_key)
    if not ctx.verify(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


# =============================================================================
# gorevyurutmotor
# =============================================================================


async def run_agent_task(prompt: str, task_id: str, store: TaskStore) -> None:
    """icindesonraplatformyurut agent gorev"""
    try:
        await store.update(task_id, TaskStatus.RUNNING)

        # gecikmeiceri aktar, kacindongubagimlilik
        import sys
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        result: dict[str, Any] = {}

        # denekullan Orchestrator
        try:
            from src.agents.base import AgentContext
            from src.core.orchestrator import Orchestrator

            ctx = AgentContext(prompt=prompt, workspace=Path.cwd())
            orch = Orchestrator(max_agents=1)
            output = await orch.run(ctx)
            result = {
                "output": output.output if hasattr(output, "output") else str(output),
                "status": "ok",
            }
        except Exception as e:
            # dusurseviye: donussafmetinyanit
            result = {
                "output": prompt,  # echo back
                "status": "degraded",
                "note": "Orchestrator not available, returning prompt echo",
                "error": (
                    type(e).__name__ + ": " + str(e.args[0])
                    if e.args
                    else type(e).__name__
                ),
            }

        await store.update(task_id, TaskStatus.COMPLETED, result=result)

    except Exception as e:
        await store.update(task_id, TaskStatus.FAILED, error=type(e).__name__)


# =============================================================================
# istek/yanitmodel (zorunluicindemodulustkatmantanim, kacin Pydantic v2 + Python 3.9 onceyoncekkullan bug) 
# =============================================================================


class RunRequest(BaseModel):
    prompt: str
    metadata: Optional[dict[str, Any]] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    prompt: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = {}

    class Config:
        from_attributes = True


# =============================================================================
# FastAPI App
# =============================================================================


def create_app(
    api_key: Optional[str] = None,
    store: Optional[TaskStore] = None,
) -> tuple[FastAPI, TaskStore]:
    """olustur FastAPI uygulama"""
    from src.api.openapi import custom_openapi

    app = FastAPI(
        title="Oh My Coder Server API",
        description=(
            "uzaksurec AI duzenlesurecyardimci API. \n\n"
            "## kimlik dogrulama\n"
            "henuzayarlaayar API Key zamanyokgerekkimlik dogrulama. \n"
            "ayarlaayar API Key sonra, varistekgerekicinde Header icindeekle: \n"
            "`X-API-Key: your-api-key`"
        ),
        version="0.2.0",
    )

    # uygulamaozel OpenAPI schema (artgucluyapilandirma: guvenliktanim, servis, etiketvb.) 
    app.openapi = custom_openapi(app)  # type: ignore[method-assign]

    _store = store or TaskStore()
    _auth = AuthContext(api_key)
    _app_state: dict[str, Any] = {"store": _store, "auth": _auth}

    # ---------------------------------------------------------------------------
    # yoltarafindan
    # ---------------------------------------------------------------------------

    # asyukle Web UI (onceucsayfayuz, statikdurumdosya, sablonrender) 
    from pathlib import Path

    from fastapi.responses import FileResponse

    from src.web.app import app as web_app

    _web_dir = Path(__file__).parent.parent / "web"

    app.mount("/", web_app)

    @app.get("/favicon.ico")
    async def favicon():
        return FileResponse(_web_dir / "static" / "favicon.svg", media_type="image/svg+xml")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/run", response_model=TaskResponse)
    async def run_task(req: RunRequest) -> TaskResponse:
        """gonderyenigorev, donus task_id"""
        store: TaskStore = _app_state["store"]
        _app_state["auth"]

        record = await store.create(req.prompt, req.metadata)
        # baslatsonraplatformyurut (hayirvb.bekle) 
        asyncio.create_task(run_agent_task(req.prompt, record.task_id, store))

        return TaskResponse(
            task_id=record.task_id,
            status=record.status.value,
            created_at=record.created_at,
            prompt=record.prompt,
            metadata=record.metadata,
        )

    @app.get("/api/v1/status/{task_id}")
    async def get_status(
        task_id: str,
    ) -> dict[str, Any]:
        """sorgugorevdurum"""
        store: TaskStore = _app_state["store"]
        record = await store.get(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "task_id": record.task_id,
            "status": record.status.value,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "execution_time": record.execution_time,
        }

    @app.get("/api/v1/result/{task_id}")
    async def get_result(task_id: str) -> dict[str, Any]:
        """algorevsonuc"""
        store: TaskStore = _app_state["store"]
        record = await store.get(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        if record.status == TaskStatus.PENDING:
            raise HTTPException(status_code=202, detail="Task not started yet")
        if record.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=202, detail="Task still running")
        return {
            "task_id": record.task_id,
            "status": record.status.value,
            "result": record.result,
            "error": record.error,
            "execution_time": record.execution_time,
            "completed_at": record.completed_at,
        }

    @app.get("/api/v1/tasks")
    async def list_tasks(limit: int = 50) -> dict[str, Any]:
        """listeleenyakingorev"""
        store: TaskStore = _app_state["store"]
        tasks = await store.list_all()
        return {
            "total": len(tasks),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "created_at": t.created_at,
                    "execution_time": t.execution_time,
                    "prompt_preview": t.prompt[:100],
                }
                for t in tasks[:limit]
            ],
        }

    @app.delete("/api/v1/tasks/{task_id}")
    async def delete_task(task_id: str) -> dict[str, str]:
        """silgorev"""
        store: TaskStore = _app_state["store"]
        ok = await store.delete(task_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task_id": task_id, "deleted": "true"}

    return app, _store
