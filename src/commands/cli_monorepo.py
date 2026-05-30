from __future__ import annotations

"""
Monorepoçalışma alanı farkındalığıCLI

Destekpnpm workspace,lerna,bazelBeklemekmonorepoyapı
"""


from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Monorepoçalışma alanı farkındalığı")
console = Console()

# MonorepoYapılandırma dosyası
MONOREPO_CONFIGS = {
    "pnpm": ["pnpm-workspace.yaml"],
    "lerna": ["lerna.json"],
    "nx": ["nx.json", "workspace.json"],
    "turborepo": ["turbo.json"],
    "bazel": ["WORKSPACE", "WORKSPACE.bazel"],
    "rush": ["rush.json"],
}


@dataclass
class MonorepoInfo:
    """Monorepobilgi"""

    root: Path
    type: str  # pnpm, lerna, nx, etc.
    packages: list[Path]
    config_file: Path


def detect_monorepo(root: Path) -> Optional[MonorepoInfo]:
    """Dizinin olup olmadığını kontrol edinmonorepokök dizin"""
    for repo_type, config_files in MONOREPO_CONFIGS.items():
        for config in config_files:
            config_path = root / config
            if config_path.exists():
                packages = _find_packages(root, repo_type)
                return MonorepoInfo(
                    root=root,
                    type=repo_type,
                    packages=packages,
                    config_file=config_path,
                )
    return None


def _find_packages(root: Path, repo_type: str) -> list[Path]:
    """buna göremonorepoTür aramapackagesİçindekiler"""
    packages = []

    if repo_type == "pnpm":
        # pnpm: packages/dizin veyaworkspaceDosyada belirtilen yol
        workspace_file = root / "pnpm-workspace.yaml"
        if workspace_file.exists():
            content = workspace_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- ") or line.startswith("packages:"):
                    #yolu ayrıştır
                    if "packages/" in line:
                        pkg_dir = root / line.split("- ")[-1].strip()
                        if pkg_dir.is_dir():
                            packages.append(pkg_dir)
        #ortak yerler
        if not packages:
            common = root / "packages"
            if common.is_dir():
                for sub in common.iterdir():
                    if sub.is_dir():
                        packages.append(sub)

    elif repo_type == "lerna":
        lerna_file = root / "lerna.json"
        if lerna_file.exists():
            import json
            from glob import glob

            data = json.loads(lerna_file.read_text(encoding="utf-8"))
            package_patterns = data.get("packages", ["packages/*"])
            for pattern in package_patterns:
                # Handle glob patterns
                matched_dirs = glob(str(root / pattern), recursive=True)
                for matched in matched_dirs:
                    pkg_path = Path(matched)
                    if pkg_path.is_dir():
                        packages.append(pkg_path)

    elif repo_type == "nx":
        # nx: packages/İçindekiler
        common = root / "packages"
        if common.is_dir():
            for sub in common.iterdir():
                if sub.is_dir():
                    packages.append(sub)

    return packages


@app.command("detect")
def detect(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Test kataloğu"),
) -> None:
    """olup olmadığını kontrol edinmonorepove bilgileri görüntüle"""
    info = detect_monorepo(path)

    if info is None:
        console.print(
            f"[yellow]⚠[/yellow]İçindekiler[cyan]{path}[/cyan]bilinmiyormonorepoyapı"
        )
        console.print(
            "[dim]Destek: pnpm workspace, lerna, nx, turborepo, bazel, rush[/dim]"
        )
        return

    console.print(f"[green]✓[/green]saptanmışMonorepo: [bold]{info.type}[/bold]")
    console.print(f"[dim]kök dizin: {info.root}[/dim]")
    console.print(f"[dim]Yenilemeye zorla: {info.config_file}[/dim]")
    console.print(f"[dim]Paket miktarı: {len(info.packages)}[/dim]\n")

    table = Table(title=f"Paket listesi({info.type})")
    table.add_column("seri numarası", style="dim", width=4)
    table.add_column("paket yolu", style="cyan")
    table.add_column("dil", style="yellow")
    table.add_column("çerçeve", style="green")

    for i, pkg in enumerate(sorted(info.packages), 1):
        #Basit algılama dili
        lang = "?"
        if (pkg / "package.json").exists():
            lang = "Node/TS"
        elif (pkg / "pyproject.toml").exists():
            lang = "Python"
        elif (pkg / "Cargo.toml").exists():
            lang = "Rust"
        elif (pkg / "go.mod").exists():
            lang = "Go"
        elif (pkg / "pom.xml").exists():
            lang = "Java"
        elif (pkg / "build.gradle").exists():
            lang = "Java/Kotlin"

        rel = pkg.relative_to(info.root)
        table.add_row(str(i), str(rel), lang, "-")

    console.print(table)


