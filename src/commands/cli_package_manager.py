from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Çok platformlu paket yöneticisi- omc pkg

DestekHomebrew/npm/scoop/winget/AURPaket yöneticisini bekleyin,
Geliştirme araçlarının birleşik kurulumu ve yönetimi.

Usage:
    omc pkg install <package>    #Kurulum paketi
    omc pkg search <query>      #Paket ara
    omc pkg list                #Liste yüklendi
    omc pkg update              #Paketi güncelle
"""


import platform
import subprocess
from enum import Enum
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Çok platformlu paket yöneticisi-Birleşik yönetimHomebrew/npm/scoop/winget/AUR")
console = Console()


class Platform(Enum):
    """Desteklenen platformlar"""

    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"


class PackageManager(Enum):
    """Paket yöneticisi"""

    HOMEBREW = "homebrew"
    NPM = "npm"
    PIP = "pip"
    SCOOP = "scoop"
    WINGET = "winget"
    AUR = "aur"
    YARN = "yarn"
    PNPM = "pnpm"


def get_current_platform() -> Platform:
    """Mevcut platformu edinin"""
    system = platform.system().lower()
    if system == "darwin":
        return Platform.MACOS
    if system == "linux":
        return Platform.LINUX
    if system == "windows":
        return Platform.WINDOWS
    return Platform.LINUX


def get_available_managers() -> list[PackageManager]:
    """Kullanılabilir paket yöneticilerini edinin"""
    available = []
    system = get_current_platform()

    #Her paket yöneticisinin mevcut olup olmadığını kontrol edin
    managers = [
        (PackageManager.NPM, "npm"),
        (PackageManager.YARN, "yarn"),
        (PackageManager.PNPM, "pnpm"),
        (PackageManager.PIP, "pip3"),
    ]

    if system == Platform.MACOS:
        managers.extend(
            [
                (PackageManager.HOMEBREW, "brew"),
            ]
        )
    elif system == Platform.LINUX:
        managers.extend(
            [
                (PackageManager.AUR, "yay"),
            ]
        )
    elif system == Platform.WINDOWS:
        managers.extend(
            [
                (PackageManager.SCOOP, "scoop"),
                (PackageManager.WINGET, "winget"),
            ]
        )

    for manager, cmd in managers:
        if _is_command_available(cmd):
            available.append(manager)

    return available


def _is_command_available(cmd: str) -> bool:
    """Komutun mevcut olup olmadığını kontrol edin"""
    try:
        result = subprocess.run(
            ["which", cmd] if platform.system() != "Windows" else ["where", cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _run_command(cmd: list[str], capture: bool = True) -> tuple:
    """Komutu çalıştır"""
    try:
        if capture:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0, result.stdout, result.stderr
        result = subprocess.run(cmd, timeout=60)
        return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception:
        return False, "", "unavailable"


#Önerilen yaygın olarak kullanılan geliştirme araçları
RECOMMENDED_PACKAGES = {
    "cli": [
        {
            "name": "git",
            "desc": "sürüm kontrolü",
            "managers": ["brew", "scoop", "winget", "aur"],
        },
        {"name": "gh", "desc": "GitHub CLI", "managers": ["brew", "scoop", "winget"]},
        {"name": "lazygit", "desc": "terminalGitmüşteri", "managers": ["brew", "scoop"]},
        {"name": "delta", "desc": "GitFark görüntüleyici", "managers": ["brew", "scoop"]},
        {"name": "fzf", "desc": "Komut satırı bulanık arama", "managers": ["brew", "scoop", "aur"]},
        {
            "name": "ripgrep",
            "desc": "Hızlı arama aracı",
            "managers": ["brew", "scoop", "winget"],
        },
        {"name": "fd", "desc": "Hızlı dosya arama", "managers": ["brew", "scoop"]},
        {"name": "bat", "desc": "catYerine geçmek", "managers": ["brew", "scoop", "winget"]},
        {"name": "exa", "desc": "lsYerine geçmek", "managers": ["brew", "scoop"]},
        {"name": "htop", "desc": "Sistem izleme", "managers": ["brew", "aur"]},
        {"name": "tldr", "desc": "çıktımanmanuel", "managers": ["brew", "scoop", "pip"]},
        {"name": "httpie", "desc": "HTTPmüşteri", "managers": ["brew", "pip", "scoop"]},
        {
            "name": "jq",
            "desc": "JSONuğraşmak",
            "managers": ["brew", "scoop", "winget", "aur"],
        },
        {"name": "yq", "desc": "YAMLuğraşmak", "managers": ["brew", "scoop"]},
        {"name": "tree", "desc": "dizin ağacı", "managers": ["brew", "scoop", "winget"]},
    ],
    "dev": [
        {"name": "node", "desc": "Node.jsçalışma zamanı", "managers": ["brew"]},
        {"name": "python", "desc": "Pythontercüman", "managers": ["brew"]},
        {"name": "go", "desc": "Goderleyici", "managers": ["brew", "scoop"]},
        {"name": "rustc", "desc": "Rustderleyici", "managers": ["brew", "scoop"]},
        {"name": "docker", "desc": "konteyner motoru", "managers": ["brew", "scoop", "winget"]},
        {"name": "kubectl", "desc": "Kubernetes CLI", "managers": ["brew", "scoop"]},
        {"name": "helm", "desc": "KubernetesPaket yöneticisi", "managers": ["brew", "scoop"]},
        {"name": "terraform", "desc": "IaCalet", "managers": ["brew", "scoop"]},
        {"name": "ansible", "desc": "Otomasyon araçları", "managers": ["pip"]},
    ],
}


@app.command()
def install(
    package: str = typer.Argument(..., help="paket adı"),
    manager: Optional[str] = typer.Option(None, "--manager", "-m", help="Paket yöneticisini belirtin"),
    sudo: bool = typer.Option(False, "--sudo", "-s", help="kullanmaksudoDüzenlemek"),
):
    """
