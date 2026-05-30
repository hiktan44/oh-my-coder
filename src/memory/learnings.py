from __future__ import annotations

"""
ogrenogrenhafiza - tuzakkayit, en iyi uygulamalar

depolama: 
- hatamod (nedurumaltyapacakyanlis) 
- cozplan (orneginneduzeltme) 
- en iyi uygulamalar (oneryapyontem) 
- tekniktekniknot

tasarim: 
- Markdown format, kolaydeokuokuvesurumkontrol
- goresinifayrigrupduzen (errors, solutions, best-practices, notes) 
- destekara
"""

import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class LearningEntry:
    """ogrenogrenogrehedef"""

    id: str
    category: str  # "error", "solution", "best-practice", "note"
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    context: str = ""  # tetikgondersenaryo
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearningEntry:
        return cls(**data)


class LearningsMemory:
    """ogrenogrenhafizayonet"""

    CATEGORIES = ["error", "solution", "best-practice", "note"]

    def __init__(self, storage_dir: Path):
        """
        Args:
            storage_dir: depolamadizin
        """
        self.storage_dir = storage_dir / "learnings"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # goresinifayripuandizin
        for cat in self.CATEGORIES:
            (self.storage_dir / cat).mkdir(exist_ok=True)

        self.index_file = self.storage_dir / "index.json"
        self._index: dict[str, LearningEntry] = {}
        self._load_index()

    def _load_index(self):
        """yukleindeks"""
        if self.index_file.exists():
            data = self._parse_markdown_index()
            self._index = {k: LearningEntry.from_dict(v) for k, v in data.items()}

    def _parse_markdown_index(self) -> dict[str, dict]:
        """ Markdown dosyaayristirindeks"""
        index = {}
        for cat in self.CATEGORIES:
            cat_dir = self.storage_dir / cat
            if not cat_dir.exists():
                continue
            for md_file in cat_dir.glob("*.md"):
                entry = self._parse_learning_file(md_file)
                if entry:
                    index[entry.id] = entry.to_dict()
        return index

    def _parse_learning_file(self, path: Path) -> Optional[LearningEntry]:
        """ayristirtekil Markdown dosya"""
        try:
            content = path.read_text()
            # basittekilayristir: baslikcikar
            lines = content.split("\n")
            title = lines[0].lstrip("# ").strip() if lines else path.stem

            # cikar tags
            tags = []
            tag_match = re.search(r"\[tags?: ([^\]]+)\]", content)
            if tag_match:
                tags = [t.strip() for t in tag_match.group(1).split(",")]

            return LearningEntry(
                id=path.stem,
                category=path.parent.name,
                title=title,
                content=content,
                tags=tags,
            )
        except Exception:
            return None

    def _save_entry(self, entry: LearningEntry):
        """kaydetogrehedefkadar Markdown dosya"""
        cat_dir = self.storage_dir / entry.category
        cat_dir.mkdir(exist_ok=True)

        file_path = cat_dir / f"{entry.id}.md"
        content = f"# {entry.title}\n\n"
        if entry.tags:
            content += f"[tags: {', '.join(entry.tags)}]\n\n"
        if entry.context:
            content += f"**senaryo**: {entry.context}\n\n"
        content += entry.content

        file_path.write_text(content)

    def add(
        self,
        title: str,
        content: str,
        category: str = "note",
        tags: Optional[list[str]] = None,
        context: str = "",
    ) -> LearningEntry:
        """ekleogrenogrenogrehedef"""
        # olustur ID
        import uuid

        entry_id = f"{title.lower().replace(' ', '-')[:30]}-{uuid.uuid4().hex[:4]}"

        entry = LearningEntry(
            id=entry_id,
            category=category,
            title=title,
            content=content,
            tags=tags or [],
            context=context,
        )

        self._index[entry_id] = entry
        self._save_entry(entry)
        self._save_index()

        return entry

    def _save_index(self):
        """kaydetindeks"""
        data = {k: v.to_dict() for k, v in self._index.items()}
        import json

        self.index_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def search(self, query: str, category: Optional[str] = None) -> list[LearningEntry]:
        """araogrenogrenogrehedef"""
        results = []
        query_lower = query.lower()

        for entry in self._index.values():
            if category and entry.category != category:
                continue

            # arabaslik, icerik, tags
            if (
                query_lower in entry.title.lower()
                or query_lower in entry.content.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)

        return results

    def get_by_category(self, category: str) -> list[LearningEntry]:
        """goresinifayrial"""
        return [e for e in self._index.values() if e.category == category]

    def get_recent(self, limit: int = 10) -> list[LearningEntry]:
        """alenyakinekle"""
        sorted_entries = sorted(
            self._index.values(), key=lambda e: e.created_at, reverse=True
        )
        return sorted_entries[:limit]

    def delete(self, entry_id: str) -> bool:
        """silogrehedef"""
        if entry_id not in self._index:
            return False

        entry = self._index[entry_id]
        file_path = self.storage_dir / entry.category / f"{entry_id}.md"
        if file_path.exists():
            file_path.unlink()

        del self._index[entry_id]
        self._save_index()
        return True
