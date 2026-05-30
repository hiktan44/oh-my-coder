"""Niyet tanıma kurallarını yapılandırma"""

import json
import os
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(name="config", help="⚙️Yapılandırma yönetimi")
console = Console()


@app.command()
def show(
    model: str = typer.Option(None, "--model", "-m", help="Model adını belirtin"),
):
    """Mevcut yapılandırmayı görüntüle"""
    CONFIG_DIR = Path.home() / ".omc"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def _load() -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    cfg = _load()
    console.print("[bold]⚙️Mevcut yapılandırma[/bold]\n")

    #Genel yapılandırma (başlangıçtan itibaren).env)
    console.print("[bold]Küresel yapılandırma:[/bold]")
    global_keys = [
        "DEFAULT_MODEL",
        "DEFAULT_WORKFLOW",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "KIMI_API_KEY",
        "DOUBAO_API_KEY",
    ]
    for k in global_keys:
        val = os.getenv(k, "")
        masked = _mask_secret(val)
        status = "[green]✓[/green]" if val else "[dim]—[/dim]"
        console.print(f"  {status} [cyan]{k}[/cyan] = {masked}")

    console.print()

    #Modele göre yapılandır
    models = cfg.get("models", {})
    if model:
        #Belirtilen modelin konfigürasyonunu görüntüle
        if model in models:
            console.print(f"[bold]Modeli{model}Yapılandırma:[/bold]")
            for k2, v2 in models[model].items():
                if k2 == "api_key":
                    v2 = _mask_secret(str(v2))
                console.print(f"  {k2}: {v2}")
        else:
            console.print(f"[dim]Modeli{model}Henüz yapılandırılmadı[/dim]")
    elif models:
        console.print(f"[bold]Modele göre yapılandırma ({len(models)}modeli):[/bold]")
        for name, opts in models.items():
            console.print(f"\n  [cyan]{name}[/cyan]")
            for k2, v2 in opts.items():
                if k2 == "api_key":
                    v2 = _mask_secret(str(v2))
                console.print(f"    {k2}: {v2}")
    else:
        console.print("[dim]Model başına yapılandırma yok, genel varsayılanları kullanın[/dim]")

    console.print()
    console.print(
        "[dim]yardım: omc config --helpModeli ayarlama: omc config set -m <model> -k <key> -v <value>[/dim]"
    )


@app.command()
def list():
    """Tüm yapılandırma öğelerini listeleyin"""

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    console.print("[bold]Mevcut genel yapılandırma öğeleri:[/bold]\n")
    items = [
        ("DEFAULT_MODEL", "Varsayılan model (varsayılandeepseek)"),
        ("DEFAULT_WORKFLOW", "Varsayılan iş akışı (varsayılanbuild)"),
        ("DEEPSEEK_API_KEY", "DeepSeek API Key(Önerilen, uygun maliyetli)"),
        ("DEEPSEEK_BASE_URL", "DeepSeek APIAdres (varsayılan resmi)"),
        ("KIMI_API_KEY", "KIMI API Key"),
        ("DOUBAO_API_KEY", "Doubao API Key"),
    ]
    for k, desc in items:
        val = os.getenv(k, "")
        masked = _mask_secret(val)
        status = "[green]✓[/green]" if val else "[red]✗[/red]"
        console.print(f"  {status} [cyan]{k}[/cyan]  {desc}")
        if val:
            console.print(f"Ulaşılamıyor, ağ veya proxy ayarlarını kontrol edin: {masked}")
    console.print()
    console.print(
        "[bold]Modele göre yapılandırın:[/bold] omc config set -m <model> -k <key> -v <value>"
    )
    console.print(
        "[dim]Model mevcutkey: api_key / base_url / temperature / max_tokens / system_prompt[/dim]"
    )


@app.command()
def set(
    key: str = typer.Option(None, "--key", "-k", help="Yapılandırma öğesi adı"),
    value: str = typer.Option(None, "--value", "-v", help="Yapılandırma değeri (silmek için boş bırakın)key)"),
    model: str = typer.Option(None, "--model", "-m", help="Model adını belirtin"),
):
    """Yapılandırma öğelerini ayarlayın"""
    if not key:
        console.print("[red]❗ihtiyaç--keyparametre[/red]")
        raise typer.Exit(1)

    CONFIG_DIR = Path.home() / ".omc"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load() -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _save(cfg: dict) -> None:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    if model:
        #Modele göre yapılandır
        cfg = _load()
        if "models" not in cfg:
            cfg["models"] = {}
        if model not in cfg["models"]:
            cfg["models"][model] = {}

        if value is None or value == "":
            #Bunu silkey
            cfg["models"][model].pop(key, None)
            console.print(f"[yellow]✓Kaldırıldı[/yellow] [cyan]{model}[/cyan].{key}")
        else:
            cfg["models"][model][key] = value
            console.print(
                f"[green]✓Zaten ayarlandı[/green] [cyan]{model}[/cyan].{key} = {value}"
            )
        _save(cfg)
        console.print(f"[dim]şuraya kaydedildi:{CONFIG_FILE}[/dim]")
    else:
        #Genel yapılandırma, yazma.env
        env_path = Path(".env")
        env_vars: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line:
                    k2, v2 = line.split("=", 1)
                    env_vars[k2.strip()] = v2.strip()
        env_vars[key] = value
        env_path.write_text("\n".join(f"{k}={v}" for k, v in env_vars.items()) + "\n")
        console.print(
            f"[green]✓Ayarla (genel)[/green] [cyan]{key}[/cyan] = {_mask_secret(value)}"
        )
        console.print("[dim]Gerçek entegrasyon sırasında içe aktarılması gerekiyor.envbelge[/dim]")


@app.command()
def models():
    """Yapılandırılmış modelleri listeleme"""
    CONFIG_DIR = Path.home() / ".omc"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def _load() -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    cfg = _load()
    models = cfg.get("models", {})
    if not models:
        console.print("[dim]Henüz hiçbir model yapılandırılmadı[/dim]")
        console.print(
            "\n[bold]Hızlı başlangıç:[/bold] omc config set -m kimi -k api_key -v <your-key>"
        )
    else:
        console.print(f"[bold]yapılandırılmış{len(models)}modeller:[/bold]\n")
        for name, opts in models.items():
            api_key = opts.get("api_key", "")
            base = opts.get("base_url", "")
            temp = opts.get("temperature", None)
            console.print(f"  [cyan]{name}[/cyan]")
            if api_key:
                console.print(f"    api_key: {_mask_secret(api_key)}")
            if base:
                console.print(f"    base_url: {base}")
            if temp is not None:
                console.print(f"    temperature: {temp}")
            console.print()
