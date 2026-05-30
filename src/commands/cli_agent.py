from __future__ import annotations

"""
AgentYapılandırmaCLI -İhracat/içe aktarmak/üstesinden gelmekAgentYapılandırma

Emir:
- omc agent list              #Mevcut olanların hepsini listeleAgent
- omc agent show <name>       #göstermekAgentDetaylar
- omc agent export <name>     #İhracatAgentolarak yapılandırılmışJSON
- omc agent import <file>     #dosyadan içe aktarAgentYapılandırma
- omc agent evolve <name>     #tetiklemekAgentModel yapılandırmasını toplulukla paylaşın
- omc agent stats <name>      #göstermekAgentEvrimsel İstatistikler
"""


import contextlib
import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="AgentYapılandırma yönetimi")
console = Console()


@app.command("list")
def list_agents(
    monorepo: bool = typer.Option(
        False,
        "--monorepo",
        "-m",
        help="göstermekMonorepoÇıkış yolu (varsayılan olarak terminale yazdırılır)Agent",
    ),
):
    """Mevcut olanların hepsini listeleAgent"""
    from src.agents.base import list_all_agents

    agents = list_all_agents()

    table = Table(title="MevcutAgentliste")
    table.add_column("isim", style="cyan")
    table.add_column("betimlemek", style="white")
    table.add_column("Lane", style="yellow")
    table.add_column("varsayılanTier", style="green")

    for agent_info in agents:
        table.add_row(
            agent_info.get("name", ""),
            agent_info.get("description", "")[:50],
            agent_info.get("lane", ""),
            agent_info.get("default_tier", ""),
        )

    console.print(table)

    # Monorepoİzin kuralları dosyası
    if monorepo:
        from src.core.monorepo import detect_monorepo, list_subprojects

        info = detect_monorepo()
        if info is None:
            console.print("\n[yellow]⚠[/yellow]Geçerli dizin değilMonorepokök dizin")
            return

        console.print()
        subprojects = list_subprojects(info)
        if not subprojects:
            console.print("[dim]Hiçbir alt proje algılanmadı[/dim]")
            return

        pkg_table = Table(title=f"MonorepoAlt proje- {info.type}")
        pkg_table.add_column("proje", style="cyan")
        pkg_table.add_column("yol", style="dim")
        pkg_table.add_column("dil", style="yellow")
        pkg_table.add_column("çerçeve", style="green")
        pkg_table.add_column("AgentYapılandırma", style="magenta")

        for sp in subprojects:
            agent_status = "✓yapılandırılmış" if sp.has_agent_config else "-Yapılandırılmadı"
            rel_path = sp.path.relative_to(info.root)
            pkg_table.add_row(
                sp.name,
                str(rel_path),
                sp.language,
                sp.framework,
                agent_status,
            )

        console.print(pkg_table)
        console.print(
            f"\n[dim]yaygın{len(subprojects)}alt proje,"
            f"{sum(1 for sp in subprojects if sp.has_agent_config)}yapılandırılmışAgent[/dim]"
        )


