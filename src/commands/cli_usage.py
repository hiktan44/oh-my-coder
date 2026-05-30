from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
omc usageEmir-Kullanım istatistikleri ve izleme

Üç dosyadan birleştirildi:
- cli_stats.py -Proje dosyası istatistikleri
- cli_trace.py - AgentYürütme kaydı takibi
- cli_memory.py -Hiyerarşik bellek yönetimi

kullanım:
    omc usage stats [PATH]— Proje dosyalarının sayısını sayın
    omc usage trace list— Son zamanları listelesessionVetrace
    omc usage trace show <agent>- bir gösterAgentDetaylı yürütme süreci
    omc usage trace agents— akımı göstersessionhepsindenAgent
    omc usage trace latest— en sonuncuyu göstersession
    omc usage memory tier0 — GörüntüleTier0 çekirdek bellek (< 500 token)
    omc usage memory tier1 — GörüntüleTier1 Seçilmiş Anılar (< 2000 token)
    omc usage memory summaryDüşünce zinciri başladı
    omc usage memory stats— Bellek istatistiklerini görüntüleyin (öğe sayısı,tokensayı)
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Forward reference for FileNode (defined in cli.py)
try:
    from src.commands.cli import FileNode
except ImportError:
    # Type checking only
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from src.commands.cli import FileNode

import click
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ============================================================================
# Statsalt komut (dancli_stats.py)
# ============================================================================


def _get_count_files():
    """Gecikmeli içe aktarmacount_filesprogramlamastatsModül uyumluluk sorunları"""
    from src.stats import count_files
    return count_files


def stats_command(
    path: str = ".",
    output_json: bool = False,
    exclude_dirs: tuple = (),
    exclude_files: tuple = (),
    exclude_extensions: tuple = (),
    max_depth: Optional[int] = None,
    follow_symlinks: bool = False,
    sort_by: str = "count",
) -> None:
    """Proje dosyalarının sayısını sayın.

    PATHGeçerli dizine varsayılan olan, sayılacak proje kök dizininin yoludur.
    """
    count_files = _get_count_files()
    result = count_files(
        root_path=path,
        exclude_dirs=set(exclude_dirs),
        exclude_files=set(exclude_files),
        exclude_extensions=set(exclude_extensions),
        max_depth=max_depth,
        follow_symlinks=follow_symlinks,
    )

    if output_json:
        data = {
            "total_files": result.total_files,
            "total_dirs": result.total_dirs,
            "total_size": result.total_size,
            "by_type": {k: v.to_dict() for k, v in result.by_type.items()},
            "by_directory": result.by_directory,
            "errors": result.errors,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        console = Console()
        console.print(f"📊Proje istatistikleri: {path}")
        console.print(f"toplam dosya sayısı: {result.total_files}")
        console.print(f"Toplam dizin sayısı: {result.total_dirs}")
        console.print(f"toplam boyut: {result.total_size:,}bayt")
        if result.by_type:
            console.print("\n📁Türe göre sınıflandırılmış:")
            sorted_types = sorted(
                result.by_type.items(),
                key=lambda x: x[1].count,
                reverse=True,
            )
            for ext, stats in sorted_types:
                console.print(
                    f"  {ext or '(uzatma yok)'}: {stats.count}dosyalar, {stats.size:,}bayt"
                )
        if result.errors:
            console.print(f"\n⚠️ {len(result.errors)}hatalar:", err=True)
            for error in result.errors:
                console.print(f"  {error}", err=True)


# ============================================================================
# Tracealt komut (dancli_trace.py)
# ============================================================================

console_trace = Console()


def _get_store():
    """Gecikmeli içe aktarmaTraceStore"""
    from src.agents.transparency import TraceStore

    return TraceStore.get_instance()


def trace_list(
    session: str = None,
    limit: int = 20,
) -> None:
    """Son yürütme kayıtlarını listele"""
    store = _get_store()
    sessions = [session] if session else store.list_sessions()[:limit]

    if not sessions:
        console_trace.print("[dim]Henüz yürütme kaydı yok[/dim]")
        return

    for sid in sessions:
        traces = store.list_traces(sid)
        if not traces:
            continue
        console_trace.print(f"\n[bold cyan]Session: {sid}[/bold cyan] ({len(traces)}kayıtlar)")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="green")
        table.add_column("durum", style="yellow")
        table.add_column("zaman tükeniyor", style="blue")
        table.add_column("başlangıç ​​zamanı", style="dim")
        table.add_column("özet", style="white")
        for t in traces[:10]:
            duration = f"{t.get('total_duration_ms', 0) / 1000:.2f}s"
            started = t.get("started_at", "")[:19]
            status = t.get("status", "unknown")
            summary = t.get("output_summary", "")[:40]
            error = t.get("error", "")
            table.add_row(
                t.get("agent_name", ""),
                status,
                duration,
                started,
                (summary + " ❌ " + error[:20]) if error else summary,
            )
        console_trace.print(table)


