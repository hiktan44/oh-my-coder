from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
omc share - Oturum paylaşma komutu

İşlev:
1. Oturumu farklı dışa aktar JSON(yapılandırma dahil+tarih)
2. Paylaşım bağlantısı oluştur (kısa ID)
3. Oturumları bağlantı yoluyla içe aktarın
4. Paylaşımları listeleme ve silme
"""


import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = typer.Typer(
    name="share",
    help="Konuşma paylaşımı - İhracat/içe aktarmak/Paylaşılan bağlantıları yönet",
    add_completion=False,
)

# ========================================
# Share Storage
# ========================================

SHARE_DIR = Path.home() / ".omc" / "shares"


def _ensure_dir() -> None:
    """Paylaşılan dizinin mevcut olduğundan emin olun"""
    SHARE_DIR.mkdir(parents=True, exist_ok=True)


def _generate_share_id() -> str:
    """oluşturmak 8 kısa paylaşım ID"""
    return uuid.uuid4().hex[:8]


def _share_path(share_id: str) -> Path:
    """Paylaşılan dosya yolunu al"""
    return SHARE_DIR / f"share_{share_id}.json"


# ========================================
# Core Functions
# ========================================


def export_session(
    task_id: Optional[str] = None,
    history_dir: Optional[Path] = None,
    include_config: bool = True,
    tags: Optional[list[str]] = None,
    expires_hours: int = 0,
) -> dict[str, Any]:
    """
    Oturumları paylaşılan kayıtlar olarak dışa aktarın.

    Args:
        task_id: Görevleri belirtin ID, eğer boşsa, en son olanı dışa aktarın
        history_dir: Geçmiş dizini
        include_config: Yapılandırma bilgilerinin dahil edilip edilmeyeceği
        tags: Etiket
        expires_hours: Son kullanma süresi (saat),0 anlamı asla sona ermez

    Returns:
        Kayıt sözlüğünü paylaş
    """
    _ensure_dir()

    h_dir = history_dir or Path(".omc/history")
    if not h_dir.exists():
        console.print("[red]❌ Geçmiş dizini mevcut değil[/red]")
        return {}

    # Hedef görevleri bulun
    target_file = None
    if task_id:
        target_file = h_dir / f"{task_id}.json"
        if not target_file.exists():
            # denemek history_ önek
            target_file = h_dir / f"history_{task_id}.json"
        if not target_file.exists():
            console.print(f"[red]❌ Görev bulunamadı: {task_id}[/red]")
            return {}
    else:
        # En yakın olanı bul
        json_files = sorted(
            h_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True
        )
        if not json_files:
            console.print("[red]❌ tarih yok[/red]")
            return {}
        target_file = json_files[0]

    # Geçmiş verileri okuyun
    try:
        with open(target_file, encoding="utf-8") as f:
            history_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]❌ Okuma başarısız oldu: {e}[/red]")
        return {}

    # Paylaşım kayıtları oluşturun
    share_id = _generate_share_id()
    now = datetime.now().isoformat()

    share_record = {
        "share_id": share_id,
        "version": 1,
        "created_at": now,
        "expires_at": (
            datetime.fromtimestamp(
                datetime.now().timestamp() + expires_hours * 3600
            ).isoformat()
            if expires_hours > 0
            else None
        ),
        "tags": tags or [],
        "session": {
            "history": history_data,
        },
    }

    # İsteğe bağlı yapılandırma dahil
    if include_config:
        config_path = Path.home() / ".omc" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                # Duyarsızlaştırma: kaldır API Key
                safe_config = _sanitize_config(config)
                share_record["session"]["config"] = safe_config
            except (json.JSONDecodeError, OSError):
                pass

    # Paylaşılan dosyayı kaydet
    share_file = _share_path(share_id)
    with open(share_file, "w", encoding="utf-8") as f:
        json.dump(share_record, f, ensure_ascii=False, indent=2)

    console.print("[green]✅ Paylaşım oluşturuldu[/green]")
    console.print(f"  Share ID: [bold cyan]{share_id}[/bold cyan]")
    console.print(f"  belge: {share_file}")

    return share_record


def _sanitize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Duyarsızlaştırma yapılandırması, kaldır API Key"""
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
            # rezervasyondan önce 4 Biraz + ****
            safe[key] = value[:4] + "****" if len(value) > 4 else "****"
        else:
            safe[key] = value
    return safe


