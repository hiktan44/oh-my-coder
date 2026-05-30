"""
Capsule - tamyetenekpaketyapi

tarafindan Gene (ogresayigore) + manifest (yapilandirma) + dependencies + checksum grupol. 
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .gene import Gene


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Capsule:
    """
    GEP Capsule - tamyetenekpaket

    Gene + manifest + dependencies + checksum. 
    """

    gene: Gene  # ogresayigore
    manifest: dict[str, Any] = field(default_factory=dict)  # tools/agents/prompts yapilandirma
    dependencies: list[str] = field(default_factory=list)  # bagimlilikonuno Capsule ID
    checksum: str = ""  # SHA256 kontroldogrula

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self.compute_checksum()

    # --- kontroldogrulave ---

    def compute_checksum(self) -> str:
        """temelde gene + manifest + dependencies hesapla SHA256"""
        payload = json.dumps(
            {
                "gene": self.gene.to_dict(),
                "manifest": self.manifest,
                "dependencies": sorted(self.dependencies),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return _sha256_hex(payload.encode("utf-8"))

    def verify_checksum(self) -> bool:
        return self.checksum == self.compute_checksum()

    # --- sira ---

    def to_dict(self) -> dict[str, Any]:
        return {
            "gene": self.gene.to_dict(),
            "manifest": self.manifest,
            "dependencies": self.dependencies,
            "checksum": self.checksum,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Capsule":
        gene = Gene.from_dict(data["gene"])
        return cls(
            gene=gene,
            manifest=data.get("manifest", {}),
            dependencies=data.get("dependencies", []),
            checksum=data.get("checksum", ""),
        )

    @classmethod
    def from_json(cls, text: str) -> "Capsule":
        return cls.from_dict(json.loads(text))

    # --- yonsonrauyumlu .omcp ---

    @classmethod
    def from_omcp(cls, data: dict[str, Any], file_name: str = "") -> "Capsule":
        """
        eski .omcp formatyukseltseviyeicin Capsule. 

        eskiformatustkisimolabiliredebiliryokvar gene alan, otomatikolustursanal Gene (temeldedosyaisimcikarim) . 
        """
        gene_data = data.get("gene")
        if gene_data:
            gene = Gene.from_dict(gene_data)
        else:
            # dosyaisimcikarimsanal Gene
            name = data.get("name", file_name.replace(".omcp", ""))
            category = _infer_category(data)
            tags = data.get("tags", [])
            gene = Gene(
                name=name,
                category=category,
                tags=tags,
                description=data.get("description", ""),
                version=data.get("version", "0.1.0"),
                author=data.get("author", "anonymous"),
            )

        # manifest koruhamolmayan gene alan
        manifest = {k: v for k, v in data.items() if k != "gene"}

        return cls(gene=gene, manifest=manifest)

    # --- kalici ---

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Capsule":
        return cls.from_json(path.read_text(encoding="utf-8"))


def _infer_category(data: dict[str, Any]) -> str:
    """ .omcp icerikcikarimyetenekpuansinif"""
    name = data.get("name", "").lower()
    desc = data.get("description", "").lower()
    tools = str(data.get("tools", [])).lower()
    combined = f"{name} {desc} {tools}"

    if "review" in combined:
        return "review"
    if "debug" in combined or "fix" in combined:
        return "debug"
    if "doc" in combined or "readme" in combined:
        return "docs"
    if "test" in combined:
        return "test"
    return "coding"
