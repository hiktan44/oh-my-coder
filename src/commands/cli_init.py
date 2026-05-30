# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Init CLI -Etkileşimli başlatma önyüklemesi

Emir:
- omc init  #Yeni kullanıcılara ilk kez yapılandırma yoluyla etkileşimli olarak rehberlik edin

işlem:
1.Hoş geldiniz arayüzü
2.Modeli seçin
3.girmekAPI Key
4.Çalışma dizinini ayarla
5.Yapılandırma doğrulaması
6.Tamamlama istemi
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

app = typer.Typer(
    name="init",
    help="Etkileşimli başlatma önyüklemesi-Düşünce zinciri başladı",
    add_completion=False,
)

#Yapılandırma dosyası yolu
CONFIG_DIR = Path.home() / ".omc"
CONFIG_FILE = CONFIG_DIR / "config.json"

#Desteklenen modellerin listesi (referanscli_model.py)
SUPPORTED_MODELS = {
    "deepseek": {
        "name": "DeepSeek",
        "tier": "low",
        "note": "Yüksek maliyet performansı, önerilir",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "glm": {
        "name": "Bilgelik spektrumuGLM",
        "tier": "low",
        "note": "GLM-4.7-Flashkullanımı ücretsiz",
        "api_key_env": "ZHIPUAI_API_KEY",
    },
    "wenxin": {
        "name": "Wenxinyiyan",
        "tier": "medium",
        "note": "Baidu",
        "api_key_env": "ERNIE_API_KEY",
    },
    "tongyi": {
        "name": "Tongyi",
        "tier": "medium",
        "note": "Ali",
        "api_key_env": "DASHSCOPE_API_KEY",
    },
    "minimax": {
        "name": "MiniMax",
        "tier": "medium",
        "note": "",
        "api_key_env": "MINIMAX_API_KEY",
    },
    "kimi": {
        "name": "Kimi",
        "tier": "medium",
        "note": "ayın karanlık yüzü",
        "api_key_env": "KIMI_API_KEY",
    },
    "hunyuan": {
        "name": "Tencent Hunyuan",
        "tier": "medium",
        "note": "Tencent",
        "api_key_env": "HUNYUAN_API_KEY",
    },
    "doubao": {
        "name": "Doubao (ByteDance)",
        "tier": "medium",
        "note": "ByteDance",
        "api_key_env": "DOUBAO_API_KEY",
    },
    "tiangong": {
        "name": "TiangongAI",
        "tier": "medium",
        "note": "",
        "api_key_env": "TIANGONG_API_KEY",
    },
    "spark": {
        "name": "Yalnızca onarım önerilerinin gösterilip gösterilmeyeceği",
        "tier": "medium",
        "note": "",
        "api_key_env": "SPARK_API_KEY",
    },
    "baichuan": {
        "name": "Baichuan İstihbaratı",
        "tier": "medium",
        "note": "",
        "api_key_env": "BAICHUAN_API_KEY",
    },
    "mimo": {
        "name": "DarıMiMo",
        "tier": "medium",
        "note": "Darı",
        "api_key_env": "MIMO_API_KEY",
    },
}

#sürüm numarası (dancli.pysenkron)
__version__ = "0.2.0"


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


def _mask_api_key(key: str) -> str:
    """Duyarsızlaştırılmış ekranAPI Key"""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def _tier_style(tier: str) -> str:
    """buna göretierDönüş rengi"""
    return {"free": "green", "low": "cyan", "medium": "yellow", "high": "red"}.get(
        tier, "white"
    )


# =============================================================================
#ana komut
# =============================================================================


@app.callback(invoke_without_command=True)
def init_wizard(
    ctx: typer.Context,
) -> None:
    """
Etkileşimli başlatma önyüklemesi-Düşünce zinciri başladı

işlem:
    1.Hoş geldiniz arayüzü
    2.Varsayılan modeli seçin
    3.girmekAPI Key
    4.Çalışma dizinini ayarla
    5.Yapılandırmayı onaylayın
    6.Sona ermek
    """
    if ctx.invoked_subcommand is not None:
        return

    # ============================================================
    #1. Adım:Hoş geldiniz arayüzü
    # ============================================================
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]🎉Hoş geldinOh My Coder![/bold cyan]\n\n"
            f"[dim]Sürüm: v{__version__}[/dim]\n"
            f"[dim]çoklu ajanAIProgramlama Asistanı[/dim]\n\n"
            f"[yellow]Geliştirme ortamınızı yapılandırmaya başlayalım![/yellow]",
            title="🚀Başlatma sihirbazı",
            border_style="cyan",
        )
    )
    console.print()

    # ============================================================
    #2. Adım:Modeli seçin
    # ============================================================
    console.print("[bold]📋1. Adım/4:Varsayılan modeli seçin[/bold]")
    console.print("[dim]Lütfen kullanmak istediğinizi seçinAIvarsayılan model olarak model[/dim]")
    console.print()

    #Model listesini göster
    table = Table(title="Mevcut modeller", show_header=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("ModeliID", style="cyan")
    table.add_column("isim", style="green")
    table.add_column("Hiyerarşi", style="yellow")
    table.add_column("tavsiye etmek", style="magenta")
    table.add_column("Açıklama", style="dim")

    #Tavsiyeye göre sırala:free > low > medium
    tier_order = {"free": 0, "low": 1, "medium": 2, "high": 3}
    sorted_models = sorted(
        SUPPORTED_MODELS.items(),
        key=lambda x: tier_order.get(x[1]["tier"], 99),
    )

    for i, (model_id, info) in enumerate(sorted_models, 1):
        tier = info["tier"]
        tier_color = _tier_style(tier)
        recommend = "⭐tavsiye etmek" if tier in ("free", "low") else ""
        table.add_row(
            str(i),
            model_id,
            info["name"],
            f"[{tier_color}]{tier}[/{tier_color}]",
            recommend,
            info.get("note", ""),
        )

    console.print(table)
    console.print()

    #Kullanıcı seçim modeli
    model_choices = [str(i) for i in range(1, len(sorted_models) + 1)]
    model_id_choices = [m[0] for m in sorted_models]

    while True:
        choice = Prompt.ask(
            "[bold]Modeli seçmek için lütfen seri numarasını girin[/bold]",
            default="1",
        )
        if choice in model_choices:
            idx = int(choice) - 1
            selected_model_id = model_id_choices[idx]
            selected_model_info = sorted_models[idx][1]
            break
        else:
            console.print(
                f"[red]Geçersiz seçim: {choice}, lütfen 1 girin-{len(sorted_models)}[/red]"
            )

    console.print()
    console.print(
        f"[green]✓Seçildi: {selected_model_info['name']} ({selected_model_id})[/green]"
    )
    console.print()

    # ============================================================
    #3. Adım:girmekAPI Key
    # ============================================================
    console.print("[bold]🔑2. Adım/4:YapılandırmaAPI Key[/bold]")

    #Ortam değişkenlerinin zaten mevcut olup olmadığını kontrol edinAPI Key
    api_key_env = selected_model_info["api_key_env"]
    existing_key = os.getenv(api_key_env)

    if existing_key:
        console.print(f"[dim]Ortam değişkeni algılandı{api_key_env}Zaten ayarlandı[/dim]")
        use_existing = Confirm.ask(
            "Mevcut olanın kullanılıp kullanılmayacağıAPI Key?",
            default=True,
        )
        if use_existing:
            api_key = existing_key
            console.print(
                f"[green]✓Mevcut olanı kullanAPI Key: {_mask_api_key(api_key)}[/green]"
            )
        else:
            api_key = Prompt.ask(
                f"Lütfen yeni girin{selected_model_info['name']} API Key",
                password=True,
            )
    else:
        console.print(f"[dim]Lütfen girin{selected_model_info['name']}ile ilgiliAPI Key[/dim]")
        console.print("[dim]ipucu: API Keyekranda görüntülenmeyecek[/dim]")
        api_key = Prompt.ask(
            "API Key",
            password=True,
        )

    if not api_key:
        console.print("[yellow]⚠GirilmediAPI Key, konfigürasyon anahtar olmadan kaydedilecektir[/yellow]")
        api_key = ""

    console.print()

    # ============================================================
    #4. Adım:Çalışma dizinini ayarla
    # ============================================================
    console.print("[bold]📁3. Adım/4:Çalışma dizinini ayarla[/bold]")
    console.print("[dim]Çalışma diziniOh My CoderVarsayılan proje yolu[/dim]")

    current_dir = str(Path.cwd())
    work_dir = Prompt.ask(
        "Lütfen çalışma dizini yolunu girin",
        default=current_dir,
    )

    #Yolu doğrula
    work_path = Path(work_dir).expanduser().resolve()
    if not work_path.exists():
        create_dir = Confirm.ask(
            f"İçindekiler{work_path}Mevcut değil mi, yaratılsın mı?",
            default=True,
        )
        if create_dir:
            try:
                work_path.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓Dizin oluşturuldu: {work_path}[/green]")
            except Exception as e:
                console.print(f"[red]✗Dizin oluşturulamadı: {e}[/red]")
                work_path = Path.cwd()
                console.print(f"[yellow]geçerli dizini kullan: {work_path}[/yellow]")
    else:
        console.print(f"[green]✓çalışma dizini: {work_path}[/green]")

    console.print()

    # ============================================================
    #Adım 5:Yapılandırma doğrulaması
    # ============================================================
    console.print("[bold]✅4. Adım/4:Yapılandırmayı onaylayın[/bold]")
    console.print()

    #Lütfen bir eylem seçin
    summary_table = Table(title="Yapılandırma özeti", show_header=False)
    summary_table.add_column("proje", style="cyan")
    summary_table.add_column("değer", style="green")

    summary_table.add_row(
        "Varsayılan model", f"{selected_model_info['name']} ({selected_model_id})"
    )
    summary_table.add_row(
        "API Key", _mask_api_key(api_key) if api_key else "[yellow]ayarlanmamış[/yellow]"
    )
    summary_table.add_row("çalışma dizini", str(work_path))
    summary_table.add_row("Yenilemeye zorla", str(CONFIG_FILE))

    console.print(summary_table)
    console.print()

    #onaylamak
    confirm = Confirm.ask(
        "[bold]Yukarıdaki yapılandırmayı kaydettiğinizden emin misiniz?[/bold]",
        default=True,
    )

    if not confirm:
        console.print("[yellow]❌Yapılandırma iptal edildi[/yellow]")
        raise typer.Exit(0)

    # ============================================================
    #Yapılandırmayı kaydet
    # ============================================================
    config = _load_config()
    config["default_model"] = selected_model_id
    config["work_dir"] = str(work_path)

    #kaydetmekAPI anahtarı yapılandırmasıa (kullanıcı yeni bir tane girmişse)
    if api_key and api_key != existing_key:
        api_keys = config.get("api_keys", {})
        api_keys[selected_model_id] = api_key
        config["api_keys"] = api_keys

    _save_config(config)

    #Ayrıca ortam değişkenlerini de ayarlayın (mevcut oturum için etkilidir)
    if api_key:
        os.environ[api_key_env] = api_key

    # ============================================================
    #Adım 6:Tamamlama istemi
    # ============================================================
    console.print()
    console.print(
        Panel.fit(
            "[bold green]✅Yapılandırma tamamlandı![/bold green]\n\n"
            f"[dim]Yapılandırma şuraya kaydedildi:: {CONFIG_FILE}[/dim]\n\n"
            "[bold]🚀Sonraki adım:[/bold]\n"
            "  [cyan]omc agent list[/cyan]Mevcut olanı görüntüleAgent\n"
            "  [cyan]omc model list[/cyan]Tüm modelleri görüntüle\n"
            '  [cyan]omc run "<task>"[/cyan]görevleri gerçekleştirmek\n'
            "  [cyan]omc --help[/cyan]Tüm komutları görüntüle\n\n"
            "[dim]ipucu:kullanmak[cyan]omc model switch <name>[/cyan]İstediğiniz zaman modelleri değiştirebilir[/dim]",
            title="🎉Başlatma tamamlandı",
            border_style="green",
        )
    )
    console.print()


@app.command("reset")
def reset_config() -> None:
    """Yapılandırmayı sıfırla (yapılandırma dosyasını sil)"""
    if not CONFIG_FILE.exists():
        console.print("[yellow]Yapılandırma dosyası mevcut değil, sıfırlamaya gerek yok[/yellow]")
        return

    confirm = Confirm.ask(
        f"[bold red]Yapılandırma dosyasını silmek istediğinizden emin misiniz?{CONFIG_FILE}?[/bold red]",
        default=False,
    )

    if confirm:
        CONFIG_FILE.unlink()
        console.print(f"[green]✓Profil silindi: {CONFIG_FILE}[/green]")
        console.print("[dim]koşmak[cyan]omc init[/cyan]Yeniden yapılandır[/dim]")
    else:
        console.print("[dim]İptal edildi[/dim]")


@app.command("show")
def show_config() -> None:
    """Geçerli yapılandırmayı göster"""
    if not CONFIG_FILE.exists():
        console.print("[yellow]Yapılandırma dosyası mevcut değil, lütfen önce çalıştırın[cyan]omc init[/cyan][/yellow]")
        raise typer.Exit(1)

    config = _load_config()
    if not config:
        console.print("[yellow]Yapılandırma dosyası boş, lütfen önce çalıştırın[cyan]omc init[/cyan][/yellow]")
        raise typer.Exit(1)

    console.print()
    console.print(f"[bold cyan]Yenilemeye zorla: {CONFIG_FILE}[/bold cyan]")
    console.print()

    table = Table(show_header=False)
    table.add_column("proje", style="cyan")
    table.add_column("değer", style="green")

    #Ana yapılandırma öğelerini göster
    if "default_model" in config:
        model_id = config["default_model"]
        model_info = SUPPORTED_MODELS.get(model_id, {})
        model_name = model_info.get("name", model_id)
        table.add_row("Varsayılan model", f"{model_name} ({model_id})")

    if "work_dir" in config:
        table.add_row("çalışma dizini", config["work_dir"])

    # API Keys(duyarsızlaştırılmış ekran)
    if "api_keys" in config:
        for model_id, key in config["api_keys"].items():
            table.add_row(f"{model_id} API Key", _mask_api_key(key))

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
