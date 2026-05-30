from __future__ import annotations

from typing import Optional

"""
gorevtoplammodul - otomatikgorevtamamlasonraolusturyapitoplam

Islev:
- kayitis akisiyuruttumsurec
- istatistik Token tuketveol
- analiz Agent yurutdurum
- disa aktarcokturformat (JSON/TXT/HTML) 
- olusturaltkeziyioneri

kullansenaryo: 
1. gorevtamamlasonraotomatikolusturtoplamrapor
2. analiz Token tuket, iyiol
3. geribakis akisiyurutdurum
4. takimisbirligiyapzamanpaylasyurutme sonucu

kullanornek: 
    from src.core.summary import generate_summary, print_summary, save_summary

    # olusturtoplam
    summary = generate_summary(
        task="uygulakullanicikimlik dogrulamamodul",
        workflow="build",
        completed_steps=[...],
    )

    # yazdirkadarsonuc
    print_summary(summary)

    # kaydetkadardosya
    save_path = save_summary(summary, format="json")
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


# ============================================================
# sayigoremodel
# ============================================================
@dataclass
class StepRecord:
    """tekiladimyurutkayit"""

    agent: str
    status: str  # "completed" | "failed" | "skipped"
    duration: float  # saniye
    tokens: int = 0
    cost: float = 0.0
    result: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModelUsage:
    """tekilmodelcagriistatistik"""

    provider: str
    model_name: str
    calls: int = 0
    tokens: int = 0
    cost: float = 0.0


@dataclass
class TaskSummary:
    """
    gorevtoplamsayigoresinif

    Attributes:
        task: gorev aciklamasi
        workflow: is akisi adi (build/review/debug/test) 
        start_time: baslatzamanarasinda (ISO format) 
        end_time: bitirzamanarasinda (ISO format) 
        duration_seconds: toplamtuketzaman (saniye) 
        total_tokens: Token toplamtuket
        total_cost: toplamol (ogre) 
        steps_completed: tamamlaadimliste
        agent_count: ilgilive Agent sayimiktar
        models_used: kullanmodelliste
        success: olup olmadigitumkisimbasarili
        errors: hataliste
        recommendations: iyioneri
    """

    task: str
    workflow: str
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    steps_completed: list = field(default_factory=list)
    agent_count: int = 0
    models_used: list = field(default_factory=list)
    success: bool = True
    errors: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TaskSummary:
        return cls(**data)


# ============================================================
# toplamolustur
# ============================================================
def generate_summary(
    task: str,
    workflow: str,
    completed_steps: list[dict],
    project_path: str = "",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> TaskSummary:
    """
    goretamamlaadimolusturgorevtoplam

    Args:
        task: gorev aciklamasi
        workflow: is akisi adi
        completed_steps: adimliste, her dict icerir:
            - agent: Agent ad
            - status: durum (completed/failed/skipped) 
            - duration: tuketzaman (saniye) 
            - tokens: Token tuket
            - result: yurutme sonucuaciklama
            - error: hata mesaji (orneginvar) 
        project_path: proje yolu

    Returns:
        TaskSummary icinnesne
    """
    now = datetime.now()
    start = start_time or now
    end = end_time or now

    # donusturadim
    steps = []
    agents_used = set()
    total_tokens = 0
    total_cost = 0.0
    success = True
    errors = []

    for step_data in completed_steps:
        step = StepRecord(
            agent=step_data.get("agent", "unknown"),
            status=step_data.get("status", "unknown"),
            duration=step_data.get("duration", 0.0),
            tokens=step_data.get("tokens", 0),
            cost=step_data.get("cost", 0.0),
            result=step_data.get("result", ""),
            error=step_data.get("error", ""),
        )
        steps.append(step)

        agents_used.add(step.agent)
        total_tokens += step.tokens
        total_cost += step.cost

        if step.status != "completed":
            success = False
            if step.error:
                errors.append(f"{step.agent}: {step.error}")

    # tahminol (gore DeepSeek deger: ¥1/yuz10 bin Token) 
    if total_cost == 0 and total_tokens > 0:
        total_cost = total_tokens / 1_000_000 * 1.0

    # olusturiyioneri
    recommendations = _generate_recommendations(
        steps=steps,
        total_cost=total_cost,
        total_tokens=total_tokens,
        workflow=workflow,
    )

    # cikarimkullanmodel (basitsurum:  Agent isimcikarim) 
    models_used = _infer_models(workflow, len(agents_used))

    return TaskSummary(
        task=task,
        workflow=workflow,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        duration_seconds=(end - start).total_seconds(),
        total_tokens=total_tokens,
        total_cost=total_cost,
        steps_completed=[s.to_dict() for s in steps],
        agent_count=len(agents_used),
        models_used=models_used,
        success=success,
        errors=errors,
        recommendations=recommendations,
    )


def _generate_recommendations(
    steps: list[StepRecord],
    total_cost: float,
    total_tokens: int,
    workflow: str,
) -> list[str]:
    """olusturiyioneri"""
    recs = []

    # oloneri
    if total_cost > 1.0:
        recs.append("💡 olkiyasyuksek, dusunkullan DeepSeek-V4 (dusukol) islebasittekilgorev")
    elif total_cost > 0.1:
        recs.append("💡 mevcutoluygunicinde, devamdevamkoru")

    # Token oneri
    if total_tokens > 50000:
        recs.append("💡 Token tuketkiyasyuksek, olabilirdusunazaltazkesfetderinlikveyapuantoplucaisle")

    # yurutzamanarasindaoneri
    total_duration = sum(s.duration for s in steps)
    if total_duration > 60:
        recs.append("💡 yurutzamanarasindakiyasuzunluk, olabilirdusunvesatiryuruttekkuradim")

    # basarisizoneri
    failed_steps = [s for s in steps if s.status == "failed"]
    if failed_steps:
        recs.append(f"⚠️  {len(failed_steps)} adimbasarisiz, onerikontrolilgili Agent yapilandirma")

    if not recs:
        recs.append("✅ yurutetkioraniyiiyi, yokgerekozeliyi")

    return recs


def _infer_models(workflow: str, agent_count: int) -> list[str]:
    """cikarimkullanmodel"""
    if workflow == "build":
        return ["deepseek-chat", "deepseek-chat", "deepseek-chat"]
    if workflow == "review":
        return ["deepseek-chat"]
    if workflow == "debug":
        return ["deepseek-chat"]
    if workflow == "test":
        return ["deepseek-chat", "deepseek-chat"]
    return ["deepseek-chat"]


# ============================================================
# yazdirtoplam
# ============================================================
def print_summary(summary: TaskSummary) -> None:
    """icindesonucyazdirtoplam (kemerformat) """
    status_icon = "✅" if summary.success else "❌"

    print(f"\n{status_icon} gorev: {summary.task}")
    print(f"📋 is akisi: {summary.workflow}")
    print(f"⏱️  tuketzaman: {summary.duration_seconds:.1f}s")
    print(f"💰 ol: ¥{summary.total_cost:.4f}")
    print(f"🔢 Token: {summary.total_tokens:,}")
    print(f"🤖 Agent sayi: {summary.agent_count}")
    print(f"🔧 model: {', '.join(summary.models_used)}")

    if summary.steps_completed:
        print("\n📊 yurutadim: ")
        for i, step in enumerate(summary.steps_completed, 1):
            icon = (
                "✅"
                if step["status"] == "completed"
                else ("❌" if step["status"] == "failed" else "⏭️")
            )
            agent_short = step["agent"].replace("Agent", "")
            print(
                f"  {i}. {icon} {agent_short:<15} - {step['duration']:.1f}s"
                f" | {step['tokens']:,} tokens | {step['result'][:50]}..."
            )

    if summary.errors:
        print("\n❌ hata: ")
        for err in summary.errors:
            print(f"  • {err}")

    if summary.recommendations:
        print("\n💡 iyioneri: ")
        for rec in summary.recommendations:
            print(f"  {rec}")


def print_summary_compact(summary: TaskSummary) -> None:
    """kompaktsurumtoplam (tekilsatir) """
    status = "✅" if summary.success else "❌"
    print(
        f"{status} [{summary.workflow}] {summary.task[:40]} | "
        f"{summary.duration_seconds:.1f}s | "
        f"¥{summary.total_cost:.4f} | "
        f"{summary.agent_count} agents"
    )


# ============================================================
# kaydetileyukle
# ============================================================
def save_summary(
    summary: TaskSummary,
    output_dir: Optional[Path] = None,
    format: str = "json",
    filename: Optional[str] = None,
) -> Path:
    """
    kaydettoplamkadardosya

    Args:
        summary: toplamicinnesne
        output_dir: ciktidizin (varsayilan reports/) 
        format: format (json/txt/html) 
        filename: ozeldosyaisim

    Returns:
        kaydetdosyayol
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "reports"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # olusturdosyaisim
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_task = "".join(c if c.isalnum() else "_" for c in summary.task[:30])
        filename = f"summary_{summary.workflow}_{safe_task}_{timestamp}.{format}"

    filepath = output_dir / filename

    if format == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, ensure_ascii=False, indent=2)
    elif format == "txt":
        with open(filepath, "w", encoding="utf-8") as f:
            _write_txt_summary(f, summary)
    elif format == "html":
        with open(filepath, "w", encoding="utf-8") as f:
            _write_html_summary(f, summary)
    else:
        raise ValueError(f"hayirdestekformat: {format}")

    return filepath


