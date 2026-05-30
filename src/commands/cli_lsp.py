from __future__ import annotations

"""
LSPentegre- AIOkunabilirdiagnostics

DestekVSCode ESLint/PylanceBeklemekLanguage ServerKod tanılama bilgilerini alın.
"""


import json
import os
import subprocess
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="LSPentegre-Kod tanılama bilgilerini okuyun")
console = Console()


# LSPteşhis seviyesi
class DiagnosticSeverity:
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


SEVERITY_NAMES = {
    1: "[red]hata[/red]",
    2: "[yellow]uyarmak[/yellow]",
    3: "[blue]bilgi[/blue]",
    4: "[dim]ipucu[/dim]",
}


def find_lsp_diagnostics(file_path: Optional[str] = None) -> list[dict[str, Any]]:
    """
BulmakLSPteşhis bilgileri

Desteklenen teşhis kaynakları:
    1. VSCode .vscode/problems.json
    2. ESLint JSONçıktı biçimi
    3. Pylance/ruffAraçlar bekleniyorJSONçıktı
    """
    diagnostics = []
    root = Path.cwd()

    # 1. VSCode problems.json
    vscode_dir = root / ".vscode"
    if vscode_dir.exists():
        problems_file = vscode_dir / "problems.json"
        if problems_file.exists():
            try:
                problems = json.loads(problems_file.read_text())
                for problem in problems.get("problems", []):
                    diagnostics.append(
                        {
                            "source": "VSCode",
                            "file": problem.get("file", ""),
                            "line": problem.get("line", 0),
                            "column": problem.get("column", 0),
                            "severity": problem.get("severity", 2),
                            "message": problem.get("message", ""),
                            "rule": problem.get("ruleId", ""),
                        }
                    )
            except Exception:
                pass

    # 2. ESLintSonuçları kontrol edin
    eslint_output = root / ".eslint-results.json"
    if eslint_output.exists():
        try:
            eslint_results = json.loads(eslint_output.read_text())
            for result in eslint_results:
                file_name = result.get("filePath", "")
                for msg in result.get("messages", []):
                    diagnostics.append(
                        {
                            "source": "ESLint",
                            "file": file_name,
                            "line": msg.get("line", 0),
                            "column": msg.get("column", 0),
                            "severity": msg.get("severity", 1),
                            "message": msg.get("message", ""),
                            "rule": msg.get("ruleId", ""),
                        }
                    )
        except Exception:
            pass

    # 3. ruffSonuçları kontrol edin(eğer mevcutsa)
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", "."],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=root,
        )
        if result.stdout:
            ruff_results = json.loads(result.stdout)
            for issue in ruff_results:
                diagnostics.append(
                    {
                        "source": "ruff",
                        "file": issue.get("filename", ""),
                        "line": issue.get("location", {}).get("row", 0),
                        "column": issue.get("location", {}).get("column", 0),
                        "severity": 2,  # ruffVarsayılan:warning
                        "message": issue.get("message", ""),
                        "rule": issue.get("code", ""),
                    }
                )
    except Exception:
        pass

    # 4. mypySonuçları kontrol edin(eğer mevcutsa)
    try:
        result = subprocess.run(
            ["mypy", "--output-format=json", "."],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=root,
        )
        if result.stdout:
            mypy_results = json.loads(result.stdout)
            for issue in mypy_results:
                diagnostics.append(
                    {
                        "source": "mypy",
                        "file": issue.get("file", ""),
                        "line": issue.get("line", 0),
                        "column": issue.get("column", 0),
                        "severity": 1 if issue.get("severity") == "error" else 2,
                        "message": issue.get("message", ""),
                        "rule": "type-error",
                    }
                )
    except Exception:
        pass

    #Belirtilen dosyaları filtrele
    if file_path:
        diagnostics = [d for d in diagnostics if file_path in d.get("file", "")]

    #Önem derecesine göre sırala
    diagnostics.sort(key=lambda x: x.get("severity", 999))

    return diagnostics