@app.command("show")
def show_agent(
    name: str = typer.Argument(..., help="Agentisim"),
    evolution: bool = typer.Option(False, "--evolution", "-e", help="Evrim bilgilerini göster"),
):
    """göstermekAgentDetaylar"""
    from src.agents.base import get_agent

    agent_class = get_agent(name)
    if not agent_class:
        console.print(f"[red]Hata: bulunamadıAgent '{name}'[/red]")
        raise typer.Exit(1)

    #Bilgi almak için bir örnek oluşturun
    agent = agent_class()

    lane_str = agent.lane.value if hasattr(agent.lane, "value") else str(agent.lane)
    info = Panel(
        f"[bold]isim:[/bold] {agent.name}\n"
        f"[bold]betimlemek:[/bold] {agent.description}\n"
        f"[bold]Lane:[/bold] {lane_str}\n"
        f"[bold]varsayılanTier:[/bold] {agent.default_tier}\n"
        f"[bold]simge:[/bold] {agent.icon}\n"
        f"[bold]alet:[/bold] {', '.join(agent.tools) if agent.tools else 'hiçbiri'}\n\n"
        f"[bold]System Prompt:[/bold]\n{agent.system_prompt[:500]}...",
        title=f"Agent: {name}",
        border_style="cyan",
    )
    console.print(info)

    if evolution:
        from src.agents.self_improving import SelfImprovingAgent

        sia = SelfImprovingAgent()
        stats = sia.get_evolution_stats(name)

        evolution_info = Panel(
            f"[bold]güncel cebir:[/bold] {stats.get('current_generation', 1)}\n"
            f"[bold]Toplam evrim sayısı:[/bold] {stats.get('total_evolutions', 0)}\n"
            f"[bold]Mod sayısı:[/bold] {stats.get('total_patterns', 0)}\n"
            f"[bold]PromptSürüm:[/bold] {stats.get('prompt_version', 0)}\n"
            f"[bold]son evrim:[/bold] {stats.get('last_evolution', 'Henüz gelişmemiş')}",
            title="evrimsel bilgi",
            border_style="green",
        )
        console.print(evolution_info)


