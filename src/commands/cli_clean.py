from __future__ import annotations

from typing import Optional

"""
kod temizlemeCLI - omc cleanEmir

Kullanım örneği:
  omc clean                    #Geçerli dizini tara
  omc clean .                  #Geçerli dizini tara
  omc clean /path/to/project  #Belirtilen dizini tara
  omc clean --fix             #Otomatik olarak tarayın ve onarın
  omc clean --aggressive      #Agresif mod (boş dosyaları otomatik olarak siler)
  omc clean -o report.md      #Raporun dosyaya çıktısı
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="kod temizleme araçları-Gereksiz kodu otomatik olarak tespit edin ve temizleyin")
console = Console()


@app.command()
def clean(
    path: str = typer.Argument(".", help="Proje yolu"),
    fix: bool = typer.Option(False, "--fix", "-f", help="Düzeltilebilir sorunları otomatik olarak düzeltin"),
    strategy: str = typer.Option(
        "safe", "--strategy", "-s", help="Strateji: safe/aggressive"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="rapor çıktı dosyası"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Ayrıntıları göster"),
):
    """
Projelerdeki gereksiz kodları tarayın ve temizleyin

Temizleme stratejisi:
    -kullanılmayanimport/işlev/değişken
    -Kod pasajını tekrarlayın (>5 satır)
    -Ölü kod (referans yok)
    -boş dosya
    -Güncel olmayan yapılandırma dosyası
    """
    from src.agents.code_cleaner import CleanerStrategy

    project_path = Path(path).resolve()

    if not project_path.exists():
        console.print(f"[red]Hata: yol mevcut değil'{path}'[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Öğeleri tara: {project_path}[/cyan]")

    #Temizlemek
    strategy_obj = CleanerStrategy()
    if strategy == "aggressive":
        console.print("[yellow]Agresif mod: boş dosyaları otomatik olarak sil[/yellow]")
        strategy_obj.auto_delete_empty = True
        strategy_obj.dead_code_safe_mode = False

    #Temizleyiciyi içe aktar
    from src.agents.code_cleaner import CodeCleaner

    cleaner = CodeCleaner(project_path, strategy_obj)

    #Temizleme gerçekleştirin
    with console.status("[bold green]Tarama..."):
        report = cleaner.fix_all_auto() if fix else cleaner.scan()

    #raporu göster
    _display_report(report, verbose)

    #raporu kaydet
    if output:
        report_md = cleaner.generate_report_md(report)
        Path(output).write_text(report_md, encoding="utf-8")
        console.print(f"\n[green]✓[/green]Rapor şuraya kaydedildi:: {output}")


def _display_report(report, verbose: bool = False):
    """Temizleme raporunu göster"""
    #İstatistikler
    stats_panel = Panel(
        f"**Dosyaları tara**: {report.files_scanned}\n"
        f"**toplam soru sayısı**: {report.total_issues}\n"
        f"**Sabit**: {report.fixed_count}\n"
        f"**Onaylanacak**: {report.pending_count}\n"
        f"**Satır sayısında beklenen azalma**: {report.lines_removed}\n"
        f"**Tahmini tasarrufToken**: ~{report.estimated_token_savings}",
        title="📊Tarama sonuçları",
        border_style="cyan",
    )
    console.print(stats_panel)

    #Soru türü dağılımı
    if report.by_type:
        table = Table(title="Soru türü dağılımı")
        table.add_column("tip", style="yellow")
        table.add_column("miktar", style="cyan")

        for issue_type, count in sorted(report.by_type.items(), key=lambda x: -x[1]):
            table.add_row(issue_type, str(count))

        console.print(table)

    #Onarılan dosyalar
    if report.fixed_files:
        console.print("\n[green]✓Otomatik olarak onarıldı:[/green]")
        for f in report.fixed_files[:10]:
            console.print(f"  - {f}")
        if len(report.fixed_files) > 10:
            console.print(f"  ...Ayrıca{len(report.fixed_files) - 10}bireysel")

    #Onaylanması gereken sorunlar
    if report.pending_issues:
        console.print(f"\n[yellow]⚠Onaylanması gereken sorunlar({report.pending_count}bireysel):[/yellow]")
        for issue in report.pending_issues[:20]:
            severity_emoji = {
                "info": "ℹ",
                "warning": "⚠",
                "error": "❌",
            }.get(issue.severity, "?")

            if verbose:
                console.print(
                    f"  {severity_emoji} [{issue.severity}] {issue.file_path}"
                )
                console.print(f"     {issue.content}")
                console.print(f"     → {issue.fix_suggestion}")
            else:
                console.print(
                    f"  {severity_emoji} {issue.file_path}: {issue.content[:60]}"
                )

        if len(report.pending_issues) > 20:
            console.print(f"  ...Ayrıca{len(report.pending_issues) - 20}bireysel")

    #ipucu
    console.print("\n[dim]ipucu:[/dim]")
    console.print("  -kullanmak--fixDüşünce zinciri başladı")
    console.print("  -kullanmak--aggressiveAgresif mod (boş dosyaları otomatik olarak siler)")
    console.print("  -kullanmak-o report.mdraporu kaydet")


if __name__ == "__main__":
    app()
