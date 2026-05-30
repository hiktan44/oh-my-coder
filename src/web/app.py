from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Web arayüzü giriş noktası - FastAPI uygulaması
AI programlama görevlerini yürütmek için görsel arayüz sağlar
"""

import asyncio
import json as _json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# src modülünün içe aktarılabildiğinden emin ol
project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(project_root))

# İçe aktarma işlemi sys.path.insert sonrasında yapılmalı
try:
    from src.agents.base import AgentContext, AgentOutput, AgentStatus, get_agent
    from src.config.workflow_loader import WorkflowLoader
    from src.core.orchestrator import WORKFLOW_TEMPLATES, Orchestrator
    from src.core.router import ModelRouter, RouterConfig
    from src.web.coverage_api import format_coverage_report, run_coverage_analysis
    from src.web.dashboard_api import router as dashboard_router
    from src.web.history_api import (
        agent_router,
        history_router,
        history_store,
        verify_api_token,
    )
    from src.web.local_models_api import router as local_models_router
    from src.web.share_api import router as share_router
    from src.web.team_api import router as team_router
except ImportError as e:
    print(f"İçe aktarma hatası: {e}")
    raise

# ========================================
# URL / hedef ön işleme
# ========================================


def _detect_target_type(target: str) -> str:
    """Girdi türünü otomatik tespit et: github / url / local"""
    target = target.strip()
    if not target:
        return "local"
    # GitHub URL
    if re.match(r"https?://(www\.)?github\.com/[^/]+/[^/]+", target):
        return "github"
    # Git URL (git@...)
    if target.startswith("git@"):
        return "github"
    # Diğer HTTP URL
    if target.startswith("http://") or target.startswith("https://"):
        return "url"
    return "local"


def _preprocess_target(target: str, target_type: str, task_id: str) -> tuple:
    """
    Analiz hedefini ön işle, (project_path, extra_context) döndürür.
    - github: geçici dizine klonla, yolu döndür
    - url: web içeriğini çek, ('.', extra_context) döndür
    - local: orijinal yolu doğrudan döndür
    """
    target = target.strip()
    if not target:
        return ".", ""

    if target_type == "github":
        # GitHub URL'yi normalleştir → .git klon URL'si
        clone_url = target
        if not target.endswith(".git"):
            clone_url = target.rstrip("/") + ".git"
        if clone_url.startswith("https://github.com") and ".git" not in target:
            clone_url = target.rstrip("/") + ".git"

        tmp_dir = Path(tempfile.mkdtemp(prefix=f"omc-gh-{task_id[:8]}-"))
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(tmp_dir)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise RuntimeError(f"git clone başarısız: {result.stderr.strip()[:200]}")
            return str(
                tmp_dir
            ), f"\n\n## Kaynak kodu konumu\nGitHub deposu: {target}\nKlonlandığı yer: {tmp_dir}"
        except Exception as e:
            print(f"[ERROR] Git clone failed: {e}")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise

    elif target_type == "url":
        # Web içeriğini çek
        try:
            import requests

            resp = requests.get(
                target,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            # Kodlamayı otomatik algıla
            content = resp.text
            # Basit HTML → metin: etiketleri kaldır
            text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", content, flags=re.I)
            text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            # Token patlamasını önlemek için 8000 karaktere kırp
            if len(text) > 8000:
                text = text[:8000] + "\n\n... (içerik kısaltıldı)"
            return ".", f"\n\n## Web içeriği\nKaynak: {target}\n\n{text}"
        except Exception as e:
            raise RuntimeError(f"Web sayfası alınamadı: {e}")

    else:
        # Yerel yol
        return target, ""


def _cleanup_target(project_path: str, target_type: str):
    """Geçici dizini temizle (GitHub clone)"""
    if target_type == "github" and project_path.startswith(tempfile.gettempdir()):
        shutil.rmtree(project_path, ignore_errors=True)


# ========================================
# FastAPI App
# ========================================
app = FastAPI(
    title="Oh My Coder Web",
    description="Çoklu ajanlı AI programlama asistanı Web arayüzü",
    version="0.1.0",
)

# Statik dosyaları ve şablonları bağla
web_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=web_dir / "static"), name="static")
templates = Jinja2Templates(directory=web_dir / "templates")


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse(web_dir / "static" / "favicon.svg", media_type="image/svg+xml")

# Geliştirme rotalarını kaydet
app.include_router(history_router)
app.include_router(agent_router)
app.include_router(dashboard_router)
app.include_router(team_router)
app.include_router(local_models_router)
app.include_router(share_router)


# ========================================
# SSE Manager (Task → SSE subscribers)
# ========================================
class TaskManager:
    """Çalışan tüm görevleri yönetir"""

    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}
        self._queues: dict[str, asyncio.Queue] = {}

    def create_task(
        self,
        task_desc: str = "",
        model: str = "",
        workflow: str = "",
        project_path: str = "",
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        queue = asyncio.Queue()
        self._tasks[task_id] = {
            "task_id": task_id,
            "task": task_desc,
            "model": model,
            "workflow": workflow,
            "project_path": project_path,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "step_status": {},
            "step_outputs": {},
            "stats": {
                "total_tokens": 0,
                "total_cost": 0.0,
                "execution_time": 0.0,
                "steps_completed": [],
                "steps_failed": [],
                "steps_total": 5,
            },
        }
        self._queues[task_id] = queue
        return task_id

    def get_queue(self, task_id: str) -> Optional[asyncio.Queue]:
        return self._queues.get(task_id)

    def update_step(
        self, task_id: str, step: str, status: str, content: Optional[str] = None
    ):
        if task_id not in self._tasks:
            return
        task = self._tasks[task_id]
        task["step_status"][step] = status
        if content:
            task["step_outputs"][step] = content
        # Push SSE event (use put_nowait to avoid needing running event loop)
        queue = self._queues.get(task_id)
        if queue:
            data = {"type": f"step_{status}", "step": step, "content": content}
            try:
                queue.put_nowait(data)
            except Exception as e:
                print(f"[WARNING] Queue full, skipping step event: {e}")

    def complete_task(
        self, task_id: str, result: Any = None, error: Optional[str] = None
    ):
        if task_id not in self._tasks:
            return
        task = self._tasks[task_id]
        task["status"] = "completed" if not error else "failed"
        task["completed_at"] = datetime.now().isoformat()
        task["result"] = result
        task["error"] = error
        # Push final event (use put_nowait to avoid needing running event loop)
        queue = self._queues.get(task_id)
        if queue:
            data = {
                "type": "complete" if not error else "error",
                "result": result,
                "content": error,
                "stats": task["stats"],
            }
            try:
                queue.put_nowait(data)
                queue.put_nowait(None)  # Sentinel to close SSE
            except Exception as e:
                print(f"[WARNING] Queue full, skipping complete event: {e}")

    def delete_task(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        # Close queue if exists
        queue = self._queues.pop(task_id, None)
        if queue:
            try:
                queue.put_nowait(None)  # Sentinel to close SSE
            except Exception as e:
                print(f"[WARNING] Queue full, skipping delete event: {e}")
        del self._tasks[task_id]
        return True

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        return [
            {
                "task_id": k,
                "status": v["status"],
                "started_at": v["started_at"],
                "completed_at": v["completed_at"],
            }
            for k, v in self._tasks.items()
        ]


task_manager = TaskManager()

# ========================================
# Orchestrator Singleton (shared across SSE + task execution)
# ========================================
_global_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """Global Orchestrator tekil örneğini al (mevcut router'ı yeniden kullanır)"""
    global _global_orchestrator
    if _global_orchestrator is None:
        router = create_router()
        _global_orchestrator = create_orchestrator(router)
    return _global_orchestrator


# ========================================
# Model & Orchestrator Factory
# ========================================
def create_router() -> ModelRouter:
    """Model router oluştur"""
    config = RouterConfig()
    return ModelRouter(config)


def create_orchestrator(router: ModelRouter) -> Orchestrator:
    """Orkestratör oluştur"""
    orch = Orchestrator(model_router=router, state_dir=project_root / ".omc" / "state")

    # Uygulanmış tüm Agent'ları kaydet
    for name in [
        "explore",
        "analyst",
        "architect",
        "executor",
        "verifier",
        "debugger",
        "code-reviewer",
        "test_engineer",
        "security",
        "tracer",
    ]:
        try:
            agent_cls = get_agent(name)
            if agent_cls:
                orch.register_agent(agent_cls(router))
        except Exception as e:
            print(f"[WARNING] Failed to register agent {name}: {e}")

    return orch


# ========================================
# SSE Endpoint
# ========================================
@app.get("/sse/execute/{task_id}")
async def sse_execute(task_id: str):
    """SSE akışı ile yürütme ilerlemesini gönder"""
    queue = task_manager.get_queue(task_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        while True:
            data = await queue.get()
            if data is None:  # Sentinel
                break
            yield f"data: {json_dumps(data)}\n\n"
            await asyncio.sleep(0.01)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/agent/live")
async def agent_live_stream():
    """
    SSE ile mevcut Agent işbirliği durumunu gerçek zamanlı gönder

    Returns:
        StreamingResponse: text/event-stream, her 2 saniyede bir
        orchestrator.get_current_state() gönderir
    """
    orch = get_orchestrator()

    async def event_generator():
        while True:
            try:
                state = orch.get_current_state()
                yield f"data: {json_dumps(state)}\n\n"
                await asyncio.sleep(2)
            except Exception as e:
                print(f"[WARNING] Failed to get orchestrator state: {e}")
                error_state = {
                    "error": "Sunucu durumu alınamadı",
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"data: {json_dumps(error_state)}\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ========================================
# JSON Helper (avoid orjson dependency)
# ========================================


def json_dumps(obj):
    return _json.dumps(obj, ensure_ascii=False, default=str)


# ========================================
# API Routes
# ========================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Ana sayfa - Web arayüzü"""
    return templates.TemplateResponse(request, "index.html")


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Geçmiş kayıt sayfası"""
    return templates.TemplateResponse(request, "history.html")


@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    """Agent durum sayfası"""
    return templates.TemplateResponse(request, "agents.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Proje gösterge paneli sayfası"""
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/api/tasks")
async def list_tasks():
    """Tüm görevleri listele"""
    return JSONResponse({"tasks": task_manager.list_tasks()})


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Görev durumunu al"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(task)


@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: str,
    token: Optional[str] = Depends(verify_api_token),
):
    """Görevi sil (API token doğrulaması gerekir)"""
    if not task_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse({"status": "deleted"})


@app.get("/api/history")
async def api_history():
    """Görev geçmişini al (history.html ile uyumlu)"""
    tasks = task_manager.list_tasks()
    tasks.sort(key=lambda t: t.get("started_at", ""), reverse=True)
    return JSONResponse({"records": tasks})


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Gösterge paneli istatistik verileri — gerçek görev istatistiklerini döndürür"""
    stats = history_store.get_stats()
    return JSONResponse(stats)


@app.get("/api/dashboard/files")
async def dashboard_files():
    """Gösterge paneli proje dosya listesi — en son görevden proje yolunu alır ve dosyaları listeler"""
    # En son görevden proje yolunu al
    records = history_store.list_all(limit=10)
    project_path = "."

    for r in records:
        if r.get("project_path") and Path(r.get("project_path", ".")).exists():
            project_path = r.get("project_path", ".")
            break

    # Geçmiş görev yoksa geçerli çalışma dizinini kullan
    if project_path == "." and project_root.exists():
        project_path = str(project_root)

    # Dosyaları listele
    files = []
    try:
        p = Path(project_path)
        if p.exists() and p.is_dir():
            for f in sorted(p.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[
                :30
            ]:
                if f.is_file() and not f.name.startswith("."):
                    size = f.stat().st_size
                    size_str = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
                    files.append({"name": f.name, "size": size_str, "path": str(f)})
    except Exception as e:
        print(f"[WARNING] Failed to list project files: {e}")

    return JSONResponse({"files": files, "project_path": project_path})


@app.post("/api/open-folder")
async def open_folder(payload: Optional[dict] = None):
    """Belirtilen yoldaki klasörü aç (dosya yöneticisinde göster)"""
    if not payload or not payload.get("path"):
        raise HTTPException(status_code=400, detail="path required")

    path = payload["path"]
    import platform
    import subprocess

    try:
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", path], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", path], check=True)
        return JSONResponse({"status": "ok", "message": f"Açıldı: {path}"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/save-report")
async def save_report(payload: Optional[dict] = None):
    """Görev raporunu dosyaya kaydet"""
    if not payload or not payload.get("task_id"):
        raise HTTPException(status_code=400, detail="task_id required")

    task_id = payload["task_id"]
    # Önce bellekten ara (geçerli oturum görevi)
    task = task_manager.get_task(task_id)
    # Bellekte yoksa, geçmiş kayıtlardan ara (kalıcı görev)
    if not task:
        task = history_store.load(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Varsayılan olarak masaüstüne kaydet
    desktop = Path.home() / "Desktop" / "omc-reports"
    desktop.mkdir(parents=True, exist_ok=True)

    # Dosya adı oluştur
    ts = task.get("started_at", "").replace(":", "-").replace(" ", "_")[:19]
    task_desc = task.get("task", "task")[:30].replace("/", "_").replace("\\", "_")
    filename = f"{ts}_{task_desc}_{task_id[:8]}.md"
    filepath = desktop / filename

    # Rapor içeriği oluştur
    lines = [
        f"# Görev raporu: {task.get('task', 'Bilinmeyen görev')}\n",
        f"- **Görev ID**: {task_id}",
        f"- **Durum**: {task.get('status', 'unknown')}",
        f"- **Başlangıç zamanı**: {task.get('started_at', '-')}",
        f"- **Model**: {task.get('model', '-')}",
        f"- **İş akışı**: {task.get('workflow', '-')}",
        f"- **Proje yolu**: {task.get('project_path', '-')}\n",
        "## İstatistikler\n",
        f"- Tokens: {task.get('stats', {}).get('total_tokens', 0)}",
        f"- Yürütme süresi: {task.get('stats', {}).get('execution_time', 0)}s",
        f"- Maliyet: ¥{task.get('stats', {}).get('total_cost', 0):.4f}",
        f"- Tamamlanan adımlar: {task.get('stats', {}).get('steps_completed', [])}",
        f"- Başarısız adımlar: {task.get('stats', {}).get('steps_failed', [])}\n",
    ]

    # Her bir adımın çıktıları
    # Önce result.outputs içinde ara (kalıcı geçmiş görev)
    step_outputs = task.get("result", {}).get("outputs", {})
    # Uyumluluk: result.outputs yoksa, step_outputs'u dene (bellek görevi)
    if not step_outputs:
        step_outputs = task.get("step_outputs", {})
    if step_outputs:
        lines.append("## Adım çıktıları\n")
        for step_name, output in step_outputs.items():
            lines.append(f"### {step_name}\n")
            # Türüne göre satır sonlarını doğru işle
            if isinstance(output, str):
                lines.append(output)
            elif isinstance(output, dict):
                # Sözlükte result alanı varsa, doğrudan result dizesini kullan
                result = (
                    output.get("result")
                    or output.get("output")
                    or output.get("content")
                )
                if isinstance(result, str):
                    lines.append(result)
                else:
                    lines.append(_json.dumps(output, ensure_ascii=False, indent=2))
            else:
                lines.append(
                    _json.dumps(output, ensure_ascii=False, indent=2)
                    if output
                    else "Çıktı yok"
                )
            lines.append("")

    # Nihai sonuç
    final = task.get("result", {})
    if final:
        lines.append("## Nihai sonuç\n")
        if isinstance(final, dict):
            lines.append(f"- Özet: {final.get('summary', '-')}")
            lines.append(f"- Süre: {final.get('execution_time', 0)}s")
            lines.append(f"- Tokens: {final.get('total_tokens', 0)}\n")
            for key, val in final.items():
                if key not in ("summary", "execution_time", "total_tokens", "outputs"):
                    lines.append(f"### {key}\n")
                    # Farklı türleri doğru işle
                    if isinstance(val, str):
                        lines.append(val)
                    elif isinstance(val, dict):
                        lines.append(_json.dumps(val, ensure_ascii=False, indent=2))
                    else:
                        lines.append(str(val))
                    lines.append("")
        else:
            lines.append(str(final))

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return JSONResponse({"path": str(filepath), "status": "saved"})


# ========================================
# Chat API - Sohbet tabanlı görev oluşturma
# ========================================


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    ready_to_execute: bool = False
    summary: str = ""
    task: dict | None = None


# İş akışı anahtar kelime eşlemesi
WORKFLOW_KEYWORDS = {
    "review": ["inceleme", "review", "kontrol", "kod kalitesi", "güvenlik açığı", "security", "quality"],
    "debug": ["hata ayıklama", "debug", "düzelt", "fix", "bug", "hata", "error", "sorun"],
    "test": ["test", "unittest", "birim test", "coverage", "kapsama"],
    "build": ["geliştirme", "uygula", "build", "create", "yaz", "ekle"],
}

# Model anahtar kelime eşlemesi
MODEL_KEYWORDS = {
    "deepseek": ["deepseek", "v4", "ucuz", "düşük maliyet"],
    "glm-4-flash": ["glm", "flash", "ücretsiz", "zhipu"],
    "MiniMax-Text-01": ["mimo", "xiaomi", "minimax"],
    "moonshot-v1-128k": ["kimi", "moonshot", "128k"],
    "doubao-pro-32k": ["doubao", "bytedance"],
    "tiangong-3": ["tiangong"],
    "Baichuan4": ["baichuan"],
}


def _detect_workflow(message: str) -> str:
    """Mesaj içeriğine göre iş akışı türünü tespit et"""
    message_lower = message.lower()
    scores = {}
    for workflow, keywords in WORKFLOW_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in message_lower)
        if score > 0:
            scores[workflow] = score
    return max(scores, key=scores.get) if scores else "build"


def _detect_model(message: str) -> str:
    """Mesaj içeriğine göre model tercihini tespit et"""
    message_lower = message.lower()
    scores = {}
    for model, keywords in MODEL_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in message_lower)
        if score > 0:
            scores[model] = score
    return max(scores, key=scores.get) if scores else "deepseek"


def _detect_target_type_from_message(message: str) -> tuple[str, str]:
    """Hedef türünü ve yolunu tespit et"""
    # GitHub URL
    github_match = re.search(r"github\.com/[^/\s]+/[^/\s]+", message)
    if github_match:
        return "github", f"https://{github_match.group(0)}"

    # HTTP URL
    url_match = re.search(r'https?://[^\s<>"\']+', message)
    if url_match:
        parsed = urlparse(url_match.group(0))
        if parsed.netloc == "github.com":
            return "github", parsed.geturl()
        return "url", parsed.geturl()

    # Yerel yol (basit tespit)
    path_match = re.search(r'[~./][^\s<>"\']*', message)
    if path_match:
        path = path_match.group(0)
        if path.startswith((".", "~/", "/")):
            return "local", path

    return "local", "."


def _generate_task_summary(task: dict) -> str:
    """Görev özeti oluştur"""
    workflow_names = {
        "build": "Tam geliştirme",
        "review": "Kod incelemesi",
        "debug": "Hata ayıklama ve düzeltme",
        "test": "Test senaryoları",
    }
    model_names = {
        "deepseek": "DeepSeek V4",
        "glm-4-flash": "GLM-4.7-Flash",
        "MiniMax-Text-01": "MiMo Flash",
        "moonshot-v1-128k": "Kimi 128K",
        "doubao-pro-32k": "Doubao-Pro",
        "tiangong-3": "Tiangong 3.0",
        "Baichuan4": "Baichuan 4",
    }

    wf_name = workflow_names.get(task["workflow"], task["workflow"])
    model_name = model_names.get(task["model"], task["model"])

    target_desc = task["project_path"]
    if task["target_type"] == "github":
        target_desc = f"GitHub deposu {task['project_path']}"
    elif task["target_type"] == "url":
        target_desc = f"Web sayfası {task['project_path']}"

    return f"{wf_name} · {model_name} · {target_desc}"


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Sohbet tabanlı görev oluşturma API

    Kullanıcının niyetini anlar, gerekli bilgileri toplar ve sonunda yürütülebilir görev yapılandırması üretir
    """
    message = request.message.strip()
    history = request.history

    # Niyeti tespit et
    workflow = _detect_workflow(message)
    model = _detect_model(message)
    target_type, target_path = _detect_target_type_from_message(message)

    # Daha fazla bilgi gerekip gerekmediğini kontrol et
    # Basit sezgisel: mesaj çok kısaysa (<10 karakter), daha fazla bilgi gerekebilir
    if len(message) < 10 and len(history) < 2:
        return ChatResponse(
            reply="Lütfen ihtiyacını detaylı bir şekilde açıkla, örneğin:\n• Hangi işlevi uygulamak istiyorsun?\n• Hangi kodu incelemek/düzeltmek gerekiyor?\n• Hedef kod nerede (yerel yol/GitHub bağlantısı)?",
            ready_to_execute=False,
        )

    # Görev yapılandırmasını oluştur
    task_config = {
        "description": message,
        "workflow": workflow,
        "model": model,
        "target_type": target_type,
        "project_path": target_path,
    }

    summary = _generate_task_summary(task_config)

    # Onay yanıtı oluştur
    workflow_desc = {
        "build": "Yeni özellik geliştir",
        "review": "Kod kalitesini incele",
        "debug": "Sorunları ayıkla ve düzelt",
        "test": "Test senaryoları üret",
    }

    reply = "Tamam, anladım! Şunu onaylayalım:\n\n"
    reply += f"**Görev türü:** {workflow_desc.get(workflow, workflow)}\n"
    reply += f"**Kullanılan model:** {model}\n"
    reply += f"**Hedef:** {target_path if target_type == 'local' else target_path}\n\n"
    reply += "Onayladığında AI ekibini başlatacağım."

    return ChatResponse(
        reply=reply, ready_to_execute=True, summary=summary, task=task_config
    )


class ChatCompletionRequest(BaseModel):
    """AI sohbet tamamlama isteği"""

    messages: list[dict]  # [{role: "user"|"assistant", content: "..."}]
    model: str = "deepseek"  # Model ID
    stream: bool = False  # Akış halinde dönülsün mü


class ChatCompletionResponse(BaseModel):
    """AI sohbet tamamlama yanıtı"""

    content: str
    model: str
    usage: dict = {}


@app.post("/api/chat/completions")
async def chat_completion_endpoint(request: ChatCompletionRequest):
    """
    Gerçek AI sohbet arayüzü — yanıt üretmek için model router'ı çağırır

    Hem akış (SSE) hem de akışsız modu destekler.
    """
    orch = get_orchestrator()
    router = orch.model_router

    # Mesaj listesi oluştur
    from src.models.base import Message as BaseMessage

    base_messages = [
        BaseMessage(role=m["role"], content=m["content"]) for m in request.messages
    ]

    if request.stream:
        # Akış yanıtı: SSE kullan
        async def event_stream():
            try:
                response = await router.route_and_call(
                    task_type="chat",
                    messages=base_messages,
                    complexity="medium",
                    use_cache=False,
                    override_model=request.model,
                )
                content = response.content or ""
                # Parçalar halinde gönder (akışı simüle et)
                chunk_size = max(1, len(content) // 20)
                for i in range(0, len(content), chunk_size):
                    chunk = content[i : i + chunk_size]
                    data = _json.dumps({"content": chunk, "done": False})
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0.02)
                # Tamamlama sinyali gönder
                done_data = _json.dumps(
                    {
                        "content": "",
                        "done": True,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens,
                        },
                        "model": response.model,
                    }
                )
                yield f"data: {done_data}\n\n"
            except Exception as e:
                err_data = _json.dumps(
                    {
                        "content": f"\n\n❌ Model çağrısı başarısız: {type(e).__name__}",
                        "done": True,
                        "error": True,
                    }
                )
                yield f"data: {err_data}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        # Akışsız yanıt
        try:
            response = await router.route_and_call(
                task_type="chat",
                messages=base_messages,
                complexity="medium",
                use_cache=False,
                override_model=request.model,
            )
            return ChatCompletionResponse(
                content=response.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )
        except Exception as e:
            return ChatCompletionResponse(
                content=f"❌ Model çağrısı başarısız: {type(e).__name__}",
                model=request.model,
            )


@app.post("/api/execute")
async def execute_task(background: BackgroundTasks, payload: Optional[dict] = None):
    """
    Görev yürütme API (asenkron, olay tabanlı)

    Adımlar:
    1. Görev oluştur, task_id döndür
    2. SSE /sse/execute/{task_id} üzerinden gerçek zamanlı ilerleme al
    3. Tamamlandığında SSE complete olayı gönderir
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Missing JSON body")

    task = payload.get("task")
    project_path = payload.get("project_path", ".")
    model = payload.get("model", "deepseek")
    workflow_name = payload.get("workflow", "build")
    target_type = payload.get("target_type", "")  # github / url / local / auto

    if not task:
        raise HTTPException(status_code=400, detail="Missing 'task' field")

    # Hedef türünü otomatik tespit et
    if not target_type or target_type == "auto":
        target_type = _detect_target_type(project_path)

    # Görev oluştur
    task_id = task_manager.create_task(
        task_desc=task, model=model, workflow=workflow_name, project_path=project_path
    )
    task_manager._tasks[task_id]["started_at"] = datetime.now().isoformat()
    task_manager._tasks[task_id]["status"] = "running"
    task_manager._tasks[task_id]["target_type"] = target_type

    # Arka planda yürüt
    background.add_task(
        run_task, task_id, task, project_path, model, workflow_name, target_type
    )

    return JSONResponse(
        {
            "status": "started",
            "task_id": task_id,
            "target_type": target_type,
            "message": "Görev başlatıldı, ilerlemeyi SSE bağlantısı üzerinden alın",
        }
    )


async def run_task(
    task_id: str,
    task: str,
    project_path: str,
    model: str,
    workflow_name: str,
    target_type: str = "local",
):
    """Arka planda görev yürüt"""
    import time

    start_time = time.time()
    orch = None
    extra_context = ""

    # Hedefi ön işle (clone GitHub / fetch URL)
    try:
        project_path, extra_context = _preprocess_target(
            project_path, target_type, task_id
        )
    except Exception as e:
        err_type = type(e).__name__
        task_manager.complete_task(task_id, error=f"Hedef ön işleme başarısız ({err_type})")
        history_store.save(
            task_id,
            {
                "task_id": task_id,
                "task": task,
                "status": "failed",
                "error_type": err_type,
                "started_at": datetime.now().isoformat(),
            },
        )
        return

    try:
        # Global orchestrator'ı yeniden kullan (SSE /api/agent/live ile aynı örneği paylaşır)
        orch = get_orchestrator()

        # İş akışını belirle
        steps = WORKFLOW_TEMPLATES.get(workflow_name, WORKFLOW_TEMPLATES["build"])

        # Görev durumundaki toplam adım sayısını güncelle
        task_manager._tasks[task_id]["stats"]["steps_total"] = len(steps)

        # Orchestrator'a geçerli görevi kaydet (/api/agent/live SSE tüketicisi için)
        from src.core.orchestrator import WorkflowResult, WorkflowStatus

        workflow_id = task_id
        wf_result = WorkflowResult(
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
        orch._active_workflows[workflow_id] = wf_result

        # Her adımı sırayla yürüt
        # context = {
        #             "project_path": project_path,
        #             "task": task,
        # }
        previous_outputs = {}

        for step in steps:
            agent_name = step.agent_name

            # Başlangıcı bildir
            task_manager.update_step(task_id, agent_name, "active")

            try:
                agent = orch.get_agent(agent_name)
                agent_context = AgentContext(
                    project_path=Path(project_path),
                    task_description=task + extra_context,
                    previous_outputs=previous_outputs,
                    override_model=model if model != "deepseek" else None,
                )

                output: AgentOutput = await asyncio.wait_for(
                    agent.execute(agent_context),
                    timeout=step.timeout,
                )

                if output.status == AgentStatus.COMPLETED:
                    previous_outputs[agent_name] = output
                    wf_result.steps_completed.append(agent_name)
                    wf_result.outputs[agent_name] = output
                    wf_result.total_tokens += output.usage.get("total_tokens", 0)
                    task_manager.update_step(
                        task_id, agent_name, "completed", output.result
                    )
                    task_manager._tasks[task_id]["stats"]["steps_completed"].append(
                        agent_name
                    )
                    task_manager._tasks[task_id]["stats"]["total_tokens"] += (
                        output.usage.get("total_tokens", 0)
                    )
                else:
                    wf_result.steps_failed.append(agent_name)
                    task_manager.update_step(
                        task_id, agent_name, "failed", output.error or "Unknown error"
                    )
                    task_manager._tasks[task_id]["stats"]["steps_failed"].append(
                        agent_name
                    )

            except TimeoutError:
                wf_result.steps_failed.append(agent_name)
                task_manager.update_step(task_id, agent_name, "failed", "Yürütme zaman aşımı")
                task_manager._tasks[task_id]["stats"]["steps_failed"].append(agent_name)
            except Exception as e:
                wf_result.steps_failed.append(agent_name)
                # Kullanıcı dostu hata mesajı çıkar
                err_str = str(e)
                if "429" in err_str or "Too Many Requests" in err_str:
                    error_msg = "API hız sınırı (429), lütfen sonra deneyin veya model değiştirin"
                elif "401" in err_str or "Unauthorized" in err_str:
                    error_msg = "API Anahtarı geçersiz veya süresi dolmuş, lütfen ayarları kontrol edin"
                elif "403" in err_str or "Forbidden" in err_str:
                    error_msg = "API erişimi reddedildi, lütfen API Anahtarı izinlerini kontrol edin"
                elif "timeout" in err_str.lower() or "zaman aşımı" in err_str:
                    error_msg = "API isteği zaman aşımına uğradı, lütfen sonra deneyin"
                elif "NoModelAvailable" in type(e).__name__:
                    error_msg = f"Tüm modeller kullanılamıyor: {err_str[:150]}"
                else:
                    error_msg = f"{type(e).__name__}: {err_str[:200]}"
                task_manager.update_step(task_id, agent_name, "failed", error_msg)
                task_manager._tasks[task_id]["stats"]["steps_failed"].append(agent_name)

        # İş akışını tamamlandı olarak işaretle
        wf_result.execution_time = time.time() - start_time
        wf_result.status = (
            WorkflowStatus.COMPLETED
            if not wf_result.steps_failed
            else WorkflowStatus.FAILED
        )

        # Sonuçları topla
        total_time = time.time() - start_time
        task_manager._tasks[task_id]["stats"]["execution_time"] = round(total_time, 1)

        result = {
            "result": f"İş akışı '{workflow_name}' tamamlandı",
            "outputs": {
                name: {
                    "result": out.result,
                    "status": out.status.value,
                    "usage": out.usage,
                }
                for name, out in previous_outputs.items()
            },
            "stats": task_manager._tasks[task_id]["stats"],
        }

        task_manager.complete_task(task_id, result=result)

        # Geçmiş kaydını sakla
        history_record = {
            "task_id": task_id,
            "task": task,
            "workflow": workflow_name,
            "project_path": project_path,
            "model": model,
            "status": "completed",
            "started_at": task_manager._tasks[task_id].get("started_at"),
            "completed_at": datetime.now().isoformat(),
            "stats": task_manager._tasks[task_id]["stats"],
            "result": result,
        }
        history_store.save(task_id, history_record)

    except Exception as e:
        if orch is not None and workflow_id in orch._active_workflows:
            orch._active_workflows[workflow_id].status = WorkflowStatus.FAILED
        task_manager.complete_task(task_id, error="Görev yürütme başarısız")

        # Başarısızlık kaydını sakla (yalnızca istisna türü, detay sızdırmaz)
        history_record = {
            "task_id": task_id,
            "task": task,
            "workflow": workflow_name,
            "project_path": project_path,
            "model": model,
            "status": "failed",
            "started_at": task_manager._tasks[task_id].get("started_at"),
            "completed_at": datetime.now().isoformat(),
            "error_type": type(e).__name__,
        }
        history_store.save(task_id, history_record)

    finally:
        # Geçici dizini temizle (GitHub clone)
        _cleanup_target(project_path, target_type)


# ===== Senkron yürütme uç noktası (küçük görevler için uygundur) =====
class ExecuteRequest(BaseModel):
    task: str
    project_path: str = "."
    model: str = "deepseek"
    workflow: str = "build"


@app.post("/api/execute-sync")
async def execute_task_sync(req: ExecuteRequest):
    """Senkron görev yürüt (sonucu doğrudan döner, küçük görevler için uygundur)"""
    import time

    start_time = time.time()

    try:
        router = create_router()
        orch = create_orchestrator(router)

        steps = WORKFLOW_TEMPLATES.get(req.workflow, WORKFLOW_TEMPLATES["build"])
        previous_outputs = {}
        total_tokens = 0

        for step in steps:
            agent_name = step.agent_name
            try:
                agent = orch.get_agent(agent_name)
                output = await asyncio.wait_for(
                    agent.execute(
                        AgentContext(
                            project_path=Path(req.project_path),
                            task_description=req.task,
                            previous_outputs=previous_outputs,
                        )
                    ),
                    timeout=step.timeout,
                )

                if output.status == AgentStatus.COMPLETED:
                    previous_outputs[agent_name] = output
                    total_tokens += output.usage.get("total_tokens", 0)
                else:
                    return JSONResponse(
                        {
                            "status": "error",
                            "message": f"{agent_name} yürütme başarısız: {output.error}",
                        }
                    )

            except TimeoutError:
                return JSONResponse(
                    {
                        "status": "error",
                        "message": f"{agent_name} yürütme zaman aşımı",
                    }
                )

        return JSONResponse(
            {
                "status": "success",
                "result": {
                    "task": req.task,
                    "workflow": req.workflow,
                    "steps_completed": list(previous_outputs.keys()),
                    "total_tokens": total_tokens,
                    "execution_time": round(time.time() - start_time, 1),
                    "outputs": {
                        name: out.result for name, out in previous_outputs.items()
                    },
                },
            }
        )

    except Exception as e:
        print(f"[ERROR] API endpoint error: {e}")
        return JSONResponse(
            {
                "status": "error",
                "message": "Sunucu iç hatası, lütfen sonra deneyin",
            }
        )


# ===== Yapılandırma uç noktası =====
@app.get("/api/config")
async def get_config():
    """Kullanılabilir yapılandırmayı al"""
    return JSONResponse(
        {
            "models": ["deepseek", "tongyi", "wenxin"],
            "workflows": list(WORKFLOW_TEMPLATES.keys()),
            "agents": [s.agent_name for s in WORKFLOW_TEMPLATES["build"]],
        }
    )


# ===== Settings sayfası ve API =====
SETTINGS_DIR = Path.home() / ".omc"
SETTINGS_FILE = SETTINGS_DIR / "config.json"


def _read_settings() -> dict[str, Any]:
    """~/.omc/config.json oku, yoksa varsayılan değerleri döndür"""
    if not SETTINGS_FILE.exists():
        return {
            "models": {
                "deepseek": {
                    "provider": "DeepSeek",
                    "api_key": "",
                    "cost_level": "free",
                    "enabled": True,
                },
                "tongyi": {
                    "provider": "Alibaba Cloud",
                    "api_key": "",
                    "cost_level": "low",
                    "enabled": False,
                },
                "wenxin": {
                    "provider": "Baidu",
                    "api_key": "",
                    "cost_level": "low",
                    "enabled": False,
                },
            },
            "defaults": {
                "model": "deepseek",
                "workflow": "build",
                "timeout": 300,
            },
        }
    try:
        import json

        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARNING] Failed to parse settings JSON: {e}")
        return (
            _read_settings.__wrapped__()
            if hasattr(_read_settings, "__wrapped__")
            else {
                "models": {
                    "deepseek": {
                        "provider": "DeepSeek",
                        "api_key": "",
                        "cost_level": "free",
                        "enabled": True,
                    },
                    "tongyi": {
                        "provider": "Alibaba Cloud",
                        "api_key": "",
                        "cost_level": "low",
                        "enabled": False,
                    },
                    "wenxin": {
                        "provider": "Baidu",
                        "api_key": "",
                        "cost_level": "low",
                        "enabled": False,
                    },
                },
                "defaults": {
                    "model": "deepseek",
                    "workflow": "build",
                    "timeout": 300,
                },
            }
        )
    # Gerekli alanların mevcut olduğundan emin ol
    if "models" not in raw:
        raw["models"] = {}
    if "defaults" not in raw:
        raw["defaults"] = {}
    for key in ("deepseek", "tongyi", "wenxin"):
        if key not in raw["models"]:
            raw["models"][key] = {
                "provider": {
                    "deepseek": "DeepSeek",
                    "tongyi": "Alibaba Cloud",
                    "wenxin": "Baidu",
                }.get(key, key),
                "api_key": "",
                "cost_level": {
                    "deepseek": "free",
                    "tongyi": "low",
                    "wenxin": "low",
                }.get(key, "low"),
                "enabled": key == "deepseek",
            }
    for dk, dv in {
        "model": "deepseek",
        "workflow": "build",
        "timeout": 300,
    }.items():
        raw["defaults"].setdefault(dk, dv)
    return raw


def _mask_key(key: str) -> str:
    """API Anahtarını maskele, yalnızca son 4 hane gösterilir"""
    if not key or len(key) <= 4:
        return key or ""
    return "*" * (len(key) - 4) + key[-4:]


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Ayarlar sayfası"""
    return templates.TemplateResponse(request, "settings.html")


@app.get("/api/settings")
async def get_settings():
    """Geçerli ayarları al (API Anahtarı maskelenir)"""
    settings = _read_settings()
    # API Anahtarını maskele
    # masked = json_dumps(settings, ensure_ascii=False)  # keep original for structure
    # Deep-copy models with masked keys
    for _m in settings.get("models", {}).values():
        raw_key = _m.get("api_key", "")
        _m["api_key_masked"] = _mask_key(raw_key)
        _m["has_key"] = bool(raw_key)
        # Ön ucun geri doldurması için orijinal anahtarı koru (localhost güvenli)
        # api_key alanı silinmez, ön uç giriş alanına geri doldurması için gerekir
    return JSONResponse(settings)


@app.post("/api/settings")
async def save_settings(payload: dict):
    """Ayarları ~/.omc/config.json dosyasına kaydet"""
    import json

    # Mevcut ayarları okuyup birleştir
    current = _read_settings()

    # models'i birleştir
    if "models" in payload:
        for name, model_conf in payload["models"].items():
            if name not in current["models"]:
                current["models"][name] = {}
            for k, v in model_conf.items():
                if k == "api_key":
                    # Maskelenmiş değeri atla (* ile başlayanı yazma)
                    if isinstance(v, str) and v.startswith("*"):
                        continue
                current["models"][name][k] = v

    # defaults'u birleştir
    if "defaults" in payload:
        current["defaults"].update(payload["defaults"])

    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return JSONResponse({"status": "ok", "message": "Ayarlar kaydedildi"})


# ===== Bağlantı testi =====
@app.post("/api/test-connection")
async def test_connection(payload: dict):
    """API Anahtarının kullanılabilirliğini test eder.

    İki mod destekler:
    - provider modu: { provider, api_key, base_url } → Bilinen modelle belirli provider'ı test eder
    - custom modu: { url, api_key, model_id } → Belirtilen URL ile özel modeli test eder

    Döner: { ok: bool, msg: str, latency_ms?: number }
    """
    import time

    import httpx

    provider = payload.get("provider")
    api_key = payload.get("api_key")
    base_url = payload.get("base_url")
    model_id = payload.get("model_id")  # Yalnızca custom modu

    # ── Provider modu ──────────────────────────────────
    if provider:
        # En küçük istek gövdesi oluştur (token tüketmez)
        try:
            if provider == "glm":
                url = (
                    base_url or "https://open.bigmodel.cn/api/paas/v4"
                ) + "/chat/completions"
                body = {
                    "model": "glm-4-flash",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "deepseek":
                url = (base_url or "https://api.deepseek.com/v1") + "/chat/completions"
                body = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "kimi":
                url = (base_url or "https://api.moonshot.cn/v1") + "/chat/completions"
                body = {
                    "model": "moonshot-v1-8k",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "doubao":
                url = (
                    base_url or "https://ark.cn-beijing.volces.com/api/v3"
                ) + "/chat/completions"
                body = {
                    "model": "doubao-pro-32k",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "mimo":
                url = (
                    base_url or "https://api.xiaomimimo.com/v1"
                ) + "/chat/completions"
                body = {
                    "model": "MiMo-V2-Flash",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "tiangong":
                url = (
                    base_url or "https://model-platform.tiangong.cn/v1"
                ) + "/chat/completions"
                body = {
                    "model": "tiangong",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "baichuan":
                url = (
                    base_url or "https://api.baichuan-ai.com/v1"
                ) + "/chat/completions"
                body = {
                    "model": "Baichuan4",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            else:
                return JSONResponse(
                    {"ok": False, "msg": f"Bilinmeyen sağlayıcı: {provider}"}, status_code=400
                )

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            start = time.time()
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=body, headers=headers)
            latency_ms = round((time.time() - start) * 1000)

            if resp.status_code == 200:
                # Check if response is actually JSON (not an HTML page)
                ct = resp.headers.get("content-type", "")
                if "html" in ct.lower():
                    return JSONResponse(
                        {
                            "ok": False,
                            "msg": "API yanıtı yerine bir web sayfası döndü — lütfen Base URL'nin API uç noktası (web sayfası değil) olduğundan emin olun",
                        }
                    )
                return JSONResponse(
                    {
                        "ok": True,
                        "msg": f"Bağlantı başarılı ({latency_ms}ms)",
                        "latency_ms": latency_ms,
                    }
                )
            elif resp.status_code == 401:
                return JSONResponse(
                    {"ok": False, "msg": "API Anahtarı geçersiz (401 Unauthorized)"}
                )
            elif resp.status_code == 403:
                return JSONResponse(
                    {"ok": False, "msg": "API Anahtarı reddedildi (403 Forbidden)"}
                )
            else:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text[:100])
                except Exception as e:
                    print(f"[WARNING] Failed to parse error JSON: {e}")
                    err = resp.text[:100]
                return JSONResponse(
                    {"ok": False, "msg": f"API hatası {resp.status_code}: {err}"},
                    status_code=502,
                )

        except httpx.TimeoutException:
            return JSONResponse(
                {"ok": False, "msg": "Bağlantı zaman aşımına uğradı (15s), lütfen Base URL veya ağ bağlantısını kontrol edin"}
            )
        except httpx.ConnectError as e:
            return JSONResponse({"ok": False, "msg": f"Bağlantı başarısız: {e}"}, status_code=502)
        except Exception as e:
            return JSONResponse({"ok": False, "msg": f"Test başarısız: {e}"}, status_code=500)

    # ── Custom modu ──────────────────────────────────
    if base_url and model_id:
        if not api_key:
            return JSONResponse(
                {"ok": False, "msg": "API Anahtarı boş (özel model genellikle Anahtar gerektirir)"},
                status_code=400,
            )
        try:
            url = base_url.rstrip("/") + "/chat/completions"
            body = {
                "model": model_id,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            start = time.time()
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=body, headers=headers)
            latency_ms = round((time.time() - start) * 1000)
            if resp.status_code == 200:
                return JSONResponse(
                    {
                        "ok": True,
                        "msg": f"Bağlantı başarılı ({latency_ms}ms)",
                        "latency_ms": latency_ms,
                    }
                )
            else:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text[:100])
                except Exception as e:
                    print(f"[WARNING] Failed to parse error JSON: {e}")
                    err = resp.text[:100]
                return JSONResponse(
                    {"ok": False, "msg": f"API hatası {resp.status_code}: {err}"},
                    status_code=502,
                )
        except httpx.TimeoutException:
            return JSONResponse({"ok": False, "msg": "Bağlantı zaman aşımı (15s)"})
        except httpx.ConnectError as e:
            return JSONResponse({"ok": False, "msg": f"Bağlantı başarısız: {e}"}, status_code=502)
        except Exception as e:
            return JSONResponse({"ok": False, "msg": f"Test başarısız: {e}"}, status_code=500)

    return JSONResponse(
        {"ok": False, "msg": "Parametreler eksik (provider veya base_url+model_id gerekir)"},
        status_code=400,
    )


# ===== İş akışı yönetim API (P1-6 Agent alt sistem yeniden yapılandırması Aşama 1) =====


@app.get("/api/workflows")
async def list_workflows():
    """Tüm kullanılabilir iş akışlarını listele (yerleşik + kullanıcı tanımlı)"""
    loader = WorkflowLoader()
    names = loader.list_workflows()
    builtin = set(loader.list_builtins())
    return JSONResponse(
        {
            "workflows": names,
            "builtin_count": len(builtin),
            "user_count": len(names) - len(builtin),
        }
    )


@app.get("/api/workflows/{name}")
async def get_workflow(name: str):
    """Belirtilen iş akışının tam yapılandırmasını al"""
    loader = WorkflowLoader()
    config = loader.get_workflow_config(name)
    if config is None:
        # Yedek: WORKFLOW_TEMPLATES'ten dene
        steps = WORKFLOW_TEMPLATES.get(name, [])
        if steps:
            return JSONResponse(
                {
                    "name": name,
                    "description": "",
                    "source": "builtin",
                    "steps": [
                        s.model_dump() if hasattr(s, "model_dump") else s for s in steps
                    ],
                }
            )
        return JSONResponse({"error": f"İş akışı '{name}' bulunamadı"}, status_code=404)
    d = config.model_dump() if hasattr(config, "model_dump") else asdict(config)
    return JSONResponse({"name": name, **d})


@app.put("/api/workflows/{name}")
async def save_workflow(name: str, payload: dict):
    """Özel iş akışını kaydet veya güncelle (PUT oluşturma veya üzerine yazma için)"""
    try:
        loader = WorkflowLoader()
        # Eski önbelleği temizle
        loader._cache.pop(name, None)
        # YAML dizesini ayrıştır
        yaml_str = payload.get("yaml", "")
        config = loader.parse_yaml_string(yaml_str, name)
        if config is None:
            return JSONResponse({"error": "YAML ayrıştırma başarısız, lütfen biçimi kontrol edin"}, status_code=400)
        # Adın tutarlı olduğundan emin ol
        config.name = name
        config.source = "user"
        loader.save_workflow(name, config)
        return JSONResponse({"status": "ok", "message": f"İş akışı '{name}' kaydedildi"})
    except Exception as e:
        return JSONResponse(
            {"error": f"İş akışı '{name}' kaydedilemedi: {e}"}, status_code=400
        )


@app.delete("/api/workflows/{name}")
async def delete_workflow(name: str):
    """Özel iş akışını sil (yerleşik silinemez)"""
    loader = WorkflowLoader()
    if loader.is_builtin(name):
        return JSONResponse({"error": "Yerleşik iş akışları silinemez"}, status_code=403)
    try:
        loader.delete_workflow(name)
        return JSONResponse({"status": "ok", "message": f"İş akışı '{name}' silindi"})
    except FileNotFoundError:
        return JSONResponse({"error": f"İş akışı '{name}' bulunamadı"}, status_code=404)
    except Exception as e:
        print(f"[ERROR] Failed to delete workflow '{name}': {e}")
        return JSONResponse({"error": f"İş akışı '{name}' silinemedi"}, status_code=400)


# ========================================
# Session API - Oturum yönetimi
# ========================================

SESSIONS_DIR = Path.home() / ".omc" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class SessionCreate(BaseModel):
    title: str = "Yeni oturum"


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    messages: Optional[list] = None


@app.get("/api/sessions")
async def list_sessions():
    """Tüm oturum listesini al"""
    sessions = []
    for f in sorted(
        SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            data = _json.loads(f.read_text(encoding="utf-8"))
            sessions.append(
                {
                    "id": data.get("id", f.stem),
                    "title": data.get("title", "Yeni oturum"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                }
            )
        except Exception as e:
            print(f"[WARNING] Failed to load session {f.name}: {e}")
    return JSONResponse({"sessions": sessions})


@app.post("/api/sessions")
async def create_session(req: SessionCreate):
    """Yeni oturum oluştur"""
    session_id = str(uuid.uuid4())[:12]
    now = datetime.now().isoformat()
    session_data = {
        "id": session_id,
        "title": req.title,
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    filepath = SESSIONS_DIR / f"{session_id}.json"
    filepath.write_text(
        _json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return JSONResponse(
        {
            "status": "ok",
            "session": {
                "id": session_id,
                "title": req.title,
                "created_at": now,
                "updated_at": now,
                "message_count": 0,
            },
        }
    )


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Tek bir oturum detayını al"""
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        data = _json.loads(filepath.read_text(encoding="utf-8"))
        return JSONResponse(data)
    except Exception as e:
        print(f"[WARNING] Failed to read session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read session")


@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, req: SessionUpdate):
    """Oturumu güncelle (başlık veya mesajlar)"""
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        data = _json.loads(filepath.read_text(encoding="utf-8"))
        if req.title is not None:
            data["title"] = req.title
        if req.messages is not None:
            data["messages"] = req.messages
        data["updated_at"] = datetime.now().isoformat()
        filepath.write_text(
            _json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return JSONResponse({"status": "ok", "updated_at": data["updated_at"]})
    except Exception as e:
        print(f"[WARNING] Failed to update session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Oturumu sil"""
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        filepath.unlink()
        return JSONResponse({"status": "ok"})
    except Exception as e:
        print(f"[WARNING] Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


# ===== Kapsama API =====
@app.get("/api/coverage")
async def get_coverage():
    """Test kapsama verilerini al"""
    try:
        summary = run_coverage_analysis(project_root)
        report = format_coverage_report(summary)
        return JSONResponse(report)
    except Exception as e:
        return JSONResponse(
            {
                "error": f"Kapsama analizi başarısız: {type(e).__name__}",
                "overall": {"coverage": 0, "color": "#ef4444"},
            },
            status_code=500,
        )


@app.post("/api/coverage/run")
async def run_coverage():
    """Kapsama analizini yeniden çalıştır"""
    try:
        summary = run_coverage_analysis(project_root)
        report = format_coverage_report(summary)
        return JSONResponse(report)
    except Exception as e:
        return JSONResponse(
            {
                "error": f"Kapsama analizi başarısız: {type(e).__name__}",
                "overall": {"coverage": 0, "color": "#ef4444"},
            },
            status_code=500,
        )


# ===== Sağlık kontrolü =====
@app.get("/health")
async def health_check():
    """Sağlık kontrolü"""
    return JSONResponse({"status": "healthy", "version": "0.1.0"})


# ===== Kapsama sayfası =====
@app.get("/coverage", response_class=HTMLResponse)
async def coverage_page(request: Request):
    """Test kapsama sayfası"""
    return templates.TemplateResponse(request, "coverage.html")


# ===== API belgeleri sayfası =====
@app.get("/docs", response_class=HTMLResponse)
async def docs_page(request: Request):
    """Kullanım belgeleri sayfası"""
    return templates.TemplateResponse(request, "docs.html")


# ========================================
# Main Entry
# ========================================
def run():
    """Servisi başlat"""
    print("=" * 50)
    print("  🤖 Oh My Coder Web Interface")
    print("  📍 http://localhost:8000")
    print("  📖 API Docs: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)  # nosec B104


if __name__ == "__main__":
    run()
