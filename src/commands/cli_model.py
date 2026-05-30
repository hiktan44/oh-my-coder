from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Model CLI -Model değiştirme+ Catwalkmodeli depo+Model yapılandırma paylaşımı+Model önerisi

Emir:
- omc model list [--extended]  #Modelleri listele (normal/ayrıntılı)
- omc model current            #Mevcut modeli göster
- omc model switch <name>      #Varsayılan modeli değiştir
- omc model catwalk            #Etkileşimli tarama modeli (Catwalk)
- omc model import <url>      #itibarenURLModel yapılandırmasını içe aktar
- omc model export <name> [--yaml]  #Model yapılandırmasını dışa aktar
- omc model recommend [--task] #Öne Çıkan Model Önerileri
- omc model share              #Model yapılandırmasını toplulukla paylaşın
- omc model browse             #Topluluk tarafından paylaşılan model yapılandırmalarına göz atın
- omc model show <id>          #Model yapılandırma ayrıntılarını görüntüleyin
- omc model shared             #Yerel olarak paylaşılan konfigürasyonları listeleyin
- omc model remove <id>        #Paylaşılan yapılandırmayı sil
"""


import json
import os
import subprocess
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

#Model bulma modülünü içe aktar
try:
    from model_discovery import ModelDiscovery, get_discovery_summary
except ImportError:
    try:
        from src.model_discovery import ModelDiscovery, get_discovery_summary
    except ImportError:
        ModelDiscovery = None
        get_discovery_summary = None

console = Console()

app = typer.Typer(
    name="model",
    help="Mevcut tüm modelleri listeleyin (destekler)-Kontrol etmek/Varsayılan modeli değiştirin ve topluluk modeli deposuna göz atın (Catwalk128'i destekleyen güçlü kod oluşturma ve tamamlama yetenekleri/Önerilen model konfigürasyonu",
    add_completion=False,
)

# =============================================================================
#Yerel model yönetimi alt komutları(from cli_local_models.py)
# =============================================================================

local_app = typer.Typer(help="Yerel model yönetimi- OllamaDestek")


@local_app.command("status")
def local_check_status():
    """
incelemekOllamaHizmet durumu

Örnek:
        omc model local status
    """
    import os

    from src.models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    console.print(f"[cyan]AlgılamaOllamaSert({base_url})...[/cyan]")

    #Durum denetimi modülünü deneyin (gelişmiş sürüm)
    try:
        from ..core.ollama_health import OllamaHealthChecker

        health = OllamaHealthChecker(base_url=base_url)
        status = health.check_ollama()

        if status.running:
            console.print("[green]✓ OllamaHizmet çalışıyor[/green]")
            console.print(f"Sürüm: {status.version or 'bilinmiyor'}")
            console.print(f"Model sayısı: {status.model_count}")
            console.print(f"Gecikme: {status.latency_ms:.0f}ms")

            #Yerel modelleri listeleme (model keşfini kullanarak)
            if status.available_models:
                console.print(
                    f"\n[bold]Yerel olarak mevcut modeller({len(status.available_models)}bireysel):[/bold]"
                )
                try:
                    from ..core.local_model_discovery import discover_ollama_models

                    discovered = discover_ollama_models(base_url)
                    table = Table()
                    table.add_column("Model adı", style="cyan")
                    table.add_column("boyut")
                    table.add_column("Parametre miktarı")
                    table.add_column("Ölçün")

                    for m in discovered:
                        size_str = (
                            f"{m.size_gb:.1f} GB"
                            if m.size_gb >= 1
                            else f"{m.size_mb:.0f} MB"
                        )
                        table.add_row(
                            m.model_name,
                            size_str,
                            m.parameter_size or "-",
                            m.quantization or "-",
                        )
                    console.print(table)
                except ImportError:
                    for name in status.available_models:
                        console.print(f"  • {name}")
            else:
                console.print("[yellow]Henüz yerli model yok[/yellow]")
                console.print("\n[dim]Modeli çekmek için aşağıdaki komutu çalıştırın:[/dim]")
                console.print("[green]  omc model local pull qwen2:7b[/green]")
        else:
            console.print("[red]✗ OllamaHizmet çalışmıyor[/red]")
            console.print("\n[yellow]Lütfen önce başlayınOllama:[/yellow]")
            console.print("[green]  ollama serve[/green]")
            console.print("\nveya yükleyinOllama:https://ollama.ai/")
        return
    except ImportError:
        #Temel algılamaya geri dönme
        if OllamaModel.is_available(base_url):
            console.print("[green]✓ OllamaHizmet çalışıyor[/green]")
            models = OllamaModel.list_models(base_url)
            if models:
                console.print(f"\n[bold]Yerel olarak mevcut modeller({len(models)}bireysel):[/bold]")

                table = Table()
                table.add_column("Model adı", style="cyan")
                table.add_column("boyut")
                table.add_column("değişiklik zamanı")

                for m in models:
                    size = m.get("size", 0)
                    if size > 1e9:
                        size_str = f"{size / 1e9:.1f} GB"
                    else:
                        size_str = f"{size / 1e6:.0f} MB"

                    table.add_row(
                        m.get("name", "unknown"),
                        size_str,
                        m.get("modified_at", "")[:10] if m.get("modified_at") else "",
                    )

                console.print(table)
            else:
                console.print("[yellow]Henüz yerli model yok[/yellow]")
                console.print("\n[dim]Modeli çekmek için aşağıdaki komutu çalıştırın:[/dim]")
                console.print("[green]  omc model local pull qwen2:7b[/green]")
        else:
            console.print("[red]✗ OllamaHizmet çalışmıyor[/red]")
            console.print("\n[yellow]Lütfen önce başlayınOllama:[/yellow]")
            console.print("[green]  ollama serve[/green]")
            console.print("\nveya yükleyinOllama:https://ollama.ai/")


@local_app.command("list")
def local_list_models():
    """
Yerel olarak mevcut modelleri listeleyin

Örnek:
        omc model local list
    """
    from src.models.base import ModelTier
    from src.models.ollama import OLLAMA_MODELS, OllamaModel

    console.print("[bold]yerel model durumu:[/bold]\n")

    #Kurulu modelleri kontrol edin
    installed = OllamaModel.list_models()
    installed_names = {m["name"] for m in installed}

    #Önerilen modelleri göster
    for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
        console.print(f"\n[cyan]{tier.value.upper()} Tier:[/cyan]")

        table = Table()
        table.add_column("Modeli", style="cyan")
        table.add_column("betimlemek")
        table.add_column("durum")

        for m in OLLAMA_MODELS.get(tier, []):
            status = (
                "[green]✓Yüklendi[/green]"
                if m["name"] in installed_names
                else "[dim]Kurulu değil[/dim]"
            )
            table.add_row(m["name"], m["desc"], status)

        console.print(table)

    console.print(f"\n[dim]Yüklendi{len(installed)}yerel modeller[/dim]")


@local_app.command("pull")
def local_pull_model(
    model_name: str = typer.Argument(..., help="Model adı (ör.qwen2:7b)"),
):
    """
Modeli yerele çekin

Örnek:
        omc model local pull qwen2:7b
        omc model local pull llama3:8b
    """
    from src.models.ollama import OllamaModel

    console.print(f"[cyan]Çekme modeli: {model_name}[/cyan]")
    console.print("[dim]Bu, model boyutuna bağlı olarak birkaç dakika sürebilir...[/dim]\n")

    success = OllamaModel.pull_model(model_name)

    if success:
        console.print(f"\n[green]✓Modeli{model_name}Başarılı bir şekilde çekin[/green]")
        console.print("[dim]kullanmak[green]omc model local status[/dim]Kurulu modelleri görüntüle[/dim]")
    else:
        console.print("\n[red]✗Çekme başarısız oldu[/red]")
        console.print("\n[yellow]Lütfen şunlardan emin olun:[/yellow]")
        console.print("  1. OllamaKurulu ve çalışıyor:ollama serve")
        console.print("  2.Model adı doğrudur:https://ollama.ai/library")


@local_app.command("run")
def local_run_ollama(
    model_name: str = typer.Argument("qwen2:7b", help="Varsayılan model"),
    port: int = typer.Option(11434, "--port", "-p", help="liman"),
):
    """
