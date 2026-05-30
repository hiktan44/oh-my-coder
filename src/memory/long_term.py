from __future__ import annotations

"""
uzunlukdonemhafiza - projeegilimiyi, sikkullanmod

depolama: 
- projeogrebilgi (ad, dil, iskelet) 
- kullaniciegilimiyi (modelsecsec, is akisi, Agent yapilandirma) 
- sikkullankomutmod
- projeozelbiltani (API uc nokta, veritabaniyapivb.) 

tasarim: 
- JSON formatkalici
- goreprojeizole (project_path yapicin key) 
- destekmanuelguncelle + otomatikogrenogren
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ProjectPreference:
    """projeegilimiyi"""

    project_path: str
    name: str = ""
    language: str = ""  # python, go, rust, etc.
    framework: str = ""  # django, react, etc.
    default_model: str = "deepseek"
    default_workflow: str = "build"
    preferred_agents: list[str] = field(default_factory=list)
    custom_commands: dict[str, str] = field(default_factory=dict)  # alias -> command
    notes: str = ""  # projenot
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectPreference:
        return cls(**data)


@dataclass
class UserPreference:
    """kullaniciglobalegilimiyi"""

    user_id: str = "default"
    default_model: str = "deepseek"
    default_workflow: str = "build"
    notification_enabled: bool = True
    theme: str = "auto"  # auto, light, dark
    editor: str = "code"  # vscode, vim, nano
    shell: str = "bash"
    api_keys: dict[str, str] = field(default_factory=dict)  # model -> key
    recent_projects: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPreference:
        return cls(**data)


class LongTermMemory:
    """uzunlukdonemhafizayonet"""

    def __init__(self, storage_dir: Path):
        """
        Args:
            storage_dir: depolamadizin
        """
        self.storage_dir = storage_dir / "long-term"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.user_prefs_file = self.storage_dir / "user_preferences.json"
        self.projects_file = self.storage_dir / "projects.json"
        self._user_prefs: Optional[UserPreference] = None
        self._projects: dict[str, ProjectPreference] = {}

    def _load_projects(self) -> dict[str, ProjectPreference]:
        """yukleprojeegilimiyi"""
        if self._projects:
            return self._projects

        if self.projects_file.exists():
            data = json.loads(self.projects_file.read_text())
            self._projects = {
                k: ProjectPreference.from_dict(v) for k, v in data.items()
            }
        return self._projects

    def _save_projects(self):
        """kaydetprojeegilimiyi"""
        data = {k: v.to_dict() for k, v in self._projects.items()}
        self.projects_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def get_user_prefs(self) -> UserPreference:
        """alkullaniciegilimiyi"""
        if self._user_prefs is not None:
            return self._user_prefs

        if self.user_prefs_file.exists():
            data = json.loads(self.user_prefs_file.read_text())
            self._user_prefs = UserPreference.from_dict(data)
        else:
            self._user_prefs = UserPreference()
            self._save_user_prefs()
        return self._user_prefs

    def _save_user_prefs(self):
        """kaydetkullaniciegilimiyi"""
        self.user_prefs_file.write_text(
            json.dumps(self._user_prefs.to_dict(), ensure_ascii=False, indent=2)
        )

    def update_user_prefs(self, **kwargs):
        """guncellekullaniciegilimiyi"""
        prefs = self.get_user_prefs()
        for k, v in kwargs.items():
            if hasattr(prefs, k):
                setattr(prefs, k, v)
        prefs.updated_at = time.time()
        self._save_user_prefs()

    def get_project_prefs(self, project_path: Path) -> ProjectPreference:
        """alprojeegilimiyi"""
        projects = self._load_projects()
        key = str(project_path.resolve())

        if key not in projects:
            projects[key] = ProjectPreference(project_path=key)
            self._save_projects()

        return projects[key]

    def update_project_prefs(self, project_path: Path, **kwargs):
        """guncelleprojeegilimiyi"""
        projects = self._load_projects()
        key = str(project_path.resolve())

        if key not in projects:
            projects[key] = ProjectPreference(project_path=key)

        prefs = projects[key]
        for k, v in kwargs.items():
            if hasattr(prefs, k):
                setattr(prefs, k, v)
        prefs.updated_at = time.time()
        self._save_projects()

    def add_recent_project(self, project_path: Path):
        """ekleenyakinproje"""
        prefs = self.get_user_prefs()
        key = str(project_path.resolve())

        # kaldirkaydeticinde
        if key in prefs.recent_projects:
            prefs.recent_projects.remove(key)

        # eklekadarenonceyuz
        prefs.recent_projects.insert(0, key)

        # koruenyakin 10 
        prefs.recent_projects = prefs.recent_projects[:10]
        prefs.updated_at = time.time()
        self._save_user_prefs()

    def get_recent_projects(self, limit: int = 5) -> list[Path]:
        """alenyakinproje"""
        prefs = self.get_user_prefs()
        return [Path(p) for p in prefs.recent_projects[:limit] if Path(p).exists()]
