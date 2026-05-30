from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.agents.cross_validation import CrossValidationLayer
from src.core.orchestrator import Orchestrator
from src.core.router import ModelRouter, RouterConfig
from src.wiki import WikiGenerator

console = Console()

# ============================================================
#bağımsız yaratTyper app
# ============================================================
app = typer.Typer(
    name="run",
    help="Görev yürütmeyle ilgili komutlar",
    add_completion=False,
)

# ============================================================
# run— Görevin yürütülmesi
# ============================================================


@app.command()
def run(
    task: str = typer.Argument(..., help="Görev açıklaması"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    model: str = typer.Option("deepseek", "--model", "-m", help="Model seçimi"),
    workflow: str = typer.Option(
        "build",
        "--workflow",
        "-w",
        help=(
            "İş akışı adı:build(gelişim)/ review(gözden geçirmek)/ debug(hata ayıklama)/ test(test)"
            " / autopilot(otomatik yönlendirme)/ pair(çift programlama)/ refactor(yeniden düzenleme)"
            " / doc(Belge oluşturma)/ sequential(Sıralı yürütme düzenlemesi)"
        ),
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Yalnızca yürütme planının ön izlemesini yapar, gerçekte çalıştırmaz"),
    notify: bool = typer.Option(
        False, "--notify", "-n", help="Tamamlandığında bildirim gönder (masaüstü+DingTalk)"
    ),
    no_checkpoint: bool = typer.Option(
        False, "--no-checkpoint", help="Otomatik anlık görüntüyü atla (devam ettirilebilir yükleme)"
    ),
    simple: bool = typer.Option(
        False, "--simple", "-s", help="Basit mod: iş akışına geçmeden doğrudan yürütün (dosya oluşturma gibi hızlı görevler için uygundur)"
    ),
    cross_validate: bool = typer.Option(
        False,
        "--cross-validate",
        help="İş akışı sona erdikten sonra yürütülürAgentÇapraz doğrulama (çıktıya bağımsız bir perspektiften bakmak)",
    ),
    use_sourcegraph: bool = typer.Option(
        False,
        "--use-sourcegraph",
        help="Analyst AgentkullanmakSourcegraphGelişmiş analiz için genel kod tabanlarını arayın",
    ),
):
    """Programlama görevlerini gerçekleştirin"""
    #ön kontrol
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold green]Oh My Coder[/bold green]\n"
            f"Görev: {task}\n"
            f"proje: {project_path}\n"
            f"İş akışı: {workflow}",
            title="🚀başlatmak",
        )
    )

    # Dry-runMod: Yalnızca planları göster
    if dry_run:
        console.print(
            Panel.fit(
                "[yellow]🔍 Dry-runMod—yalnızca yürütme planını gösterir[/yellow]\n\n"
                "[bold]İş akışı:[/bold] "
                + workflow
                + "\n[bold]Görev:[/bold] "
                + task
                + "\n[bold]proje:[/bold] "
                + str(project_path.absolute())
                + "\n\n[dim]Lütfen gerçek uygulamayı kaldırın--dry-runparametre[/dim]",
                title="📋Model yapılandırmasını topluluk dizininde paylaşın",
                border_style="yellow",
            )
        )
        raise typer.Exit(0)

    #Yönlendiriciyi ve orkestratörü başlatın
    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    # ----Basit mod: iş akışına geçmeden yürütmek için doğrudan model oluşturma komutunu çağırın.----
    if simple:
        _run_simple_task(router, task)
        raise typer.Exit(0)

    orchestrator = Orchestrator(router, state_dir=project_path / ".omc" / "state")

    #İş akışını yürütün
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        #İlerleme geri araması: o anda yürütülen işlemi görüntülerAgent
        main_task = progress.add_task("🚀Başlangıç...", total=None)

        def _progress_callback(step_name: str, status: str):
            """değişiklik zamanı"""
            nonlocal main_task
            if status == "started":
                progress.update(main_task, description=f"🔄Yürütme: {step_name}")
            elif status == "completed":
                progress.update(main_task, description=f"✅Tamamlanmış: {step_name}")
            elif status == "failed":
                progress.update(main_task, description=f"❌hata: {step_name}")

        try:
            result = asyncio.run(
                orchestrator.execute_workflow(
                    workflow,
                    {
                        "project_path": str(project_path.absolute()),
                        "task": task,
                        "use_sourcegraph": use_sourcegraph,
                    },
                    skip_checkpoint=no_checkpoint,
                    progress_callback=_progress_callback,
                )
            )

            #Sonuçları göster
            _display_result(result)

            # ----Çapraz doğrulama: iş akışı çıktısına bağımsız bir bakış----
            if cross_validate:
                cv_progress = progress.add_task("🔍çapraz doğrulama...", total=None)
                try:
                    cv_layer = CrossValidationLayer(
                        model_router=router,
                        state_dir=project_path / ".omc" / "state",
                    )
                    cv_result = asyncio.run(
                        cv_layer.validate_workflow(result, workflow)
                    )
                    progress.remove_task(cv_progress)

                    #Doğrulama özetini göster
                    _display_cross_validation_result(cv_result)

                    #Doğrulama sıfır olmayan bir çıkış koduyla başarısız oluyor.
                    if cv_result.status.value in ("fail", "need_fix"):
                        console.print(
                            Panel.fit(
                                "[yellow]⚠️Çapraz doğrulamada bir sorun bulundu; sorunu düzeltip tekrar denemeniz önerilir.[/yellow]\n"
                                "[dim]Doğrulama raporu şuraya kaydedildi:.omc/state/cross_validation/[/dim]",
                                title="⚠️Doğrulama hatırlatıcısı",
                                border_style="yellow",
                            )
                        )
                except Exception as cv_err:
                    progress.remove_task(cv_progress)
                    console.print(
                        f"[yellow]⚠️Çapraz doğrulama hatası (ana işlemi etkilemez): {cv_err}[/yellow]"
                    )

            #Bildirim gönder
            if notify:
                from src.utils.notify import (
                    notify_workflow_complete,
                    notify_workflow_complete_dingtalk,
                )

                status = "completed" if result.success else "failed"
                steps = len(result.steps) if hasattr(result, "steps") else 1
                exec_time = getattr(result, "execution_time", 0.0)

                #Masaüstü bildirimleri
                notify_workflow_complete(workflow, status, steps, exec_time)
                #DingTalk bildirimleri
                notify_workflow_complete_dingtalk(
                    None, workflow, status, steps, exec_time, str(project_path)
                )

        except Exception as e:
            _print_fatal(
                f"İş akışı yürütme hatası: {e}",
                hint="Aşağıdaki yöntemleri deneyebilirsiniz:\n"
                "  1.Ağ bağlantısını kontrol edin\n"
                "  2.onaylamakAPI Keyverimli:omc status\n"
                "  3.Ayrıntılı günlüğü görüntüle",
            )
            raise typer.Exit(1)


