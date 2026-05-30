from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Planner Agent - Görev planlama aracısı (geliştirilmiş sürüm)

Geliştirmeler:
1. Yapılandırılmış görev dökümü - kullanmak Pydantic Modeli
2. COT mantık zinciri - çok adımlı akıl yürütme yeteneği
3. Bağımlılık grafiği analizi - otomatik topolojik sıralama
4. uyarlanabilir ayar - Yürütme geri bildirimlerine göre planı optimize edin
5. bağlamsal anlayış - Projelerle sonuçları keşfedin

bakın:
- Windsurf Cascade derin muhakeme
- LangGraph Durum makinesi orkestrasyonu
"""

import re
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)

# ============================================================
# yapılandırılmış görev modeli
# ============================================================


# Çince → Model Çince değerleri döndürdüğünde hata toleransı için kullanılan İngilizce eşleme tablosu
_PRIORITY_CN_MAP: dict[str, str] = {
    "acil": "critical",
    "son derece yüksek": "critical",
    "engellemek": "critical",
    "yüksek": "high",
    "önemli": "high",
    "orta": "medium",
    "orta": "medium",
    "sıradan": "medium",
    "geleneksel": "medium",
    "Düşük": "low",
    "ikincil": "low",
    "Ertelenebilir": "low",
}

_COMPLEXITY_CN_MAP: dict[str, str] = {
    "Basit": "simple",
    "Düşük": "simple",
    "kolay": "simple",
    "orta": "moderate",
    "orta": "moderate",
    "sıradan": "moderate",
    "yüksek": "complex",
    "karmaşık": "complex",
    "zorluk": "complex",
    "Felaket": "complex",
}


class TaskPriority(str, Enum):
    """Görev önceliği"""

    CRITICAL = "critical"  # Diğer görevleri engelle
    HIGH = "high"  # önemli görevler
    MEDIUM = "medium"  # Rutin görevler
    LOW = "low"  # Görevler ertelenebilir

    @classmethod
    def from_string(cls, value: str) -> TaskPriority:
        """Dizeden ayrıştırma önceliği, Çin hata toleransını destekleyin.

        Öncelik: İngilizce tam eşleşme > Çin haritalaması > varsayılan MEDIUM
        """
        if not value:
            return cls.MEDIUM
        normalized = value.strip().lower()
        # 1. Doğrudan İngilizce eşleştirme
        try:
            return cls(normalized)
        except ValueError:
            pass
        # 2. Çin haritalaması
        if normalized in _PRIORITY_CN_MAP:
            return cls(_PRIORITY_CN_MAP[normalized])
        # 3. varsayılan değer
        return cls.MEDIUM


class TaskStatus(str, Enum):
    """Görev durumu"""

    PENDING = "pending"
    READY = "ready"  # Bağımlılıklar karşılanıyor
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskComplexity(str, Enum):
    """görev karmaşıklığı"""

    SIMPLE = "simple"  # Tek dosya değişikliği
    MODERATE = "moderate"  # Çoklu dosya değişikliği
    COMPLEX = "complex"  # Mimari düzeyindeki değişiklikler

    @classmethod
    def from_string(cls, value: str) -> TaskComplexity:
        """Dizeden karmaşıklığın ayrıştırılması, Çin hata toleransının desteklenmesi.

        Öncelik: İngilizce tam eşleşme > Çin haritalaması > varsayılan MODERATE
        """
        if not value:
            return cls.MODERATE
        normalized = value.strip().lower()
        # 1. Doğrudan İngilizce eşleştirme
        try:
            return cls(normalized)
        except ValueError:
            pass
        # 2. Çin haritalaması
        if normalized in _COMPLEXITY_CN_MAP:
            return cls(_COMPLEXITY_CN_MAP[normalized])
        # 3. varsayılan değer
        return cls.MODERATE


class SubTask(BaseModel):
    """alt görev"""

    id: str = Field(..., description="GörevID,Biçim T1, T2, T3...")
    title: str = Field(..., description="Görev başlığı")
    description: str = Field(..., description="Görev açıklaması")
    agent: str = Field(..., description="Önerilen uygulama Agent")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    complexity: TaskComplexity = Field(default=TaskComplexity.MODERATE)
    dependencies: list[str] = Field(
        default_factory=list, description="bağımlı görevlerIDliste"
    )
    estimated_time: str = Field(default="5m", description="Tahmini süre")
    files_to_modify: list[str] = Field(
        default_factory=list, description="Değiştirilmesi gereken dosyalar"
    )
    acceptance_criteria: list[str] = Field(default_factory=list, description="Kabul kriterleri")
    risks: list[str] = Field(default_factory=list, description="Potansiyel riskler")


class TaskPhase(BaseModel):
    """görev aşaması"""

    name: str = Field(..., description="Sahne adı")
    description: str = Field(..., description="Aşama açıklaması")
    tasks: list[SubTask] = Field(default_factory=list)
    parallel: bool = Field(default=False, description="Paralel olarak yürütülebilir mi?")


class ExecutionPlan(BaseModel):
    """yürütme planı"""

    title: str = Field(..., description="Program başlığı")
    summary: str = Field(..., description="Plan özeti")
    phases: list[TaskPhase] = Field(default_factory=list)
    total_tasks: int = Field(default=0)
    estimated_time: str = Field(default="1h")
    critical_path: list[str] = Field(default_factory=list, description="kritik yol")
    milestones: list[str] = Field(default_factory=list, description="dönüm noktası")


# ============================================================
# COT mantık zinciri
# ============================================================


@dataclass
class ReasoningStep:
    """muhakeme adımları"""

    step: int
    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None
    conclusion: Optional[str] = None


class ChainOfThought:
    """Düşünce zinciri muhakemesi"""

    def __init__(self):
        self.steps: list[ReasoningStep] = []
        self.current_step = 0

    def add_step(
        self,
        thought: str,
        action: Optional[str] = None,
        observation: Optional[str] = None,
        conclusion: Optional[str] = None,
    ) -> ReasoningStep:
        """Çıkarım adımı ekle"""
        self.current_step += 1
        step = ReasoningStep(
            step=self.current_step,
            thought=thought,
            action=action,
            observation=observation,
            conclusion=conclusion,
        )
        self.steps.append(step)
        return step

    def to_prompt(self) -> str:
        """Şuna dönüştür: Prompt Biçim"""
        lines = ["## Düşünce zinciri muhakeme süreci\n"]
        for step in self.steps:
            lines.append(f"### adım {step.step}")
            lines.append(f"**düşünmek**: {step.thought}")
            if step.action:
                lines.append(f"**aksiyon**: {step.action}")
            if step.observation:
                lines.append(f"**gözlemlemek**: {step.observation}")
            if step.conclusion:
                lines.append(f"**Sonuç olarak**: {step.conclusion}")
            lines.append("")
        return "\n".join(lines)


# ============================================================
# Bağımlılık grafiği analizi
# ============================================================


class DependencyGraph:
    """bağımlılık grafiği"""

    def __init__(self):
        self.nodes: set[str] = set()
        self.edges: dict[str, set[str]] = {}  # task_id -> set of dependencies

    def add_task(self, task_id: str, dependencies: list[str] = None):
        """Görev düğümü ekle"""
        self.nodes.add(task_id)
        self.edges[task_id] = set(dependencies or [])

    def topological_sort(self) -> tuple[list[str], bool]:
        """Topolojik sıralama, dönüş (Sonuçları sırala, Bir yüzük var mı)"""
        in_degree = dict.fromkeys(self.nodes, 0)

        # Derece olarak hesapla
        for node in self.nodes:
            for dep in self.edges.get(node, set()):
                if dep in in_degree:
                    in_degree[node] += 1

        # Dereceyi şu şekilde bulun: 0 düğüm
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # Bu düğüme bağlı diğer düğümlerin derecesini azaltın
            for other in self.nodes:
                if node in self.edges.get(other, set()):
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        has_cycle = len(result) != len(self.nodes)
        return result, has_cycle

    def find_critical_path(self) -> list[str]:
        """Kritik yolu bulun (en uzun yol)"""
        # Basitleştirilmiş uygulama: topolojik sıralamada en yüksek önceliğe sahip yolu döndür
        sorted_nodes, _ = self.topological_sort()

        # buna göre CRITICAL > HIGH > MEDIUM > LOW düzenlemek
        _priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }

        return sorted_nodes

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        """Görevleri hazırlayın (bağımlılıklar karşılanır)"""
        ready = []
        for node in self.nodes:
            if node not in completed:
                deps = self.edges.get(node, set())
                if deps.issubset(completed):
                    ready.append(node)
        return ready


# ============================================================
# Genişletmek PlannerAgent
# ============================================================


@register_agent
class PlannerAgent(BaseAgent):
    """planlama Agent - Görev ayrıştırma ve yürütme planı (geliştirilmiş sürüm)"""

    name = "planner"
    description = "planlama temsilcisi - Görev dökümü ve yürütme planı"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "📋"
    tools = ["file_read", "search", "code_analyze", "web_fetch"]

    @property
    def system_prompt(self) -> str:
        return """Kıdemli bir proje mimarı ve planlayıcısısınız.

