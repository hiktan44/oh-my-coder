from __future__ import annotations

"""
Server CLI - omc serverEmir

omc server [--port PORT] [--host HOST] [--api-key KEY] [--no-open]
omc server stop

belge:docs/guide/server-mode.md
API: http://localhost:{port}/docsModel önerisiSwagger UI)
"""


import asyncio
import contextlib
import os
import signal
import socket
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel

from src.api.server_api import create_app

console = Console()

app = typer.Typer(
    name="server",
    help="Uzaktan başlatAIProgramlama AsistanıServerModel önerisiHTTP REST API)",
    add_completion=False,
)

#küresel süreç referansı
_server_process: Optional[uvicorn.Server] = None
_config: Optional[dict] = None


def _find_free_port(port: int) -> int:
    """Kullanılabilir bağlantı noktalarını bulun"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) != 0:
            return port
    #Bağlantı noktası dolu, deneyin+1
    for p in range(port + 1, port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
            if s2.connect_ex(("localhost", p)) != 0:
                return p
    return port + 1


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


@app.command("start")
def start(
    port: int = typer.Option(8080, "--port", "-p", help="dinleme portu"),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="dinleme adresi (0.0.0.0 =Öğe sayısı",  # nosec B104
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="APIAnahtar (ayarlanmadığı takdirde kimlik doğrulama yapılmayacaktır)"
    ),
    no_auth: bool = typer.Option(
        False, "--no-auth", help="Kimlik doğrulamayı devre dışı bırak (ile--api-keybirbirini dışlayan)"
    ),
    no_open: bool = typer.Option(False, "--no-open", help="Başlangıçtan sonra tarayıcı açılmıyor"),
    reload: bool = typer.Option(False, "--reload", help="Geliştirme modu: kod değişiklikleri için otomatik yeniden yükleme"),
) -> None:
    """başlatmakServer"""
    global _server_process, _config

    #karşılıklı dışlama kontrolü
    if api_key and no_auth:
        console.print("[red]--api-keyVe--no-authaynı anda kullanılamaz[/red]")
        raise typer.Exit(1)

    #Bağlantı noktası işgalini onaylayın
    if _is_port_in_use(port):
        free = _find_free_port(port)
        console.print(f"[yellow]Uyarı: bağlantı noktası{port}Zaten meşgul[/yellow]")
        if free != port:
            console.print(f"[green]→Otomatik olarak bağlantı noktasına geçildi{free}lütfen ziyaret edinhttp://localhost:{free}[/green]")
            port = free
        else:
            console.print("[red]✗Kullanılabilir bağlantı noktası bulunamıyor[/red]")
            raise typer.Exit(1)

    # API Keyvar olmakWeb UIyapılandırma, komut satırı istemde bulunmuyor
    effective_key = os.getenv("OMC_SERVER_API_KEY") or _load_api_key_from_config()

    #yaratmakFastAPI app
    fastapi_app, store = create_app(api_key=effective_key)
    _config = {
        "port": port,
        "host": host,
        "api_key": effective_key,
        "store": store,
    }

    #Başlangıç ​​parametreleri
    api_url = f"http://localhost:{port}"
    docs_url = f"{api_url}/docs"
    redoc_url = f"{api_url}/redoc"

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🚀 Oh My Coder Server[/bold cyan]\n\n"
            f"  [green]API:[/]   {api_url}\n"
            f"  [green]Docs:[/]  {docs_url}\n"
            f"  [green]Redoc:[/]{redoc_url}\n"
            f"  [green]Host:[/]  {host}\n"
            f"  [green]Port:[/]  {port}\n"
            + (
                "  [yellow]Auth:[/]  API KeyEtkinleştirilmiş\n"
                if effective_key
                else "  [dim]Auth:[/]Sertifika yok\n"
            ),
            border_style="cyan",
        )
    )
    console.print()
    console.print("[dim]buna göreCtrl+CHizmeti durdur[/dim]")
    console.print()

    #Sinyal işlemeyi kaydedin
    def stop_handler(sig: int, frame) -> None:
        console.print("\n[yellow]Durdurma sinyali alındı, kapatılıyor...[/yellow]")
        if _server_process:
            _server_process.should_exit = True

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    #başlatmakuvicorn
    config = uvicorn.Config(
        fastapi_app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
    )
    _server_process = uvicorn.Server(config)

    #Tarayıcıyı aç
    if not no_open:
        import threading

        threading.Timer(1.5, _open_browser, args=(api_url,)).start()

    #Eşzamanlı olarak çalıştır (engelleme)
    asyncio.run(_server_process.serve())


@app.command("stop")
def stop() -> None:
    """durmakServer(geçmekPIDbelge)"""
    pid_file = Path.home() / ".omc" / "server.pid"
    if not pid_file.exists():
        console.print("[yellow]ServerBaşlatılmadı (bulunamadı)PIDbelge)[/yellow]")
        raise typer.Exit(1)
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink()
        console.print(f"[green]✓ Server (PID {pid})Durduruldu[/green]")
    except ProcessLookupError:
        console.print("[yellow]İşlem artık mevcut değil, temizleyinPIDbelge[/yellow]")
        pid_file.unlink()
    except Exception as e:
        console.print(f"[red]✗Durdurma başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status() -> None:
    """incelemekServerÇalışma durumu"""
    #OkumakPIDbelge
    pid_file = Path.home() / ".omc" / "server.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  #Sürecin var olup olmadığını kontrol edin
            console.print(f"[green]✓ ServerKoşma(PID {pid})[/green]")
        except (ProcessLookupError, ValueError):
            console.print("[yellow]⚠ PIDDosya mevcut ancak süreç artık mevcut değil[/yellow]")
            pid_file.unlink()
            console.print("[red]✗ ServerÇalışmıyor[/red]")
    else:
        console.print("[red]✗ ServerÇalışmıyor[/red]")


@app.command("logs")
def logs(
    lines: int = typer.Option(50, "-n", "--lines", help="En sonları gösterNTAMAM"),
) -> None:
    """Kontrol etmekServerkayıt"""
    log_file = Path.home() / ".omc" / "logs" / "server.log"
    if not log_file.exists():
        console.print("[yellow]Henüz günlük dosyası yok[/yellow]")
        raise typer.Exit(1)
    content = log_file.read_text(encoding="utf-8", errors="replace")
    log_lines = content.splitlines()
    for line in log_lines[-lines:]:
        console.print(f"[dim]{line}[/dim]")


# ---------------------------------------------------------------------------
#Yardımcı işlevi
# ---------------------------------------------------------------------------


def _load_api_key_from_config() -> Optional[str]:
    """itibaren~/.omc/.envOkumakAPI Key"""
    env_file = Path.home() / ".omc" / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(errors="replace").splitlines():
        if line.strip().startswith("OMC_SERVER_API_KEY"):
            _, _, key = line.partition("=")
            return key.strip()
    return None


def _open_browser(url: str) -> None:
    import platform
    import subprocess

    with contextlib.suppress(Exception):
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", url])
        elif system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", url])
        else:
            import webbrowser
            webbrowser.open(url)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """omc server— uzaktan başlatAIProgramlama AsistanıHTTP API"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