Kurulum paketi

Örnek:
        omc pkg install git
        omc pkg install gh --manager brew
        omc pkg install node --sudo
    """
    console.print(f"\n[cyan]Kurulum paketi: {package}[/cyan]")

    #Yönetici belirtilmemişse otomatik olarak seçilir
    if not manager:
        manager = _select_best_manager(package)
        if not manager:
            console.print("[yellow]Uygun paket yöneticisi bulunamadı[/yellow]")
            console.print("[dim]Lütfen önce yükleyinHomebrewveya diğer paket yöneticileri[/dim]")
            return

    console.print(f"[dim]Yöneticiyi kullan: {manager}[/dim]\n")

    #Komut oluştur
    cmd = _build_install_command(manager, package, sudo)

    if not cmd:
        console.print(f"[red]Desteklenmeyen paket yöneticisi: {manager}[/red]")
        return

    console.print(f"[yellow]çalıştır: {' '.join(cmd)}[/yellow]\n")

    #Kurulumu gerçekleştir
    success, _stdout, stderr = _run_command(cmd, capture=False)

    if success:
        console.print(f"[green]✅Kurulum başarılı: {package}[/green]")
    else:
        console.print("[red]❌Kurulum başarısız oldu[/red]")
        if stderr:
            console.print(f"[dim]{stderr}[/dim]")


def _select_best_manager(package: str) -> Optional[str]:
    """En iyi paket yöneticisini seçin"""
    available = get_available_managers()

    #Paket adından anlaşıldı
    npm_packages = ["node", "npm", "yarn", "pnpm", "typescript", "eslint", "prettier"]
    pip_packages = ["python", "pip", "ansible", "httpie", "tldr"]

    if package.lower() in npm_packages and PackageManager.NPM in available:
        return "npm"

    if package.lower() in pip_packages and PackageManager.PIP in available:
        return "pip"

    #Varsayılan seçim
    if PackageManager.HOMEBREW in available:
        return "brew"
    if PackageManager.NPM in available:
        return "npm"
    if PackageManager.SCOOP in available:
        return "scoop"
    if PackageManager.WINGET in available:
        return "winget"
    if PackageManager.AUR in available:
        return "aur"

    return None


def _build_install_command(
    manager: str, package: str, sudo: bool
) -> Optional[list[str]]:
    """Kurulum komutunu oluştur"""
    cmd_prefix = ["sudo"] if sudo else []

    commands = {
        "brew": [*cmd_prefix, "brew", "install", package],
        "npm": ["npm", "install", "-g", package],
        "yarn": ["yarn", "global", "add", package],
        "pnpm": ["pnpm", "add", "-g", package],
        "pip": [*cmd_prefix, "pip3", "install", package],
        "scoop": ["scoop", "install", package],
        "winget": ["winget", "install", "--id", package, "--silent"],
        "aur": ["yay", "-S", package],
    }

    return commands.get(manager)


@app.command()
def search(
    query: str = typer.Argument(..., help="Anahtar kelimeleri arayın"),
    manager: Optional[str] = typer.Option(None, "--manager", "-m", help="Paket yöneticisini belirtin"),
):
    """
