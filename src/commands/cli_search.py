from __future__ import annotations

from typing import Optional

"""
Search CLI - omc searchEmir

omc search <query> [--language LANG] [--repo REPO] [--limit N]
                  [--json|--table|--code] [--status] [--setup]

omc search setup   #YapılandırmaSourcegraph API Key
omc search status  #incelemekAPI/CLIKullanılabilirlik
"""


import typer
from rich.console import Console
from rich.panel import Panel

from src.tools.sourcegraph import (
    SearchResult,
    check_status,
    install_src_cli,
    search,
    setup_api_key,
)

console = Console()

app = typer.Typer(
    name="search",
    help="kod arama-geçmekSourcegraphGenel kod depolarında arama yapın",
    add_completion=False,
)


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="arama sorgusu, destekSourcegraphArama sözdizimi"),
    language: Optional[str] = typer.Option(
        None, "--language", "-l", help="Dil filtreleme, örneğinrust/python/go"
    ),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Depo filtreleme, destekglobmodeli"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Döndürülen sonuç sayısı (1-100)"),
    output: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="Çıkış formatı: table(çarşaf)/ code(kod parçacığı)/ json",
    ),
    json_output: bool = typer.Option(False, "--json", help="JSONçıktı"),
    code_output: bool = typer.Option(False, "--code", help="AIKolay kod formatı çıktısı"),
    after: Optional[str] = typer.Option(
        None, "--after", help="Zaman filtresi, sonrası (ör. 2024)-01-01)"
    ),
    before: Optional[str] = typer.Option(None, "--before", help="zaman filtresi, önceki"),
) -> None:
    """aramakGitHub/GitLabGenel kod tabanını bekleyin"""
    result: SearchResult = search(
        query=query,
        language=language,
        repo=repo,
        limit=limit,
        after=after,
        before=before,
    )

    #çıktı
    if json_output or output == "json":
        console.print(result.format_json())
    elif code_output or output == "code":
        console.print(result.format_code(limit=min(limit, 10)))
    else:
        console.print()
        if result.source == "none":
            console.print(
                Panel.fit(
                    "[bold red]⚠ SourcegraphYapılandırılmadı[/bold red]\n\n"
                    "Yapılandırma yöntemi:\n"
                    "  [cyan]omc search setup[/cyan]  -YapılandırmaAPI Key\n"
                    "  [cyan]omc search install[/cyan] -Düzenlemeksrc CLI",
                    border_style="red",
                )
            )
            for w in result.warnings:
                console.print(f"  [dim]- {w}[/dim]")
        else:
            console.print(result.format_table(limit=limit))
            console.print()
            console.print(
                f"[dim]arka uç: {result.source}  "
                f"Sorgu: {query}  "
                f"dil: {language or 'Tümü'}  "
                f"depo: {repo or 'Tümü'}[/dim]"
            )


@app.command("setup")
def setup_cmd(
    api_key: Optional[str] = typer.Argument(
        None, help="Sourcegraph API Key(Atlanırsa giriş istenir)"
    ),
    install_cli: bool = typer.Option(False, "--cli", help="Aynı anda yüklesrc CLI"),
) -> None:
    """YapılandırmaSourcegraph API Key"""
    if install_cli:
        console.print("[dim]Kurulumsrc CLI...[/dim]")
        ok, msg = install_src_cli()
        if ok:
            console.print(f"[green]✓ {msg}[/green]")
        else:
            console.print(f"[red]✗ {msg}[/red]")
            console.print("[dim]Manuel kurulum: https://sourcegraph.com/cli[/dim]")

    if not api_key:
        try:
            import getpass

            api_key = getpass.getpass("Sourcegraph API Key: ").strip()
        except Exception:
            console.print("[red]Şifre okunamıyor, lütfen doğrudan iletinAPI Key[/red]")
            raise typer.Exit(1)

    if not api_key:
        console.print("[red]API Keyboş olamaz[/red]")
        raise typer.Exit(1)

    ok, msg = setup_api_key(api_key)
    if ok:
        console.print(f"[green]✓ {msg}[/green]")
        console.print()
        console.print(
            "[dim]Elde etmekAPI Key: https://sourcegraph.com/user/settings/tokens[/dim]"
        )
        console.print("[dim]özgürtier:Ayda 100.000 arama, günlük kullanım için yeterli[/dim]")
    else:
        console.print(f"[red]✗ {msg}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status_cmd() -> None:
    """incelemekSourcegrapharama durumu"""
    status = check_status()

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🔍 Sourcegrapharama durumu[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    # APIdurum
    api = status["api"]
    if api["available"]:
        console.print(
            f"  [green]✓[/green] Sourcegraph API  [dim]{api['endpoint']}[/dim]"
        )
        console.print(f"      Key: {api['key_prefix']}")
    else:
        console.print(
            "  [red]✗[/red] Sourcegraph API  [dim]YapılandırılmadıSOURCEGRAPH_API_KEY[/dim]"
        )
        console.print("Elde etmek: https://sourcegraph.com/user/settings/tokens")

    # CLIdurum
    cli = status["cli"]
    if cli["available"]:
        console.print(f"  [green]✓[/green] src CLI  [dim]{cli['path']}[/dim]")
    else:
        console.print("  [red]✗[/red] src CLI  [dim]Kurulu değil[/dim]")
        console.print("Düzenlemek: [cyan]omc search install[/cyan]")

    console.print()
    rec = status["recommendation"]
    if rec == "api":
        console.print("  [green]tavsiye etmek:kullanmakSourcegraph API[/green]")
    elif rec == "cli":
        console.print("  [green]tavsiye etmek:kullanmaksrc CLI[/green]")
    else:
        console.print("  [yellow]⚠Lütfen önce yapılandırınAPI Keyveya yükleyinsrc CLI[/yellow]")
        console.print("  [cyan]omc search setup[/cyan]  #YapılandırmaAPI Key")
        console.print("  [cyan]omc search install[/cyan]  #Düzenlemeksrc CLI")


@app.command("install")
def install_cmd() -> None:
    """Düzenlemeksrc CLI"""
    console.print("[dim]Kurulumsrc CLI...[/dim]")
    ok, msg = install_src_cli()
    if ok:
        console.print(f"[green]✓ {msg}[/green]")
    else:
        console.print(f"[red]✗ {msg}[/red]")
        console.print()
        console.print("Manuel kurulum yöntemi:")
        console.print("  macOS:  [cyan]brew install sourcegraph/tap/src[/cyan]")
        console.print(
            "  Linux:  [cyan]curl -L https://sourcegraph.com/.api/src-cli.sh | sh[/cyan]"
        )
        console.print("  Windows:[cyan]scoop install src[/cyan]")
        console.print()
        console.print("İndirme sayfası: https://sourcegraph.com/cli")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Yardımı varsayılan olarak göster"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
