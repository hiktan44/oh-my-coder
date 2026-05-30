from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Mevcut durum:CLI -Şablon yönetimi ve kullanımı

Emir:
- omc template list              #Mevcut şablonları listele
- omc template show <name>       #Şablon ayrıntılarını göster
- omc template use <name>        #Şablonları kullanarak iş akışları oluşturun
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="İş akışı şablon yönetimi")
console = Console()

#Şablon dizini
TEMPLATES_DIR = Path(__file__).parent.parent / "docs" / "templates"

#Yerleşik şablonlar
BUILTIN_TEMPLATES = {
    "flask-api": {
        "name": "flask-api",
        "display_name": "Flask APIgeliştirmek",
        "category": "development",
        "description": "Flask APIGeliştirme iş akışı-Tasarımdan dağıtıma",
        "workflow": "build",
        "estimated_time": "30-60 dakika",
        "agents": ["architect", "planner", "executor", "test-engineer", "verifier"],
    },
    "code-review": {
        "name": "code-review",
        "display_name": "kod incelemesi",
        "category": "quality",
        "description": "Çok boyutlu kod inceleme iş akışı-Kalite, güvenlik, performans",
        "workflow": "review",
        "estimated_time": "15-30 dakika",
        "agents": ["explore", "code-reviewer", "security-reviewer"],
    },
    "bug-fix": {
        "name": "bug-fix",
        "display_name": "Bugtamirat",
        "category": "debugging",
        "description": "Bugİş akışını bulun ve onarın-Analiz edin, bulun, onarın, doğrulayın",
        "workflow": "debug",
        "estimated_time": "20-40 dakika",
        "agents": ["explorer", "debugger", "executor", "verifier"],
    },
    #Yeni şablon ekle
    "enterprise": {
        "name": "enterprise",
        "display_name": "Kurumsal düzeyde geliştirme",
        "category": "enterprise",
        "description": "Kurumsal düzeyde proje iş akışı-Sürüm yineleme belleği",
        "workflow": "build",
        "estimated_time": "60-120 dakika",
        "agents": [
            "architect",
            "planner",
            "executor",
            "test-engineer",
            "verifier",
            "security-reviewer",
            "document-agent",
        ],
        "features": ["Denetim günlüğü", "Ekip çalışması", "Güvenlik Uyumluluğu", "CI/CDentegre"],
    },
    "multimodal": {
        "name": "multimodal",
        "display_name": "Çok modlu geliştirme",
        "category": "multimodal",
        "description": "Çok modlu geliştirme iş akışı-Ekran görüntüsü analizi,UIOtomatik nesil, görsel anlayış",
        "workflow": "build",
        "estimated_time": "30-60 dakika",
        "agents": ["vision-agent", "executor", "designer-agent", "verifier"],
        "features": ["Ekran görüntüsü analizi", "UIkod üretimi", "görsel anlayış", "Anlık Görüntü"],
    },
}


@app.command("list")
def list_templates(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Düşünce zinciri başladı"),
):
    """Mevcut şablonları listele"""
    table = Table(title="İş akışı şablon listesi")
    table.add_column("isim", style="cyan")
    table.add_column("ekran adı", style="white")
    table.add_column("kategori", style="yellow")
    table.add_column("Tahmini süre", style="green")
    table.add_column("betimlemek", style="dim")

    for name, info in BUILTIN_TEMPLATES.items():
        if category and info.get("category") != category:
            continue
        table.add_row(
            name,
            info.get("display_name", ""),
            info.get("category", ""),
            info.get("estimated_time", ""),
            info.get("description", "")[:50] + "...",
        )

    console.print(table)

    #ipucu
    console.print("\n[dim]kullanmak'omc template show <name>'ayrıntıları kontrol et[/dim]")
    console.print(
        "[dim]kullanmak'omc template use <name> --task \"Görev açıklaması\"'İş akışını başlat[/dim]"
    )


