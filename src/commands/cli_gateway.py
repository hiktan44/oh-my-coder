from __future__ import annotations

"""
Gateway CLI -Çoklu platform ağ geçidi komutları

omc gateway start --telegram <token>
omc gateway start --discord <token>
omc gateway status
"""


import asyncio
import os

import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(
    name="gateway",
    help="Çoklu platform mesaj ağ geçidi (Telegram / Discord)",
    add_completion=False,
)


def _load_gateway():
    """Tembel yüklemeGateway(Bağımlılıklar kurulu olmadığında kaçınınimporthata)"""
    from src.gateway.gateway import Gateway

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    discord_token = os.getenv("DISCORD_BOT_TOKEN")

    return Gateway(
        orchestrator=None,
        telegram_token=telegram_token,
        discord_token=discord_token,
    )


@app.command()
def status():
    """Ağ geçidi durumunu görüntüle"""
    try:
        gateway = _load_gateway()
        status_data = gateway.status()

        table = Table(title="Gateway Status")
        table.add_column("platformu", style="cyan")
        table.add_column("tip", style="yellow")
        table.add_column("yapılandırılmış", style="green")
        table.add_column("Koşma", style="green")

        for platform, info in status_data["handlers"].items():
            table.add_row(
                platform,
                info["type"],
                "✅" if info["configured"] else "❌",
                "✅" if info["started"] else "❌",
            )

        console.print(table)
        console.print(
            f"\nKomut listesi:: {', '.join(status_data['started_platforms']) or '(none)'}"
        )

    except Exception as e:
        console.print(f"[red]hata: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def start(
    telegram: str = typer.Option(
        None, "--telegram", help="Telegram Bot Token(ayrıca ayarlanabilirenv TELEGRAM_BOT_TOKEN)"
    ),
    discord: str = typer.Option(
        None, "--discord", help="Discord Bot Token(ayrıca ayarlanabilirenv DISCORD_BOT_TOKEN)"
    ),
):
    """Ağ geçidini başlatın (mevcut işlemi engelleyecektir, tuşuna basın)Ctrl+Cdurmak)"""
    telegram_token = telegram or os.getenv("TELEGRAM_BOT_TOKEN")
    discord_token = discord or os.getenv("DISCORD_BOT_TOKEN")

    if not telegram_token and not discord_token:
        console.print(
            "[yellow]⚠️Platform belirtilmediToken.\n"
            "Aşağıdaki ortam değişkenlerinden birini ayarlayın:\n"
            "  TELEGRAM_BOT_TOKEN=<token>  omc gateway start --telegram <token>\n"
            "  DISCORD_BOT_TOKEN=<token>   omc gateway start --discord <token>[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print("[green]Düşünce zinciri başladı...[/green]")
    if telegram_token:
        console.print("  ✅ Telegram:yapılandırılmış")
    if discord_token:
        console.print("  ✅ Discord:yapılandırılmış")

    try:
        from src.gateway.gateway import Gateway

        gateway = Gateway(
            orchestrator=None,  # TODO:Gerçekliğe erişimOrchestrator(öncelikle uygulanması gerekir)WorkflowLoader)
            telegram_token=telegram_token,
            discord_token=discord_token,
        )

        async def run():
            await gateway.start_all()
            console.print("\n[green]✅Ağ geçidi başlatıldı, tuşuna basınCtrl+Cdurmak[/green]")
            #Sinyal alınana kadar çalışmaya devam edin
            try:
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                pass
            finally:
                await gateway.stop_all()

        asyncio.run(run())

    except ImportError as e:
        console.print(f"[red]❌Eksik bağımlılıklar: {e}[/red]")
        console.print("Kurulum komutu:pip install python-telegram-bot discord.py")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌Başlatma başarısız oldu: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def stop():
    """Ağ geçidini durdurun (yalnızca arka plan işlemi kullanıldığında anlamlıdır)"""
    console.print("[yellow]Ağ geçidini durdur...(Geçerli sürüm gerektirirCtrl+C)[/yellow]")
