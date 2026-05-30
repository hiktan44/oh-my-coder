from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Quest yonet

biryonet Quest olustur, SPEC olustur, yurut, sorgu. 
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

from ..core.router import ModelRouter, RouterConfig
from .executor import QuestExecutor
from .models import Quest, QuestNotification, QuestStatus
from .spec_generator import SpecGenerator
from .store import QuestStore


class QuestManager:
    """
    Quest Mode toplamyonet

    kullanyontem:
        manager = QuestManager(project_path)
        quest = await manager.create_quest("uygulakullanicikimlik dogrulama")
        quest = await manager.generate_spec(quest)  # olustur SPEC
        manager.confirm_and_execute(quest)           # onaylasonrayurut
        quests = manager.list_quests()                # goruntuledurum
    """

    def __init__(
        self,
        project_path: Path,
        notify_callback: Optional[Callable[[QuestNotification], None]] = None,
        review_callback: Optional[Callable[[str, str, str], Awaitable[str]]] = None,
    ):
        self.project_path = Path(project_path)
        self.store = QuestStore(self.project_path)
        self.notify_callback = notify_callback
        self.review_callback = review_callback

        # gecikmebaslat ModelRouter
        self._router: Optional[ModelRouter] = None
        self._executor: Optional[QuestExecutor] = None

    @property
    def router(self) -> ModelRouter:
        if self._router is None:
            self._router = ModelRouter(RouterConfig())
        return self._router

    @property
    def executor(self) -> QuestExecutor:
        if self._executor is None:
            self._executor = QuestExecutor(
                project_path=self.project_path,
                store=self.store,
                notify_callback=self.notify_callback,
                review_callback=self.review_callback,
            )
        return self._executor

    # ============================================================
    # cekirdekislem
    # ============================================================

    async def create_quest(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "medium",
    ) -> Quest:
        """olusturyeni Quest"""
        return self.store.create(
            title=title or self._extract_title(description),
            description=description,
            project_path=str(self.project_path),
        )

    async def generate_spec(self, quest: Quest) -> Quest:
        """
        icin Quest olustur SPEC

        yapacakotomatikguncelle quest.spec ve quest.spec_path
        """
        # guncelledurum
        self.store.update_status(quest.id, QuestStatus.SPEC_GENERATING)

        try:
            generator = SpecGenerator(
                model_router=self.router,
                project_path=self.project_path,
            )
            spec = await generator.generate(quest)
            self.store.set_spec(quest.id, spec)
            self.store.update_status(quest.id, QuestStatus.SPEC_READY)
        except Exception as e:
            self.store.update_status(quest.id, QuestStatus.FAILED)
            quest = self.store.get(quest.id)
            if quest:
                quest.error_message = f"SPEC olusturbasarisiz: {e}"
                self.store.save(quest)
            raise

        return self.store.get(quest.id)

    def confirm_and_execute(self, quest_id: str) -> Quest:
        """kullanicionayla SPEC sonra, baslatsonraplatformyurut"""
        quest = self.store.get(quest_id)
        if quest is None:
            raise ValueError(f"Quest {quest_id} mevcut degil")

        if quest.status != QuestStatus.SPEC_READY:
            raise ValueError(
                f"Quest durumicin {quest.status}, gerekister SPEC_READY durumyetenekedebiliryurut"
            )

        self.store.update_status(quest_id, QuestStatus.EXECUTING)
        quest = self.store.get(quest_id)
        if quest:
            self.executor.start(quest)
        return self.store.get(quest_id)

    def execute_without_spec(self, quest_id: str) -> Quest:
        """dogrubaglanyurut (hayirolustur SPEC) """
        quest = self.store.get(quest_id)
        if quest is None:
            raise ValueError(f"Quest {quest_id} mevcut degil")

        self.executor.start(quest)
        return quest

    # ============================================================
    # sorguislem
    # ============================================================

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """altekil Quest"""
        return self.store.get(quest_id)

    def list_quests(
        self,
        status_filter: Optional[QuestStatus] = None,
    ) -> list[Quest]:
        """listele Quest"""
        return self.store.list(status_filter=status_filter)

    def get_active_quests(self) -> list[Quest]:
        """alaktif Quest"""
        quests = self.store.list()
        active_statuses = {
            QuestStatus.PENDING,
            QuestStatus.SPEC_GENERATING,
            QuestStatus.SPEC_READY,
            QuestStatus.EXECUTING,
            QuestStatus.PAUSED,
        }
        return [q for q in quests if q.status in active_statuses]

    # ============================================================
    # kontrolislem
    # ============================================================

    def cancel(self, quest_id: str) -> bool:
        """iptal Quest"""
        return self.executor.cancel(quest_id)

    def stop(self, quest_id: str) -> bool:
        """durduryurut"""
        return self.executor.stop(quest_id)

    def pause(self, quest_id: str) -> bool:
        """duraklat"""
        return self.executor.pause(quest_id)

    def resume(self, quest_id: str) -> Optional[Quest]:
        """kurtar"""
        return self.executor.resume(quest_id)

    def delete(self, quest_id: str) -> bool:
        """sil Quest"""
        return self.store.delete(quest_id)

    def is_running(self, quest_id: str) -> bool:
        """kontrololup olmadigiicindesatir"""
        return self.executor.is_running(quest_id)

    # ============================================================
    # yardimciyontem
    # ============================================================

    def _extract_title(self, description: str) -> str:
        """aciklamaicindecikarbasittemizbaslik"""
        # alonce 50 karakter
        title = description.strip()[:50]
        if len(description) > 50:
            title += "..."
        return title
