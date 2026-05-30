from __future__ import annotations

"""
omc quality -Kod kalitesi kontrol komutları

Aşağıdaki alt komutlar desteklenir:
- omc quality check [path]  #koşmakruff check
- omc quality fix [path]   #koşmakruff check --fix
- omc quality type [path]  #koşmakmypytip kontrolü
- omc quality all [path]   #BirinciblackTekrarruff checkTekrarmypy
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(help="Kod kalite kontrolü- ruff/black/mypyentegre")
console = Console()


def _check_ruff_installed() -> bool:
    """incelemekruffKurulu mu?"""
    return shutil.which("ruff") is not None


def _check_black_installed() -> bool:
    """incelemekblackKurulu mu?"""
    try:
        subprocess.run(
            [sys.executable, "-m", "black", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _check_mypy_installed() -> bool:
    """incelemekmypyKurulu mu?"""
    try:
        subprocess.run(
            [sys.executable, "-m", "mypy", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@app.command("check")
def quality_check(
    path: Optional[str] = typer.Argument("src", help="Kontrol edilecek yol (varsayılansrc/)"),
) -> None:
    """
koşmakruff checkKodu kontrol et

    Examples:
        omc quality check
        omc quality check src/
        omc quality check src/commands/
    """
    if not _check_ruff_installed():
        console.print("[red]❌ ruffYüklü değil, lütfen çalıştırın:[/red]")
        console.print("  [cyan]pip install ruff[/cyan]")
        raise typer.Exit(1)

    target_path = Path(path) if path else Path("src")

    console.print(f"[bold]🔍koşmakruff check {target_path}...[/bold]\n")

    try:
        result = subprocess.run(
            ["ruff", "check", str(target_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]✅ ruff check passed[/green]")
        else:
            console.print(result.stdout)
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            console.print(f"\n[yellow]⚠️Keşfetmek{result.returncode}kaydetmek[/yellow]")
            raise typer.Exit(result.returncode)

    except FileNotFoundError:
        console.print("[red]❌ ruffkomut bulunamadı[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌Yürütme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command("fix")
def quality_fix(
    path: Optional[str] = typer.Argument("src", help="Onarım yolu (varsayılansrc/)"),
) -> None:
    """
koşmakruff check --fixKodu otomatik olarak düzelt

    Examples:
        omc quality fix
        omc quality fix src/
        omc quality fix src/commands/
    """
    if not _check_ruff_installed():
        console.print("[red]❌ ruffYüklü değil, lütfen çalıştırın:[/red]")
        console.print("  [cyan]pip install ruff[/cyan]")
        raise typer.Exit(1)

    target_path = Path(path) if path else Path("src")

    console.print(f"[bold]🔧koşmakruff check --fix {target_path}...[/bold]\n")

    try:
        result = subprocess.run(
            ["ruff", "check", "--fix", str(target_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]✅Tüm sorunlar otomatik olarak düzeltildi[/green]")
        else:
            console.print(result.stdout)
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            console.print(
                f"\n[yellow]⚠️Bazı sorunlar giderildi ama hâlâ var{result.returncode}Sorunların manuel olarak ele alınması gerekiyor[/yellow]"
            )

    except FileNotFoundError:
        console.print("[red]❌ ruffkomut bulunamadı[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌Yürütme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command("type")
def quality_type(
    path: Optional[str] = typer.Argument("src", help="Kontrol edilecek yol (varsayılansrc/)"),
) -> None:
    """