def format_diagnostics_for_ai(diagnostics: list[dict[str, Any]]) -> str:
    """Tanılama bilgilerini şu şekilde biçimlendir:AIokunabilir format"""
    if not diagnostics:
        return "✅Kod sorunu bulunamadı"

    lines = ["##Kod Tanılama Raporu\n"]

    #Dosyalara göre gruplandır
    by_file: dict[str, list[dict]] = {}
    for d in diagnostics:
        file_name = os.path.basename(d.get("file", "unknown"))
        if file_name not in by_file:
            by_file[file_name] = []
        by_file[file_name].append(d)

    for file_name, issues in by_file.items():
        lines.append(f"\n### {file_name}\n")

        for issue in issues:
            severity = SEVERITY_NAMES.get(issue.get("severity", 2), "[dim]bilinmiyor[/dim]")
            line = issue.get("line", 0)
            message = issue.get("message", "")
            rule = issue.get("rule", "")
            source = issue.get("source", "")

            lines.append(f"- {severity} **L{line}**: {message}")
            if rule:
                lines.append(f"  -kural: `{rule}` ({source})")

    lines.append(f"\n---\n**toplam**: {len(diagnostics)}kaydetmek")

    #istatistikler
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for d in diagnostics:
        counts[d.get("severity", 2)] = counts.get(d.get("severity", 2), 0) + 1

    lines.append(f"- 🔴hata: {counts.get(1, 0)}")
    lines.append(f"- 🟡uyarmak: {counts.get(2, 0)}")
    lines.append(f"- 🔵bilgi: {counts.get(3, 0)}")

    return "\n".join(lines)


@app.command()
def check(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Dosyayı belirtin"),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Teşhis kaynağını belirtin(ruff/mypy/eslint)"
    ),
    format: str = typer.Option(
        "table", "--format", "-o", help="Çıkış formatı(table/ai/json)"
    ),
):
    """
Kod tanılama bilgilerini kontrol edin

Örnek:
        omc lsp check
        omc lsp check --file src/main.py
        omc lsp check --source ruff --format ai
    """
    console.print("\n[cyan]🔍Kod Teşhis Kontrolü[/cyan]\n")

    diagnostics = find_lsp_diagnostics(file)

    if source:
        diagnostics = [
            d for d in diagnostics if d.get("source", "").lower() == source.lower()
        ]

    if not diagnostics:
        console.print("[green]✅Kod sorunu bulunamadı[/green]")
        return

    if format == "ai":
        # AIDostu format
        output = format_diagnostics_for_ai(diagnostics)
        console.print(Panel.fit(output, title="teşhis raporu", border_style="cyan"))
    elif format == "json":
        # JSONBiçim
        console.print_json(data=diagnostics)
    else:
        #tablo formatı
        table = Table(title=f"Aynı anda yükle(yaygın{len(diagnostics)}öğe)")
        table.add_column("seviye", style="cyan", width=10)
        table.add_column("belge", style="white")
        table.add_column("TAMAM", style="cyan", width=4)
        table.add_column("bilgi", style="white")
        table.add_column("kural", style="dim")

        for d in diagnostics[:100]:  #Gösterimi 100 öğeyle sınırla
            severity = SEVERITY_NAMES.get(d.get("severity", 2), "bilinmiyor")
            file_name = os.path.basename(d.get("file", ""))
            line = str(d.get("line", ""))
            message = d.get("message", "")[:60]
            rule = d.get("rule", "")

            table.add_row(severity, file_name, line, message, rule)

        console.print(table)

        if len(diagnostics) > 100:
            console.print(f"\n[dim]...Ayrıca{len(diagnostics) - 100}çubuk gösterilmiyor[/dim]")

    #istatistikler
    console.print("\n[bold]istatistikler:[/bold]")
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for d in diagnostics:
        sev = d.get("severity", 2)
        counts[sev] = counts.get(sev, 0) + 1

    console.print(f"  🔴hata: {counts.get(1, 0)}")
    console.print(f"  🟡uyarmak: {counts.get(2, 0)}")
    console.print(f"  🔵bilgi: {counts.get(3, 0)}")


