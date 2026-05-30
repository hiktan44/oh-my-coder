from __future__ import annotations

"""
Checkpoint CLIEmir

omc checkpoint --list                      #Tüm anlık görüntüleri listele
omc checkpoint --restore <id>             #Belirtilen anlık görüntüye geri dönün
omc checkpoint --diff <id>                 #Anlık görüntü ile geçerli görüntü arasındaki farkları görüntüleme
omc checkpoint --delete <id>               #Anlık görüntüyü sil
omc checkpoint --info <id>                 #Anlık görüntü ayrıntılarını görüntüle
omc checkpoint --stats                     #İstatistikleri görüntüle
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.core.checkpoint import CheckpointManager

app = typer.Typer(
    name="checkpoint", help="CheckpointAnlık görüntü yönetimi - görev başlamadan önce otomatik olarak kayıt yapın ve herhangi bir sorun oluştuğunda geri alın"
)
console = Console()


@app.command()
def list(
    task_id: str = typer.Option(None, "--task", "-t", help="göreve göreIDfiltre"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="Proje yolu"),
    limit: int = typer.Option(20, "--limit", "-n", help="Öğe sayısını döndür"),
):
    """hepsini listeleCheckpoint"""
    cm = CheckpointManager(project_path=project_path)
    checkpoints = cm.list(task_id=task_id, limit=limit)

    if not checkpoints:
        console.print("[dim]Henüz anlık görüntü yok, kullanın`omc run`otomatik olarak oluşturulacak[/dim]")
        raise typer.Exit(0)

    table = Table(title="Checkpointliste")
    table.add_column("ID", style="cyan", no_wrap=False)
    table.add_column("Görev", style="green")
    table.add_column("betimlemek", style="white")
    table.add_column("belge", style="yellow", justify="right")
    table.add_column("boyut", style="magenta")
    table.add_column("yaratılış zamanı", style="dim")

    for cp in checkpoints:
        size_kb = cp.get("total_size", 0) // 1024
        size_str = f"{size_kb} KB" if size_kb > 0 else "<1 KB"
        table.add_row(
            cp["id"],
            cp.get("task_id", ""),
            cp.get("description", "")[:40],
            str(cp.get("file_count", 0)),
            size_str,
            cp.get("created_at", "")[:19],
        )

    console.print(table)
    console.print(
        f"\n[dim]yaygın{len(checkpoints)}anlık görüntüler|Yedekleme konumu: ~/.omc/backup/[/dim]"
    )


@app.command()
def restore(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="Proje yolu"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Onayı atla"),
):
    """Belirtilen Checkpoint'e geri dön (geri yükleme öncesi mevcut durum otomatik yedeklenir)"""
    cm = CheckpointManager(project_path=project_path)

    #İlk siz oluncheckpointbilgi
    cp = cm.get_checkpoint(checkpoint_id)
    if cp is None:
        console.print(f"[red]❌bulunamadıCheckpoint: {checkpoint_id}[/red]")
        raise typer.Exit(1)

    #onaylamak
    if not yes:
        console.print(
            f"[yellow]⚠️Aşağıdakileri geri alacakCheckpoint:[/yellow]\n"
            f"  ID:      {checkpoint_id}\n"
            f"Görev:    {cp.task_id}\n"
            f"betimlemek:    {cp.description}\n"
            f"Tüm çocukları listele:    {cp.file_count}bireysel\n"
            f"\n[yellow]Geçerli çalışma alanındaki değişiklik dosyaları otomatik olarak şuraya yedeklenecek:~/.omc/backup/[/yellow]"
        )
        confirm = typer.prompt("Geri alma onaylansın mı? girmek'yes'devam etmek", default="no")
        if confirm.lower() != "yes":
            console.print("[dim]İptal edildi[/dim]")
            raise typer.Exit(0)

    try:
        backup_path = cm.restore(checkpoint_id)
        console.print("[green]✅Geri alma başarılı![/green]")
        console.print(f"Anlık GörüntüID: {checkpoint_id}")
        console.print(f"Dosya sayısı:  {cp.file_count}bireysel")
        console.print(f"Mevcut durum şu tarihe kadar yedeklendi:: {backup_path}")
    except Exception as e:
        console.print(f"[red]❌Geri alma başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def diff(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="Proje yolu"),
):
    """Kontrol etmekCheckpointMevcut çalışma alanından farklılıklar"""
    cm = CheckpointManager(project_path=project_path)

    try:
        diff_result = cm.diff(checkpoint_id)
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]Checkpoint:[/bold cyan] {checkpoint_id}\n")
    console.print(cm.format_diff(diff_result))

    total_changes = (
        len(diff_result["added"])
        + len(diff_result["removed"])
        + len(diff_result["modified"])
    )
    console.print(f"\n[dim]yaygın{total_changes}her yerde değiş[/dim]")


@app.command()
def delete(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="Proje yolu"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Onayı atla"),
):
    """belirtileni silCheckpoint"""
    cm = CheckpointManager(project_path=project_path)

    if not cm.delete(checkpoint_id):
        console.print(f"[red]❌bulunamadıCheckpoint: {checkpoint_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]✅Silindi: {checkpoint_id}[/green]")


@app.command()
def info(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="Proje yolu"),
):
    """Kontrol etmekCheckpointDetaylar"""
    cm = CheckpointManager(project_path=project_path)

    cp = cm.get_checkpoint(checkpoint_id)
    if cp is None:
        console.print(f"[red]❌bulunamadıCheckpoint: {checkpoint_id}[/red]")
        raise typer.Exit(1)

    from rich.panel import Panel

    files = "\n".join(f"  • {e.path} ({e.size} B)" for e in cp.entries[:30])
    if len(cp.entries) > 30:
        files += f"\n  ...Ayrıca{len(cp.entries) - 30}dosyalar"

    panel = Panel(
        f"[bold]ID:[/bold]       {cp.id}\n"
        f"[bold]Görev:[/bold]     {cp.task_id}\n"
        f"[bold]betimlemek:[/bold]     {cp.description}\n"
        f"[bold]yaratmak:[/bold]     {cp.created_at}\n"
        f"[bold]belge:[/bold]     {cp.file_count}bireysel\n"
        f"[bold]boyut:[/bold]     {cp.total_size // 1024} KB\n"
        f"[bold]çalışma alanı:[/bold]  {cp.working_dir}\n\n"
        f"[bold]Yapılandırma dosyası bütünlüğü (:[/bold]\n{files}",
        title=f"Checkpoint: {checkpoint_id}",
        border_style="cyan",
    )
    console.print(panel)


@app.command()
def stats(
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="Proje yolu"),
):
    """Kontrol etmekCheckpointistatistikler"""
    cm = CheckpointManager(project_path=project_path)
    stats = cm.get_stats()

    console.print(
        f"[bold cyan]Checkpointistatistikler[/bold cyan]\n\n"
        f"Anlık görüntü sayısı:  {stats['total_checkpoints']}bireysel\n"
        f"toplam dosya sayısı:  {stats['total_files']}bireysel\n"
        f"toplam boyut:    {stats['total_size_bytes'] // 1024} KB\n"
        f"\n[dim]Yedekleme dizini: ~/.omc/backup/[/dim]"
    )