def import_session(share_id: str, target_dir: Optional[Path] = None) -> dict[str, Any]:
    """
    paylaşarak ID Oturumu içe aktar.

    Args:
        share_id: paylaşmak ID
        target_dir: Hedef dizini içe aktar

    Returns:
        İçe aktarılan oturum verileri
    """
    _ensure_dir()

    share_file = _share_path(share_id)
    if not share_file.exists():
        console.print(f"[red]❌ Paylaşım mevcut değil: {share_id}[/red]")
        return {}

    try:
        with open(share_file, encoding="utf-8") as f:
            share_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]❌ Paylaşım okunamadı: {e}[/red]")
        return {}

    # Çekin süresi dolmuş
    if share_data.get("expires_at"):
        expires = datetime.fromisoformat(share_data["expires_at"])
        if datetime.now() > expires:
            console.print("[red]❌ Paylaşımın süresi doldu[/red]")
            return {}

    # İçe aktarma geçmişi
    session = share_data.get("session", {})
    history_data = session.get("history", {})

    if not history_data:
        console.print("[red]❌ Paylaşımda geçmiş veri yok[/red]")
        return {}

    t_dir = target_dir or Path(".omc/history")
    t_dir.mkdir(parents=True, exist_ok=True)

    # Yeni geçmiş oluştur ID
    history_id = history_data.get("history_id", str(uuid.uuid4())[:8])
    imported_id = f"{history_id}_imported_{share_id}"

    history_data["history_id"] = imported_id
    history_data["imported_from"] = share_id
    history_data["imported_at"] = datetime.now().isoformat()

    # Hedef dizine kaydet
    target_file = t_dir / f"history_{imported_id}.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

    console.print("[green]✅ Oturum içe aktarıldı[/green]")
    console.print(f"  History ID: [bold cyan]{imported_id}[/bold cyan]")
    console.print(f"  Kaynak paylaşımı: {share_id}")
    console.print(f"  belge: {target_file}")

    return history_data