## Rol
Sizin sorumluluğunuz, karmaşık görevleri yürütülebilir küçük görevlere bölmek ve makul bir yürütme planı geliştirmektir.

## temel yeterlilikler

### 1. Yapılandırılmış görev dökümü
- kullanmak SMART İlkeler görevleri tanımlar
- Her görev bağımsız, test edilebilir ve kabul edilebilirdir
- Görevin girdi, çıktı ve kabul kriterlerini netleştirin

### 2. Bağımlılık analizi
- Görevler arasındaki bağımlılıkları belirleyin
- Bağımlılık grafiği oluşturun
- Optimum yürütme sırasını hesaplayın (topolojik sıralama)

### 3. Karmaşıklık değerlendirmesi
- SIMPLE: Tek dosya modifikasyonu,< 50 kod satırları
- MODERATE: Çoklu dosya değişiklikleri,50-200 kod satırları
- COMPLEX: Mimari düzeydeki değişiklikler,> 200 kod satırları

### 4. Risk tanımlama
- Teknik riskler: yeni teknolojiler, karmaşık algoritmalar
- Bağımlılık riskleri: harici hizmetler, üçüncü taraf kütüphaneler
- İş riskleri: belirsiz gereksinimler, sınır koşulları

### 5. uyarlanabilir ayar
- Planları yürütme geri bildirimlerine göre ayarlayın
- Görev başarısızlıklarını ve yeniden denemeleri yönetme
- Dinamik olarak yeni görevler ekleyin