def _write_txt_summary(f, summary: TaskSummary) -> None:
    """yazgiris TXT format"""
    f.write("gorevtoplam\n")
    f.write(f"{'=' * 50}\n")
    f.write(f"gorev: {summary.task}\n")
    f.write(f"is akisi: {summary.workflow}\n")
    f.write(f"durum: {'basarili' if summary.success else 'basarisiz'}\n")
    f.write(f"tuketzaman: {summary.duration_seconds:.1f}s\n")
    f.write(f"Token: {summary.total_tokens:,}\n")
    f.write(f"ol: ¥{summary.total_cost:.4f}\n")
    f.write("\nyurutadim:\n")
    for step in summary.steps_completed:
        f.write(f"  - {step['agent']}: {step['result']}\n")
    if summary.recommendations:
        f.write("\niyioneri:\n")
        for rec in summary.recommendations:
            f.write(f"  {rec}\n")


def _write_html_summary(f, summary: TaskSummary) -> None:
    """yazgiris HTML format"""
    status_color = "#4CAF50" if summary.success else "#F44336"
    f.write(
        f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>gorevtoplam - {summary.task[:30]}</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
h1 {{ color: #333; }}
.stat {{ display: inline-block; background: #f5f5f5; padding: 8px 16px; margin: 4px; border-radius: 4px; }}
.step {{ border-left: 3px solid #ddd; padding: 8px 16px; margin: 8px 0; }}
.step.success {{ border-color: #4CAF50; }}
.step.failed {{ border-color: #F44336; }}
.rec {{ background: #fff3cd; padding: 8px 16px; border-radius: 4px; margin: 4px 0; }}
</style>
</head>
<body>
<h1>📋 {summary.task}</h1>
<p>is akisi: <strong>{summary.workflow}</strong> |
   durum: <span style="color:{status_color}">{"✅ basarili" if summary.success else "❌ basarisiz"}</span></p>

<div class="stat">⏱️ {summary.duration_seconds:.1f}s</div>
<div class="stat">💰 ¥{summary.total_cost:.4f}</div>
<div class="stat">🔢 {summary.total_tokens:,} tokens</div>
<div class="stat">🤖 {summary.agent_count} agents</div>

<h2>yurutadim</h2>
"""
    )
    for step in summary.steps_completed:
        cls = "success" if step["status"] == "completed" else "failed"
        icon = "✅" if step["status"] == "completed" else "❌"
        f.write(
            f"""<div class="step {cls}">
<strong>{icon} {step["agent"]}</strong> ({step["duration"]:.1f}s)<br>
{step["result"]}
</div>
"""
        )
    if summary.recommendations:
        f.write("<h2>💡 iyioneri</h2>\n")
        for rec in summary.recommendations:
            f.write(f"<div class='rec'>{rec}</div>\n")
    f.write("</body></html>")


def load_summary(filepath: Path) -> TaskSummary:
    """dosyayukletoplam"""
    filepath = Path(filepath)
    if filepath.suffix == ".json":
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return TaskSummary.from_dict(data)
    raise ValueError(f"hayirdestekdosyaformat: {filepath.suffix}")


# ============================================================
# kullanislifonksiyon
# ============================================================
def quick_summary(
    task: str,
    workflow: str,
    duration: float,
    tokens: int,
    steps: list[str],
) -> TaskSummary:
    """
    hizlihizolusturbasittekiltoplam (kullandehayirgerekistertambilgisenaryo) 

    Args:
        task: gorev aciklamasi
        workflow: is akisi adi
        duration: toplamtuketzaman (saniye) 
        tokens: Token toplamtuket
        steps: adimaciklamaliste

    Returns:
        TaskSummary icinnesne
    """
    completed = [
        {
            "agent": f"Step{i + 1}",
            "status": "completed",
            "duration": 0,
            "tokens": 0,
            "result": s,
        }
        for i, s in enumerate(steps)
    ]
    return generate_summary(
        task=task,
        workflow=workflow,
        completed_steps=completed,
        start_time=datetime.now(),
        end_time=datetime.now(),
    )
