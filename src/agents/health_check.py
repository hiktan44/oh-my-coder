from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Agent Durum kontrolü ve arızaların otomatik olarak yeniden dağıtılması

HealthChecker tür:
- Her 60 Tüm aktifleri kontrol etmek için saniyeler yeterli Agent durum
- Karar başarısızlığı koşulu: zaman aşımı (>5min Kalp atışı yok), anormal çıkış, görev hatası
- Başarısızlıktan sonra görevleri otomatik olarak boşta olanlara yeniden atayın Agent
- retry_count üst sınır 3 aşıldıktan sonra işaretlenen zamanlar failed ve bildir

Yeni veri yapısı:
- AgentHealth: agent_name / status / last_heartbeat / task_id / retry_count
- HealthCheckResult: Her denetimin sonuçları (günlük kaydedilebilir)
"""


import asyncio
import contextlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..core.orchestrator import Orchestrator, WorkflowStep


# ------------------------------------------------------------------
# veri yapısı
# ------------------------------------------------------------------


class AgentStatus(Enum):
    """Agent durum"""

    HEALTHY = "healthy"
    STALE = "stale"  # Kalp atışı olmadan zaman aşımı
    FAILED = "failed"
    REASSIGNED = "reassigned"


@dataclass
class AgentHealth:
    """Bekar Agent sağlık durumu"""

    agent_name: str
    status: AgentStatus = AgentStatus.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)
    task_id: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    workflow_id: Optional[str] = None
    step_index: int = -1  # İş akışındaki adım dizini

    # retry üst limit (yapılandırılabilir)
    MAX_RETRIES: int = field(default=3, repr=False)

    def touch(self) -> None:
        """Kalp atışı süresini güncelle"""
        self.last_heartbeat = time.time()
        if self.status == AgentStatus.STALE:
            self.status = AgentStatus.HEALTHY

    def is_stale(self, threshold: float = 300.0) -> bool:
        """Zaman aşımının kalp atışı olmadan gerçekleşip gerçekleşmeyeceğini belirleme"""
        return (time.time() - self.last_heartbeat) > threshold

    def record_failure(self, error: str) -> bool:
        """
        Bir başarısızlığı kaydedin ve yeniden deneme sınırının aşılıp aşılmadığını geri gönderin.

        - beğenmek retry_count < MAX_RETRIES → Yeniden denenebilir (durum şu şekilde değiştirildi: STALE)
        - beğenmek retry_count >= MAX_RETRIES → Tekrar denenemez (durum şu şekilde değiştirildi: FAILED)
        """
        self.retry_count += 1
        self.last_error = error
        self.last_heartbeat = time.time()  # Tekrarlanan belirlemeyi önlemek için kalp atışını sıfırlayın

        if self.retry_count >= self.MAX_RETRIES:
            self.status = AgentStatus.FAILED
            return True  # Sınıra ulaşıldı
        self.status = AgentStatus.STALE
        return False  # Yine de tekrar deneyebilirsin

    def can_retry(self) -> bool:
        return self.retry_count < self.MAX_RETRIES

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["last_heartbeat"] = datetime.fromtimestamp(self.last_heartbeat).isoformat()
        d.pop("MAX_RETRIES")  # Sabitleri serileştirmeyin
        return d


@dataclass
class HealthCheckResult:
    """Tek bir sağlık kontrolünün sonuçları"""

    check_id: str
    checked_agents: int
    healthy_count: int
    stale_count: int
    failed_count: int
    reassigned_count: int
    reassignments: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("check_id")
        return d


# ------------------------------------------------------------------
# HealthChecker
# ------------------------------------------------------------------


class HealthChecker:
    """
    Agent sağlık denetleyicisi

    İşlev:
    1. Tümünü aktif tut Agent sağlık durumu kaydı
    2. Periyodik kontrol (varsayılan 60 saniye aralığı) kalp atışı ve başarısızlık
    3. Bir başarısızlıktan sonra görevleri otomatik olarak boştaki görevlere yeniden atayın Agent
    4. Yeniden deneme sınırı 3 kez aşın ve kullanıcıyı bilgilendirin
    5. Sonuçlar sürdürülür .omc/state/health/
    """

    def __init__(
        self,
        orchestrator: Optional[Orchestrator] = None,
        check_interval: float = 60.0,
        stale_threshold: float = 300.0,
        max_retries: int = 3,
        state_dir: Optional[Path] = None,
        on_notification: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Args:
            orchestrator: Orchestrator Örnek (görevin yeniden dağıtımı için)
            check_interval: Kontrol aralığı (saniye), varsayılan 60
            stale_threshold: Kalp atışı zaman aşımı eşiği (saniye), varsayılan 300(5 dakika)
            max_retries: Bekar Agent Maksimum başarısız yeniden deneme sayısı, varsayılan 3
            state_dir: Durum dosyası dizini
            on_notification: Bildirim geri araması (title: str, body: str) -> None
        """
        self.orchestrator = orchestrator
        self.check_interval = check_interval
        self.stale_threshold = stale_threshold
        self.max_retries = max_retries
        self.state_dir = state_dir or Path(".omc/state/health")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.on_notification = on_notification

        # Agent Sağlık durumu:agent_name -> AgentHealth
        self._agent_health: dict[str, AgentHealth] = {}

        # Aktif kalp atışı:agent_name -> asyncio.Task(Görev şu anda yürütülüyor)
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}

        # arka plan kontrol döngüsü
        self._check_task: Optional[asyncio.Task[None]] = None
        self._stop_event: Optional[asyncio.Event] = None

        # Geçmişi kontrol et
        self._history: list[HealthCheckResult] = []

        # Toplam istatistikler
        self._total_reassignments = 0

    # ------------------------------------------------------------------
    # kalp atışı kaydı
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_name: str,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        step_index: int = -1,
    ) -> AgentHealth:
        """
        Kayıt ol Agent Görevi yürütmeye başlayın (kalp atışı zamanlamayı başlatır).

        var olmak Agent Yürütme başladığında çağrılır.
        """
        health = AgentHealth(
            agent_name=agent_name,
            status=AgentStatus.HEALTHY,
            last_heartbeat=time.time(),
            task_id=task_id,
            workflow_id=workflow_id,
            step_index=step_index,
        )
        health.MAX_RETRIES = self.max_retries
        self._agent_health[agent_name] = health
        return health

    def unregister_agent(self, agent_name: str) -> bool:
        """Kaydı sil (görev tamamlandıktan sonra çağrılır)"""
        if agent_name in self._agent_health:
            del self._agent_health[agent_name]
        if agent_name in self._active_tasks:
            del self._active_tasks[agent_name]
        return True

    def register_task(self, agent_name: str, task: asyncio.Task[Any]) -> None:
        """kayıt olmak Agent Şu anda yürütülüyor asyncio.Task(iptal için)"""
        self._active_tasks[agent_name] = task

    def heartbeat(self, agent_name: str) -> bool:
        """
        yenilemek Agent Kalp atışı.

        var olmak Agent Yürütme sırasında periyodik olarak çağrılır (her biri gibi) LLM arama tamamlandıktan sonra).

        Returns:
            True = normal,False = Agent Kayıtlı değil
        """
        if agent_name not in self._agent_health:
            return False
        self._agent_health[agent_name].touch()
        return True

    # ------------------------------------------------------------------
    # Arıza kaydı ve yeniden dağıtım
    # ------------------------------------------------------------------

    def record_failure(
        self,
        agent_name: str,
        error: str,
        workflow_id: Optional[str] = None,
        step: Optional[WorkflowStep] = None,
    ) -> bool:
        """
        Kayıt Agent Yürütme başarısız oldu.

        Args:
            agent_name: arızalı Agent
            error: hata mesajı
            workflow_id: Ait iş akışı ID
            step: arızalı WorkflowStep(yeniden tahsis için)

        Returns:
            True = Yeniden deneme sınırına ulaşıldı (kullanıcının bilgilendirilmesi gerekiyor)
            False = Hala yeniden deneniyor
        """
        if agent_name not in self._agent_health:
            health = self.register_agent(agent_name, workflow_id=workflow_id)
        else:
            health = self._agent_health[agent_name]

        exceeded = health.record_failure(error)

        if exceeded:
            # Kullanıcıya bildir
            self._notify(
                f"⚠️ Agent {agent_name} hata",
                f"Yeniden denendi {health.retry_count} Yine de başarısız olduğundan görevden vazgeçildi."
                f"\n\nhata:{error[:200]}",
            )
        else:
            # Yeniden tahsisi tetikleyin
            self._notify(
                f"🔄 Agent {agent_name} Yürütme istisnası, yeniden deneniyor",
                f"Tekrar deneyin {health.retry_count}/{self.max_retries}\nhata:{error[:100]}",
            )

        self._save_health_log(health)
        return exceeded

    def reassign_task(
        self,
        agent_name: str,
        workflow_id: str,
        step: WorkflowStep,
    ) -> Optional[str]:
        """
        Görevleri boşta olana yeniden atayın Agent.

        Strateji:
        1. Tüm kayıtlı olanları yineleyin Agentdurumu şu şekilde bulun: HEALTHY meşgul değil
        2. Bulunamazsa yeni bir tane oluşturun executor agent
        3. Yeni tahsis edileni iade et agent_name

        Returns:
            yeni tahsis edilmiş agent_name,veya None(yeniden tahsis edilemez)
        """
        # Ücretsiz akranlar bulun Agent
        for name, health in self._agent_health.items():
            if (
                name != agent_name
                and health.status == AgentStatus.HEALTHY
                and name not in self._active_tasks
            ):
                new_agent_name = name
                self._log_reassignment(
                    from_agent=agent_name,
                    to_agent=new_agent_name,
                    reason=f"agent {agent_name} failed",
                    step=step.agent_name,
                    workflow_id=workflow_id,
                )
                return new_agent_name

        # Agent bulunamadı; hata kaydedildi ama devam ediliyor
        self._log_reassignment(
            from_agent=agent_name,
            to_agent="<none>",
            reason="no idle agent available",
            step=step.agent_name,
            workflow_id=workflow_id,
        )
        return None

    def _log_reassignment(
        self,
        from_agent: str,
        to_agent: str,
        reason: str,
        step: str,
        workflow_id: str,
    ) -> None:
        """Yeniden tahsis olaylarını günlüğe kaydet"""
        self._total_reassignments += 1
        log_entry = {
            "id": str(uuid.uuid4())[:8],
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "step": step,
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
        }

        log_file = self.state_dir / f"reassignment_{log_entry['id']}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Periyodik muayene döngüsü
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Arka plan durum denetimi döngüsünü başlat"""
        if self._check_task is not None:
            return  # Başlatıldı

        self._stop_event = asyncio.Event()
        self._check_task = asyncio.create_task(self._check_loop())
        self._save_status()

    async def stop(self) -> None:
        """Durum denetimi döngüsünü durdur"""
        if self._check_task is None:
            return

        self._stop_event.set()
        await self._check_task
        self._check_task = None
        self._stop_event = None
        self._save_status()

    async def _check_loop(self) -> None:
        """Arka plan kontrol döngüsü: her check_interval Saniyede bir kez çalıştır"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                if self._stop_event and self._stop_event.is_set():
                    break

                result = await self._check_all()
                if result:
                    self._history.append(result)
                    # Yalnızca en güncel olanı sakla 100 şerit
                    if len(self._history) > 100:
                        self._history = self._history[-100:]

            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Sessizlik, çöküş yok

    async def _check_all(self) -> Optional[HealthCheckResult]:
        """
        Tam bir inceleme yapın.

        Algılama STALE(zaman aşımı) Agent, yeniden denemeyi tetikliyor.
        """
        if not self._agent_health:
            return None

        checked = 0
        healthy = 0
        stale = 0
        failed = 0
        reassigned = 0
        reassignments: list[dict[str, Any]] = []

        for agent_name, health in list(self._agent_health.items()):
            # atlama tamamlandı/arızalı
            if health.status in (AgentStatus.FAILED, AgentStatus.REASSIGNED):
                continue

            checked += 1

            # Zaman aşımına uğrayıp uğramadığını kontrol edin
            if health.is_stale(self.stale_threshold):
                stale += 1
                health.status = AgentStatus.STALE

                if health.can_retry():
                    # Kayıt başarısız oldu, yeniden tahsis tetikleniyor
                    health.record_failure(
                        f"Kalp atışı zaman aşımı (>{self.stale_threshold}s Yanıt yok)"
                    )
                    reassigned += 1
                    reassignments.append(
                        {
                            "agent": agent_name,
                            "reason": "heartbeat_timeout",
                            "retry_count": health.retry_count,
                            "workflow_id": health.workflow_id,
                        }
                    )
                else:
                    failed += 1
                    health.status = AgentStatus.FAILED
                    self._notify(
                        f"❌ Agent {agent_name} Terk edilmiş",
                        f"sürekli {health.retry_count} zaman aşımı, görev durur.",
                    )

                self._save_health_log(health)
            else:
                healthy += 1

        result = HealthCheckResult(
            check_id=str(uuid.uuid4())[:8],
            checked_agents=checked,
            healthy_count=healthy,
            stale_count=stale,
            failed_count=failed,
            reassigned_count=reassigned,
            reassignments=reassignments,
        )

        self._save_check_result(result)
        return result

    # ------------------------------------------------------------------
    # Durum görünümü
    # ------------------------------------------------------------------

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        """Hepsini al Agent sağlık durumu"""
        return {name: h.to_dict() for name, h in self._agent_health.items()}

    def get_summary(self) -> dict[str, Any]:
        """Durum denetimi özetini alın"""
        statuses = [h.status for h in self._agent_health.values()]
        return {
            "total_registered": len(self._agent_health),
            "healthy": sum(1 for s in statuses if s == AgentStatus.HEALTHY),
            "stale": sum(1 for s in statuses if s == AgentStatus.STALE),
            "failed": sum(1 for s in statuses if s == AgentStatus.FAILED),
            "reassigned": sum(1 for s in statuses if s == AgentStatus.REASSIGNED),
            "total_reassignments": self._total_reassignments,
            "running": len(self._active_tasks),
            "check_interval": self.check_interval,
            "stale_threshold": self.stale_threshold,
            "max_retries": self.max_retries,
            "is_running": self._check_task is not None,
        }

    # ------------------------------------------------------------------
    # sebat
    # ------------------------------------------------------------------

    def _save_health_log(self, health: AgentHealth) -> None:
        """tekli kaydet Agent sağlık günlüğü"""
        log_file = self.state_dir / f"health_{health.agent_name}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(health.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_check_result(self, result: HealthCheckResult) -> None:
        """Test sonuçlarını kaydet"""
        log_file = self.state_dir / f"check_{result.check_id}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_status(self) -> None:
        """Genel durum özetini kaydet"""
        status_file = self.state_dir / "status.json"
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(self.get_summary(), f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # bildirmek
    # ------------------------------------------------------------------

    def _notify(self, title: str, body: str) -> None:
        """Bildirim gönder"""
        if self.on_notification:
            with contextlib.suppress(Exception):
                self.on_notification(title, body)
        # Günlük dosyalarını da yazabilir
        log_file = self.state_dir / "notifications.jsonl"
        entry = {
            "title": title,
            "body": body,
            "timestamp": datetime.now().isoformat(),
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------
# CLI Çıkış formatı
# ------------------------------------------------------------------


def format_health_display(health_map: dict[str, dict[str, Any]]) -> str:
    """
    Şunun için sağlık durumunu okunabilir metin olarak biçimlendir: `omc agent health` çıktı.
    """
    if not health_map:
        return "  (no agents registered)"

    lines = []
    status_emoji = {
        "healthy": "✅",
        "stale": "⚠️",
        "failed": "❌",
        "reassigned": "🔄",
    }

    for name, h in health_map.items():
        emoji = status_emoji.get(h["status"], "?")
        retry = h.get("retry_count", 0)
        heartbeat = h.get("last_heartbeat", "")
        workflow = h.get("workflow_id") or "—"
        error = h.get("last_error", "") or ""

        lines.append(f"{emoji} {name}")
        lines.append(
            f"   status: {h['status']}  |  retries: {retry}  |  workflow: {workflow}"
        )
        if heartbeat:
            lines.append(f"   heartbeat: {heartbeat}")
        if error:
            lines.append(f"   error: {error[:80]}")
        lines.append("")

    return "\n".join(lines).rstrip()