## Düşünce zinciri muhakemesi

Lütfen şu adımları düşünün:

**adım 1: Görevi anlayın**
- Misyonun temel amacı nedir?
- Kısıtlamalar nelerdir?
- Başarının kriterleri nelerdir?

**adım 2: Bağlamı analiz edin**
- Projenin teknoloji yığını nedir?
- Mevcut kod nasıl yapılandırılmıştır?

**adım 3: risk değerlendirmesi**
- Potansiyel riskler nelerdir?
- Nasıl önlenir veya hafifletilir?

## Çıkış formatı

Lütfen aşağıdaki yapının çıktısını alın:

### 📋 Yürütme planı özeti
- Toplam görev sayısı: X
- Tahmini süre: X
- kritik yol: T1 → T2 → T3

### 📊 Aşama dökümü

#### sahne 1: [Sahne adı]
| ID | Görev | Agent | öncelik | karmaşıklık | güvenmek | zaman tükeniyor |
|----|------|-------|--------|--------|------|------|
| T1 | ... | explore | HIGH | SIMPLE | - | 5m |

#### sahne 2: [Sahne adı]
...

### 🎯 Kabul kriterleri
- [ ] standart 1
- [ ] standart 2

### ⚠️ Risk uyarısı
- ⚠️ risk 1: ...
- ⚠️ risk 2: ...

