
# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Oh My Coder CLI -Komut satırı girişi

kullanmaktyperDostça inşa edinCLIarayüz.

Ana komutlar:
- omc run <task>         #görevleri gerçekleştirmek
- omc explore            #Kod tabanını keşfedin
- omc wiki               #Proje oluşturWiki
- omc agents             #hepsini listeleAgent
- omc status             #Durumu görüntüle
- omc --version          #sürümü göster
- omc --help             #Yardım bilgileri
"""

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .agents.cross_validation import CrossValidationLayer
from .capabilities import app as cap_app
from .commands.cli_checkpoint import app as checkpoint_app
from .commands.cli_commands import app as commands_app
from .commands.cli_config_ext import app as config_ext_app
from .commands.cli_lsp import app as lsp_app
from .commands.cli_mcp import app as mcp_app
from .commands.cli_migrate import app as migrate_app
from .commands.cli_multiagent import app as multiagent_app
from .commands.cli_package_manager import app as pkg_app
from .commands.cli_search import app as search_app
from .commands.cli_security import app as security_app
from .commands.cli_self_config import app as self_config_app
from .commands.cli_server import app as server_app
from .commands.cli_skill import app as skill_app
from .commands.cli_task import app as task_app
from .commands.cli_tui import app as tui_app
from .commands.cli_usage import app as usage_app
from .core.orchestrator import Orchestrator
from .core.router import ModelRouter, RouterConfig
from .quest import QuestStatus
from .wiki import WikiGenerator

#Sürüm bilgisi
__version__ = "0.2.0"
__author__ = "VOBC"
__repo__ = "https://github.com/VOBC/oh-my-coder"

app = typer.Typer(
    name="omc",
    help=f"Oh My Coder v{__version__} -çoklu ajanAIProgramlama Asistanı",
    add_completion=False,
    no_args_is_help=True,
)

#Alt komutu kaydet
app.add_typer(config_ext_app, name="agent-config")
app.add_typer(task_app, name="task")
app.add_typer(multiagent_app, name="multiagent")
app.add_typer(security_app, name="security")
app.add_typer(checkpoint_app, name="checkpoint")
app.add_typer(mcp_app, name="mcp")
app.add_typer(
    skill_app, name="skill", help="Skillsistem-Yerleşik ve özelSkillYönetim ve Yürütme"
)
app.add_typer(usage_app, name="usage", help="Kullanım istatistikleri ve izleme- stats/trace/memory")
app.add_typer(migrate_app, name="migrate", help="hafıza aktarımı-itibarenClaude/Geminiçalışma alanı")
app.add_typer(tui_app, name="tui", help="TUIEtkileşimli arayüz-Basit terminal etkileşimi")
app.add_typer(
    self_config_app, name="self-config", help="kendi kendini yapılandırma-Doğal dil yapılandırmasıAPI Key/Modeli/oyunculuk"
)
app.add_typer(commands_app, name="cmd", help="komuta sistemi-Özel çalıştırMarkdownEmir")
app.add_typer(pkg_app, name="pkg", help="Paket yöneticisi- Homebrew/npm/scoop/winget/AUR")
app.add_typer(lsp_app, name="lsp", help="LSPentegre-Kod tanılama bilgilerini okuyun")
app.add_typer(search_app, name="search", help="kod arama- SourcegraphGenel kod tabanı araması")
app.add_typer(server_app, name="server", help="uzakServer - HTTP REST APISert")

#kod temizleme komutları
try:
    from .cli_clean import app as clean_app

    app.add_typer(clean_app, name="clean", help="kod temizleme-Gereksiz kodu tespit edin ve temizleyin")
except Exception:
    pass

# modelalt komut
from .commands.cli_model import app as model_app  # noqa: E402

app.add_typer(model_app, name="model", help="Mevcut tüm modelleri listeleyin (destekler)-Kontrol etmek/Varsayılan modeli değiştir, yerelOllamaDestek")

# gatewayalt komut (tembel içe aktarma, kaçınmagatewayBir bağımlılık eksik olduğunda bir hata oluşur)
try:
    from .cli_gateway import app as gateway_app  # noqa: E402

    app.add_typer(gateway_app, name="gateway", help="Çok platformlu ağ geçidi- Telegram / Discord")
except Exception:
    pass  # gatewayBağımlılık eksikse atla

# agentalt komut- AgentKonfigürasyon yönetimi ve kişisel gelişim
try:
    from .cli_agent import app as agent_app  # noqa: E402

    app.add_typer(agent_app, name="agent", help="Agentüstesinden gelmek-İhracat/içe aktarmak/evrim")
except Exception:
    pass

# templatealt komut-İş akışı şablonu
try:
    from .cli_template import app as template_app  # noqa: E402

    app.add_typer(template_app, name="template", help="Mevcut durum:-Ekran miktarı/Şablonları kullanın")
except Exception:
    pass

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Sürüm bilgilerini göster",
        is_eager=True,
    ),
):
    """Oh My Coder -çoklu ajanAIProgramlama Asistanı"""
    if version:
        _print_version()
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold cyan]Oh My Coder[/bold cyan] v{__version__}\n"
                f"[dim]çoklu ajanAIProgramlama Asistanı[/dim]\n\n"
                f"[dim]kullanmak[bold]omc --help[/bold]Tüm komutları görüntüle[/dim]\n"
                f"[dim]depo: {__repo__}[/dim]",
                border_style="cyan",
            )
        )
        raise typer.Exit(0)


def _print_version():
    """Sürüm bilgilerini yazdır"""
    console.print(
        f"[bold cyan]oh-my-coder[/bold cyan] version [green]{__version__}[/green]"
    )
    console.print(f"[dim]Author: {__author__}[/dim]")
    console.print(f"[dim]Repo: {__repo__}[/dim]")


@app.command()
def run(
    task: str = typer.Argument(..., help="Görev açıklaması"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    model: str = typer.Option("deepseek", "--model", "-m", help="Model seçimi"),
    workflow: str = typer.Option(
        "build",
        "--workflow",
        "-w",
        help=(
            "İş akışı adı:build(gelişim)/ review(gözden geçirmek)/ debug(hata ayıklama)/ test(test)"
            " / autopilot(otomatik yönlendirme)/ pair(çift programlama)/ refactor(yeniden düzenleme)"
            " / doc(Belge oluşturma)/ sequential(Sıralı yürütme düzenlemesi)"
        ),
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Yalnızca yürütme planının ön izlemesini yapar, gerçekte çalıştırmaz"),
    notify: bool = typer.Option(
        False, "--notify", "-n", help="Tamamlandığında bildirim gönder (masaüstü+DingTalk)"
    ),
    no_checkpoint: bool = typer.Option(
        False, "--no-checkpoint", help="Otomatik anlık görüntüyü atla (devam ettirilebilir yükleme)"
    ),
    cross_validate: bool = typer.Option(
        False,
        "--cross-validate",
        help="İş akışı sona erdikten sonra yürütülürAgentÇapraz doğrulama (çıktıya bağımsız bir perspektiften bakmak)",
    ),
):
    """Programlama görevlerini gerçekleştirin"""
    #ön kontrol
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold green]Oh My Coder[/bold green]\n"
            f"Görev: {task}\n"
            f"proje: {project_path}\n"
            f"İş akışı: {workflow}",
            title="🚀başlatmak",
        )
    )

    # Dry-runMod: Yalnızca planları göster
    if dry_run:
        console.print(
            Panel.fit(
                "[yellow]🔍 Dry-runMod—yalnızca yürütme planını gösterir[/yellow]\n\n"
                "[bold]İş akışı:[/bold] "
                + workflow
                + "\n[bold]Görev:[/bold] "
                + task
                + "\n[bold]proje:[/bold] "
                + str(project_path.absolute())
                + "\n\n[dim]Lütfen gerçek uygulamayı kaldırın--dry-runparametre[/dim]",
                title="📋Model yapılandırmasını topluluk dizininde paylaşın",
                border_style="yellow",
            )
        )
        raise typer.Exit(0)

    #Yönlendiriciyi ve orkestratörü başlatın
    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    orchestrator = Orchestrator(router, state_dir=project_path / ".omc" / "state")

    #İş akışını yürütün
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("İş akışını yürütün...", total=None)

        try:
            result = asyncio.run(
                orchestrator.execute_workflow(
                    workflow,
                    {
                        "project_path": str(project_path.absolute()),
                        "task": task,
                    },
                    skip_checkpoint=no_checkpoint,
                )
            )

            #Sonuçları göster
            _display_result(result)

            # ----Çapraz doğrulama: iş akışı çıktısına bağımsız bir bakış----
            if cross_validate:
                cv_progress = progress.add_task("🔍çapraz doğrulama...", total=None)
                try:
                    cv_layer = CrossValidationLayer(
                        model_router=router,
                        state_dir=project_path / ".omc" / "state",
                    )
                    cv_result = asyncio.run(
                        cv_layer.validate_workflow(result, workflow)
                    )
                    progress.remove_task(cv_progress)

                    #Doğrulama özetini göster
                    _display_cross_validation_result(cv_result)

                    #Doğrulama sıfır olmayan bir çıkış koduyla başarısız oluyor.
                    if cv_result.status.value in ("fail", "need_fix"):
                        console.print(
                            Panel.fit(
                                "[yellow]⚠️Çapraz doğrulamada bir sorun bulundu; sorunu düzeltip tekrar denemeniz önerilir.[/yellow]\n"
                                "[dim]Doğrulama raporu şuraya kaydedildi:.omc/state/cross_validation/[/dim]",
                                title="⚠️Doğrulama hatırlatıcısı",
                                border_style="yellow",
                            )
                        )
                except Exception as cv_err:
                    progress.remove_task(cv_progress)
                    console.print(
                        f"[yellow]⚠️Çapraz doğrulama hatası (ana işlemi etkilemez): {cv_err}[/yellow]"
                    )

            #Bildirim gönder
            if notify:
                from src.core.orchestrator import WorkflowStatus

                from .utils.notify import (
                    notify_workflow_complete,
                    notify_workflow_complete_dingtalk,
                )

                status = (
                    "completed"
                    if result.status == WorkflowStatus.COMPLETED
                    else "failed"
                )
                steps = len(result.steps) if hasattr(result, "steps") else 1
                exec_time = getattr(result, "execution_time", 0.0)

                #Masaüstü bildirimleri
                notify_workflow_complete(workflow, status, steps, exec_time)
                #DingTalk bildirimleri
                notify_workflow_complete_dingtalk(
                    None, workflow, status, steps, exec_time, str(project_path)
                )

        except Exception as e:
            _print_fatal(
                f"İş akışı yürütme hatası: {e}",
                hint="Aşağıdaki yöntemleri deneyebilirsiniz:\n"
                "  1.Ağ bağlantısını kontrol edin\n"
                "  2.onaylamakAPI Keyverimli:omc status\n"
                "  3.Ayrıntılı günlüğü görüntüle",
            )
            raise typer.Exit(1)


@app.command()
def explore(
    project_path: Path = typer.Argument(".", help="Proje yolu"),
):
    """Kod tabanını keşfedin"""
    if not _check_env():
        raise typer.Exit(1)

    console.print(f"[bold]🔍Projeleri keşfedin: {project_path}[/bold]")

    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    orchestrator = Orchestrator(router)

    try:
        result = asyncio.run(
            orchestrator.execute_single_agent(
                "explore",
                {
                    "project_path": str(project_path.absolute()),
                    "task": "Kod tabanını keşfedin ve bir proje haritası oluşturun",
                },
            )
        )

        if result.result:
            console.print(Panel(result.result, title="proje haritası"))
        else:
            _print_fatal(f"Keşif başarısız oldu: {result.error}")

    except Exception as e:
        _print_fatal(f"Keşif hatası: {e}", hint="Proje yolunun var olduğunu ve okunabilir olduğunu doğrulayın")
        raise typer.Exit(1)


@app.command()
def wiki(
    project_path: Path = typer.Argument(".", help="Proje yolu"),
    output: Path = typer.Option(
        None, "--output", "-o", help="Çıkış dosyası yolu, varsayılanREPO_WIKI.md"
    ),
):
    """Proje oluşturWikibelge"""
    project_path = project_path.resolve()

    if not project_path.exists():
        _print_fatal(f"Proje yolu mevcut değil: {project_path}")
        raise typer.Exit(1)

    #Çıkış yolunu belirleyin
    if output is None:
        output = project_path / "REPO_WIKI.md"

    console.print(f"[bold]📝oluşturmakWiki: {project_path}[/bold]")

    try:
        #itibarenpyproject.tomlVeya proje adını almak için dizin adı
        project_name = _detect_project_name(project_path)

        #oluşturmakWiki
        generator = WikiGenerator(
            project_name=project_name,
            project_path=project_path,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("ayrıştırma kodu...", total=None)
            generator.generate(output)

        console.print(
            Panel.fit(
                f"[green]✓ WikiOluşturuldu[/green]\n\n"
                f"belge: [cyan]{output}[/cyan]\n\n"
                f"[dim]kullanmak`omc wiki`Yenile[/dim]",
                title="📚 Wiki",
            )
        )

    except Exception as e:
        _print_fatal(f"WikiDerleme başarısız oldu: {e}")
        raise typer.Exit(1)


def _detect_project_name(project_path: Path) -> str:
    """Test öğesi adı"""
    #baştan başlamayı denepyproject.tomlOkumak
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            if "project" in data and "name" in data["project"]:
                return data["project"]["name"]
        except Exception:
            pass

    #baştan başlamayı denesetup.pyOkumak
    setup_py = project_path / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text()
            import re

            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
        except Exception:
            pass

    #Başarı modelinin dahil edilmesi durumunda da tasarruf sağlar
    return project_path.name


# ============================================================
# Quest Mode -Asenkron otonom programlama
# ============================================================


@app.command()
def quest(
    ctx: typer.Context,
    description: str = typer.Argument(..., help="Görev açıklaması (doğal dil)"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    title: str = typer.Option(None, "--title", "-t", help="Görev başlığı (isteğe bağlı)"),
    skip_spec: bool = typer.Option(False, "--skip-spec", help="SPEC üretimini atla, doğrudan çalıştır"),
    auto_confirm: bool = typer.Option(False, "--yes", "-y", help="Otomatik olarak onayla ve yürüt"),
):
    """
    🧙 Quest Mode -Asenkron otonom programlama