başlatmakOllamaServis (çalışmıyorsa)

Örnek:
        omc model local run
        omc model local run --port 11435
    """
    import subprocess

    from src.models.ollama import OllamaModel

    if OllamaModel.is_available():
        console.print("[green]✓ OllamaZaten çalışıyor[/green]")
        return

    console.print("[cyan]başlatmakOllamaSert...[/cyan]")

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print(f"[green]✓ OllamaBaşlatıldı(liman{port})[/green]")
        console.print("[dim]Varsayılan model:[/dim] " + model_name)
    except FileNotFoundError:
        console.print("[red]✗ OllamaKurulu değil[/red]")
        console.print("\n[yellow]Lütfen önce yükleyinOllama:[/yellow]")
        console.print("[green]  https://ollama.ai/[/green]")


@local_app.command("info")
def local_model_info(
    model_name: str = typer.Argument(..., help="Model adı"),
):
    """
Model ayrıntılarını göster

Örnek:
        omc model local info qwen2:7b
    """
    from src.models.ollama import OLLAMA_MODELS

    #Model açıklamasını bulun
    desc = "Açık kaynak büyük dil modeli"
    tier = "medium"

    for t, models in OLLAMA_MODELS.items():
        for m in models:
            if m["name"] == model_name:
                desc = m["desc"]
                tier = t.value
                break

    console.print(
        Panel.fit(
            f"[bold cyan]{model_name}[/bold cyan]\n\n"
            f"[dim]betimlemek:[/dim] {desc}\n"
            f"[dim]Hiyerarşi:[/dim] {tier}\n\n"
            f"[dim]Nasıl kullanılır:[/dim]\n"
            f"  1.Çekme modeli: [green]omc model local pull {model_name}[/green]\n"
            f"  2.Varsayılan olarak ayarla: [green]export OLLAMA_MODEL={model_name}[/green]",
            title="Model bilgisi",
            border_style="cyan",
        )
    )


@local_app.command("chat")
def local_chat_model(
    model_name: str = typer.Argument("qwen2:7b", help="Model adı"),
    system: str = typer.Option(None, "--system", "-s", help="Sistem istemi sözcüğü"),
    temperature: float = typer.Option(0.7, "--temp", "-t", help="Sıcaklık parametreleri"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Akış çıkışını devre dışı bırak"),
):
    """
Projelerdeki gereksiz kodları tarayın ve temizleyin

Örnek:
        omc model local chat
        omc model local chat llama3:8b
        omc model local chat qwen2:7b --system "Sen kimsinPythonuzman"
    """
    import asyncio
    import os

    from src.models.base import Message
    from src.models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    #Hizmet durumunu kontrol edin
    console.print(f"[cyan]bağlamakOllamaSert({base_url})...[/cyan]")
    if not OllamaModel.is_available(base_url):
        console.print("[red]✗ OllamaHizmet çalışmıyor[/red]")
        console.print("\n[yellow]Lütfen önce başlayınOllama:[/yellow]")
        console.print("[green]  ollama serve[/green]")
        raise typer.Exit(1)

    #Modelin mevcut olup olmadığını kontrol edin
    models = OllamaModel.list_models(base_url)
    model_names = {m.get("name", "").split(":")[0] for m in models}
    full_names = {m.get("name", "") for m in models}

    #Tam eşleşmeyi ve önek eşleşmesini deneyin
    target_model = None
    if model_name in full_names:
        target_model = model_name
    elif model_name.split(":")[0] in model_names:
        #Kullanıcı kısa bir ad girdi (ör.qwen2), tam adı bulun
        for m in models:
            name = m.get("name", "")
            if name.startswith(model_name.split(":")[0]):
                target_model = name
                break

    if not target_model:
        console.print(f"[red]✗Modeli{model_name}Kurulu değil[/red]")
        console.print("\n[yellow]Mevcut modeller:[/yellow]")
        for m in models[:10]:
            console.print(f"  • {m.get('name', 'unknown')}")
        console.print(f"\n[dim]Çekme modeli: omc model local pull {model_name}[/dim]")
        raise typer.Exit(1)

    console.print(f"[green]✓Bağlı model: {target_model}[/green]")
    console.print("[dim]girmek/exitveya/quitçıkış yapmak,/clearGeçmişi temizle[/dim]\n")

    #Modeli başlat
    from src.models.base import ModelConfig

    config = ModelConfig(api_key="", base_url=base_url)
    model = OllamaModel(config, model_name=target_model)

    #Sohbet geçmişi
    messages: list[Message] = []
    if system:
        messages.append(Message(role="system", content=system))

    #etkileşimli döngü
    console.print("[bold cyan]💬Sohbete başla[/bold cyan]\n")
    while True:
        try:
            #Kullanıcı girişini oku
            user_input = console.input("[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            #komut işleme
            if user_input in ("/exit", "/quit", "/q"):
                console.print("\n[dim]Sohbetten çık[/dim]")
                break
            elif user_input == "/clear":
                messages = [m for m in messages if m.role == "system"]
                console.print("[dim]Konuşma geçmişi temizlendi[/dim]\n")
                continue
            elif user_input == "/help":
                console.print(
                    "\n[dim]Komut listesi:[/dim]\n"
                    "  /exit, /quit  -Sohbetten çık\n"
                    "  /clear        -Geçmişi temizle\n"
                    "  /help         -yardım göster\n"
                )
                continue

            #Kullanıcı mesajı ekle
            messages.append(Message(role="user", content=user_input))

            #çağrı modeli
            console.print("[bold blue]Assistant:[/bold blue] ", end="")

            if no_stream:
                #akış dışı
                response = asyncio.run(
                    model.complete(messages, temperature=temperature)
                )
                console.print(response.content)
                messages.append(Message(role="assistant", content=response.content))
            else:
                #akış
                async def stream_chat():
                    full_response = ""
                    async for chunk in model.stream(messages, temperature=temperature):
                        full_response += chunk
                        console.print(chunk, end="")
                    console.print()  #yeni satır
                    return full_response

                response_text = asyncio.run(stream_chat())
                messages.append(Message(role="assistant", content=response_text))

            console.print()  #boş satır

        except KeyboardInterrupt:
            console.print("\n[dim]kesinti, giriş/exitçıkış yapmak[/dim]\n")
            continue
        except Exception as e:
            console.print(f"\n[red]hata: {e}[/red]\n")
            #Başarısız kullanıcı mesajlarını kaldırın
            if messages and messages[-1].role == "user":
                messages.pop()


#kayıt olmaklocalana alt komutapp
app.add_typer(local_app, name="local")

#Yapılandırma dosyası yolu
CONFIG_DIR = Path.home() / ".omc"
CONFIG_FILE = CONFIG_DIR / "config.json"

# CatwalkModel ambar dizini (proje yerleşik+kullanıcı uzantısı)
CATWALK_DIR = Path(__file__).parent.parent / "models"
USER_MODELS_DIR = Path.home() / ".omc" / "models"

#Yapılandırma depolama yolunu paylaşın
SHARED_MODELS_DIR = Path.home() / ".oh-my-coder" / "shared_models"

#Yerleşik model bilgisi (Tier 1 -özgür/düşük maliyetli)
SUPPORTED_MODELS = {
    #düşük maliyetli/ücretsiz model
    "deepseek": {"name": "DeepSeek", "tier": "low", "note": "Yüksek maliyet performansı, önerilir"},
    "glm": {"name": "Bilgelik spektrumuGLM", "tier": "low", "note": "GLM-4.7-Flashkullanımı ücretsiz"},
    #Ana akım model
    "wenxin": {"name": "Wenxinyiyan", "tier": "medium", "note": "Baidu"},
    "tongyi": {"name": "Tongyi", "tier": "medium", "note": "Ali"},
    "minimax": {"name": "MiniMax", "tier": "medium", "note": ""},
    "kimi": {"name": "Kimi", "tier": "medium", "note": "ayın karanlık yüzü"},
    "hunyuan": {"name": "Tencent Hunyuan", "tier": "medium", "note": "Tencent"},
    "doubao": {"name": "Doubao (ByteDance)", "tier": "medium", "note": "ByteDance"},
    #Diğer modeller
    "tiangong": {"name": "TiangongAI", "tier": "medium", "note": ""},
    "spark": {"name": "Yalnızca onarım önerilerinin gösterilip gösterilmeyeceği", "tier": "medium", "note": ""},
    "baichuan": {"name": "Baichuan İstihbaratı", "tier": "medium", "note": ""},
    "mimo": {"name": "DarıMiMo", "tier": "medium", "note": "Darı"},
}


# =============================================================================
#Fayda fonksiyonu
# =============================================================================


def _ensure_config_dir() -> None:
    """Yapılandırma dizininin mevcut olduğundan emin olun"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """Yapılandırma dosyasını yükle"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict) -> None:
    """Yapılandırma dosyasını kaydet"""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _get_current_model() -> str:
    """Geçerli varsayılan modeli alın"""
    env_model = os.getenv("OMC_DEFAULT_MODEL")
    if env_model:
        return env_model
    config = _load_config()
    return config.get("default_model", "deepseek")


