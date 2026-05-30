from __future__ import annotations

"""
omc self-configEmir-kendi kendini yapılandırmaSkill

Olası nedenler:
Kullanıcılar diyor ki"YapılandırmaGLM API",AIYapılandırma otomatik olarak tamamlanır.

kullanmakLLMKullanıcının amacını anlayın ve ilgili yapılandırmayı çağırınAPI.
"""


import contextlib
import json
import re
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

try:
    from ..core.config_manager import ConfigManager  # noqa: F401
    from ..core.router import ModelRouter  # noqa: F401

    HAS_CORE = True
except ImportError:
    HAS_CORE = False

app = typer.Typer(help="kendini yapılandırma komutu-Her şeyi doğal dille yapılandırın")
console = Console()


#Niyet tanıma kurallarını yapılandırma
CONFIG_INTENTS = {
    #Model konfigürasyonu
    "api_key": {
        "patterns": [
            r"Yapılandırma.*API.*KEY",
            r"kurmak.*API.*KEY",
            r"api.?key",
            r"api_key",
            r"Yapılandırma.*anahtar",
        ],
        "action": "set_api_key",
        "examples": ["YapılandırmaGLM API KEY", "kurmakDeepSeek API Key"],
    },
    "model": {
        "patterns": [
            r"anahtar.*Modeli",
            r"kullanmak.*Modeli",
            r"set.*model",
            r"default.*model",
            r"Modeli.*varsayılan",
        ],
        "action": "set_default_model",
        "examples": ["geçiş yapmakDeepSeekModeli", "kullanmakGLMvarsayılan model olarak"],
    },
    "proxy": {
        "patterns": [
            r"Yapılandırma.*oyunculuk",
            r"kurmak.*oyunculuk",
            r"proxy",
            r"http.proxy",
        ],
        "action": "set_proxy",
        "examples": ["YapılandırmaHTTPoyunculuk", "Proxy'yi 127'ye ayarla.0.0.1:4780"],
    },
    "temperature": {
        "patterns": [
            r"sıcaklık",
            r"temperature",
            r"yaratıcılık.*kurmak",
        ],
        "action": "set_temperature",
        "examples": ["Sıcaklığı 0'a ayarlayın.7", "Yaratıcı sıcaklığı artırın"],
    },
    "template": {
        "patterns": [
            r"şablon",
            r"template",
            r"İş akışı.*Yapılandırma",
        ],
        "action": "set_template",
        "examples": ["Kod inceleme şablonlarını yapılandırma", "Varsayılan iş akışını ayarla"],
    },
}

#Model sağlayıcı listesi
MODEL_PROVIDERS = {
    "glm": {
        "name": "Bilgelik spektrumuGLM",
        "api_key_env": "ZHIPUAI_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "free_quota": "2 milyonTokens",
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/",
        "free_quota": "60 yuan",
    },
    "mimo": {
        "name": "MiMo",
        "api_key_env": "MIMOX_API_KEY",
        "base_url": "https://api.minimax.chat/v1",
        "free_quota": "sınırsız",
    },
    "qwen": {
        "name": "Tongyi",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "free_quota": "Ücretsiz kota var",
    },
    "wenxin": {
        "name": "Wenxinyiyan",
        "api_key_env": "ERNIE_API_KEY",
        "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1",
        "free_quota": "Ücretsiz kota var",
    },
}


def parse_config_intent(text: str) -> Optional[dict[str, Any]]:
    """Yapılandırma amacını ayrıştır"""
    text_lower = text.lower()

    for intent_id, intent_info in CONFIG_INTENTS.items():
        for pattern in intent_info["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return {
                    "intent": intent_id,
                    "action": intent_info["action"],
                    "raw_text": text,
                }

    #Model sağlayıcısını tanımlamaya çalışın
    for provider_id, provider_info in MODEL_PROVIDERS.items():
        if provider_id in text_lower or provider_info["name"] in text:
            return {
                "intent": "api_key",
                "action": "set_api_key",
                "provider": provider_id,
                "raw_text": text,
            }

    return None


def detect_api_key_in_text(text: str) -> Optional[str]:
    """metinden alıntıAPI Key"""
    #yaygınAPI KeyBiçim
    patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAIBiçim
        r"[a-zA-Z0-9]{32,}",  #ortak format
        r'["\']([a-zA-Z0-9_-]{20,})["\']',  #tırnak işaretleri ile
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            key = match.group(0).strip("'\"")
            #Bariz olmayanları filtrelekeyiçerik
            if not key.startswith("http") and len(key) > 20:
                return key

    return None


