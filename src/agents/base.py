from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Agent temel sınıf - Tüm aracılar için temel sınıf

Tasarım ilkeleri:
1. her biri Agent Tek ve net sorumluluklar
2. geçmek Prompt Rolleri ve davranışları tanımlayın
3. İş süreçlerini ve çıktılarını otomatik olarak kaydedin
4. Destek ve diğer Agent işbirliği

Agent yaşam döngüsü:
1. Başlatma (yapılandırmayı yükleme ve Prompt)
2. görevleri al
3. Yürütme (modelleri çağırma, araçları kullanma)
4. Çıktı sonuçları
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from src.models.base import Message, ModelResponse

logger = logging.getLogger(__name__)

# alet Schema tanım(OpenAI function calling Biçimi)
WEB_FETCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": "Belirtilen alın URL Harici bağlantılara erişmek ve çevrimiçi belgelere danışmak için kullanılan web sayfası metin içeriği",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "erişmek URL"}
            },
            "required": ["url"],
        },
    },
}

SUPPORTED_TOOLS = {"web_fetch": WEB_FETCH_TOOL_SCHEMA}

if TYPE_CHECKING:
    from src.models.router import ModelRouter


class AgentStatus(Enum):
    """Agent durum"""

    IDLE = "idle"  # boşta
    WORKING = "working"  # işte
    WAITING = "waiting"  # giriş bekleniyor
    COMPLETED = "completed"  # Tamamlanmış
    FAILED = "failed"  # hata


class AgentLane(Enum):
    """Agent koridor - Orijinal projeye karşılık gelen dört ana kanal"""

    BUILD_ANALYSIS = "build_analysis"  # inşa etmek/analiz etmek
    REVIEW = "review"  # gözden geçirmek
    DOMAIN = "domain"  # alan
    COORDINATION = "coordination"  # koordinasyon


@dataclass
class AgentContext:
    """Agent yürütme bağlamı"""

    project_path: Path  # Proje yolu
    task_description: str  # Görev açıklaması
    working_directory: Optional[Path] = None  # çalışma dizini
    relevant_files: list[Path] = field(default_factory=list)  # İlgili belgeler
    previous_outputs: dict[str, Any] = field(default_factory=dict)  # Önsöz Agent çıktı
    metadata: dict[str, Any] = field(default_factory=dict)  # Diğer meta veriler
    skill_context: str = ""  # Tier 0 Otomatik enjeksiyon:Skill Deneyim Kontrol Listesi (tarafından: Orchestrator doldurma)
    override_model: Optional[str] = (
        None  # kullanıcı tarafından belirlenen model ID(beğenmek "glm-4-flash"), ön uç seçiminden
    )