def _get_current_api_key(model_id: str) -> Optional[str]:
    """Mevcut modeli alınAPI Key(ortam değişkenlerinden çıkarılmıştır)"""
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "glm": "ZHIPUAI_API_KEY",
        "wenxin": "ERNIE_API_KEY",
        "tongyi": "DASHSCOPE_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "kimi": "KIMI_API_KEY",
        "hunyuan": "HUNYUAN_API_KEY",
        "doubao": "DOUBAO_API_KEY",
        "tiangong": "TIANGONG_API_KEY",
        "spark": "SPARK_API_KEY",
        "baichuan": "BAICHUAN_API_KEY",
        "mimo": "MIMO_API_KEY",
    }
    env_var = key_map.get(model_id)
    if env_var:
        return os.getenv(env_var)
    return None


def _tier_style(tier: str) -> str:
    """buna göretierDönüş rengi"""
    return {"free": "green", "low": "cyan", "medium": "yellow", "high": "red"}.get(
        tier, "white"
    )


# =============================================================================
#Yapılandırma aracı işlevini paylaşma (from cli_models.py)
# =============================================================================


def _ensure_shared_dir() -> None:
    """Paylaşılan dizinin mevcut olduğundan emin olun"""
    SHARED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _list_shared_configs() -> list[dict]:
    """Tüm paylaşılan konfigürasyonları listele"""
    configs = []
    if not SHARED_MODELS_DIR.exists():
        return configs

    for json_file in sorted(SHARED_MODELS_DIR.glob("*.json")):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = json_file.name
                configs.append(data)
        except Exception:
            continue

    return configs


def _get_author_name() -> str:
    """Yazar adını alın (ilk olarak ortam değişkenleri, ikincigit config)"""
    # 1.ortam değişkenleri
    author = os.getenv("OMC_AUTHOR_NAME")
    if author:
        return author

    # 2. git config
    try:
        result = subprocess.run(
            ["git", "config", "--get", "user.name"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # 3.varsayılan
    return "Anonymous"


# =============================================================================
#Model öneri verileri ve işlevleri (from cli_models_recommend.py)
# =============================================================================

RECOMMENDATIONS: dict[str, list[dict]] = {
    "coding": [
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "YüklendiKbağlam",
            "free_quota": "5 milyontokens/ay",
        },
        {
            "model": "qwen2.5-coder-32b-instruct",
            "provider": "Tongyi",
            "reason": "Çoklu dil programlamada mükemmel performansla kodlama senaryoları için özel olarak optimize edilmiştir",
            "free_quota": "5 milyontokens/ay",
        },
        {
            "model": "glm-4-flash",
            "provider": "Bilgelik spektrumuAI",
            "reason": "Hızlı kod anlama ve oluşturma, sıfır başlangıç ​​maliyeti",
            "free_quota": "Ücretsiz sınırsız",
        },
    ],
    "reasoning": [
        {
            "model": "qwen3-235b-a22b",
            "provider": "Tongyi",
            "reason": "MoEMükemmel mimari akıl yürütme, eksiksiz ve şeffaf düşünme zinciri",
            "free_quota": "5 milyontokens/ay",
        },
        {
            "model": "glm-4-plus",
            "provider": "Bilgelik spektrumuAI",
            "reason": "Karmaşık akıl yürütme ve bilgi soru ve cevaplarında mükemmel performans",
            "free_quota": "Hediye kotası",
        },
    ],
    "creative": [
        {
            "model": "qwen-max",
            "provider": "Tongyi",
            "reason": "Yaratıcı yazma ve çok stilde metin oluşturmada üstün yetenek",
            "free_quota": "5 milyontokens/ay",
        },
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "Uzun metin oluşturma işlemi sorunsuzdur ve Çince ifadeler doğaldır",
            "free_quota": "5 milyontokens/ay",
        },
        {
            "model": "glm-4-flash",
            "provider": "Bilgelik spektrumuAI",
            "reason": "Hızla yaratıcı içerik oluşturun ve sıfır maliyetle yineleyin",
            "free_quota": "Ücretsiz sınırsız",
        },
    ],
    "fast": [
        {
            "model": "glm-4-flash",
            "provider": "Bilgelik spektrumuAI",
            "reason": "Yüksek frekanslı arama senaryolarına uygun son derece hızlı yanıt hızı",
            "free_quota": "Ücretsiz sınırsız",
        },
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "KAFAtokenDüşük gecikme süresi, yüksek verim",
            "free_quota": "5 milyontokens/ay",
        },
        {
            "model": "qwen2.5-7b-instruct",
            "provider": "Tongyi",
            "reason": "Basit görevlere uygun, küçük modellerle son derece hızlı akıl yürütme",
            "free_quota": "5 milyontokens/ay",
        },
    ],
    "chat": [
        {
            "model": "glm-4-flash",
            "provider": "Bilgelik spektrumuAI",
            "reason": "Günlük konuşmalar sorunsuz ve doğaldır, tamamen ücretsizdir",
            "free_quota": "Ücretsiz sınırsız",
        },
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "İyi konuşma tutarlılığı ve geniş bilgi",
            "free_quota": "5 milyontokens/ay",
        },
        {
            "model": "qwen-turbo",
            "provider": "Tongyi",
            "reason": "Hafif diyalog modeli, hızlı yanıt ve düşük maliyet",
            "free_quota": "5 milyontokens/ay",
        },
    ],
}

TASK_ALIASES: dict[str, str] = {
    "code": "coding",
    "kod yaz": "coding",
    "programlama": "coding",
    "muhakeme": "reasoning",
    "mantık": "reasoning",
    "yaratıcılık": "creative",
    "Yenilemeye zorla": "creative",
    "hızlı": "fast",
    "hız": "fast",
    "sohbet": "chat",
    "modeli):": "chat",
}

VALID_TASKS = list(RECOMMENDATIONS.keys())


def _resolve_task(task: str) -> str:
    """Ayrıştırma görev türü (takma adları destekler)"""
    task_lower = task.lower().strip()
    if task_lower in VALID_TASKS:
        return task_lower
    if task_lower in TASK_ALIASES:
        return TASK_ALIASES[task_lower]
    return task_lower


def _show_all_recommendations() -> None:
    """Tüm öneri formlarını göster"""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🏆Öne Çıkan Model Önerileri[/bold cyan]— Senaryolara göre seçilen ücretsiz modeller",
            border_style="cyan",
        )
    )
    console.print()

    for task_type, models in RECOMMENDATIONS.items():
        table = Table(
            title=f"📦 {task_type.upper()}",
            show_lines=False,
            title_style="bold yellow",
            expand=True,
        )
        table.add_column("Modeli", style="cyan", no_wrap=True)
        table.add_column("sağlayıcı", style="blue")
        table.add_column("Tavsiye nedenleri", style="white", no_wrap=False)
        table.add_column("Ücretsiz kota", style="green")

        for m in models:
            table.add_row(m["model"], m["provider"], m["reason"], m["free_quota"])

        console.print(table)
        console.print()

    console.print(
        "[dim]💡kullanmak[cyan]omc model recommend --task <type>[/cyan]Türe özel önerilere bakın[/dim]"
    )
    console.print(f"[dim]Mevcut türler: {', '.join(VALID_TASKS)}[/dim]")
    console.print()