# ============================================================
# explore— Keşif modu
# ============================================================


@app.command()
def explore(
    project_path: Path = typer.Argument(".", help="Proje yolu"),
):
    """Kod tabanını keşfedin"""
    if not _check_env():
        raise typer.Exit(1)

    console.print(f"[bold]🔍Projeleri keşfedin: {project_path}[/bold]")

    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    orchestrator = Orchestrator(router)

    try:
        result = asyncio.run(
            orchestrator.execute_single_agent(
                "explore",
                {
                    "project_path": str(project_path.absolute()),
                    "task": "Kod tabanını keşfedin ve bir proje haritası oluşturun",
                },
            )
        )

        if result.result:
            console.print(Panel(result.result, title="proje haritası"))
        else:
            _print_fatal(f"Keşif başarısız oldu: {result.error}")

    except Exception as e:
        _print_fatal(f"Keşif hatası: {e}", hint="Proje yolunun var olduğunu ve okunabilir olduğunu doğrulayın")
        raise typer.Exit(1)


# ============================================================
# wiki — Wikioluşturmak
# ============================================================


@app.command()
def wiki(
    project_path: Path = typer.Argument(".", help="Proje yolu"),
    output: Path = typer.Option(
        None, "--output", "-o", help="Çıkış dosyası yolu, varsayılanREPO_WIKI.md"
    ),
):
    """Proje oluşturWikibelge"""
    project_path = project_path.resolve()

    if not project_path.exists():
        _print_fatal(f"Proje yolu mevcut değil: {project_path}")
        raise typer.Exit(1)

    #Çıkış yolunu belirleyin
    if output is None:
        output = project_path / "REPO_WIKI.md"

    console.print(f"[bold]📝oluşturmakWiki: {project_path}[/bold]")

    try:
        #itibarenpyproject.tomlVeya proje adını almak için dizin adı
        project_name = _detect_project_name(project_path)

        #oluşturmakWiki
        generator = WikiGenerator(
            project_name=project_name,
            project_path=project_path,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("ayrıştırma kodu...", total=None)
            generator.generate(output)

        console.print(
            Panel.fit(
                f"[green]✓ WikiOluşturuldu[/green]\n\n"
                f"belge: [cyan]{output}[/cyan]\n\n"
                f"[dim]kullanmak`omc wiki`Yenile[/dim]",
                title="📚 Wiki",
            )
        )

    except Exception as e:
        _print_fatal(f"WikiDerleme başarısız oldu: {e}")
        raise typer.Exit(1)


# ============================================================
#Yardımcı işlevi
# ============================================================


def _detect_project_name(project_path: Path) -> str:
    """Test öğesi adı"""
    #baştan başlamayı denepyproject.tomlOkumak
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            if "project" in data and "name" in data["project"]:
                return data["project"]["name"]
        except Exception:
            pass

    #baştan başlamayı denesetup.pyOkumak
    setup_py = project_path / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text()
            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
        except Exception:
            pass

    #Başarı modelinin dahil edilmesi durumunda da tasarruf sağlar
    return project_path.name


def _load_config() -> dict:
    """itibaren~/.omc/config.jsonYapılandırmayı oku"""
    config_path = Path.home() / ".omc" / "config.json"
    if not config_path.exists():
        return {}
    import json
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _resolve_default_model(config: dict) -> str:
    """Varsayılan modeli ayrıştırma: ortam değişkenleri> config.json >İlki varapi_keymodeli> deepseek"""
    env_model = os.getenv("OMC_DEFAULT_MODEL") or os.getenv("DEFAULT_MODEL")
    if env_model:
        return env_model
    cfg_model = config.get("defaults", {}).get("model") or config.get("default_model")
    if cfg_model:
        return cfg_model
    models = config.get("models", {})
    if isinstance(models, dict):
        for name, mcfg in models.items():
            if isinstance(mcfg, dict) and mcfg.get("api_key"):
                return name
    return "deepseek"


def _get_api_key(config: dict, model: str) -> str:
    """İlgili modeli alınAPI Key:config.json >ortam değişkenleri"""
    # 1.itibarenconfig.jsonile ilgilimodelsOku
    models = config.get("models", {})
    if isinstance(models, dict):
        for name, mcfg in models.items():
            if isinstance(mcfg, dict) and mcfg.get("api_key") and name in (model, model.replace("-", "_"), model.replace("_", "-")):
                return mcfg["api_key"]
    # 2.Ortam değişkeni geri dönüşü
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "kimi": "KIMI_API_KEY",
        "doubao": "DOUBAO_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "glm": "ZHIPUAI_API_KEY",
        "tongyi": "DASHSCOPE_API_KEY",
        "wenxin": "ERNIE_API_KEY",
        "hunyuan": "HUNYUAN_API_KEY",
    }
    return os.getenv(key_map.get(model, f"{model.upper()}_API_KEY"), "")


