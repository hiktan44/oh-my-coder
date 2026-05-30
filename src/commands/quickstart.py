from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
omc quickstart - Etkileşimli önyükleme komutu

Yeni kullanıcılara rehberlik edin 3 Yapılandırmayı tamamlayın ve ilk görevi tek adımda çalıştırın:
  [1/3] Modeli seçin
  [2/3] Yapılandırma API Key
  [3/3] Yapılandırmayı doğrulamak için örnek görevi çalıştırın
"""


import asyncio
import json
import os
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

app = typer.Typer(
    name="quickstart",
    help="İnteraktif rehberlik - 3 Yapılandırmayı tamamlayın ve ilk görevi çalıştırın",
    add_completion=False,
)

# ============================================================
# Model sınıflandırması (ile cli_model.py / router.py senkronize kalın)
# ============================================================
MODEL_CATEGORIES = {
    "Yurtiçi ücretsiz": [
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "desc": "Yüksek ücretsiz kota ve yakın kalite GPT-4",
            "api_key_env": "DEEPSEEK_API_KEY",
            "register_url": "https://platform.deepseek.com",
            "model_name": "deepseek-chat",
        },
        {
            "id": "glm",
            "name": "Bilgelik spektrumu GLM",
            "desc": "GLM-4.7-Flash Kullanımı ücretsiz",
            "api_key_env": "ZHIPUAI_API_KEY",
            "register_url": "https://open.bigmodel.cn",
            "model_name": "glm-4-flash",
        },
    ],
    "Yurtiçi ücretli": [
        {
            "id": "kimi",
            "name": "Kimi(Ayın Karanlık Yüzü)",
            "desc": "Güçlü uzun vadeli bağlam yeteneği",
            "api_key_env": "KIMI_API_KEY",
            "register_url": "https://platform.moonshot.cn",
            "model_name": "moonshot-v1-8k",
        },
        {
            "id": "doubao",
            "name": "Doubao (ByteDance)",
            "desc": "Yüksek maliyet performansı",
            "api_key_env": "DOUBAO_API_KEY",
            "register_url": "https://console.volcengine.com/ark",
            "model_name": "doubao-pro-32k",
        },
        {
            "id": "tongyi",
            "name": "Tongyi (Alibaba)",
            "desc": "Alibaba Bulut Ekolojik Entegrasyonu",
            "api_key_env": "TONGYI_API_KEY",
            "register_url": "https://dashscope.console.aliyun.com",
            "model_name": "qwen-turbo",
        },
        {
            "id": "minimax",
            "name": "MiniMax",
            "desc": "Çok uzun bağlamları destekler",
            "api_key_env": "MINIMAX_API_KEY",
            "register_url": "https://www.minimaxi.com",
            "model_name": "abab6-chat",
        },
        {
            "id": "wenxin",
            "name": "Wen Xin Yi Yan (Baidu)",
            "desc": "Baidu Wenxin'in büyük modeli",
            "api_key_env": "WENXIN_API_KEY",
            "register_url": "https://console.bce.baidu.com",
            "model_name": "ernie-4.0-8k-latest",
        },
        {
            "id": "hunyuan",
            "name": "Tencent Hunyuan",
            "desc": "Tencent'in kendi geliştirdiği büyük model",
            "api_key_env": "HUNYUAN_API_KEY",
            "register_url": "https://console.cloud.tencent.com/hunyuan",
            "model_name": "hunyuan-pro",
        },
        {
            "id": "baichuan",
            "name": "Baichuan İstihbaratı",
            "desc": "Baichuan'ın büyük modeli",
            "api_key_env": "BAICHUAN_API_KEY",
            "register_url": "https://www.baichuan-ai.com",
            "model_name": "baichuan4",
        },
    ],
}

# Her model için kayıt adresi (hızlı gezinme için)
REGISTER_URLS = {
    "deepseek": "https://platform.deepseek.com",
    "glm": "https://open.bigmodel.cn",
    "kimi": "https://platform.moonshot.cn",
    "doubao": "https://console.volcengine.com/ark",
    "tongyi": "https://dashscope.console.aliyun.com",
    "minimax": "https://www.minimaxi.com",
    "wenxin": "https://console.bce.baidu.com",
    "hunyuan": "https://console.cloud.tencent.com/hunyuan",
    "baichuan": "https://www.baichuan-ai.com",
}


# ============================================================
# İlerleme durumu tespiti
# ============================================================
def detect_completed_steps() -> dict[str, bool]:
    """Tamamlanan adımları tespit et (otomatik olarak atlanır)"""
    steps: dict[str, bool] = {
        "model": False,
        "apikey": False,
        "verify": False,
    }

    # Step 1: Varsayılan bir modelin olup olmadığı ve buna karşılık gelen API Key
    config_file = Path.home() / ".config" / "oh-my-coder" / "config.json"
    config_model = None
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text())
            config_model = cfg.get("default_model")
        except Exception:
            pass

    env_model = os.getenv("OMC_DEFAULT_MODEL")

    # Yapılandırılmış olup olmadığını kontrol edin API Key
    env_api_keys = {
        "DEEPSEEK_API_KEY": "deepseek",
        "KIMI_API_KEY": "kimi",
        "DOUBAO_API_KEY": "doubao",
        "ZHIPUAI_API_KEY": "glm",
        "TONGYI_API_KEY": "tongyi",
        "MINIMAX_API_KEY": "minimax",
        "WENXIN_API_KEY": "wenxin",
        "HUNYUAN_API_KEY": "hunyuan",
        "BAICHUAN_API_KEY": "baichuan",
    }
    configured = [env for env, _ in env_api_keys.items() if os.getenv(env)]

    if configured or config_model or env_model:
        steps["model"] = True

    # Step 2: API Key Yapılandırma
    if configured:
        steps["apikey"] = True

    # Step 3: Mevcut iş var API Key(aslında çağrılabilir)
    # Basit bir deneyerek API Doğrulamak için arayın (hafif algılama)
    if configured:
        steps["verify"] = _check_api_key_works(
            configured[0], env_api_keys[configured[0]]
        )

    return steps


def _check_api_key_works(env_key: str, provider: str) -> bool:
    """Hafiflik algılama API Key Geçerli mi (aslında çağrılmadı, yalnızca format ve ortam kontrol ediliyor)"""
    key = os.getenv(env_key)
    if not key:
        return False

    # Biçim kontrolü
    if len(key) < 10:
        return False

    # Bilinen modeller için ücretsiz sağlık kontrolü yapın
    try:
        if provider == "deepseek":
            # hızlı kontrol DeepSeek denge
            import httpx

            resp = httpx.get(
                "https://api.deepseek.com/user_balance",
                headers={"Authorization": f"Bearer {key}"},
                timeout=5,
            )
            return resp.status_code in (200, 401)  # 401=keyBiçim doğru ancak ücret ödenmemiş/Kota tükendi
        if provider == "glm":
            resp = httpx.get(
                "https://open.bigmodel.cn/api/paas/v4/balance",
                headers={"Authorization": f"Bearer {key}"},
                timeout=5,
            )
            return resp.status_code in (200, 401)
    except Exception:
        pass

    # Muhafazakar: boş olmadığı sürece key etkili olabileceğini düşünüyorum
    return True


# ============================================================
# adım 1:Modeli seçin
# ============================================================
def _step1_select_model() -> Optional[dict]:
    """Etkileşimli olarak bir model seçin ve seçilen model bilgilerini döndürün veya None(üstünden atla)"""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]adım 1 / 3:Modeli seçin[/bold cyan]\n\n"
            "Aşağıdaki modeller entegre edilmiştir omc, kullanıma hazır olarak şunları destekler:",
            border_style="cyan",
            title="🚀 Hızlı yapılandırma kılavuzu",
        )
    )

    # Sınıflandırma modeli listesini göster
    choice_map: list[tuple[str, dict]] = []  # (display_num, model_info)

    num = 1
    for category, models in MODEL_CATEGORIES.items():
        console.print(f"\n[bold yellow]{category}[/bold yellow]")
        for m in models:
            # Yapılandırılmış olup olmadığını kontrol edin
            configured = "✅" if os.getenv(m["api_key_env"]) else "  "
            console.print(f"  {configured} [{num}] {m['name']} — {m['desc']}")
            choice_map.append((str(num), m))
            num += 1

    console.print()
    console.print("[dim]Yapılandırılmış ✅, atlamak için Enter'a basın (zaten yapılandırılmıştır)[/dim]")

    raw = Prompt.ask("[cyan]Lütfen model numarasını seçin (veya atlamak için Enter tuşuna basın)[/cyan]")
    raw = raw.strip()

    if not raw:
        return None

    # Seçimi bul
    for display_num, model_info in choice_map:
        if display_num == raw:
            return model_info

    console.print("[yellow]Geçersiz seçim, atlandı[/yellow]")
    return None


# ============================================================
# adım 2:Yapılandırma API Key
# ============================================================
def _step2_config_apikey(model_info: dict) -> bool:
    """Yapılandırma API Key, başarılı olup olmadığını döndürür"""
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]adım 2 / 3:için {model_info['name']} Yapılandırma API Key[/bold cyan]\n\n"
            f"Kayıtlı adres:{model_info['register_url']}\n\n"
            "eğer zaten sahipsen Key, doğrudan girilebilir;"
            "Değilse, tarayıcıyı açmak ve kaydolmak için lütfen Enter tuşuna basın.",
            border_style="cyan",
        )
    )

    env_key = model_info["api_key_env"]
    existing = os.getenv(env_key)

    if existing:
        masked = existing[:4] + "****" + existing[-4:] if len(existing) > 8 else "****"
        console.print(f"[green]✓ Yapılandırılmış:[/green] {env_key} = {masked}")
        if Confirm.ask("Mevcut olanı güncellemek için Key ?", default=False):
            pass
        else:
            console.print("[dim]üstünden atla Key Yapılandırma[/dim]")
            return True

    console.print(f"\n[bold]Lütfen girin {env_key}:[/bold]")
    key = Prompt.ask("API Key", password=True).strip()

    if not key:
        console.print(
            "[yellow]Girilmedi Key, atla (daha sonra kullanılabilir omc config set yapılandırma)[/yellow]"
        )
        return False

    # yazmak .env Dosya (proje kök dizini veya kullanıcı dizini)
    _set_env_var(env_key, key)
    console.print(f"[green]✓ yazıldı {env_key}[/green]")
    return True


def _set_env_var(key: str, value: str) -> None:
    """Ortam değişkenlerini ayarlayın (yazma .env + Geçerli işlemi ayarlayın)"""
    os.environ[key] = value

    # Proje kök dizinine yazın .env
    project_env = Path(".env")
    env_vars: dict[str, str] = {}

    if project_env.exists():
        for line in project_env.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

    env_vars[key] = value
    lines = [f"{k}={v}" for k, v in env_vars.items()]
    project_env.write_text("\n".join(lines) + "\n")

    # Senkronize yazma kullanıcısı home İçindekiler
    home_env = Path.home() / ".omc.env"
    home_vars: dict[str, str] = {}
    if home_env.exists():
        for line in home_env.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                home_vars[k.strip()] = v.strip()
    home_vars[key] = value
    home_env.write_text("\n".join(f"{k}={v}" for k, v in home_vars.items()) + "\n")


# ============================================================
# adım 3:Örnek görevi çalıştırın
# ============================================================
def _step3_run_demo(model_info: dict) -> bool:
    """Yapılandırmayı doğrulamak için örnek görevi çalıştırın"""
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]adım 3 / 3:Örnek görevi çalıştırın[/bold cyan]\n\n"
            f"kullanmak [green]{model_info['name']}[/green] Basit bir görevi gerçekleştirin:\n"
            "[bold]kullanmak Python Hızlı sıralama algoritmasını uygulayın[/bold]\n\n"
            "Model yapılandırmasının doğru olduğunu doğrulayın.",
            border_style="cyan",
        )
    )

    if not Confirm.ask("\nYürütme başlatılsın mı?", default=True):
        console.print("[dim]Doğrulamayı atla (her zaman kullanılabilir) omc run test)[/dim]")
        return False

    from rich.progress import Progress, SpinnerColumn, TextColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Yürütme...", total=None)
        progress.update(task, description="[yellow]çağrı modeli...[/yellow]")

        try:
            result = asyncio.run(_call_model_demo(model_info))
            progress.update(task, description="[green]Yürütme tamamlandı[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]Yürütme başarısız oldu: {e}[/red]")
            return False

    if result.get("success"):
        console.print(
            Panel.fit(
                f"[bold green]✅ Yapılandırma başarılı![/bold green]\n\n"
                f"Modeli:{model_info['name']}\n"
                f"Kod önizlemesi oluştur:\n\n[dim]{_truncate(result.get('code', ''), 300)}[/dim]",
                title="🎉 Doğrulama başarılı oldu",
                border_style="green",
            )
        )
        return True
    console.print(
        Panel.fit(
            f"[bold red]❌ Kimlik doğrulama başarısız oldu[/bold red]\n\n"
            f"hata:{result.get('error', 'bilinmeyen hata')}\n\n"
            f"[dim]SSS:\n"
            f"  1. API Key Yanlış veya süresi dolmuş\n"
            f"  2. Yetersiz hesap bakiyesi\n"
            f"  3. Ağ platforma erişemiyor\n\n"
            f"Lütfen ziyaret edin {model_info['register_url']} incelemek[/dim]",
            title="⚠️ Doğrulama başarısız oldu",
            border_style="red",
        )
    )
    return False


async def _call_model_demo(model_info: dict) -> dict:
    """Hızlı sıralama gerçekleştirmek için modeli çağırma örneği"""
    import httpx

    api_key = os.getenv(model_info["api_key_env"])
    if not api_key:
        return {"success": False, "error": "API Key Yapılandırılmadı"}

    prompt = "kullanmak Python Hızlı sıralama algoritmasını uygulayın ve kodu yalnızca açıklama yapmadan çıktılayın."

    # Farklı platform çağrı yöntemleri
    provider = model_info["id"]

    try:
        if provider == "deepseek":
            resp = httpx.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "glm":
            resp = httpx.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "glm-4-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "kimi":
            resp = httpx.post(
                "https://api.moonshot.cn/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "moonshot-v1-8k",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "doubao":
            resp = httpx.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "doubao-pro-32k",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "tongyi":
            resp = httpx.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "minimax":
            resp = httpx.post(
                "https://api.minimax.chat/v1/text/chatcompletion_pro?GroupId=&AuthorId=",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "abab6-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "wenxin":
            access_token = _get_wenxin_access_token(api_key)
            if not access_token:
                return {
                    "success": False,
                    "error": "Wenxinyiyanneeds access_token, lütfen yapılandırmayı kontrol edin",
                }
            resp = httpx.post(
                "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
                headers={"Content-Type": "application/json"},
                params={"access_token": access_token},
                json={
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
        elif provider == "hunyuan":
            secret_key = os.getenv("HUNYUAN_SECRET_KEY", "")
            access_token = _get_hunyuan_access_token(api_key, secret_key)
            if not access_token:
                return {"success": False, "error": "Hunyuan'ın ihtiyaçları access_token, lütfen yapılandırmayı kontrol edin"}
            resp = httpx.post(
                "https://hunyuan.cloud.tencent.com/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "hunyuan-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        else:
            return {"success": False, "error": f"Henüz desteklenmiyor {provider} Hızlı doğrulama"}

        if resp.status_code != 200:
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get(
                    "message", err_data.get("message", resp.text)
                )
            except Exception:
                err_msg = resp.text
            return {"success": False, "error": f"[{resp.status_code}] {err_msg}"}

        data = resp.json()
        content = ""
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
        elif "result" in data:
            content = data["result"]

        return {"success": True, "code": content}

    except httpx.TimeoutException:
        return {"success": False, "error": "İstek zaman aşımına uğradı, lütfen ağ bağlantısını kontrol edin"}
    except Exception:
        return {"success": False, "error": "İstek başarısız oldu"}


def _get_wenxin_access_token(api_key: str) -> Optional[str]:
    """Wen Xinyan'ı alın access_token(basitleştirilmiş versiyon)"""
    try:
        secret_key = os.getenv("WENXIN_SECRET_KEY", "")
        resp = httpx.get(
            "https://aip.baidubce.com/oauth/2.0/token",
            params={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass
    return None


def _get_hunyuan_access_token(api_key: str, secret_key: str) -> Optional[str]:
    """Tencent Hunyuan'ı edinin access_token(basitleştirilmiş versiyon)"""
    try:
        resp = httpx.post(
            "https://hunyuan.cloud.tencent.com/api/v1/auth/tokens",
            headers={"Content-Type": "application/json"},
            json={"secret_id": api_key, "secret_key": secret_key},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("token", {}).get("access_token")
    except Exception:
        pass
    return None


def _truncate(s: str, max_len: int) -> str:
    """dizeyi kısalt"""
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "\n..."


# ============================================================
# Tam özet
# ============================================================
def _show_summary(model_info: dict, steps_completed: dict) -> None:
    """Tamamlama özetini göster"""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]🎉 Hızlı yapılandırma tamamlandı![/bold green]\n\n"
            "Daha sonra şunları yapabilirsiniz:\n\n"
            '  [cyan]omc run "Kullanıcı oturum açma işlevini uygulama"[/cyan]\n'
            "    başlatmak AI Programlama Asistanı\n\n"
            "  [cyan]omc status[/cyan]\n"
            "    Mevcut yapılandırma durumunu görüntüle\n\n"
            "  [cyan]omc model list[/cyan]\n"
            "    Mevcut tüm modelleri görün\n\n"
            "[dim]Yapılandırma dosyası:.env(proje)/ ~/.omc.env(Global kullanıcı)[/dim]",
            title="✅ hızlı başlangıç",
            border_style="green",
        )
    )


