"""is akisiyukle - destek YAML formatis akisitanimilesicaktekraryukle"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from src.core.orchestrator import WORKFLOW_TEMPLATES, WorkflowStep

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class StepConfig:
    """tekilis akisiadimyapilandirma (karsilik gelen YAML icinde step) """

    id: str
    agent: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    timeout: float = 300.0
    retry: int = 0
    metadata: dict = field(default_factory=dict)

    def to_workflow_step(self) -> WorkflowStep:
        """donusturicin orchestrator.WorkflowStep"""
        return WorkflowStep(
            agent_name=self.agent,
            description=self.description,
            dependencies=self.dependencies,
            retry_count=self.retry,
            timeout=self.timeout,
            metadata={**self.metadata, "step_id": self.id},
        )


@dataclass
class WorkflowConfig:
    """tamis akisiyapilandirma (karsilik gelen YAML dosya) """

    name: str
    description: str = ""
    steps: list[StepConfig] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source: str = "builtin"  # builtin | user

    def to_workflow_steps(self) -> list[WorkflowStep]:
        """donusturicin orchestrator.WorkflowStep liste"""
        return [s.to_workflow_step() for s in self.steps]


# ---------------------------------------------------------------------------
# WorkflowLoader
# ---------------------------------------------------------------------------


class WorkflowLoader:
    """
    is akisiyukle

    ozellik: 
    - yuklevarsayilanis akisi (src/config/default_workflows/*.yaml) 
    - yuklekullaniciis akisi (~/.omc/workflows/*.yaml, kullanicitanimoncelik) 
    - sicaktekraryukle: onbellek + mtime kontrol (5saniyesogutma) 
    - gerigeri: YAML yuklebasarisizzamankullan WORKFLOW_TEMPLATES
    """

    def __init__(self, default_workflows_dir: Optional[Path] = None):
        """
        Args:
            default_workflows_dir: varsayilanis akisidizin (varsayilan: src/config/default_workflows) 
        """
        # projekokyol
        project_root = Path(__file__).parent.parent.parent
        self._default_dir = (
            default_workflows_dir
            or project_root / "src" / "config" / "default_workflows"
        )
        self._user_dir = Path.home() / ".omc" / "workflows"

        # onbellek: workflow_name -> (cached_at, mtime, config)
        self._cache: dict[str, tuple[float, float, WorkflowConfig]] = {}
        self._cache_ttl = 5.0  # 5saniyesogutma

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_workflow(self, name: str) -> list[WorkflowStep]:
        """
        yukleis akisiadimliste. 

        oncelik YAML yukle, kullanici workflows uzerine yazvarsayilan. 
        yuklebasarisizzaman fallback kadar WORKFLOW_TEMPLATES. 

        Args:
            name: is akisi adi

        Returns:
            list[WorkflowStep]: adimliste
        """
        config = self.get_workflow_config(name)
        if config:
            return config.to_workflow_steps()
        # Fallback
        return WORKFLOW_TEMPLATES.get(name, [])

    def list_workflows(self) -> list[str]:
        """donusvaris akisi adi (icerirkaynak) """
        names: set[str] = set()

        # varsayilanis akisi
        if self._default_dir.exists():
            for p in self._default_dir.glob("*.yaml"):
                names.add(p.stem)

        # kullaniciis akisi
        if self._user_dir.exists():
            for p in self._user_dir.glob("*.yaml"):
                names.add(p.stem)

        # WORKFLOW_TEMPLATES icindekotadisindaogrehedef (henuzyazol YAML yedek) 
        names.update(WORKFLOW_TEMPLATES.keys())

        return sorted(names)

    def list_builtins(self) -> list[str]:
        """donusicindeayaris akisi adiliste"""
        names: set[str] = set()
        if self._default_dir.exists():
            for p in self._default_dir.glob("*.yaml"):
                names.add(p.stem)
        names.update(WORKFLOW_TEMPLATES.keys())
        return sorted(names)

    def is_builtin(self, name: str) -> bool:
        """karar verolup olmadigiicinicindeayaris akisi"""
        return name in self.list_builtins()

    def parse_yaml_string(
        self, yaml_str: str, name: str = ""
    ) -> Optional[WorkflowConfig]:
        """
         YAML karakter dizisiayristiricin WorkflowConfig. 

        Args:
            yaml_str: YAML icerikkarakter dizisi
            name: is akisi adi (kullanderaporyanlisbaglam) 

        Returns:
            WorkflowConfig veyaayristirma basarisizzaman None
        """
        try:
            raw = yaml.safe_load(yaml_str) or {}
            steps = []
            for s in raw.get("steps", []):
                steps.append(
                    StepConfig(
                        id=s.get("id", s.get("agent", "step")),
                        agent=s.get("agent", ""),
                        description=s.get("description", ""),
                        dependencies=list(s.get("dependencies", [])),
                        timeout=float(s.get("timeout", 300)),
                        retry=int(s.get("retry", 0)),
                        metadata=s.get("metadata", {}),
                    )
                )
            return WorkflowConfig(
                name=raw.get("name", name) or name,
                description=raw.get("description", ""),
                steps=steps,
                metadata=raw.get("metadata", {}),
                source="user",
            )
        except Exception:
            return None

    def get_workflow_config(self, name: str) -> Optional[WorkflowConfig]:
        """
        altamis akisiyapilandirma (icerir metadata) . 

        sicaktekraryukle: kontroldosya mtime, 5saniyeicindehayirtekrartekraroku. 

        Args:
            name: is akisi adi

        Returns:
            WorkflowConfig veya None (bulhayirkadarzamandonus None, tarafindancagriyon fallback) 
        """
        # kullanici workflows oncelik
        user_path = self._user_dir / f"{name}.yaml"
        default_path = self._default_dir / f"{name}.yaml"

        # kesinisterokudosya (oncelikkullanici) 
        file_path: Optional[Path] = None
        source = "user"
        if user_path.exists():
            file_path = user_path
        elif default_path.exists():
            file_path = default_path
            source = "builtin"

        # kontrolonbellek
        now = time.time()
        if name in self._cache:
            cached_at, cached_mtime, config = self._cache[name]
            if now - cached_at < self._cache_ttl:
                if file_path is None or cached_mtime >= file_path.stat().st_mtime:
                    return config

        # yokonbellekveyadonem, tekraryeniyukle
        if file_path is None:
            # yokvar YAML dosya → onbellekicindekaldir (zorunlu fallback) 
            self._cache.pop(name, None)
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

            steps = []
            for s in raw.get("steps", []):
                steps.append(
                    StepConfig(
                        id=s.get("id", s.get("agent", "step")),
                        agent=s.get("agent", ""),
                        description=s.get("description", ""),
                        dependencies=list(s.get("dependencies", [])),
                        timeout=float(s.get("timeout", 300)),
                        retry=int(s.get("retry", 0)),
                        metadata=s.get("metadata", {}),
                    )
                )

            config = WorkflowConfig(
                name=raw.get("name", name),
                description=raw.get("description", ""),
                steps=steps,
                metadata=raw.get("metadata", {}),
                source=source,
            )

            # yazgirisonbellek
            mtime = file_path.stat().st_mtime
            self._cache[name] = (now, mtime, config)
            return config

        except Exception:
            # YAML ayristirma basarisiz → onbellekkaldir, zorunlu fallback
            self._cache.pop(name, None)
            return None

    def _ensure_user_dir(self):
        """saglarkullaniciis akisidizinkaydeticinde"""
        self._user_dir.mkdir(parents=True, exist_ok=True)

    def save_workflow(self, name: str, config: WorkflowConfig) -> Path:
        """
        kaydetkullaniciis akisikadar ~/.omc/workflows/. 

        Args:
            name: is akisi adi
            config: is akisiyapilandirma

        Returns:
            Path: kaydetdosyayol
        """
        self._ensure_user_dir()
        file_path = self._user_dir / f"{name}.yaml"

        data = {
            "name": name,
            "description": config.description,
            "steps": [
                {
                    "id": s.id,
                    "agent": s.agent,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "timeout": s.timeout,
                    "retry": s.retry,
                }
                for s in config.steps
            ],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # izinonbellekkayipetki
        self._cache.pop(name, None)
        return file_path

    def delete_workflow(self, name: str) -> bool:
        """
        silkullaniciis akisi (~/.omc/workflows/<name>.yaml) . 

        icindeayaris akisihayirolabilirsil (donus False) . 

        Args:
            name: is akisi adi

        Returns:
            bool: olup olmadigisilbasarili
        """
        # icindeayaris akisikontrol (kaydeticinde default_workflows icinde) 
        default_path = self._default_dir / f"{name}.yaml"
        if default_path.exists():
            return False

        user_path = self._user_dir / f"{name}.yaml"
        if user_path.exists():
            user_path.unlink()
            self._cache.pop(name, None)
            return True
        return False