Gereksinimleri verinAI, otomatik olarak oluşturulmuşSPECBelge arka planda yürütülür ve tamamlandıktan sonra kabul bilgisi verilir.

Örnek:
      omc quest "Desteklemek için kullanıcı kimlik doğrulama modülünü uygulayınJWT"
      omc quest "Önbelleğe alma katmanı ekle" -p myproject/
      omc quest "Veritabanı erişim katmanını yeniden düzenleyin" --skip-spec
    """
    import asyncio

    project_path = project_path.resolve()
    if not project_path.exists():
        _print_fatal(f"Proje yolu mevcut değil: {project_path}")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold magenta]🧙 Quest Mode[/bold magenta]\n\n"
            f"[cyan]ihtiyaç:[/cyan] {description}\n"
            f"[cyan]proje:[/cyan] {project_path}",
            title="🚀başlatmak",
            border_style="magenta",
        )
    )

    from .quest import QuestManager

    #Adım doğrulama geri araması (etkileşimli)
    async def review_callback(quest_id: str, step_id: str, preview: str) -> str:
        console.print(f"\n[bold cyan]📋Adım kabulü: {step_id}[/bold cyan]")
        if preview:
            console.print(
                Panel.fit(preview[:500], title="kod incelemesi", border_style="dim")
            )

        from rich.prompt import Prompt

        choice = Prompt.ask(
            "Lütfen seçin",
            choices=["p", "r", "s"],
            default="p",
            show_choices=True,
        )
        mapping = {"p": "pass", "r": "retry", "s": "skip"}
        return mapping.get(choice, "pass")

    manager = QuestManager(project_path, review_callback=review_callback)

    async def run():
        # 1.yaratmakQuest
        quest_obj = await manager.create_quest(description, title=title)
        console.print(f"[dim]📋 QuestOluşturuldu: {quest_obj.id[:8]}[/dim]")

        # 2.oluşturmakSPEC
        if not skip_spec:
            console.print("[yellow]⏳ÜretiliyorSPEC...[/yellow]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("oluşturmakSPECŞartname belgesi...", total=None)
                quest_obj = await manager.generate_spec(quest_obj)

            #göstermekSPEC
            spec = quest_obj.spec
            if spec:
                spec_content = spec.to_markdown()
                console.print(
                    Panel.fit(
                        spec_content[:3000]
                        + ("\n..." if len(spec_content) > 3000 else ""),
                        title="📄 SPECŞartname belgesi",
                        border_style="cyan",
                    )
                )

            if not auto_confirm:
                console.print("\n[yellow]⚠️gözden geçirmekSPECBundan sonra, yürütmek için aşağıdaki komutu çalıştırın:[/yellow]")
                console.print(f"  [green]omc quest exec {quest_obj.id}[/green]")
                console.print("  [dim]veya kullanın[green]-y[/dim]otomatik onay[/dim]")
                raise typer.Exit(0)

        # 3.Yürütmeyi başlat
        console.print("[yellow]⏳Arka planda yürütülüyor...[/yellow]")
        console.print("[dim]kullanmak[green]omc quest status[/dim]İlerlemeyi görüntüle[/dim]")
        console.print("[dim]kullanmak[green]omc quest log {id}[/dim]Ayrıntılı günlüğü görüntüle[/dim]")

        manager.confirm_and_execute(quest_obj.id)
        console.print(f"[green]✅ QuestBaşlatıldı(ID: {quest_obj.id[:8]})[/green]")
        console.print("[dim]Tamamlandığında bildirim alın[/dim]")

    try:
        asyncio.run(run())
    except SystemExit:
        raise
    except Exception as e:
        _print_fatal(f"QuestYürütme hatası: {e}")
        raise typer.Exit(1)


@app.command("quest-list")
def quest_list(
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    status_filter: str = typer.Option(
        None, "--status", "-s", help="Duruma göre filtrele(pending/executing/completed/failed)"
    ),
    all_quests: bool = typer.Option(False, "--all", "-a", help="Tümünü gösterQuest"),
):
    """
    📋Kontrol etmekQuestliste
    """
    from .quest import QuestManager, QuestStatus

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    #Durum filtresini ayrıştır
    sf = None
    if status_filter:
        try:
            sf = QuestStatus(status_filter)
        except ValueError:
            _print_fatal(f"bilinmeyen durum: {status_filter}")
            raise typer.Exit(1)

    quests = manager.list_quests(status_filter=sf)

    if not quests:
        console.print("[dim]HiçbiriQuest[/dim]")
        return

    #durum rengi
    status_colors = {
        QuestStatus.PENDING: "dim",
        QuestStatus.SPEC_GENERATING: "yellow",
        QuestStatus.SPEC_READY: "cyan",
        QuestStatus.EXECUTING: "green",
        QuestStatus.COMPLETED: "bold green",
        QuestStatus.FAILED: "bold red",
        QuestStatus.CANCELLED: "dim",
        QuestStatus.PAUSED: "yellow",
    }

    table = Table(title=f"Questliste({len(quests)})")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("başlık", style="white")
    table.add_column("durum", width=14)
    table.add_column("takvim", width=12)
    table.add_column("zaman tükeniyor", width=8)
    table.add_column("yaratılış zamanı", style="dim")

    for q in quests:
        color = status_colors.get(q.status, "white")
        progress = int(q.progress() * 10)
        bar = "█" * progress + "░" * (10 - progress)
        table.add_row(
            q.id[:8],
            q.title[:35],
            f"[{color}]{q.status.value}[/{color}]",
            f"{bar} {int(q.progress() * 100)}%",
            f"{q.duration():.0f}s" if q.duration() else "—",
            q.created_at.strftime("%m-%d %H:%M"),
        )

    console.print(table)


@app.command("quest-status")
def quest_status(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
):
    """
    📊Kontrol etmekQuestayrıntılı durum
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id}çubuk gösterilmiyor")
        raise typer.Exit(1)

    #durum rengi
    status_color = {
        QuestStatus.PENDING: "dim",
        QuestStatus.SPEC_GENERATING: "yellow",
        QuestStatus.SPEC_READY: "cyan",
        QuestStatus.EXECUTING: "green",
        QuestStatus.COMPLETED: "bold green",
        QuestStatus.FAILED: "bold red",
        QuestStatus.CANCELLED: "dim",
        QuestStatus.PAUSED: "yellow",
    }
    sc = status_color.get(quest.status, "white")

    lines = [
        f"[cyan]ID:[/cyan]     {quest.id}",
        f"[cyan]başlık:[/cyan]   {quest.title}",
        f"[cyan]durum:[/cyan]   [{sc}]{quest.status.value}[/{sc}]",
        f"[cyan]takvim:[/cyan]   {int(quest.progress() * 100)}%",
    ]

    if quest.duration():
        lines.append(f"[cyan]zaman tükeniyor:[/cyan]   {quest.duration():.1f}s")

    if quest.spec_path:
        lines.append(f"[cyan]SPEC:[/cyan]  {quest.spec_path}")

    if quest.error_message:
        lines.append(f"[red]hata:[/red]   {quest.error_message}")

    if quest.result_summary:
        lines.append(f"[green]sonuç:[/green]  {quest.result_summary}")

    console.print(
        Panel("\n".join(lines), title=f"Quest {quest.id[:8]}", border_style="cyan")
    )

    #Adımları göster
    if quest.steps:
        console.print("\n[bold]📌Yürütme adımları:[/bold]")
        step_table = Table()
        step_table.add_column("ID", width=4)
        step_table.add_column("adım", width=20)
        step_table.add_column("Agent", width=15)
        step_table.add_column("durum", width=12)

        step_colors = {
            QuestStatus.PENDING: "dim",
            QuestStatus.EXECUTING: "yellow",
            QuestStatus.COMPLETED: "bold green",
            QuestStatus.FAILED: "bold red",
        }

        for step in quest.steps:
            sc2 = step_colors.get(step.status, "white")
            step_table.add_row(
                step.step_id,
                step.title[:20],
                step.agent,
                f"[{sc2}]{step.status.value}[/{sc2}]",
            )

        console.print(step_table)