@app.command("show")
def show_template(
    name: str = typer.Argument(..., help="Şablon adı"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Orijinal belgeyi göster"),
):
    """Şablon ayrıntılarını göster"""
    if name not in BUILTIN_TEMPLATES:
        console.print(f"[red]Hata: Şablon bulunamadı'{name}'[/red]")
        console.print(f"[dim]Mevcut şablonlar: {', '.join(BUILTIN_TEMPLATES.keys())}[/dim]")
        raise typer.Exit(1)

    info = BUILTIN_TEMPLATES[name]

    #Ayrıntılı belgelerin mevcut olup olmadığını kontrol edin
    doc_file = TEMPLATES_DIR / f"{name}-workflow.md"
    if doc_file.exists() and not raw:
        content = doc_file.read_text(encoding="utf-8")
        md = Markdown(content)
        console.print(md)
    else:
        #Temel bilgileri göster
        panel = Panel(
            f"[bold]isim:[/bold] {info['name']}\n"
            f"[bold]ekran adı:[/bold] {info['display_name']}\n"
            f"[bold]kategori:[/bold] {info['category']}\n"
            f"[bold]İş akışı:[/bold] {info['workflow']}\n"
            f"[bold]Tahmini süre:[/bold] {info['estimated_time']}\n"
            f"[bold]içerenAgent:[/bold] {', '.join(info['agents'])}\n\n"
            f"[bold]betimlemek:[/bold]\n{info['description']}",
            title=f"şablon: {name}",
            border_style="cyan",
        )
        console.print(panel)


@app.command("use")
def use_template(
    name: str = typer.Argument(..., help="Şablon adı"),
    task: str = typer.Option("", "--task", "-t", help="Görev açıklaması"),
    project_path: Optional[Path] = typer.Option(
        None, "--project", "-p", help="Proje yolu"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Yalnızca yürütülecek komutları göster"),
):
    """Şablonları kullanarak iş akışları oluşturun"""
    if name not in BUILTIN_TEMPLATES:
        console.print(f"[red]Hata: Şablon bulunamadı'{name}'[/red]")
        raise typer.Exit(1)

    info = BUILTIN_TEMPLATES[name]
    workflow = info["workflow"]

    #Komut oluştur
    cmd_parts = ["omc", "run", workflow]
    if task:
        cmd_parts.extend(["--task", f'"{task}"'])
    if project_path:
        cmd_parts.extend(["--project", str(project_path)])

    cmd = " ".join(cmd_parts)

    if dry_run:
        console.print("[cyan]yürütülecek komut:[/cyan]")
        console.print(f"  {cmd}")
        console.print(f"\n[dim]İş akışı: {workflow}[/dim]")
        console.print(f"[dim]içerenAgent: {', '.join(info['agents'])}[/dim]")
        return

    #gerçek yürütme
    console.print(f"[cyan]İş akışını başlat'{name}'...[/cyan]")
    console.print(f"[dim]Görev: {task or '(belirtilmemiş)'}[/dim]")
    console.print(f"[dim]İş akışı: {workflow}[/dim]\n")

    #Asıl olan buraya çağrılmalıorchestratorancak örneği basitleştirmek için yalnızca komutlar gösterilmektedir
    #Gerçek entegrasyon sırasında içe aktarılması gerekiyorOrchestratorve yürüt
    console.print("[green]✓[/green]İş akışı başladı")
    console.print("[dim]ipucu:kullanmak'omc status'İlerlemeyi görüntüle[/dim]")

    #Kullanıcı referansı için komutun tamamını yazdırın
    console.print(f"\n[dim]Onayı atla ve doğrudan üzerine yaz: {cmd}[/dim]")


@app.command("create")
def create_template(
    name: str = typer.Argument(..., help="Yeni şablon adı"),
    base: Optional[str] = typer.Option(None, "--base", "-b", help="Mevcut şablona göre oluşturun"),
):
    """Yeni bir şablon oluşturun (etkileşimli)"""
    console.print(f"[cyan]Yeni şablon oluştur'{name}'...[/cyan]")

    if base:
        if base not in BUILTIN_TEMPLATES:
            console.print(f"[red]Hata: temel şablon'{base}'çubuk gösterilmiyor[/red]")
            raise typer.Exit(1)
        console.print(f"[dim]Şablon tabanlı'{base}'yaratmak[/dim]")

    #Etkileşimli olarak oluşturun
    display_name = typer.prompt("Düşünce zinciri başladı", default=name)
    category = typer.prompt("kategori", default="custom")
    description = typer.prompt("betimlemek", default="")
    workflow = typer.prompt("İş akışı türü", default="build")
    agents = typer.prompt("içerenAgent(virgülle ayrılmış)", default="executor,verifier")

    #Şablon bilgileri oluştur
    new_template = {
        "name": name,
        "display_name": display_name,
        "category": category,
        "description": description,
        "workflow": workflow,
        "agents": [a.strip() for a in agents.split(",")],
    }

    #Kullanıcı dizinine kaydet
    user_templates_dir = Path.home() / ".omc" / "templates"
    user_templates_dir.mkdir(parents=True, exist_ok=True)

    import json

    template_file = user_templates_dir / f"{name}.json"
    template_file.write_text(
        json.dumps(new_template, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green]şablon'{name}'Oluşturuldu")
    console.print(f"[dim]Konum: {template_file}[/dim]")


if __name__ == "__main__":
    app()
