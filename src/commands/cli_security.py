from __future__ import annotations

from typing import Optional

"""
Emniyet/İzinlerCLIEmir

omc security check <command>  -Ön kontrol komutu güvenli mi?
omc security list             -Yerleşik tehlikeli kalıpları listeleyin
omc security sandbox-test     -Korumalı alan yolu kısıtlamalarını test edin
"""


import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.sandbox.sandbox import Sandbox
from src.security.permissions import (
    PermissionGuard,
)

app = typer.Typer(
    name="security",
    help="güvenlik kontrolü-İzin doğrulama, tehlikeli komut müdahalesi, korumalı alan testi",
    add_completion=False,
)
console = Console()


@app.command("check")
def security_check(
    command: str = typer.Argument(..., help="kontrol etme komutu"),
    config_file: str = typer.Option(
        None,
        "--config",
        "-c",
        help="İzin kuralları dosyası(.yaml/.json)",
    ),
) -> None:
    """
Ön kontrol komutu güvenli mi?

Örnek:
        omc security check "git status"
        omc security check "rm -rf /tmp/test"
        omc security check "dd if=/dev/zero of=/dev/sda"
    """
    guard: Optional[PermissionGuard] = None

    if config_file:
        try:
            from src.config.agent_config import load_config_file

            config = load_config_file(config_file)
            guard = PermissionGuard.from_agent_config(config.to_dict())
        except Exception as e:
            console.print(f"[yellow]Varsayılan kurallar kullanılarak yapılandırma yüklenemedi: {e}[/yellow]")
            guard = PermissionGuard()
    else:
        guard = PermissionGuard()

    result = guard.check(command)
    needs_appr = guard.needs_approval(command)

    if result.allowed:
        if needs_appr:
            console.print(
                Panel(
                    f"[yellow]⚠️Komutun yürütülmesine izin veriliyor ancak onay gerekiyor[/yellow]\n\n"
                    f"Emir: [cyan]{command}[/cyan]\n"
                    f"sebep: {result.reason or 'kibritrequire_approvalkural'}",
                    title="🔒güvenlik kontrolü",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel.fit(
                    f"[green]✅komut güvenliği[/green]\n\nEmir: [cyan]{command}[/cyan]",
                    title="🔒güvenlik kontrolü",
                    border_style="green",
                )
            )
    else:
        console.print(
            Panel(
                f"[red]❌Komut ele geçirildi[/red]\n\n"
                f"Emir: [cyan]{command}[/cyan]\n"
                f"sebep: {result.reason}\n"
                f"kibrit: [dim]{result.matched_pattern}[/dim]",
                title="🔒güvenlik kontrolü",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command("list")
def security_list() -> None:
    """
Yerleşik tehlikeli komut modellerini listeleyin

Örnek:
        omc security list
    """
    console.print(
        Panel.fit(
            "[bold]Yerleşik tehlikeli komut modu (yapılandırılmamış olsa bile engellenir)[/bold]\n",
            title="🔒Dahili tehlike modu",
            border_style="red",
        )
    )

    patterns = [
        ("rm -rf /", "Kök dizini yinelemeli olarak sil"),
        ("rm -rf /{dir}", "Sistem dizinlerini yinelemeli olarak silme"),
        ("Fork Bomb", "ForkÖnerilen modelleri göster"),
        ("> /dev/sd[a-z]", "Doğrudan disk cihazına yaz"),
        ("dd if=... of=/dev/", "Cihaz dosyalarını doğrudan yazın"),
        ("mkfs", "Dosya sistemini biçimlendir"),
        (":(){ :|:& };:", "Forkbomba çeşidi"),
    ]

    table = Table()
    table.add_column("modeli", style="red")
    table.add_column("göstermek", style="white")

    for pattern, desc in patterns:
        table.add_row(pattern, desc)

    console.print(table)


@app.command("sandbox-test")
def sandbox_test(
    path: str = typer.Argument(".", help="test yolu"),
) -> None:
    """
Korumalı alan yolu kısıtlamalarını test edin

Örnek:
        omc security sandbox-test "/tmp/test"
        omc security sandbox-test "~/.ssh/id_rsa"
        omc security sandbox-test "/etc/passwd"
    """
    sandbox = Sandbox()

    allowed = sandbox.validate_path(path)

    if allowed:
        console.print(
            Panel.fit(
                f"[green]✅Yol izin verilen aralıkta[/green]\n\nyol: [cyan]{path}[/cyan]\n"
                f"Dizine izin ver: {', '.join(sandbox.get_allowed_dirs())}",
                title="🛡️korumalı alan testi",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]❌Yol korumalı alan kapsamını aşıyor[/red]\n\n"
                f"yol: [cyan]{path}[/cyan]\n"
                f"Dizine izin ver: {', '.join(sandbox.get_allowed_dirs())}",
                title="🛡️korumalı alan testi",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command("run")
def security_run(
    command: str = typer.Argument(..., help="Korumalı alanda yürütülen komutlar"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Zaman aşımı saniyeleri"),
) -> None:
    """
Komutları sanal alanda güvenle yürütün

Örnek:
        omc security run "ls ~/.omc"
        omc security run "git status" -t 10
    """
    sandbox = Sandbox()

    console.print(f"[dim]Korumalı alanda yürüt: {command}[/dim]")

    try:
        result = sandbox.run_command(command, timeout=timeout)

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")

        if result.returncode == 0:
            console.print(f"\n[green]✓Yürütme başarılı (dönüş{result.returncode})[/green]")
        else:
            console.print(f"\n[yellow]Yürütme tamamlandı (dönüş{result.returncode})[/yellow]")

    except PermissionError as e:
        console.print(f"[red]❌yapılandırılmış: {e}[/red]")
        raise typer.Exit(1)
    except TimeoutError:
        console.print(f"[red]❌Komut yürütme zaman aşımı ({timeout}Saniye)[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌Yürütme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)