@app.command("export")
def export_agent(
    name: str = typer.Argument(..., help="Agentisim"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Çıkış dosyası yolu"),
    include_evolution: bool = typer.Option(
        False, "--evolution", "-e", help="Evrimsel tarih içerir"
    ),
    include_patterns: bool = typer.Option(
        False, "--patterns", "-p", help="Başarı Modeli Kitaplığını İçerir"
    ),
):
    """
İhracatAgentolarak yapılandırılmışJSON

Dışa aktarılan içerik şunları içerir:
    - AgentTemel yapılandırma (system prompt, model, sıcaklık vb.)
    -Evrimsel tarih (isteğe bağlı)
    -Başarı Modeli Kitaplığı (isteğe bağlı)
    """
    from src.agents.base import get_agent

    agent_class = get_agent(name)
    if not agent_class:
        console.print(f"[red]Hata: bulunamadıAgent '{name}'[/red]")
        raise typer.Exit(1)

    agent = agent_class()

    #Yapı yapılandırması
    config_data = {
        "name": agent.name,
        "description": agent.description,
        "model": getattr(agent, "model", "deepseek"),
        "tools": agent.tools,
        "lane": agent.lane.value if hasattr(agent.lane, "value") else str(agent.lane),
        "default_tier": agent.default_tier,
        "icon": agent.icon,
        "prompts": {
            "system": agent.system_prompt,
        },
        "environment": {
            "max_tokens": getattr(agent, "max_tokens", 8000),
            "temperature": getattr(agent, "temperature", 0.7),
            "timeout": getattr(agent, "timeout", 60),
        },
    }

    #İsteğe bağlı: evrimsel geçmişi dahil edin
    if include_evolution:
        from pathlib import Path

        from src.agents.evolution import EvolutionStore

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)
        history = store.load_evolution_history(name)
        config_data["evolution_history"] = [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "generation": r.generation,
                "changes": r.changes,
            }
            for r in history
        ]

    #Duruma göre filtrele
    if include_patterns:
        from pathlib import Path

        from src.agents.evolution import EvolutionStore

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)
        patterns = store.load_success_patterns(name)
        config_data["success_patterns"] = [
            {
                "id": p.id,
                "pattern_type": p.pattern_type,
                "description": p.description,
                "effectiveness_score": p.effectiveness_score,
            }
            for p in patterns
        ]

    #Çıkış yolunu belirleyin
    if output is None:
        output = Path(f"{name}-agent-config.json")

    #dosya yaz
    output.write_text(
        json.dumps(config_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] Agent '{name}'İstatistiksel özeti okuyun: {output}")
    console.print("  -Temel konfigürasyon: ✓")
    if include_evolution:
        console.print("  -evrim tarihi: ✓")
    if include_patterns:
        console.print("  -başarı modeli: ✓")


@app.command("import")
def import_agent(
    source: str = typer.Argument(..., help="Yapılandırma dosyası yolu veyaURL"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="yeniAgentisim"),
):
    """
dosyadan veyaURLiçe aktarmakAgentYapılandırma

Destek:
    -yerelJSONbelge
    - GitHub raw URL
    - HTTP/HTTPS URL
    """
    source_path: Optional[Path] = None
    config_data: dict[str, Any]

    #Karar şu:URLVeya yerel bir dosya
    if source.startswith(("http://", "https://")):
        #itibarenURLindirmek
        console.print("[cyan]Şuradan kaldırılıyor:URLYapılandırmayı indir...[/cyan]")
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(source)
                response.raise_for_status()
                config_data = response.json()
        except Exception as e:
            console.print(f"[red]İndirme başarısız oldu: {e}[/red]")
            raise typer.Exit(1)
        console.print("[green]✓[/green]Yapılandırma indirme işlemi başarılı")
    else:
        #yerel dosya
        source_path = Path(source)
        if not source_path.exists():
            console.print(f"[red]Hata: Dosya mevcut değil'{source}'[/red]")
            raise typer.Exit(1)

        try:
            config_data = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            console.print(f"[red]JSONAyrıştırma başarısız oldu: {e}[/red]")
            raise typer.Exit(1)

    #Destek
    required_fields = ["name", "description"]
    for field in required_fields:
        if field not in config_data:
            console.print(f"[red]Düşünce zinciri başladı'{field}'[/red]")
            raise typer.Exit(1)

    #Soyadını belirle
    final_name = name or config_data["name"]

    #Yapılandırmayı şuraya kaydet:.omc/agents/İçindekiler
    agents_dir = Path.home() / ".omc" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    config_file = agents_dir / f"{final_name}.json"
    config_data["name"] = final_name  #Adı güncelle

    config_file.write_text(
        json.dumps(config_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] Agent '{final_name}'Yapılandırma içe aktarıldı")
    console.print(f"Konum: {config_file}")

    #Evrimsel tarih dahil edilmişse şunu da kaydedin:
    if "evolution_history" in config_data:
        from src.agents.evolution import EvolutionRecord, EvolutionStore

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)

        for record_data in config_data["evolution_history"]:
            record = EvolutionRecord(
                id=record_data.get("id", ""),
                timestamp=record_data.get("timestamp", ""),
                agent_type=final_name,
                generation=record_data.get("generation", 1),
                trigger="imported",
                changes=record_data.get("changes", []),
            )
            store.save_evolution_record(record)

        console.print("  -Evrim geçmişi içe aktarıldı")

    #Başarı modelinin dahil edilmesi durumunda da tasarruf sağlar
    if "success_patterns" in config_data:
        from src.agents.evolution import EvolutionStore

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)

        for pattern_data in config_data["success_patterns"]:
            store.add_success_pattern(
                agent_name=final_name,
                pattern_type=pattern_data.get("pattern_type", "imported"),
                description=pattern_data.get("description", ""),
                context=pattern_data.get("context", ""),
            )

        console.print("  -Başarı modeli içe aktarıldı")


@app.command("evolve")
def evolve_agent(
    name: str = typer.Argument(..., help="Agentisim"),
    trigger: str = typer.Option("manual", "--trigger", "-t", help="Tetikleyici neden"),
):
    """manuel tetikAgentModel yapılandırmasını toplulukla paylaşın"""
    from src.agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    record = sia.evolve(name, trigger=trigger)

    if record:
        console.print(
            f"[green]✓[/green] Agent '{name}'İlkini tamamla{record.generation}Nesiller boyu evrim"
        )
        console.print(f"evrimID: {record.id}")
        console.print("değiştirmek:")
        for change in record.changes:
            console.print(f"    - {change}")
    else:
        console.print("[yellow]Evrim tetiklenmiyor (yetersiz örnek veya optimizasyona gerek yok)[/yellow]")