def trace_show(
    agent: str,
    session: str = None,
) -> None:
    """bir gösterAgentDetaylı yürütme süreci"""
    store = _get_store()
    sid = session or store.get_latest_session()
    if not sid:
        console_trace.print("[red]Mevcut değilsession[/red]")
        raise typer.Exit(1)

    trace_data = store.get_trace(sid, agent)
    if not trace_data:
        #Bulanık eşleştirmeyi deneyin
        all_agents = store.get_all_agents_in_session(sid)
        if agent in all_agents:
            trace_data = store.get_trace(sid, agent)
        else:
            #bulanık eşleştirme
            matches = [a for a in all_agents if agent.lower() in a.lower()]
            if matches:
                trace_data = store.get_trace(sid, matches[0])
                console_trace.print(f"[dim]Görev yürütmeyle ilgili komutlar: {matches[0]}[/dim]")
            else:
                console_trace.print(f"[red]bulunamadıAgent '{agent}'kayıtlar[/red]")
                if all_agents:
                    console_trace.print("[dim]MevcutAgent:[/dim] " + ", ".join(all_agents))
                raise typer.Exit(1)

    # Header
    console_trace.print(
        Panel(
            f"[green]Agent:[/green] {trace_data['agent_name']}\n"
            f"[green]Session:[/green] {trace_data['session_id']}\n"
            f"[green]durum:[/green] {trace_data['status']}\n"
            f"[green]Harcanan toplam süre:[/green] {trace_data['total_duration_ms'] / 1000:.2f}s\n"
            f"[green]başlangıç:[/green] {trace_data['started_at'][:19]}\n"
            f"[green]Sona ermek:[/green] {trace_data['ended_at'][:19]}",
            title=f"Trace: {trace_data['agent_name']}",
            border_style="cyan",
        )
    )

    if trace_data.get("error"):
        console_trace.print(f"[red]hata: {trace_data['error']}[/red]")

    # Events timeline
    events = trace_data.get("events", [])
    if not events:
        console_trace.print("[dim]Hiçbir etkinlik günlüğe kaydedilmedi[/dim]")
        return

    for _i, ev in enumerate(events):
        etype = ev.get("type", "")
        ts = ev.get("timestamp", "")[11:23]  # HH:MM:SS.mmm
        desc = ev.get("description", "")
        dur_ms = ev.get("duration_ms", 0)
        dur_str = f"[dim]@{dur_ms / 1000:.3f}s[/dim]"

        #Etiket rengini yazın
        color_map = {
            "start": "bold green",
            "end": "bold red",
            "read_file": "cyan",
            "write_file": "yellow",
            "call_api": "magenta",
            "run_command": "blue",
            "error": "bold red",
            "thinking": "white",
            "metadata": "dim",
        }
        style = color_map.get(etype, "white")
        label = f"[{style}]{etype:12s}[/{style}]"

        details = ev.get("details", {})
        extra = ""
        if details:
            if "path" in details:
                extra = f"  → {details['path']}"
            elif "command" in details:
                extra = f"  → {details['command'][:60]}"
            elif "model" in details:
                extra = (
                    f"  → model={details['model']} tokens={details.get('tokens', 0)}"
                )

        console_trace.print(f"  {ts} {dur_str} {label} {desc}{extra}")

        preview = ev.get("output_preview", "")
        if preview:
            console_trace.print(f"         [dim]│ {preview[:80]}[/dim]")


def trace_agents(
    session: str = None,
) -> None:
    """Geçerli olanı göstersessionhepsindenAgent"""
    store = _get_store()
    sid = session or store.get_latest_session()
    if not sid:
        console_trace.print("[red]Mevcut değilsession[/red]")
        raise typer.Exit(1)
    agents = store.get_all_agents_in_session(sid)
    if not agents:
        console_trace.print("[dim]HiçbiriAgentKayıt[/dim]")
    else:
        console_trace.print(f"[cyan]Session {sid}[/cyan]ile ilgiliAgents:")
        for a in agents:
            console_trace.print(f"  • {a}")


def trace_latest() -> None:
    """En sonuncuyu göstersession"""
    store = _get_store()
    sid = store.get_latest_session()
    if not sid:
        console_trace.print("[dim]Henüz yürütme kaydı yok[/dim]")
        raise typer.Exit(0)
    console_trace.print(f"[green]güncelSession: {sid}[/green]")
    trace_list(session=sid, limit=10)


# ============================================================================
# Memoryalt komut (dancli_memory.py)
# ============================================================================

console_memory = Console()


def _get_manager(project_path: Path):
    """başlatmaMemoryManager"""
    from src.memory.manager import MemoryManager

    return MemoryManager.from_project(project_path)


def memory_tier0(
    project_path: Path = ".",
) -> None:
    """
    🧠Kontrol etmekTier0 çekirdek bellek (< 500 token)

sistem içinPromptMinimum bellek enjekte edildi.
    """
    manager = _get_manager(Path(project_path).resolve())
    tier0 = manager.get_tier0_summary()

    tokens = manager.count_tokens(tier0)

    console_memory.print(
        Panel(
            tier0 if tier0.strip() else "[dim](hükümsüz)[/dim]",
            title=f"🧠 Tier0 çekirdek hafıza[{tokens} tokens]",
            border_style="cyan",
        )
    )


def memory_tier1(
    project_path: Path = ".",
) -> None:
    """
    📋Kontrol etmekTier1 Seçilmiş Anılar (< 2000 token)

Projeye özgü bilgiler, ortak komutlar, öğrenilen önemli dersler.
    """
    manager = _get_manager(Path(project_path).resolve())
    tier1 = manager.get_tier1_summary()

    tokens = manager.count_tokens(tier1)

    console_memory.print(
        Panel(
            tier1 if tier1.strip() else "[dim](hükümsüz)[/dim]",
            title=f"📋 Tier1 Seçilmiş Anılar[{tokens} tokens]",
            border_style="green",
        )
    )


def memory_summary(
    project_path: Path = ".",
) -> None:
    """
    📦Tam hafıza özetini görün (TierKomutu düzenle

Tüm projeler, tüm öğrenme kayıtları, tüm tercihler.
    """
    manager = _get_manager(Path(project_path).resolve())
    archive = manager.get_tier2_archive()

    tokens = manager.count_tokens(archive)

    console_memory.print(
        Panel(
            archive[:5000]
            + (
                f"\n\n[dim]...(Toplamı göstermek için kısaltılmıştır{tokens} tokens)[/dim]"
                if len(archive) > 5000
                else ""
            ),
            title=f"📦 Tier2 tam arşiv[{tokens} tokens]",
            border_style="yellow",
        )
    )


def memory_stats(
    project_path: Path = ".",
) -> None:
    """
    📊Bellek istatistiklerini görüntüle

Proje sayısı, öğrenme kaydı sayısı, her katmantokentüketim.
    """
    manager = _get_manager(Path(project_path).resolve())
    stats = manager.get_memory_stats()

    table = Table(title="📊Yapılandırma dosyası bulunamadı")
    table.add_column("dizin", style="cyan")
    table.add_column("değer", style="green")

    table.add_row("Öğe sayısı", str(stats["projects_count"]))
    table.add_row("Öğrenme kayıtlarının sayısı", str(stats["learnings_count"]))
    table.add_row("Tier 0 tokens", str(stats["tier0_tokens"]))
    table.add_row("Tier 1 tokens", str(stats["tier1_tokens"]))

    if stats["categories"]:
        table.add_row("sınıflandırma", ", ".join(stats["categories"]))

    console_memory.print(table)


# ============================================================================
# Typer Apptanım
# ============================================================================