Paket ara

Örnek:
        omc pkg search git
        omc pkg search node --manager npm
    """
    console.print(f"\n[cyan]aramak: {query}[/cyan]\n")

    if manager:
        _search_with_manager(manager, query)
    else:
        #Mevcut tüm yöneticiler arasında arama yapın
        for mgr in get_available_managers():
            _search_with_manager(mgr.value, query)


def _search_with_manager(manager: str, query: str):
    """Belirtilen yöneticiyi kullanarak arama yapın"""
    console.print(f"\n[bold]{manager.upper()}:[/bold]")

    commands = {
        "npm": ["npm", "search", query],
        "brew": ["brew", "search", query],
        "pip": ["pip", "search", query] if platform.system() != "Windows" else None,
    }

    cmd = commands.get(manager)
    if not cmd:
        console.print(f"[dim]Müdür{manager}Arama desteklenmiyor[/dim]")
        return

    success, stdout, _stderr = _run_command(cmd)

    if success and stdout:
        lines = stdout.strip().splitlines()[:10]  #Yalnızca ilk 10'u göster
        for line in lines:
            console.print(f"  {line}")
    else:
        console.print("[dim]Sonuç bulunamadı[/dim]")


@app.command()
def list_installed(
    manager: Optional[str] = typer.Option(None, "--manager", "-m", help="Paket yöneticisini belirtin"),
):
    """
Kurulu paketleri listele

Örnek:
        omc pkg list
        omc pkg list --manager npm
    """
    console.print("\n[cyan]Kurulu paketler[/cyan]\n")

    if manager:
        _list_with_manager(manager)
    else:
        for mgr in get_available_managers():
            _list_with_manager(mgr.value)


def _list_with_manager(manager: str):
    """Belirli bir yönetici için paketleri listeleme"""
    console.print(f"\n[bold]{manager.upper()}:[/bold]")

    commands = {
        "npm": ["npm", "list", "-g", "--depth=0"],
        "brew": ["brew", "list"],
        "pip": ["pip", "list"],
        "yarn": ["yarn", "global", "list"],
    }

    cmd = commands.get(manager)
    if not cmd:
        console.print(f"[dim]Müdür{manager}Listeleme desteklenmiyor[/dim]")
        return

    success, stdout, _stderr = _run_command(cmd)

    if success and stdout:
        lines = stdout.strip().splitlines()[:20]  #Yalnızca ilk 20'yi göster
        for line in lines:
            console.print(f"  {line}")
    else:
        console.print("[dim]hiçbiri[/dim]")


@app.command()
def update(
    package: Optional[str] = typer.Argument(None, help="Paket adı (belirtilmemişse tümü güncellenir)"),
    manager: Optional[str] = typer.Option(None, "--manager", "-m", help="Paket yöneticisini belirtin"),
):
    """