def _run_simple_task(router: ModelRouter, task: str) -> None:
    """
Basit mod: iş akışına geçmeden, oluşturmak ve yürütmek için doğrudan modeli çağırınshellEmir.
Dosya oluşturma ve komut çalıştırma gibi hızlı görevler için uygundur.
    """
    import json
    import subprocess

    from src.models.base import Message

    console.print(Panel.fit(
        f"[cyan]⚡Basit mod - doğrudan yürütme[/cyan]\nGörev: {task}",
        title="🚀başlatmak",
        border_style="cyan",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("🤔Analiz görevleri...", total=None)

        try:
            response = asyncio.run(
                router.route_and_call(
                    task_type="simple",
                    messages=[
                        Message(
                            role="system",
                            content=(
                                "Sen bir görev yürütme asistanısın. Kullanıcının görevini bir veya daha fazla shell komutuna dönüştür.\n"
                                "Çıktı SADECE geçerli bir JSON dizisi olmalı, başka hiçbir metin yok.\n"
                                'Biçim: [{"cmd": "komut", "desc": "adım açıklaması"}, ...]\n'
                                "[Katı kurallar - mutlaka uy]\n"
                                "1. Yalnızca kullanıcının açıkça istediğini yap; kendiliğinden ekstra adım ekleme.\n"
                                "2. rm/del/remove/unlink gibi silme komutlarını kesinlikle kullanma.\n"
                                "3. Kullanıcının mevcut dosyalarını değiştirme veya üzerine yazma.\n"
                                "4. Dosya oluştururken echo veya cat komutlarını kullan.\n"
                                "5. Yollar mutlak olmalı (ör. ~/Desktop/xxx).\n"
                                "6. Her komut bağımsız çalıştırılabilir olmalı.\n"
                                "7. Görev hiç komut gerektirmiyorsa (örn. soru-cevap), çıktı [] olmalı."
                            ),
                        ),
                        Message(role="user", content=f"Görev: {task}"),
                    ],
                    complexity="low",
                )
            )
        except Exception as e:
            _print_fatal(
                f"Model isteği başarısız oldu: {e}",
                hint="Lütfen ağ bağlantınızı kontrol edin ve API anahtarı yapılandırmasını.",
            )
            raise typer.Exit(1)

        progress.remove_task(progress.task_ids[0])

        #Adım 2: Komutu ayrıştırın
        raw = response.content.strip()
        #mümkün olanı kaldırmarkdownkod bloğu etiketi
        if raw.startswith("```"):
            first_newline = raw.find("\n")
            if first_newline != -1:
                raw = raw[first_newline + 1:]
            end_marker = raw.rfind("```")
            if end_marker != -1:
                raw = raw[:end_marker].strip()

        try:
            commands = json.loads(raw)
        except json.JSONDecodeError:
            console.print("[red]Model dönüş sonucu ayrıştırma başarısız oldu[/red]")
            console.print(f"ham çıktı:\n{raw}")
            return

    #Güvenlik filtrelemesi: Tehlikeli komutları engelleyin
    DANGEROUS_PREFIXES = ("rm ", "rm -rf", "rmdir ", "dd ", "> /dev/", ":(){ :|:& };:")
    for cmd_info in commands:
        cmd = cmd_info.get("cmd", "")
        if any(cmd.strip().startswith(p) for p in DANGEROUS_PREFIXES):
            console.print(f"[red]⛔Güvenlik Müdahalesi: Tehlikeli komut algılandı —{cmd}[/red]")
            console.print(Panel.fit(
                "[yellow]Yürütme engellendi. Bu, model tarafından bağımsız olarak oluşturulan ve sizin tarafınızdan talep edilmeyen bir komuttur.\n"
                "Tehlikeli işlemler gerçekleştirmeniz gerekiyorsa doğrudan iş akışı modunda çalıştırın.[/yellow]",
                border_style="yellow",
            ))
            return

    #komutu yürütmek
    if not commands:
        console.print("[yellow]⚠️Yürütülecek komut yok[/yellow]")
        console.print(f"\nmodel cevap:\n{response.content}")
        return

    console.print(f"[bold]📋Yürütme planı —{len(commands)}adım[/bold]\n")
    for i, cmd_info in enumerate(commands, 1):
        desc = cmd_info.get("desc", "")
        cmd = cmd_info.get("cmd", "")
        console.print(f"  {i}. {desc}")
        console.print(f"     $ {cmd}\n")

    #Doğrudan yürütme
    success_count = 0
    for cmd_info in commands:
        cmd = cmd_info.get("cmd", "")
        desc = cmd_info.get("desc", "")
        if not cmd:
            continue

        console.print(f"[cyan]▶çalıştır: {desc}[/cyan]")
        console.print(f"   $ {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                console.print("  [green]✓ başarılı[/green]")
                if result.stdout.strip():
                    console.print(f"    {result.stdout.rstrip()}")
                success_count += 1
            else:
                console.print(f"  [red]✗hata(exit {result.returncode})[/red]")
                if result.stderr.strip():
                    console.print(f"    [red]{result.stderr.rstrip()}[/red]")
        except subprocess.TimeoutExpired:
            console.print("  [red]✗zaman aşımı(30s)[/red]")
        except Exception as e:
            console.print(f"  [red]✗anormal: {e}[/red]")

    console.print()
    if success_count == len(commands):
        console.print(Panel.fit(
            f"[green]✅Tamamlandı({success_count}/{len(commands)}başarı)[/green]",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            f"[yellow]⚠️kısmen tamamlandı({success_count}/{len(commands)}başarı)[/yellow]",
            border_style="yellow",
        ))


def _init_router() -> ModelRouter:
    """Model yönlendiriciyi başlatın ve başarısız olduğunda kolay uyarılar verin."""
    config = RouterConfig()
    user_config = _load_config()
    default_model = _resolve_default_model(user_config)

    #incelemekAPI KeyHazır ol ya da olma
    api_key = _get_api_key(user_config, default_model)
    if not api_key:
        #bulunamadıkey, bir ipucu ver
        api_key_hint_map = {
            "deepseek": ("DEEPSEEK_API_KEY", "https://platform.deepseek.com/", "En uygun maliyetli, önerilen konfigürasyon"),
            "glm": ("ZHIPUAI_API_KEY", "https://www.zhipuai.cn/", "Bilgelik spektrumuGLMModeli"),
            "kimi": ("KIMI_API_KEY", "https://platform.moonshot.cn/", "ayın karanlık yüzüKimi"),
            "doubao": ("DOUBAO_API_KEY", "https://console.volcengine.com/", "Doubao (ByteDance)"),
            "minimax": ("MINIMAX_API_KEY", "https://www.minimax.io/", "MiniMax"),
            "tongyi": ("DASHSCOPE_API_KEY", "https://dashscope.console.aliyun.com/", "Tongyi"),
            "wenxin": ("ERNIE_API_KEY", "https://cloud.baidu.com/", "Wenxinyiyan"),
            "hunyuan": ("HUNYUAN_API_KEY", "https://cloud.tencent.com/", "Tencent Hunyuan"),
        }
        hint = api_key_hint_map.get(default_model)
        if hint:
            _print_missing_key_hint(hint[0], hint[2], url=hint[1])
        else:
            _print_missing_key_hint(f"{default_model.upper()}_API_KEY", "")
        raise typer.Exit(1)

    try:
        return ModelRouter(config)
    except Exception as e:
        _print_fatal(f"Çalışma dizini taraması: {e}")


def _print_missing_key_hint(key: str, reason: str = "", url: str = ""):
    """Eksik baskıAPI KeyDostça ipuçları"""

    console.print()
    hint_lines = (
        f"[dim]tavsiye etmek:[/dim] {key.split('_')[0].title()} — {reason}\n\n" if reason else ""
    )
    url_line = f"[dim]Adresi al:[/dim] {url}" if url else ""
    console.print(
        Panel(
            f"[bold red]✗bulunamadı{key}[/bold red]\n\n"
            f"[yellow]Lütfen önce yapılandırınAPI Key[/yellow]\n\n"
            f"{hint_lines}"
            f"[cyan]Birinci yöntem:[/cyan]Ortam değişkenlerini ayarlama\n"
            f"  [green]export {key}=your_key_here[green]\n\n"
            f"[cyan]İkinci yöntem:[/cyan]yazmak.envbelge\n"
            f"  [green]echo '{key}=your_key_here' >> .env[green]\n\n"
            f"{url_line}",
            title="⚠️EksiklikAPI Key",
            border_style="red",
        )
    )
    console.print()


def _print_fatal(msg: str, hint: str = ""):
    """Önemli hatayı yazdırın ve çıkın"""

    console.print()
    console.print(
        Panel(
            f"[bold red]✗ {msg}[/bold red]"
            + (f"\n\n[cyan]ipucu:[/cyan] {hint}" if hint else ""),
            title="❌Yürütme başarısız oldu",
            border_style="red",
        )
    )
    console.print()


def _check_env() -> bool:
    """Mevcut varsayılan modeli kontrol edinAPI KeyHazır mı? Geri dönmekTruehazır demektir"""
    user_config = _load_config()
    default_model = _resolve_default_model(user_config)
    api_key = _get_api_key(user_config, default_model)
    if not api_key:
        api_key_hint_map = {
            "deepseek": ("DEEPSEEK_API_KEY", "En uygun maliyetli, önerilen konfigürasyon"),
            "glm": ("ZHIPUAI_API_KEY", "Bilgelik spektrumuGLMModeli"),
            "kimi": ("KIMI_API_KEY", "ayın karanlık yüzüKimi"),
            "doubao": ("DOUBAO_API_KEY", "Doubao (ByteDance)"),
            "minimax": ("MINIMAX_API_KEY", "MiniMax"),
            "tongyi": ("DASHSCOPE_API_KEY", "Tongyi"),
            "wenxin": ("ERNIE_API_KEY", "Wenxinyiyan"),
            "hunyuan": ("HUNYUAN_API_KEY", "Tencent Hunyuan"),
        }
        hint = api_key_hint_map.get(default_model)
        if hint:
            _print_missing_key_hint(hint[0], hint[1])
        else:
            _print_missing_key_hint(f"{default_model.upper()}_API_KEY", "")
        return False
    return True


def _display_result(result):
    """İş akışı sonuçlarını göster"""
    console.print(f"\n[bold]İş akışı{result.workflow_id}[/bold]")
    console.print(f"durum: {_status_color(result.status.value)}")
    console.print(f"Yürütme süresi: {result.execution_time:.2f}s")
    console.print(f"Tokenkullanmak: {result.total_tokens:,}")

    #Her birini gösterAgentGerçek çıktı
    if result.outputs:
        for agent_name, output in result.outputs.items():
            if hasattr(output, 'result') and output.result:
                console.print(f"\n[bold]📋 {agent_name}çıktı:[/bold]")
                #kullanmakPanelEkranı güzelleştir
                console.print(
                    Panel(
                        output.result[:2000] + ("..." if len(output.result) > 2000 else ""),
                        title=f"{agent_name}sonuç",
                        border_style="cyan",
                    )
                )
                #Sonuç çok uzunsa dosyanın tamamını görüntülemenizi isteyin
                if len(output.result) > 2000:
                    console.print(
                        f"[dim]💡Sonuçların tamamı şuraya kaydedildi:: .omc/state/workflow_{result.workflow_id}.json[/dim]"
                    )

    if result.steps_completed:
        console.print("\n[green]✓Tamamlanan adımlar:[/green]")
        for step in result.steps_completed:
            console.print(f"  - {step}")

    if result.steps_failed:
        console.print("\n[red]✗başarısız adım:[/red]")
        for step in result.steps_failed:
            console.print(f"  - {step}")

    if result.error:
        console.print(f"\n[red]hata: {result.error}[/red]")
        console.print(
            f"\n[cyan]💡Ayrıntılı günlük:[/cyan] .omc/state/workflow_{result.workflow_id}.json"
        )


def _display_cross_validation_result(result):
    """Çapraz doğrulama sonuçlarını göster"""

    status_color = {
        "pass": "green",
        "fail": "red",
        "need_fix": "yellow",
        "skipped": "dim",
    }.get(result.status.value, "white")

    status_icon = {
        "pass": "✅",
        "fail": "❌",
        "need_fix": "⚠️",
        "skipped": "⏭",
    }.get(result.status.value, "?")

    panel_color = {
        "pass": "green",
        "fail": "red",
        "need_fix": "yellow",
        "skipped": "dim",
    }.get(result.status.value, "white")

    lines = [
        f"**tanımID**: `{result.validation_id}`",
        f"**İş akışı**: `{result.workflow_name}` (`{result.workflow_id}`)",
        f"**durum**: [{status_color}]{result.status.value.upper()}[/{status_color}]",
        f"**Bulunan sorunlar**: {len(result.issues)}bireysel",
        f"**Doğrulama zaman alır**: {result.execution_time:.1f}s",
    ]

    if result.issues:
        lines.append("")
        lines.append("[bold]Soru listesi:[/bold]")
        for i, issue in enumerate(result.issues, 1):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "⚪",
            }.get(issue.severity.value, "⚪")
            lines.append(
                f"{i}. {severity_icon} **[{issue.severity.value.upper()}]**"
                f"[{issue.category}] {issue.description}"
            )
            if issue.location:
                lines.append(f"   📍 {issue.location}")
            if issue.suggestion:
                lines.append(f"   💡 {issue.suggestion}")

    panel_title = f"{status_icon}Çapraz doğrulama sonuçları"

    console.print(
        Panel.fit("\n".join(lines), title=panel_title, border_style=panel_color)
    )


def _status_color(status: str) -> str:
    """Durumu renklendir"""
    colors = {
        "completed": "[green]Tamamlanmış[/green]",
        "failed": "[red]hata[/red]",
        "running": "[yellow]Koşma[/yellow]",
        "pending": "[dim]Beklemek[/dim]",
    }
    return colors.get(status, status)