@app.command("stats")
def agent_stats(
    name: str = typer.Argument(..., help="Agentisim"),
):
    """göstermekAgentEvrimsel İstatistikler"""
    from src.agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    stats = sia.get_evolution_stats(name)

    table = Table(title=f"Agent '{name}'Evrimsel İstatistikler")
    table.add_column("dizin", style="cyan")
    table.add_column("değer", style="green")

    table.add_row("güncel cebir", str(stats.get("current_generation", 1)))
    table.add_row("Toplam evrim sayısı", str(stats.get("total_evolutions", 0)))
    table.add_row("Başarılı kalıpların sayısı", str(stats.get("total_patterns", 0)))
    table.add_row("PromptSürüm", str(stats.get("prompt_version", 0)))
    table.add_row("son evrim", stats.get("last_evolution", "Henüz gelişmemiş"))
    table.add_row("Kişisel gelişim etkin", str(stats.get("config", {}).get("enabled", True)))
    table.add_row(
        "Eşiği geliştirin", f"{stats.get('config', {}).get('improvement_threshold', 0.8):.0%}"
    )

    console.print(table)


# ------------------------------------------------------------------
#Sürüm yineleme belleği-şuraya kaydedildi:
# ------------------------------------------------------------------


@app.command("decisions")
def list_decisions(
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Kategoriye göre filtrele(bug_fix/solution_choice/rejection/architecture)",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Ekran miktarı"),
):
    """Geçmiş karar kayıtlarını listeleyin"""
    from src.agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    decisions = sia.list_decisions(category=category, limit=limit)

    if not decisions:
        console.print("[yellow]Henüz karar kaydı yok[/yellow]")
        return

    table = Table(title="Tarihsel karar kaydı")
    table.add_column("ID", style="cyan", width=25)
    table.add_column("başlık", style="white")
    table.add_column("kategori", style="yellow")
    table.add_column("sonuç", style="green")
    table.add_column("alt komut", style="dim", width=40)

    for d in decisions:
        table.add_row(
            d["id"],
            d["title"],
            d["category"],
            d["result"],
            d["problem"],
        )

    console.print(table)
    console.print("\n[dim]kullanmak'omc agent decision <Sorun açıklaması>'İlgili kararları alın[/dim]")


@app.command("decision")
def retrieve_decision(
    problem: str = typer.Argument(..., help="Benzer kararların alınmasına ilişkin problem tanımı"),
    limit: int = typer.Option(3, "--limit", "-n", help="İade miktarı"),
):
    """Tekrarlanan hatalardan kaçınmak için geçmiş kararları alın"""
    from src.agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    decisions = sia.retrieve_past_decisions(problem, limit=limit)

    if not decisions:
        console.print("[yellow]İlgili karar kaydı bulunamadı[/yellow]")
        console.print("[dim]kullanmak'omc agent record-decision'Yeni kararları kaydedin[/dim]")
        return

    console.print(f"[cyan]açmak{len(decisions)}İlgili kararlar:[/cyan]\n")

    for i, d in enumerate(decisions, 1):
        panel = Panel(
            f"**alt komut**: {d['problem']}\n\n"
            f"**çözüm**: {d['chosen_solution']}\n\n"
            f"**sonuç**: {d['result']}\n\n"
            f"**Etki**: {d.get('outcome', 'N/A')}\n\n"
            f"**Uygulanabilir senaryolar**: {d.get('reusable_for', 'N/A')}\n\n"
            f"**anahtar kelimeler**: {', '.join(d.get('keywords', []))}",
            title=f"{i}. {d['title']}",
            border_style="cyan",
        )
        console.print(panel)