@app.command("quest-exec")
def quest_exec(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
):
    """
    ▶️İnfaz hazırQuest
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id}çubuk gösterilmiyor")
        raise typer.Exit(1)

    if quest.status != QuestStatus.SPEC_READY:
        _print_fatal(f"QuestDurum:{quest.status},ihtiyaçSPEC_READYdurum")
        console.print("[dim]kullanmak[green]omc quest[/green]Yol korumalı alan kapsamını aşıyorQuest[/dim]")
        raise typer.Exit(1)

    manager.confirm_and_execute(quest_id)
    console.print(
        Panel.fit(
            f"[green]✅ QuestBaşlatıldı[/green]\n\n"
            f"ID: {quest.id[:8]}\n"
            f"başlık: {quest.title}\n\n"
            "[dim]kullanmak[green]omc quest status {id}[/green]İlerlemeyi görüntüle[/dim]",
            title="🚀Başarıyla başlatıldı",
            border_style="green",
        )
    )


@app.command("quest-cancel")
def quest_cancel(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
):
    """
    ⏹️İptal etmekQuest
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    if manager.cancel(quest_id):
        console.print(f"[yellow]⏹️ Quest {quest_id[:8]}İptal edildi[/yellow]")
    else:
        _print_fatal(f"Quest {quest_id}çubuk gösterilmiyor")
        raise typer.Exit(1)


