from __future__ import annotations

"""
Checkpoint & Rollback sistem

saf Python uygula, hayirbagimlilik Git. 
Islev:
- olusturhizligore: kayitisbolgedegisiklikdosya (SHA256 farkfarklialgilama) 
- listelehizligore: destekgore task_id filtrele
- kurtarhizligore: uzerine yazisbolgedosya, kurtaronceonceyedekmevcutdurum
- icinkiyasfarkfarkli: goster snapshot ilemevcutisbolgefarkfarkli
- temizlemantik: her checkpoint en fazla 100 dosya, asiriotomatiktemizleenerken

dizinyapi: 
.omc/checkpoints/
├── index.json              # tummiktarindeks
└── <task-id>/
    ├── manifest.json        # dosyaliste + SHA256
    └── snapshot/            # degisiklikdosyaicerik
        ├── <file1>
        └── <file2>
"""


import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import builtins

# degisiklikdosyaustsinir (asirizamanotomatiktemizleenerken snapshot) 
MAX_SNAPSHOT_FILES = 100


@dataclass
class SnapshotEntry:
    """hizligoreicindetekildosyaogrehedef"""

    path: str  # icinyol
    sha256: str  # dosyaicerik SHA256
    size: int  # dosyabuyukkucuk (byte) 
    modified_at: str  # degistirzamanarasinda (ISO 8601) 