app = typer.Typer(
    name="usage",
    help="Kullanım istatistikleri ve izleme- stats/trace/memory",
    no_args_is_help=True,
)

# Statsalt komut
stats_app = typer.Typer(name="stats", help="Proje dosyası istatistikleri")
app.add_typer(stats_app, name="stats")


@stats_app.callback(invoke_without_command=True)
def stats_main(
    ctx: typer.Context,
    path: str = typer.Argument(
        ".",
        help="Proje yolu",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="inceleme raporuJSONÇıkış istatistikleri sonuçlarını biçimlendirme",
    ),
    exclude_dir: list[str] = typer.Option(
        [],
        "--exclude-dir",
        help="Hariç tutulan ek dizin adları (birden çok kez belirtilebilir)",
    ),
    exclude_file: list[str] = typer.Option(
        [],
        "--exclude-file",
        help="Hariç tutulan ek dosya adları (birden çok kez belirtilebilir)",
    ),
    exclude_ext: list[str] = typer.Option(
        [],
        "--exclude-ext",
        help="Dağıtım başarısız oldu",
    ),
    max_depth: Optional[int] = typer.Option(
        None,
        "--max-depth",
        help="maksimum yineleme derinliği",
    ),
    follow_symlinks: bool = typer.Option(
        False,
        "--follow-symlinks",
        help="Sembolik bağlantıları takip edin",
    ),
    sort: str = typer.Option(
        "count",
        "--sort",
        help="Şuna göre sırala (yalnızcaJSONçıktı geçerlidir)",
    ),
) -> None:
    """Proje dosyalarının sayısını sayın"""
    if ctx.invoked_subcommand is None:
        stats_command(
            path=path,
            output_json=json_output,
            exclude_dirs=tuple(exclude_dir),
            exclude_files=tuple(exclude_file),
            exclude_extensions=tuple(exclude_ext),
            max_depth=max_depth,
            follow_symlinks=follow_symlinks,
            sort_by=sort,
        )


# Tracealt komut
trace_app = typer.Typer(name="trace", help="Kontrol etmekAgentYürütme kaydı")
app.add_typer(trace_app, name="trace")


@trace_app.command("list")
def trace_list_cmd(
    session: str = typer.Option(None, "--session", "-s", help="Belirtsession ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Ekran numarası"),
) -> None:
    """Son yürütme kayıtlarını listele"""
    trace_list(session=session, limit=limit)


@trace_app.command("show")
def trace_show_cmd(
    agent: str = typer.Argument(..., help="Agentisim"),
    session: str = typer.Option(None, "--session", "-s", help="Belirtsession ID"),
) -> None:
    """bir gösterAgentDetaylı yürütme süreci"""
    trace_show(agent=agent, session=session)


@trace_app.command("agents")
def trace_agents_cmd(
    session: str = typer.Option(None, "--session", "-s", help="Belirtsession ID"),
) -> None:
    """Geçerli olanı göstersessionhepsindenAgent"""
    trace_agents(session=session)


@trace_app.command("latest")
def trace_latest_cmd() -> None:
    """En sonuncuyu göstersession"""
    trace_latest()


# Memoryalt komut
memory_app = typer.Typer(name="memory", help="Hiyerarşik bellek yönetimi")
app.add_typer(memory_app, name="memory")


@memory_app.command("tier0")
def memory_tier0_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
) -> None:
    """
    🧠Kontrol etmekTier0 çekirdek bellek (< 500 token)

sistem içinPromptMinimum bellek enjekte edildi.
    """
    memory_tier0(project_path=project_path)


@memory_app.command("tier1")
def memory_tier1_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
) -> None:
    """
    📋Kontrol etmekTier1 Seçilmiş Anılar (< 2000 token)

Projeye özgü bilgiler, ortak komutlar, öğrenilen önemli dersler.
    """
    memory_tier1(project_path=project_path)


@memory_app.command("summary")
def memory_summary_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
) -> None:
    """
    📦Tam hafıza özetini görün (TierKomutu düzenle

Tüm projeler, tüm öğrenme kayıtları, tüm tercihler.
    """
    memory_summary(project_path=project_path)


@memory_app.command("stats")
def memory_stats_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
) -> None:
    """
    📊Bellek istatistiklerini görüntüle

Proje sayısı, öğrenme kaydı sayısı, her katmantokentüketim.
    """
    memory_stats(project_path=project_path)


# ============================================================================
# Compactalt komut (dancli_compact.py)
# ============================================================================

console_compact = Console()


@app.command("stats")
def compact_stats(
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
) -> None:
    """
    📊Geçerli oturumun sıkıştırma istatistiklerini görüntüle

İçeriği görüntüle:
    -Toplam sıkıştırma sayısı
    -kaydedilditokensayı
    -Temizlenen mesaj sayısı
    -Kopyaları kaldırmak için yapılan araç çağrılarının sayısı
    -Temizlenen geçmiş hataların sayısı
    """
    from src.memory.manager import MemoryManager
    manager = MemoryManager.from_project(project_path.resolve())
    stats = manager.compact_stats

    table = Table(
        title="🗜️ AutoCompactistatistikler", show_header=True, header_style="bold cyan"
    )
    table.add_column("dizin", style="dim")
    table.add_column("değer", justify="right")

    table.add_row("Sıkıştırma süreleri", f"{stats['total_compact_count']}")
    table.add_row("kaydetmektoken", f"{stats['total_tokens_saved']:,}")
    table.add_row("varsayılan model olarak model", f"{stats['total_messages_removed']:,}")
    table.add_row("Yinelenenleri kaldırtool_call", f"{stats['total_deduplicated']}")
    table.add_row("Hata mesajlarını temizleyin", f"{stats['total_errors_removed']}")

    console_compact.print(table)

    if stats["total_compact_count"] == 0:
        console_compact.print("\n[dim]Hiçbir sıkıştırma yapılmadı ve henüz istatistik yok.[/dim]")