@app.command("record-decision")
def record_decision(
    title: str = typer.Option(..., "--title", "-t", help="Karar başlığı"),
    problem: str = typer.Option(..., "--problem", "-p", help="Karşılaşılan sorunlar"),
    solution: str = typer.Option(..., "--solution", "-s", help="Seçilen çözüm"),
    category: str = typer.Option(
        "solution_choice", "--category", "-c", help="Karar Kategorisi"
    ),
    result: str = typer.Option(
        "success", "--result", "-r", help="sonuç(success/failure)"
    ),
    outcome: str = typer.Option("", "--outcome", "-o", help="Efekt açıklaması"),
    reusable_for: str = typer.Option("", "--reusable-for", help="Uygulanabilir senaryolar"),
):
    """Önemli kararları kaydedin"""
    from src.agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    decision_id = sia.record_decision(
        title=title,
        problem=problem,
        chosen_solution=solution,
        category=category,
        result=result,
        outcome=outcome,
        reusable_for=reusable_for,
    )

    console.print(f"[green]✓[/green]Karar kaydedildi: {decision_id}")


@app.command("decision-stats")
def decision_stats():
    """Karar hafızası istatistiklerini göster"""
    from src.agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    stats = sia.get_decision_stats()

    table = Table(title="Karar Hafızası İstatistikleri")
    table.add_column("dizin", style="cyan")
    table.add_column("değer", style="green")

    table.add_row("toplam karar sayısı", str(stats.get("total_decisions", 0)))
    table.add_row("Son kararlar", stats.get("latest_decision", "hiçbiri"))

    category_data = stats.get("by_category", {})
    if category_data:
        table.add_row(
            "kategoriye göre", ", ".join(f"{k}: {v}" for k, v in category_data.items())
        )

    console.print(table)


@app.command("health")
def agent_health(
    show_logs: bool = typer.Option(
        False, "--logs", "-l", help="Ayrıca son yeniden tahsis günlüklerini de görüntüler"
    ),
):
    """Tümünü gösterAgentsağlık durumu (oku.omc/state/health/İçindekiler)"""
    from pathlib import Path

    from src.agents.health_check import format_health_display

    state_dir = Path.cwd() / ".omc" / "state" / "health"

    if not state_dir.exists():
        console.print("[yellow]Sağlık kontrolü kaydı yok (iş akışı henüz yürütülmedi)[/yellow]")
        return

    #Tüm sağlık kayıtlarını okuyun
    health_files = sorted(state_dir.glob("health_*.json"))
    health_map: dict[str, dict] = {}

    import json

    for f in health_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            name = data.get("agent_name", f.stem.replace("health_", ""))
            health_map[name] = data
        except Exception:
            pass

    #İstatistiksel özeti okuyun
    status_file = state_dir / "status.json"
    summary: dict = {}
    if status_file.exists():
        with contextlib.suppress(Exception):
            summary = json.loads(status_file.read_text(encoding="utf-8"))

    #Özeti yazdır
    if summary:
        summary_table = Table(title="Durum Kontrolü Özeti", show_header=False)
        summary_table.add_column("dizin", style="cyan")
        summary_table.add_column("değer", style="green")
        summary_table.add_row("toplam kayıtAgent", str(summary.get("total_registered", 0)))
        summary_table.add_row("✅ Healthy", str(summary.get("healthy", 0)))
        summary_table.add_row("⚠️  Stale", str(summary.get("stale", 0)))
        summary_table.add_row("❌ Failed", str(summary.get("failed", 0)))
        summary_table.add_row("🔄Yeniden tahsis edildi", str(summary.get("total_reassignments", 0)))
        summary_table.add_row("Koşma", str(summary.get("running", 0)))
        summary_table.add_row("Kontrol aralığı", f"{summary.get('check_interval', 60):.0f}s")
        summary_table.add_row("zaman aşımı eşiği", f"{summary.get('stale_threshold', 300):.0f}s")
        summary_table.add_row("Maksimum yeniden deneme sayısı", str(summary.get("max_retries", 3)))
        console.print(summary_table)
        console.print()

    #Her birini yazdırAgentdurum
    if health_map:
        console.print("[bold cyan]AgentSağlık durumu:[/bold cyan]")
        display = format_health_display(health_map)
        console.print(display)
    else:
        console.print("[yellow]Henüz aktif değilAgentTüm öneri formlarını göster[/yellow]")

    #model cevap
    if show_logs:
        reassign_files = sorted(state_dir.glob("reassignment_*.json"))[-5:]
        if reassign_files:
            console.print("\n[bold yellow]Son yeniden tahsis kayıtları:[/bold yellow]")
            for f in reassign_files:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    ts = data.get("timestamp", "")
                    console.print(
                        f"  [{ts}] {data.get('from_agent')} → {data.get('to_agent')}"
                        f"  | step: {data.get('step')} | reason: {data.get('reason')}"
                    )
                except Exception:
                    pass


