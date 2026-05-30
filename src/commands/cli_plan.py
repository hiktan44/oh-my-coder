from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
omc plan - Plan ModeEmir

Yalnızca değişiklik planının çıktısı alınır ve kullanıcı bunu onayladıktan sonra yürütülür.
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..agents.planner import PlannerAgent
from ..core.router import ModelRouter, RouterConfig

app = typer.Typer(help="Plan Mode -Önce planlayın, sonra uygulayın")
console = Console()


def _init_router() -> ModelRouter:
    """Model yönlendiriciyi başlat"""
    config = RouterConfig()
    return ModelRouter(config)


def _check_env() -> bool:
    """Ortam yapılandırmasını kontrol edin"""
    import os

    keys = [
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OLLAMA_BASE_URL",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "XAI_API_KEY",
        "ZHIPUAI_API_KEY",
    ]
    if not any(os.getenv(k) for k in keys):
        console.print(
            "[red]❌Hiçbiri tespit edilmediAPI Key, lütfen önce yapılandırın:[/red]\n"
            "  [cyan]omc self-config set deepseek.api_key sk-xxx[/cyan]"
        )
        return False
    return True


@app.command()
def plan(
    task: str = typer.Argument(..., help="Doğal dil görev tanımı"),
    project_path: Path = typer.Option(".", "--project", "-p", help="Proje yolu"),
    model: str = typer.Option("deepseek", "--model", "-m", help="Model seçimi"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Onayı atlayın ve doğrudan yürütün"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Planı dosyaya kaydet"
    ),
):
    """
    Plan Mode -Görevi analiz edin, değişiklik planının çıktısını alın ve onaylandıktan sonra uygulayın.

    Examples:
        omc plan "Vermeksrc/utils.pyFeishu ("
        omc plan "Yeniden düzenlemecore/agent.pyhata işleme"
        omc plan "Kullanıcı kimlik doğrulama modülünü ekle" -o plan.md
    """
    #ön kontrol
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]Plan Mode[/bold cyan]\n"
            f"Görev: [yellow]{task}[/yellow]\n"
            f"proje: [dim]{project_path.absolute()}[/dim]",
            title="📋planlama modeli",
        )
    )

    #başlatma
    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    planner = PlannerAgent(model_router=router)

    # Step 1:Plan oluştur
    console.print("\n[bold]🔍Analiz görevleri...[/bold]")

    from ..agents.base import AgentContext

    context = AgentContext(
        project_path=project_path,
        task_description=task,
    )

    #AramaplannerPlan oluştur
    import asyncio

    try:
        result = asyncio.run(
            planner._run(
                context,
                prompt=[
                    {
                        "role": "user",
                        "content": f"Lütfen aşağıdaki görevler için ayrıntılı bir yürütme planı geliştirin:\n\n{task}",
                    }
                ],
            )
        )
        output_obj = planner._post_process(result, context)
    except Exception as e:
        console.print(f"[red]❌Planlama başarısız oldu: {type(e).__name__}[/red]")
        raise typer.Exit(1)

    # Step 2:Sunum planı
    plan_data = output_obj.artifacts.get("plan", {})
    execution_order = output_obj.artifacts.get("execution_order", [])

    _display_plan(plan_data, execution_order, console)

    #dosyaya kaydet
    if output:
        _save_plan(plan_data, execution_order, output, console)

    # Step 3:Yürütülüp yürütülmeyeceğini sorun
    if yes:
        execute = True
    else:
        console.print()
        response = typer.prompt(
            "Bu planı uygulamak istiyor musunuz?[y/N]",
            default="N",
            show_default=False,
        )
        execute = response.lower() in ("y", "yes")

    if not execute:
        console.print("\n[dim]İnfaz iptal edildi. Plan hafızaya kaydedildi.[/dim]")
        raise typer.Exit(0)

    # Step 4:yürütme planı
    console.print("\n[bold green]🚀Planı uygulamaya başlayın...[/bold green]")
    console.print("[dim](çift programlama)[/dim]\n")

    # TODO:Gerçekliğe erişimOrchestratoryürütme planı
    #Önce hayata geçirilmesi gerekiyorWorkflowLoaderKullanıcı tanımlı dinamik olarak yükleYAML
    # orchestrator = Orchestrator(router, state_dir=project_path / ".omc" / "state")
    # await orchestrator.run_workflow("build", task)

    console.print("[yellow]⚠️ Plan ModeYürütme işlevi geliştirilme aşamasındadır...[/yellow]")
    console.print("Şu anda mevcut: [cyan]omc run[/cyan]Komut yürütme görevi")


def _display_plan(
    plan_data: dict, execution_order: list[str], console: Console
) -> None:
    """Sunum planı"""
    if not plan_data:
        console.print("[yellow]⚠️Geçerli bir plan oluşturulmadı[/yellow]")
        return

    #(Kontrol etmek)
    title = plan_data.get("title", "isimsiz plan")
    summary = plan_data.get("summary", "")
    console.print(f"\n[bold cyan]📋 {title}[/bold cyan]")
    if summary:
        console.print(f"[dim]{summary}[/dim]\n")

    #sahne masası
    phases = plan_data.get("phases", [])
    if phases:
        table = Table(title="Yürütme aşaması", show_lines=True)
        table.add_column("sahne", style="cyan", no_wrap=True)
        table.add_column("Görev", style="white")
        table.add_column("belge", style="green")
        table.add_column("Agent", style="magenta")

        for phase in phases:
            phase_name = phase.get("name", "?")
            tasks = phase.get("tasks", [])
            task_lines = []
            file_lines = []
            agent_lines = []

            for t in tasks:
                tid = t.get("id", "?")
                ttitle = t.get("title", "?")
                task_lines.append(f"[{tid}] {ttitle}")
                files = t.get("files_to_modify", [])
                file_lines.append(", ".join(files) if files else "-")
                agent_lines.append(t.get("agent", "?"))

            table.add_row(
                phase_name,
                "\n".join(task_lines),
                "\n".join(file_lines),
                "\n".join(agent_lines),
            )

        console.print(table)

    #İnfaz emri
    if execution_order:
        console.print(
            f"\n[bold]İnfaz emri:[/bold] [dim]{' → '.join(execution_order[:8])}"
            + ("..." if len(execution_order) > 8 else "")
            + "[/dim]"
        )


def _save_plan(
    plan_data: dict, execution_order: list[str], output: Path, console: Console
) -> None:
    """Planı dosyaya kaydet"""
    import json

    content = f"""#yürütme planı

##özet
{plan_data.get("summary", "hiçbiri")}

##İnfaz emri
{" → ".join(execution_order)}

##detaylı plan

```json
{json.dumps(plan_data, indent=2, ensure_ascii=False)}
```
"""
    output.write_text(content, encoding="utf-8")
    console.print(f"\n[green]✓Plan şuraya kaydedildi::[/green] [dim]{output}[/dim]")