Paketi güncelle

Örnek:
        omc pkg update
        omc pkg update npm
        omc pkg update git --manager brew
    """
    console.print("\n[cyan]Paketi güncelle[/cyan]\n")

    if not manager:
        manager = _select_best_manager(package or "npm")

    if not manager:
        console.print("[yellow]Kullanılabilir paket yöneticisi bulunamadı[/yellow]")
        return

    console.print(f"[dim]Müdür: {manager}[/dim]")

    commands = {
        "npm": (
            ["npm", "update", "-g"] if not package else ["npm", "update", "-g", package]
        ),
        "brew": ["brew", "upgrade"] if not package else ["brew", "upgrade", package],
        "pip": ["pip", "install", "--upgrade"] + ([package] if package else ["pip"]),
    }

    cmd = commands.get(manager)
    if not cmd:
        console.print(f"[red]Müdür{manager}Güncellemeler desteklenmiyor[/red]")
        return

    console.print(f"[yellow]çalıştır: {' '.join(cmd)}[/yellow]\n")

    success, _stdout, stderr = _run_command(cmd, capture=False)

    if success:
        console.print("[green]✅Güncelleme başarılı[/green]")
    else:
        console.print(f"[red]❌Güncelleme başarısız oldu: {stderr}[/red]")


@app.command("recommend")
def recommend():
    """Yüklenecek önerilen geliştirme araçlarını göster"""
    console.print(
        Panel.fit(
            "[bold cyan]Önerilen geliştirme araçları[/bold cyan]\n[dim]Yaygın komut satırı araçlarını hızlı bir şekilde yükleyin[/dim]",
            border_style="cyan",
        )
    )

    for category, packages in RECOMMENDED_PACKAGES.items():
        table = Table(title=f"[bold]{category.upper()}[/bold]")
        table.add_column("orijinal komut", style="cyan")
        table.add_column("betimlemek", style="white")
        table.add_column("Kurulum komutu", style="dim")

        for pkg in packages:
            install_cmd = f"omc pkg install {pkg['name']}"
            table.add_row(pkg["name"], pkg["desc"], install_cmd)

        console.print(table)
        console.print()


@app.command("check")
def check():
    """Mevcut paket yöneticilerini kontrol edin"""
    console.print("\n[cyan]Paket yöneticisi durumu[/cyan]\n")

    system = get_current_platform()
    console.print(f"platformu: [yellow]{system.value}[/yellow]\n")

    all_managers = [
        ("brew", "Homebrew", "macOS/Linux"),
        ("npm", "npm", "Tüm platformlar"),
        ("yarn", "Yarn", "Tüm platformlar"),
        ("pnpm", "pnpm", "Tüm platformlar"),
        ("pip", "pip", "Tüm platformlar"),
        ("scoop", "Scoop", "Windows"),
        ("winget", "WinGet", "Windows"),
        ("yay", "Yay (AUR)", "Linux"),
    ]

    table = Table()
    table.add_column("Emir", style="cyan")
    table.add_column("Müdür", style="white")
    table.add_column("platformu", style="dim")
    table.add_column("durum", style="green")

    available = [m.value for m in get_available_managers()]

    for cmd, name, platforms in all_managers:
        if cmd in available or (cmd == "brew" and system == Platform.MACOS):
            status = "✅Yüklendi" if cmd in available else "❌Kurulu değil"
        else:
            if platforms.lower() == system.value.lower() or platforms == "Tüm platformlar":
                status = "❌Kurulu değil"
            else:
                status = "⏭️uygulanamaz"

        table.add_row(cmd, name, platforms, status)

    console.print(table)


if __name__ == "__main__":
    app()