@dataclass
class AgentOutput:
    """Agent çıktı"""

    agent_name: str  # Agent isim
    status: AgentStatus  # Yürütme durumu
    result: Optional[str] = None  # Ana sonuçlar
    artifacts: dict[str, Any] = field(default_factory=dict)  # Ürünler (belgeler, veriler vb.)
    recommendations: list[str] = field(default_factory=list)  # Önerilen sonraki adımlar
    next_agent: Optional[str] = None  # Sonrakini öner Agent
    usage: dict[str, int] = field(default_factory=dict)  # Token kullanmak
    execution_time: float = 0.0  # Yürütme süresi (saniye)
    error: Optional[str] = None  # hata mesajı
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAgent(ABC):
    """
    Agent temel sınıf

    Temel yöntemler:
    - execute(): Görevleri yürütme (şablon yöntemi)
    - _prepare_prompt(): Hazırlanmak Prompt
    - _run(): Gerçek yürütme mantığı (alt sınıf uygulaması)
    - _post_process(): İşlem sonrası

    Alt sınıfların uygulaması gerekir:
    - _run(): çekirdek yürütme mantığı
    - tanım name, description, default_tier özellikler
    """

    # Alt sınıfların geçersiz kılması gereken özellikler
    name: str = "base_agent"
    description: str = "temel sınıf Agent"
    lane: AgentLane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"  # low, medium, high

    # İsteğe bağlı özellikler
    icon: str = "🤖"
    tools: list[str] = ["web_fetch"]  # Varsayılan olarak etkinleştirilmiş, kullanılabilir araçların listesi web_fetch

    def __init__(
        self,
        model_router: Optional[ModelRouter] = None,
        config: Optional[dict[str, Any]] = None,
        orchestrator: Optional[Any] = None,
    ):
        """
        Args:
            model_router: model yönlendirici (isteğe bağlı,CLI info Salt okunur sahneyi beklerken geçmenize gerek yoktur)
            config: Agent özel konfigürasyon
            orchestrator: Orchestrator örnek (sub'u çağırmak için) Agent), bağlıdır Orchestrator.get_agent() otomatik enjeksiyon
        """
        self.model_router = model_router
        self.orchestrator = orchestrator
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self._output_history: list[AgentOutput] = []
        self._last_model_response: Optional[Any] = (
            None  # son kez önbellek ModelResponse, için kullanılır token istatistikler
        )

        # Çalışma dizini bağlam tarayıcısını başlatın
        try:
            from ..context import WorkspaceScanner

            project_path = config.get("project_path") if config else None
            if project_path:
                self.workspace_scanner = WorkspaceScanner(Path(project_path))
            else:
                self.workspace_scanner = WorkspaceScanner(Path.cwd())
        except Exception:
            # Tarayıcı bağlamı farkındalığının başarısız olması, Agent başlatma
            self.workspace_scanner = None

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Sistem istemi sözcüğüne geri dön (tanım Agent rol ve davranış)"""
        pass

    def get_workspace_context(self, max_depth: int = 3) -> str:
        """
        Çalışma dizini bağlamını alın

        Proje dizinini tarayın ve geliştirme için bir dosya ağacı yapısı oluşturun Agent bağlam farkındalığı.

        Args:
            max_depth: Maksimum tarama derinliği

        Returns:
            str: dosya ağacı bağlam dizesi
        """
        if self.workspace_scanner is None:
            return "[Çalışma dizini içeriği mevcut değil]"

        try:
            return self.workspace_scanner.to_context_string(max_depth=max_depth)
        except Exception as e:
            return f"[Çalışma dizini içerik taraması başarısız oldu: {e}]"

    def get_full_context(self, max_depth: int = 3) -> dict[str, str]:
        """
        Tam bağlamı alın (dosya + tarayıcı)

        Returns:
            Dict[str, str]: Katmak workspace Ve browser bağlam sözlüğü
        """
        from ..context import BrowserAwareness

        result = {
            "workspace": self.get_workspace_context(max_depth=max_depth),
        }

        try:
            awareness = BrowserAwareness()
            browser_ctx = asyncio.run(awareness.get_current_tab())
            result["browser"] = browser_ctx.to_context_string()
        except Exception:
            result["browser"] = "[Tarayıcı içeriği mevcut değil]"

        return result

    def get_context_prompt(self, context: AgentContext) -> str:
        """Bağlama göre ek bilgi istemi sözcükleri oluşturun"""
        parts = []

        if context.task_description:
            parts.append(f"## mevcut görev\n{context.task_description}")

        if context.project_path:
            parts.append(f"## Proje yolu\n{context.project_path}")

        # Çalışma dizini bağlamı ekle (dosya ağacı)
        workspace_ctx = self.get_workspace_context()
        if workspace_ctx and workspace_ctx != "[Çalışma dizini içeriği mevcut değil]":
            parts.append(f"## Proje dosya yapısı\n{workspace_ctx}")

        if context.relevant_files:
            files_str = "\n".join(str(f) for f in context.relevant_files)
            parts.append(f"## İlgili belgeler\n{files_str}")

        if context.previous_outputs:
            parts.append("## Ön çalışma sonuçları")
            for agent_name, output in context.previous_outputs.items():
                parts.append(f"### {agent_name}\n{output}")

        # Tier 0: Ekle Skill ampirik bağlam
        if context.skill_context:
            parts.append(context.skill_context)

        return "\n\n".join(parts)

    async def execute(self, context: AgentContext, **kwargs) -> AgentOutput:
        """
        Görevleri yürütme (şablon yöntemi)

        işlem:
        1. güncelleme durumu
        2. Hazırlanmak Prompt
        3. çağrı modeli
        4. İşlem sonrası
        5. Günlük çıkışı
        """
        import time

        start_time = time.time()

        self.status = AgentStatus.WORKING

        try:
            # Kullanıcı tarafından belirlenen modeli kaydedin (için _run orta route_and_call kullanmak)
            self._override_model = getattr(context, "override_model", None)

            # Hazırlanmak Prompt
            prompt = self._prepare_prompt(context)

            # uygulamak
            result = await self._run(context, prompt, **kwargs)

            # İşlem sonrası
            output = self._post_process(result, context)

            # doldurma token Kullanım istatistikleri (önbelleğe alınmış ModelResponse çıkarılan)
            if self._last_model_response is not None:
                usage = self._last_model_response.usage
                output.usage = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(usage, "completion_tokens", 0),
                    "total_tokens": getattr(usage, "total_tokens", 0),
                }

            output.execution_time = time.time() - start_time
            self.status = AgentStatus.COMPLETED

        except Exception as e:
            output = AgentOutput(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                error=f"{type(e).__name__}",  # Yalnızca türü kaydedin, ayrıntıları açıklamayın
                execution_time=time.time() - start_time,
            )
            self.status = AgentStatus.FAILED

        # geçmişi kaydet
        self._output_history.append(output)

        return output

    def _prepare_prompt(self, context: AgentContext) -> list[dict[str, str]]:
        """
        eksiksiz hazırlan Prompt

        Returns:
            List[Dict]: Mesaj listesi (sistem + kullanıcı)
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]

        context_prompt = self.get_context_prompt(context)
        if context_prompt:
            messages.append({"role": "user", "content": context_prompt})

        return messages

    @abstractmethod
    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """
        Gerçek yürütme mantığı (alt sınıf uygulaması)

        Args:
            context: yürütme bağlamı
            prompt: hazır Prompt
            **kwargs: ekstra parametreler

        Returns:
            str: Yürütme sonucu
        """
        pass

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """
        İşlem sonrası (alt sınıflar tarafından geçersiz kılınabilir)

        Varsayılan uygulama: doğrudan çıktı olarak paketlenir
        """
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
        )

    async def call_model(
        self,
        task_type: str,
        messages: list[Message],
        complexity: str = "medium",
        use_cache: bool = True,
        **kwargs,
    ) -> ModelResponse:
        """
        Modeli çağırın (kullanıcı tarafından belirlenen model geçersiz kılmalarını otomatik olarak enjekte eder)

        Destek aracı çağrıları:self.tools Boş olmadığında takım tanımını otomatik olarak enjekte edin,
        Model iadeleri tool_calls En fazla aracı otomatik olarak çalıştırın ve sonuçları döndürün 5 teker.
        """
        # Zorla enjeksiyon web_fetch Araçlar (tümü Agent varsayılan olarak mevcuttur)
        if "tools" not in kwargs:
            if "web_fetch" in SUPPORTED_TOOLS:
                kwargs["tools"] = [SUPPORTED_TOOLS["web_fetch"]]

        available_tools = {"web_fetch": self._web_fetch_tool}
        current_messages: list[Message] = list(messages)

        for _ in range(5):  # en 5 tekerlek aracı çağrısı
            response = await self.model_router.route_and_call(
                task_type=task_type,
                messages=current_messages,
                complexity=complexity,
                use_cache=use_cache,
                override_model=getattr(self, "_override_model", None),
                **kwargs,
            )
            self._last_model_response = response

            if not response.tool_calls:
                return response

            # Önce ekle assistant mesaj (ile tool_calls),DeepSeek bu siparişi gerektir
            current_messages.append(Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            ))

            # Araç çağrısını yürüt
            for tc in response.tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                func_args_str = tc.get("function", {}).get("arguments", "{}")
                try:
                    func_args = json.loads(func_args_str)
                except Exception:
                    func_args = {}

                if func_name in available_tools:
                    try:
                        result = await available_tools[func_name](func_args)
                    except Exception as e:
                        result = f"Error: {type(e).__name__}: {e}"
                else:
                    result = f"Error: unknown tool {func_name}"

                current_messages.append(Message(
                    role="tool",
                    content=result,
                    tool_call_id=tc.get("id", ""),
                    name=func_name,
                ))

            # Sonraki turlarda devredilmeyecektir. tools
            kwargs = {k: v for k, v in kwargs.items() if k != "tools"}

        return response

    async def _web_fetch_tool(self, args_json) -> str:
        """web_fetch Araçlar: Al URL Web sayfasının metin içeriği (HTML Düz metne dönüştürün)"""
        import json
        import re
        import subprocess
        # kabul etmek dict(doğrudan arama) veya JSON sicim(call_model (geçti)
        if isinstance(args_json, dict):
            args = args_json
        else:
            try:
                args = json.loads(args_json)
            except Exception:
                return f"[web_fetch error] Invalid arguments (not JSON): {str(args_json)[:200]}"

        url = args.get("url", "")
        if not url:
            return "[web_fetch error] Missing url parameter"

        try:
            result = subprocess.run(
                ["curl", "-s", "-L", "--max-time", "15", url],
                capture_output=True, timeout=20
            )
            html = result.stdout.decode("utf-8", errors="replace")[:8000]
            # Basit kaldırma HTML Etiket
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:8000]
        except Exception as e:
            return f"[web_fetch error] {type(e).__name__}: {e}"

    def get_last_output(self) -> Optional[AgentOutput]:
        """Son çıktıyı al"""
        return self._output_history[-1] if self._output_history else None

    def get_output_history(self) -> list[AgentOutput]:
        """Çıkış geçmişini alın"""
        return self._output_history.copy()

    async def call_subagent(
        self,
        agent_name: str,
        task: str,
        context: AgentContext,
        max_depth: int = 3,
    ) -> AgentOutput:
        """
        arayan Agent(P1-6 Agent Alt sistemin yeniden yapılandırılması Phase 1)

        akıma izin ver Agent Karmaşık görevleri parçalara ayırın ve bunları diğer profesyonellere devredin Agent uğraşmak.
        geçmek orchestrator Özyinelemeyi önleme ve zaman aşımı kontrolünü desteklemek için uygulanmıştır.

        Kullanım örnekleri (herhangi biri tarafından) Agent var olmak execute() Çağrıldı):
            result = await self.call_subagent(
                agent_name="analyst",
                task="Bu kodun performans darboğazlarını analiz edin",
                context=context,
            )
            if result.status == AgentStatus.COMPLETED:
                self.logger.info(f"Analyst Alt görev tamamlandı: {result.result}")

        Args:
            agent_name: oğul Agent Ad (örneğin "analyst", "planner")
            task: Alt görev açıklaması
            context: akım Agent yürütme bağlamı (iletilecek)
            max_depth: Maksimum arama derinliği, varsayılan 3

        Returns:
            AgentOutput: oğul Agent yürütme sonucu

        Raises:
            RuntimeError: eğer Orchestrator Enjekte edilmedi (olmamalı)
        """
        if self.orchestrator is None:
            raise RuntimeError(
                f"Agent '{self.name}' Alt çağrı yapılamıyor Agent:Orchestrator Enjekte edilmedi."
                "Lütfen iletildiğini onaylayın Orchestrator.get_agent() bunu yarat Agent Örnek."
            )

        # akımı değiştir Agent ile ilgili previous_outputs birleşmek context Zhonggongzi Agent kullanmak
        if not hasattr(context, "previous_outputs"):
            context.previous_outputs = {}  # type: ignore
        if self._output_history:
            context.previous_outputs[self.name] = self._output_history[-1]

        return await self.orchestrator.invoke_subagent(
            agent_name=agent_name,
            task=task,
            context={
                "project_path": str(context.project_path),
                "override_model": context.override_model,
                "skill_context": context.skill_context,
                "working_directory": str(context.working_directory)
                if context.working_directory
                else None,
                "previous_outputs": context.previous_outputs,
                "_subagent_depth": context.metadata.get("_subagent_depth", 0),
            },
            max_depth=max_depth,
        )

    def save_output(self, output_path: Path):
        """Çıktıyı dosyaya kaydet"""
        if not self._output_history:
            return

        last_output = self._output_history[-1]
        output_file = (
            output_path / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "agent": last_output.agent_name,
                    "status": last_output.status.value,
                    "result": last_output.result,
                    "artifacts": last_output.artifacts,
                    "recommendations": last_output.recommendations,
                    "error": last_output.error,
                    "timestamp": last_output.timestamp,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )


# Agent Kayıt defteri (dinamik keşif ve oluşturma için)
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {}


def register_agent(agent_class: type[BaseAgent]):
    """kayıt olmak Agent"""
    AGENT_REGISTRY[agent_class.name] = agent_class
    return agent_class


def get_agent(name: str) -> Optional[type[BaseAgent]]:
    """Kayıt olun Agent"""
    return AGENT_REGISTRY.get(name)


def list_all_agents() -> list[dict[str, Any]]:
    """
    Tüm kayıtlı olanları listele Agent

    Returns:
        Agent Bilgi listesi, her öğe içerir name, description, lane, default_tier Beklemek
    """
    result = []
    for name, agent_class in AGENT_REGISTRY.items():
        info = {
            "name": name,
            "description": getattr(agent_class, "description", ""),
            "lane": getattr(agent_class, "lane", ""),
            "default_tier": getattr(agent_class, "default_tier", ""),
            "icon": getattr(agent_class, "icon", ""),
        }
        result.append(info)
    return result


def list_agents() -> list[str]:
    """Tüm kayıtlı olanları listele Agent"""
    return list(AGENT_REGISTRY.keys())