koşmakmypytip kontrolü

    Examples:
        omc quality type
        omc quality type src/
        omc quality type src/commands/
    """
    if not _check_mypy_installed():
        console.print("[red]❌ mypyYüklü değil, lütfen çalıştırın:[/red]")
        console.print("  [cyan]pip install mypy[/cyan]")
        raise typer.Exit(1)

    target_path = Path(path) if path else Path("src")

    console.print(f"[bold]🔍koşmakmypytip kontrolü{target_path}...[/bold]\n")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", str(target_path), "--no-error-summary"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]✅Tip kontrolü başarılı oldu[/green]")
        else:
            # Parse output to count errors
            output = result.stdout + result.stderr
            lines = [
                line for line in output.split("\n") if line.strip() and "error:" in line
            ]
            error_count = len(lines)

            # Show up to 10 errors
            console.print("[yellow]⚠️hata bulundu:[/yellow]\n")
            for line in lines[:10]:
                console.print(f"  {line}")
            if len(lines) > 10:
                console.print(f"\n  ...Ayrıca{len(lines) - 10}hatalar gösterilmiyor")

            console.print(f"\n[yellow]⚠️Keşfetmek{error_count}yazım hataları[/yellow]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]❌ mypykomut bulunamadı[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌Yürütme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command("all")
def quality_all(
    path: Optional[str] = typer.Argument("src", help="İşleme yolu (varsayılansrc/)"),
) -> None:
    """
İlk önce koşblackFormatlayıp tekrar çalıştırınruff checkve sonunda koşmypytip kontrolü

    Examples:
        omc quality all
        omc quality all src/
        omc quality all src/commands/
    """
    if not _check_ruff_installed():
        console.print("[red]❌ ruffYüklü değil, lütfen çalıştırın:[/red]")
        console.print("  [cyan]pip install ruff[/cyan]")
        raise typer.Exit(1)

    if not _check_black_installed():
        console.print("[red]❌ blackYüklü değil, lütfen çalıştırın:[/red]")
        console.print("  [cyan]pip install black[/cyan]")
        raise typer.Exit(1)

    if not _check_mypy_installed():
        console.print("[red]❌ mypyYüklü değil, lütfen çalıştırın:[/red]")
        console.print("  [cyan]pip install mypy[/cyan]")
        raise typer.Exit(1)

    target_path = Path(path) if path else Path("src")

    # Step 1: blackbiçim
    console.print(f"[bold]📝koşmakblackbiçim{target_path}...[/bold]\n")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "black", str(target_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]✅ blackBiçimlendirme tamamlandı[/green]\n")
        else:
            console.print(result.stdout)
            if result.stderr:
                console.print(f"[yellow]⚠️ {result.stderr}[/yellow]")
            console.print()

    except FileNotFoundError:
        console.print("[red]❌ blackkomut bulunamadı[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ blackYürütme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)

    # Step 2: ruff check
    console.print(f"[bold]🔍koşmakruff check {target_path}...[/bold]\n")

    try:
        result = subprocess.run(
            ["ruff", "check", str(target_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]✅ ruff check passed[/green]\n")
        else:
            console.print(result.stdout)
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            console.print(f"\n[yellow]⚠️Keşfetmek{result.returncode}kaydetmek[/yellow]")
            raise typer.Exit(result.returncode)

    except FileNotFoundError:
        console.print("[red]❌ ruffkomut bulunamadı[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ ruffYürütme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)

    # Step 3: mypytip kontrolü
    console.print(f"[bold]🔍koşmakmypytip kontrolü{target_path}...[/bold]\n")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", str(target_path), "--no-error-summary"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]✅ mypyTip kontrolü başarılı oldu[/green]\n")
        else:
            output = result.stdout + result.stderr
            lines = [
                line for line in output.split("\n") if line.strip() and "error:" in line
            ]
            error_count = len(lines)

            console.print("[yellow]⚠️yazmak:[/yellow]\n")
            for line in lines[:10]:
                console.print(f"  {line}")
            if len(lines) > 10:
                console.print(f"\n  ...Ayrıca{len(lines) - 10}hatalar gösterilmiyor")

            console.print(f"\n[yellow]⚠️Keşfetmek{error_count}yazım hataları[/yellow]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]❌ mypykomut bulunamadı[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ mypyYürütme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)

    # All checks passed
    console.print("[bold green]🎉Tüm kontroller geçti![/bold green]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Yardımı varsayılan olarak göster"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