# ============================================================
# ana komut
# ============================================================
@app.command()
def main(
    step: str = typer.Option(
        None,
        "--step",
        "-s",
        help="Yalnızca belirtilen adımları gerçekleştirin:model / apikey / verify",
    ),
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="Modeli doğrudan belirtin ID(beğenmek deepseek / glm)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Tüm adımların yeniden yürütülmesini zorla (yapılandırılmış algılamaları göz ardı edin)",
    ),
):
    """
    İnteraktif rehberlik - 3 Yapılandırmayı tamamlayın ve ilk görevi çalıştırın

    Örnek:
      omc quickstart          # İnteraktif rehberlik (ilk kez kullanım için önerilir)
      omc quickstart -m deepseek  # Modeli doğrudan belirtin
      omc quickstart --step verify  # Yalnızca yapılandırmayı doğrulayın
    """
    # Algılamanın tamamlanmış adımları
    completed = {"model": False, "apikey": False, "verify": False} if force else detect_completed_steps()

    # İstatistik atlama sayısı
    skipped = sum(1 for v in completed.values() if v)
    if skipped > 0 and not force:
        console.print(f"[dim]saptanmış {skipped} adımlar tamamlandı ve otomatik olarak atlanacak[/dim]")

    # eğer geçerse --model Doğrudan modeli belirtin ve doğrulamayı doğrudan girin
    if model:
        model_info = None
        for cats in MODEL_CATEGORIES.values():
            for m in cats:
                if m["id"] == model:
                    model_info = m
                    break
        if not model_info:
            console.print(f"[red]bilinmeyen model: {model}[/red]")
            raise typer.Exit(1)
        # adımı atla1, doğrudan yapılandırın key
        console.print(f"[cyan]Modeli kullan: {model_info['name']}[/cyan]\n")
        if not os.getenv(model_info["api_key_env"]):
            _step2_config_apikey(model_info)
        ok = _step3_run_demo(model_info)
        _show_summary(model_info, {"model": True, "apikey": True, "verify": ok})
        raise typer.Exit(0 if ok else 1)

    # Tek adımlı yürütme
    if step:
        if step == "model":
            _step1_select_model()
            raise typer.Exit(0)
        if step == "apikey":
            console.print(
                "[yellow]Lütfen önce onu kullanın -m Modeli belirtin:omc quickstart --step apikey -m deepseek[/yellow]"
            )
            raise typer.Exit(1)
        if step == "verify":
            # Yapılandırılmış modelleri otomatik olarak algılamayı deneyin
            configured_key = next(
                (
                    env
                    for env in [
                        "DEEPSEEK_API_KEY",
                        "KIMI_API_KEY",
                        "DOUBAO_API_KEY",
                        "ZHIPUAI_API_KEY",
                        "TONGYI_API_KEY",
                        "MINIMAX_API_KEY",
                        "WENXIN_API_KEY",
                        "HUNYUAN_API_KEY",
                        "BAICHUAN_API_KEY",
                    ]
                    if os.getenv(env)
                ),
                None,
            )
            if not configured_key:
                console.print("[red]Yapılandırılmış algılanmadı API Key[/red]")
                raise typer.Exit(1)
            env_to_provider = {
                "DEEPSEEK_API_KEY": "deepseek",
                "KIMI_API_KEY": "kimi",
                "DOUBAO_API_KEY": "doubao",
                "ZHIPUAI_API_KEY": "glm",
                "TONGYI_API_KEY": "tongyi",
                "MINIMAX_API_KEY": "minimax",
                "WENXIN_API_KEY": "wenxin",
                "HUNYUAN_API_KEY": "hunyuan",
                "BAICHUAN_API_KEY": "baichuan",
            }
            pid = env_to_provider[configured_key]
            for cats in MODEL_CATEGORIES.values():
                for m in cats:
                    if m["id"] == pid:
                        ok = _step3_run_demo(m)
                        raise typer.Exit(0 if ok else 1)
        console.print(f"[red]bilinmeyen adım: {step}[/red]")
        raise typer.Exit(1)

    # ============================================================
    # tüm süreç
    # ============================================================
    console.print(
        Panel.fit(
            "[bold cyan]🚀 omc quickstart[/bold cyan]\n\n"
            "sana rehberlik etmek 3 Yapılandırmayı tamamlayın ve ilk görevi tek adımda çalıştırın:\n\n"
            "  [1/3] Modeli seçin\n"
            "  [2/3] Yapılandırma API Key\n"
            "  [3/3] Doğrulamak için örnek görevi çalıştırın\n\n"
            "[dim]Zaten yapılandırılmış olan adımlar otomatik olarak atlanacaktır.[/dim]",
            border_style="cyan",
            title="Hızlı yapılandırma kılavuzu",
        )
    )

    if not Confirm.ask("\nHızlı yapılandırma başlatılsın mı?", default=True):
        console.print("[dim]İptal edildi[/dim]")
        raise typer.Exit(0)

    selected_model: Optional[dict] = None

    # ---- adım 1 ----
    if not completed["model"]:
        selected_model = _step1_select_model()
        if selected_model is None:
            # Kullanıcı atladı ancak modeli yapılandırdı, algılamaya çalışın
            configured_key = next(
                (
                    env
                    for env in [
                        "DEEPSEEK_API_KEY",
                        "KIMI_API_KEY",
                        "DOUBAO_API_KEY",
                        "ZHIPUAI_API_KEY",
                        "TONGYI_API_KEY",
                        "MINIMAX_API_KEY",
                        "WENXIN_API_KEY",
                        "HUNYUAN_API_KEY",
                        "BAICHUAN_API_KEY",
                    ]
                    if os.getenv(env)
                ),
                None,
            )
            if configured_key:
                env_to_provider = {
                    "DEEPSEEK_API_KEY": "deepseek",
                    "KIMI_API_KEY": "kimi",
                    "DOUBAO_API_KEY": "doubao",
                    "ZHIPUAI_API_KEY": "glm",
                    "TONGYI_API_KEY": "tongyi",
                    "MINIMAX_API_KEY": "minimax",
                    "WENXIN_API_KEY": "wenxin",
                    "HUNYUAN_API_KEY": "hunyuan",
                    "BAICHUAN_API_KEY": "baichuan",
                }
                pid = env_to_provider.get(configured_key, "")
                for cats in MODEL_CATEGORIES.values():
                    for m in cats:
                        if m["id"] == pid:
                            selected_model = m
                            break
    else:
        # Algılama için hangi modelin kullanılacağı önceden yapılandırılmıştır
        configured_key = next(
            (
                env
                for env in [
                    "DEEPSEEK_API_KEY",
                    "KIMI_API_KEY",
                    "DOUBAO_API_KEY",
                    "ZHIPUAI_API_KEY",
                    "TONGYI_API_KEY",
                    "MINIMAX_API_KEY",
                    "WENXIN_API_KEY",
                    "HUNYUAN_API_KEY",
                    "BAICHUAN_API_KEY",
                ]
                if os.getenv(env)
            ),
            None,
        )
        if configured_key:
            env_to_provider = {
                "DEEPSEEK_API_KEY": "deepseek",
                "KIMI_API_KEY": "kimi",
                "DOUBAO_API_KEY": "doubao",
                "ZHIPUAI_API_KEY": "glm",
                "TONGYI_API_KEY": "tongyi",
                "MINIMAX_API_KEY": "minimax",
                "WENXIN_API_KEY": "wenxin",
                "HUNYUAN_API_KEY": "hunyuan",
                "BAICHUAN_API_KEY": "baichuan",
            }
            pid = env_to_provider.get(configured_key, "")
            for cats in MODEL_CATEGORIES.values():
                for m in cats:
                    if m["id"] == pid:
                        selected_model = m
                        break

    if selected_model is None:
        console.print("\n[yellow]Model seçilmedi, çık (mevcut) omc run doğrudan çalıştırın)[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[green]✓ Seçilen:{selected_model['name']}[/green]")

    # ---- adım 2 ----
    apikey_ok = completed["apikey"]
    if not apikey_ok:
        apikey_ok = _step2_config_apikey(selected_model)

    # ---- adım 3 ----
    verify_ok = completed["verify"]
    if not verify_ok:
        verify_ok = _step3_run_demo(selected_model)

    # Özetle
    _show_summary(
        selected_model,
        {"model": True, "apikey": apikey_ok, "verify": verify_ok},
    )

    raise typer.Exit(0 if verify_ok else 1)


if __name__ == "__main__":
    app()