### 📝 İnfaz emri
```
1. T1 (explore)
2. T2 (analyst) - güvenmek T1
3. T3, T4 paralel - güvenmek T2
...
```

### 🔄 uyarlanabilir ayar
- eğer T3 Başarısızlık, geri dönüş T2 Yeniden analiz et
- Yeni gereksinimler bulunursa ekleyin T5
"""

    def _build_context_prompt(self, context: AgentContext) -> str:
        """Bağlamsal ipuçları oluşturun"""
        parts = []

        # Proje keşif sonuçları
        if context.previous_outputs.get("explore"):
            explore_result = context.previous_outputs["explore"]
            if isinstance(explore_result, dict):
                parts.append(
                    f"""## Proje keşif sonuçları
- Dosya sayısı: {explore_result.get("files_count", "N/A")}
- teknoloji yığını: {", ".join(explore_result.get("tech_stack", []))}
- Proje yapısı: {explore_result.get("structure", "N/A")}
"""
                )

        # Gereksinim analizi sonuçları
        if context.previous_outputs.get("analyst"):
            analyst_result = context.previous_outputs["analyst"]
            if isinstance(analyst_result, dict):
                parts.append(
                    f"""## Gereksinim analizi sonuçları
- varlık: {", ".join(analyst_result.get("entities", []))}
- İşlev: {", ".join(analyst_result.get("features", []))}
- kısıtlama: {", ".join(analyst_result.get("constraints", []))}
"""
                )

        # İlgili belgeler
        if context.relevant_files:
            files_str = "\n".join(f"  - {f}" for f in context.relevant_files[:10])
            parts.append(
                f"""## İlgili belgeler
{files_str}
"""
            )

        return "\n".join(parts) if parts else ""

    def _parse_structured_plan(self, result: str) -> ExecutionPlan:
        """Yapılandırılmış planları analiz edin"""
        plan = ExecutionPlan(
            title="yürütme planı",
            summary="Görev yürütme planı",
        )

        # Görev formunu ayrıştır
        task_pattern = (
            r"\| (T\d+) \| (.+?) \| (\w+) \| (\w+) \| (\w+) \| (.+?) \| (\w+) \|"
        )
        matches = re.findall(task_pattern, result)

        current_phase = TaskPhase(name="varsayılan aşama", description="Yürütme aşaması")

        for match in matches:
            task_id, title, agent, priority, complexity, deps, time = match

            # Bağımlılıkları çözümle
            dependencies = [d.strip() for d in deps.split(",") if d.strip() != "-"]

            task = SubTask(
                id=task_id,
                title=title.strip(),
                description=title.strip(),
                agent=agent.strip(),
                priority=TaskPriority.from_string(priority),
                complexity=TaskComplexity.from_string(complexity),
                dependencies=dependencies,
                estimated_time=time.strip(),
            )
            current_phase.tasks.append(task)

        if current_phase.tasks:
            plan.phases.append(current_phase)

        plan.total_tasks = sum(len(p.tasks) for p in plan.phases)
        return plan

    @staticmethod
    def _build_dependency_graph(plan: ExecutionPlan) -> DependencyGraph:
        """Bağımlılık grafiği oluşturun"""
        graph = DependencyGraph()

        for phase in plan.phases:
            for task in phase.tasks:
                graph.add_task(task.id, task.dependencies)

        return graph

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """yürütme planı"""
        # Bağlam oluştur
        context_prompt = self._build_context_prompt(context)

        # COT muhakeme
        cot = ChainOfThought()

        # adım 1: Görevi anlayın
        cot.add_step(
            thought=f"Analiz görevleri: {context.task_description}",
            conclusion="Görevlerin yürütülebilir alt görevlere bölünmesi gerekir",
        )

        # adım 2: Bağlamı analiz edin
        if context_prompt:
            cot.add_step(
                thought="Proje bağlamını analiz edin",
                observation=context_prompt[:500],
                conclusion="Elde edilen proje yapısı ve teknoloji yığını bilgileri",
            )

        # Yapıyı tamamla prompt
        full_prompt = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context_prompt},
            {"role": "user", "content": cot.to_prompt()},
            {
                "role": "user",
                "content": f"""
