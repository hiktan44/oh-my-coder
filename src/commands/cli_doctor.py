from __future__ import annotations

"""
omc doctor -Çevresel teşhis komutları

Yaygın sorunları kontrol edin ve düzeltme önerilerinde bulunun:
- PythonSürüm>= 3.9
-Paket bütünlüğüne bağımlılık
-Yapılandırma dosyası bütünlüğü (API Key)
-Ağ bağlantısı (testAPI endpoint)
"""

import importlib
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = typer.Typer(
    name="doctor",
    help="Çevresel teşhis-Yaygın sorunları kontrol edin ve düzeltme önerilerinde bulunun",
    add_completion=False,
    no_args_is_help=True,
)


# ============================================================
#Öğe tanımını kontrol edin
# ============================================================

REQUIRED_PACKAGES = [
    ("pydantic", "pydantic", ">=2.5.0"),
    ("typer", "typer", ">=0.9.0"),
    ("rich", "rich", ">=13.7.0"),
    ("httpx", "httpx", ">=0.25.0"),
    ("dotenv", "python-dotenv", ">=1.0.0"),
    ("tenacity", "tenacity", ">=8.0.0"),
]

OPTIONAL_PACKAGES = [
    ("fastapi", "fastapi", ">=0.104.0"),
    ("uvicorn", "uvicorn", ">=0.24.0"),
    ("jinja2", "jinja2", ">=3.0.0"),
    ("redis", "redis", ">=4.0.0"),
    ("websockets", "websockets", ">=10.0"),
    ("yaml", "pyyaml", ">=6.0"),
]

API_KEYS = [
    ("DEEPSEEK_API_KEY", "DeepSeek", "https://platform.deepseek.com/"),
    ("KIMI_API_KEY", "KIMI (Moonshot)", "https://platform.moonshot.cn/"),
    ("DOUBAO_API_KEY", "Doubao(Volcengine)", "https://console.volcengine.com/"),
    ("TONGYI_API_KEY", "Tongyi", "https://dashscope.console.aliyun.com/"),
    ("ZHIPUAI_API_KEY", "Bilgelik spektrumuGLM", "https://open.bigmodel.cn/"),
    ("MINIMAX_API_KEY", "MiniMax", "https://www.minimaxi.com/"),
]

API_TEST_URLS = [
    ("DeepSeek API", "https://api.deepseek.com", "DeepSeekmodel hizmeti"),
    ("KIMI API", "https://api.moonshot.cn", "KIMImodel hizmeti"),
    ("Doubao API", "https://ark.cn-beijing.volces.com", "Fasulye torbası model servisi"),
]


def _check_python_version() -> tuple[bool, str, str]:
    """incelemekPythonSürüm"""
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 9:
        return True, f"Python {major}.{minor}.{sys.version_info[2]}", ""
    return (
        False,
        f"Python {major}.{minor}.{sys.version_info[2]}",
        (
            "oh-my-coderihtiyaçPython >= 3.9\n"
            f"Güncel sürüm: {sys.version}\n"
            "Lütfen yükseltinPython: https://www.python.org/downloads/"
        ),
    )


def _check_package(
    module_name: str, package_name: str, version_req: str
) -> tuple[bool, str, str]:
    """Bireysel bağımlılıkları kontrol edin"""
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", getattr(mod, "version", "unknown"))
        return True, f"{package_name} {ver}", ""
    except ImportError:
        return (
            False,
            f"{package_name} {version_req}",
            (
                f"Eksik bağımlılıklar: {package_name} {version_req}\n"
                f"Düzenlemek: pip install '{package_name}{version_req}'"
            ),
        )


def _check_config_file() -> tuple[bool, str, str]:
    """Yapılandırma dosyasını kontrol edin"""
    paths = []
    #Kullanıcı düzeyinde yapılandırma
    user_env = Path.home() / ".omc" / ".env"
    if user_env.exists():
        paths.append(f"~/.omc/.env ({len(user_env.read_text().splitlines())}TAMAM)")

    #Proje düzeyinde yapılandırma
    project_env = Path(".env")
    if project_env.exists():
        paths.append(f".env ({len(project_env.read_text().splitlines())}TAMAM)")

    #Durum renk haritasıJSONYapılandırma
    user_config = Path.home() / ".config" / "oh-my-coder" / "config.json"
    if user_config.exists():
        paths.append("~/.omc/config.json")

    if paths:
        return True, " / ".join(paths), ""
    return (
        False,
        "Yapılandırma dosyası bulunamadı",
        (
            "Yapılandırma dosyası bulunamadı\n"
            "Proje yapılandırması oluştur: omc config set -k DEEPSEEK_API_KEY -v <your-key>\n"
            "veya manuel olarak oluşturun~/.omc/.envbelge"
        ),
    )