@dataclass
class Checkpoint:
    """hizligoreogresayigore"""

    id: str  # checkpoint ID (zamanarasindadamga + task_id) 
    task_id: str  # iliskiligorev ID
    description: str  # hizligoreaciklama
    created_at: str  # olusturzamanarasinda (ISO 8601) 
    file_count: int  # hizligoredosya sayisimiktar
    total_size: int  # hizligoretoplambuyukkucuk (byte) 
    working_dir: str  # isbolgekokdizin
    entries: list[SnapshotEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "description": self.description,
            "created_at": self.created_at,
            "file_count": self.file_count,
            "total_size": self.total_size,
            "working_dir": self.working_dir,
            "entries": [vars(e) for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        entries = [SnapshotEntry(**e) for e in data.get("entries", [])]
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            description=data["description"],
            created_at=data["created_at"],
            file_count=data["file_count"],
            total_size=data["total_size"],
            working_dir=data["working_dir"],
            entries=entries,
        )


class CheckpointManager:
    """
    Checkpoint yonet

    kullanyontem: 
        cm = CheckpointManager(project_path=Path("."))
        cp_id = cm.create(task_id="build-flask", description="baslatyeniden duzenleme")
        cm.restore(cp_id)
        cm.diff(cp_id)
    """

    # hayirkabulgirishizligoredizin/dosyamod
    IGNORE_PATTERNS: set[str] = {
        ".git",
        ".omc",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        ".DS_Store",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dylib",
        "*.egg-info",
        ".eggs",
        "dist",
        "build",
        ".coverage",
        "htmlcov",
        "*.whl",
    }

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.checkpoint_root = self.project_path / ".omc" / "checkpoints"
        self.index_file = self.checkpoint_root / "index.json"
        self.backup_root = Path.home() / ".omc" / "backup"
        self._index: dict[str, dict[str, Any]] = {}
        self._seq = 0  # tekilayariletartsirano, saglar cp_id tekbir
        self._init()
        self._load_index()

    # ------------------------------------------------------------------
    # baslat
    # ------------------------------------------------------------------

    def _init(self) -> None:
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        if self.index_file.exists():
            try:
                self._index = json.loads(self.index_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        self.index_file.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # cekirdekislem
    # ------------------------------------------------------------------

    def create(
        self,
        task_id: str,
        description: str = "",
        max_files: int = MAX_SNAPSHOT_FILES,
    ) -> str:
        """
        olustur checkpoint (hizligoremevcutisbolge) 

        sadecekaydetvardegisiklikdosya (SHA256 icinkiyas) . 

        Args:
            task_id: gorev ID
            description: hizligoreaciklama
            max_files: kezhizligoreen fazlakaydetdosya sayisi

        Returns:
            checkpoint ID
        """
        ts = time.strftime("%Y%m%d-%H%M%S")
        self._seq += 1
        cp_id = f"{ts}-{self._seq:04d}-{task_id}"
        cp_dir = self.checkpoint_root / task_id / cp_id
        snapshot_dir = cp_dir / "snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        entries: list[SnapshotEntry] = []
        total_size = 0

        # dolasisbolgedosya
        for file_path in self._iter_files():
            # atlayoksaymod
            if self._is_ignored(file_path):
                continue

            try:
                content = file_path.read_bytes()
            except OSError:
                continue

            # hesapla SHA256
            sha256 = hashlib.sha256(content).hexdigest()
            rel_path = str(file_path.relative_to(self.project_path))

            # kayitogrehedef
            entry = SnapshotEntry(
                path=rel_path,
                sha256=sha256,
                size=len(content),
                modified_at=time.strftime("%Y-%m-%dT%H:%M:%S") + f".{self._seq:04d}",
            )
            entries.append(entry)

            # yazgiris snapshot (sadecekaydeticerik, manifest tekiltekkaydet) 
            dest = snapshot_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            total_size += entry.size

        # sinirdosya sayisi (asirizamanalenyakin) 
        if len(entries) > max_files:
            entries.sort(key=lambda e: e.modified_at, reverse=True)
            entries = entries[:max_files]

        created_at = time.strftime("%Y-%m-%dT%H:%M:%S") + f".{self._seq:04d}"

        # yaz manifest
        manifest = {
            "id": cp_id,
            "task_id": task_id,
            "description": description,
            "created_at": created_at,
            "file_count": len(entries),
            "total_size": total_size,
            "working_dir": str(self.project_path.resolve()),
            "entries": [vars(e) for e in entries],
        }
        (cp_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # guncelleindeks
        self._index[cp_id] = {
            "id": cp_id,
            "task_id": task_id,
            "description": description,
            "created_at": created_at,
            "file_count": len(entries),
            "total_size": total_size,
            "working_dir": str(self.project_path.resolve()),
            "path": str(cp_dir),
        }
        self._save_index()

        return cp_id

    def restore(self, checkpoint_id: str) -> str:
        """
        kurtar checkpoint (uzerine yazisbolgedosya) 

        kurtaronceotomatikmevcutisbolgeyedekkadar ~/.omc/backup/<timestamp>/

        Args:
            checkpoint_id: checkpoint ID

        Returns:
            yedekyol
        """
        cp_dir = self._get_checkpoint_dir(checkpoint_id)
        manifest_file = cp_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Checkpoint '{checkpoint_id}' mevcut degil")

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        snapshot_dir = cp_dir / "snapshot"

        # yedekmevcutdurum
        backup_ts = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = self.backup_root / backup_ts
        backup_dir.mkdir(parents=True, exist_ok=True)

        restored_files = []
        for entry_data in manifest.get("entries", []):
            rel_path = entry_data["path"]
            current_file = self.project_path / rel_path

            # 1. onceyedekmevcutdosya (egerkaydeticinde) 
            if current_file.exists():
                dest = backup_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current_file, dest)

            # 2. tekrarkurtar snapshot dosya
            snap_file = snapshot_dir / rel_path
            if snap_file.exists():
                dest = self.project_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(snap_file.read_bytes())
                restored_files.append(rel_path)

        # yazyedekogresayigore
        (backup_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "restored_from": checkpoint_id,
                    "restored_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "files_restored": len(restored_files),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return str(backup_dir)

    def diff(self, checkpoint_id: str) -> dict[str, builtins.list[str]]:
        """
        icinkiyas checkpoint ilemevcutisbolgefarkfarkli

        Returns:
            {"added": [...], "removed": [...], "modified": [...], "unchanged": [...]}
        """
        cp_dir = self._get_checkpoint_dir(checkpoint_id)
        manifest_file = cp_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Checkpoint '{checkpoint_id}' mevcut degil")

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        cp_dir / "snapshot"

        result: dict[str, list[str]] = {
            "added": [],
            "removed": [],
            "modified": [],
            "unchanged": [],
        }

        #  manifest olustur path -> sha256 esle
        snapshot_map: dict[str, str] = {}
        for entry_data in manifest.get("entries", []):
            snapshot_map[entry_data["path"]] = entry_data["sha256"]

        # dolasmevcutisbolgedosya
        current_files: set[str] = set()
        for file_path in self._iter_files():
            if self._is_ignored(file_path):
                continue
            rel_path = str(file_path.relative_to(self.project_path))
            current_files.add(rel_path)

        # icinkiyas snapshot vs mevcut
        for rel_path, snapshot_sha in snapshot_map.items():
            current_file = self.project_path / rel_path
            if rel_path not in current_files:
                result["removed"].append(rel_path)
            else:
                current_sha = self._file_sha256(current_file)
                if current_sha == snapshot_sha:
                    result["unchanged"].append(rel_path)
                else:
                    result["modified"].append(rel_path)

        # mevcutvarancak snapshot yokvar → added
        for file_path in self._iter_files():
            if self._is_ignored(file_path):
                continue
            rel_path = str(file_path.relative_to(self.project_path))
            if rel_path not in snapshot_map:
                result["added"].append(rel_path)

        return result

    def delete(self, checkpoint_id: str) -> bool:
        """sil checkpoint"""
        if checkpoint_id not in self._index:
            return False
        cp_dir = Path(self._index[checkpoint_id]["path"])
        if cp_dir.exists():
            shutil.rmtree(cp_dir)
        del self._index[checkpoint_id]
        self._save_index()
        return True

    def list(
        self,
        task_id: Optional[str] = None,
        limit: int = 50,
    ) -> builtins.list[dict[str, Any]]:
        """
        listele checkpoint

        Args:
            task_id: goregorev ID filtrele
            limit: donusustsinir

        Returns:
            checkpoint bilgiliste
        """
        results = []
        for cp_id, info in self._index.items():
            if task_id and info.get("task_id") != task_id:
                continue
            results.append({**info, "id": cp_id})

        # gorezamanarasindaters sira
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """altekil checkpoint tambilgi"""
        if checkpoint_id not in self._index:
            return None
        cp_dir = Path(self._index[checkpoint_id]["path"])
        manifest_file = cp_dir / "manifest.json"
        if not manifest_file.exists():
            return None
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        return Checkpoint.from_dict(data)

    # ------------------------------------------------------------------
    # yardimciyontem
    # ------------------------------------------------------------------

    def _iter_files(self):
        """iterasyonisbolgeicindevardosya"""
        if not self.project_path.exists():
            return
        for item in self.project_path.rglob("*"):
            if item.is_file():
                yield item

    def _is_ignored(self, path: Path) -> bool:
        """karar verdosyaolup olmadigiolmalibuyoksay"""
        rel_str = str(path.relative_to(self.project_path))
        for part in rel_str.split("/"):
            if part in self.IGNORE_PATTERNS:
                return True
            for pattern in self.IGNORE_PATTERNS:
                if pattern.startswith("*") and part.endswith(pattern[1:]):
                    return True
        return False

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """hesapladosya SHA256"""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _get_checkpoint_dir(self, checkpoint_id: str) -> Path:
        """gore ID bulkadar checkpoint dizin"""
        if checkpoint_id in self._index:
            return Path(self._index[checkpoint_id]["path"])
        # dene task_id dizinara
        for cp_dir in self.checkpoint_root.rglob("*/manifest.json"):
            manifest = json.loads(cp_dir.read_text(encoding="utf-8"))
            if manifest.get("id") == checkpoint_id:
                return cp_dir.parent
        raise FileNotFoundError(f"Checkpoint '{checkpoint_id}' mevcut degil")

    # ------------------------------------------------------------------
    # istatistik
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """alhizligoreistatistik"""
        total = len(self._index)
        total_size = sum(c.get("total_size", 0) for c in self._index.values())
        total_files = sum(c.get("file_count", 0) for c in self._index.values())
        return {
            "total_checkpoints": total,
            "total_size_bytes": total_size,
            "total_files": total_files,
        }

    def format_diff(self, diff_result: dict[str, builtins.list[str]]) -> str:
        """format diff sonucicinolabilirokukarakter dizisi"""
        lines = []
        if diff_result["added"]:
            lines.append(f"🆕 yeniart ({len(diff_result['added'])}):")
            lines.extend([f"  + {f}" for f in diff_result["added"][:20]])
            if len(diff_result["added"]) > 20:
                lines.append(f"  ... halavar {len(diff_result['added']) - 20} ")

        if diff_result["removed"]:
            lines.append(f"❌ sil ({len(diff_result['removed'])}):")
            lines.extend([f"  - {f}" for f in diff_result["removed"][:20]])
            if len(diff_result["removed"]) > 20:
                lines.append(f"  ... halavar {len(diff_result['removed']) - 20} ")

        if diff_result["modified"]:
            lines.append(f"🔄 degistir ({len(diff_result['modified'])}):")
            lines.extend([f"  ~ {f}" for f in diff_result["modified"][:20]])
            if len(diff_result["modified"]) > 20:
                lines.append(f"  ... halavar {len(diff_result['modified']) - 20} ")

        if diff_result["unchanged"]:
            lines.append(f"✅ henuzdegis ({len(diff_result['unchanged'])})")

        if not lines:
            lines.append(" (yokfarkfarkli) ")

        return "\n".join(lines)
