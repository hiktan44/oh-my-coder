from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
TUIEtkileşimli arayüz-Basit etkileşimli arayüz

dayalıBubble TeaKlavye odaklı tasarım konseptiTUIdeneyim.

Analiz ediliyor
- ↑/↓:navigasyon
- Enter:onaylamak
- Esc:geri dönmek/çıkış yapmak
- 1-7:Hızla bir iş akışı seçin
- m:Modeli değiştir
- a:Tümünü görüntüleAgent
- q:çıkış yapmak
"""


import subprocess
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


# Rich 14 removed Keys, define manually
class Keys:
    Up = "\x1b[A"
    Down = "\x1b[B"
    Left = "\x1b[D"
    Right = "\x1b[C"
    Enter = "\r"
    Escape = "\x1b"
    CtrlC = "\x03"


app = typer.Typer(help="TUIEtkileşimli arayüz-Klavye odaklı terminal etkileşimi")
console = Console()


class State(Enum):
    """TUIdurum makinesi"""

    MAIN = "main"
    WORKFLOW = "workflow"
    MODEL = "model"
    AGENTS = "agents"
    TASK = "task"
    CONFIRM = "confirm"


#İş akışı seçenekleri
WORKFLOWS = [
    ("explore", "Kod tabanını keşfedin", "Proje yapısını ve kod organizasyonunu anlayın"),
    ("build", "inşa etmek/geliştirmek", "Yeni özellikleri veya yeniden düzenleme kodunu uygulayın"),
    ("debug", "Hata ayıklama düzeltmesi", "Bulun ve onarınBug"),
    ("review", "kod incelemesi", "Kod kalitesini ve güvenliğini inceleyin"),
    ("test", "test üretimi", "Birim testleri ve entegrasyon testleri oluşturun"),
    ("pair", "çift ​​programlama", "VeAIBirlikte çalışın ve birlikte geliştirin"),
    ("autopilot", "Otonom sürüş", "Karmaşık görevleri tamamen otomatik olarak tamamlayın"),
]

#Desteklenen modeller
MODELS = [
    ("deepseek", "DeepSeek", "60 yuan ücretsiz kota, hızlı hız"),
    ("glm", "Bilgelik spektrumuGLM", "2 milyonTokensözgür"),
    ("mimo", "MiMo", "1MTarayıcı reddedildi"),
    ("qwen", "Tongyi", "Alibaba Bulut, ücretsiz kota"),
    ("wenxin", "Wenxinyiyan", "Baidu, ücretsiz kota"),
]

# Agentsınıflandırma
AGENT_CATEGORIES = {
    "inşa etmek/analiz etmek": [
        "ExploreAgent",
        "AnalystAgent",
        "PlannerAgent",
        "ArchitectAgent",
        "ExecutorAgent",
        "VerifierAgent",
        "DebuggerAgent",
        "TracerAgent",
        "PerformanceAgent",
    ],
    "gözden geçirmek": [
        "CodeReviewerAgent",
        "SecurityReviewerAgent",
    ],
    "alan": [
        "TestEngineerAgent",
        "DesignerAgent",
        "VisionAgent",
        "DocumentAgent",
        "WriterAgent",
        "ScientistAgent",
        "GitMasterAgent",
        "CodeSimplifierAgent",
        "QATesterAgent",
        "DatabaseAgent",
        "APIAgent",
        "DevOpsAgent",
        "UMLAgent",
        "MigrationAgent",
        "AuthAgent",
        "DataAgent",
    ],
    "koordinasyon": [
        "PromptAgent",
        "SelfImprovingAgent",
        "SkillManageAgent",
        "CriticAgent",
    ],
}


class TUISession:
    """TUIoturum durumu"""

    def __init__(self):
        self.state = State.MAIN
        self.selected_workflow: Optional[str] = None
        self.selected_model: str = "deepseek"
        self.task_input: str = ""
        self.cursor: int = 0
        self.confirm_choice: bool = False

    def render(self) -> Panel:
        """Mevcut durumu oluştur"""
        if self.state == State.MAIN:
            return self._render_main()
        if self.state == State.WORKFLOW:
            return self._render_workflow()
        if self.state == State.MODEL:
            return self._render_model()
        if self.state == State.AGENTS:
            return self._render_agents()
        if self.state == State.TASK:
            return self._render_task()
        if self.state == State.CONFIRM:
            return self._render_confirm()
        return Panel("Unknown state")

    def _render_main(self) -> Panel:
        """Güncelleme başarılı"""
        content = Text()
        content.append("🤖 Oh My Coder TUI\n\n", style="bold cyan")
        content.append("Lütfen bir eylem seçin:\n\n", style="white")

        for i, (key, desc, _) in enumerate(WORKFLOWS):
            marker = "▶ " if i == self.cursor else "  "
            style = "cyan bold" if i == self.cursor else "white"
            content.append(f"{marker}[{i + 1}] {key:<12}", style=style)
            content.append(f" {desc}\n", style="dim")

        content.append("\n[kısayol tuşu] ", style="dim")
        content.append("m", style="cyan")
        content.append("Modeli", style="dim")
        content.append("a", style="cyan")
        content.append(" Agent  ", style="dim")
        content.append("q", style="cyan")
        content.append("çıkış yapmak\n", style="dim")

        return Panel(
            content,
            title="[bold cyan]Oh My Coder TUI[/bold cyan]",
            border_style="cyan",
        )

    def _render_workflow(self) -> Panel:
        """Yenilemeye zorla"""
        content = Text()
        content.append("📋İş akışını seçin\n\n", style="bold cyan")

        for i, (key, desc, detail) in enumerate(WORKFLOWS):
            marker = "▶ " if i == self.cursor else "  "
            style = "cyan bold" if i == self.cursor else "white"
            content.append(f"{marker}{key:<12}", style=style)
            content.append(f"{desc} - {detail}\n", style="dim")

        content.append("\n[kısayol tuşu] ", style="dim")
        content.append("↑↓", style="cyan")
        content.append("navigasyon", style="dim")
        content.append("Enter", style="cyan")
        content.append("onaylamak", style="dim")
        content.append("Esc", style="cyan")
        content.append("geri dönmek", style="dim")

        return Panel(content, title="[bold]Yenilemeye zorla[/bold]", border_style="cyan")

    def _render_model(self) -> Panel:
        """Model seçimi"""
        content = Text()
        content.append("🔧Modeli seçin\n\n", style="bold cyan")

        for i, (key, name, desc) in enumerate(MODELS):
            marker = "▶ " if i == self.cursor else "  "
            style = "cyan bold" if i == self.cursor else "white"
            current = " ◀akım" if key == self.selected_model else ""
            content.append(f"{marker}{name:<12}", style=style)
            content.append(f"{desc}{current}\n", style="dim")

        content.append("\n[kısayol tuşu] ", style="dim")
        content.append("↑↓", style="cyan")
        content.append("navigasyon", style="dim")
        content.append("Enter", style="cyan")
        content.append("onaylamak", style="dim")
        content.append("Esc", style="cyan")
        content.append("geri dönmek", style="dim")

        return Panel(content, title="[bold]Model seçimi[/bold]", border_style="cyan")

    def _render_agents(self) -> Panel:
        """Agentliste"""
        content = Text()
        content.append("🤖 AgentListe (toplam 31)\n\n", style="bold cyan")

        for category, agents in list(AGENT_CATEGORIES.items())[:3]:  #Yalnızca ilk 3 kategoriyi göster
            content.append(f"[bold]{category}:[/bold]\n", style="white")
            for agent in agents[:5]:  #Kategori başına yalnızca 5 adet gösteriliyor
                content.append(f"  • {agent}\n", style="dim")
            if len(agents) > 5:
                content.append(f"  ...yaygın{len(agents)}bireysel\n", style="dim")

        content.append("\n[kısayol tuşu] ", style="dim")
        content.append("Esc", style="cyan")
        content.append("evrim", style="dim")

        return Panel(
            content,
            title="[bold]Agentliste[/bold]",
            border_style="cyan",
            width=60,
        )

    def _render_task(self) -> Panel:
        """Görev girişi"""
        content = Text()
        content.append("📝Görevi girin\n\n", style="bold cyan")
        content.append(
            f"İş akışı: [cyan]{self.selected_workflow}[/cyan]\n", style="white"
        )
        content.append(f"Modeli: [cyan]{self.selected_model}[/cyan]\n\n", style="white")
        content.append("Lütfen görevinizi açıklayın:\n", style="dim")
        content.append("[dim]Görevi girdikten sonra tuşuna basın.Enteronaylamak[/dim]\n\n", style="dim")
        content.append("[kısayol tuşu] ", style="dim")
        content.append("Esc", style="cyan")
        content.append("geri dönmek", style="dim")
        content.append("Enter", style="cyan")
        content.append("Görevi onayla", style="dim")

        return Panel(content, title="[bold]Görev girişi[/bold]", border_style="cyan")

    def _render_confirm(self) -> Panel:
        """Yürütmeyi onayla"""
        content = Text()
        content.append("✅Yürütmeyi onayla\n\n", style="bold cyan")
        content.append("Emir: [cyan]omc run[/cyan] ", style="white")
        content.append(f'"[yellow]{self.task_input}[/yellow]"', style="white")
        content.append(
            f" [cyan]--workflow {self.selected_workflow}[/cyan]\n", style="white"
        )
        content.append(f"Modeli: [cyan]{self.selected_model}[/cyan]\n\n", style="white")

        content.append("[kısayol tuşu] ", style="dim")
        content.append("y", style="cyan")
        content.append("uygulamak", style="dim")
        content.append("n", style="cyan")
        content.append("geri dönmek", style="dim")
        content.append("Esc", style="cyan")
        content.append("İptal etmek", style="dim")

        return Panel(content, title="[bold]onaylamak[/bold]", border_style="cyan")

    def handle_key(self, key: str) -> bool:
        """Klavye olaylarını yönetin ve devam etmeniz gerekip gerekmediğini geri dönün"""
        if key == "q":
            return False

        if self.state == State.MAIN:
            return self._handle_main(key)
        if self.state == State.WORKFLOW:
            return self._handle_workflow(key)
        if self.state == State.MODEL:
            return self._handle_model(key)
        if self.state == State.AGENTS:
            return self._handle_agents(key)
        if self.state == State.TASK:
            return self._handle_task(key)
        if self.state == State.CONFIRM:
            return self._handle_confirm(key)

        return True

    def _handle_slash_command(self, raw_input: str) -> bool:
        """tespit et ve çalıştır/skillkomut, tutulup tutulmayacağını döndürürTUIModel önerisiFalse=çıkış yapmak)"""
        #ayrıştırmak/skill-name [file-path]
        parts = raw_input.strip().split(maxsplit=2)
        if not parts or not parts[0].startswith("/"):
            return False

        skill_name = parts[0][1:]  #kaldırmak/
        file_path = parts[1] if len(parts) > 1 else None

        #kodu oku
        code_content = ""
        if file_path:
            p = Path(file_path)
            if p.is_file():
                code_content = p.read_text()
            else:
                console.print(f"[red]File not found: {file_path}[/red]")
                return True
        else:
            #Mevcut çalışma alanından okumayı deneyin
            ws_code = self._collect_workspace_code()
            code_content = ws_code if ws_code else "# No code provided"

        #uygulamakskill(geçmekomc skill run)
        cmd = ["omc", "skill", "run", skill_name]
        try:
            result = subprocess.run(
                cmd, input=code_content, capture_output=True, text=True, timeout=30
            )
            console.print(
                Panel.fit(
                    f"[green]✓ Skill /{skill_name} executed[/green]",
                    border_style="green",
                )
            )
            if result.stdout:
                console.print(
                    Syntax(
                        result.stdout[:2000],
                        "python",
                        theme="monokai",
                        line_numbers=True,
                    )
                )
            if result.stderr:
                console.print(f"[red]{result.stderr[:500]}[/red]")
        except subprocess.TimeoutExpired:
            console.print("[red]✗ Skill execution timed out[/red]")
        except Exception as exc:
            console.print(f"[red]✗ Skill failed: {exc}[/red]")

        console.print("[dim]Press any key to continue...[/dim]")
        self._wait_key()
        return True

    def _collect_workspace_code(self) -> str:
        """Geçerli çalışma alanındaki kod dosyalarını toplayın"""
        code_files = list(Path.cwd().rglob("*.py"))[:10]
        snippets = []
        for f in code_files[:3]:
            try:
                lines = f.read_text().splitlines()[:50]
                snippets.append(
                    f"# === {f.relative_to(Path.cwd())} ===\n" + "\n".join(lines)
                )
            except Exception:
                pass
        return "\n\n".join(snippets)

    def _wait_key(self) -> None:
        """Herhangi bir tuş girişini bekleyin"""
        console.input("")

    def _handle_main(self, key: str) -> bool:
        """Ana menü klavyesinin kullanımı"""
        if key == Keys.Up:
            self.cursor = max(0, self.cursor - 1)
        elif key == Keys.Down:
            self.cursor = min(len(WORKFLOWS) - 1, self.cursor + 1)
        elif key in ["1", "2", "3", "4", "5", "6", "7"]:
            idx = int(key) - 1
            if idx < len(WORKFLOWS):
                self.cursor = idx
                self.selected_workflow = WORKFLOWS[idx][0]
                self.state = State.TASK
        elif key in ["\n", "enter"]:
            self.selected_workflow = WORKFLOWS[self.cursor][0]
            self.state = State.TASK
        elif key.lower() == "m":
            self.state = State.MODEL
            self.cursor = 0
        elif key.lower() == "a":
            self.state = State.AGENTS
        return True

    def _handle_workflow(self, key: str) -> bool:
        """İş akışı seçimi klavyesinin kullanımı"""
        if key == Keys.Up:
            self.cursor = max(0, self.cursor - 1)
        elif key == Keys.Down:
            self.cursor = min(len(WORKFLOWS) - 1, self.cursor + 1)
        elif key in ["\n", "enter"]:
            self.selected_workflow = WORKFLOWS[self.cursor][0]
            self.state = State.TASK
        elif key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
            self.cursor = 0
        return True

    def _handle_model(self, key: str) -> bool:
        """Model seçimi klavye kullanımı"""
        if key == Keys.Up:
            self.cursor = max(0, self.cursor - 1)
        elif key == Keys.Down:
            self.cursor = min(len(MODELS) - 1, self.cursor + 1)
        elif key in ["\n", "enter"]:
            self.selected_model = MODELS[self.cursor][0]
            self.state = State.MAIN
        elif key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
        return True

    def _handle_agents(self, key: str) -> bool:
        """AgentKlavye kullanımını listeleme"""
        if key in ["escape", "ctrl+c", "q"]:
            self.state = State.MAIN
        return True

    def _handle_task(self, key: str) -> bool:
        """Görev girişi klavyesi kullanımı"""
        if key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
        elif key in ["\n", "enter"]:
            if self.task_input.strip():
                #Algılama/skillEmir
                if self.task_input.strip().startswith("/"):
                    self._handle_slash_command(self.task_input)
                    self.task_input = ""
                    self.state = State.MAIN
                else:
                    self.state = State.CONFIRM
        elif key == "backspace":
            self.task_input = self.task_input[:-1]
        elif len(key) == 1:
            self.task_input += key
        return True

    def _handle_confirm(self, key: str) -> bool:
        """Klavye işleminin yürütülmesini onaylayın"""
        if key.lower() == "y":
            self._execute_task()
            return False
        if key.lower() == "n":
            self.state = State.TASK
        elif key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
            self.task_input = ""
        return True

    def _execute_task(self):
        """görevleri gerçekleştirmek"""
        console.print("\n[yellow]Başlangıç:[/yellow]")
        console.print(
            f'  omc run "{self.task_input}" --workflow {self.selected_workflow} --model {self.selected_model}'
        )
        console.print("\n[dim](Gerçek yürütme işlevi geliştirme aşamasındadır)[/dim]")


@app.command()
def start(
    task: Optional[str] = typer.Argument(None, help="Görev açıklaması (isteğe bağlı)"),
    workflow: Optional[str] = typer.Option(None, "--workflow", "-w", help="İş akışını belirtin"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Modeli belirtin"),
):
    """başlatmakTUIEtkileşimli arayüz"""
    session = TUISession()

    #Parametreler doğrudan sağlandıysa atlayınTUI
    if task or workflow:
        if task:
            session.task_input = task
        if workflow:
            session.selected_workflow = workflow
        if model:
            session.selected_model = model

        session.state = State.CONFIRM if task else State.TASK
        with Live(session.render(), console=console, refresh_per_second=30):
            session.handle_key("\n")
        return

    #etkileşimliTUI
    console.print(
        Panel.fit(
            "[bold cyan]🤖 Oh My Coder TUI[/bold cyan]\n[dim]dosya yaz[/dim]",
            border_style="cyan",
        )
    )

    with Live(session.render(), console=console, refresh_per_second=30) as live:
        while True:
            key = console.input("")

            #Görev giriş modunu yönet
            if session.state == State.TASK and key not in [
                "\n",
                "enter",
                "escape",
                "ctrl+c",
            ]:
                if key == "backspace":
                    session.task_input = session.task_input[:-1]
                elif len(key) == 1 and key.isprintable():
                    session.task_input += key
                live.update(session.render())
                continue

            if not session.handle_key(key):
                break

            live.update(session.render())


@app.command("agents")
def list_agents():
    """hepsini listeleAgent"""
    table = Table(title="[bold cyan]🤖 AgentKontrol listesi[/bold cyan]")
    table.add_column("sınıflandırma", style="cyan")
    table.add_column("Agent", style="white")

    for category, agents in AGENT_CATEGORIES.items():
        table.add_row(category, ", ".join(agents))

    console.print(table)
    console.print(
        f"\n[dim]yaygın{sum(len(a) for a in AGENT_CATEGORIES.values())}bireyselAgent[/dim]"
    )


@app.command("workflows")
def list_workflows():
    """Tüm iş akışlarını listele"""
    table = Table(title="[bold cyan]📋İş akışı kontrol listesi[/bold cyan]")
    table.add_column("seri numarası", style="cyan", width=4)
    table.add_column("İş akışı", style="white")
    table.add_column("göstermek", style="dim")

    for i, (key, desc, _) in enumerate(WORKFLOWS, 1):
        table.add_row(str(i), f"[bold]{key}[/bold]", desc)

    console.print(table)


@app.command("models")
def list_models():
    """Mevcut tüm modelleri listele"""
    table = Table(title="[bold cyan]🔧Model listesi[/bold cyan]")
    table.add_column("Modeli", style="cyan")
    table.add_column("göstermek", style="dim")

    for _key, name, desc in MODELS:
        table.add_row(name, desc)

    console.print(table)


if __name__ == "__main__":
    app()
