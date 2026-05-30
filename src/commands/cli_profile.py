"""
Profile CLI - omc profileEmir

müdürAgentizolasyonprofileBağlam kirliliği sorununu çözmek için.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.profile_manager import (
    PREDEFINED_PROFILES,
    ProfileManager,
    create_predefined_profile,
    get_profile_summary,
)

app = typer.Typer(help="Profileüstesinden gelmek-oğulAgentbağlam izolasyonu")
console = Console()


@app.command("create")
def create_profile(
    agent_id: str = typer.Argument(..., help="Agentbenzersiz tanımlayıcı"),
    name: str = typer.Option(..., "--name", "-n", help="Agentisim"),
    template: str = typer.Option(
        None,
        "--template",
        "-t",
        help=f"Önceden tanımlanmış şablonları kullanın: {', '.join(PREDEFINED_PROFILES.keys())}",
    ),
):
    """yeni oluşturAgent Profile"""
    manager = ProfileManager()

    if template:
        if template not in PREDEFINED_PROFILES:
            console.print(f"[red]Bilinmeyen şablon: {template}[/red]")
            console.print(f"Mevcut şablonlar: {', '.join(PREDEFINED_PROFILES.keys())}")
            raise typer.Exit(1)

        profile = create_predefined_profile(template)
        if profile:
            #kapakIDve isim
            profile.agent_id = agent_id
            profile.agent_name = name
            manager.update_profile(profile)
    else:
        if manager.get_profile(agent_id):
            console.print(f"[red]ProfileZaten var: {agent_id}[/red]")
            raise typer.Exit(1)
        profile = manager.create_profile(agent_id, name)

    console.print("[green]✅ ProfileBaşarıyla oluşturuldu[/green]")
    console.print(f"[dim]ID: {profile.agent_id}[/dim]")
    console.print(f"Name: {profile.agent_name}")
    if profile.skills:
        console.print(f"Skills: {', '.join(profile.skills)}")


@app.command("list")
def list_profiles():
    """hepsini listeleAgent Profiles"""
    manager = ProfileManager()
    profiles = manager.list_profiles()

    if not profiles:
        console.print("[dim]HAYIRProfile[/dim]")
        return

    table = Table(title="Agent Profiles")
    table.add_column("ID", style="cyan")
    table.add_column("isim", style="green")
    table.add_column("hafıza numarası", justify="right")
    table.add_column("Görev sayısı", justify="right")
    table.add_column("Yetenek", style="dim")

    for p in profiles:
        table.add_row(
            p.agent_id[:20] + "..." if len(p.agent_id) > 20 else p.agent_id,
            p.agent_name,
            str(len(p.memories)),
            str(len(p.task_history)),
            ", ".join(p.skills[:3]) or "-",
        )

    console.print(table)


@app.command("show")
def show_profile(agent_id: str):
    """Kontrol etmekProfileDetaylar"""
    summary = get_profile_summary(agent_id)
    console.print(Panel(summary, title="Profile Details"))


@app.command("context")
def show_context(agent_id: str):
    """Kontrol etmekAgentEtkileşimli başlatma önyüklemesi"""
    manager = ProfileManager()
    context = manager.get_context_for_agent(agent_id)

    if not context:
        console.print(f"[red]Profileçubuk gösterilmiyor: {agent_id}[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]{context['agent_name']}[/bold]\n\n"
            f"[dim]son hafıza({len(context['memories'])}):[/dim]\n"
            + "\n".join(f"  • {m[:80]}" for m in context["memories"][-5:])
            + f"\n\n[dim]son görevler({len(context['recent_tasks'])}):[/dim]\n"
            + "\n".join(
                f"  • {t['task'][:60]}... [{t['status']}]"
                for t in context["recent_tasks"][-5:]
            )
            + "\n\n[dim]Tercihler:[/dim]\n"
            + "\n".join(f"  {k}: {v}" for k, v in context["preferences"].items()),
            title="Agent Context (Isolated)",
        )
    )


@app.command("add-memory")
def add_memory(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    memory: str = typer.Argument(..., help="bellek içeriği"),
):
    """KarşıProfileDüşünce zinciri başladı"""
    manager = ProfileManager()
    if manager.add_memory(agent_id, memory):
        console.print("[green]✅bellek eklendi[/green]")
    else:
        console.print(f"[red]Profileçubuk gösterilmiyor: {agent_id}[/red]")
        raise typer.Exit(1)


@app.command("add-task")
def add_task(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    task: str = typer.Argument(..., help="Görev açıklaması"),
    status: str = typer.Option("completed", "--status", "-s", help="Görev durumu"),
):
    """Görev yürütme geçmişini kaydedin"""
    manager = ProfileManager()
    if manager.add_task(agent_id, task, status):
        console.print("[green]✅Görev kaydedildi[/green]")
    else:
        console.print(f"[red]Profileçubuk gösterilmiyor: {agent_id}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_profile(agent_id: str):
    """silmekProfile"""
    manager = ProfileManager()
    if manager.delete_profile(agent_id):
        console.print(f"[green]✅Silindi: {agent_id}[/green]")
    else:
        console.print(f"[red]Profileçubuk gösterilmiyor: {agent_id}[/red]")
        raise typer.Exit(1)


@app.command("templates")
def list_templates():
    """Önceden tanımlanmış listeProfileÇocuk oluştur"""
    console.print("[bold]önceden tanımlanmışProfileÇocuk oluştur:[/bold]\n")

    for key, config in PREDEFINED_PROFILES.items():
        prefs = config["preferences"]
        suitable = prefs.get("suitable_for", [])
        not_suitable = prefs.get("not_suitable_for", [])

        console.print(
            Panel(
                f"[bold]{config['name']}[/bold] ({key})\n"
                f"Yetenek: {', '.join(config['skills'])}\n"
                + (
                    "\n[green]✓Uygun:[/green]\n  " + "\n  ".join(suitable)
                    if suitable
                    else ""
                )
                + (
                    "\n[red]✗Uygun değil:[/red]\n  " + "\n  ".join(not_suitable)
                    if not_suitable
                    else ""
                )
                + f"\n\n[dim]kullanmak: omc profile create <id> -n <name> -t {key}[/dim]",
                expand=False,
            )
        )


if __name__ == "__main__":
    app()
