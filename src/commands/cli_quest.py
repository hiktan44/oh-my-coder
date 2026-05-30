from __future__ import annotations

# mypy: disable-error-code="abstract,arg-type,assignment,attr-defined,call-arg,call-overload,dict-item,func-returns-value,import-untyped,index,misc,no-any-return,no-redef,operator,override,return,return-value,syntax,union-attr,var-annotated"

"""
Quest Mode CLI -Asenkron otonom programlama

Gereksinimleri verinAI, otomatik olarak oluşturulmuşSPECBelge arka planda yürütülür ve tamamlandıktan sonra kabul bilgisi verilir.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.quest import QuestStatus

console = Console()
app = typer.Typer(name="quest", help="Quest ModeEmir")


def _print_fatal(msg: str):
    """Önemli hatayı yazdır"""
    console.print(f"[bold red]❌ {msg}[/bold red]")


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

    from src.quest import QuestManager

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
                console.print("  [dim]veya kullanın[green]-y[/green]otomatik onay[/dim]")
                raise typer.Exit(0)

        # 3.Yürütmeyi başlat
        console.print("[yellow]⏳Arka planda yürütülüyor...[/yellow]")
        console.print("[dim]kullanmak[green]omc quest status[/green]İlerlemeyi görüntüle[/dim]")
        console.print("[dim]kullanmak[green]omc quest log {id}[/green]Ayrıntılı günlüğü görüntüle[/dim]")

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
    from src.quest import QuestManager, QuestStatus

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
    from src.quest import QuestManager

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
    from src.quest import QuestManager

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
    from src.quest import QuestManager

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
    from src.quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    if manager.pause(quest_id):
        console.print(f"[yellow]⏸️ Quest {quest_id[:8]}yaygın[/yellow]")
        console.print("[dim]kullanmak[green]omc quest resume {id}[/green]iyileşmek[/dim]")
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
    from src.quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.resume(quest_id)
    if quest:
        console.print(f"[green]▶️ Quest {quest_id[:8]}Geri yüklendi[/green]")
        console.print("[dim]kullanmak[green]omc quest status {id}[/green]İlerlemeyi görüntüle[/dim]")
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

    from src.quest import NotificationConfig, NotificationManager, QuestManager

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
    from src.quest.notifications import ConsoleNotificationChannel

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

    from src.quest import QuestManager, QuestStatus

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

    from src.quest import QuestStatus

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
