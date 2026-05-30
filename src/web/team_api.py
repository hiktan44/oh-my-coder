from __future__ import annotations

"""
Takım API rotaları

Takım oluşturma, katılma, görev senkronizasyonu ve istatistik gibi API'ler sağlar.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.team import (
    TaskStatus,
    task_sync,
    team_auth,
    team_notifier,
    team_statistics,
)

router = APIRouter(prefix="/api/team", tags=["team"])


# ========================================
# İstek modelleri
# ========================================


class CreateTeamRequest(BaseModel):
    """Takım oluşturma isteği"""

    name: str
    owner_id: str
    description: str = ""


class JoinTeamRequest(BaseModel):
    """Takıma katılma isteği"""

    invite_code: str
    user_id: str
    display_name: str = ""
    email: str = ""


class CreateTaskRequest(BaseModel):
    """Görev oluşturma isteği"""

    team_id: str
    creator_id: str
    title: str
    description: str = ""
    workflow: str = "build"
    model: str = "deepseek"


class UpdateTaskRequest(BaseModel):
    """Görev güncelleme isteği"""

    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0


class RecordUsageRequest(BaseModel):
    """Kullanım kaydı isteği"""

    team_id: str
    user_id: str
    task_id: str
    task_type: str
    model: str
    tokens_used: int
    cost: float
    execution_time: float
    status: str = "success"


class BroadcastRequest(BaseModel):
    """Yayın mesajı isteği"""

    team_id: str
    title: str
    message: str
    priority: str = "normal"


# ========================================
# Takım yönetim API
# ========================================


@router.post("/create")
async def create_team(request: CreateTeamRequest) -> dict[str, Any]:
    """
    Takım oluştur

    Args:
        request: Takım oluşturma isteği

    Returns:
        Takım bilgisi
    """
    team = await team_auth.create_team(
        name=request.name,
        owner_id=request.owner_id,
        description=request.description,
    )
    return team.to_dict()


@router.post("/join")
async def join_team(request: JoinTeamRequest) -> dict[str, Any]:
    """
    Takıma katıl

    Args:
        request: Takıma katılma isteği

    Returns:
        Takım bilgisi
    """
    team = await team_auth.join_team(
        invite_code=request.invite_code,
        user_id=request.user_id,
        display_name=request.display_name,
        email=request.email,
    )
    if not team:
        raise HTTPException(status_code=404, detail="Geçersiz davet kodu")
    return team.to_dict()


@router.post("/leave")
async def leave_team(user_id: str, team_id: str) -> dict[str, bool]:
    """
    Takımdan ayrıl

    Args:
        user_id: Kullanıcı ID
        team_id: Takım ID

    Returns:
        İşlem sonucu
    """
    success = await team_auth.leave_team(user_id, team_id)
    if not success:
        raise HTTPException(status_code=400, detail="Takımdan ayrılamadı")
    return {"success": True}


@router.post("/delete")
async def delete_team(team_id: str, requester_id: str) -> dict[str, bool]:
    """
    Takımı sil

    Args:
        team_id: Takım ID
        requester_id: İsteyen kişi ID

    Returns:
        İşlem sonucu
    """
    success = await team_auth.delete_team(team_id, requester_id)
    if not success:
        raise HTTPException(status_code=403, detail="Takımı silme yetkisi yok")
    return {"success": True}


@router.get("/{team_id}")
async def get_team(team_id: str) -> dict[str, Any]:
    """
    Takım bilgisini al

    Args:
        team_id: Takım ID

    Returns:
        Takım bilgisi
    """
    team = await team_auth.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Takım bulunamadı")
    return team.to_dict()


@router.get("/user/{user_id}")
async def get_user_team(user_id: str) -> dict[str, Any]:
    """
    Kullanıcının dahil olduğu takımı al

    Args:
        user_id: Kullanıcı ID

    Returns:
        Takım bilgisi
    """
    team = await team_auth.get_user_team(user_id)
    if not team:
        raise HTTPException(status_code=404, detail="Kullanıcı hiçbir takıma katılmamış")
    return team.to_dict()


@router.post("/{team_id}/regenerate-invite")
async def regenerate_invite(team_id: str, requester_id: str) -> dict[str, str]:
    """
    Davet kodunu yeniden oluştur

    Args:
        team_id: Takım ID
        requester_id: İsteyen kişi ID

    Returns:
        Yeni davet kodu
    """
    code = await team_auth.regenerate_invite_code(team_id, requester_id)
    if not code:
        raise HTTPException(status_code=403, detail="Davet kodu oluşturma yetkisi yok")
    return {"invite_code": code}


# ========================================
# Görev senkronizasyon API
# ========================================


@router.post("/task/create")
async def create_task(request: CreateTaskRequest) -> dict[str, Any]:
    """
    Takım görevi oluştur

    Args:
        request: Görev oluşturma isteği

    Returns:
        Görev bilgisi
    """
    import uuid

    task_id = f"task_{uuid.uuid4().hex[:8]}"

    task = await task_sync.create_task(
        task_id=task_id,
        team_id=request.team_id,
        creator_id=request.creator_id,
        title=request.title,
        description=request.description,
        workflow=request.workflow,
        model=request.model,
    )

    # Bildirim gönder
    await team_notifier.notify_task_created(
        task_id=task.task_id,
        team_id=task.team_id,
        creator_id=task.creator_id,
        title=task.title,
    )

    return task.to_dict()


@router.put("/task/{task_id}/status")
async def update_task_status(
    task_id: str, request: UpdateTaskRequest
) -> dict[str, Any]:
    """
    Görev durumunu güncelle

    Args:
        task_id: Görev ID
        request: Güncelleme isteği

    Returns:
        Güncellenmiş görev bilgisi
    """
    status = TaskStatus(request.status)
    task = await task_sync.update_status(
        task_id=task_id,
        status=status,
        result=request.result,
        error=request.error,
        tokens_used=request.tokens_used,
        cost=request.cost,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")

    # Bildirim gönder
    if status == TaskStatus.COMPLETED:
        await team_notifier.notify_task_completed(
            task_id=task.task_id,
            team_id=task.team_id,
            title=task.title,
            result=request.result or {},
        )
    elif status == TaskStatus.FAILED:
        await team_notifier.notify_task_failed(
            task_id=task.task_id,
            team_id=task.team_id,
            title=task.title,
            error=request.error or "Bilinmeyen hata",
        )

    return task.to_dict()


@router.get("/task/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    """
    Görev detayını al

    Args:
        task_id: Görev ID

    Returns:
        Görev bilgisi
    """
    task = await task_sync.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return task.to_dict()


@router.get("/{team_id}/tasks")
async def get_team_tasks(team_id: str) -> list[dict[str, Any]]:
    """
    Takım görev listesini al

    Args:
        team_id: Takım ID

    Returns:
        Görev listesi
    """
    tasks = await task_sync.get_team_tasks(team_id)
    return [t.to_dict() for t in tasks]


@router.post("/task/{task_id}/subscribe")
async def subscribe_task(task_id: str, user_id: str) -> dict[str, bool]:
    """
    Görev güncellemelerine abone ol

    Args:
        task_id: Görev ID
        user_id: Kullanıcı ID

    Returns:
        İşlem sonucu
    """
    success = await task_sync.subscribe_task(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return {"success": True}


@router.delete("/task/{task_id}")
async def delete_task(task_id: str) -> dict[str, bool]:
    """
    Görevi sil

    Args:
        task_id: Görev ID

    Returns:
        İşlem sonucu
    """
    success = await task_sync.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return {"success": True}


# ========================================
# İstatistik API
# ========================================


@router.post("/usage/record")
async def record_usage(request: RecordUsageRequest) -> dict[str, Any]:
    """
    Kullanım verilerini kaydet

    Args:
        request: Kayıt isteği

    Returns:
        Kayıt bilgisi
    """
    import uuid

    record_id = f"usage_{uuid.uuid4().hex[:8]}"

    record = team_statistics.record_usage(
        record_id=record_id,
        team_id=request.team_id,
        user_id=request.user_id,
        task_id=request.task_id,
        task_type=request.task_type,
        model=request.model,
        tokens_used=request.tokens_used,
        cost=request.cost,
        execution_time=request.execution_time,
        status=request.status,
    )

    return record.to_dict()


@router.get("/{team_id}/stats")
async def get_team_stats(
    team_id: str, period: str = Query("week", pattern="^(day|week|month)$")
) -> dict[str, Any]:
    """
    Takım istatistiklerini al

    Args:
        team_id: Takım ID
        period: İstatistik dönemi

    Returns:
        İstatistik verileri
    """
    stats = team_statistics.get_team_stats(team_id, period)
    return stats.to_dict()


@router.get("/{team_id}/user/{user_id}/stats")
async def get_user_stats(
    team_id: str,
    user_id: str,
    period: str = Query("week", pattern="^(day|week|month)$"),
) -> dict[str, Any]:
    """
    Kullanıcı istatistiklerini al

    Args:
        team_id: Takım ID
        user_id: Kullanıcı ID
        period: İstatistik dönemi

    Returns:
        İstatistik verileri
    """
    stats = team_statistics.get_user_stats(user_id, team_id, period)
    return stats.to_dict()


# ========================================
# Bildirim API
# ========================================


@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest) -> dict[str, Any]:
    """
    Takıma yayın mesajı gönder

    Args:
        request: Yayın isteği

    Returns:
        Bildirim bilgisi
    """
    from src.team.notification import NotificationPriority

    priority = NotificationPriority(request.priority)

    notification = await team_notifier.broadcast(
        team_id=request.team_id,
        title=request.title,
        message=request.message,
        priority=priority,
    )

    return notification.to_dict()


@router.get("/{team_id}/notifications")
async def get_team_notifications(
    team_id: str, unread_only: bool = False
) -> list[dict[str, Any]]:
    """
    Takım bildirimlerini al

    Args:
        team_id: Takım ID
        unread_only: Yalnızca okunmamışları döndür

    Returns:
        Bildirim listesi
    """
    notifications = team_notifier.get_team_notifications(team_id, unread_only)
    return [n.to_dict() for n in notifications]


@router.get("/{team_id}/user/{user_id}/notifications")
async def get_user_notifications(
    team_id: str, user_id: str, unread_only: bool = False
) -> list[dict[str, Any]]:
    """
    Kullanıcı bildirimlerini al

    Args:
        team_id: Takım ID
        user_id: Kullanıcı ID
        unread_only: Yalnızca okunmamışları döndür

    Returns:
        Bildirim listesi
    """
    notifications = team_notifier.get_user_notifications(user_id, team_id, unread_only)
    return [n.to_dict() for n in notifications]


@router.post("/notification/{notification_id}/read")
async def mark_notification_read(notification_id: str) -> dict[str, bool]:
    """
    Bildirimi okundu olarak işaretle

    Args:
        notification_id: Bildirim ID

    Returns:
        İşlem sonucu
    """
    success = team_notifier.mark_as_read(notification_id)
    return {"success": success}