def _show_task_recommendation(task: str) -> None:
    """Belirli görev türleri için önerileri göster"""
    resolved = _resolve_task(task)

    if resolved not in RECOMMENDATIONS:
        console.print(f"[red]✗Bilinmeyen görev türü: {task}[/red]")
        console.print(f"[dim]Mevcut türler: {', '.join(VALID_TASKS)}[/dim]")
        raise typer.Exit(1)

    models = RECOMMENDATIONS[resolved]
    label = resolved.upper()

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]🏆 {label}Senaryo önerisi[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    table = Table(show_lines=False, expand=True)
    table.add_column("Modeli", style="cyan", no_wrap=True)
    table.add_column("sağlayıcı", style="blue")
    table.add_column("Tavsiye nedenleri", style="white", no_wrap=False)
    table.add_column("Ücretsiz kota", style="green")

    for m in models:
        table.add_row(m["model"], m["provider"], m["reason"], m["free_quota"])

    console.print(table)
    console.print()


# =============================================================================
# YAMLModel konfigürasyon yönetimi
# =============================================================================


def _list_yaml_configs() -> list[dict[str, Any]]:
    """Tümünü taraYAMLModel yapılandırma dosyası"""
    configs: list[dict[str, Any]] = []

    for models_dir in [CATWALK_DIR, USER_MODELS_DIR]:
        if not models_dir.exists():
            continue
        for yaml_file in sorted(models_dir.glob("*.yaml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    data["_source"] = (
                        "user" if models_dir == USER_MODELS_DIR else "builtin"
                    )
                    data["_file"] = yaml_file.name
                    configs.append(data)
            except Exception:
                continue

    return configs


def _validate_model_config(data: dict) -> tuple[bool, str]:
    """Model yapılandırmasının yasal olup olmadığını doğrulayın"""
    required = ["name", "provider", "model"]
    for field in required:
        if field not in data:
            return False, f"Gerekli alanlar eksik: {field}"

    valid_tiers = ["free", "low", "medium", "high"]
    tier = data.get("tier", "medium")
    if tier not in valid_tiers:
        return False, f"tierolmalıdır{valid_tiers}bir, şu anda: {tier}"

    valid_providers = [
        "deepseek",
        "glm",
        "wenxin",
        "tongyi",
        "minimax",
        "kimi",
        "hunyuan",
        "doubao",
        "baichuan",
        "tiangong",
        "spark",
        "mimo",
        "openai",
        "anthropic",
        "google",
    ]
    provider = data.get("provider", "")
    if provider not in valid_providers:
        return False, f"provider '{provider}'Destek listesinde yok"

    return True, "OK"


def _save_model_config(data: dict) -> Path:
    """Model konfigürasyonunu kullanıcı dizinine kaydedin ve kaydetme yolunu döndürün"""
    USER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    #dosya adı:provider-model.yaml
    filename = f"{data['provider']}-{data['model'].replace('/', '-')}.yaml"
    filepath = USER_MODELS_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    return filepath


# =============================================================================
#yerleşikCatwalkModel yapılandırma verileri (10+bireysel)
# =============================================================================

#Dış kaynaklara bağımlı olmaktan kaçınmak için model verilerini ekleyinmodels/İçindekiler
BUILTIN_CATWALK_MODELS: list[dict[str, Any]] = [
    {
        "name": "DeepSeek V4",
        "provider": "deepseek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "tier": "low",
        "pricing": {"input": 2, "output": 8},
        "context": 64000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "GLM-4.7-Flash",
        "provider": "glm",
        "api_key_env": "ZHIPUAI_API_KEY",
        "endpoint": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "tier": "free",
        "pricing": {"input": 0, "output": 0},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "MiMo Flash",
        "provider": "mimo",
        "api_key_env": "MIMO_API_KEY",
        "endpoint": "https://api.minimax.chat/v1",
        "model": "MiniMax-Text-01",
        "tier": "free",
        "pricing": {"input": 0, "output": 0},
        "context": 1000000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "Wenxinyiyan 4.0",
        "provider": "wenxin",
        "api_key_env": "ERNIE_API_KEY",
        "endpoint": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1",
        "model": "ernie-4.0-8k-latest",
        "tier": "medium",
        "pricing": {"input": 120, "output": 120},
        "context": 8000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "Tongyi 2.5",
        "provider": "tongyi",
        "api_key_env": "DASHSCOPE_API_KEY",
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "tier": "medium",
        "pricing": {"input": 60, "output": 180},
        "context": 131072,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "Kimi 128K",
        "provider": "kimi",
        "api_key_env": "KIMI_API_KEY",
        "endpoint": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-128k",
        "tier": "medium",
        "pricing": {"input": 60, "output": 240},
        "context": 128000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "Doubao-Pro",
        "provider": "doubao",
        "api_key_env": "DOUBAO_API_KEY",
        "endpoint": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-pro-32k",
        "tier": "medium",
        "pricing": {"input": 30, "output": 30},
        "context": 32000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "yolu ayrıştırTurbo",
        "provider": "hunyuan",
        "api_key_env": "HUNYUAN_APP_ID",
        "endpoint": "https://hunyuan.cloud.tencent.com",
        "model": "hunyuan-turbo",
        "tier": "medium",
        "pricing": {"input": 100, "output": 100},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "MiniMax text-01",
        "provider": "minimax",
        "api_key_env": "MINIMAX_API_KEY",
        "endpoint": "https://api.minimax.chat/v1",
        "model": "MiniMax-Text-01",
        "tier": "low",
        "pricing": {"input": 10, "output": 10},
        "context": 1000000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "Tiangong 3.0",
        "provider": "tiangong",
        "api_key_env": "TIANGONG_API_KEY",
        "endpoint": "https://api.tiangong.cn/v1",
        "model": "tiangong-3",
        "tier": "medium",
        "pricing": {"input": 50, "output": 50},
        "context": 128000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "iFlytek Kıvılcım 4.0",
        "provider": "spark",
        "api_key_env": "SPARK_API_KEY",
        "endpoint": "https://spark-api.xf-yun.com/v4.0/chat",
        "model": "generalv4.0",
        "tier": "medium",
        "pricing": {"input": 80, "output": 80},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "Baiçuan 4",
        "provider": "baichuan",
        "api_key_env": "BAICHUAN_API_KEY",
        "endpoint": "https://api.baichuan-ai.com/v1",
        "model": "Baichuan4",
        "tier": "medium",
        "pricing": {"input": 120, "output": 120},
        "context": 128000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "GPT-4o-mini",
        "provider": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "tier": "high",
        "pricing": {"input": 21, "output": 84},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "endpoint": "https://api.anthropic.com/v1",
        "model": "claude-3-5-haiku-20241022",
        "tier": "high",
        "pricing": {"input": 11, "output": 55},
        "context": 200000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "Gemini 2.0 Flash",
        "provider": "google",
        "api_key_env": "GOOGLE_API_KEY",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-2.0-flash",
        "tier": "low",
        "pricing": {"input": 0, "output": 0},
        "context": 1000000,
        "features": ["function_call", "vision", "streaming"],
    },
]


# =============================================================================
#Komut uygulaması-orijinal komut
# =============================================================================


@app.command("list")
def list_models(
    extended: bool = typer.Option(
        False, "--extended", "-e", help="Tamamlandı gösterYAMLYapılandırma ayrıntıları (Catwalkmodeli)"
    ),
    tier: str = typer.Option(None, "--tier", help="Seviyeye göre filtrele: free/low/medium/high"),
    provider: str = typer.Option(None, "--provider", "-p", help="Tedarikçiye göre filtrele"),
    status: str = typer.Option(
        None,
        "--status",
        help="Hazır durumuna göre filtrele: production/beta/deprecated/all (varsayılanproduction)",
    ),
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Tüm modelleri göster (dahil)beta/deprecated, eşdeğer--status all)",
    ),
    beta: bool = typer.Option(False, "--beta", "-b", help="göstermekbetaModeli"),
    json_output: bool = typer.Option(False, "--json", help="JSONçıktı"),
    source: str = typer.Option(
        None, "--source", "-s", help="veri kaynağı: builtin(yerleşik)/user(kullanıcı)/all"
    ),
) -> None:
    """Mevcut tüm modelleri listeleyin (destekler)CatwalkAyrıntılı görünüm)"""
    from src.models import (
        enrich_with_status,
        filter_by_status,
        get_model_status,
    )

    # Resolve effective status filter
    if all or status == "all":
        _show_prod, _show_beta, _show_dep = True, True, True
    elif beta or status == "beta":
        _show_prod, _show_beta, _show_dep = False, True, False
    elif status == "deprecated":
        _show_prod, _show_beta, _show_dep = False, False, True
    elif status in ("production", None):
        _show_prod, _show_beta, _show_dep = True, False, False
    else:
        _show_prod, _show_beta, _show_dep = True, False, False

    if extended or json_output:
        # Catwalkayrıntılı mod
        all_configs: list[dict[str, Any]] = []

        #Gömülü veriler
        for cfg in BUILTIN_CATWALK_MODELS:
            cfg_copy = dict(cfg)
            cfg_copy["_source"] = "builtin"
            all_configs.append(cfg_copy)

        # YAMLDosya (kullanıcı tanımlı)
        for cfg in _list_yaml_configs():
            all_configs.append(cfg)

        # Enrich with status metadata
        all_configs = enrich_with_status(all_configs)

        # Filter
        if tier:
            all_configs = [c for c in all_configs if c.get("tier") == tier]
        if provider:
            all_configs = [c for c in all_configs if c.get("provider") == provider]
        if source:
            all_configs = [c for c in all_configs if c.get("_source") == source]

        # Apply status filter (not combined with source/tier/provider)
        if status or all or beta:
            all_configs = filter_by_status(
                all_configs,
                show_production=_show_prod,
                show_beta=_show_beta,
                show_deprecated=_show_dep,
            )
        else:
            # Default: production only
            all_configs = filter_by_status(
                all_configs,
                show_production=True,
                show_beta=False,
                show_deprecated=False,
            )

        if json_output:
            # JSONçıktı (içinAITüketim)
            import json

            out = []
            for cfg in all_configs:
                out.append(
                    {
                        "name": cfg.get("name"),
                        "provider": cfg.get("provider"),
                        "model": cfg.get("model"),
                        "endpoint": cfg.get("endpoint"),
                        "tier": cfg.get("tier"),
                        "pricing": cfg.get("pricing", {}),
                        "context": cfg.get("context"),
                        "features": cfg.get("features", []),
                        "source": cfg.get("_source"),
                        "model_status": cfg.get("model_status", "beta"),
                    }
                )
            console.print_json(json.dumps(out, ensure_ascii=False, indent=2))
            return

        #Detaylı form
        table = Table(
            title=f"CatwalkGörev yürütmeyle ilgili komutlar{len(all_configs)}modeli)",
            show_lines=True,
        )
        table.add_column("Modeli", style="cyan", no_wrap=False)
        table.add_column("tedarikçi", style="blue")
        table.add_column("Tier", style="yellow", no_wrap=True)
        table.add_column("hazır", style="magenta", no_wrap=True)
        table.add_column("Fiyat (yuan/milyontoken)", style="dim")
        table.add_column("bağlam", style="green")
        table.add_column("kaynak", style="white")

        current = _get_current_model()

        for cfg in all_configs:
            pricing = cfg.get("pricing", {})
            in_p = pricing.get("input", "-")
            out_p = pricing.get("output", "-")
            price_str = f"{in_p}/{out_p}" if in_p != "-" else "-"

            ", ".join(cfg.get("features", [])[:3])
            tier_label = cfg.get("tier", "medium")
            source_label = cfg.get("_source", "builtin")

            # Status badge
            raw_status = cfg.get("model_status", "beta")
            status_badge = {
                "production": "✅Üretme",
                "beta": "🔶Beta",
                "deprecated": "⛔terk edilmiş",
            }.get(raw_status, raw_status)

            #Mevcut modeli vurgula
            provider_id = cfg.get("provider", "")
            is_current = "★" if provider_id == current else ""

            table.add_row(
                f"{cfg.get('name', '')} {is_current}",
                cfg.get("provider", ""),
                tier_label,
                status_badge,
                price_str,
                str(cfg.get("context", "-")),
                source_label,
            )

        console.print(table)
        console.print()
        console.print(
            f"[dim]yerleşik: {len([c for c in all_configs if c.get('_source') == 'builtin'])}bireysel| "
            f"kullanıcı: {len([c for c in all_configs if c.get('_source') == 'user'])}bireysel[/dim]"
        )
        console.print(f"[dim]Yerleşik model dizini: {CATWALK_DIR}(salt okunur)[/dim]")
        console.print(f"[dim]Kullanıcı modeli dizini: {USER_MODELS_DIR}[/dim]")
        console.print("[dim]ipucu:kullanmak[cyan]omc model catwalk[/cyan]etkileşimli tarama[/dim]")
    else:
        #Basit mod
        table = Table(title="Desteklenen model listesi")
        table.add_column("ModeliID", style="cyan")
        table.add_column("isim", style="green")
        table.add_column("Hiyerarşi", style="yellow")
        table.add_column("hazır", style="magenta")
        table.add_column("Komut yürütme başarısız oldu", style="white")

        current = _get_current_model()

        for model_id, info in SUPPORTED_MODELS.items():
            is_current = "★" if model_id == current else ""
            status_raw = get_model_status(model_id)
            status_map = {
                "production": "✅Üretme",
                "beta": "🔶Beta",
                "deprecated": "⛔terk edilmiş",
            }
            status_str = status_map.get(status_raw, status_raw)
            # Filtering logic:
            # --all: show all; --beta: show only beta; default: production only
            if beta:
                if status_raw != "beta" and status_raw != "deprecated":
                    continue
            elif not all and status_raw != "production":
                continue
            table.add_row(
                model_id,
                info["name"],
                info["tier"],
                status_str,
                is_current,
            )

        console.print(table)
        console.print()
        console.print(f"[dim]Yenilemeye zorla: {CONFIG_FILE}[/dim]")
        console.print(f"[dim]mevcut model: {current}[/dim]")
        console.print("[dim]kullanmak[cyan]--extended[/cyan]Kontrol etmekCatwalkayrıntılı mod[/dim]")

        #Yeni modelleri kontrol edin (engellenmeyen, önbellek kullanan veya hızlı bulma)
        if get_discovery_summary and not json_output:
            try:
                summary = get_discovery_summary(BUILTIN_CATWALK_MODELS)
                if summary.get("has_new"):
                    new_models = summary.get("new_models", [])
                    if new_models:
                        #Yalnızca ilk 3 yeni modeli göster
                        display_models = new_models[:3]
                        model_names = ", ".join(
                            [
                                f"{m['model_id']} ({m['provider']})"
                                for m in display_models
                            ]
                        )
                        if len(new_models) > 3:
                            model_names += f"Beklemek{len(new_models)}bireysel"
                        console.print()
                        console.print(
                            f"[bold yellow]💡Yeni modelleri keşfedin:[/] [cyan]{model_names}[/]"
                        )
                        console.print(
                            "[dim]koşmak[cyan]omc model sync[/cyan]Ayrıntıları görüntüleyin ve senkronize edin[/dim]"
                        )
            except Exception:
                #Sessizce başarısız olur ve ana işlevi etkilemez
                pass


