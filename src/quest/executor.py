from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Quest yurutmotor

sorumlugorevsonraplatformyurut, destekgercekduraklat/kurtar. 
kullan asyncio icindesonraplatformsatir omc is akisi, zamanizleizleilerlederece. 
"""

import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path

from .models import Quest, QuestNotification, QuestStatus, QuestStep
from .store import QuestStore


class QuestExecutor:
    """Quest sonraplatformyurutmotor"""

    def __init__(
        self,
        project_path: Path,
        store: QuestStore,
        notify_callback: Optional[Callable[[QuestNotification], None]] = None,
        replan_callback: Optional[Callable[[str, str], None]] = None,
        review_callback: Optional[Callable[[str, str, str], Awaitable[str]]] = None,
    ):
        self.project_path = Path(project_path)
        self.store = store
        self.notify_callback = notify_callback
        # basarisizzamantetikgondertekrarplanlageri arama (iletgiris quest_id, failed_step_id) 
        self.replan_callback = replan_callback
        # dogrulaalgeri arama: iletgiris quest_id, step_id, result_preview, donus "pass"/"retry"/"skip"
        self.review_callback = review_callback
        # satirzamandurum (icindekaydeticinde) : depolamamevcutvb.beklegirdiadim
        self._running_quests: dict[str, asyncio.Task] = {}
        # kesnoktakayit: quest_id -> mevcutadimindeks
        self._breakpoint: dict[str, int] = {}

    def _notify(
        self, quest: Optional[Quest], event: str, message: str, details=None
    ) -> None:
        """gondergonderbildirim"""
        if self.notify_callback:
            notification = QuestNotification(
                quest_id=quest.id if quest else "unknown",
                title=quest.title if quest else "",
                event=event,
                message=message,
                details=details,
            )
            self.notify_callback(notification)

    # ============================================================
    # baslatyurut
    # ============================================================

    def start(self, quest: Quest) -> None:
        """baslatsonraplatformyurut (sadecebaslat, hayiryapacakblokla) """
        if quest.id in self._running_quests:
            return  # zatenicindesatir

        task = asyncio.create_task(self._execute_quest(quest))
        self._running_quests[quest.id] = task

    async def _execute_quest(self, quest: Quest) -> None:
        """asenkronyurut Quest anadongu (destekkesnoktadevamkos) """
        try:
            self.store.update_status(quest.id, QuestStatus.EXECUTING)
            fresh = self.store.get(quest.id)
            if fresh is None:
                return

            self._notify(fresh, "started", f"🧙 Quest baslat: {fresh.title}")

            # kesinkalkbaslangicadim (kesnoktadevamkos) 
            start_index = self._breakpoint.pop(quest.id, 0)

            #  SPEC olusturadim (sadeceilkkezolustur, sonradevam store kurtar) 
            if not fresh.steps:
                steps = self._generate_steps(fresh)
                fresh.steps = steps
                self.store.save(fresh)
            else:
                steps = fresh.steps

            # yurutheradim (atlatamamla/basarisiz) 
            for i, step in enumerate(steps):
                # atlatamamlaadim
                if i < start_index:
                    continue

                # herkeziterasyontumtekraryeniokuenyenidurum
                fresh = self.store.get(quest.id)
                if fresh is None:
                    return

                # kontroliptal/duraklat
                if fresh.status == QuestStatus.CANCELLED:
                    self._notify(fresh, "cancelled", "⏹️ Quest iptal edildi")
                    return
                if fresh.status == QuestStatus.PAUSED:
                    # kaydetkesnoktakonum
                    self._breakpoint[quest.id] = i
                    self._notify(
                        fresh,
                        "paused",
                        f"⏸️ Quest duraklat (icindeadim {step.step_id} kurtar) ",
                    )
                    return

                # guncellemevcutadimdurum
                step.status = QuestStatus.EXECUTING
                self.store.save(fresh)

                try:
                    result = await self._execute_step(step, fresh)
                    step.result = result
                    # ilerlegirisdogrulaaldurum, vb.beklekullanicionayla
                    step.status = QuestStatus.PENDING_REVIEW
                    fresh.status = QuestStatus.PENDING_REVIEW
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "pending_review",
                        f"⏳ adim [{step.step_id}] {step.title} yuruttamamla, vb.bekledogrulaal",
                        details={
                            "step_id": step.step_id,
                            "result_preview": result[:200] if result else "",
                        },
                    )
                    # vb.beklekullanicidogrulaal (blokla) 
                    review_result = await self._wait_for_review(fresh.id, step.step_id)
                    if review_result == "retry":
                        # yeniden denemevcutadim
                        step.status = QuestStatus.PENDING
                        step.result = None
                        self.store.save(fresh)
                        i -= 1  # gerigeriindeksyeniden dene
                        continue
                    if review_result == "skip":
                        # atla (isareticinuyari) 
                        step.status = QuestStatus.COMPLETED
                        step.completed_at = datetime.now()
                        step.notes = "kullaniciatladogrulaal"
                        self.store.save(fresh)
                        self._notify(
                            fresh, "step_skipped", f"⏭️ adim [{step.step_id}] atla"
                        )
                    else:
                        # araciligiyla
                        step.status = QuestStatus.COMPLETED
                        step.completed_at = datetime.now()
                        self.store.save(fresh)
                        self._notify(
                            fresh,
                            "step_completed",
                            f"✅ adim [{step.step_id}] {step.title} dogrulaalaraciligiyla",
                        )
                except asyncio.CancelledError:
                    # duraklat/iptalvurkes
                    self.store.save(fresh)
                    self._breakpoint[quest.id] = i
                    return
                except Exception as e:
                    step.status = QuestStatus.FAILED
                    step.error = type(e).__name__
                    fresh.error_message = f"adim {step.step_id} basarisiz"
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "failed",
                        f"⚠️ adim [{step.step_id}] {step.title} basarisiz",
                        details={"step_id": step.step_id, "error": type(e).__name__},
                    )
                    # tetikgondertekrarplanlageri arama
                    if self.replan_callback:
                        try:
                            self.replan_callback(fresh.id, step.step_id)
                        except Exception as cb_err:
                            self._notify(
                                fresh, "replan_error", f"tekrarplanlageri aramabasarisiz: {cb_err}"
                            )
                    # devamdevamyurutsonradevamadim
                    continue

            # varadimtamamla
            fresh = self.store.get(quest.id)
            if fresh and fresh.status == QuestStatus.EXECUTING:
                failed_count = sum(
                    1 for s in fresh.steps if s.status == QuestStatus.FAILED
                )
                if failed_count == 0:
                    self.store.update_status(fresh.id, QuestStatus.COMPLETED)
                    fresh.result_summary = f"✅ tumkisim {len(fresh.steps)} adimbasarilitamamla"
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "completed",
                        f"🎉 Quest tamamla: {fresh.title}",
                    )
                else:
                    self.store.update_status(fresh.id, QuestStatus.FAILED)
                    fresh.result_summary = (
                        f"{len(fresh.steps) - failed_count}/{len(fresh.steps)} adimbasarili"
                    )
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "failed",
                        f"⚠️ Quest tamamlaancakvar {failed_count} adimbasarisiz",
                    )

        except Exception as e:
            self.store.update_status(quest.id, QuestStatus.FAILED)
            fresh = self.store.get(quest.id)
            if fresh:
                fresh.error_message = type(e).__name__
                self.store.save(fresh)
            self._notify(
                fresh,
                "failed",
                "❌ Quest yurutbasarisiz",
            )
        finally:
            self._running_quests.pop(quest.id, None)
            self._breakpoint.pop(quest.id, None)

    async def _wait_for_review(self, quest_id: str, step_id: str) -> str:
        """vb.beklekullanicidogrulaaladimsonuc

        Returns:
            "pass" - dogrulaalaraciligiyla
            "retry" - yeniden denebuadim
            "skip" - atlabuadim
        """
        if self.review_callback:
            quest = self.store.get(quest_id)
            step = (
                next((s for s in quest.steps if s.step_id == step_id), None)
                if quest
                else None
            )
            preview = step.result[:500] if step and step.result else ""
            try:
                return await self.review_callback(quest_id, step_id, preview)
            except Exception as e:
                self._notify(quest, "review_error", f"dogrulaalgeri aramabasarisiz: {e}")
                return "pass"  # varsayilanaraciligiyla
        # yokvargeri aramazamanvarsayilanaraciligiyla
        return "pass"

    def _generate_steps(self, quest: Quest) -> list[QuestStep]:
        """ SPEC olusturyurutadim"""
        steps: list[QuestStep] = []

        if not quest.spec or not quest.spec.acceptance_criteria:
            return [
                QuestStep(
                    step_id="S1",
                    title="analizgerekiste",
                    description=f"analizveanla: {quest.description}",
                    agent="analyst",
                ),
                QuestStep(
                    step_id="S2",
                    title="planlauygula",
                    description="olusturuygulaplan",
                    agent="planner",
                ),
                QuestStep(
                    step_id="S3",
                    title="yurutduzenlekod",
                    description="goregoreplanyurutduzenlekod",
                    agent="executor",
                ),
                QuestStep(
                    step_id="S4",
                    title="dogrulama sonucu",
                    description="test dogrulama calistir",
                    agent="verifier",
                ),
            ]

        # temelde acceptance_criteria olusturadim
        ac_chunks = [
            quest.spec.acceptance_criteria[i : i + 3]
            for i in range(0, len(quest.spec.acceptance_criteria), 3)
        ]

        for i, chunk in enumerate(ac_chunks, 1):
            criteria_text = "; ".join(ac.description for ac in chunk)
            steps.append(
                QuestStep(
                    step_id=f"S{i}",
                    title=f"uygula: {criteria_text[:30]}...",
                    description=f"kabul kriterleri: {criteria_text}",
                    agent="executor",
                )
            )

        steps.append(
            QuestStep(
                step_id=f"S{len(steps) + 1}",
                title="kodinceleme",
                description="ilerlesatirkodincelemevekalitemiktarkontrol",
                agent="code-reviewer",
            )
        )

        return steps

    async def _execute_step(self, step: QuestStep, quest: Quest) -> str:
        """yuruttekiladim"""
        project_path = quest.project_path

        cmd = [
            sys.executable,
            "-m",
            "oh_my_coder",
            "run",
            step.description,
            "--project",
            project_path,
            "--workflow",
            "build",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_path,
            env={**os.environ},
        )

        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"komutbasarisiz (code={proc.returncode}): {error[:500]}")

        return output[:2000]

    # ============================================================
    # kontrolislem
    # ============================================================

    def stop(self, quest_id: str) -> bool:
        """kuryanidurdur (hayirvb.tamamla, dogrubaglaniptalgorev) """
        task = self._running_quests.pop(quest_id, None)
        if task:
            task.cancel()
            return True
        return False

    def cancel(self, quest_id: str) -> bool:
        """iptal Quest"""
        self.stop(quest_id)
        self._breakpoint.pop(quest_id, None)
        return bool(self.store.update_status(quest_id, QuestStatus.CANCELLED))

    def pause(self, quest_id: str) -> bool:
        """duraklat Quest (icindemevcutadimtamamlasonraduraklat) """
        quest = self.store.get(quest_id)
        if quest is None:
            return False

        # egersatir, durdurgorev, altkezbaslatzamanyapacakkesnoktadevamdevam
        self.stop(quest_id)

        # bulkadarmevcutyurutadimindeks
        running_idx = 0
        for i, step in enumerate(quest.steps):
            if step.status == QuestStatus.EXECUTING:
                running_idx = i
                break
            if step.status in (QuestStatus.PENDING, QuestStatus.EXECUTING):
                running_idx = i
                break

        self._breakpoint[quest_id] = running_idx
        return bool(self.store.update_status(quest_id, QuestStatus.PAUSED))

    def resume(self, quest_id: str) -> Optional[Quest]:
        """kurtarduraklat Quest, kesnoktadevamdevam"""
        quest = self.store.get(quest_id)
        if quest is None or quest.status != QuestStatus.PAUSED:
            return None

        # temizlehariconcekesnokta (yapacakkaydetadimdevamdevam) 
        self._breakpoint.pop(quest_id, None)
        self.store.update_status(quest_id, QuestStatus.EXECUTING)
        quest = self.store.get(quest_id)
        if quest:
            self.start(quest)
        return quest

    def is_running(self, quest_id: str) -> bool:
        """kontrol Quest olup olmadigiicindesatir"""
        return quest_id in self._running_quests

    def get_breakpoint(self, quest_id: str) -> Optional[int]:
        """alduraklatzamankesnoktakonum"""
        return self._breakpoint.get(quest_id)
