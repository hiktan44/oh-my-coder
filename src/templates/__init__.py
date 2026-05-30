from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
sablonpazar

ontanimis akisisablondepolamaveyonet. 
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class TemplateCategory(str, Enum):
    """sablonpuansinif"""

    BUILD = "build"
    REVIEW = "review"
    DEBUG = "debug"
    TEST = "test"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    DEPLOY = "deploy"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """is akisiadim"""

    agent_name: str
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    condition: Optional[str] = None
    timeout: int = 300
    retry: int = 0
    config: dict[str, Any] = field(default_factory=dict)


class TemplateMetadata(BaseModel):
    """sablonogresayigore"""

    name: str
    display_name: str
    description: str
    category: TemplateCategory
    version: str = "0.2.0"
    author: str = ""
    tags: list[str] = []
    icon: str = "📦"
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    estimated_time: str = ""


@dataclass
class WorkflowTemplate:
    """is akisisablon"""

    metadata: TemplateMetadata
    steps: list[WorkflowStep]
    variables: dict[str, Any] = field(default_factory=dict)
    hooks: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """donusturicinsozluk"""
        return {
            "metadata": self.metadata.model_dump(),
            "steps": [
                {
                    "agent_name": s.agent_name,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "condition": s.condition,
                    "timeout": s.timeout,
                    "retry": s.retry,
                    "config": s.config,
                }
                for s in self.steps
            ],
            "variables": self.variables,
            "hooks": self.hooks,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowTemplate:
        """sozlukolustur"""
        metadata = TemplateMetadata(**data["metadata"])
        steps = [
            WorkflowStep(
                agent_name=s["agent_name"],
                description=s.get("description", ""),
                dependencies=s.get("dependencies", []),
                condition=s.get("condition"),
                timeout=s.get("timeout", 300),
                retry=s.get("retry", 0),
                config=s.get("config", {}),
            )
            for s in data["steps"]
        ]
        return cls(
            metadata=metadata,
            steps=steps,
            variables=data.get("variables", {}),
            hooks=data.get("hooks", {}),
        )


# icindeayarsablon
BUILTIN_TEMPLATES: list[WorkflowTemplate] = [
    # olustursablon
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="build",
            display_name="tamolusturakis",
            description="planlakadardogrulamatamacgonderakis",
            category=TemplateCategory.BUILD,
            tags=["acgonder", "olustur"],
            icon="🔨",
            difficulty="intermediate",
            estimated_time="5-15puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="Planner", description="olusturacgonderplan"),
            WorkflowStep(
                agent_name="Architect",
                description="tasarimsistemmimari",
                dependencies=["Planner"],
            ),
            WorkflowStep(
                agent_name="Executor",
                description="olusturkod",
                dependencies=["Architect"],
            ),
            WorkflowStep(
                agent_name="Verifier",
                description="dogrulamavetest",
                dependencies=["Executor"],
            ),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="quick-fix",
            display_name="hizlihizduzeltme",
            description="hizlihizkonumveduzeltmesorun",
            category=TemplateCategory.BUILD,
            tags=["duzeltme", "hizlihiz"],
            icon="⚡",
            difficulty="beginner",
            estimated_time="1-5puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="Executor", description="dogrubaglanduzeltme"),
            WorkflowStep(agent_name="Verifier", description="dogrulamaduzeltme"),
        ],
    ),
    # incelemesablon
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="review",
            display_name="kodinceleme",
            description="tumyuzkodkalitemiktarinceleme",
            category=TemplateCategory.REVIEW,
            tags=["inceleme", "kalitemiktar"],
            icon="🔍",
            difficulty="beginner",
            estimated_time="2-5puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="CodeReviewer", description="kodkalitemiktarinceleme"),
            WorkflowStep(agent_name="SecurityReviewer", description="guvenlikguvenlik acigitara"),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="pr-review",
            display_name="PR inceleme",
            description="Pull Request tamincelemeakis",
            category=TemplateCategory.REVIEW,
            tags=["PR", "inceleme"],
            icon="📋",
            difficulty="intermediate",
            estimated_time="5-10puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="CodeReviewer", description="kodkalitemiktarinceleme"),
            WorkflowStep(agent_name="SecurityReviewer", description="guvenlikinceleme"),
            WorkflowStep(agent_name="TestEngineer", description="testuzerine yazkontrol"),
            WorkflowStep(
                agent_name="Writer",
                description="olusturincelemerapor",
                dependencies=["CodeReviewer", "SecurityReviewer", "TestEngineer"],
            ),
        ],
    ),
    # hata ayiklasablon
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="debug",
            display_name="sorunhata ayikla",
            description="sistemsorunkonumveduzeltme",
            category=TemplateCategory.DEBUG,
            tags=["hata ayikla", "duzeltme"],
            icon="🐛",
            difficulty="intermediate",
            estimated_time="5-20puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="Debugger", description="konumsorun"),
            WorkflowStep(
                agent_name="Tracer", description="izleizlekokneden", dependencies=["Debugger"]
            ),
            WorkflowStep(
                agent_name="Executor", description="duzeltmesorun", dependencies=["Tracer"]
            ),
            WorkflowStep(
                agent_name="Verifier", description="dogrulamaduzeltme", dependencies=["Executor"]
            ),
        ],
    ),
    # testsablon
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="test",
            display_name="olusturtest",
            description="otomatikolusturtekilogretest",
            category=TemplateCategory.TEST,
            tags=["test", "tekilogretest"],
            icon="🧪",
            difficulty="beginner",
            estimated_time="2-5puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="TestEngineer", description="olusturtekilogretest"),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="test-full",
            display_name="tamtest",
            description="olusturtekilogretestvesetoltest",
            category=TemplateCategory.TEST,
            tags=["test", "setoltest"],
            icon="🔬",
            difficulty="intermediate",
            estimated_time="5-10puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="TestEngineer", description="olusturtekilogretest"),
            WorkflowStep(
                agent_name="Executor",
                description="olustursetoltest",
                dependencies=["TestEngineer"],
            ),
            WorkflowStep(
                agent_name="Verifier", description="satirtest", dependencies=["Executor"]
            ),
        ],
    ),
    # yeniden duzenlemesablon
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="refactor",
            display_name="kodyeniden duzenleme",
            description="akilliedebilirkodyeniden duzenlemeveiyi",
            category=TemplateCategory.REFACTOR,
            tags=["yeniden duzenleme", "iyi"],
            icon="🔧",
            difficulty="advanced",
            estimated_time="10-30puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="CodeReviewer", description="taniyeniden duzenlemenokta"),
            WorkflowStep(
                agent_name="Architect",
                description="tasarimyeniden duzenlemeplan",
                dependencies=["CodeReviewer"],
            ),
            WorkflowStep(
                agent_name="Executor",
                description="yurutyeniden duzenleme",
                dependencies=["Architect"],
            ),
            WorkflowStep(
                agent_name="Verifier", description="dogrulamaislev", dependencies=["Executor"]
            ),
        ],
    ),
    # dokumantasyonsablon
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="document",
            display_name="olusturdokumantasyon",
            description="otomatikolusturprojedokumantasyon",
            category=TemplateCategory.DOCUMENT,
            tags=["dokumantasyon", "README"],
            icon="📝",
            difficulty="beginner",
            estimated_time="2-10puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="Writer", description="olusturdokumantasyon"),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="api-doc",
            display_name="API dokumantasyon",
            description="olustur API dokumantasyon",
            category=TemplateCategory.DOCUMENT,
            tags=["dokumantasyon", "API"],
            icon="📚",
            difficulty="beginner",
            estimated_time="5-15puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="Explorer", description="analiz API yapi"),
            WorkflowStep(
                agent_name="Writer",
                description="olustur API dokumantasyon",
                dependencies=["Explorer"],
            ),
        ],
    ),
    # kesfetsablon
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="explore",
            display_name="kodkesfet",
            description="kesfetveanlakodkutuphane",
            category=TemplateCategory.CUSTOM,
            tags=["kesfet", "analiz"],
            icon="📖",
            difficulty="beginner",
            estimated_time="2-10puandakika",
        ),
        steps=[
            WorkflowStep(agent_name="Explorer", description="kesfetkodkutuphane"),
            WorkflowStep(
                agent_name="Writer",
                description="olusturanalizrapor",
                dependencies=["Explorer"],
            ),
        ],
    ),
]


