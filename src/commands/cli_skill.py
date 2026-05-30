from __future__ import annotations

from typing import Optional

"""
Skill CLI - omc skillEmir

kullanım:
    omc skill list                      #Mevcut olanların hepsini listeleSkill
    omc skill run <name> [--code <path>]  #Belirtilenleri yürütSkill
    omc skill info <name>               #Kontrol etmekSkillDetaylar
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from src.skills import get_registry

app = typer.Typer(help="Skillüstesinden gelmek-listele ve çalıştırSkill")
console = Console()


@app.command("list")
def list_skills(
    builtin_only: bool = typer.Option(False, "--builtin", help="Yalnızca yerleşikleri gösterSkill"),
    custom_only: bool = typer.Option(False, "--custom", help="Yalnızca özel gösterSkill"),
) -> None:
    """Mevcut olanların hepsini listeleSkill"""
    registry = get_registry()

    if builtin_only:
        skills = registry.list_builtin()
    elif custom_only:
        skills = registry.list_custom()
    else:
        skills = registry.list_all()

    if not skills:
        console.print("[dim]No skills found.[/dim]")
        return

    registry.display_list()


@app.command("info")
def skill_info(name: str) -> None:
    """Kontrol etmekSkillDetaylar"""
    registry = get_registry()
    skill = registry.get(name)

    if skill is None:
        console.print(f"[red]Skill '{name}' not found[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold cyan]/{skill.name}[/bold cyan]\n"
            f"[dim]Source:[/dim] {skill.source}\n"
            f"[dim]File:[/dim] {skill.file_path or 'builtin'}\n\n"
            f"{skill.description or 'No description'}",
            title="Skill Info",
            expand=False,
        )
    )

    if skill.file_path:
        console.print(f"[dim]Defined in:[/dim] {skill.file_path}")


@app.command("run")
def run_skill(
    name: str = typer.Argument(..., help="SkillAd (hariç/)"),
    code: Optional[Path] = typer.Option(
        None, "--code", "-c", help="Kod dosyası yolu (başlamak için boş bırakın)stdinOkumak)"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Sonuçları dosyaya aktar"
    ),
) -> None:
    """Belirtilenleri yürütSkill"""
    registry = get_registry()

    #kodu oku
    if code is not None:
        if not code.is_file():
            console.print(f"[red]File not found: {code}[/red]")
            raise typer.Exit(1)
        code_content = code.read_text()
        ctx = {"file_path": str(code), "module_name": code.stem}
    else:
        #itibarenstdinOkumak
        console.print("[dim]Paste or pipe your code (Ctrl+D to finish):[/dim]")
        code_content = ""
        try:
            import sys

            code_content = sys.stdin.read()
        except Exception:
            pass

    if not code_content.strip():
        console.print("[yellow]No code provided. Use --code or pipe input.[/yellow]")
        raise typer.Exit(1)

    ctx = {"file_path": str(code) if code else ""}
    result = registry.run(name, code_content, ctx)

    if not result.success:
        console.print(f"[red]✗ Skill failed:[/red] {result.error}")
        raise typer.Exit(1)

    console.print(f"[green]✓ Skill executed in {result.duration_ms:.1f}ms[/green]")
    console.print()

    #Çıktı sonuçları
    if output_file:
        output_file.write_text(result.output)
        console.print(f"[dim]Output written to {output_file}[/dim]")
    else:
        if result.output:
            syntax = Syntax(result.output, "python", theme="monokai", line_numbers=True)
            console.print(syntax)

    #meta veri
    if result.metadata:
        console.print(f"\n[dim]Metadata:[/dim] {result.metadata}")


@app.command("init")
def init_custom_skills() -> None:
    """(kod parçacığı)Skillİçindekiler"""
    skill_dir = Path.home() / ".omc" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)

    example_file = skill_dir / "example_skill.py"
    if not example_file.exists():
        example_file.write_text(
            '''"""Örnek özelleştirmeSkill"""

from src.skills import Skill, SkillResult


def skill_custom_analysis(code: str, context: dict) -> SkillResult:
    """Özel kod analiziSkill"""
    lines = code.splitlines()
    return SkillResult(
        success=True,
        output=f"Analyzed {len(lines)} lines of code",
        metadata={"lines": len(lines)},
    )


#kayıt olmak
SKILL = Skill(
    name="custom_analysis",
    description="Özel kod analizi-Kod ve yapı satırlarını analiz edin",
    func=skill_custom_analysis,
    source="custom",
)
'''
        )
        console.print(f"[green]✓ Created example skill:[/green] {example_file}")
        console.print(
            "[dim]Edit it to create your own skills, then run 'omc skill list'.[/dim]"
        )
    else:
        console.print(f"[dim]Custom skills dir already exists:[/dim] {skill_dir}")


# ===== SkillYağış kapalı döngüsü=====


@app.command("propose")
def propose_skill(
    task: str = typer.Argument(..., help="Görev açıklaması"),
    steps: str = typer.Option("", "--steps", "-s", help="Yürütme adımları (virgülle ayrılmış)"),
    reflections: str = typer.Option(
        "", "--reflections", "-r", help="Yansıma notları (virgülle ayrılmış)"
    ),
):
    """Görevden çıkarSkillteklif"""
    from src.core.skill_extractor import (
        extract_skill_from_task,
        save_proposal,
    )

    steps_list = [s.strip() for s in steps.split(",") if s.strip()]
    reflections_list = [r.strip() for r in reflections.split(",") if r.strip()]

    proposal = extract_skill_from_task(task, steps_list, reflections_list)

    if not proposal:
        console.print("[yellow]⚠️Çıkarmaya değmez (çok az adım veya yeterince genel değil)[/yellow]")
        raise typer.Exit(0)

    filepath = save_proposal(proposal)

    console.print("[green]✅ SkillTeklif oluşturuldu[/green]")
    console.print(f"[dim]ID: {proposal.id}[/dim]")
    console.print(f"[bold]{proposal.title}[/bold]")
    console.print(f"tetiklemek: {proposal.trigger}")
    console.print("\nadım:")
    for i, step in enumerate(proposal.steps, 1):
        console.print(f"  {i}. {step}")
    console.print(f"\n[dim]kaydet: {filepath}[/dim]")
    console.print("[dim]koşmak'omc skill review'Bekleyen teklifleri görüntüle[/dim]")


@app.command("review")
def review_proposals():
    """Bekleyenleri görüntüleSkillteklif"""
    from src.core.skill_extractor import list_proposals

    proposals = list_proposals()
    pending = [p for p in proposals if p.status == "pending"]

    if not pending:
        console.print("[dim]bekleyen hiçbir şey yokSkillteklif[/dim]")
        return

    console.print(f"[bold]📋Askıda olmasıSkillteklif({len(pending)})\n[/bold]")

    for i, p in enumerate(pending, 1):
        console.print(
            Panel(
                f"[bold]{i}. {p.title}[/bold]\n"
                f"[dim]ID: {p.id}[/dim]\n"
                f"tetiklemek: {p.trigger}\n"
                f"adım sayısı: {len(p.steps)}\n"
                f"kaynak: {p.source_task[:60]}...",
                expand=False,
            )
        )

    console.print("\n[dim]İşlemek için aşağıdaki komutu kullanın:[/dim]")
    console.print("  omc skill accept <id>  #kabul et ve oluşturSKILL.md")
    console.print("  omc skill reject <id>  #reddetmek")


@app.command("accept")
def accept_skill_proposal(proposal_id: str):
    """kabul etmekSkillteklif"""
    from src.core.skill_extractor import accept_proposal

    skill_path = accept_proposal(proposal_id)
    if skill_path:
        console.print("[green]✅ SkillKabul edildi[/green]")
        console.print(f"[dim]Dosya oluştur: {skill_path}[/dim]")
    else:
        console.print(f"[red]❌Teklif bulunamadı: {proposal_id}[/red]")
        raise typer.Exit(1)


@app.command("reject")
def reject_skill_proposal(proposal_id: str):
    """reddetmekSkillteklif"""
    from src.core.skill_extractor import reject_proposal

    if reject_proposal(proposal_id):
        console.print(f"[green]✅Teklif reddedildi: {proposal_id}[/green]")
    else:
        console.print(f"[red]❌Teklif bulunamadı: {proposal_id}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