@app.command("sweep")
def compact_sweep(
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    since_last_user: bool = typer.Option(
        False,
        "--since-last-user",
        help="Sıkıştırma son kullanıcı mesajından başlar (önceki mesajlar atılır)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Yalnızca sonuçlar görüntülenir, gerçek bir sıkıştırma yapılmaz"),
) -> None:
    """
    🧹Sıkıştırmayı manuel olarak tetikleyin (sweep)

İsteğe bağlı bayraklar:
      --since-last-userTemizlemeye son kullanıcı mesajından başlayın
      --dry-runYalnızca sonuçlar görüntülenir, gerçek bir sıkıştırma yapılmaz
    """
    from src.memory.manager import MemoryManager
    manager = MemoryManager.from_project(project_path.resolve())
    session = manager.get_latest_session()

    if session is None:
        console_compact.print("[red]Aktif oturum bulunamadı.[/red]")
        raise typer.Exit(1)

    if since_last_user:
        console_compact.print("[cyan]Son kullanıcı mesajından kırp...[/cyan]")
        #Sonuncuyu buldumuserbilgi
        messages = session.messages
        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "user":
                last_user_idx = i
                break
        if last_user_idx is not None and last_user_idx > 0:
            session.messages = messages[last_user_idx:]
            console_compact.print(
                f"[green]Şuraya kırpıldı:{last_user_idx + 1}mesajlar (toplam{len(messages)}şerit)[/green]"
            )
        else:
            console_compact.print("[yellow]Daha eski kullanıcı mesajı bulunamadı, kırpmaya gerek yok.[/yellow]")
            raise typer.Exit(0)

    if dry_run:
        #Yalnızca kontrol edin, sıkıştırma yok
        result = manager.auto_compact_check(session, force=False, since_last_user=False)
        if result.compacted:
            console_compact.print(
                f"[yellow]Dry-run:sıkıştıracak{result.messages_removed}Basit mod"
                f"Yaklaşık tasarruf edin.{result.tokens_saved} tokens[/yellow]"
            )
        else:
            console_compact.print("[dim]Dry-run:Mevcut kullanım eşiğe ulaşmadı ve herhangi bir sıkıştırma gerekmiyor.[/dim]")
            console_compact.print(f"Kullanım kayıtlarını yükletoken: {result.tokens_before}")
        raise typer.Exit(0)

    result = manager.auto_compact_check(session, force=True)
    manager.save_session(session)

    if result.compacted:
        console_compact.print(
            f"[green]✅Sıkıştırma tamamlandı:Temizlemek{result.messages_removed}Basit mod"
            f"kaydetmek~{result.tokens_saved} tokens[/green]"
        )
    else:
        console_compact.print("[yellow]⚠️Sıkıştırma tetiklenmiyor (usage_ratio < threshold).[/yellow]")
        console_compact.print(f"Kullanım kayıtlarını yükletoken: {result.tokens_before}")


# ============================================================================
# Thoughtalt komut (dancli_thought.py)
# ============================================================================

console_thought = Console()


@app.command("start")
def thought_start(
    task: str = typer.Argument(..., help="Görev açıklaması"),
    agent: str = typer.Option("assistant", "--agent", "-a", help="Agentisim"),
) -> None:
    """Düşünce zincirini kaydetmeye başlayın"""
    from src.core.chain_of_thought import ChainOfThoughtRecorder
    recorder = ChainOfThoughtRecorder()
    chain = recorder.start_chain(task, agent)

    console_thought.print("[green]✅Düşünce zinciri başladı[/green]")
    console_thought.print(f"[dim]ID: {chain.chain_id}[/dim]")
    console_thought.print(f"Görev: {chain.task_description}")
    console_thought.print("\n[dim]Aşağıdaki komutu kullanarak adımı ekleyin:[/dim]")
    console_thought.print(f"  omc thought step {chain.chain_id} -t analysis -d 'analiz etmek...'")


@app.command("step")
def thought_step(
    chain_id: str = typer.Argument(..., help="Düşünce zinciriID"),
    step_type: str = typer.Option("analysis", "--type", "-t", help="adım türü"),
    description: str = typer.Option(..., "--desc", "-d", help="Adım açıklaması"),
    reasoning: str = typer.Option("", "--reasoning", "-r", help="muhakeme süreci"),
    conclusion: str = typer.Option("", "--conclusion", "-c", help="Sonuç olarak"),
    confidence: str = typer.Option("medium", "--confidence", help="Kendinden emin"),
) -> None:
    """Çıkarım adımı ekle"""
    from src.core.chain_of_thought import (
        ChainOfThoughtRecorder,
        ConfidenceLevel,
        ReasoningStepType,
    )
    recorder = ChainOfThoughtRecorder()

    try:
        st = ReasoningStepType(step_type)
    except ValueError:
        console_thought.print(f"[red]Geçersiz adım türü: {step_type}[/red]")
        console_thought.print(f"Mevcut: {[t.value for t in ReasoningStepType]}")
        raise typer.Exit(1)

    try:
        conf = ConfidenceLevel(confidence)
    except ValueError:
        conf = ConfidenceLevel.MEDIUM

    step = recorder.add_step(
        chain_id=chain_id,
        step_type=st,
        description=description,
        reasoning=reasoning or description,
        conclusion=conclusion,
        confidence=conf,
    )

    if step:
        console_thought.print(f"[green]✅Adım eklendi[/green] [{step.step_id}]")
    else:
        console_thought.print(f"[red]Düşünce zinciri mevcut değil: {chain_id}[/red]")
        raise typer.Exit(1)


@app.command("complete")
def thought_complete(
    chain_id: str = typer.Argument(..., help="Düşünce zinciriID"),
    conclusion: str = typer.Option("", "--conclusion", "-c", help="nihai sonuç"),
) -> None:
    """Düşünce zincirini tamamla"""
    from src.core.chain_of_thought import ChainOfThoughtRecorder
    recorder = ChainOfThoughtRecorder()
    recorder.complete_chain(chain_id, conclusion)
    console_thought.print(f"[green]✅Düşünce zinciri tamamlandı[/green] {chain_id}")


@app.command("show")
def thought_show(
    chain_id: str = typer.Argument(..., help="Düşünce zinciriID"),
    format: str = typer.Option(
        "text", "--format", "-f", help="Biçim: text/html/mermaid"
    ),
) -> None:
    """Düşünce zincirini görüntüle"""
    import tempfile

    from src.core.chain_of_thought import (
        ChainOfThoughtRecorder,
        visualize_chain,
    )
    recorder = ChainOfThoughtRecorder()
    chain = recorder.get_chain(chain_id)

    if not chain:
        console_thought.print(f"[red]Düşünce zinciri mevcut değil: {chain_id}[/red]")
        raise typer.Exit(1)

    output = visualize_chain(chain, format)

    if format == "html":
        #Geçici dosyaya kaydet
        output_path = os.path.join(tempfile.gettempdir(), f"chain_{chain_id}.html")
        with open(output_path, "w") as f:
            f.write(output)
        console_thought.print(f"[green]HTMLkaydedildi:[/green] {output_path}")
    else:
        console_thought.print(output)


