"""
Profile izole - alt Agent baglamizoleyonet

cozyerineolabilirsatirvb.alt agent baglamkirliliksorun: 
- heralt agent vartekkur profile (hafiza/teknikedebilir/egilimiyi) 
- ana session vealt session baglamizole
- alt agent sadeceedebilirerisimkendi profile, hayiredebilirokuyazana session hafiza
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

PROFILES_DIR = Path.home() / ".omc" / "profiles"


@dataclass
class AgentProfile:
    """Agent Profile - izolebaglamkapasite"""

    agent_id: str
    agent_name: str
    created_at: str
    # izolehafiza (sadeceicerirbu agent ilgili) 
    memories: list[str] = field(default_factory=list)
    # bu agent olabilirkullanteknikedebilir
    skills: list[str] = field(default_factory=list)
    # bu agent egilimiyiayarlaayar
    preferences: dict = field(default_factory=dict)
    # yurutgecmis (sadecekayitbu agent gorev) 
    task_history: list[dict] = field(default_factory=list)
    # ustseviye profile (kullandedevamustlen) 
    parent_profile: Optional[str] = None


class ProfileManager:
    """Profile yonet"""

    def __init__(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def create_profile(
        self,
        agent_id: str,
        agent_name: str,
        parent_profile: Optional[str] = None,
    ) -> AgentProfile:
        """olusturyeni agent profile"""
        profile = AgentProfile(
            agent_id=agent_id,
            agent_name=agent_name,
            created_at=datetime.now().isoformat(),
            parent_profile=parent_profile,
        )
        self._save_profile(profile)
        return profile

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """al agent profile"""
        filepath = PROFILES_DIR / f"{agent_id}.json"
        if not filepath.exists():
            return None

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return AgentProfile(**data)
        except Exception:
            return None

    def update_profile(self, profile: AgentProfile) -> None:
        """guncelle profile"""
        self._save_profile(profile)

    def add_memory(self, agent_id: str, memory: str) -> bool:
        """yon profile eklehafiza (izoledepolama) """
        profile = self.get_profile(agent_id)
        if not profile:
            return False

        profile.memories.append(f"[{datetime.now().isoformat()}] {memory}")
        # sinirhafizasayimiktar, sismeyi onle
        if len(profile.memories) > 100:
            profile.memories = profile.memories[-100:]

        self._save_profile(profile)
        return True

    def add_task(self, agent_id: str, task: str, status: str) -> bool:
        """kayitgorevyurutgecmis"""
        profile = self.get_profile(agent_id)
        if not profile:
            return False

        profile.task_history.append(
            {
                "task": task[:200],
                "status": status,
                "timestamp": datetime.now().isoformat(),
            }
        )
        # sinirgecmissayimiktar
        if len(profile.task_history) > 50:
            profile.task_history = profile.task_history[-50:]

        self._save_profile(profile)
        return True

    def get_context_for_agent(self, agent_id: str) -> dict:
        """
        al agent izolebaglam (kullandeiletiletveralt agent) 

        sadeceicerir: 
        - bu agent hafiza
        - bu agent teknikedebilir
        - bu agent egilimiyi
        - enyakingorevgecmis

        hayiricerir: 
        - ana session hafiza
        - onuno agent baglam
        """
        profile = self.get_profile(agent_id)
        if not profile:
            return {}

        return {
            "agent_name": profile.agent_name,
            "memories": profile.memories[-20:],  # enyakin 20 ogrehafiza
            "skills": profile.skills,
            "preferences": profile.preferences,
            "recent_tasks": profile.task_history[-10:],  # enyakin 10 gorev
        }

    def list_profiles(self) -> list[AgentProfile]:
        """tumunu listelevar profiles"""
        profiles = []
        for filepath in sorted(PROFILES_DIR.glob("*.json")):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                profiles.append(AgentProfile(**data))
            except Exception:
                continue
        return profiles

    def delete_profile(self, agent_id: str) -> bool:
        """sil profile"""
        filepath = PROFILES_DIR / f"{agent_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def _save_profile(self, profile: AgentProfile) -> None:
        """kaydet profile kadardosya"""
        filepath = PROFILES_DIR / f"{profile.agent_id}.json"
        filepath.write_text(
            json.dumps(asdict(profile), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ===== ontanim Profile =====

PREDEFINED_PROFILES = {
    "daikexing": {
        "name": "yerineolabilirsatir",
        "skills": ["simple_research", "single_file_edit", "doc_generation"],
        "preferences": {
            "max_steps_per_task": 5,
            "max_files_per_batch": 2,
            "build_after_edit": True,
            "timeout_minutes": 15,
            "suitable_for": [
                "dokumantasyonayararastir",
                "tekildosyabasittekildegistir",
                "kodformat",
            ],
            "not_suitable_for": [
                "cokdosyayeniden duzenleme",
                "tekrarkarisikmantikuygula",
                "mimari tasarim",
            ],
        },
    },
    "code_reviewer": {
        "name": "kodincelemeuye",
        "skills": ["security_audit", "style_check", "best_practices"],
        "preferences": {
            "focus_areas": ["security", "performance", "readability"],
            "severity_levels": ["critical", "warning", "suggestion"],
        },
    },
    "test_writer": {
        "name": "testissurecuzman",
        "skills": ["unit_test", "integration_test", "coverage_analysis"],
        "preferences": {
            "test_framework": "pytest",
            "min_coverage": 80,
        },
    },
}


def create_predefined_profile(agent_type: str) -> Optional[AgentProfile]:
    """olusturontanim profile"""
    if agent_type not in PREDEFINED_PROFILES:
        return None

    config = PREDEFINED_PROFILES[agent_type]
    manager = ProfileManager()

    profile = manager.create_profile(
        agent_id=f"{agent_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        agent_name=config["name"],
    )
    profile.skills = config["skills"]
    profile.preferences = config["preferences"]
    manager.update_profile(profile)

    return profile


def get_profile_summary(agent_id: str) -> str:
    """al profile alintiister (kullandehata ayikla) """
    manager = ProfileManager()
    profile = manager.get_profile(agent_id)

    if not profile:
        return f"Profile not found: {agent_id}"

    return (
        f"Agent: {profile.agent_name} ({profile.agent_id})\n"
        f"Created: {profile.created_at}\n"
        f"Memories: {len(profile.memories)}\n"
        f"Tasks: {len(profile.task_history)}\n"
        f"Skills: {', '.join(profile.skills) or 'None'}\n"
    )
