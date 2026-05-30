from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
anlamsalaramodul

Islev:
1. yonmiktarbenzerdereceara
2. karisikbirlestirara (anahtar kelime + anlamsal) 
3. baglamilgiliara
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SearchResult:
    """arasonuc"""

    element_id: str
    file_path: str
    name: str
    type: str
    relevance_score: float
    source_code: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    signature: Optional[str] = None
    highlights: list[str] = field(default_factory=list)
    context: str = ""


@dataclass
class SearchConfig:
    """arayapilandirma"""

    max_results: int = 10
    min_score: float = 0.3
    hybrid_alpha: float = 0.5  # anlamsalarayetkitekrar (0-1) , kalankalanicinanahtar kelimeyetkitekrar
    context_lines: int = 3  # baglamsatirsayi


class SemanticSearch:
    """
    anlamsalara

    destek: 
    1. safanlamsalara (yonmiktarbenzerderece) 
    2. safanahtar kelimeara (BM25) 
    3. karisikbirlestirara (anlamsal + anahtar kelime) 
    """

    def __init__(self, indexer, config: Optional[SearchConfig] = None):
        """
        Args:
            indexer: CodebaseIndexer ornek
            config: arayapilandirma
        """
        self.indexer = indexer
        self.config = config or SearchConfig()
        self.embedding_client = None

    def search(
        self,
        query: str,
        search_type: str = "hybrid",
        filters: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """
        yurutara

        Args:
            query: arasorgu
            search_type: aratip (semantic/keyword/hybrid) 
            filters: filtrelekosul

        Returns:
            arasonucliste
        """
        if search_type == "semantic":
            return self._semantic_search(query, filters)
        if search_type == "keyword":
            return self._keyword_search(query, filters)
        return self._hybrid_search(query, filters)

    def _semantic_search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """anlamsalara (yonmiktarbenzerderece) """
        results = []

        # alsorgugomu
        query_embedding = self._get_embedding(query)

        if not query_embedding:
            # yokvargomu, dusurseviyeicinanahtar kelimeara
            return self._keyword_search(query, filters)

        # hesaplailevarogreogrebenzerderece
        similarities = []
        for element in self.indexer.element_index.values():
            if not element.embedding:
                continue

            # uygulamafiltrele
            if filters and not self._match_filters(element, filters):
                continue

            similarity = self._cosine_similarity(query_embedding, element.embedding)
            similarities.append((element, similarity))

        # siralavedonus top-k
        similarities.sort(key=lambda x: x[1], reverse=True)

        for element, score in similarities[: self.config.max_results]:
            if score < self.config.min_score:
                continue

            results.append(self._element_to_result(element, score))

        return results

    def _keyword_search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """anahtar kelimeara (BM25 ruzgar) """
        results = []

        # puankelime
        query_terms = self._tokenize(query)

        # hesaplaherogreogre BM25 puansayi
        scores = []
        for element in self.indexer.element_index.values():
            if filters and not self._match_filters(element, filters):
                continue

            score = self._bm25_score(element, query_terms)
            if score > 0:
                scores.append((element, score))

        # siralavedonus top-k
        scores.sort(key=lambda x: x[1], reverse=True)

        for element, score in scores[: self.config.max_results]:
            results.append(self._element_to_result(element, score))

        return results

    def _hybrid_search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        """karisikbirlestirara (anlamsal + anahtar kelime) """
        semantic_results = self._semantic_search(query, filters)
        keyword_results = self._keyword_search(query, filters)

        # birlestirvesonuc
        combined = {}

        # anlamsalarasonuc
        for result in semantic_results:
            combined[result.element_id] = result
            result.relevance_score *= self.config.hybrid_alpha

        # anahtar kelimearasonuc
        for result in keyword_results:
            if result.element_id in combined:
                # birlestirvepuansayi
                combined[result.element_id].relevance_score += (
                    result.relevance_score * (1 - self.config.hybrid_alpha)
                )
            else:
                result.relevance_score *= 1 - self.config.hybrid_alpha
                combined[result.element_id] = result

        # sirala
        results = sorted(
            combined.values(),
            key=lambda x: x.relevance_score,
            reverse=True,
        )

        return results[: self.config.max_results]

    def search_context(
        self,
        query: str,
        context_elements: list[str],
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        baglamilgiliara

        goremevcutbaglam (orneginduzenleduzenlekod) arailgiliogreogre

        Args:
            query: arasorgu
            context_elements: baglamogreogre ID liste
            max_results: enbuyuksonucsayi

        Returns:
            ilebaglamilgiliarasonuc
        """
        # albaglamogreogregomu
        context_embeddings = []
        for eid in context_elements:
            element = self.indexer.element_index.get(eid)
            if element and element.embedding:
                context_embeddings.append(element.embedding)

        if not context_embeddings:
            return self.search(query)

        # hesaplabaglamduzortalamagomu
        avg_embedding = self._average_embeddings(context_embeddings)

        # alsorgugomu
        query_embedding = self._get_embedding(query)

        if not query_embedding:
            return self._keyword_search(query)

        # birlestirsorgugomuvebaglamgomu
        combined_embedding = [
            (q + c) / 2 for q, c in zip(query_embedding, avg_embedding)
        ]

        # ara
        results = []
        for element in self.indexer.element_index.values():
            if not element.embedding:
                continue

            if element.id in context_elements:
                continue  # harir tuticindebaglamicindeogreogre

            similarity = self._cosine_similarity(combined_embedding, element.embedding)

            if similarity >= self.config.min_score:
                results.append((element, similarity))

        # siralavedonus
        results.sort(key=lambda x: x[1], reverse=True)

        return [self._element_to_result(e, s) for e, s in results[:max_results]]

    def _get_embedding(self, text: str) -> Optional[list[float]]:
        """almetingomu. yok embedding_client zamandonus None, aradusurseviyeicinanahtar kelimeeslestir. """
        if self.embedding_client:
            # TODO: cagri embedding_client.embed(text) - baglanagizbekletanim
            pass
        return None

    def _cosine_similarity(
        self,
        vec1: list[float],
        vec2: list[float],
    ) -> float:
        """hesaplakalantelbenzerderece"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _average_embeddings(
        self,
        embeddings: list[list[float]],
    ) -> list[float]:
        """hesapladuzortalamagomu"""
        if not embeddings:
            return []

        n = len(embeddings)
        dim = len(embeddings[0])

        return [sum(e[i] for e in embeddings) / n for i in range(dim)]

    def _tokenize(self, text: str) -> list[str]:
        """puankelime"""
        # basittekilpuankelime: kucukyaz + goreolmayanharfanasayiharfpuanayir
        text = text.lower()
        return re.findall(r"[a-z0-9_]+", text)

    def _bm25_score(
        self,
        element,
        query_terms: list[str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> float:
        """hesapla BM25 puansayi"""
        # alogreogremetin
        text = f"{element.name} {element.signature or ''} {element.docstring or ''}"
        text = text.lower()

        # puankelime
        element_terms = self._tokenize(text)
        if not element_terms:
            return 0.0

        # hesaplakelimefrekans
        term_freq = {}
        for term in element_terms:
            term_freq[term] = term_freq.get(term, 0) + 1

        # hesapladokumantasyonuzunlukderece
        doc_length = len(element_terms)
        avg_doc_length = 50  # basitsahteayarla

        # hesaplapuansayi
        score = 0.0
        for term in query_terms:
            if term not in term_freq:
                continue

            tf = term_freq[term]
            idf = 1.0  # basit, yokvardokumantasyonfrekansoran

            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_length / avg_doc_length)

            score += idf * numerator / denominator

        return score

    def _match_filters(
        self,
        element,
        filters: dict[str, Any],
    ) -> bool:
        """kontrologreogreolup olmadigieslestirfiltrelekosul"""
        for key, value in filters.items():
            if key == "type":
                if element.type.value != value:
                    return False
            elif key == "file_pattern":
                if not Path(element.file_path).match(value):
                    return False
            elif key == "name_pattern":
                if not re.search(value, element.name):
                    return False

        return True

    def _element_to_result(
        self,
        element,
        score: float,
    ) -> SearchResult:
        """ogreogredonusturicinarasonuc"""
        # cikaryuksekparlak
        highlights = []
        if element.docstring:
            highlights.append(element.docstring[:100])

        return SearchResult(
            element_id=element.id,
            file_path=element.file_path,
            name=element.name,
            type=element.type.value,
            relevance_score=score,
            source_code=element.source_code,
            start_line=element.start_line,
            end_line=element.end_line,
            docstring=element.docstring,
            signature=element.signature,
            highlights=highlights,
        )


class ContextBuilder:
    """
    baglamolustur

    icin Agent olusturprojebaglam
    """

    def __init__(self, indexer, search: SemanticSearch):
        self.indexer = indexer
        self.search = search

    def build_context(
        self,
        task: str,
        relevant_files: Optional[list[str]] = None,
        max_tokens: int = 4000,
    ) -> str:
        """
        olusturprojebaglam

        Args:
            task: gorev aciklamasi
            relevant_files: ilgili dosyalarliste
            max_tokens: enbuyuk token sayi

        Returns:
            formatbaglamkarakter dizisi
        """
        parts = []

        # 1. projegenel bakis
        stats = self.indexer.get_stats()
        parts.append(
            f"""## projegenel bakis
- dosya sayisi: {stats["files_indexed"]}
- kodogreogre: {stats["elements_indexed"]}
- dilpuan: {stats["languages"]}
"""
        )

        # 2. ilgilikodara
        search_results = self.search.search(task, search_type="hybrid")

        if search_results:
            parts.append("## ilgilikod\n")
            for result in search_results[:5]:
                parts.append(
                    f"""### {result.name} ({result.type})
dosya: {result.file_path}:{result.start_line}-{result.end_line}
```python
{result.source_code[:500]}{"..." if len(result.source_code) > 500 else ""}
```
"""
                )

        # 3. ilgili dosyalaryapi
        if relevant_files:
            parts.append("## dosyayapi\n")
            for file_path in relevant_files[:10]:
                file_index = self.indexer.file_indices.get(file_path)
                if file_index:
                    elements_summary = self._summarize_elements(file_index.elements)
                    parts.append(f"- {file_path}\n  {elements_summary}\n")

        return "\n".join(parts)

    def _summarize_elements(self, elements) -> str:
        """toplamogreogre"""
        counts = {}
        for e in elements:
            type_name = e.type.value
            counts[type_name] = counts.get(type_name, 0) + 1

        return ", ".join(f"{count} {type_name}" for type_name, count in counts.items())