def _check_network(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Ağ bağlantısını test edin"""
    import requests

    try:
        resp = requests.head(url, timeout=timeout, headers={"User-Agent": "omc-doctor/1.0"})
        return resp.status_code < 500, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "zaman aşımı"
    except requests.exceptions.ConnectionError:
        return False, "Bağlantı başarısız oldu"
    except Exception as e:
        return False, type(e).__name__


@app.command()
def run(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Ayrıntılı bilgileri göster (isteğe bağlı bağımlılıklar ve sürüm karşılaştırması dahil)"
    ),
    skip_network: bool = typer.Option(
        False, "--skip-network", help="Ağ bağlantısı kontrolünü atla"
    ),
):
    """
    🏥Çalışma ortamı teşhisi

incelemekPythonSürüm, bağımlılık paketi, yapılandırma dosyası,API Keyve ağ bağlantısı,
ve onarım önerileri verin.
    """
    issues_found = 0
    checks_passed = 0

    #Sonuç tablosu oluştur
    table = Table(title="🏥 omc doctor— Çevresel teşhis raporu")
    table.add_column("durum", width=4)
    table.add_column("Öğeleri kontrol et", style="cyan", width=22)
    table.add_column("sonuç")
    table.add_column("Onarım önerileri", style="dim")

    def _add_row(ok: bool, name: str, result: str, fix: str = ""):
        nonlocal issues_found, checks_passed
        if ok:
            checks_passed += 1
            table.add_row("✅", name, f"[green]{result}[/green]", "")
        else:
            issues_found += 1
            table.add_row("❌", name, f"[red]{result}[/red]", fix)

    console.print()
    console.print(
        Panel.fit(
            "[bold]🏥 omc doctor[/bold]yeni modeller...\n"
            f"[dim]Python {sys.version_info[0]}.{sys.version_info[1]} | "
            f"{sys.platform}[/dim]",
            border_style="cyan",
        )
    )

    # ---- 1. PythonSürüm----
    ok, result, fix = _check_python_version()
    _add_row(ok, "PythonSürüm", result, fix)

    # ---- 2.çekirdek bağımlılıkları----
    for module, package, ver in REQUIRED_PACKAGES:
        ok, result, fix = _check_package(module, package, ver)
        _add_row(ok, f"güvenmek: {package}", result, fix)

    # ---- 3.İsteğe bağlı bağımlılıklar (verbosemodeli)----
    if verbose:
        for module, package, ver in OPTIONAL_PACKAGES:
            ok, result, fix = _check_package(module, package, ver)
            if ok:
                table.add_row("✅", f"İsteğe bağlı: {package}", f"[dim]{result}[/dim]", "")
            else:
                table.add_row(
                    "⚠️", f"İsteğe bağlı: {package}", f"[yellow]{result}[/yellow]", fix
                )

    # ---- 4.Yapılandırma dosyası----
    ok, result, fix = _check_config_file()
    _add_row(ok, "Yenilemeye zorla", result, fix)

    # ---- 5. API Keyincelemek----
    any_key = False
    for env_key, display_name, _url in API_KEYS:
        val = os.getenv(env_key, "")
        if val:
            if not any_key:
                any_key = True
            masked = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
            table.add_row("✅", f"Key: {display_name}", f"[green]{masked}[/green]", "")
        #yapılandırılmamışKeyGörüntülenmiyor (çok fazla gürültü), yalnızcanoneçabuk

    if not any_key:
        _add_row(
            False,
            "API Key",
            "Hiçbiriyle yapılandırılmadıAPI Key",
            "En az birini yapılandırınAPI Key:\n"
            "  omc config set -k DEEPSEEK_API_KEY -v <your-key>\n"
            "Tavsiye edilen:DeepSeekElde etmek: https://platform.deepseek.com/",
        )

    # ---- 6.ağ bağlantısı----
    if not skip_network:
        for name, url, desc in API_TEST_URLS:
            ok, status = _check_network(url)
            if ok:
                table.add_row("✅", f"ağ: {name}", f"[green]{status}[/green]", "")
            else:
                table.add_row(
                    "⚠️",
                    f"ağ: {name}",
                    f"[yellow]{status}[/yellow]",
                    f"{desc}Ulaşılamıyor, ağ veya proxy ayarlarını kontrol edin",
                )

    # ----Çıktı sonuçları----
    console.print()
    console.print(table)

    #özet
    total = checks_passed + issues_found
    if issues_found == 0:
        console.print(
            Panel.fit(
                f"[bold green]✅Hepsi geçti({checks_passed}/{total})[/bold green]\n"
                "[dim]Ortam iyi durumda, omc kullanıma hazır[/dim]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[bold yellow]⚠️Keşfetmek{issues_found}sorular"
                f"({checks_passed}/{total}geçmek)[/bold yellow]\n"
                "[dim]Lütfen yukarıdaki onarım önerilerine göre bunları tek tek çözün.[/dim]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
