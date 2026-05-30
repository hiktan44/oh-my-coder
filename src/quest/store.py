from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Quest kalicidepolama

kullan JSON dosyadepolama Quest liste, her Quest tekiltekbir JSON dosya. 
depolamaicinde <project_path>/.omc/quests/ dizinalt. 
"""

import builtins
import json
import uuid
from datetime import datetime
from pathlib import Path

from .models import Quest, QuestSpec, QuestStatus


class QuestStore:
    """Quest kalicidepolama"""

    def __init__(self, project_path: Path | str):
        project_path = Path(project_path)
        self.project_path = project_path
        self.quests_dir = project_path / ".omc" / "quests"
        self._quests_cache: dict[str, Quest] = {}

    def _ensure_dir(self) -> None:
        """kesinkaydetdepoladizinkaydeticinde"""
        self.quests_dir.mkdir(parents=True, exist_ok=True)

    def _quest_file(self, quest_id: str) -> Path:
        """al Quest dosyayol"""
        return self.quests_dir / f"{quest_id}.json"

    # ============================================================
    # CRUD islem
    # ============================================================

    def create(self, title: str, description: str, project_path: str) -> Quest:
        """olusturyeni Quest"""
        self._ensure_dir()
        quest = Quest(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            project_path=project_path,
        )
        self._save(quest)
        return quest

    def get(self, quest_id: str) -> Optional[Quest]:
        """al Quest"""
        if quest_id in self._quests_cache:
            return self._quests_cache[quest_id]

        path = self._quest_file(quest_id)
        if not path.exists():
            return None

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            # dosyazararkotu, donus None
            return None

        try:
            quest = Quest(**data)
            self._quests_cache[quest_id] = quest
            return quest
        except Exception:
            return None

    def save(self, quest: Quest) -> None:
        """kaydet Quest"""
        quest.updated_at = datetime.now()
        self._save(quest)
        self._quests_cache[quest.id] = quest

    def delete(self, quest_id: str) -> bool:
        """sil Quest"""
        path = self._quest_file(quest_id)
        if path.exists():
            path.unlink()
        self._quests_cache.pop(quest_id, None)
        return True

    def list(self, status_filter: Optional[QuestStatus] = None) -> list[Quest]:
        """tumunu listelevar Quest"""
        self._ensure_dir()

        if not self.quests_dir.exists():
            return []

        quests = []
        for file in self.quests_dir.glob("*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                quest = Quest(**data)
                if status_filter is None or quest.status == status_filter:
                    quests.append(quest)
            except Exception:
                continue

        # goreolusturzamanarasindaters sira
        quests.sort(key=lambda q: q.created_at, reverse=True)
        return quests

    def get_active(self) -> builtins.list[Quest]:
        """alaktif Quest (henuztamamlavehenuziptal) """
        return self.list(status_filter=None)

    # ============================================================
    # kullanisliislem
    # ============================================================

    def update_status(self, quest_id: str, status: QuestStatus) -> Optional[Quest]:
        """guncelle Quest durum"""
        quest = self.get(quest_id)
        if quest is None:
            return None

        quest.status = status
        if status == QuestStatus.EXECUTING and quest.started_at is None:
            quest.started_at = datetime.now()
        if status in (QuestStatus.COMPLETED, QuestStatus.FAILED):
            quest.completed_at = datetime.now()

        self.save(quest)
        return quest

    def set_spec(self, quest_id: str, spec: QuestSpec) -> Optional[Quest]:
        """ayarlaayar SPEC"""
        quest = self.get(quest_id)
        if quest is None:
            return None

        quest.spec = spec
        # kaydetkadardosya
        spec_path = self.quests_dir / f"{quest_id}_SPEC.md"
        spec_path.write_text(spec.to_markdown(), encoding="utf-8")
        quest.spec_path = str(spec_path)
        self.save(quest)
        return quest

    def _save(self, quest: Quest) -> None:
        """icindekisimkaydetyontem"""
        self._ensure_dir()
        path = self._quest_file(quest.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                quest.model_dump(mode="json"),
                f,
                ensure_ascii=False,
                indent=2,
            )
