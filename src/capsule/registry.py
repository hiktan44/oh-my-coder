from __future__ import annotations

from typing import Optional

"""
GEPRegistry - yetenekkayittablo

register / discover / resolve / export_event
"""

from .capsule import Capsule
from .gene import Gene


class GEPRegistry:
    """
    GEP yetenekkayittablo

    yerelicindekaydetkayittablo, destekkayit, kesfet, ayristirveolaydisa aktar. 
    """

    def __init__(self) -> None:
        self._store: dict[str, Capsule] = {}  # gene_id -> Capsule

    # --- cekirdek API ---

    def register(self, capsule: Capsule) -> str:
        """
        kayitbir Capsule, donus Gene ID. 

        eger gene.id kaydeticindekuraluzerine yaz. 
        """
        gene_id = capsule.gene.id
        self._store[gene_id] = capsule
        return gene_id

    def discover(self, query: str) -> list[Gene]:
        """
        goreanahtar kelimekesfetyetenek. 

        araaralik: name / description / tags / capabilities. 
        eslestirkural: buyukkucukyazhayirhassas, destekbospuanayircokanahtar kelime (AND mantik) . 
        """
        keywords = [k.lower() for k in query.strip().split() if k]
        if not keywords:
            return []

        results: list[Gene] = []
        for capsule in self._store.values():
            gene = capsule.gene
            searchable = " ".join(
                [
                    gene.name,
                    gene.description,
                    gene.category,
                    " ".join(gene.tags),
                    " ".join(gene.capabilities),
                ]
            ).lower()

            if all(kw in searchable for kw in keywords):
                results.append(gene)

        return results

    def resolve(self, gene_id: str) -> Optional[Capsule]:
        """gore Gene ID al Capsule, mevcut degildonus None"""
        return self._store.get(gene_id)

    def export_event(self, gene_id: str) -> Optional[dict]:
        """
        disa aktar GEP Event format. 

        {
            "type": "GEP/Register",
            "version": "1.0",
            "payload": {"gene": {...}, "manifest": {...}, ...}
        }
        """
        capsule = self._store.get(gene_id)
        if capsule is None:
            return None

        return {
            "type": "GEP/Register",
            "version": "1.0",
            "payload": capsule.to_dict(),
        }

    # --- yardimci ---

    def list_all(self) -> list[Gene]:
        """tumunu listelevarkayit Gene"""
        return [c.gene for c in self._store.values()]

    def unregister(self, gene_id: str) -> bool:
        """kaldirkayit, donusbasarili mi"""
        if gene_id in self._store:
            del self._store[gene_id]
            return True
        return False

    def count(self) -> int:
        return len(self._store)
