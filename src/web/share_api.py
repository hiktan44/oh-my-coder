from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Share API - Oturum paylaşımı Web uç noktaları

Uç noktalar:
- POST /api/share        Paylaşım oluştur
- GET  /api/share/{id}   Paylaşım detayını al
- GET  /api/share        Paylaşımları listele
- POST /api/share/{id}/import  Paylaşımı içe aktar
- DELETE /api/share/{id} Paylaşımı sil
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/share", tags=["share"])

# ========================================
# Share Storage (commands/share.py mantığını yeniden kullanır)
# ========================================

SHARE_DIR = Path.home() / ".omc" / "shares"
HISTORY_DIR = Path(".omc/history")


def _ensure_dir() -> None:
    SHARE_DIR.mkdir(parents=True, exist_ok=True)


def _share_path(share_id: str) -> Path:
    return SHARE_DIR / f"share_{share_id}.json"


def _sanitize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Yapılandırma bilgilerini maskele"""
    safe = {}
    for key, value in config.items():
        if isinstance(value, dict):
            safe[key] = _sanitize_config(value)
        elif isinstance(value, str) and (
            "key" in key.lower()
            or "token" in key.lower()
            or "secret" in key.lower()
            or "password" in key.lower()
        ):
            safe[key] = value[:4] + "****" if len(value) > 4 else "****"
        else:
            safe[key] = value
    return safe


# ========================================
# Pydantic Models
# ========================================


class ShareCreateRequest(BaseModel):
    """Paylaşım oluşturma isteği"""

    task_id: Optional[str] = Field(None, description="Görev ID, boşsa en son görev")
    include_config: bool = Field(True, description="Yapılandırma dahil edilsin mi")
    tags: list[str] = Field(default_factory=list, description="Etiketler")
    expires_hours: int = Field(0, description="Son kullanma süresi (saat), 0=hiç sona ermesin")


class ShareImportRequest(BaseModel):
    """Paylaşım içe aktarma isteği"""

    target_dir: Optional[str] = Field(None, description="İçe aktarma hedef dizini")


class ShareResponse(BaseModel):
    """Paylaşım yanıtı"""

    share_id: str
    created_at: str
    expires_at: Optional[str] = None
    tags: list[str] = []
    task: str = ""
    steps: int = 0


class ShareDetailResponse(BaseModel):
    """Paylaşım detay yanıtı"""

    share_id: str
    version: int = 1
    created_at: str
    expires_at: Optional[str] = None
    tags: list[str] = []
    session: dict[str, Any] = {}


# ========================================
# API Endpoints
# ========================================


@router.post("", response_model=ShareDetailResponse)
async def create_share(req: ShareCreateRequest) -> Any:
    """Paylaşım oluştur"""
    _ensure_dir()

    # Hedef geçmişi bul
    target_file = None
    if req.task_id:
        for prefix in ["", "history_"]:
            candidate = HISTORY_DIR / f"{prefix}{req.task_id}.json"
            if candidate.exists():
                target_file = candidate
                break
        if not target_file:
            raise HTTPException(status_code=404, detail=f"Görev bulunamadı: {req.task_id}")
    else:
        json_files = sorted(
            HISTORY_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not json_files:
            raise HTTPException(status_code=404, detail="Geçmiş kayıt yok")
        target_file = json_files[0]

    try:
        with open(target_file, encoding="utf-8") as f:
            history_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Okuma başarısız: {e}")

    # Paylaşım ID oluştur
    import uuid

    share_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()

    share_record = {
        "share_id": share_id,
        "version": 1,
        "created_at": now,
        "expires_at": (
            datetime.fromtimestamp(
                datetime.now().timestamp() + req.expires_hours * 3600
            ).isoformat()
            if req.expires_hours > 0
            else None
        ),
        "tags": req.tags,
        "session": {
            "history": history_data,
        },
    }

    if req.include_config:
        config_path = Path.home() / ".omc" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                share_record["session"]["config"] = _sanitize_config(config)
            except (json.JSONDecodeError, OSError):
                pass

    share_file = _share_path(share_id)
    with open(share_file, "w", encoding="utf-8") as f:
        json.dump(share_record, f, ensure_ascii=False, indent=2)

    return share_record


@router.get("", response_model=list[ShareResponse])
async def list_shares() -> Any:
    """Tüm paylaşımları listele"""
    _ensure_dir()

    shares = []
    for f in SHARE_DIR.glob("share_*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            history = data.get("session", {}).get("history", {})
            shares.append(
                ShareResponse(
                    share_id=data.get("share_id", ""),
                    created_at=data.get("created_at", ""),
                    expires_at=data.get("expires_at"),
                    tags=data.get("tags", []),
                    task=history.get("task_description", ""),
                    steps=len(history.get("steps", [])),
                )
            )
        except (json.JSONDecodeError, OSError):
            continue

    shares.sort(key=lambda s: s.created_at, reverse=True)
    return shares


@router.get("/{share_id}", response_model=ShareDetailResponse)
async def get_share(share_id: str) -> Any:
    """Paylaşım detayını al"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        raise HTTPException(status_code=404, detail=f"Paylaşım bulunamadı: {share_id}")

    try:
        with open(share_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Okuma başarısız: {e}")

    # Süre dolumunu kontrol et
    if data.get("expires_at"):
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() > expires:
            raise HTTPException(status_code=410, detail="Paylaşımın süresi dolmuş")

    return data


@router.post("/{share_id}/import")
async def import_share(share_id: str, req: ShareImportRequest) -> Any:
    """Paylaşım ID ile oturumu içe aktar"""
    _ensure_dir()

    share_file = _share_path(share_id)
    if not share_file.exists():
        raise HTTPException(status_code=404, detail=f"Paylaşım bulunamadı: {share_id}")

    try:
        with open(share_file, encoding="utf-8") as f:
            share_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Okuma başarısız: {e}")

    # Süre dolumunu kontrol et
    if share_data.get("expires_at"):
        expires = datetime.fromisoformat(share_data["expires_at"])
        if datetime.now() > expires:
            raise HTTPException(status_code=410, detail="Paylaşımın süresi dolmuş")

    session = share_data.get("session", {})
    history_data = session.get("history", {})

    if not history_data:
        raise HTTPException(status_code=400, detail="Paylaşımda geçmiş verisi yok")

    t_dir = Path(req.target_dir) if req.target_dir else HISTORY_DIR
    t_dir.mkdir(parents=True, exist_ok=True)

    # İçe aktarma ID oluştur
    import uuid

    orig_id = history_data.get("history_id", uuid.uuid4().hex[:8])
    imported_id = f"{orig_id}_imported_{share_id}"

    history_data["history_id"] = imported_id
    history_data["imported_from"] = share_id
    history_data["imported_at"] = datetime.now().isoformat()

    target_file = t_dir / f"history_{imported_id}.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

    return {
        "status": "imported",
        "history_id": imported_id,
        "share_id": share_id,
        "file": str(target_file),
    }


@router.delete("/{share_id}")
async def delete_share(share_id: str) -> Any:
    """Paylaşımı sil"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        raise HTTPException(status_code=404, detail=f"Paylaşım bulunamadı: {share_id}")

    share_file.unlink()
    return {"status": "deleted", "share_id": share_id}