@app.command("list")
def thought_list(
    agent: str = typer.Option(None, "--agent", "-a", help="buna göreAgentfiltre"),
) -> None:
    """Düşünce zincirini listeleyin"""
    from src.core.chain_of_thought import ChainOfThoughtRecorder
    recorder = ChainOfThoughtRecorder()
    chains = recorder.list_chains(agent)

    if not chains:
        console_thought.print("[dim]düşünce zinciri yok[/dim]")
        return

    table = Table(title="Düşünce zinciri listesi")
    table.add_column("ID", style="cyan")
    table.add_column("Görev", style="green")
    table.add_column("Agent", style="blue")
    table.add_column("adım sayısı", justify="right")
    table.add_column("durum", style="yellow")

    for c in chains:
        table.add_row(
            c.chain_id,
            c.task_description[:40],
            c.agent_name,
            str(len(c.steps)),
            c.status,
        )

    console_thought.print(table)


# ============================================================================
# Contextalt komut (dancli_context.py)
# ============================================================================

console_context = Console()

#Döngüsel bağımlılıklardan kaçınmak için içe aktarmayı geciktirin

def _get_scanner():
    """Gecikmeli içe aktarmaWorkspaceScanner"""
    from src.context import WorkspaceScanner
    return WorkspaceScanner


def _get_browser_awareness():
    """Gecikmeli içe aktarmaBrowserAwareness"""
    from src.context import BrowserAwareness
    return BrowserAwareness


context_app = typer.Typer(
    name="context",
    help="Çalışma dizini bağlam yönetimi - dosyaları tarayın, özetleri alın, tarayıcı farkındalığı",
    add_completion=False,
    no_args_is_help=True,
)

app.add_typer(context_app, name="context")


@context_app.command("scan")
def context_scan(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="Proje yolu",
    ),
    depth: int = typer.Option(3, "--depth", "-d", help="Tarama derinliği (maksimum yineleme düzeyi sayısı)"),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="inceleme raporuJSONÇıkışı formatla (program ayrıştırma için uygun)"
    ),
) -> None:
    """
Geçerli çalışma dizinini tarayın ve bir dosya ağacı yapısı oluşturun

Örnek:
        omc usage context scan
        omc usage context scan -p /path/to/project -d 2
        omc usage context scan --depth 5
        omc usage context scan --json
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    scanner = _get_scanner()(project_path.resolve())

    #tarama gerçekleştir
    tree = scanner.scan(max_depth=depth)
    stats = scanner._scan_stats

    if json_output:
        import json

        console.print(
            json.dumps(
                {
                    "tree": tree.to_dict(),
                    "stats": {
                        "files_scanned": stats["files_scanned"],
                        "dirs_scanned": stats["dirs_scanned"],
                        "bytes_scanned": stats["bytes_scanned"],
                        "errors": stats["errors"],
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    #Dosya ağacını oluştur
    lines = scanner._render_tree(tree, prefix="", is_last=True)
    tree_str = "\n".join(lines)

    #İstatistikleri biçimlendir
    size_str = scanner._format_size(stats["bytes_scanned"])

    console.print(
        Panel(
            f"[bold cyan]{project_path.name}[/bold cyan] ({project_path})\n"
            f"[dim]derinlik: {depth} | "
            f"belge: {stats['files_scanned']} | "
            f"İçindekiler: {stats['dirs_scanned']} | "
            f"boyut: {size_str}[/dim]",
            title="📁Çalışma dizini taraması",
            border_style="cyan",
        )
    )

    console.print(f"\n[white]{tree_str}[/white]\n")

    #Hata mesajı
    if stats["errors"]:
        console.print(f"[yellow]⚠️  {len(stats['errors'])}hatalar[/yellow]")
        for err in stats["errors"][:5]:
            console.print(f"  [dim]{err}[/dim]")
        if len(stats["errors"]) > 5:
            console.print(f"  [dim]...yaygın{len(stats['errors'])}bireysel[/dim]")


@context_app.command("summary")
def context_summary(
    path: str = typer.Argument(..., help="Dosya veya dizin yolu"),
    max_lines: int = typer.Option(50, "--lines", "-n", help="Okunan maksimum satır sayısı"),
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="Proje kök dizini (göreceli yolları hesaplamak için kullanılır)",
    ),
) -> None:
    """
Dosya özeti oluştur

Aşağıdakiler de dahil olmak üzere belirtilen dosyanın içeriğinin bir özetini görüntüler:
    -Temel bilgiler (boyut, değişiklik zamanı)
    -Kod yapısı (içe aktarmalar, sınıflar, işlevler)
    -İçerik önizlemesi

Örnek:
        omc usage context summary src/main.py
        omc usage context summary config.yaml -n 100
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    console = Console()
    scanner = _get_scanner()(project_path.resolve())

    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = project_path / file_path

    if not file_path.exists():
        console.print(f"[red]✗Dosya mevcut değil: {file_path}[/red]")
        raise typer.Exit(1)

    result = scanner.get_file_summary(file_path, max_lines=max_lines)

    #Özet sonuçları ayrıştır
    lines = result.split("\n")
    header_lines = []
    content_lines = []
    in_content = False

    for line in lines:
        if line.startswith("---"):
            in_content = True
            continue
        if in_content:
            content_lines.append(line)
        else:
            header_lines.append(line)

    header = "\n".join(header_lines)
    content = "\n".join(content_lines)

    #Sözdizimi vurgulaması için dilleri algıla
    lang = None
    for line in header_lines:
        if line.startswith("["):
            lang = line.split("]")[0][1:]
            break

    console.print(Panel(header, title=f"📄 {file_path.name}", border_style="green"))

    if content_lines:
        #Kod ise, sözdizimi vurgulamayı deneyin
        if lang and lang not in ("unknown", "markdown", "rst"):
            try:
                syntax = Syntax(content, lang, theme="monokai", line_numbers=True)
                console.print(syntax)
            except Exception:
                console.print(content)
        else:
            console.print(content)