@app.command("quest-pause")
def quest_pause(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
):
    """
    ⏸️duraklatmaQuest(Geçerli adım tamamlandıktan sonra duraklatın)
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    if manager.pause(quest_id):
        console.print(f"[yellow]⏸️ Quest {quest_id[:8]}yaygın[/yellow]")
        console.print("[dim]kullanmak[green]omc quest resume {id}[/dim]iyileşmek[/dim]")
    else:
        _print_fatal(f"Quest {quest_id}Mevcut değil veya duraklatılamaz")
        raise typer.Exit(1)


@app.command("quest-resume")
def quest_resume(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
):
    """
    ▶️Duraklatılmış bir işlemi devam ettirQuest(kesme noktasından devam edin)
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.resume(quest_id)
    if quest:
        console.print(f"[green]▶️ Quest {quest_id[:8]}Geri yüklendi[/green]")
        console.print("[dim]kullanmak[green]omc quest status {id}[/dim]İlerlemeyi görüntüle[/dim]")
    else:
        _print_fatal(f"Quest {quest_id}Mevcut değil veya beklemede değil")
        raise typer.Exit(1)


@app.command("quest-notify")
def quest_notify(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    dingtalk_webhook: str = typer.Option(
        None, "--dingtalk", "-d", help="DingTalkWebhook URL"
    ),
    dingtalk_secret: str = typer.Option(None, "--secret", "-s", help="DingTalk imzalama anahtarı"),
    telegram_bot_token: str = typer.Option(
        None, "--telegram-bot-token", help="Telegram Bot Token"
    ),
    telegram_chat_id: str = typer.Option(
        None, "--telegram-chat-id", help="Telegram Chat ID"
    ),
    discord_webhook: str = typer.Option(None, "--discord", help="Discord Webhook URL"),
    slack_webhook: str = typer.Option(
        None, "--slack", help="Slack Incoming Webhook URL"
    ),
    teams_webhook: str = typer.Option(
        None, "--teams", help="Microsoft Teams Webhook URL"
    ),
    feishu_webhook: str = typer.Option(
        None, "--feishu", help="Feishu (Lark)Webhook URL"
    ),
    wecom_webhook: str = typer.Option(None, "--wecom", help="Kurumsal WeChatWebhook URL"),
    pushplus_token: str = typer.Option(None, "--pushplus", help="PushPlus Token"),
):
    """
    🔔abonelikQuestBildirimler (Masaüstü+ÇeşitliWebhookkanal)
    """
    import asyncio

    from .quest import NotificationConfig, NotificationManager, QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id}çubuk gösterilmiyor")
        raise typer.Exit(1)

    #Bildirimleri yapılandırma
    config = NotificationConfig(
        desktop=True,
        dingtalk_webhook=dingtalk_webhook,
        dingtalk_secret=dingtalk_secret,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        discord_webhook=discord_webhook,
        slack_webhook=slack_webhook,
        teams_webhook=teams_webhook,
        feishu_webhook=feishu_webhook,
        wecom_webhook=wecom_webhook,
        pushplus_token=pushplus_token,
    )
    notifier = NotificationManager(config)

    def on_progress(title: str, body: str, level: str) -> None:
        """İlerlemeyi gerçek zamanlı olarak görüntüleyin (konsol geri araması)"""
        color_map = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        color = color_map.get(level, "white")
        console.print(f"[{color}]{title}[/{color}]: {body}")

    #Konsol geri çağırma kanalı ekle
    from .quest.notifications import ConsoleNotificationChannel

    notifier._channels.append(ConsoleNotificationChannel(callback=on_progress))

    #Tamamlanana kadar ilerlemeyi takip edin
    last_status = quest.status.value
    last_step = -1

    async def watch():
        nonlocal last_status, last_step
        console.print(f"[dim]⏳monitörQuest {quest_id[:8]},buna göreCtrl+Cçıkış yapmak...[/dim]\n")
        try:
            while True:
                await asyncio.sleep(5)
                fresh = manager.get_quest(quest_id)
                if fresh is None:
                    break

                #Gerçek zamanlı ilerleme (adımlar değiştiğinde çıktı)
                if fresh.steps:
                    completed = sum(
                        1 for s in fresh.steps if s.status == QuestStatus.COMPLETED
                    )
                    total = len(fresh.steps)
                    if completed != last_step:
                        last_step = completed
                        bar = "█" * completed + "░" * (total - completed)
                        console.print(
                            f"  [{fresh.status.value:12}] "
                            f"{bar} {completed}/{total}adım"
                        )

                #Durum değiştiğinde masaüstünü gönder/DingTalk bildirimleri
                if fresh.status.value != last_status:
                    last_status = fresh.status.value
                    if fresh.status.value == "completed":
                        notifier.notify_completed(
                            fresh.title, fresh.result_summary or "", fresh.id
                        )
                    elif fresh.status.value == "failed":
                        notifier.notify_failed(
                            fresh.title,
                            fresh.error_message or "bilinmeyen hata",
                            fresh.id,
                        )
                    elif fresh.status.value == "paused":
                        notifier.send(
                            "⏸️ Questyaygın",
                            fresh.title,
                            event="paused",
                            quest_id=fresh.id,
                        )

                #tamamlamak veya sonlandırmak
                if fresh.status.value in ("completed", "failed", "cancelled"):
                    console.print(f"\n[bold]son durum: {fresh.status.value}[/bold]")
                    break
        except asyncio.CancelledError:
            pass

    try:
        asyncio.run(watch())
    except KeyboardInterrupt:
        console.print("\n[dim]bomba[/dim]")


