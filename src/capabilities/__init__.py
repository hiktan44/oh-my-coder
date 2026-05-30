from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
yetenekpaket CLI komut

saglaryetenekpaketdisa aktar, liste, uygulamavegonderislev. 
"""

from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .package import (
    CapabilityPackage as CapabilityPackage,
)
from .package import (
    CapabilityPackageManager,
    get_manager,
)

app = typer.Typer(
    name="cap",
    help="yetenekpaketyonet - disa aktar, iceri aktarvepaylas Agent yapilandirma",
    add_completion=False,
)
console = Console()


def _get_manager() -> CapabilityPackageManager:
    """alyetenekpaketyonet"""
    return get_manager()


@app.command("export")
def export_capability(
    name: str = typer.Argument(..., help="yetenekpaketad"),
    version: str = typer.Option("0.2.0", "--version", "-v", help="surumno (semver)"),
    description: str = typer.Option(None, "--description", "-d", help="islevaciklama"),
    author: str = typer.Option(None, "--author", "-a", help="yazar"),
    tags: str = typer.Option(None, "--tags", "-t", help="etiket (virgulnopuanayir) "),
    config_path: Path = typer.Option(
        None, "--config", "-c", help="yapilandirma dosyasiyol (varsayilanmevcutprojeoku) "
    ),
):
    """
    disa aktaryetenekpaket

    mevcut Agent yapilandirmavurpaketdisa aktaricinyetenekpaket, yonkolaypaylasvetekrarkullan. 

    ornek:
        omc cap export my-config --version 1.0.0 --description "benyapilandirma"
        omc cap export code-review -t "review,python,quality"
    """
    manager = _get_manager()

    # etkilesimtarzgirdieksikbilgi
    if description is None:
        description = Prompt.ask("islevaciklama", default=f"{name} yapilandirmapaket")

    if author is None:
        author = Prompt.ask("yazar", default="anonymous")

    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    # mevcutprojeokuyapilandirma
    agents, model_config, tools, prompts = _load_current_config(config_path)

    # olusturyetenekpaket
    try:
        package = manager.export_from_config(
            name=name,
            version=version,
            description=description,
            author=author,
            tags=tag_list,
            agents=agents,
            model_config=model_config,
            tools=tools,
            prompts=prompts,
            readme=f"# {name}\n\n{description}",
        )

        # dogrulama
        errors = package.validate()
        if errors:
            console.print("[red]dogrulamabasarisiz:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(1)

        console.print(
            Panel.fit(
                f"[green]✓ yetenekpaketdisa aktar[/green]\n\n"
                f"ad: [cyan]{package.name}[/cyan]\n"
                f"surum: [cyan]{package.version}[/cyan]\n"
                f"aciklama: [dim]{package.description}[/dim]\n"
                f"yazar: [dim]{package.author}[/dim]\n"
                f"etiket: [dim]{', '.join(package.tags) or 'yok'}[/dim]\n\n"
                f"yol: [cyan]{manager._get_package_path(name)}[/cyan]",
                title="📦 yetenekpaket",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]disa aktarbasarisiz: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_capabilities(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="gosterdetaylibilgi"),
):
    """
    tumunu listelevaryetenekpaket

    gosteryereldepolamavaryetenekpaket. 

    ornek:
        omc cap list
        omc cap list -v
    """
    manager = _get_manager()
    packages = manager.list_packages()

    if not packages:
        console.print("[dim]geçiciyokyetenekpaket, kullan `omc cap export` olustur[/dim]")
        return

    if verbose:
        # detayliliste
        for pkg in packages:
            console.print(
                Panel(
                    f"[bold cyan]{pkg.name}[/bold cyan] [dim]v{pkg.version}[/dim]\n"
                    f"{pkg.description}\n"
                    f"[dim]yazar: {pkg.author} | "
                    f"etiket: {', '.join(pkg.tags) or 'yok'} | "
                    f"olustur: {pkg.created_at[:10]}[/dim]",
                    border_style="cyan",
                )
            )
    else:
        # basittemiztablo
        table = Table(title=f"yetenekpaketliste ({len(packages)})")
        table.add_column("ad", style="cyan")
        table.add_column("surum", style="dim", width=10)
        table.add_column("aciklama", style="white")
        table.add_column("etiket", style="dim")
        table.add_column("olusturzamanarasinda", style="dim", width=12)

        for pkg in packages:
            table.add_row(
                pkg.name,
                pkg.version,
                (
                    pkg.description[:40] + "..."
                    if len(pkg.description) > 40
                    else pkg.description
                ),
                ", ".join(pkg.tags[:3]),
                pkg.created_at[:10],
            )

        console.print(table)


@app.command("apply")
def apply_capability(
    name: str = typer.Argument(..., help="yetenekpaketad"),
    dry_run: bool = typer.Option(False, "--dry-run", help="ongoz atuygulamasonuc, hayirgercekdegistir"),
    force: bool = typer.Option(False, "--force", "-f", help="zorunluuygulama, hayiripucuonayla"),
):
    """
    uygulamayetenekpaket

    yetenekpaketicindeyapilandirmauygulamakadarmevcutproje. 

    ornek:
        omc cap apply my-config
        omc cap apply my-config --dry-run
    """
    manager = _get_manager()

    package = manager.get_package(name)
    if package is None:
        console.print(f"[red]yetenekpaketmevcut degil: {name}[/red]")
        raise typer.Exit(1)

    # gosteryetenekpaketbilgi
    console.print(
        Panel(
            f"[bold cyan]{package.name}[/bold cyan] v{package.version}\n"
            f"{package.description}\n"
            f"[dim]yazar: {package.author}[/dim]",
            title="📦 yaniuygulamayetenekpaket",
            border_style="cyan",
        )
    )

    # gosteryapilandirmagenel bakis
    config_summary = []
    if package.agents:
        config_summary.append(f"- Agent yapilandirma: {len(package.agents)} ")
    if package.model_config:
        config_summary.append(f"- modelyapilandirma: {len(package.model_config)} ogre")
    if package.tools:
        config_summary.append(f"- arac: {len(package.tools)} ")
    if package.prompts:
        config_summary.append(f"- Prompt sablon: {len(package.prompts)} ")

    if config_summary:
        console.print("[bold]yapilandirmaicerik:[/bold]")
        for item in config_summary:
            console.print(f"  {item}")

    if dry_run:
        console.print("\n[yellow]Dry-run mod, henuzgercekuygulama[/yellow]")
        return

    # onayla
    if not force and not Confirm.ask("\nonaylauygulamabuyapilandirma? "):
        console.print("[dim]iptal edildi[/dim]")
        return

    # uygulamayapilandirma
    try:
        # okumevcutyapilandirma
        current_config = _load_config_file() or {}

        # uygulamayetenekpaket
        new_config = manager.apply_package(name, current_config)

        # kaydetyapilandirma
        _save_config_file(new_config)

        console.print("[green]✓ yetenekpaketuygulama[/green]")

    except Exception as e:
        console.print(f"[red]uygulamabasarisiz: {e}[/red]")
        raise typer.Exit(1)


@app.command("publish")
def publish_capability(
    name: str = typer.Argument(..., help="yetenekpaketad"),
    registry: str = typer.Option(None, "--registry", "-r", help="toplulukbolgedepokutuphaneadres"),
):
    """
    gonderyetenekpaketkadartoplulukbolge

    yetenekpaketpaylaskadartoplulukbolgedepokutuphane (acgondericinde) . 

    ornek:
        omc cap publish my-config
    """
    console.print(
        Panel.fit(
            "[yellow]toplulukbolgeislevacgondericinde[/yellow]\n\n"
            "yetenekpaketgonderislevicindehenuzgelsurumdestek, \n"
            "hedefoncesizolabilirilemanuelpaylasyetenekpaketdosya. \n\n"
            f"[dim]yetenekpaketkonum: ~/.omc/capabilities/{name}.json[/dim]",
            title="🚀 gonder",
            border_style="yellow",
        )
    )


@app.command("show")
def show_capability(
    name: str = typer.Argument(..., help="yetenekpaketad"),
):
    """
    goruntuleyetenekpaketdetay

    ornek:
        omc cap show my-config
    """
    manager = _get_manager()

    package = manager.get_package(name)
    if package is None:
        console.print(f"[red]yetenekpaketmevcut degil: {name}[/red]")
        raise typer.Exit(1)

    # temelbilgi
    console.print(
        Panel(
            f"[bold cyan]{package.name}[/bold cyan] [dim]v{package.version}[/dim]\n\n"
            f"[bold]aciklama:[/bold] {package.description}\n"
            f"[bold]yazar:[/bold] {package.author}\n"
            f"[bold]olusturzamanarasinda:[/bold] {package.created_at}\n"
            f"[bold]etiket:[/bold] {', '.join(package.tags) or 'yok'}",
            title="📦 yetenekpaketdetay",
            border_style="cyan",
        )
    )

    # yapilandirmadetay
    if package.readme:
        console.print("\n[bold]kullanaciklama:[/bold]")
        console.print(package.readme)

    if package.agents:
        console.print(f"\n[bold]Agent yapilandirma ({len(package.agents)}):[/bold]")
        for agent_name in package.agents:
            console.print(f"  - {agent_name}")

    if package.tools:
        console.print(f"\n[bold]aracliste ({len(package.tools)}):[/bold]")
        for tool in package.tools:
            console.print(f"  - {tool}")

    if package.examples:
        console.print(f"\n[bold]kullanornek ({len(package.examples)}):[/bold]")
        for i, example in enumerate(package.examples, 1):
            console.print(f"\n  ornek {i}:")
            for key, value in example.items():
                console.print(f"    {key}: {value}")


@app.command("delete")
def delete_capability(
    name: str = typer.Argument(..., help="yetenekpaketad"),
    force: bool = typer.Option(False, "--force", "-f", help="zorunlusil, hayiripucuonayla"),
):
    """
    silyetenekpaket

    ornek:
        omc cap delete my-config
    """
    manager = _get_manager()

    package = manager.get_package(name)
    if package is None:
        console.print(f"[red]yetenekpaketmevcut degil: {name}[/red]")
        raise typer.Exit(1)

    if not force and not Confirm.ask(f"onaylasilyetenekpaket '{name}'? "):
        console.print("[dim]iptal edildi[/dim]")
        return

    if manager.delete_package(name):
        console.print(f"[green]✓ yetenekpaket '{name}' sil[/green]")
    else:
        console.print("[red]silbasarisiz[/red]")
        raise typer.Exit(1)


def _load_current_config(
    config_path: Optional[Path] = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str], dict[str, Any]]:
    """
    yuklemevcutprojeyapilandirma

    Returns:
        (agents, model_config, tools, prompts)
    """
    # varsayilanyapilandirma
    agents = {}
    model_config = {}
    tools = []
    prompts = {}

    # deneyapilandirma dosyasiyukle
    if config_path and config_path.exists():
        try:
            import json

            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            agents = config.get("agents", {})
            model_config = config.get("model_config", {})
            tools = config.get("tools", [])
            prompts = config.get("prompts", {})
        except Exception:
            pass

    # egeryapilandirmaicinbos, kullanornekyapilandirma
    if not agents:
        agents = {
            "explore": {
                "enabled": True,
                "tier": "medium",
            },
            "analyst": {
                "enabled": True,
                "tier": "medium",
            },
            "planner": {
                "enabled": True,
                "tier": "high",
            },
            "executor": {
                "enabled": True,
                "tier": "high",
            },
        }

    if not model_config:
        model_config = {
            "default_model": "deepseek",
            "temperature": 0.7,
            "max_tokens": 4000,
        }

    if not tools:
        tools = [
            "file_read",
            "file_write",
            "shell_exec",
            "web_search",
        ]

    if not prompts:
        prompts = {
            "system": "You are a helpful coding assistant.",
        }

    return agents, model_config, tools, prompts


def _load_config_file() -> Optional[dict[str, Any]]:
    """yukleprojeyapilandirma dosyasi"""
    config_paths = [
        Path(".omc/config.json"),
        Path("oh-my-coder.json"),
        Path.home() / ".omc" / "config.json",
    ]

    for path in config_paths:
        if path.exists():
            try:
                import json

                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue

    return None


def _save_config_file(config: dict[str, Any]) -> None:
    """kaydetprojeyapilandirma dosyasi"""
    config_dir = Path(".omc")
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "config.json"

    import json

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