@context_app.command("browser")
def context_browser(
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Tarayıcı değişikliklerini sürekli izleyin (Ctrl+Cçıkış yapmak)"
    ),
    interval: int = typer.Option(5, "--interval", "-i", help="İzleme aralığı (saniye)"),
) -> None:
    """
Tarayıcının geçerli içeriğini alın

Geçerli tarayıcı sekmesinin başlığını okuyun,URLve içerik özeti.
Kurulum gerektirirPlaywrightveyaSelenium.

Örnek:
        omc usage context browser
        omc usage context browser --watch
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    awareness = _get_browser_awareness()()

    async def get_and_display():
        ctx = await awareness.get_current_tab()

        if not ctx.available:
            console.print(
                Panel(
                    "[yellow]Tarayıcı içeriği mevcut değil[/yellow]\n\n"
                    "[dim]Olası nedenler:\n"
                    "  1.Kurulu değilPlaywrightveyaSelenium\n"
                    "  2.Etkin tarayıcı sekmesi yok\n"
                    "  3.Tarayıcı reddedildiCDPbağlamak[/dim]",
                    title="🌐tarayıcı bağlamı",
                    border_style="yellow",
                )
            )
            return

        #Bağlantı listesini göster
        links_text = ""
        if ctx.links:
            links_text = "\n\n[cyan]Bağlantı önizlemesi:[/cyan]\n"
            for link in ctx.links[:10]:
                links_text += f"  • {link}\n"

        console.print(
            Panel(
                f"[bold]{ctx.title}[/bold]\n"
                f"[dim]{ctx.url}[/dim]\n\n"
                f"[green]İçerik özeti:[/green]\n"
                f"{ctx.content[:500]}"
                + ("..." if len(ctx.content) > 500 else "")
                + links_text,
                title="🌐tarayıcı bağlamı",
                border_style="green",
            )
        )

    async def watch_loop():
        console.print("[dim]Tarayıcınızı sürekli izlemek için tuşuna basın.Ctrl+Cçıkış yapmak...[/dim]\n")
        try:
            while True:
                console.clear()
                await get_and_display()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            console.print("\n[dim]bomba[/dim]")

    if watch:
        asyncio.run(watch_loop())
    else:
        asyncio.run(get_and_display())


@context_app.command("tree")
def context_tree(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="Proje yolu",
    ),
    depth: int = typer.Option(3, "--depth", "-d", help="Ekran derinliği"),
    filter_ext: str = typer.Option(
        None, "--ext", "-e", help="Yalnızca belirli uzantıları göster (ör.py, js)"
    ),
) -> None:
    """
Dosya ağacını göster

Proje dizinini aşağıdakine benzer bir ağaç yapısında görüntüleyintreeEmir.

Örnek:
        omc usage context tree
        omc usage context tree -p src -d 2
        omc usage context tree --ext py
    """
    from rich.console import Console
    from rich.tree import Tree

    console = Console()

    scanner = _get_scanner()(project_path.resolve())
    tree_node = scanner.scan(max_depth=depth)

    def build_rich_tree(node: FileNode, filter_ext: Optional[str] = None) -> Tree:
        """inşa etmekrich Tree"""
        label = f"[cyan]{node.name}[/cyan]"
        if node.language:
            label += f" [dim][[{node.language}]][/dim]"
        if node.size > 0 and not node.is_dir:
            label += f" [dim]({scanner._format_size(node.size)})[/dim]"

        t = Tree(label)

        if node.is_dir and node.children:
            for child in node.children:
                if filter_ext:
                    ext = filter_ext.lstrip(".").lower()
                    child_lang = scanner.LANGUAGE_EXTENSIONS.get(f".{ext}")
                    if child.is_dir or child.language == child_lang:
                        t.add(build_rich_tree(child, filter_ext))
                else:
                    t.add(build_rich_tree(child, filter_ext))

        return t

    console.print(
        build_rich_tree(tree_node, filter_ext),
        soft_wrap=True,
    )


@context_app.command("stats")
def context_stats(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="Proje yolu",
    ),
) -> None:
    """
Proje istatistiklerini göster

İstatistikler, dosya sayısını, kod satırlarını ve projedeki her dilin oranını içerir.

Örnek:
        omc usage context stats
        omc usage context stats -p /path/to/project
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    scanner = _get_scanner()(project_path.resolve())

    #İki kez tarayın (biri büyük derinlikle, diğeri küçük derinlikle)
    tree = scanner.scan(max_depth=10)

    #Her dildeki dosya ve satır sayısını sayın
    lang_stats: dict = {}

    def collect_stats(node: FileNode):
        if node.is_dir:
            for child in node.children:
                collect_stats(child)
        else:
            lang = node.language or "other"
            if lang not in lang_stats:
                lang_stats[lang] = {"files": 0, "lines": 0, "size": 0}

            lang_stats[lang]["files"] += 1
            lang_stats[lang]["size"] += node.size

            #Satırları say
            try:
                with open(node.path, encoding="utf-8", errors="replace") as f:
                    lang_stats[lang]["lines"] += sum(1 for _ in f if _.strip())
            except Exception:
                pass

    collect_stats(tree)

    #Dosya sayısına göre sırala
    sorted_langs = sorted(
        lang_stats.items(),
        key=lambda x: x[1]["files"],
        reverse=True,
    )

    #İstatistik tablosu
    table = Table(title="Dil istatistikleri")
    table.add_column("dil", style="cyan")
    table.add_column("belge", justify="right")
    table.add_column("Satır sayısı", justify="right")
    table.add_column("boyut", justify="right")

    total_files = sum(s["files"] for _, s in sorted_langs)
    total_lines = sum(s["lines"] for _, s in sorted_langs)
    total_size = sum(s["size"] for _, s in sorted_langs)

    for lang, s in sorted_langs[:15]:
        table.add_row(
            lang,
            str(s["files"]),
            f"{s['lines']:,}",
            scanner._format_size(s["size"]),
        )

    console.print(
        Panel(
            f"[cyan]proje:[/cyan] {project_path}\n"
            f"[cyan]belge:[/cyan] {total_files}bireysel\n"
            f"[cyan]Kod satırları:[/cyan] {total_lines:,}TAMAM\n"
            f"[cyan]toplam boyut:[/cyan] {scanner._format_size(total_size)}",
            title="📊Proje istatistikleri",
            border_style="green",
        )
    )
    console.print(table)