@app.command("quest-wait")
def quest_wait(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    timeout: int = typer.Option(0, "--timeout", "-t", help="Zaman aşımı saniyeleri (0=sınırsız)"),
):
    """
    ⏳beklemeyi engelleQuestKabul sonuçlarını tamamlayın ve sunun

Tamamlandıktan sonra, her adımın geçme durumunu ve sonuçların özetini içeren ayrıntılı bir kabul raporu görüntülenecektir.
    """
    import asyncio

    from .quest import QuestManager, QuestStatus

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id}çubuk gösterilmiyor")
        raise typer.Exit(1)

    #Tamamlanan durumlar sonuçları doğrudan görüntüler
    if quest.status in (
        QuestStatus.COMPLETED,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    ):
        _show_acceptance_report(quest, console)
        return

    #Tamamlanana kadar gerçek zamanlı olarak takip edin
    elapsed = 0

    async def watch():
        nonlocal elapsed
        try:
            while True:
                await asyncio.sleep(3)
                elapsed += 3
                fresh = manager.get_quest(quest_id)
                if fresh is None:
                    break

                #Komut listesi:
                if fresh.steps:
                    completed = sum(
                        1 for s in fresh.steps if s.status == QuestStatus.COMPLETED
                    )
                    total = len(fresh.steps)
                    int(completed / total * 100)
                    bar = "█" * completed + "░" * (total - completed)
                    console.print(
                        f"\r  [{fresh.status.value:12}] "
                        f"{bar} {completed}/{total} | {elapsed}s",
                        end="",
                    )

                if fresh.status in (
                    QuestStatus.COMPLETED,
                    QuestStatus.FAILED,
                    QuestStatus.CANCELLED,
                ):
                    console.print()  #yeni satır
                    _show_acceptance_report(fresh, console)
                    break

                if timeout > 0 and elapsed >= timeout:
                    console.print(f"\n[yellow]⏰zaman aşımı({timeout}s)[/yellow]")
                    break
        except asyncio.CancelledError:
            console.print()

    try:
        asyncio.run(watch())
    except KeyboardInterrupt:
        console.print("\n[dim]Bekleme kesintiye uğradı[/dim]")


