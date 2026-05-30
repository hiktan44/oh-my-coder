from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
hafıza aktarımıCLI -Yapılandırmayı diğer araçlardan içe aktarın

Emir:
- omc migrate claude <path>     #itibarenClaude Codeiçe aktarmakCLAUDE.mdYapılandırma
- omc migrate gemini <path>     #itibarenGemini CLIçalışma alanı
- omc migrate list              #Desteklenen taşıma kaynaklarını listeleyin
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="hafıza aktarımı-Yapılandırmayı diğer araçlardan içe aktarın")
console = Console()


#Desteklenen taşıma kaynakları
MIGRATION_SOURCES = {
    "claude": {
        "name": "Claude Code",
        "config_file": "CLAUDE.md",
        "description": "itibarenClaude CodeProje yapılandırmasını içe aktarma",
        "fields": ["working_directory", "agent", "commands"],
    },
    "gemini": {
        "name": "Gemini CLI",
        "config_file": ".clinerules",
        "description": "itibarenGemini CLIKural yapılandırmasını içe aktarma",
        "fields": ["rules", "model", "project"],
    },
}


@app.command("list")
def list_sources():
    """Desteklenen taşıma kaynaklarını listeleyin"""
    table = Table(title="Desteklenen taşıma kaynakları")
    table.add_column("kaynak", style="cyan")
    table.add_column("Yenilemeye zorla", style="yellow")
    table.add_column("betimlemek", style="white")

    for info in MIGRATION_SOURCES.values():
        table.add_row(
            info["name"],
            info["config_file"],
            info["description"],
        )

    console.print(table)
    console.print(
        "\n[dim]kullanmak'omc migrate claude <path>'veya'omc migrate gemini <path>'çalışma alanı[/dim]"
    )


@app.command("claude")
def migrate_claude(
    path: Optional[Path] = typer.Argument(
        None,
        help="Proje yolu (varsayılan geçerli dizin)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Gerçek yürütme olmadan yalnızca içe aktarılan içerik görüntülenir.",
    ),
):
    """itibarenClaude Codeçalışma alanı"""
    project_path = path or Path.cwd()
    claude_md = project_path / "CLAUDE.md"

    if not claude_md.exists():
        console.print("[red]Hata: bulunamadıCLAUDE.mdbelge[/red]")
        console.print(f"[dim]Lütfen proje dizinine gidin: {project_path}Oluşturulma tarihiCLAUDE.md[/dim]")
        raise typer.Exit(1)

    console.print(f"[cyan]OkumakCLAUDE.md from {project_path}...[/cyan]")

    content = claude_md.read_text(encoding="utf-8")

    if dry_run:
        console.print("[yellow]===İçerik önizlemesini içe aktar===[/yellow]")
        console.print(content[:500] + "..." if len(content) > 500 else content)
        console.print(f"\n[dim]yaygın{len(content)}karakter[/dim]")
        return

    #ayrıştırmakCLAUDE.mdiçerik ve dönüştürme
    _parse_claude_config(content)

    #kaydetOMChafıza dizini
    memory_dir = Path.home() / ".omc" / "memory" / "imported"
    memory_dir.mkdir(parents=True, exist_ok=True)

    output_file = memory_dir / f"claude_import_{project_path.name}.md"
    output_file.write_text(
        f"#itibarenClaude Codeiçe aktarmak\n\n"
        f"kaynak: {project_path}\n"
        f"İçe aktarma zamanı: {__import__('datetime').datetime.now().isoformat()}\n\n"
        f"---\n\n"
        f"{content}",
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green]Yapılandırma içe aktarıldı: {output_file}")
    console.print("[dim]mevcut'omc memory view'İçe aktarılan anıları görüntüle[/dim]")


@app.command("gemini")
def migrate_gemini(
    path: Optional[Path] = typer.Argument(
        None,
        help="Proje yolu (varsayılan geçerli dizin)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Gerçek yürütme olmadan yalnızca içe aktarılan içerik görüntülenir.",
    ),
):
    """itibarenGemini CLIçalışma alanı"""
    project_path = path or Path.cwd()

    # Gemini CLIkullanmak.clinerulesveya.clinerules.json
    clinerules = project_path / ".clinerules"
    clinerules_json = project_path / ".clinerules.json"

    config_file = None
    if clinerules.exists():
        config_file = clinerules
    elif clinerules_json.exists():
        config_file = clinerules_json

    if not config_file:
        console.print("[red]Hata: bulunamadı.clinerulesbelge[/red]")
        console.print(f"[dim]Lütfen proje dizinine gidin: {project_path}Oluşturulma tarihi.clinerules[/dim]")
        raise typer.Exit(1)

    console.print(f"[cyan]Okumak{config_file.name} from {project_path}...[/cyan]")

    content = config_file.read_text(encoding="utf-8")

    if dry_run:
        console.print("[yellow]===İçerik önizlemesini içe aktar===[/yellow]")
        console.print(content[:500] + "..." if len(content) > 500 else content)
        console.print(f"\n[dim]yaygın{len(content)}karakter[/dim]")
        return

    #kaydetOMChafıza dizini
    memory_dir = Path.home() / ".omc" / "memory" / "imported"
    memory_dir.mkdir(parents=True, exist_ok=True)

    output_file = memory_dir / f"gemini_import_{project_path.name}.md"
    output_file.write_text(
        f"#itibarenGemini CLIiçe aktarmak\n\n"
        f"kaynak: {project_path}\n"
        f"Yenilemeye zorla: {config_file.name}\n"
        f"İçe aktarma zamanı: {__import__('datetime').datetime.now().isoformat()}\n\n"
        f"---\n\n"
        f"{content}",
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green]Yapılandırma içe aktarıldı: {output_file}")
    console.print("[dim]mevcut'omc memory view'İçe aktarılan anıları görüntüle[/dim]")


def _parse_claude_config(content: str) -> dict:
    """ayrıştırmakCLAUDE.mdiçerik"""
    config = {
        "working_directory": None,
        "agent": None,
        "commands": [],
    }

    lines = content.split("\n")
    in_commands = False

    for line in lines:
        if line.startswith("## Working Directory:"):
            config["working_directory"] = line.split(":", 1)[1].strip()
        elif line.startswith("## Agent:"):
            config["agent"] = line.split(":", 1)[1].strip()
        elif "## Commands" in line:
            in_commands = True
        elif in_commands and line.strip().startswith("- "):
            config["commands"].append(line.strip()[2:])

    return config


if __name__ == "__main__":
    app()