# ------------------------------------------------------------------
# AgentDurum kalıcılığı komutları
# ------------------------------------------------------------------


@app.command("save")
def save_agent(
    name: str = typer.Argument(..., help="Agentisim"),
    model: str = typer.Option("deepseek", "--model", "-m", help="Modeli"),
    description: str = typer.Option("", "--description", "-d", help="betimlemek"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="İhracatJSONbelge"
    ),
):
    """
kaydetmekAgentiçin yapılandırılmış~/.oh-my-coder/agents/<name>/

İçeriği kaydet:
    - config.json: AgentYapılandırma anlık görüntüsü
    - state.json:Çalışma zamanı durumu (session_id, tokensBeklemek)
    """
    from src.agents.persistence.store import AgentConfig, AgentState, AgentStateStore

    store = AgentStateStore()

    #Yapılandırma oluştur
    config = AgentConfig(
        name=name,
        description=description,
        model=model,
    )

    #Başlangıç ​​durumu oluştur
    state = AgentState(
        agent_name=name,
        session_id=f"sess-{int(time.time())}",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )

    #diske kaydet
    agent_dir = store.save(name, config, state=state)

    console.print(f"[green]✓[/green] Agent '{name}'şuraya kaydedildi:: {agent_dir}")

    #Belirtilmişseoutputve aynı anda ihracat
    if output:
        store.export_agent(name, output, include_history=False)
        console.print(f"[green]✓[/green]İstatistiksel özeti okuyun: {output}")


@app.command("restore")
def restore_agent(
    name: str = typer.Argument(..., help="Agentisim"),
    show_history: bool = typer.Option(False, "--history", "-h", help="Konuşma geçmişini göster"),
):
    """
itibaren~/.oh-my-coder/agents/<name>/iyileşmekAgentdurum

doğrulamak
    - config.json → AgentYapılandırma
    - history.jsonl →Konuşma geçmişi (isteğe bağlı yükleme)
    - state.json →çalışma zamanı durumu
    """
    from src.agents.persistence.store import AgentStateStore

    store = AgentStateStore()
    config, history, state = store.restore(name, include_history=show_history)

    if config is None:
        console.print(f"[red]hata:Agent '{name}'bulunamadı[/red]")
        raise typer.Exit(1)

    #Kurtarma bilgilerini göster
    info_lines = [
        f"[bold]isim:[/bold] {config.name}",
        f"[bold]betimlemek:[/bold] {config.description}",
        f"[bold]Modeli:[/bold] {config.model}",
        f"[bold]Lane:[/bold] {config.lane}",
        f"[bold]alet:[/bold] {', '.join(config.tools) if config.tools else 'hiçbiri'}",
    ]

    if state:
        info_lines.extend(
            [
                f"[bold]Session ID:[/bold] {state.session_id}",
                f"[bold]toplamTokens:[/bold] {state.total_tokens:,}",
                f"[bold]var olmak,:[/bold] ¥{state.total_cost:.4f}",
                f"[bold]son görev:[/bold] {state.last_task or 'hiçbiri'}",
            ]
        )

    console.print(
        Panel("\n".join(info_lines), title=f"📦 Agent: {name}", border_style="cyan")
    )

    if show_history and history:
        console.print(f"\n[cyan]Konuşma geçmişi({len(history)}şerit):[/cyan]")
        for _i, entry in enumerate(history[-10:], 1):
            role_color = "green" if entry.role == "user" else "yellow"
            console.print(
                f"  [{role_color}]{entry.role}[/{role_color}] {entry.content[:60]}..."
            )


