from __future__ import annotations

"""
kisadonemhafiza - mevcutyapacakkonusmabaglam

depolamamevcutyapacakkonusma: 
- icinkonusmagecmis (enyakin N ogre) 
- mevcutgorevdurum
- baglamdegismiktar

tasarim: 
- kaydetdeicindekaydet + geçicizamandosya (yapacakkonusmabitiryazgirisuzunlukdonem) 
- destekbaglamsikistir (ne zamanicinkonusmauzunlukzaman) 
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class Message:
    """tekilogremesaj"""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """yapacakkonusmabaglam"""

    session_id: str
    project_path: Optional[Path] = None
    task: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str, metadata: Optional[dict] = None):
        """eklemesaj"""
        self.messages.append(
            Message(role=role, content=content, metadata=metadata or {})
        )
        self.last_active = time.time()

    def get_recent_messages(self, limit: int = 20) -> list[Message]:
        """alenyakin N ogremesaj"""
        return self.messages[-limit:]

    def to_dict(self) -> dict[str, Any]:
        """sira"""
        return {
            "session_id": self.session_id,
            "project_path": str(self.project_path) if self.project_path else None,
            "task": self.task,
            "messages": [asdict(m) for m in self.messages],
            "variables": self.variables,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionContext:
        """terssira"""
        messages = [Message(**m) for m in data.get("messages", [])]
        return cls(
            session_id=data["session_id"],
            project_path=(
                Path(data["project_path"]) if data.get("project_path") else None
            ),
            task=data.get("task"),
            messages=messages,
            variables=data.get("variables", {}),
            created_at=data.get("created_at", time.time()),
            last_active=data.get("last_active", time.time()),
        )


class ShortTermMemory:
    """kisadonemhafizayonet"""

    def __init__(self, storage_dir: Path, max_messages: int = 100):
        """
        Args:
            storage_dir: depolamadizin
            max_messages: tekilyapacakkonusmaenbuyukmesajsayi (asirisonrasikistir) 
        """
        self.storage_dir = storage_dir / "short-term"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_messages = max_messages
        self._current_session: Optional[SessionContext] = None

    def create_session(
        self, project_path: Optional[Path] = None, task: Optional[str] = None
    ) -> SessionContext:
        """olusturyeniyapacakkonusma"""
        session = SessionContext(
            session_id=str(uuid.uuid4())[:8],
            project_path=project_path,
            task=task,
        )
        self._current_session = session
        return session

    def get_current_session(self) -> Optional[SessionContext]:
        """almevcutyapacakkonusma"""
        return self._current_session

    def set_current_session(self, session: SessionContext):
        """ayarlaayarmevcutyapacakkonusma"""
        self._current_session = session

    def load_session(self, session_id: str) -> Optional[SessionContext]:
        """yuklevaryapacakkonusma"""
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            data = json.loads(session_file.read_text())
            return SessionContext.from_dict(data)
        return None

    def save_session(self, session: SessionContext):
        """kaydetyapacakkonusmakadargeçicizamandosya"""
        session_file = self.storage_dir / f"{session.session_id}.json"
        session_file.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2)
        )

    def compress_if_needed(self, session: SessionContext) -> list[Message]:
        """ne zamanmesajcokzamansikistir, donuskorumesaj

        .. deprecated::
            buyontemisareticinkullanim disi, lutfenkullan `memory.auto_compact.check_and_compact()`
            yedekyerine. yeniuygulatemelde token kullanoranveolmayanmesajogresayi, dahaekleakilliedebilir. 
        """
        if len(session.messages) <= self.max_messages:
            return session.messages

        # sikistirstrateji: korusistemmesaj + enyakinbiryari + alintiister
        system_msgs = [m for m in session.messages if m.role == "system"]
        recent = session.messages[len(system_msgs) :]
        keep = recent[-self.max_messages // 2 :]

        # alintiisterkayipmesaj
        summary = Message(
            role="system",
            content=f"[hafizasikistir] atla {len(session.messages) - len(keep)} ogreerkendonemmesaj",
        )

        session.messages = [*system_msgs, summary, *keep]
        return session.messages

    def list_sessions(self) -> list[SessionContext]:
        """tumunu listelevaryapacakkonusma (goreensonraaktifzamanarasindaters sira) """
        sessions = []
        for f in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                sessions.append(SessionContext.from_dict(data))
            except Exception:
                pass
        sessions.sort(key=lambda s: s.last_active, reverse=True)
        return sessions

    def get_latest_session(self) -> Optional[SessionContext]:
        """alenyeniaktifyapacakkonusma"""
        sessions = self.list_sessions()
        return sessions[0] if sessions else None

    def clear_expired(self, max_age_hours: int = 24):
        """temizledonemyapacakkonusma (asiri max_age_hours) """
        now = time.time()
        max_age = max_age_hours * 3600

        for f in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                last_active = data.get("last_active", 0)
                if now - last_active > max_age:
                    f.unlink()
            except Exception:
                pass