def list_shares() -> list[dict[str, Any]]:
    """Tüm paylaşımları listele"""
    _ensure_dir()

    shares = []
    for f in SHARE_DIR.glob("share_*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            # Yalnızca özeti döndür
            shares.append(
                {
                    "share_id": data.get("share_id"),
                    "created_at": data.get("created_at"),
                    "expires_at": data.get("expires_at"),
                    "tags": data.get("tags", []),
                    "task": data.get("session", {})
                    .get("history", {})
                    .get("task_description", "-"),
                    "steps": len(
                        data.get("session", {}).get("history", {}).get("steps", [])
                    ),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue

    shares.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return shares


def delete_share(share_id: str) -> bool:
    """Paylaşımı sil"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        console.print(f"[red]❌ Paylaşım mevcut değil: {share_id}[/red]")
        return False

    share_file.unlink()
    console.print(f"[green]✅ Paylaşım silindi: {share_id}[/green]")
    return True


def get_share(share_id: str) -> Optional[dict[str, Any]]:
    """Paylaşım ayrıntılarını alın"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        return None

    try:
        with open(share_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ========================================
# CLI Commands
# ========================================


@app.command("create")
def share_create(
    task_id: Optional[str] = typer.Option(
        None, "--task", "-t", help="Görevleri belirtin ID(En sonuncuyu dışa aktarmak için boş)"
    ),
    tags: Optional[str] = typer.Option(None, "--tags", help="etiketler, virgülle ayrılmış"),
    no_config: bool = typer.Option(False, "--no-config", help="Yapılandırma bilgisi içermiyor"),
    expires: int = typer.Option(
        0, "--expires", "-e", help="Son kullanma süresi (saat),0=asla sona ermez"
    ),
) -> None:
    """Konuşmaları dışa aktarın ve paylaşım bağlantıları oluşturun"""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = export_session(
        task_id=task_id,
        include_config=not no_config,
        tags=tag_list,
        expires_hours=expires,
    )
    if result:
        console.print(
            Panel(
                f"Share ID: [bold cyan]{result['share_id']}[/bold cyan]\n"
                f"yaratılış zamanı: {result['created_at']}\n"
                f"Günü geçmiş: {result.get('expires_at') or 'asla sona ermez'}\n"
                f"Etiket: {', '.join(result.get('tags', [])) or 'hiçbiri'}",
                title="📤 Paylaşım oluşturuldu",
                border_style="green",
            )
        )


@app.command("import")
def share_import(
    share_id: str = typer.Argument(..., help="paylaşmak ID"),
) -> None:
    """paylaşarak ID Oturumu içe aktar"""
    result = import_session(share_id)
    if result:
        console.print(
            Panel(
                f"History ID: [bold cyan]{result.get('history_id')}[/bold cyan]\n"
                f"kaynak: {share_id}",
                title="📥 Oturum içe aktarıldı",
                border_style="green",
            )
        )


@app.command("list")
def share_list() -> None:
    """Tüm paylaşımları listele"""
    shares = list_shares()
    if not shares:
        console.print("[dim]Henüz paylaşım kaydı yok[/dim]")
        return

    table = Table(title="📤 paylaşım listesi", show_lines=True)
    table.add_column("Share ID", style="cyan")
    table.add_column("Görev açıklaması", max_width=40)
    table.add_column("adım sayısı", justify="right")
    table.add_column("yaratılış zamanı")
    table.add_column("Günü geçmiş")
    table.add_column("Etiket")

    for s in shares:
        expired = ""
        if s.get("expires_at"):
            exp = datetime.fromisoformat(s["expires_at"])
            expired = "❌ Günü geçmiş" if datetime.now() > exp else "✅ verimli"
        else:
            expired = "♾️ kalıcı"

        table.add_row(
            s["share_id"],
            s.get("task", "-")[:40],
            str(s.get("steps", 0)),
            (s.get("created_at") or "")[:19],
            expired,
            ", ".join(s.get("tags", [])) or "-",
        )

    console.print(table)


@app.command("delete")
def share_delete(
    share_id: str = typer.Argument(..., help="paylaşmak ID"),
) -> None:
    """Paylaşımı sil"""
    delete_share(share_id)


@app.command("show")
def share_show(
    share_id: str = typer.Argument(..., help="paylaşmak ID"),
) -> None:
    """Paylaşım ayrıntılarını görüntüle"""
    data = get_share(share_id)
    if not data:
        console.print(f"[red]❌ Paylaşım mevcut değil: {share_id}[/red]")
        return

    session = data.get("session", {})
    history = session.get("history", {})

    console.print(
        Panel(
            f"Share ID: [bold cyan]{data['share_id']}[/bold cyan]\n"
            f"Sürüm: v{data.get('version', 1)}\n"
            f"yaratmak: {data.get('created_at')}\n"
            f"Günü geçmiş: {data.get('expires_at') or 'asla sona ermez'}\n"
            f"Etiket: {', '.join(data.get('tags', [])) or 'hiçbiri'}\n"
            f"---\n"
            f"Görev: {history.get('task_description', '-')}\n"
            f"İş akışı: {history.get('workflow_name', '-')}\n"
            f"adım sayısı: {len(history.get('steps', []))}\n"
            f"toplam Token: {history.get('total_tokens', 0)}\n"
            f"toplam maliyet: ¥{history.get('total_cost', 0):.4f}\n"
            f"Yapılandırma içerir: {'Evet' if 'config' in session else 'HAYIR'}",
            title="📋 Ayrıntıları paylaş",
            border_style="cyan",
        )
    )
