from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
birçokAgentişbirliğiCLIEmir

omc multiagent status      -İşbirliği durumunu görüntüle
omc multiagent spawn <role> <name> -Çocuk oluşturAgent
omc multiagent dispatch <task>     -Görevleri dağıt
omc multiagent list                -Tüm çocukları listeleAgent
omc multiagent remove <agent_id>   -KaldırmakAgent
"""


import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.multiagent.coordinator import (
    SubAgentStatus,
    get_coordinator,
)

app = typer.Typer(
    name="multiagent",
    help="birçokAgentişbirliği-Alt öğeleri oluşturun, planlayın, görüntüleyinAgent",
    add_completion=False,
)
console = Console()


def _agent_status_color(status: SubAgentStatus) -> str:
    return {
        SubAgentStatus.IDLE: "dim",
        SubAgentStatus.RUNNING: "cyan",
        SubAgentStatus.COMPLETED: "green",
        SubAgentStatus.FAILED: "red",
    }.get(status, "white")


@app.command("status")
def multiagent_status() -> None:
    """
Daha fazlasını görüntüleAgentİşbirliği durumu

Örnek:
        omc multiagent status
    """
    coordinator = get_coordinator()
    status = coordinator.get_status()

    console.print(
        Panel(
            f"[bold]toplamAgentsayı:[/bold] {status['total_agents']}\n"
            f"[bold]aktif görevler:[/bold] {status['active_tasks']}\n\n"
            f"🔄Koşma: [cyan]{status['running']}[/cyan]\n"
            f"✅Tamamlanmış: [green]{status['completed']}[/green]\n"
            f"❌hata: [red]{status['failed']}[/red]\n"
            f"⏳boşta: [dim]{status['idle']}[/dim]",
            title="🤖birçokAgentdurum",
            border_style="cyan",
        )
    )

    if status["agents"]:
        table = Table(title="oğulAgentliste")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("isim", style="white")
        table.add_column("Rol", style="yellow")
        table.add_column("durum", width=10)

        for agent in status["agents"]:
            color = _agent_status_color(SubAgentStatus(agent["status"]))
            status_display = f"[{color}]{agent['status']}[/{color}]"
            table.add_row(
                agent["agent_id"],
                agent["name"],
                agent["role"],
                status_display,
            )

        console.print(table)
    else:
        console.print("[dim]Henüz çocuk yokAgent,kullanmak`omc multiagent spawn`yaratmak[/dim]")


@app.command("spawn")
def multiagent_spawn(
    role: str = typer.Argument(
        ..., help="AgentRol(coder/reviewer/tester/planner/explorer/executor)"
    ),
    name: str = typer.Argument(..., help="Agentisim"),
    metadata: str = typer.Option(
        None,
        "--metadata",
        "-m",
        help="meta veriJSONsicim",
    ),
) -> None:
    """
Çocuk oluşturAgent

Örnek:
        omc multiagent spawn coder review-agent-1
        omc multiagent spawn reviewer security-checker -m '{"priority": "high"}'
    """
    import json

    meta = {}
    if metadata:
        try:
            meta = json.loads(metadata)
        except json.JSONDecodeError as e:
            console.print(f"[red]❗ metadata JSONAyrıştırma başarısız oldu: {e}[/red]")
            raise typer.Exit(1)

    coordinator = get_coordinator()
    agent = coordinator.spawn(role=role, name=name, metadata=meta)

    console.print(
        Panel.fit(
            f"[green]✓oğulAgentOluşturuldu[/green]\n\n"
            f"ID:   [cyan]{agent.agent_id}[/cyan]\n"
            f"isim: [cyan]{agent.name}[/cyan]\n"
            f"Rol: {role}\n"
            f"durum: [dim]idle[/dim]",
            title="🤖oğulAgent",
            border_style="green",
        )
    )


@app.command("list")
def multiagent_list() -> None:
    """
Tüm çocukları listeleAgent