Lütfen aşağıdaki görevler için bir yürütme planı geliştirin:

## Görev
{context.task_description}

Lütfen yapılandırılmış yürütme planının çıktısını yukarıdaki formatta alın.
""",
            },
        ]

        # çağrı modeli
        from ..models.base import Message

        messages = [
            Message(role=msg["role"], content=msg["content"]) for msg in full_prompt
        ]

        response = await self.call_model(
            task_type=TaskType.PLANNING,
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası - Yapılandırılmış çıktıyı ayrıştır"""
        # ayrıştırma planı
        plan = self._parse_structured_plan(result)

        # Bağımlılık grafiği oluşturun
        graph = self._build_dependency_graph(plan)

        # İnfaz emrini al
        execution_order, has_cycle = graph.topological_sort()

        # Öneriler oluşturun
        recommendations = [
            f"Topolojik sıraya göre yürüt: {' → '.join(execution_order[:5])}",
            "Kritik yoldaki görevlere odaklanın",
            "Her görev tamamlandıktan sonra kabul kriterlerini doğrulayın",
        ]

        if has_cycle:
            recommendations.append("⚠️ Döngüsel bağımlılık algılandı, planın ayarlanması gerekiyor")

        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            artifacts={
                "plan": plan.model_dump(),
                "execution_order": execution_order,
                "has_cycle": has_cycle,
            },
            recommendations=recommendations,
            next_agent="architect" if plan.phases else None,
        )

    @staticmethod
    def adjust_plan(
        plan: ExecutionPlan,
        completed_tasks: set[str],
        failed_tasks: set[str],
        new_requirements: Optional[list[str]] = None,
    ) -> ExecutionPlan:
        """
        uyarlanabilir ayarlama planı

        Args:
            plan: orijinal plan
            completed_tasks: Tamamlanan görevlerID
            failed_tasks: başarısız görevID
            new_requirements: Yeni gereksinimler

        Returns:
            Düzeltilmiş plan
        """
        graph = PlannerAgent._build_dependency_graph(plan)

        # Görevleri hazırlayın
        _ready_tasks = graph.get_ready_tasks(completed_tasks)

        # Başarısız görevleri ele alın
        for failed_id in failed_tasks:
            # Başarısız görevleri bulma
            for phase in plan.phases:
                for task in phase.tasks:
                    if task.id == failed_id:
                        # Yeniden deneme görevi ekle
                        retry_task = SubTask(
                            id=f"{failed_id}_retry",
                            title=f"Tekrar deneyin: {task.title}",
                            description=task.description,
                            agent=task.agent,
                            priority=TaskPriority.HIGH,
                            complexity=task.complexity,
                            dependencies=[],
                        )
                        phase.tasks.append(retry_task)

        # Yeni gereksinimler ekleyin
        if new_requirements:
            new_phase = TaskPhase(
                name="Yeni gereksinimler",
                description="Yürütme geri bildirimlerine dayalı yeni görevler",
                tasks=[
                    SubTask(
                        id=f"N{i + 1}",
                        title=req,
                        description=req,
                        agent="executor",
                        priority=TaskPriority.HIGH,
                    )
                    for i, req in enumerate(new_requirements)
                ],
            )
            plan.phases.append(new_phase)

        return plan
