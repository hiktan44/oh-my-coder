from __future__ import annotations

"""
AgentYapılandırmaCLIEmir

omc config load <file>    -yükYAML/JSONYapılandırma
omc config validate <file> -Yapılandırma dosyasını doğrulayın
omc config list           -Yerel yapılandırmayı listele
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config.agent_config import (
    list_configs_in_dir,
    load_config_file,
    validate_config_file,
)

app = typer.Typer(
    name="agent-config",
    help="AgentHızlı arama aracı-Yükle, doğrulaYAML/JSONYapılandırma dosyası",
    add_completion=False,
)
console = Console()


@app.command("load")
def load_config(
    file: Path = typer.Argument(..., help="Yapılandırma dosyası yolu(.yaml/.yml/.json)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Ayrıntıları göster"),
) -> None:
    """
yükAgentYapılandırma dosyası

Örnek:
        omc config load agents/code_review.yaml
        omc config load config/agent.json -v
    """
    try:
        config = load_config_file(file)

        console.print(
            Panel.fit(
                f"[green]✓ Yapılandırma başarıyla yüklendi[/green]\n\n"
                f"isim: [cyan]{config.name}[/cyan]\n"
                f"betimlemek: [dim]{config.description or 'hiçbiri'}[/dim]\n"
                f"Modeli: [cyan]{config.model}[/cyan]",
                title="📋 AgentYapılandırma",
                border_style="green",
            )
        )

        if verbose:
            console.print("\n[bold]alet:[/bold]")
            for tool in config.tools:
                console.print(f"  - {tool}")

            console.print("\n[bold]Ortam yapılandırması:[/bold]")
            console.print(f"  max_tokens: {config.environment.max_tokens}")
            console.print(f"  temperature: {config.environment.temperature}")
            console.print(f"  timeout: {config.environment.timeout}s")

            console.print("\n[bold]İzin kuralları:[/bold]")
            perm = config.permissions
            console.print(f"  allowed_patterns: {perm.get('allowed_patterns', 'hiçbiri')}")
            console.print(f"  denied_patterns: {perm.get('denied_patterns', 'hiçbiri')}")
            console.print(f"  require_approval: {perm.get('require_approval', 'hiçbiri')}")

    except FileNotFoundError:
        console.print(f"[red]❗Yapılandırma dosyası mevcut değil: {file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❗Yükleme başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command("validate")
def validate_config(
    file: Path = typer.Argument(..., help="Yapılandırma dosyası yolu"),
) -> None:
    """
doğrulamakAgentYapılandırma dosyasının yasallığı

Örnek:
        omc config validate agents/code_review.yaml
    """
    valid, errors = validate_config_file(file)

    if valid:
        console.print(f"[green]✓Yapılandırma dosyası yasal: {file}[/green]")
    else:
        console.print(f"[red]✗Yanlış yapılandırma dosyası: {file}[/red]\n")
        for error in errors:
            console.print(f"  - [red]{error}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_configs(
    dir: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="Arama dizini (varsayılan: ~/.omc/agents/)",
    ),
) -> None:
    """
yerel listeleAgentYapılandırma dosyası

Örnek:
        omc config list
        omc config list --dir ./agents/
    """
    if dir is None:
        dir = Path.home() / ".omc" / "agents"

    configs = list_configs_in_dir(dir)

    if not configs:
        console.print(
            f"[dim]Dizinde yapılandırma dosyası yok: {dir}\n"
            "kullanmak`omc config load <file>`Yapılandırmayı yükle[/dim]"
        )
        return

    table = Table(title=f"AgentYapılandırma listesi({len(configs)})")
    table.add_column("belge", style="cyan")
    table.add_column("isim", style="green")
    table.add_column("Modeli", style="dim")
    table.add_column("Bilgi almak için bir örnek oluşturun", style="dim", width=8)

    for path in configs:
        try:
            config = load_config_file(path)
            table.add_row(
                Path(path).name,
                config.name,
                config.model,
                str(len(config.tools)),
            )
        except Exception:
            table.add_row(Path(path).name, "[red]Ayrıştırma başarısız oldu[/red]", "-", "-")

    console.print(table)


@app.command("create")
def create_from_config(
    file: Path = typer.Argument(..., help="Yapılandırma dosyası yolu"),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Çıkış yolu (varsayılan olarak terminale yazdırılır)",
    ),
) -> None:
    """
Yapılandırmadan oluşturAgent(yapılandırma anlık görüntüsünü oluştur)

Örnek:
        omc config create agents/code_review.yaml
        omc config create agents/code_review.yaml -o .omc/my_agent.json
    """
    try:
        config = load_config_file(file)
        data = config.to_dict()

        import json

        content = json.dumps(data, ensure_ascii=False, indent=2)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
            console.print(f"[green]✓şuraya kaydedildi:: {output}[/green]")
        else:
            console.print(content)

    except FileNotFoundError:
        console.print(f"[red]❗Yapılandırma dosyası mevcut değil: {file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❗Oluşturma başarısız oldu: {e}[/red]")
        raise typer.Exit(1)