@app.command()
def fix(
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="Yalnızca onarım önerilerinin gösterilip gösterilmeyeceği"
    ),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Onarım araçlarını belirtin"),
):
    """
Kod sorunlarını otomatik olarak düzeltin

Örnek:
        omc lsp fix                    #Yalnızca düzeltme önerilerini göster
        omc lsp fix --no-dry-run       #Onarım gerçekleştirin
        omc lsp fix --source ruff      #kullanmakrufftamirat
    """
    console.print("\n[cyan]🔧kod düzeltme[/cyan]\n")

    if dry_run:
        console.print("[yellow]Dry Runmodeli-Yalnızca düzeltme önerilerini göster[/yellow]\n")

    # ruffLütfen bir eylem seçin
    if not source or source == "ruff":
        console.print("[cyan]koşmakruffincelemek...[/cyan]")
        try:
            cmd = ["ruff", "check", "."]
            if dry_run:
                cmd.append("--preview")  #önizleme modu

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path.cwd(),
            )

            if result.stdout:
                console.print(result.stdout)

            if not dry_run and result.returncode == 0:
                #Otomatik onarım gerçekleştirin
                console.print("\n[cyan]Otomatik onarım gerçekleştirin...[/cyan]")
                fix_result = subprocess.run(
                    ["ruff", "check", "--fix", "."],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=Path.cwd(),
                )
                if fix_result.returncode == 0:
                    console.print("[green]✅ ruffYapılandırma yönetimi komutları[/green]")
                else:
                    console.print(f"[red]Onarım başarısız oldu: {fix_result.stderr}[/red]")
        except FileNotFoundError:
            console.print("[yellow]ruffMod—yalnızca yürütme planını gösterir[/yellow]")
        except Exception as e:
            console.print(f"[red]ruffYürütme başarısız oldu: {e}[/red]")


@app.command()
def setup(
    tool: str = typer.Argument(..., help="Kurulum aracı(ruff/mypy/eslint)"),
):
    """
Hızlı ayarlarLSPalet

Örnek:
        omc lsp setup ruff
        omc lsp setup mypy
    """
    console.print(f"\n[cyan]kurmak{tool}[/cyan]\n")

    if tool == "ruff":
        _setup_ruff()
    elif tool == "mypy":
        _setup_mypy()
    elif tool == "eslint":
        _setup_eslint()
    else:
        console.print(f"[red]Desteklenmeyen araçlar: {tool}[/red]")


def _setup_ruff():
    """kurmakruff"""
    try:
        #Kurulu olup olmadığını kontrol edin
        subprocess.run(["ruff", "--version"], capture_output=True, check=True)

        #yaratmakruff.toml
        config_file = Path.cwd() / "ruff.toml"
        if config_file.exists():
            console.print("[yellow]ruff.tomlZaten var[/yellow]")
        else:
            config_file.write_text(
                """
# Ruff - Python linter and formatter
line-length = 100
target-version = "py39"

[lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[lint.isort]
known-first-party = ["src"]
"""
            )
            console.print("[green]✅Oluşturulduruff.toml[/green]")

        console.print("\n[cyan]koşmakruff check --fixLütfen bir eylem seçin...[/cyan]")
        subprocess.run(["ruff", "check", "--fix", "."], capture_output=True)
        console.print("[green]✅ ruffKurulum tamamlandı[/green]")

    except FileNotFoundError:
        console.print("[red]ruffKurulu değil[/red]")
        console.print("Kurulum yöntemi:")
        console.print("  pip install ruff")
        console.print("  omc pkg install ruff")


def _setup_mypy():
    """kurmakmypy"""
    try:
        subprocess.run(["mypy", "--version"], capture_output=True, check=True)

        config_file = Path.cwd() / "mypy.ini"
        if config_file.exists():
            console.print("[yellow]mypy.iniZaten var[/yellow]")
        else:
            config_file.write_text(
                """
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
"""
            )
            console.print("[green]✅Oluşturuldumypy.ini[/green]")

    except FileNotFoundError:
        console.print("[red]mypyKurulu değil[/red]")
        console.print("Kurulum yöntemi:")
        console.print("  pip install mypy")
        console.print("  omc pkg install mypy")


def _setup_eslint():
    """kurmakESLint"""
    try:
        subprocess.run(["npx", "eslint", "--version"], capture_output=True, check=True)

        console.print("[green]✅ ESLintyapılandırılmış[/green]")
        console.print("\nkoşmakESLint:")
        console.print("  npx eslint .")

    except FileNotFoundError:
        console.print("[red]ESLintKurulu değil[/red]")
        console.print("Kurulum yöntemi:")
        console.print("  npm install -g eslint")
        console.print("  omc pkg install eslint")


if __name__ == "__main__":
    app()