# ============================================================================
# Costalt komut (dancli_cost.py)
# ============================================================================

console_cost = Console()

#Yapılandırma yolu
_COST_CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
_COST_USAGE_FILE = _COST_CONFIG_DIR / "usage.json"
_COST_PRICES_FILE = _COST_CONFIG_DIR / "model_prices.json"

#Varsayılan model fiyatı (yuan/1k tokens)
_COST_DEFAULT_PRICES = {
    "deepseek-chat": {"prompt": 0.001, "completion": 0.002},
    "deepseek-coder": {"prompt": 0.001, "completion": 0.002},
    "gpt-4o": {"prompt": 0.036, "completion": 0.108},
    "gpt-4o-mini": {"prompt": 0.003, "completion": 0.012},
    "claude-3-opus": {"prompt": 0.105, "completion": 0.525},
    "claude-3-sonnet": {"prompt": 0.021, "completion": 0.105},
    "claude-3-haiku": {"prompt": 0.004, "completion": 0.02},
    "glm-4": {"prompt": 0.01, "completion": 0.01},
    "glm-4-flash": {"prompt": 0.0, "completion": 0.0},
    "qwen-turbo": {"prompt": 0.002, "completion": 0.006},
    "qwen-plus": {"prompt": 0.008, "completion": 0.02},
    "moonshot-v1": {"prompt": 0.006, "completion": 0.006},
    "hunyuan-lite": {"prompt": 0.0, "completion": 0.0},
    "hunyuan-standard": {"prompt": 0.0045, "completion": 0.005},
    "doubao-lite": {"prompt": 0.0003, "completion": 0.0006},
    "doubao-pro": {"prompt": 0.0008, "completion": 0.002},
    "minimax": {"prompt": 0.005, "completion": 0.005},
    "spark": {"prompt": 0.006, "completion": 0.006},
    "baichuan": {"prompt": 0.005, "completion": 0.005},
    "tiangong": {"prompt": 0.005, "completion": 0.005},
    "mimo": {"prompt": 0.002, "completion": 0.006},
    "ollama": {"prompt": 0.0, "completion": 0.0},
}


def _cost_load_prices() -> dict[str, dict[str, float]]:
    """Model fiyat yapılandırmasını yükle"""
    if _COST_PRICES_FILE.exists():
        try:
            with open(_COST_PRICES_FILE, encoding="utf-8") as f:
                custom_prices = json.load(f)
                return {**_COST_DEFAULT_PRICES, **custom_prices}
        except Exception:
            pass
    return _COST_DEFAULT_PRICES


def _cost_load_usage_data() -> list[dict[str, Any]]:
    """Kullanım kayıtlarını yükle"""
    if _COST_USAGE_FILE.exists():
        try:
            with open(_COST_USAGE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _cost_calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Arama başına maliyeti hesaplayın"""
    prices = _cost_load_prices()
    model_lower = model.lower()

    if model_lower in prices:
        p = prices[model_lower]
        return (prompt_tokens / 1000) * p["prompt"] + (completion_tokens / 1000) * p["completion"]

    for key, p in prices.items():
        if model_lower.startswith(key) or key in model_lower:
            return (prompt_tokens / 1000) * p["prompt"] + (completion_tokens / 1000) * p["completion"]

    return (prompt_tokens + completion_tokens) / 1000 * 0.01


def _cost_format_datetime(dt_str: str) -> str:
    """Tarih saatini biçimlendir"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str


def _cost_format_cost(cost: float) -> str:
    """Maliyet gösterimini biçimlendir"""
    if cost == 0:
        return "Free"
    elif cost < 0.01:
        return "< 0.01"
    else:
        return f"{cost:.3f}"


def _cost_list_models(optimizer) -> None:
    """Mevcut tüm modelleri listele"""
    models = optimizer.get_all_models()
    by_provider: dict = {}
    for m in models:
        provider = m["provider"]
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(m)

    for provider, model_list in by_provider.items():
        console_cost.print(f"\n### {provider.upper()}")
        for m in model_list:
            cost_bars = "💰" * m["cost"]
            console_cost.print(f"  {m['model']:30s} {cost_bars}")


@app.command("suggest")
def cost_suggest(
    task: str = typer.Argument("", help="Task description"),
    files: int = typer.Option(0, "--files", "-f", help="Number of files involved"),
    list_models: bool = typer.Option(False, "--list", "-l", help="List all available models"),
    prefer_local: bool = typer.Option(True, "--prefer-local/--no-local", help="Prefer local models"),
) -> None:
    """Recommend optimal model based on task complexity"""
    # Extract real bool from typer OptionInfo (OptionInfo is always truthy in Python)
    _files = files.default if hasattr(files, 'default') else files
    _list_models = list_models.default if hasattr(list_models, 'default') else list_models
    _prefer_local = prefer_local.default if hasattr(prefer_local, 'default') else prefer_local

    from src.agents.cost_optimizer import CostOptimizer

    optimizer = CostOptimizer(prefer_local=_prefer_local)

    if _list_models:
        _cost_list_models(optimizer)
        return

    if not task:
        console_cost.print("[yellow]Please enter a task description, e.g.:[/yellow]")
        console_cost.print("  omc cost suggest 'fix login bug'")
        console_cost.print("  omc cost suggest 'design new system architecture'")
        console_cost.print("  omc cost suggest --files 15 'implement payment'")
        return

    recommendation = optimizer.recommend(task, file_count=_files if _files > 0 else None)

    complexity_colors = {"low": "green", "medium": "yellow", "high": "red"}
    cost_bars = "💰" * int(recommendation.estimated_cost)
    complexity_color = complexity_colors.get(recommendation.complexity.value, "white")
    complexity_val = recommendation.complexity.value.upper()
    complexity_text = f"[{complexity_color}]{complexity_val}[/]"

    panel = Panel(
        f"**Recommended Model**: [cyan]{recommendation.model}[/cyan]\n\n"
        f"**Provider**: {recommendation.provider}\n\n"
        f"**Complexity**: {complexity_text}\n\n"
        f"**Est. Cost**: {cost_bars}\n\n"
        f"**Reason**:\n{recommendation.reason}",
        title="🎯 Model Recommendation",
        border_style="cyan",
    )
    console_cost.print(panel)

    if recommendation.alternatives:
        console_cost.print("\n[dim]Alternatives:[/dim]")
        for alt in recommendation.alternatives:
            console_cost.print(f"  • {alt['model']}: {alt['reason']}")

    console_cost.print("\n[dim]💡 Tips:[/dim]")
    if recommendation.complexity.value == "low":
        console_cost.print("  Use local model for simple tasks - completely free")
    elif recommendation.complexity.value == "medium":
        console_cost.print("  Chinese models offer great value for medium complexity")
    else:
        console_cost.print("  For complex tasks, try local model first to validate ideas")


@app.command("report")
def cost_report(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
) -> None:
    """Show token usage summary (month/week/today)"""
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console_cost.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📊 Cost Report",
                border_style="yellow",
            )
        )
        return

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    stats = {
        "today": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "week": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "month": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "total": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
    }

    for record in usage_data:
        try:
            record_time = datetime.fromisoformat(record.get("timestamp", ""))
        except Exception:
            continue

        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        model = record.get("model", "unknown")
        cost = _cost_calculate_cost(model, prompt, completion)

        stats["total"]["calls"] += 1
        stats["total"]["prompt"] += prompt
        stats["total"]["completion"] += completion
        stats["total"]["cost"] += cost

        if record_time >= month_start:
            stats["month"]["calls"] += 1
            stats["month"]["prompt"] += prompt
            stats["month"]["completion"] += completion
            stats["month"]["cost"] += cost

            if record_time >= week_start:
                stats["week"]["calls"] += 1
                stats["week"]["prompt"] += prompt
                stats["week"]["completion"] += completion
                stats["week"]["cost"] += cost

                if record_time >= today_start:
                    stats["today"]["calls"] += 1
                    stats["today"]["prompt"] += prompt
                    stats["today"]["completion"] += completion
                    stats["today"]["cost"] += cost

    console_cost.print()
    console_cost.print(Panel.fit("[bold cyan]📊 Token Usage Summary[/bold cyan]", border_style="cyan"))
    console_cost.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Period", style="green")
    table.add_column("Calls", justify="right")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (CNY)", justify="right")

    for period, label in [("today", "Today"), ("week", "This Week"), ("month", "This Month"), ("total", "Total")]:
        s = stats[period]
        table.add_row(
            label,
            str(s["calls"]),
            f"{s['prompt']:,}",
            f"{s['completion']:,}",
            f"{s['prompt'] + s['completion']:,}",
            f"[green]{_cost_format_cost(s['cost'])}[/green]" if period != "total" else f"[bold green]{_cost_format_cost(s['cost'])}[/bold green]",
        )

    console_cost.print(table)
    console_cost.print(f"\n[dim]Data source: {_COST_USAGE_FILE}[/dim]")
    console_cost.print(f"[dim]Prices configured: {len(_cost_load_prices())} models[/dim]")


