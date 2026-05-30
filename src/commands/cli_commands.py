from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Markdownkomuta sistemi- .omc/commands/

Güvenlik filtrelemesi: Tehlikeli komutları engelleyin.omc/commands/Dizin komut dosyalarını saklar,
kullanmak$Parametre değişimi için parametre sözdizimi.

Dosya formatı:
---
name:Komut adı
description:Komut açıklaması
usage: omc cmd <arg1> <arg2>
---
#!/omc-command
echo "Hello $1"
echo "Project: $PROJECT"
"""

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Markdownkomuta sistemi-Özel komutu çalıştır")
console = Console()

#komut dizini
COMMANDS_DIR = Path.cwd() / ".omc" / "commands"


class Command:
    """Komut tanımı"""

    def __init__(self, name: str, path: Path, content: str):
        self.name = name
        self.path = path
        self.content = content
        self.frontmatter = self._parse_frontmatter()
        self.script = self._extract_script()

    def _parse_frontmatter(self) -> dict[str, str]:
        """ayrıştırmakYAML frontmatter"""
        frontmatter = {}

        #kibrit---...---parça
        match = re.match(r"^---\n(.*?)\n---", self.content, re.DOTALL)
        if match:
            yaml_content = match.group(1)
            for line in yaml_content.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

        return frontmatter

    def _extract_script(self) -> str:
        """Komut betiğini çıkar"""
        script = self.content

        #Kaldırmak---...---parça
        script = re.sub(r"^---\n.*?\n---\n", "", script, flags=re.DOTALL)

        #Kaldırmakshebang
        script = script.lstrip()
        if script.startswith("#!"):
            lines = script.splitlines()
            script = "\n".join(lines[1:])

        return script.strip()

    def description(self) -> str:
        return self.frontmatter.get("description", "")

    def usage(self) -> str:
        return self.frontmatter.get("usage", f"omc cmd {self.name}")

    def render_usage(self, args: list[str]) -> str:
        """Paket yöneticisini belirtin

Kullanıcı sağlandıargsmutlakshlex.quote()Komut enjeksiyonunu önlemek için kaçış:
        - $1/$2/...Düşünce zinciri başladı
        - $@Tüm bağımsız değişkenlerle değiştirin (boşlukla ayrılmış, çıkışlı)
        - $PROJECT/$CWD/$HOMESistem değişkenleri örneğin: kaçmadan doğrudan değiştirme
        """
        script = self.script

        #Uygun$1, $2, ...Yapılandırılmış modelleri listelemeshlex.quote()sonraki değer
        for i, arg in enumerate(args):
            script = script.replace(f"${i + 1}", shlex.quote(arg))

        #Tüm parametreler:$@Tüm argümanlar boşlukla ayrılmış olarak değiştirildi (her biri kaçtı)
        quoted_args = " ".join(shlex.quote(a) for a in args)
        script = script.replace("$@", quoted_args)

        #Ortam değişkenleri (proje tarafından kontrol edilebilir, kullanıcı dışı girdi, doğrudan değiştirme)
        env_vars = {
            "PROJECT": os.environ.get("PROJECT", Path.cwd().name),
            "CWD": os.getcwd(),
            "HOME": os.path.expanduser("~"),
            "DATE": os.popen("date '+%Y-%m-%d'").read().strip(),
            "TIME": os.popen("date '+%H:%M:%S'").read().strip(),
        }

        for var, value in env_vars.items():
            script = script.replace(f"${var}", value)

        return script


def load_commands() -> dict[str, Command]:
    """tüm komutları yükle"""
    commands = {}

    if not COMMANDS_DIR.exists():
        COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
        _create_example_commands()
        return commands

    for path in COMMANDS_DIR.glob("*.md"):
        try:
            content = path.read_text()
            name = path.stem
            commands[name] = Command(name, path, content)
        except Exception as e:
            console.print(f"[yellow]uyarmak:yükleme komutu{path.name}hata: {e}[/yellow]")

    return commands


def _create_example_commands():
    """Örnek komut oluştur"""
    examples = {
        "hello": """---
name: hello
description:basit selamlama komutu
usage: omc cmd hello <isim>
---
#!/omc-command
echo "Hello $1!"
echo "İlerleme göstergesini güncelle: $PROJECT"
echo "zaman: $DATE $TIME"
""",
        "deploy": """---
name: deploy
description:Uygulamayı sunucuya dağıt
usage: omc cmd deploy <çevre>
---
#!/omc-command
echo "dağıtmak$1 ortam..."
echo "proje: $PROJECT"
echo "İçindekiler: $CWD"

#Örnek dağıtım betiği
# git push origin main
# ./deploy.sh $1
""",
        "test": """---
name: test
description:Testleri çalıştır
usage: omc cmd test [Modeli seçmek için numarayı girin]
---
#!/omc-command
echo "Testleri çalıştır..."
echo "proje: $PROJECT"