Örnek:
        omc multiagent list
    """
    coordinator = get_coordinator()
    agents = list(coordinator.agents.values())

    if not agents:
        console.print("[dim]Henüz çocuk yokAgent[/dim]")
        return

    table = Table(title=f"oğulAgentliste({len(agents)})")
    table.add_column("ID", style="cyan", width=10)
    table.add_column("isim", style="white")
    table.add_column("Rol", style="yellow")
    table.add_column("durum", width=10)
    table.add_column("yaratılış zamanı", style="dim", width=18)

    for agent in agents:
        color = _agent_status_color(agent.status)
        status_display = f"[{color}]{agent.status.value}[/{color}]"
        table.add_row(
            agent.agent_id,
            agent.name,
            agent.role,
            status_display,
            agent.created_at[:19].replace("T", " "),
        )

    console.print(table)


@app.command("dispatch")
def multiagent_dispatch(
    task: str = typer.Argument(..., help="Görev açıklaması"),
    agent_ids: str = typer.Option(
        None,
        "--agents",
        "-a",
        help="Belirtilen Agent ID'leri (virgülle ayrılır, varsayılan: tümü)",
    ),
    mode: str = typer.Option(
        "parallel",
        "--mode",
        "-m",
        help="yürütme modu: parallel(paralel)/ sequential(emir)",
    ),
) -> None:
    """
Görevleri çocuklara dağıtınAgent

Örnek:
        omc multiagent dispatch "Kod değişikliklerini inceleyin" -a agent1,agent2
        omc multiagent dispatch "Uygulama işleviX" --mode sequential
    """
    import asyncio

    coordinator = get_coordinator()
    all_agents = list(coordinator.agents.values())

    if not all_agents:
        console.print("[red]❗Henüz çocuk yokAgent, ilk önce kullan`omc multiagent spawn`yaratmak[/red]")
        raise typer.Exit(1)

    if agent_ids:
        target_ids = [id_.strip() for id_ in agent_ids.split(",")]
        target_agents = [coordinator.get_agent(aid) for aid in target_ids]
        target_agents = [a for a in target_agents if a is not None]
        if not target_agents:
            console.print(f"[red]❗BelirtilenAgent: {agent_ids}[/red]")
            raise typer.Exit(1)
    else:
        target_agents = all_agents

    console.print(f"[cyan]Görevleri şuraya dağıt:{len(target_agents)}bireyselAgentModel önerisi{mode})[/cyan]")
    for a in target_agents:
        console.print(f"  - {a.name} [{a.role}]")

    try:
        if mode == "sequential":
            result = asyncio.run(coordinator.dispatch_sequential(task, target_agents))
        else:
            result = asyncio.run(coordinator.dispatch(task, target_agents))

        console.print(
            Panel.fit(
                f"[green]✓Görev tamamlandı[/green]\n\n"
                f"GörevID: [cyan]{result.task_id}[/cyan]\n"
                f"başlangıç: {result.started_at}\n"
                f"Sona ermek: {result.completed_at}\n\n"
                f"[bold]Özet:[/bold]\n{result.summary}",
                title="📊işbirlikçi sonuçlar",
                border_style="green",
            )
        )

        #her biriAgentsonuç
        for r in result.results:
            icon = "✅" if r.success else "❌"
            console.print(f"\n{icon} [{r.role}] {r.agent_id}")
            if r.success:
                output = str(r.output)[:200]
                if len(str(r.output)) > 200:
                    output += "..."
                console.print(f"   {output}")
            else:
                console.print(f"   [red]hata: {r.error}[/red]")

    except Exception as e:
        console.print(f"[red]❗Dağıtım başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command("remove")
def multiagent_remove(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Hunyuan"),
) -> None:
    """
alt öğeyi kaldırAgent

Örnek:
        omc multiagent remove abc12345
    """
    coordinator = get_coordinator()
    agent = coordinator.get_agent(agent_id)

    if agent is None:
        console.print(f"[red]❗ Agentçubuk gösterilmiyor: {agent_id}[/red]")
        raise typer.Exit(1)

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Kaldırma işlemini onaylayınAgent [cyan]{agent.name}[/cyan] ({agent_id})?"):
            console.print("[dim]İptal edildi[/dim]")
            return

    if coordinator.remove_agent(agent_id):
        console.print(f"[green]✓ AgentKaldırıldı: {agent_id}[/green]")
    else:
        console.print("[red]❗Kaldırma başarısız oldu[/red]")
        raise typer.Exit(1)


@app.command("clear")
def multiagent_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Temizlemeye zorla"),
) -> None:
    """
Tüm alt öğeleri temizleAgent

Örnek:
        omc multiagent clear -f
    """
    coordinator = get_coordinator()
    count = len(coordinator.agents)

    if count == 0:
        console.print("[dim]Henüz çocuk yokAgent[/dim]")
        return

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Tümünü temizlemeyi onaylayın{count}UzunAgent?"):
            console.print("[dim]İptal edildi[/dim]")
            return

    coordinator.clear_agents()
    console.print(f"[green]✓Temizlendi{count}UzunAgent[/green]")
