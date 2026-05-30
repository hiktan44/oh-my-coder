from __future__ import annotations

"""
MCP CLIEmir

omc mcp --start              #başlatmakMCP ServerModel önerisistdiomodeli)
omc mcp --install            #oluşturmakClaude Desktop / Cursorile ilgiliMCPYapılandırma
omc mcp --list               #Mevcut araçları listele
omc mcp --status             #Kontrol etmekMCPbağlantı durumu
"""


import contextlib
import json
import sys
from pathlib import Path

import typer
from rich.console import Console

from src.mcp.resources import get_mcp_resources
from src.mcp.server import McpServer
from src.mcp.tools import get_mcp_tools

app = typer.Typer(
    name="mcp",
    help="MCPModel önerisiModel Context Protocol) destek — şu şekildeServerdışarıya maruzAgentyetenek",
)
console = Console()


@app.command()
def start(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="çalışma alanı yolu"),
) -> None:
    """başlatmakMCP ServerModel önerisistdiomodeli)"""
    console.print("[dim]başlatmakoh-my-coder MCP Server...[/dim]")
    console.print("[dim]buna göreCtrl+Cçıkış yapmak[/dim]")
    server = McpServer(workspace=workspace.resolve())
    with contextlib.suppress(KeyboardInterrupt):
        server.run()


@app.command()
def install(
    client: str = typer.Option(
        "claude-desktop",
        "--client",
        "-c",
        help="Müşteri türü:claude-desktopModel önerisiClaude Desktop)/ cursorModel önerisiCursor)/ difyModel önerisiDify)",
    ),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="Proje yolu"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Onayı atla ve doğrudan üzerine yaz"),
) -> None:
    """oluşturmakMCPİstemci yapılandırma dosyası"""
    config: dict = {}

    if client == "claude-desktop":
        config_path = Path.home() / ".claude-desktop" / "mcp.json"
    elif client == "cursor":
        config_path = Path.home() / ".cursor" / "mcp.json"
    elif client == "dify":
        config_path = project_path / "mcp-dify.json"
        config["mcpServers"] = {
            "oh-my-coder": {
                "command": "python3",
                "args": ["-m", "src.mcp.server", "--start"],
                "cwd": str(project_path.resolve()),
            }
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2))
        console.print(f"[green]✅ Dify MCPYapılandırma oluşturuldu: {config_path}[/green]")
        console.print(f"var olmakDifyEkleMCP Server, yapılandırmayı kullan: {config_path}")
        raise typer.Exit(0)
    else:
        console.print(f"[red]❌Desteklenmeyen istemci: {client}[/red]")
        raise typer.Exit(1)

    config_path.parent.mkdir(parents=True, exist_ok=True)

    #Mevcut yapılandırmayı oku
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {"mcpServers": {}}

    existing.setdefault("mcpServers", {})
    proj_abs = project_path.resolve()

    #doldurmaoh-my-coderYapılandırma
    existing["mcpServers"]["oh-my-coder"] = {
        "command": sys.executable,
        "args": ["-m", "src.mcp.server", "--start"],
        "cwd": str(proj_abs),
    }

    if not yes and config_path.exists():
        console.print(f"[yellow]⚠️Yapılandırma dosyası zaten mevcut: {config_path}[/yellow]")
        confirm = typer.prompt("Mevcut yapılandırmanın üzerine yazılsın mı? girmek'yes'devam etmek", default="no")
        if confirm.lower() != "yes":
            console.print("[dim]İptal edildi[/dim]")
            raise typer.Exit(0)

    config_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    console.print(f"[green]✅ MCPYapılandırma yazıldı: {config_path}[/green]")
    console.print(f"müşteri: {client}")
    console.print(f"çalışma dizini: {proj_abs}")
    console.print(f"Tekrar başlat{client}Kullanıma hazır")


@app.command()
def list() -> None:
    """Mevcut olanların hepsini listeleMCP toolsVeresources"""
    tools = get_mcp_tools()
    resources = get_mcp_resources()

    from rich.table import Table

    console.print("\n[bold cyan]🛠 MCP Tools[/bold cyan]")
    table = Table()
    table.add_column("isim", style="green")
    table.add_column("betimlemek", style="white")
    for t in tools:
        table.add_row(t["name"], t["description"][:60])
    console.print(table)

    console.print("\n[bold cyan]📄 MCP Resources[/bold cyan]")
    for r in resources:
        console.print(f"  • [green]{r['uri']}[/green] — {r['description']}")

    console.print(f"\n[dim]yaygın{len(tools)} tools · {len(resources)} resources[/dim]")


@app.command()
def status() -> None:
    """Kontrol etmekMCPbağlantı durumu"""
    #incelemekMCP SDKMevcut mu?
    try:
        import mcp

        sdk_version = getattr(mcp, "__version__", "unknown")
        console.print(f"[green]✅ MCP SDK[/green]Yüklendi(v{sdk_version})")
    except Exception:
        console.print("[yellow]⚠️  MCP SDKKurulu değil[/yellow]")
        console.print("Bu hizmet yerel kullanıyorJSON-RPC stdiosonuçlandırmak(Python 3.9 uyumlu)")
        console.print("GerekirseSDKModel önerisiPython 3.10+):pip install mcp")

    #Çalışma alanını kontrol edin
    workspace = Path.cwd()
    omc_dir = workspace / ".omc"
    if omc_dir.exists():
        console.print(f"\n[green]✅çalışma alanı[/green] {workspace}")
        console.print("  .omc/var olmak,checkpointVeskillFonksiyon mevcut")
    else:
        console.print(f"\n[yellow]⚠️çalışma alanı[/yellow] {workspace}")
        console.print("  .omc/Mevcut değil, bazı işlevler sınırlı olabilir")

    console.print("\n[bold]Mevcut komutlar[/bold]")
    console.print("  omc mcp --start      #başlatmakServer")
    console.print("  omc mcp --install    #İstemci yapılandırması oluştur")
    console.print("  omc mcp --list       #Araçları ve kaynakları listeleyin")