@app.command("status")
def monorepo_status(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="çalışma alanı yolu"),
    show_dirty: bool = typer.Option(True, "--dirty/--no-dirty", help="Değiştirilen paketleri göster"),
) -> None:
    """Tüm paketleri gösterGitdurum"""
    info = detect_monorepo(path)

    if info is None:
        console.print("[red]✗[/red]HAYIRmonorepoİçindekiler")
        raise typer.Exit(1)

    import subprocess

    table = Table(title=f"Monorepopaket durumu- {info.type}")
    table.add_column("Çanta", style="cyan")
    table.add_column("durum", style="yellow")
    table.add_column("değiştirmek", style="red")

    for pkg in sorted(info.packages):
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=pkg,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                count = len(lines)
                status_emoji = "📦" if count == 0 else "✏️"
                table.add_row(
                    pkg.name,
                    status_emoji,
                    f"{count}dosyalar" if count else "temiz",
                )
        except Exception:
            table.add_row(pkg.name, "❓", "yaygın")

    console.print(table)
    console.print(f"\n[dim]kök dizin: {info.root}[/dim]")


@app.command("run")
def monorepo_run(
    script: str = typer.Argument(..., help="Çalıştırılacak betiğin adı"),
    scope: str = typer.Option(None, "--scope", "-s", help="Yalnızca belirtilen paketleri çalıştırın (bulanık eşleştirme)"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="çalışma alanı yolu"),
    parallel: bool = typer.Option(False, "--parallel", help="Paralel olarak çalıştır"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Yalnızca çalıştırılacak komutları göster"),
) -> None:
    """Aynı anda yükle/Komut dosyasını belirtilen pakette çalıştır"""
    info = detect_monorepo(path)

    if info is None:
        console.print("[red]✗[/red]HAYIRmonorepoİçindekiler")
        raise typer.Exit(1)

    packages = info.packages
    if scope:
        packages = [p for p in packages if scope.lower() in p.name.lower()]

    if not packages:
        console.print(f"[yellow]⚠[/yellow]Eşleşen paket bulunamadı(scope: {scope})")
        return

    console.print(f"[cyan]içinde olacak{len(packages)}Bir pakette çalıştır: {script}[/cyan]\n")

    import subprocess

    results = []
    for pkg in packages:
        cmd = None
        if info.type == "pnpm":
            cmd = ["pnpm", "--filter", pkg.name, "run", script]
        elif info.type == "nx":
            cmd = ["npx", "nx", "run-many", "-t", script, "-p", pkg.name]
        elif info.type == "lerna":
            cmd = ["npx", "lerna", "run", script, "--scope", pkg.name]
        else:
            console.print(f"[yellow]⚠[/yellow] {info.type}toplam boyut'run'Emir")
            return

        if dry_run:
            console.print(f"[dim]  cd {pkg} && {' '.join(cmd)}[/dim]")
        else:
            console.print(f"[cyan]→[/cyan] {pkg.name}...", end=" ")
            try:
                result = subprocess.run(
                    cmd, cwd=info.root, capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    console.print("[green]✓[/green]")
                    results.append((pkg, True, ""))
                else:
                    console.print("[red]✗[/red]")
                    results.append((pkg, False, result.stderr[:100]))
            except Exception as e:
                console.print(f"[red]✗ {e}[/red]")
                results.append((pkg, False, type(e).__name__))

    #Özet
    passed = sum(1 for _, ok, _ in results if ok)
    console.print(f"\n[bold]Sona ermek: {passed}/{len(results)}başarı[/bold]")


if __name__ == "__main__":
    app()