def _show_acceptance_report(quest, console):
    """sergilemekQuestKabul raporu"""
    from rich.panel import Panel
    from rich.table import Table

    from .quest import QuestStatus

    status_color_map = {
        QuestStatus.COMPLETED: "bold green",
        QuestStatus.FAILED: "bold red",
        QuestStatus.CANCELLED: "dim",
        QuestStatus.EXECUTING: "yellow",
        QuestStatus.PAUSED: "yellow",
    }
    sc = status_color_map.get(quest.status, "white")

    #başlık
    emoji = {
        QuestStatus.COMPLETED: "✅",
        QuestStatus.FAILED: "❌",
        QuestStatus.CANCELLED: "⏹️",
    }.get(quest.status, "⏳")
    console.print(
        Panel.fit(
            f"[bold]{emoji} {quest.title}[/bold]",
            title=f"Kabul Raporu —{quest.status.value}",
            border_style=sc.value if hasattr(sc, "value") else "green",
        )
    )

    #Temel bilgiler
    duration = quest.duration()
    duration_str = f"{duration:.1f}s" if duration else "—"
    console.print(
        f"  [cyan]ID:[/cyan]     {quest.id[:8]}\n"
        f"  [cyan]zaman tükeniyor:[/cyan]   {duration_str}\n"
        + (
            f"  [cyan]özet:[/cyan]  {quest.result_summary}\n"
            if quest.result_summary
            else ""
        )
        + (
            f"  [red]hata:[/red]   {quest.error_message}\n"
            if quest.error_message
            else ""
        )
    )

    #adım kabul formu
    if quest.steps:
        table = Table(title="📋Adım kabulü", show_header=True)
        table.add_column("adım", width=6)
        table.add_column("başlık", width=30)
        table.add_column("durum", width=12)

        step_sc_map = {
            QuestStatus.PENDING: "dim",
            QuestStatus.EXECUTING: "yellow",
            QuestStatus.COMPLETED: "bold green",
            QuestStatus.FAILED: "bold red",
        }

        for step in quest.steps:
            sc2 = step_sc_map.get(step.status, "white")
            status_icon = {
                QuestStatus.COMPLETED: "✅",
                QuestStatus.FAILED: "❌",
                QuestStatus.PENDING: "⏳",
                QuestStatus.EXECUTING: "⚙️",
            }.get(step.status, "?")
            table.add_row(
                step.step_id,
                step.title[:30],
                f"[{sc2}]{status_icon} {step.status.value}[/{sc2}]",
            )

        console.print(table)

        #Başarısız adım ayrıntıları
        failed_steps = [s for s in quest.steps if s.status == QuestStatus.FAILED]
        if failed_steps:
            console.print("\n[bold red]❌Arıza ayrıntıları:[/bold red]")
            for s in failed_steps:
                console.print(f"  [{s.step_id}] {s.title}: {s.error}")


@app.command()
def agents():
    """Mevcut olanların hepsini listeleAgent"""
    table = Table(title="Mevcut acenteler")
    table.add_column("isim", style="cyan")
    table.add_column("betimlemek")
    table.add_column("Hiyerarşi", style="green")

    #Tümünü içe aktarAgent
    from .agents import (
        AnalystAgent,
        APIAgent,
        ArchitectAgent,
        AuthAgent,
        CodeReviewerAgent,
        CodeSimplifierAgent,
        CriticAgent,
        DataAgent,
        DatabaseAgent,
        DebuggerAgent,
        DesignerAgent,
        DevOpsAgent,
        ExecutorAgent,
        ExploreAgent,
        GitMasterAgent,
        MigrationAgent,
        PerformanceAgent,
        PlannerAgent,
        PromptAgent,
        QATesterAgent,
        ScientistAgent,
        SecurityReviewerAgent,
        SelfImprovingAgent,
        SkillManageAgent,
        TestEngineerAgent,
        TracerAgent,
        UMLAgent,
        VerifierAgent,
        VisionAgent,
        WriterAgent,
    )

    agents_list = [
        ("explore", ExploreAgent.description, ExploreAgent.default_tier),
        ("analyst", AnalystAgent.description, AnalystAgent.default_tier),
        ("planner", PlannerAgent.description, PlannerAgent.default_tier),
        ("architect", ArchitectAgent.description, ArchitectAgent.default_tier),
        ("executor", ExecutorAgent.description, ExecutorAgent.default_tier),
        ("verifier", VerifierAgent.description, VerifierAgent.default_tier),
        (
            "test-engineer",
            TestEngineerAgent.description,
            TestEngineerAgent.default_tier,
        ),
        (
            "code-reviewer",
            CodeReviewerAgent.description,
            CodeReviewerAgent.default_tier,
        ),
        ("debugger", DebuggerAgent.description, DebuggerAgent.default_tier),
        ("tracer", TracerAgent.description, TracerAgent.default_tier),
        ("critic", CriticAgent.description, CriticAgent.default_tier),
        ("writer", WriterAgent.description, WriterAgent.default_tier),
        ("designer", DesignerAgent.description, DesignerAgent.default_tier),
        (
            "security-reviewer",
            SecurityReviewerAgent.description,
            SecurityReviewerAgent.default_tier,
        ),
        ("git-master", GitMasterAgent.description, GitMasterAgent.default_tier),
        (
            "code-simplifier",
            CodeSimplifierAgent.description,
            CodeSimplifierAgent.default_tier,
        ),
        ("scientist", ScientistAgent.description, ScientistAgent.default_tier),
        ("qa-tester", QATesterAgent.description, QATesterAgent.default_tier),
        ("database", DatabaseAgent.description, DatabaseAgent.default_tier),
        ("api", APIAgent.description, APIAgent.default_tier),
        ("devops", DevOpsAgent.description, DevOpsAgent.default_tier),
        ("uml", UMLAgent.description, UMLAgent.default_tier),
        ("performance", PerformanceAgent.description, PerformanceAgent.default_tier),
        ("migration", MigrationAgent.description, MigrationAgent.default_tier),
        ("prompt", PromptAgent.description, PromptAgent.default_tier),
        ("vision", VisionAgent.description, VisionAgent.default_tier),
        ("auth", AuthAgent.description, AuthAgent.default_tier),
        ("data", DataAgent.description, DataAgent.default_tier),
        (
            "self-improving",
            SelfImprovingAgent.description,
            SelfImprovingAgent.default_tier,
        ),
        (
            "skill-manage",
            SkillManageAgent.description,
            SkillManageAgent.default_tier,
        ),
    ]

    for name, desc, tier in agents_list:
        table.add_row(name, desc, tier)

    console.print(table)

    console.print(f"\n[dim]yaygın{len(agents_list)}Modele göre yapılandırın:[/dim]")