@app.command("catwalk")
def catwalk(
    tier: str = typer.Option(
        None, "--tier", "-t", help="Seviyeye göre filtrele: free/low/medium/high"
    ),
    provider: str = typer.Option(None, "--provider", "-p", help="Tedarikçiye göre filtrele"),
    search: str = typer.Option(None, "--search", "-s", help="Model adını ara/karakteristik"),
) -> None:
    """etkileşimli taramaCatwalkModel deposu (etkileşimli mod)"""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🐱 Catwalkmodeli depo[/bold cyan]— Topluluk odaklı model yapılandırma paylaşımı",
            border_style="cyan",
        )
    )
    console.print()

    #Özet
    models = list(BUILTIN_CATWALK_MODELS)

    if tier:
        models = [m for m in models if m.get("tier") == tier]
    if provider:
        models = [m for m in models if m.get("provider") == provider]
    if search:
        q = search.lower()
        models = [
            m
            for m in models
            if q in m.get("name", "").lower()
            or q in m.get("provider", "").lower()
            or any(q in f.lower() for f in m.get("features", []))
        ]

    if not models:
        console.print("[red]Eşleşen model bulunamadı[/red]")
        return

    #listeyi göster
    table = Table(
        title=f"yaygın{len(models)}modeller (giriş numarası seçimi)",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Model adı", style="cyan")
    table.add_column("tedarikçi", style="blue")
    table.add_column("Tier", style="yellow")
    table.add_column("Fiyatı girin", style="magenta")
    table.add_column("bağlam", style="green")
    table.add_column("karakteristik", style="dim")

    for i, cfg in enumerate(models, 1):
        pricing = cfg.get("pricing", {})
        price_str = f"{pricing.get('input', '-')}Yuan/MTok"
        features = ", ".join(cfg.get("features", [])[:2])

        table.add_row(
            str(i),
            cfg.get("name", ""),
            cfg.get("provider", ""),
            cfg.get("tier", "medium"),
            price_str,
            str(cfg.get("context", "-")),
            features,
        )

    console.print(table)
    console.print()

    #etkileşimli seçim
    choices = [str(i) for i in range(1, len(models) + 1)]
    choice = Prompt.ask(
        "[bold]Modeli seçmek için numarayı girin[/bold](Çıkmak için Enter tuşuna basın,l=liste,s=kaydetmek)",
        default="",
    )

    if not choice.strip():
        return

    if choice.strip().lower() == "l":
        list_models(extended=True)
        return

    if choice.strip().lower() == "s":
        #Filtrelenen tüm modelleri gruplar halinde kaydedin
        USER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        for cfg in models:
            _save_model_config(cfg)
        console.print(
            f"[green]✓kaydedildi{len(models)}için yapılandırılmış modeller{USER_MODELS_DIR}[/green]"
        )
        return

    if choice in choices:
        idx = int(choice) - 1
        cfg = models[idx]

        #Ayrıntıları göster
        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]{cfg['name']}[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print()
        console.print(f"  [dim]tedarikçi:[/] {cfg.get('provider')}")
        console.print(f"  [dim]Tier:[/]   {cfg.get('tier')}")
        console.print(f"  [dim]ModeliID:[/] {cfg.get('model')}")
        console.print(f"  [dim]uç nokta:[/]   {cfg.get('endpoint')}")
        console.print(f"  [dim]bağlam:[/] {cfg.get('context')} tokens")
        pricing = cfg.get("pricing", {})
        console.print(
            f"  [dim]fiyat:[/]girmek{pricing.get('input', '-')} /çıktı{pricing.get('output', '-')}Yuan/milyontoken"
        )
        console.print(f"  [dim]karakteristik:[/]   {', '.join(cfg.get('features', []))}")
        console.print()

        #Yapılandırma içe aktarıldı
        do_save = Confirm.ask(
            f"[bold]kaydetmek'{cfg['name']}'Kullanıcı modeli kitaplığına mı?[/bold]", default=True
        )
        if do_save:
            path = _save_model_config(cfg)
            console.print(f"[green]✓şuraya kaydedildi:{path}[/green]")

        do_switch = Confirm.ask(f"[bold]geçiş yapmak'{cfg['name']}'?[/bold]", default=False)
        if do_switch:
            provider_id = cfg.get("provider", "")
            #İlgili kısayı bulunID
            for mid, minfo in SUPPORTED_MODELS.items():
                if minfo["name"] in cfg["name"] or mid == provider_id:
                    #Doğrudan satır içi anahtarlama mantığı (döngüsel içe aktarmalardan kaçınma)
                    config = _load_config()
                    config["default_model"] = mid
                    _save_config(config)
                    console.print(f"[green]✓Varsayılan modele geçildi{mid}[/green]")
                    break
    else:
        console.print(f"[red]Geçersiz seçim: {choice}[/red]")


@app.command("import")
def import_model(
    url: str = typer.Argument(..., help="model yapılandırılmışYAML URLveya yerel dosya yolu"),
    name: str = typer.Option(
        None, "--name", "-n", help="Kaydederken ad (varsayılan:URLçıkarım)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Aynı adı taşıyan mevcut konfigürasyonun üzerine yaz"),
) -> None:
    """itibarenURLVeya yerel dosyadan içe aktarınYAMLModel konfigürasyonu"""
    console.print(f"[dim]Yapılandırma alınıyor: {url}[/dim]")

    #Elde etmekYAMLiçerik
    if url.startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "oh-my-coder/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                content = resp.read().decode("utf-8")
        except Exception as e:
            console.print(f"[red]✗Alınamadı: {e}[/red]")
            raise typer.Exit(1)
    else:
        #yerel dosya
        filepath = Path(url)
        if not filepath.exists():
            console.print(f"[red]✗Dosya mevcut değil: {url}[/red]")
            raise typer.Exit(1)
        content = filepath.read_text(encoding="utf-8")

    #ayrıştırmakYAML
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        console.print(f"[red]✗ YAMLAyrıştırma başarısız oldu: {e}[/red]")
        raise typer.Exit(1)

    if not isinstance(data, dict):
        console.print("[red]✗ YAMLİçerik sözlük formatında bir model konfigürasyonu değil[/red]")
        raise typer.Exit(1)

    #doğrulamak
    valid, msg = _validate_model_config(data)
    if not valid:
        console.print(f"[red]✗Sıcaklık parametrelerini ayarlayın: {msg}[/red]")
        raise typer.Exit(1)

    #Yinelenenleri kontrol edin
    existing = _list_yaml_configs()
    provider_model = f"{data['provider']}/{data['model']}"
    for cfg in existing:
        pm = f"{cfg.get('provider')}/{cfg.get('model')}"
        if pm == provider_model and not force:
            console.print(
                "[yellow]⚠Aynı ada sahip bir konfigürasyon zaten mevcut, şunu kullanın:[cyan]--force[/cyan]kapak[/yellow]"
            )
            raise typer.Exit(1)

    #kaydetmek
    path = _save_model_config(data)
    console.print(f"[green]✓İthal: {data['name']}[/green]")
    console.print(f"[dim]yolu kaydet: {path}[/dim]")


@app.command("export")
def export_model(
    name: str = typer.Argument(..., help="Model adı (tam ad, ör.'DeepSeek V4')"),
    yaml_out: bool = typer.Option(False, "--yaml", help="çıktıYAMLbiçim (varsayılanJSON)"),
    copy: bool = typer.Option(False, "--copy", help="Yapılandırma metnini panoya kopyala"),
) -> None:
    """Model yapılandırmasını dışa aktar (destekler)YAML/JSON)"""
    #aramak
    target = None
    #Önce gömülü verilerde bulun
    for cfg in BUILTIN_CATWALK_MODELS:
        if name.lower() in cfg["name"].lower():
            target = dict(cfg)
            break
    #Daha sonra kullanıcı yapılandırmasında arama yapın
    if target is None:
        for cfg in _list_yaml_configs():
            if name.lower() in cfg.get("name", "").lower():
                target = dict(cfg)
                break

    if target is None:
        console.print(f"[red]✗etkileşimli tarama: {name}[/red]")
        console.print(
            "[dim]kullanmak[cyan]omc model list --extended[/cyan]Tüm modelleri görüntüle[/dim]"
        )
        raise typer.Exit(1)

    #Dahili alanları kaldır
    target.pop("_source", None)
    target.pop("_file", None)

    if yaml_out:
        output = yaml.dump(
            target, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    else:
        output = json.dumps(target, ensure_ascii=False, indent=2)

    if copy:
        try:
            import pyperclip

            pyperclip.copy(output)
            console.print("[green]✓Panoya kopyalandı[/green]")
        except Exception:
            console.print("[yellow]⚠ pyperclipKurulu değil, kopyalama işlevi mevcut değil[/yellow]")
            console.print("[dim]pip install pyperclip[/dim]")
    else:
        console.print(output)


@app.command("current")
def show_current() -> None:
    """Geçerli varsayılan modeli göster"""
    current = _get_current_model()
    info = SUPPORTED_MODELS.get(current, {})

    console.print()
    console.print(f"[bold cyan]mevcut model:[/] [green]{current}[/]")

    if info:
        console.print(f"[bold cyan]isim:[/] {info.get('name', '-')}")
        console.print(f"[bold cyan]Hiyerarşi:[/] {info.get('tier', '-')}")
        console.print(f"[bold cyan]Açıklama:[/] [dim]{info.get('note', '-')}[/dim]")

    api_key = _get_current_api_key(current)
    if api_key:
        console.print("[bold cyan]API Key:[/] [green]✓yapılandırılmış[/green]")
    else:
        console.print("[bold cyan]API Key:[/] [red]✗Yapılandırılmadı (ortam değişkenlerinin ayarlanması gerekiyor)[/red]")
    console.print()


@app.command("switch")
def switch_model_cmd(
    model_name: str = typer.Argument(..., help="ModeliID(beğenmekdeepseek, glm)"),
) -> None:
    """Varsayılan modeli değiştir (yapılandırma dosyasını yaz, yeniden başlatmaya gerek yok)"""
    if model_name not in SUPPORTED_MODELS:
        console.print(f"[red]hata:Desteklenmeyen model'{model_name}'[/red]")
        console.print()
        console.print("Desteklenen modeller:")
        for model_id in SUPPORTED_MODELS:
            console.print(f"  - {model_id}")
        raise typer.Exit(1)

    config = _load_config()
    old_model = config.get("default_model", "ayarlanmamış")
    config["default_model"] = model_name
    _save_config(config)

    info = SUPPORTED_MODELS[model_name]
    console.print()
    console.print("[bold green]✓Model değiştirme başarılı[/]")
    console.print(f"  [dim]eski model:[/] {old_model}")
    console.print(f"  [dim]yeni model:[/] {info['name']} ({model_name})")
    console.print(f"  [dim]Yenilemeye zorla:[/] {CONFIG_FILE}")
    console.print()
    console.print("[dim]ipucu:ortam değişkenleriOMC_DEFAULT_MODELYapılandırma dosyasının üzerine yazacak[/dim]")


@app.command("sync")
def sync_models(
    force: bool = typer.Option(False, "--force", "-f", help="Yenilemeye zorla, önbelleği yoksay"),
    timeout: int = typer.Option(5, "--timeout", "-t", help="İstek zaman aşımı (saniye)"),
) -> None:
    """Yapılandırma yönetimi"""
    if ModelDiscovery is None:
        console.print("[red]✗Model bulma modülü yüklü değil[/red]")
        raise typer.Exit(1)

    console.print()
    console.print("[bold cyan]🔍Çeşitli üreticilerin en son modellerini kontrol etme...[/bold cyan]")
    console.print()

    discovery = ModelDiscovery()

    #Önbellek durumunu kontrol edin
    if not force:
        cached = discovery.get_cached()
        if cached:
            cached_at = cached.get("cached_at", "bilinmiyor")
            console.print(
                f"[dim]Kod Teşhis Kontrolü{cached_at}),kullanmak--forceYenilemeye zorla[/dim]"
            )
            console.print()

    #Senkronizasyon gerçekleştir
    result = discovery.sync(force=force, timeout=timeout)

    if result.get("status") == "cached":
        discovered = result.get("data", {})
        console.print("[yellow]⚠çıkış yapmak[/yellow]")
    else:
        discovered = result.get("data", {})
        providers_stats = result.get("providers", {})

        #Her üreticinin durumunu görüntüleyin
        for provider, count in providers_stats.items():
            if count > 0:
                console.print(f"  [green]✅[/] {provider}:Keşfetmek{count}Komut tanımı")
            else:
                #Var olup olmadığını kontrol edinAPI key
                config = discovery.PROVIDER_APIS.get(provider, {})
                if config.get("skip"):
                    reason = config.get("reason", "Dinamik keşif desteklenmiyor")
                    console.print(f"  [dim]⏭️  {provider}: {reason}[/dim]")
                elif config.get("key_env") and not os.getenv(config["key_env"]):
                    console.print(f"  [yellow]⚠️[/] {provider}: API KeyYapılandırılmadı")
                else:
                    console.print(f"  [dim]⚪ {provider}:Model yok veya istek başarısız oldu[/dim]")

    #Yerleşik modelleri karşılaştırın
    comparison = discovery.compare_with_builtin(discovered, BUILTIN_CATWALK_MODELS)
    new_models = comparison.get("new_models", [])
    removed_models = comparison.get("removed_models", [])

    console.print()

    if new_models:
        console.print(f"[bold green]✨Keşfetmek{len(new_models)}yeni modeller:[/bold green]")
        for m in new_models[:10]:  #10'a kadar görüntüle
            console.print(f"   • {m['model_id']} ({m['provider']})")
        if len(new_models) > 10:
            console.print(f"   ...Ayrıca{len(new_models) - 10}bireysel")
        console.print()
        console.print(
            "[dim]💡ipucu:kullanmak[cyan]omc model import <url>[/cyan]Yeni model ekle[/dim]"
        )
    else:
        console.print("[dim]Yeni model bulunamadı[/dim]")

    if removed_models:
        console.print()
        console.print(f"[yellow]⚠️  {len(removed_models)}modeller çevrimdışı olabilir:[/yellow]")
        for m in removed_models[:5]:
            console.print(f"   • {m['name']} ({m['model_id']})")

    console.print()
    console.print(f"[dim]Önbellek dosyaları: {discovery.CACHE_FILE}[/dim]")


# =============================================================================
#Komut uygulaması-itibarencli_models_recommend.pybirleştirme
# =============================================================================


@app.command("recommend")
def recommend_model(
    task: str = typer.Option(
        None, "--task", "-t", help="Görev türü: coding/reasoning/creative/fast/chat"
    ),
) -> None:
    """Model Önerileri — Senaryolara göre ücretsiz modeller önerin

Örnek:
        omc model recommend
        omc model recommend --task coding
        omc model recommend --task fast
    """
    if task:
        _show_task_recommendation(task)
    else:
        _show_all_recommendations()


# =============================================================================
#Komut uygulaması-itibarencli_models.pybirleştirme
# =============================================================================


@app.command("share")
def share_model(
    name: str = typer.Option(None, "--name", "-n", help="Model konfigürasyon adı"),
    provider: str = typer.Option(
        None, "--provider", "-p", help="sağlayıcı (örn.deepseek, glm)"
    ),
    base_url: str = typer.Option(None, "--url", "-u", help="API Base URL"),
    model: str = typer.Option(None, "--model", "-m", help="ModeliID"),
    description: str = typer.Option(None, "--desc", "-d", help="Kullanım talimatları/betimlemek"),
    author: str = typer.Option(None, "--author", "-a", help="Yazar adı"),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", help="etkileşimli giriş"
    ),
) -> None:
    """Model yapılandırmasını topluluk dizininde paylaşın

Örnek:
        omc model share
        omc model share --name "My DeepSeek" --provider deepseek --url https://api.deepseek.com --model deepseek-chat
    """
    _ensure_shared_dir()

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]📤Model yapılandırmasını paylaş[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    #etkileşimli giriş
    if interactive and not all([name, provider, base_url, model]):
        console.print("[dim]Lütfen model yapılandırma bilgilerini girin (Ctrl+Cİptal etmek):[/dim]")
        console.print()

        if not name:
            name = Prompt.ask("[bold]Yapılandırma adı[/]", default="My Model Config")

        if not provider:
            provider = Prompt.ask(
                "[bold]sağlayıcı[/]",
                default="deepseek",
            )

        if not model:
            model = Prompt.ask(
                "[bold]ModeliID[/]",
                default="deepseek-chat",
            )

        if not base_url:
            base_url = Prompt.ask(
                "[bold]API Base URL[/]",
                default="https://api.deepseek.com/v1",
            )

        if not description:
            description = Prompt.ask(
                "[bold]betimlemek/Kullanım talimatları[/]",
                default="",
            )

    #Gerekli alanları doğrulayın
    if not all([name, provider, base_url, model]):
        console.print("[red]✗Gerekli parametre eksik: name, provider, base_url, model[/red]")
        raise typer.Exit(1)

    #yazar
    if not author:
        author = _get_author_name()

    #Yapı yapılandırması
    config_id = str(uuid.uuid4())[:8]
    config = {
        "id": config_id,
        "name": name,
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "description": description or "",
        "author": author,
        "created_at": datetime.now().isoformat(),
        "version": "1.0",
    }

    #onaylamak
    console.print()
    console.print("[dim]Yapılandırma önizlemesi:[/dim]")
    console.print(f"  [cyan]isim:[/] {config['name']}")
    console.print(f"  [cyan]sağlayıcı:[/] {config['provider']}")
    console.print(f"  [cyan]ModeliID:[/] {config['model']}")
    console.print(f"  [cyan]API URL:[/] {config['base_url']}")
    console.print(f"  [cyan]Varsayılan modeli seçin:[/] {config['author']}")
    console.print()

    if interactive:
        if not Confirm.ask("[bold]Bu yapılandırmayı paylaşmak istediğinizden emin misiniz?[/]", default=True):
            console.print("[yellow]İptal edildi[/yellow]")
            return

    #kaydetmek
    filename = f"{config_id}-{provider}-{model.replace('/', '-')}.json"
    filepath = SHARED_MODELS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    console.print()
    console.print("[green]✓Paylaşılan model yapılandırması[/green]")
    console.print(f"[dim]yolu kaydet: {filepath}[/dim]")
    console.print()
    console.print(
        "[dim]💡ipucu:Geçilebilir[cyan]omc model browse[/cyan]Topluluk yapılandırmasını görüntüle[/dim]"
    )


@app.command("browse")
def browse_models(
    provider: str = typer.Option(None, "--provider", "-p", help="Sağlayıcıya göre filtrele"),
    author: str = typer.Option(None, "--author", "-a", help="Yazara göre filtrele"),
    search: str = typer.Option(None, "--search", "-s", help="Anahtar kelimeleri arayın"),
    limit: int = typer.Option(20, "--limit", "-l", help="Miktar sınırını görüntüle"),
) -> None:
    """Topluluk tarafından paylaşılan model yapılandırmalarına göz atın

Örnek:
        omc model browse
        omc model browse --provider deepseek
        omc model browse --search "özgür"
    """
    _ensure_shared_dir()
    configs = _list_shared_configs()

    if not configs:
        console.print()
        console.print("[yellow]Henüz paylaşılan bir model yapılandırması yok.[/yellow]")
        console.print()
        console.print("[dim]💡kullanmak[cyan]omc model share[/cyan]Yapılandırmanızı paylaşın[/dim]")
        return

    #filtre
    if provider:
        configs = [c for c in configs if c.get("provider") == provider]
    if author:
        configs = [c for c in configs if author.lower() in c.get("author", "").lower()]
    if search:
        q = search.lower()
        configs = [
            c
            for c in configs
            if q in c.get("name", "").lower()
            or q in c.get("description", "").lower()
            or q in c.get("model", "").lower()
        ]

    #sınırlı miktar
    configs = configs[:limit]

    #göstermek
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]📚Topluluk modeli yapılandırması[/bold cyan]- yaygın{len(configs)}bireysel",
            border_style="cyan",
        )
    )
    console.print()

    table = Table(show_lines=True)
    table.add_column("ID", style="dim", width=8)
    table.add_column("isim", style="cyan", no_wrap=False)
    table.add_column("sağlayıcı", style="blue")
    table.add_column("Modeli", style="green")
    table.add_column("Varsayılan modeli seçin", style="magenta")
    table.add_column("betimlemek", style="dim", no_wrap=False)

    for cfg in configs:
        table.add_row(
            cfg.get("id", "-")[:8],
            cfg.get("name", "-"),
            cfg.get("provider", "-"),
            cfg.get("model", "-"),
            cfg.get("author", "-"),
            cfg.get("description", "")[:50] or "-",
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Yapılandırma dizini: {SHARED_MODELS_DIR}[/dim]")
    console.print("[dim]💡kullanmak[cyan]omc model show <id>[/cyan]ayrıntıları kontrol et[/dim]")


@app.command("show")
def show_shared_model(
    config_id: str = typer.Argument(..., help="YapılandırmaID(İlk 8)"),
    export: bool = typer.Option(False, "--export", "-e", help="Farklı dışa aktarJSON"),
) -> None:
    """Model yapılandırma ayrıntılarını görüntüleyin

Örnek:
        omc model show abc12345
        omc model show abc12345 --export
    """
    configs = _list_shared_configs()

    #Bulmak
    target = None
    for cfg in configs:
        if cfg.get("id", "").startswith(config_id):
            target = cfg
            break

    if not target:
        console.print(f"[red]✗Yapılandırma bulunamadı: {config_id}[/red]")
        raise typer.Exit(1)

    if export:
        #Dahili alanları kaldır
        output = dict(target)
        output.pop("_file", None)
        console.print_json(json.dumps(output, ensure_ascii=False, indent=2))
        return

    #Ayrıntılı ekran
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]{target.get('name', 'Unknown')}[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()
    console.print(f"  [dim]ID:[/]       {target.get('id', '-')}")
    console.print(f"  [dim]sağlayıcı:[/]   {target.get('provider', '-')}")
    console.print(f"  [dim]ModeliID:[/]  {target.get('model', '-')}")
    console.print(f"  [dim]API URL:[/]  {target.get('base_url', '-')}")
    console.print(f"  [dim]Varsayılan modeli seçin:[/]     {target.get('author', '-')}")
    console.print(f"  [dim]yaratılış zamanı:[/] {target.get('created_at', '-')}")
    console.print(f"  [dim]Sürüm:[/]     {target.get('version', '-')}")
    console.print()
    if target.get("description"):
        console.print(f"  [dim]betimlemek:[/] {target['description']}")
        console.print()
    console.print(f"  [dim]belge:[/] {target.get('_file', '-')}")
    console.print()


@app.command("shared")
def list_shared() -> None:
    """Yerel olarak paylaşılan tüm yapılandırmaları listeleyin

Örnek:
        omc model shared
    """
    configs = _list_shared_configs()

    if not configs:
        console.print("[yellow]Henüz paylaşılan yapılandırma yok[/yellow]")
        return

    console.print()
    console.print(f"[bold cyan]Yerel paylaşılan yapılandırma({len(configs)}bireysel):[/]")
    console.print()

    for cfg in configs:
        console.print(
            f"  • [cyan]{cfg.get('id', '-')}[/] - {cfg.get('name', '-')} ({cfg.get('provider', '-')})"
        )

    console.print()
    console.print(f"[dim]İçindekiler: {SHARED_MODELS_DIR}[/dim]")


@app.command("remove")
def remove_shared_model(
    config_id: str = typer.Argument(..., help="YapılandırmaID"),
    force: bool = typer.Option(False, "--force", "-f", help="Onayı atla"),
) -> None:
    """Paylaşılan yapılandırmayı sil

Örnek:
        omc model remove abc12345
        omc model remove abc12345 --force
    """
    configs = _list_shared_configs()

    #Bulmak
    target = None
    for cfg in configs:
        if cfg.get("id", "").startswith(config_id):
            target = cfg
            break

    if not target:
        console.print(f"[red]✗Yapılandırma bulunamadı: {config_id}[/red]")
        raise typer.Exit(1)

    filepath = SHARED_MODELS_DIR / target["_file"]

    if not force:
        console.print(
            f"[yellow]Silinmek üzere:[/] {target.get('name', '-')} ({target.get('id', '-')})"
        )
        if not Confirm.ask("[bold]Silme işlemi onaylansın mı?[/]", default=False):
            console.print("[dim]İptal edildi[/dim]")
            return

    filepath.unlink()
    console.print(f"[green]✓Silindi: {target.get('name', '-')}[/green]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Mevcut tüm modelleri listeleyin (destekler)-Kontrol etmek/anahtar/paylaşmak/tavsiye etmek"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())



if __name__ == "__main__":
    app()