class TemplateMarket:
    """
    sablonpazar

    yonetis akisisablondepolama, kesfetvepaylas. 

    Example:
        >>> market = TemplateMarket()
        >>> templates = market.list_templates(category="build")
        >>> template = market.get_template("build")
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        baslatsablonpazar

        Args:
            template_dir: ozelsablondizin
        """
        self.template_dir = template_dir or Path(".omc/templates")
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self._templates: dict[str, WorkflowTemplate] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        """yukleicindeayarsablon"""
        for template in BUILTIN_TEMPLATES:
            self._templates[template.metadata.name] = template

    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """
        alsablon

        Args:
            name: sablonad

        Returns:
            sablonornek
        """
        return self._templates.get(name)

    def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        difficulty: Optional[str] = None,
    ) -> list[WorkflowTemplate]:
        """
        listelesablon

        Args:
            category: puansiniffiltrele
            tags: etiketfiltrele
            difficulty: zorderecefiltrele

        Returns:
            sablonliste
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.metadata.category.value == category]

        if tags:
            templates = [
                t for t in templates if any(tag in t.metadata.tags for tag in tags)
            ]

        if difficulty:
            templates = [t for t in templates if t.metadata.difficulty == difficulty]

        return templates

    def register_template(self, template: WorkflowTemplate) -> None:
        """
        kayitsablon

        Args:
            template: sablonornek
        """
        self._templates[template.metadata.name] = template

    def save_template(self, template: WorkflowTemplate) -> Path:
        """
        kaydetsablonkadardosya

        Args:
            template: sablonornek

        Returns:
            dosyayol
        """
        file_path = self.template_dir / f"{template.metadata.name}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)

        return file_path

    def load_template(self, name: str) -> Optional[WorkflowTemplate]:
        """
        dosyayuklesablon

        Args:
            name: sablonad

        Returns:
            sablonornek
        """
        file_path = self.template_dir / f"{name}.json"

        if not file_path.exists():
            return None

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        template = WorkflowTemplate.from_dict(data)
        self._templates[name] = template
        return template

    def load_all(self) -> None:
        """yuklevarozelsablon"""
        for file_path in self.template_dir.glob("*.json"):
            try:
                self.load_template(file_path.stem)
            except Exception as e:
                print(f"yuklesablonbasarisiz: {file_path}: {e}")

    def get_categories(self) -> list[dict[str, Any]]:
        """
        tumunu alpuansinif

        Returns:
            puansinifbilgiliste
        """
        categories = {}
        for template in self._templates.values():
            cat = template.metadata.category.value
            if cat not in categories:
                categories[cat] = {
                    "name": cat,
                    "icon": template.metadata.icon,
                    "count": 0,
                }
            categories[cat]["count"] += 1

        return list(categories.values())

    def search(self, query: str) -> list[WorkflowTemplate]:
        """
        arasablon

        Args:
            query: arama anahtar kelimeleri

        Returns:
            eslestirsablonliste
        """
        query = query.lower()
        results = []

        for template in self._templates.values():
            meta = template.metadata
            if (
                query in meta.name.lower()
                or query in meta.display_name.lower()
                or query in meta.description.lower()
                or any(query in tag.lower() for tag in meta.tags)
            ):
                results.append(template)

        return results


# globalornek
_template_market: Optional[TemplateMarket] = None


def get_template_market() -> TemplateMarket:
    """alglobalsablonpazarornek"""
    global _template_market
    if _template_market is None:
        _template_market = TemplateMarket()
    return _template_market