@app.command("export-state")
def export_agent_state(
    name: str = typer.Argument(..., help="Agentisim"),
    output: Path = typer.Argument(..., help="çıktıJSONdosya yolu"),
    include_history: bool = typer.Option(False, "--history", "-h", help="Konuşma geçmişini içerir"),
    max_history: int = typer.Option(
        100, "--max-history", "-n", help="Dışa aktarılan maksimum geçmiş öğesi sayısı"
    ),
):
    """
İhracatAgenttek kişilikJSONDosya (paylaşılabilir)

İçeriği dışa aktar:
    - AgentYapılandırma
    -çalışma zamanı durumu
    -Konuşma geçmişi (isteğe bağlı)
    """
    from src.agents.persistence.store import AgentStateStore

    store = AgentStateStore()

    try:
        store.export_agent(
            name, output, include_history=include_history, max_history=max_history
        )
        console.print(f"[green]✓[/green] Agent '{name}'Şuraya aktarıldı:: {output}")
        if include_history:
            console.print("[dim](Konuşma geçmişini içerir)[/dim]")
    except FileNotFoundError:
        console.print(f"[red]hata:Agent '{name}'bulunamadı[/red]")
        raise typer.Exit(1)


@app.command("import-state")
def import_agent_state(
    source: Path = typer.Argument(..., help="JSONYapılandırma dosyası yolu"),
    new_name: Optional[str] = typer.Option(None, "--name", "-n", help="yeniAgentisim"),
    merge_history: bool = typer.Option(False, "--merge", help="Üzerine yazmak yerine geçmişi birleştir"),
):
    """
itibarenJSONDosya içe aktarmaAgentYapılandırma

Destek:
    -yerelJSONbelge
    -İçe aktarıldıktan sonra çalışır duruma getirilebilirAgent
    """
    from src.agents.persistence.store import AgentStateStore

    if not source.exists():
        console.print(f"[red]Hata: Dosya mevcut değil'{source}'[/red]")
        raise typer.Exit(1)

    store = AgentStateStore()

    try:
        imported_name = store.import_agent(
            source, new_name=new_name, merge_history=merge_history
        )
        console.print(f"[green]✓[/green] Agent '{imported_name}'İthal")
        console.print(f"Konum: {store.store_root / imported_name}")
    except Exception as e:
        console.print(f"[red]İçe aktarma başarısız oldu: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-saved")
def list_saved_agents():
    """Kaydedilenlerin tümünü listeleAgent"""
    from src.agents.persistence.store import AgentStateStore

    store = AgentStateStore()
    saved = store.list_saved()

    if not saved:
        console.print("[dim]Henüz hiçbiri kaydedilmediAgent[/dim]")
        console.print(
            "\n[dim]kullanmak[green]omc agent save <name>[/green]kaydetmekAgent[/dim]"
        )
        return

    table = Table(title="kaydedildiAgent")
    table.add_column("isim", style="cyan")
    table.add_column("yol", style="dim")

    for name in sorted(saved):
        table.add_row(name, str(store.store_root / name))

    console.print(table)

    #istatistikleri göster
    stats = store.get_stats()
    console.print(
        f"\n[dim]yaygın{stats['total_agents']}bireyselAgentişgal etmek{stats['total_size_bytes']}bayt[/dim]"
    )


@app.command("delete-saved")
def delete_saved_agent(
    name: str = typer.Argument(..., help="Agentisim"),
    force: bool = typer.Option(False, "--force", "-f", help="Zorunlu silme, onay yok"),
):
    """Kaydedilenleri silAgentdurum"""
    from src.agents.persistence.store import AgentStateStore

    store = AgentStateStore()

    if name not in store.list_saved():
        console.print(f"[red]hata:Agent '{name}'bulunamadı[/red]")
        raise typer.Exit(1)

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"Silmeyi onaylaAgent '{name}'?"):
            console.print("[dim]İptal edildi[/dim]")
            raise typer.Exit(0)

    if store.delete(name):
        console.print(f"[green]✓[/green] Agent '{name}'Silindi")
    else:
        console.print("[red]Silinemedi[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
