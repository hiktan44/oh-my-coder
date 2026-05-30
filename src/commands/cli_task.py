from __future__ import annotations

from typing import Optional

"""
Görev durumuCLIEmir

omc task list              -tüm görevleri listele
omc task status <id>      -Görev ayrıntılarını görüntüle
omc task pause <id>       -Görevi duraklat
omc task resume <id>      -kurtarma görevi
omc task delete <id>      -Görevi sil
omc task steps <id>       -Tarayıcı reddedildi
"""


import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.state.task_state import (
    TaskStatus,
    delete_task,
    get_task,
    list_tasks,
    pause_task,
    resume_task,
)

app = typer.Typer(
    name="task",
    help="Görev durumu yönetimi-Görevleri listeleyin, duraklatın, devam ettirin, görüntüleyin",
    add_completion=False,
)
console = Console()


def _status_color(status: TaskStatus) -> str:
    """Durum renk haritası"""
    return {
        TaskStatus.PENDING: "dim",
        TaskStatus.RUNNING: "cyan",
        TaskStatus.PAUSED: "yellow",
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "red",
    }.get(status, "white")


def _status_emoji(status: TaskStatus) -> str:
    """durumemojiharitalama"""
    return {
        TaskStatus.PENDING: "⏳",
        TaskStatus.RUNNING: "🔄",
        TaskStatus.PAUSED: "⏸️",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
    }.get(status, "❓")


@app.command("list")
def task_list(
    status_filter: str = typer.Option(
        None,
        "--status",
        "-s",
        help="Duruma göre filtrele(pending/running/paused/completed/failed)",
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Maksimum ekran miktarı"),
) -> None:
    """
tüm görevleri listele

Örnek:
        omc task list
        omc task list --status running
        omc task list --status failed -n 50
    """
    status_enum: Optional[TaskStatus] = None
    if status_filter:
        try:
            status_enum = TaskStatus(status_filter.lower())
        except ValueError:
            console.print(
                f"[red]❗Geçersiz durum: {status_filter}[/red]\n"
                "Geçerli değerler: pending, running, paused, completed, failed"
            )
            raise typer.Exit(1)

    states = list_tasks(status_enum)
    if not states:
        console.print("[dim]Henüz görev yok[/dim]")
        return

    states = states[:limit]

    table = Table(title=f"hata işleme({len(states)})")
    table.add_column("durum", width=3)
    table.add_column("GörevID", style="cyan", width=12)
    table.add_column("geçerli adım", style="white")
    table.add_column("takvim", width=10)
    table.add_column("yaratılış zamanı", style="dim", width=18)

    for state in states:
        progress_str = f"{state.progress * 100:.0f}%"
        table.add_row(
            _status_emoji(state.status),
            state.task_id,
            (
                (state.current_step[:40] + "...")
                if len(state.current_step) > 40
                else state.current_step
            ),
            progress_str,
            state.created_at[:19].replace("T", " "),
        )

    console.print(table)

    #istatistikler
    len(states)
    counts = {s: sum(1 for s_ in states if s_.status == s) for s in TaskStatus}
    stats = " ".join(f"{_status_emoji(s)} {v}" for s, v in counts.items() if v > 0)
    console.print(f"\n[dim]{stats}[/dim]")


@app.command("status")
def task_status(
    task_id: str = typer.Argument(..., help="GörevID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Tam adımları göster"),
) -> None:
    """
Görev ayrıntılarını görüntüle

Örnek:
        omc task status abc123
        omc task status abc123 -v
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗Görev mevcut değil: {task_id}[/red]")
        raise typer.Exit(1)

    status_color = _status_color(state.status)
    emoji = _status_emoji(state.status)

    info_lines = [
        f"ID: [cyan]{state.task_id}[/cyan]",
        f"durum: [{status_color}]{emoji} {state.status.value}[/{status_color}]",
        f"takvim: [cyan]{state.progress * 100:.1f}%[/cyan]",
        f"geçerli adım: {state.current_step or 'hiçbiri'}",
        f"yaratılış zamanı: {state.created_at}",
        f"Güncelleme zamanı: {state.updated_at}",
    ]

    if state.error:
        info_lines.append(f"hata: [red]{state.error}[/red]")

    if state.artifacts:
        info_lines.append(f"Ürün sayısı: [dim]{len(state.artifacts)}[/dim]")

    console.print(
        Panel(
            "\n".join(info_lines),
            title="📋Görev ayrıntıları",
            border_style="cyan",
        )
    )

    if verbose and state.steps:
        console.print("\n[bold]Yürütme adımları:[/bold]")
        for i, step in enumerate(state.steps, 1):
            console.print(f"  {i}. [{step.timestamp[11:19]}] {step.step}")
            if step.result:
                result_display = (
                    step.result[:100] + "..."
                    if len(str(step.result)) > 100
                    else step.result
                )
                console.print(f"     → {result_display}")


@app.command("pause")
def task_pause(
    task_id: str = typer.Argument(..., help="GörevID"),
) -> None:
    """
Görevi duraklat

Örnek:
        omc task pause abc123
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗Görev mevcut değil: {task_id}[/red]")
        raise typer.Exit(1)

    if state.status == TaskStatus.PAUSED:
        console.print("[yellow]Görev zaten askıya alındı[/yellow]")
        return

    if state.status not in (TaskStatus.RUNNING, TaskStatus.PENDING):
        console.print(f"[red]❗Duraklatamıyorum:Mevcut durum:{state.status.value}[/red]")
        raise typer.Exit(1)

    if pause_task(task_id):
        console.print(f"[green]✓Görev duraklatıldı: {task_id}[/green]")
        console.print(f"geçerli adım: {state.current_step or 'hiçbiri'}")
    else:
        console.print("[red]❗Askıya alma başarısız oldu[/red]")
        raise typer.Exit(1)


@app.command("resume")
def task_resume(
    task_id: str = typer.Argument(..., help="GörevID"),
) -> None:
    """
kurtarma görevi

Örnek:
        omc task resume abc123
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗Görev mevcut değil: {task_id}[/red]")
        raise typer.Exit(1)

    if state.status != TaskStatus.PAUSED:
        console.print(
            f"[yellow]Görev askıya alınmış durumda değil (şu anda: {state.status.value})[/yellow]"
        )
        return

    if resume_task(task_id):
        console.print(f"[green]✓Görev devam ettirildi: {task_id}[/green]")
        console.print(f"  Kesme noktasından devam: {state.current_step or 'Görev başlıyor'}")
    else:
        console.print("[red]❗Kurtarma başarısız oldu[/red]")
        raise typer.Exit(1)


@app.command("delete")
def task_delete(
    task_id: str = typer.Argument(..., help="GörevID"),
    force: bool = typer.Option(False, "--force", "-f", help="silmeye zorla"),
) -> None:
    """
Görevi sil

Örnek:
        omc task delete abc123
        omc task delete abc123 -f
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗Görev mevcut değil: {task_id}[/red]")
        raise typer.Exit(1)

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(
            f"Silme görevini onayla[cyan]{task_id}[/cyan](durum: {state.status.value})?"
        ):
            console.print("[dim]İptal edildi[/dim]")
            return

    if delete_task(task_id):
        console.print(f"[green]✓Fiyatı girin: {task_id}[/green]")
    else:
        console.print("[red]❗Silinemedi[/red]")
        raise typer.Exit(1)
