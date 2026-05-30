from __future__ import annotations

"""
Gene - yetenekogresayigoreyapi

GEP protokolicindetemeltekilogre, aciklamabiryetenekkimlikveozellik. 
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from uuid import uuid4


@dataclass
class Gene:
    """
    yetenekogresayigore (GEP Gene) 

    karsilik gelen GEP protokolicindeyetenektemelneden, tasikemerkimlik, puansinifveaciklamabilgi. 
    """

    name: str  # yetenekad
    category: str  # coding / review / debug / docs / test
    tags: list[str] = field(default_factory=list)  # [python, pytest, bug-fix]
    description: str = ""  # bircumlekonusmaaciklama
    capabilities: list[str] = field(default_factory=list)  # araçyetenekliste
    version: str = "0.2.0"  # surumno
    author: str = "anonymous"  # yazar
    created_at: str = ""  # ISO formatzamanarasinda
    signature: Optional[str] = None  # henuzgelicinbaglan zCloak
    id: str = ""  # UUID

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            from datetime import datetime

            self.created_at = datetime.now().isoformat()

    # --- sira ---

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Gene:
        # sadeceal Gene kendikendialan, yoksaycokkalan key
        valid = {
            k: v
            for k, v in data.items()
            if k in cls.__dataclass_fields__  # type: ignore[attr-defined]
        }
        return cls(**valid)

    # --- kontroldogrula ---

    def validate(self) -> list[str]:
        errors: list[str] = []
        valid_categories = {"coding", "review", "debug", "docs", "test"}
        if self.category and self.category not in valid_categories:
            errors.append(
                f"yoketki category '{self.category}', olmaliicin {sorted(valid_categories)}"
            )
        if not self.name:
            errors.append("name hayiredebiliricinbos")
        return errors