async def execute_config(config: dict[str, Any], api_key: Optional[str] = None) -> bool:
    """Yapılandırmayı yürüt"""
    action = config.get("action")

    if action == "set_api_key":
        return await _set_api_key(config, api_key)
    if action == "set_default_model":
        return await _set_default_model(config)
    if action == "set_proxy":
        return await _set_proxy(config)
    if action == "set_temperature":
        return await _set_temperature(config)
    console.print(f"[yellow]Bilinmeyen yapılandırma eylemi: {action}[/yellow]")
    return False


async def _set_api_key(config: dict[str, Any], api_key: Optional[str] = None) -> bool:
    """kurmakAPI Key"""
    provider = config.get("provider")
    raw_text = config.get("raw_text", "")

    if not provider:
        #Sağlayıcıyı metinden tanımlamaya çalışın
        for pid, pinfo in MODEL_PROVIDERS.items():
            if pid in raw_text.lower() or pinfo["name"] in raw_text:
                provider = pid
                break

    if not provider:
        console.print("[yellow]Tanınmayan model sağlayıcı, lütfen açıkça belirtin:[/yellow]")
        for pid, pinfo in MODEL_PROVIDERS.items():
            console.print(f"  • {pinfo['name']} ({pid})")
        return False

    provider_info = MODEL_PROVIDERS[provider]

    #sağlanmadığı takdirdeAPI Key, kullanıcının girmesini isteyen
    if not api_key:
        console.print(f"\n[cyan]Yapılandırma{provider_info['name']} API Key[/cyan]")
        console.print(f"[dim]Ücretsiz kota: {provider_info['free_quota']}[/dim]")
        api_key = Prompt.ask(
            f"Lütfen girin{provider_info['name']} API Key",
            password=True,
        )

    if not api_key or len(api_key) < 10:
        console.print("[red]API KeyYürütme[/red]")
        return False

    #Ortam değişkeni dosyasını yaz
    env_file = Path.home() / ".omc" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)

    #Mevcut yapılandırmayı oku
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    #Yapılandırmayı güncelle
    env_vars[provider_info["api_key_env"]] = api_key

    #dosya yaz
    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    console.print(f"[green]✅kaydedildi{provider_info['name']} API Key[/green]")
    console.print(f"[dim]Yenilemeye zorla: {env_file}[/dim]")

    return True


async def _set_default_model(config: dict[str, Any]) -> bool:
    """Varsayılan modeli ayarla"""
    console.print("\n[cyan]Varsayılan modeli ayarla[/cyan]\n")

    #Mevcut modelleri göster
    table = Table(title="Mevcut modeller")
    table.add_column("ID", style="cyan")
    table.add_column("isim", style="white")
    table.add_column("Ücretsiz kota", style="dim")

    for pid, pinfo in MODEL_PROVIDERS.items():
        table.add_row(pid, pinfo["name"], pinfo["free_quota"])

    console.print(table)

    model_id = Prompt.ask(
        "\nLütfen bir model seçinID",
        default="glm",
        choices=list(MODEL_PROVIDERS.keys()),
    )

    #Yapılandırma dosyasını güncelle
    config_file = Path.home() / ".omc" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config_data = {}
    if config_file.exists():
        with contextlib.suppress(Exception):
            config_data = json.loads(config_file.read_text())

    config_data["default_model"] = model_id

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    console.print(
        f"[green]✅Varsayılan model şu şekilde ayarlandı:{MODEL_PROVIDERS[model_id]['name']}[/green]"
    )
    return True


async def _set_proxy(config: dict[str, Any]) -> bool:
    """Proxy'yi ayarla"""
    console.print("\n[cyan]YapılandırmaHTTPoyunculuk[/cyan]")

    proxy = Prompt.ask("Lütfen proxy adresini girin", default="http://127.0.0.1:4780")

    if not proxy.startswith("http"):
        proxy = f"http://{proxy}"

    #Ortam değişkenlerini güncelleme
    env_file = Path.home() / ".omc" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)

    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    env_vars["HTTP_PROXY"] = proxy
    env_vars["HTTPS_PROXY"] = proxy

    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    console.print(f"[green]✅Proxy şu şekilde ayarlandı:{proxy}[/green]")
    return True


async def _set_temperature(config: dict[str, Any]) -> bool:
    """Sıcaklık parametrelerini ayarlayın"""
    console.print("\n[cyan]Model sıcaklığını ayarla[/cyan]")

    temp = Prompt.ask("Lütfen sıcaklık değerini giriniz", default="0.7")

    try:
        temp_float = float(temp)
        if not 0 <= temp_float <= 2:
            console.print("[yellow]Testleri çalıştır-2 arasında[/yellow]")
    except ValueError:
        console.print("[red]Geçersiz sıcaklık değeri[/red]")
        return False

    #Yapılandırma dosyasını güncelle
    config_file = Path.home() / ".omc" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config_data = {}
    if config_file.exists():
        with contextlib.suppress(Exception):
            config_data = json.loads(config_file.read_text())

    config_data["temperature"] = temp_float

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    console.print(f"[green]✅Sıcaklık şu şekilde ayarlandı:{temp_float}[/green]")
    return True