@app.command()
def status():
    """Sistem durumunu görüntüle"""
    console.print("[bold]Sistem durumu[/bold]\n")

    #incelemekAPI Key
    api_keys = {
        "DEEPSEEK_API_KEY": "🟢üretime hazır",
        "KIMI_API_KEY": "🟢üretime hazır",
        "DOUBAO_API_KEY": "🟢üretime hazır",
        "MINIMAX_API_KEY": "🟡 Beta",
        "ZHIPUAI_API_KEY": "🟡 Beta",
        "TONGYI_API_KEY": "🟡 Beta",
        "WENXIN_API_KEY": "🔴Geliştirilecek",
        "HUNYUAN_API_KEY": "🔴Geliştirilecek",
    }

    console.print("[bold]Model destek durumu:[/bold]")
    for key, status_label in api_keys.items():
        value = os.getenv(key)
        if value:
            console.print(f"  {key}: [{status_label}]yapılandırılmış")
        else:
            console.print(f"  {key}: [red]✗Yapılandırılmadı[/red]")

    #Yönlendiriciyi kontrol edin
    console.print()
    try:
        router = _init_router()
        stats = router.get_stats()
        console.print(
            Panel(
                f"[green]✓Yönlendirici hazır[/green]\n"
                f"Toplam istek: [cyan]{stats['total_requests']}[/cyan]\n"
                f"var olmak,:   [cyan]¥{stats['total_cost']:.4f}[/cyan]",
                title="yönlendirici",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(
            Panel(
                f"[red]✗Proje yapısını ve kod organizasyonunu anlayın[/red]\n\n{e}",
                title="yönlendirici",
                border_style="red",
            )
        )


def _init_router() -> ModelRouter:
    """Model yönlendiriciyi başlatın ve başarısız olduğunda kolay uyarılar verin."""
    config = RouterConfig()

    #Yalnızca geçerli varsayılan modeli kontrol ederkey, gerekli değilDeepSeek
    config_check = _check_env()
    if not config_check:
        raise typer.Exit(1)

    try:
        return ModelRouter(config)
    except Exception as e:
        _print_fatal(f"Çalışma dizini taraması: {e}")


def _print_missing_key_hint(key: str, reason: str = ""):
    """Eksik baskıAPI KeyDostça ipuçları"""

    console.print()
    console.print(
        Panel(
            f"[bold red]✗bulunamadı{key}[/bold red]\n\n"
            f"[yellow]Lütfen önce yapılandırınAPI Key[/yellow]\n\n"
            f"[dim]tavsiye etmek:[/dim] DeepSeek — {reason}\n\n"
            f"[cyan]Birinci yöntem:[/cyan]Ortam değişkenlerini ayarlama\n"
            f"  [green]export {key}=your_key_here[green]\n\n"
            f"[cyan]İkinci yöntem:[/cyan]yazmak.envbelge\n"
            f"  [green]echo '{key}=your_key_here' >> .env[green]\n\n"
            f"[dim]Adresi al:[/dim] https://platform.deepseek.com/",
            title="⚠️EksiklikAPI Key",
            border_style="red",
        )
    )
    console.print()


def _print_fatal(msg: str, hint: str = ""):
    """Önemli hatayı yazdırın ve çıkın"""

    console.print()
    console.print(
        Panel(
            f"[bold red]✗ {msg}[/bold red]"
            + (f"\n\n[cyan]ipucu:[/cyan] {hint}" if hint else ""),
            title="❌Yürütme başarısız oldu",
            border_style="red",
        )
    )
    console.print()


def _resolve_default_model(config: dict) -> str:
    """Varsayılan modeli ayrıştırma: ortam değişkenleri> config.json >İlki varapi_keymodeli> deepseek"""
    # 1.ortam değişkenleri
    env_model = os.getenv("OMC_DEFAULT_MODEL")
    if env_model:
        return env_model
    # 2. config.jsonaçık ayar
    cfg_model = config.get("default_model")
    if cfg_model:
        return cfg_model
    # 3.İlkini bulapi_keymodeli
    models = config.get("models", {})
    if isinstance(models, dict):
        for name, mcfg in models.items():
            if isinstance(mcfg, dict) and mcfg.get("api_key"):
                return name
    return "deepseek"


def _check_env() -> bool:
    """Mevcut varsayılan modeli kontrol edinAPI KeyHazır mı (okuconfig.json),geri dönmekTruehazır demektir"""
    config = _load_config()
    default_model = _resolve_default_model(config)

    #Öncelik verconfig.jsonile ilgilimodels[default_model].api_keyOkumak
    models = config.get("models", {})
    if isinstance(models, dict):
        model_cfg = models.get(default_model, {}) or models.get(default_model.replace("-", "_"), {})
        if model_cfg and model_cfg.get("api_key"):
            return True
    #Geri dönüş: Ortam değişkenlerini kontrol edin
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "kimi": "KIMI_API_KEY",
        "doubao": "DOUBAO_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "glm": "ZHIPUAI_API_KEY",
        "tongyi": "TONGYI_API_KEY",
        "wenxin": "WENXIN_API_KEY",
        "hunyuan": "HUNYUAN_API_KEY",
        "mimo": "MINIMAX_API_KEY",
        "glm-4-flash": "ZHIPUAI_API_KEY",
        "deepseek-chat": "DEEPSEEK_API_KEY",
    }
    key_var = key_map.get(default_model, "DEEPSEEK_API_KEY")
    if not os.getenv(key_var):
        _print_missing_key_hint(key_var, f"Mevcut varsayılan model: {default_model}")
        return False
    return True


def _load_config() -> dict:
    """itibaren~/.omc/config.jsonYapılandırmayı oku"""
    config_path = Path.home() / ".omc" / "config.json"
    if not config_path.exists():
        return {}
    import json
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def _display_result(result):
    """İş akışı sonuçlarını göster"""
    console.print(f"\n[bold]İş akışı{result.workflow_id}[/bold]")
    console.print(f"durum: {_status_color(result.status.value)}")
    console.print(f"Yürütme süresi: {result.execution_time:.2f}s")
    console.print(f"Tokenkullanmak: {result.total_tokens:,}")

    if result.steps_completed:
        console.print("\n[green]✓Tamamlanan adımlar:[/green]")
        for step in result.steps_completed:
            console.print(f"  - {step}")

    if result.steps_failed:
        console.print("\n[red]✗başarısız adım:[/red]")
        for step in result.steps_failed:
            console.print(f"  - {step}")

    if result.error:
        console.print(f"\n[red]hata: {result.error}[/red]")


def _display_cross_validation_result(result):
    """Çapraz doğrulama sonuçlarını göster"""

    status_color = {
        "pass": "green",
        "fail": "red",
        "need_fix": "yellow",
        "skipped": "dim",
    }.get(result.status.value, "white")

    status_icon = {
        "pass": "✅",
        "fail": "❌",
        "need_fix": "⚠️",
        "skipped": "⏭",
    }.get(result.status.value, "?")

    panel_color = {
        "pass": "green",
        "fail": "red",
        "need_fix": "yellow",
        "skipped": "dim",
    }.get(result.status.value, "white")

    lines = [
        f"**tanımID**: `{result.validation_id}`",
        f"**İş akışı**: `{result.workflow_name}` (`{result.workflow_id}`)",
        f"**durum**: [{status_color}]{result.status.value.upper()}[/{status_color}]",
        f"**Bulunan sorunlar**: {len(result.issues)}bireysel",
        f"**Doğrulama zaman alır**: {result.execution_time:.1f}s",
    ]

    if result.issues:
        lines.append("")
        lines.append("[bold]Soru listesi:[/bold]")
        for i, issue in enumerate(result.issues, 1):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "⚪",
            }.get(issue.severity.value, "⚪")
            lines.append(
                f"{i}. {severity_icon} **[{issue.severity.value.upper()}]**"
                f"[{issue.category}] {issue.description}"
            )
            if issue.location:
                lines.append(f"   📍 {issue.location}")
            if issue.suggestion:
                lines.append(f"   💡 {issue.suggestion}")

    panel_title = f"{status_icon}Çapraz doğrulama sonuçları"

    console.print(
        Panel.fit("\n".join(lines), title=panel_title, border_style=panel_color)
    )