#koşmakpytest
python3 -m pytest tests/ -v

#Veya birim testleri çalıştırın
# python3 -m unittest discover -s tests
""",
        "clean": """---
name: clean
description:temizleme projesi
usage: omc cmd clean
---
#!/omc-command
echo "temizleme projesi..."
echo "İçindekiler: $CWD"

#TemizlemekPythonönbellek
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null

#Temizlemeknode_modules (İsteğe bağlı)
# find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null

echo "Temizleme tamamlandı!"
""",
    }

    for name, content in examples.items():
        path = COMMANDS_DIR / f"{name}.md"
        if not path.exists():
            path.write_text(content)

    console.print(f"[dim]Örnek komut oluşturuldu{COMMANDS_DIR}[/dim]")


@app.command()
def run(
    name: str = typer.Argument(..., help="Komut adı"),
    args: Optional[list[str]] = typer.Argument(None, help="Komut parametreleri"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Yalnızca yürütülecek komutları göster"),
):
    if args is None:
        args = []
    """
Özel komutu çalıştır

Örnek:
        omc cmd run hellodünya
        omc cmd run deploy production
        omc cmd run test --dry-run
    """
    commands = load_commands()

    if name not in commands:
        console.print(f"[red]komut bulunamadı: {name}[/red]")
        console.print("\nMevcut komutlar:")
        for cmd_name, cmd in commands.items():
            console.print(f"  • {cmd_name}: {cmd.description()}")
        return

    cmd = commands[name]
    rendered = cmd.render_usage(args)

    if dry_run:
        console.print(
            Panel.fit(
                f"[cyan]Emir:[/cyan] {name}\n"
                f"[cyan]parametre:[/cyan] {' '.join(args)}\n\n"
                f"[cyan]idam edilecek:[/cyan]\n"
                f"[yellow]{rendered}[/yellow]",
                title="Dry Run",
                border_style="yellow",
            )
        )
        return

    #Betiği çalıştır
    console.print(f"\n[cyan]komutu yürütmek: {name}[/cyan]")
    console.print(f"[dim]{' '.join(args)}[/dim]\n")

    try:
        # nosec: B602,B602  # renderedKullanıcı:argsYapmakshlex.quote()kaçmak,shell=TrueEmniyet
        result = subprocess.run(
            rendered,
            shell=True,  # nosec B602
            cwd=os.getcwd(),
            capture_output=False,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"\n[red]Komut yürütme başarısız oldu(Çıkış kodu: {result.returncode})[/red]")
    except Exception as e:
        console.print(f"[red]yürütme hatası: {e}[/red]")


@app.command("list")
def list_commands():
    """Mevcut tüm komutları listele"""
    commands = load_commands()

    if not commands:
        console.print("[yellow]Komut bulunamadı[/yellow]")
        console.print(f"\nKomut dosyası oluştur: {COMMANDS_DIR}")
        console.print("[dim]kategoriye göre: .omc/commands/hello.md[/dim]")
        return

    table = Table(title=f"Özel komut(yaygın{len(commands)}bireysel)")
    table.add_column("isim", style="cyan")
    table.add_column("betimlemek", style="white")
    table.add_column("kullanım", style="dim")

    for name, cmd in commands.items():
        table.add_row(name, cmd.description(), cmd.usage())

    console.print(table)
    console.print(f"\n[dim]komut dizini: {COMMANDS_DIR}[/dim]")


@app.command("create")
def create_command(
    name: str = typer.Argument(..., help="Komut adı"),
    description: str = typer.Option("", "--description", "-d", help="Komut açıklaması"),
):
    """Yeni komut oluştur"""
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)

    path = COMMANDS_DIR / f"{name}.md"

    if path.exists():
        console.print(f"[red]komut zaten mevcut: {name}[/red]")
        return

    content = f"""---
name: {name}
description: {description or "Özel komut"}
usage: omc cmd run {name} <parametre>
---
#!/omc-command
echo "uygulamak{name}Emir"
echo "parametre: $@"
echo "proje: $PROJECT"
"""

    path.write_text(content)
    console.print(f"[green]✅Komut oluşturuldu: {name}[/green]")
    console.print(f"[dim]belge: {path}[/dim]")


@app.command("edit")
def edit_command(
    name: str = typer.Argument(..., help="Komut adı"),
):
    """Komutu düzenle"""
    commands = load_commands()

    if name not in commands:
        console.print(f"[red]komut bulunamadı: {name}[/red]")
        return

    cmd = commands[name]
    path = cmd.path

    console.print(f"[cyan]Komutu düzenle: {name}[/cyan]")
    console.print(f"[dim]belge: {path}[/dim]")

    #Düzenleyiciyi aç
    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(path)])


if __name__ == "__main__":
    app()