@app.command()
def config(
    intent: str = typer.Argument(
        None, help="Yapılandırma amacı, örneğin'YapılandırmaGLM API KEY'veya'geçiş yapmakDeepSeekModeli'"
    ),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Doğrudan sağlayınAPI Key"),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Önerilen modelleri göster"
    ),
    non_interactive: bool = typer.Option(
        False, "--yes", "-y", help="Etkileşimli olmayan mod, varsayılan değerleri kullanın"
    ),
):
    """
kendini yapılandırma komutu-Her şeyi doğal dille yapılandırın

Örnek:
        omc self-config "YapılandırmaGLM API KEY"
        omc self-config "geçiş yapmakDeepSeekModeli"
        omc self-config --key sk-xxx --provider glm
        omc self-config "Proxy'yi şuna ayarla:http://127.0.0.1:8080"
    """
    if not intent and not key:
        console.print(
            Panel.fit(
                "[bold cyan]omc self-config[/bold cyan] -Doğal dil yapılandırma asistanı\n\n"
                "Desteklenen yapılandırma türleri:\n"
                '  • API Key: [cyan]omc self-config "YapılandırmaGLM API KEY"[/cyan]\n'
                '  •Model değiştirme: [cyan]omc self-config "geçiş yapmakDeepSeekModeli"[/cyan]\n'
                '  • proxy ayarları: [cyan]omc self-config "Proxy ayarla"[/cyan]\n'
                '  • Sıcaklık parametreleri: [cyan]omc self-config "Sıcaklığı 0.7 olarak ayarla"[/cyan]\n\n'
                "[dim]Doğrudan da belirtebilirsiniz: omc self-config --key YOUR_KEY --provider glm[/dim]",
                border_style="cyan",
            )
        )
        return

    #ayrıştırma amacı
    config_info = None

    if intent:
        config_info = parse_config_intent(intent)

        #Ağ geçidi durumunu görüntüleAPI Key
        if not config_info:
            extracted_key = detect_api_key_in_text(intent)
            if extracted_key:
                config_info = {
                    "intent": "api_key",
                    "action": "set_api_key",
                    "raw_text": intent,
                }
                if key:
                    extracted_key = key

    #Doğrudan sağlanan işlemekey
    if key:
        config_info = {
            "intent": "api_key",
            "action": "set_api_key",
            "provider": provider,
            "raw_text": intent or "",
        }

    if not config_info:
        console.print("[yellow]Yapılandırmanın amacı anlaşılamıyor, lütfen daha açık bir açıklama deneyin[/yellow]")
        return

    #Yapılandırmayı yürüt
    import asyncio

    result = asyncio.run(execute_config(config_info, key if not intent else None))

    if result:
        console.print("\n[green]✅Yapılandırma tamamlandı![/green]")
    else:
        console.print("\n[red]❌Yapılandırma başarısız oldu[/red]")


@app.command("list")
def list_configs():
    """Geçerli yapılandırmayı listele"""
    console.print("\n[cyan]Mevcut yapılandırma durumu[/cyan]\n")

    #incelemekAPI Keys
    env_file = Path.home() / ".omc" / ".env"
    configured_keys = []

    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "API_KEY" in line and "=" in line:
                key_name = line.split("=")[0].strip()
                configured_keys.append(key_name)

    if configured_keys:
        console.print("[bold]yapılandırılmışAPI Keys:[/bold]")
        for key in configured_keys:
            console.print(f"  ✅ {key}")
    else:
        console.print("[dim]Hiçbiriyle yapılandırılmadıAPI Key[/dim]")

    #Varsayılan modeli kontrol edin
    config_file = Path.home() / ".omc" / "config.json"
    if config_file.exists():
        try:
            config_data = json.loads(config_file.read_text())
            if "default_model" in config_data:
                model_id = config_data["default_model"]
                model_name = MODEL_PROVIDERS.get(model_id, {}).get("name", model_id)
                console.print(f"\n[bold]Varsayılan model:[/bold] {model_name} ({model_id})")

            if "temperature" in config_data:
                console.print(f"[bold]sıcaklık ayarı:[/bold] {config_data['temperature']}")
        except Exception:
            pass

    console.print()


if __name__ == "__main__":
    app()