@app.command()
def config(
    action: str = typer.Argument(
        "show",
        help="işletmek: show(Kontrol etmek)/ set(kurmak)/ list(Mevcut yapılandırma öğelerini listeleyin)",
    ),
    key: str = typer.Option(None, "--key", "-k", help="Yapılandırma öğesi adı"),
    value: str = typer.Option(None, "--value", "-v", help="konfigürasyon değeri"),
):
    """
    ⚙️Yönetim yapılandırması

kullanım:
      omc config show          #Mevcut yapılandırmayı görüntüle
      omc config list         #Tüm yapılandırma öğelerini listeleyin
      omc config set -k DEEPSEEK_API_KEY -v xxx   #Yapılandırma öğelerini ayarlayın
    """
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    config_path = Path(".env")
    if config_path.exists():
        load_dotenv(config_path)

    if action == "list":
        console.print("[bold]Mevcut konfigürasyon öğeleri:[/bold]\n")
        items = [
            ("DEEPSEEK_API_KEY", "DeepSeek API Key(Önerilen, uygun maliyetli)"),
            ("DEEPSEEK_BASE_URL", "DeepSeek APIAdres (varsayılan resmi)"),
            ("KIMI_API_KEY", "KIMI API Key"),
            ("DOUBAO_API_KEY", "Doubao API Key"),
            ("DINGTALK_WEBHOOK_URL", "DingTalkWebhook URLModel önerisiQuestbildir)"),
            ("DINGTALK_SECRET", "DingTalk imzalama anahtarı"),
            ("DEFAULT_MODEL", "Varsayılan model (varsayılandeepseek)"),
            ("DEFAULT_WORKFLOW", "Varsayılan iş akışı (varsayılanbuild)"),
        ]
        for k, desc in items:
            val = os.getenv(k, "")
            masked = _mask_secret(val)
            status = "[green]✓[/green]" if val else "[red]✗[/red]"
            console.print(f"  {status} [cyan]{k}[/cyan]")
            console.print(f"       [dim]{desc}[/dim]")
            if val:
                console.print(f"mevcut değer: {masked}")
            console.print()
        return

    if action == "show":
        console.print("[bold]Mevcut yapılandırma:[/bold]\n")
        keys_to_show = [
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
            "KIMI_API_KEY",
            "DOUBAO_API_KEY",
            "DINGTALK_WEBHOOK_URL",
            "DINGTALK_SECRET",
            "DEFAULT_MODEL",
            "DEFAULT_WORKFLOW",
        ]
        for key_name in keys_to_show:
            val = os.getenv(key_name, "")
            masked = _mask_secret(val)
            status = "[green]✓[/green]" if val else "[dim]—[/dim]"
            console.print(f"  {status} [cyan]{key_name}[/cyan] = {masked}")
        return

    if action == "set":
        if not key or not value:
            console.print(
                "[red]❗Aynı anda sağlanması gerekiyor--keyVe--value[/red]\n"
                "kategoriye göre: [green]omc config set -k DEFAULT_MODEL -v kimi[/green]"
            )
            raise typer.Exit(1)

        #yazmak.envbelge
        env_path = Path(".env")
        env_vars: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()

        env_vars[key] = value
        lines = [f"{k}={v}" for k, v in env_vars.items()]
        env_path.write_text("\n".join(lines) + "\n")
        console.print(
            f"[green]✓Zaten ayarlandı[/green] [cyan]{key}[/cyan] = {_mask_secret(value)}"
        )
        console.print("[dim]Gerçek entegrasyon sırasında içe aktarılması gerekiyor.envbelge[/dim]")
        return

    console.print("[red]Bilinmeyen işlem[/red], mevcut: show / list / set")
    raise typer.Exit(1)


def _mask_secret(value: str) -> str:
    """Hassasiyeti azaltılmış ekran tuşu"""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def _status_color(status: str) -> str:
    """Durumu renklendir"""
    colors = {
        "completed": "[green]Tamamlanmış[/green]",
        "failed": "[red]hata[/red]",
        "running": "[yellow]Koşma[/yellow]",
        "pending": "[dim]Beklemek[/dim]",
    }
    return colors.get(status, status)


#Alt komutu kaydet
app.add_typer(cap_app, name="cap", help="Yetenek paketi yönetimi-Dışa aktarın, içe aktarın ve paylaşınAgentYapılandırma")

if __name__ == "__main__":
    app()
    app()
