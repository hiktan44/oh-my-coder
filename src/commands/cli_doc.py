"""
omc docEmir-Belge oluşturma ve yönetimi

Belge oluşturma, doğrulama, senkronizasyon ve diğer işlevleri sağlar:
- omc doc generate    #oluşturmakAPIbelge
- omc doc check       #Belge senkronizasyon durumunu kontrol edin
- omc doc serve       #Belge yerel sunucusunu başlatın
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

app = typer.Typer(name="doc", help="Doküman yönetimi-Belirtilenleri yürüt")
console = Console()

DOCS_DIR = Path("docs")
README_PATH = Path("README.md")


@app.command("generate")
def generate_docs(
    output: Path = typer.Option(Path("docs/api"), "--output", "-o", help="Çıkış dizini"),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="Çıkış formatı: markdown, json"
    ),
):
    """Otomatik olarak oluşturulduAPIbelge"""
    console.print("[bold blue]📚oluşturmakAPIbelge...[/bold blue]")

    output.mkdir(parents=True, exist_ok=True)

    #TOPLAMAKCLIkomut bilgisi
    cli_info = _collect_cli_commands()

    #TOPLAMAKWeb APIuç nokta
    api_info = _collect_web_api()

    if format == "json":
        _write_json_docs(output, cli_info, api_info)
    else:
        _write_markdown_docs(output, cli_info, api_info)

    console.print(f"[green]✅Dokümantasyon şu şekilde oluşturuldu:{output}[/green]")


@app.command("check")
def check_docs():
    """Belge senkronizasyon durumunu kontrol edin"""
    console.print("[bold blue]🔍Belge senkronizasyon durumunu kontrol edin...[/bold blue]")

    issues = []

    #incelemekREADMEvar
    if not README_PATH.exists():
        issues.append("❌ README.mdçubuk gösterilmiyor")

    #incelemekdocsDizin yapısı
    expected_dirs = ["guide", "api", "features", "agents"]
    for d in expected_dirs:
        if not (DOCS_DIR / d).exists():
            issues.append(f"❌ docs/{d}/Dizin eksik")

    #incelemekCLIKomut belgelenmiş mi?
    cli_commands = _collect_cli_commands()
    for cmd in cli_commands:
        doc_file = DOCS_DIR / "api" / f"{cmd['name']}.md"
        if not doc_file.exists():
            issues.append(f"⚠️ CLIEmir'{cmd['name']}'eksik belgeler")

    #Referans verilmeyen dokümantasyon dosyalarını kontrol edin (TODO:Hizmet durumu

    if issues:
        console.print(
            Panel("\n".join(issues[:10]), title="Bulunan sorunlar", border_style="yellow")
        )
        if len(issues) > 10:
            console.print(f"...Ayrıca{len(issues) - 10}kaydetmek")
    else:
        console.print("[green]✅Belge iyi durumda[/green]")


@app.command("serve")
def serve_docs(
    port: int = typer.Option(8080, "--port", "-p", help="servis portu"),
):
    """Belge yerel önizleme sunucusunu başlatın"""
    import http.server
    import socketserver

    docs_path = DOCS_DIR.resolve()
    if not docs_path.exists():
        console.print("[red]❌ docs/Dizin mevcut değil[/red]")
        raise typer.Exit(1)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(docs_path), **kwargs)

    console.print(f"[green]📖Doküman sunucusu başlıyor: http://localhost:{port}[/green]")
    console.print(f"[dim]kök dizin: {docs_path}[/dim]")

    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]👋Sunucu durduruldu[/yellow]")


@app.command("index")
def generate_index():
    """Belge dizini oluştur"""
    console.print("[bold blue]📑,...[/bold blue]")

    tree = Tree("📚Belge yapısı")

    for item in sorted(DOCS_DIR.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            branch = tree.add(f"📁 {item.name}/")
            for sub in sorted(item.iterdir()):
                if sub.is_file() and sub.suffix == ".md":
                    branch.add(f"📄 {sub.name}")
        elif item.suffix == ".md":
            tree.add(f"📄 {item.name}")

    console.print(tree)


# =====dahili fonksiyon=====


def _collect_cli_commands() -> list[dict]:
    """Yetenek paketi yönetimiCLIkomut bilgisi"""
    commands = []

    #itibarencli.pyKomut bilgilerini çıkarın (basitleştirilmiş versiyon)
    cli_dir = Path(__file__).parent
    for py_file in cli_dir.glob("cli_*.py"):
        cmd_name = py_file.stem.replace("cli_", "")
        if cmd_name == "doc":
            continue

        #Dosya çıkarma işlemini okuyunhelpmetin
        help_text = ""
        try:
            content = py_file.read_text(encoding="utf-8")
            #Basit çıkarmadocstring
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    help_text = content[start:end].strip().split("\n")[0]
        except Exception:
            pass

        commands.append(
            {
                "name": cmd_name,
                "file": py_file.name,
                "help": help_text or f"{cmd_name}Emir",
            }
        )

    return sorted(commands, key=lambda x: x["name"])


def _collect_web_api() -> list[dict]:
    """Yetenek paketi yönetimiWeb APIuç nokta bilgisi"""
    endpoints = []

    web_app = Path("src/web/app.py")
    if not web_app.exists():
        return endpoints

    try:
        content = web_app.read_text(encoding="utf-8")
        import re

        #kibrit@app.get/post/put/deleteDekoratör
        pattern = r'@app\.(get|post|put|delete)\(["\']([^"\']+)["\']'
        for match in re.finditer(pattern, content):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append(
                {
                    "method": method,
                    "path": path,
                }
            )
    except Exception:
        pass

    return endpoints


def _write_markdown_docs(output: Path, cli_info: list, api_info: list):
    """yazmakMarkdownbelgeyi biçimlendir"""
    # CLIkomut belgeleri
    cli_md = output / "cli-commands.md"
    with cli_md.open("w", encoding="utf-8") as f:
        f.write("# CLIKomut referansı\n\n")
        f.write("otomatik olarak oluşturuldu`omc doc generate`\n\n")
        f.write("|Emir|göstermek|belge|\n")
        f.write("|------|------|------|\n")
        for cmd in cli_info:
            f.write(f"| `{cmd['name']}` | {cmd['help']} | `{cmd['file']}` |\n")

    # Web APIbelge
    api_md = output / "web-api.md"
    with api_md.open("w", encoding="utf-8") as f:
        f.write("# Web APIbaşvurmak\n\n")
        f.write("otomatik olarak oluşturuldu`omc doc generate`\n\n")
        f.write("|yöntem|yol|\n")
        f.write("|------|------|\n")
        for ep in api_info:
            f.write(f"| `{ep['method']}` | `{ep['path']}` |\n")

    console.print(f"  [dim]yazmak{cli_md}[/dim]")
    console.print(f"  [dim]yazmak{api_md}[/dim]")


def _write_json_docs(output: Path, cli_info: list, api_info: list):
    """yazmakJSONbelgeyi biçimlendir"""
    data = {
        "cli_commands": cli_info,
        "web_api": api_info,
        "generated_at": str(Path().cwd()),
    }

    json_path = output / "api-reference.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    console.print(f"  [dim]yazmak{json_path}[/dim]")
