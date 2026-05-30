from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Oh My Coder CLI -Komut satırı girişi

kullanmaktyperDostça inşa edinCLIarayüz.

Ana komutlar:
- omc run <task>         #görevleri gerçekleştirmek
- omc explore            #Kod tabanını keşfedin
- omc wiki               #Proje oluşturWiki
- omc agents             #hepsini listeleAgent
- omc status             #Durumu görüntüle
- omc --version          #sürümü göster
- omc --help             #Yardım bilgileri
"""


import os
from pathlib import Path

import typer

# ============================================================
#Ortam değişkenlerini başlangıçta yükleyin (öncelik: kullanıcı düzeyi>proje düzeyi)
# ============================================================
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.capabilities import app as cap_app

from .cli_checkpoint import app as checkpoint_app
from .cli_commands import app as commands_app
from .cli_config import app as config_app
from .cli_config_ext import app as config_ext_app
from .cli_doctor import app as doctor_app
from .cli_lsp import app as lsp_app
from .cli_mcp import app as mcp_app
from .cli_migrate import app as migrate_app
from .cli_multiagent import app as multiagent_app
from .cli_package_manager import app as pkg_app
from .cli_profile import app as profile_app
from .cli_quality import app as quality_app
from .cli_review import app as review_app
from .cli_run import (
    _init_router,
    explore,
    run,
    wiki,
)
from .cli_search import app as search_app
from .cli_security import app as security_app
from .cli_self_config import app as self_config_app
from .cli_server import app as server_app
from .cli_skill import app as skill_app
from .cli_task import app as task_app
from .cli_tui import app as tui_app
from .cli_usage import app as usage_app

#Kullanıcı düzeyinde yapılandırma~/.omc/.env(en yüksek öncelik)
_user_env = Path.home() / ".omc" / ".env"
if _user_env.exists():
    load_dotenv(_user_env, override=True)

#Proje düzeyinde yapılandırma.env(düşük öncelik)
_project_env = Path(".env")
if _project_env.exists():
    load_dotenv(_project_env, override=True)

#Sürüm bilgisi
__version__ = "0.2.0"
__author__ = "VOBC"
__repo__ = "https://github.com/VOBC/oh-my-coder"

app = typer.Typer(
    name="omc",
    help=f"Oh My Coder v{__version__} -çoklu ajanAIProgramlama Asistanı",
    add_completion=False,
    no_args_is_help=True,
)

#Alt komutu kaydet
app.add_typer(config_ext_app, name="agent-config")
app.add_typer(task_app, name="task")
app.add_typer(multiagent_app, name="multiagent")
app.add_typer(security_app, name="security")
app.add_typer(checkpoint_app, name="checkpoint")
app.add_typer(mcp_app, name="mcp")
app.add_typer(
    skill_app, name="skill", help="Skillsistem-Yerleşik ve özelSkillYönetim ve Yürütme"
)
app.add_typer(usage_app, name="usage", help="Kullanım istatistikleri ve izleme- stats/trace/memory")
app.add_typer(migrate_app, name="migrate", help="hafıza aktarımı-itibarenClaude/Geminiçalışma alanı")
app.add_typer(tui_app, name="tui", help="TUIEtkileşimli arayüz-Basit terminal etkileşimi")
app.add_typer(
    self_config_app, name="self-config", help="kendi kendini yapılandırma-Doğal dil yapılandırmasıAPI Key/Modeli/oyunculuk"
)
app.add_typer(doctor_app, name="doctor", help="Çevresel teşhis-Yaygın sorunları kontrol edin ve düzeltme önerilerinde bulunun")
app.add_typer(commands_app, name="cmd", help="komuta sistemi-Özel çalıştırMarkdownEmir")
app.add_typer(pkg_app, name="pkg", help="Paket yöneticisi- Homebrew/npm/scoop/winget/AUR")
app.add_typer(lsp_app, name="lsp", help="LSPentegre-Kod tanılama bilgilerini okuyun")
app.add_typer(search_app, name="search", help="kod arama- SourcegraphGenel kod tabanı araması")
app.add_typer(review_app, name="review", help="kod incelemesi-Kod değişikliklerinin akıllı analizi")
app.add_typer(quality_app, name="quality", help="Kod kalite kontrolü- ruff/blackentegre")
app.add_typer(profile_app, name="profile", help="Profileizolasyon-oğulAgentbağlam yönetimi")
app.add_typer(server_app, name="server", help="uzakServer - HTTP REST APISert")

#kod temizleme komutları
try:
    from .cli_clean import app as clean_app

    app.add_typer(clean_app, name="clean", help="kod temizleme-Gereksiz kodu tespit edin ve temizleyin")
except Exception:
    pass

# modelalt komut
from .cli_model import app as model_app  # noqa: E402

app.add_typer(model_app, name="model", help="Mevcut tüm modelleri listeleyin (destekler)-Kontrol etmek/Varsayılan modeli değiştir, yerelOllamaDestek")

# gatewayalt komut (tembel içe aktarma, kaçınmagatewayBir bağımlılık eksik olduğunda bir hata oluşur)
try:
    from .cli_gateway import app as gateway_app  # noqa: E402

    app.add_typer(gateway_app, name="gateway", help="Çok platformlu ağ geçidi- Telegram / Discord")
except Exception:
    pass  # gatewayBağımlılık eksikse atla

# docalt komut-Doküman yönetimi
try:
    from .cli_doc import app as doc_app  # noqa: E402

    app.add_typer(doc_app, name="doc", help="Doküman yönetimi-Belirtilenleri yürüt")
except Exception:
    pass

# agentalt komut- AgentKonfigürasyon yönetimi ve kişisel gelişim
try:
    from .cli_agent import app as agent_app  # noqa: E402

    app.add_typer(agent_app, name="agent", help="Agentüstesinden gelmek-İhracat/içe aktarmak/evrim")
except Exception:
    pass

# templatealt komut-İş akışı şablonu
try:
    from .cli_template import app as template_app  # noqa: E402

    app.add_typer(template_app, name="template", help="Mevcut durum:-Ekran miktarı/Şablonları kullanın")
except Exception:
    pass

# monorepoalt komut-çalışma alanı farkındalığı
try:
    from .cli_monorepo import app as monorepo_app  # noqa: E402

    app.add_typer(
        monorepo_app, name="monorepo", help="MonorepoDestek- pnpm/lerna/nxçalışma alanı farkındalığı"
    )
except Exception:
    pass

# initalt komut-Etkileşimli başlatma önyüklemesi
try:
    from .cli_init import app as init_app  # noqa: E402

    app.add_typer(init_app, name="init", help="İlk önyükleme-Etkileşimli yapılandırmaoh-my-coder")
except Exception:
    pass

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Sürüm bilgilerini göster",
        is_eager=True,
    ),
):
    """Oh My Coder -çoklu ajanAIProgramlama Asistanı"""
    if version:
        _print_version()
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold cyan]Oh My Coder[/bold cyan] v{__version__}\n"
                f"[dim]çoklu ajanAIProgramlama Asistanı[/dim]\n\n"
                f"[dim]kullanmak[bold]omc --help[/bold]Tüm komutları görüntüle[/dim]\n"
                f"[dim]depo: {__repo__}[/dim]",
                border_style="cyan",
            )
        )
        raise typer.Exit(0)


def _print_version():
    """Sürüm bilgilerini yazdır"""
    console.print(
        f"[bold cyan]oh-my-coder[/bold cyan] version [green]{__version__}[/green]"
    )
    console.print(f"[dim]Author: {__author__}[/dim]")
    console.print(f"[dim]Repo: {__repo__}[/dim]")


# ============================================================
#Üst düzey komutlar (cli_runiçe aktarmak)
# ============================================================
app.command()(run)
app.command()(explore)
app.command()(wiki)


# ============================================================
# Quest Modekomut (dancli_questiçe aktarmak)
# ============================================================
from src.commands.cli_quest import (
    quest,
    quest_cancel,
    quest_exec,
    quest_list,
    quest_notify,
    quest_pause,
    quest_resume,
    quest_status,
    quest_wait,
)

app.command()(quest)
app.command("quest-list")(quest_list)
app.command("quest-status")(quest_status)
app.command("quest-exec")(quest_exec)
app.command("quest-cancel")(quest_cancel)
app.command("quest-pause")(quest_pause)
app.command("quest-resume")(quest_resume)
app.command("quest-notify")(quest_notify)
app.command("quest-wait")(quest_wait)


@app.command()
def agents():
    """Mevcut olanların hepsini listeleAgent"""
    table = Table(title="Mevcut acenteler")
    table.add_column("isim", style="cyan")
    table.add_column("betimlemek")
    table.add_column("Hiyerarşi", style="green")

    #Tümünü içe aktarAgent
    from src.agents import (
        AnalystAgent,
        APIAgent,
        ArchitectAgent,
        AuthAgent,
        CodeReviewerAgent,
        CodeSimplifierAgent,
        CriticAgent,
        DataAgent,
        DatabaseAgent,
        DebuggerAgent,
        DesignerAgent,
        DevOpsAgent,
        DocumentAgent,
        ExecutorAgent,
        ExploreAgent,
        GitMasterAgent,
        MigrationAgent,
        PerformanceAgent,
        PlannerAgent,
        PromptAgent,
        QATesterAgent,
        ScientistAgent,
        SecurityReviewerAgent,
        SelfImprovingAgent,
        SkillManageAgent,
        TestEngineerAgent,
        TracerAgent,
        UMLAgent,
        VerifierAgent,
        VisionAgent,
        WriterAgent,
    )

    agents_list = [
        ("explore", ExploreAgent.description, ExploreAgent.default_tier),
        ("analyst", AnalystAgent.description, AnalystAgent.default_tier),
        ("planner", PlannerAgent.description, PlannerAgent.default_tier),
        ("architect", ArchitectAgent.description, ArchitectAgent.default_tier),
        ("executor", ExecutorAgent.description, ExecutorAgent.default_tier),
        ("verifier", VerifierAgent.description, VerifierAgent.default_tier),
        (
            "test-engineer",
            TestEngineerAgent.description,
            TestEngineerAgent.default_tier,
        ),
        (
            "code-reviewer",
            CodeReviewerAgent.description,
            CodeReviewerAgent.default_tier,
        ),
        ("debugger", DebuggerAgent.description, DebuggerAgent.default_tier),
        ("tracer", TracerAgent.description, TracerAgent.default_tier),
        ("critic", CriticAgent.description, CriticAgent.default_tier),
        ("writer", WriterAgent.description, WriterAgent.default_tier),
        ("designer", DesignerAgent.description, DesignerAgent.default_tier),
        (
            "security-reviewer",
            SecurityReviewerAgent.description,
            SecurityReviewerAgent.default_tier,
        ),
        ("git-master", GitMasterAgent.description, GitMasterAgent.default_tier),
        (
            "code-simplifier",
            CodeSimplifierAgent.description,
            CodeSimplifierAgent.default_tier,
        ),
        ("scientist", ScientistAgent.description, ScientistAgent.default_tier),
        ("qa-tester", QATesterAgent.description, QATesterAgent.default_tier),
        ("database", DatabaseAgent.description, DatabaseAgent.default_tier),
        ("api", APIAgent.description, APIAgent.default_tier),
        ("devops", DevOpsAgent.description, DevOpsAgent.default_tier),
        ("uml", UMLAgent.description, UMLAgent.default_tier),
        ("performance", PerformanceAgent.description, PerformanceAgent.default_tier),
        ("migration", MigrationAgent.description, MigrationAgent.default_tier),
        ("prompt", PromptAgent.description, PromptAgent.default_tier),
        ("vision", VisionAgent.description, VisionAgent.default_tier),
        ("auth", AuthAgent.description, AuthAgent.default_tier),
        ("data", DataAgent.description, DataAgent.default_tier),
        (
            "self-improving",
            SelfImprovingAgent.description,
            SelfImprovingAgent.default_tier,
        ),
        (
            "skill-manage",
            SkillManageAgent.description,
            SkillManageAgent.default_tier,
        ),
        (
            "document",
            DocumentAgent.description,
            DocumentAgent.default_tier,
        ),
    ]

    for name, desc, tier in agents_list:
        table.add_row(name, desc, tier)

    console.print(table)

    console.print(f"\n[dim]yaygın{len(agents_list)}Modele göre yapılandırın:[/dim]")


@app.command()
def status():
    """Sistem durumunu görüntüle"""
    console.print("[bold]Sistem durumu[/bold]\n")

    #incelemekAPI Key
    api_keys = {
        "DEEPSEEK_API_KEY": "🟢üretime hazır",
        "KIMI_API_KEY": "🟢üretime hazır",
        "DOUBAO_API_KEY": "🟢üretime hazır",
        "MINIMAX_API_KEY": "🟡 Beta",
        "ZHIPUAI_API_KEY": "🟡 Beta",
        "TONGYI_API_KEY": "🟡 Beta",
        "WENXIN_API_KEY": "🔴Geliştirilecek",
        "HUNYUAN_API_KEY": "🔴Geliştirilecek",
    }

    console.print("[bold]Model destek durumu:[/bold]")
    for key, status_label in api_keys.items():
        value = os.getenv(key)
        if value:
            console.print(f"  {key}: [{status_label}]yapılandırılmış")
        else:
            console.print(f"  {key}: [red]✗Yapılandırılmadı[/red]")

    #Yönlendiriciyi kontrol edin
    console.print()
    try:
        router = _init_router()
        stats = router.get_stats()
        console.print(
            Panel(
                f"[green]✓Yönlendirici hazır[/green]\n"
                f"Toplam istek: [cyan]{stats['total_requests']}[/cyan]\n"
                f"var olmak,:   [cyan]¥{stats['total_cost']:.4f}[/cyan]",
                title="yönlendirici",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(
            Panel(
                f"[red]✗Proje yapısını ve kod organizasyonunu anlayın[/red]\n\n{e}",
                title="yönlendirici",
                border_style="red",
            )
        )


def _mask_secret(value: str) -> str:
    """Hassasiyeti azaltılmış ekran tuşu"""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


#Alt komutu kaydet
app.add_typer(cap_app, name="cap", help="Yetenek paketi yönetimi-Dışa aktarın, içe aktarın ve paylaşınAgentYapılandırma")
app.add_typer(config_app, name="config", help="⚙️Yapılandırma yönetimi")

if __name__ == "__main__":
    app()
