"""
Skill biriktirkapali dongu - gorevyuruticindecikarolabilirtekrarkullan Skill

akis: gorevtamamla → yansima → olustur Skill oneri → kullanicionayla → kaydet
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

SKILL_PROPOSALS_DIR = Path.home() / ".omc" / "skill-proposals"


@dataclass
class SkillProposal:
    """Skill oneri"""

    id: str
    title: str
    description: str
    trigger: str  # tetikgonderkosul
    steps: list[str]  # yurutadim
    source_task: str  # kaynakgorev
    created_at: str
    status: str = "pending"  # pending / accepted / rejected


def extract_skill_from_task(
    task_description: str,
    execution_steps: list[str],
    reflections: list[str],
) -> Optional[SkillProposal]:
    """
    gorevyuruticindecikar Skill oneri

    Args:
        task_description: hamgorev aciklamasi
        execution_steps: yurutadimliste
        reflections: yansimakayit

    Returns:
        SkillProposal veya None (egerhayirdegercikar) 
    """
    # karar verolup olmadigivarcikardegerdeger
    if not _is_worth_extracting(task_description, execution_steps, reflections):
        return None

    # olustur Skill icerik
    title = _generate_title(task_description)
    trigger = _generate_trigger(task_description)
    steps = _generate_steps(execution_steps, reflections)
    description = _generate_description(title, steps)

    proposal = SkillProposal(
        id=f"proposal-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        title=title,
        description=description,
        trigger=trigger,
        steps=steps,
        source_task=task_description[:100],
        created_at=datetime.now().isoformat(),
    )

    return proposal


def save_proposal(proposal: SkillProposal) -> Path:
    """kaydet Skill onerikadardosya"""
    SKILL_PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

    filepath = SKILL_PROPOSALS_DIR / f"{proposal.id}.json"
    filepath.write_text(
        json.dumps(asdict(proposal), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return filepath


def list_proposals() -> list[SkillProposal]:
    """tumunu listelevarbekleisle Skill oneri"""
    proposals = []

    if not SKILL_PROPOSALS_DIR.exists():
        return proposals

    for filepath in sorted(SKILL_PROPOSALS_DIR.glob("proposal-*.json")):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            proposals.append(SkillProposal(**data))
        except Exception:
            continue

    return proposals


def accept_proposal(proposal_id: str) -> Optional[Path]:
    """
    baglanal Skill oneri, olustur SKILL.md dosya

    Returns:
        olustur SKILL.md yol
    """
    proposal = _find_proposal(proposal_id)
    if not proposal:
        return None

    # guncelledurum
    proposal.status = "accepted"
    save_proposal(proposal)

    # olustur SKILL.md
    skill_content = _generate_skill_md(proposal)

    skills_dir = Path.home() / ".omc" / "skills" / proposal.id
    skills_dir.mkdir(parents=True, exist_ok=True)

    skill_path = skills_dir / "SKILL.md"
    skill_path.write_text(skill_content, encoding="utf-8")

    return skill_path


def reject_proposal(proposal_id: str) -> bool:
    """reddet Skill oneri"""
    proposal = _find_proposal(proposal_id)
    if not proposal:
        return False

    proposal.status = "rejected"
    save_proposal(proposal)
    return True


# ===== icindekisimfonksiyon =====


def _is_worth_extracting(
    task_description: str,
    execution_steps: list[str],
    reflections: list[str],
) -> bool:
    """karar vergorevolup olmadigidegercikaricin Skill"""
    # adimcokazhayirdeger
    if len(execution_steps) < 3:
        return False

    # kontrololup olmadigivarkullananahtar kelime
    generic_keywords = [
        "olustur",
        "olustur",
        "yapilandirma",
        "ayarlaayar",
        "kurulum",
        "kisimyerlestir",
        "kontrol",
        "duzeltme",
        "iyi",
        "yeniden duzenleme",
        "test",
        "dokumantasyon",
        "baslat",
        "esitle",
        "guncelle",
        "temizle",
    ]

    task_lower = task_description.lower()
    has_generic = any(kw in task_lower for kw in generic_keywords)

    # kontrolyansimaicindeolup olmadigivaryuzdegerlendirdeger
    positive_indicators = ["basarili", "tamamla", "varetki", "dogru", "duzgun", "✅"]
    has_positive = any(
        any(ind in ref for ind in positive_indicators) for ref in reflections
    )

    return has_generic and has_positive


def _generate_title(task_description: str) -> str:
    """olustur Skill baslik"""
    # cikarhareketkelime + isimkelime
    patterns = [
        r"(?:uygula|olustur|olustur|yapilandirma|ayarlaayar|kurulum|kisimyerlestir|kontrol|duzeltme|iyi|yeniden duzenleme|test|dokumantasyon)\s*(.+?)(?:\s*[--]|$)",
        r"(.+?)(?:|)(?:uygula|olustur|olustur|yapilandirma|ayarlaayar|kurulum|kisimyerlestir|kontrol|duzeltme|iyi|yeniden duzenleme|test|dokumantasyon)",
    ]

    for pattern in patterns:
        match = re.search(pattern, task_description)
        if match:
            return match.group(1).strip()[:50]

    # yedek: alonce 30 karakter
    if len(task_description) > 30:
        return task_description[:30] + "..."
    return task_description


def _generate_trigger(task_description: str) -> str:
    """olusturtetikgonderkosul"""
    # cikaranahtar kelimeyapicintetikgonderkosul
    keywords = []
    trigger_keywords = [
        "olustur",
        "olustur",
        "yapilandirma",
        "ayarlaayar",
        "kurulum",
        "kisimyerlestir",
        "kontrol",
        "duzeltme",
        "iyi",
        "yeniden duzenleme",
        "test",
        "dokumantasyon",
        "baslat",
        "esitle",
        "guncelle",
        "temizle",
    ]

    for kw in trigger_keywords:
        if kw in task_description:
            keywords.append(kw)

    if keywords:
        return f"ne zamankullanicigerekister{'/'.join(keywords[:3])}zaman"

    return "ne zamankullanicivarsinifbenzergerekistezaman"


def _generate_steps(execution_steps: list[str], reflections: list[str]) -> list[str]:
    """olusturstandartadim"""
    # yinelenenleri kaldirvebasitadim
    simplified = []
    seen = set()

    for step in execution_steps:
        # kaldiraraçdosyaisim, yolvb.incebolum
        generalized = _generalize_step(step)
        if generalized and generalized not in seen:
            seen.add(generalized)
            simplified.append(generalized)

    # ekleyansimaicindedegistirilerleoneri
    for reflection in reflections:
        if any(kw in reflection for kw in ["oneri", "degistirilerle", "iyi", "altkez"]):
            tip = f"💡 {reflection[:100]}"
            if tip not in seen:
                simplified.append(tip)

    return simplified[:10]  # en fazla 10 adim


def _generalize_step(step: str) -> str:
    """araçadimgenel"""
    # kaldiraraçyol
    step = re.sub(r"/[\w/\-.]+", "<yol>", step)
    # kaldiraraçdosyaisim
    step = re.sub(r"\b[\w\-]+\.(py|js|ts|html|css|md|json|yaml|yml)\b", "<dosya>", step)
    # kaldiraraçzamanarasinda
    step = re.sub(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?", "<zamanarasinda>", step)
    # kaldir commit hash
    step = re.sub(r"\b[0-9a-f]{7,40}\b", "<commit>", step)

    return step.strip()


def _generate_description(title: str, steps: list[str]) -> str:
    """olustur Skill aciklama"""
    return f"'{title}' gorevini otomatik isle, {len(steps)} standart adim icerir."


def _find_proposal(proposal_id: str) -> Optional[SkillProposal]:
    """arabelirtoneri"""
    filepath = SKILL_PROPOSALS_DIR / f"{proposal_id}.json"
    if not filepath.exists():
        return None

    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return SkillProposal(**data)
    except Exception:
        return None


def _generate_skill_md(proposal: SkillProposal) -> str:
    """olustur SKILL.md icerik"""
    steps_md = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(proposal.steps))

    return f"""# {proposal.title}

## aciklama

{proposal.description}

## tetikgonderkosul

{proposal.trigger}

## yurutadim

{steps_md}

## kaynak

- hamgorev: {proposal.source_task}
- cikarzamanarasinda: {proposal.created_at}

---

*tarafindan Oh My Coder otomatikcikar*
"""