@app.command("model")
def cost_model(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
) -> None:
    """Show usage grouped by model"""
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console_cost.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📈 Model Usage",
                border_style="yellow",
            )
        )
        return

    model_stats: dict[str, dict[str, Any]] = {}

    for record in usage_data:
        model = record.get("model", "unknown")
        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        cost = _cost_calculate_cost(model, prompt, completion)

        if model not in model_stats:
            model_stats[model] = {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0}
        model_stats[model]["calls"] += 1
        model_stats[model]["prompt"] += prompt
        model_stats[model]["completion"] += completion
        model_stats[model]["cost"] += cost

    sorted_models = sorted(model_stats.items(), key=lambda x: x[1]["calls"], reverse=True)

    console_cost.print()
    console_cost.print(Panel.fit("[bold cyan]📈 Usage by Model[/bold cyan]", border_style="cyan"))
    console_cost.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Model", style="green")
    table.add_column("Calls", justify="right")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (CNY)", justify="right")

    total_calls = total_prompt = total_completion = total_cost = 0
    for model, stats in sorted_models:
        total_tokens = stats["prompt"] + stats["completion"]
        total_calls += stats["calls"]
        total_prompt += stats["prompt"]
        total_completion += stats["completion"]
        total_cost += stats["cost"]
        table.add_row(
            model,
            str(stats["calls"]),
            f"{stats['prompt']:,}",
            f"{stats['completion']:,}",
            f"{total_tokens:,}",
            f"[green]{_cost_format_cost(stats['cost'])}[/green]",
        )

    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_calls}[/bold]",
        f"[bold]{total_prompt:,}[/bold]",
        f"[bold]{total_completion:,}[/bold]",
        f"[bold]{total_prompt + total_completion:,}[/bold]",
        f"[bold green]{_cost_format_cost(total_cost)}[/bold green]",
    )

    console_cost.print(table)


@app.command("history")
def cost_history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show"),
    model: str = typer.Option(None, "--model", "-m", help="Filter by model"),
) -> None:
    """Show recent call history"""
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console_cost.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📜 Call History",
                border_style="yellow",
            )
        )
        return

    filtered = usage_data
    if isinstance(model, str) and model:
        filtered = [r for r in filtered if model.lower() in r.get("model", "").lower()]

    sorted_records = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    console_cost.print()
    console_cost.print(
        Panel.fit(f"[bold cyan]📜 Recent Calls (last {len(sorted_records)})[/bold cyan]", border_style="cyan")
    )
    console_cost.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim", width=16)
    table.add_column("Model", style="green")
    table.add_column("Prompt", justify="right", width=10)
    table.add_column("Completion", justify="right", width=12)
    table.add_column("Total", justify="right", width=10)
    table.add_column("Cost", justify="right", width=10)

    for record in sorted_records:
        ts = _cost_format_datetime(record.get("timestamp", ""))
        m = record.get("model", "unknown")
        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        total = prompt + completion
        cost = _cost_calculate_cost(m, prompt, completion)
        table.add_row(ts, m[:30], f"{prompt:,}", f"{completion:,}", f"{total:,}", f"[green]{_cost_format_cost(cost)}[/green]")

    console_cost.print(table)
    if model:
        console_cost.print(f"\n[dim]Filtered by model: {model}[/dim]")


if __name__ == "__main__":
    app()
