# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Code Research Agent - kod araştırma temsilcisi

Sorumluluklar:
1. Referans uygulamalarını elde etmek için genel kod kitaplıklarını arayın
2. Bulmak API Kullanım örnekleri ve en iyi uygulamalar
3. Keşfetmekİlgili açık kaynak projeler ve kütüphaneler
4. Kod yazımı için harici referans sağlayın

Modeli seviyesi:MEDIUM(Kalite ve maliyetin dengelenmesi)

İş akışı:
1. Araştırma hedeflerini analiz edin (işlevler, modeller, kütüphaneler)
2. kullanmak Sourcegraph Genel kodu arayın
3. İlgili dosya içeriğini al
4. Bulguları özetleyin ve önerilerde bulunun
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..integrations.sourcegraph import SourcegraphClient
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@dataclass
class ResearchTarget:
    """Araştırma hedefleri"""

    query: str  # Anahtar kelimeleri arayın
    language: Optional[str] = None  # hedef dil
    context: Optional[str] = None  # bağlam (belirli bir çerçeve gibi)
    max_results: int = 10


@dataclass
class CodeExample:
    """kod örneği"""

    repo: str
    file_path: str
    content: str
    language: str = ""
    source_url: str = ""
    relevance: float = 0.0  # Uygunluk puanı


@dataclass
class ResearchResult:
    """Araştırma sonuçları"""

    target: ResearchTarget
    examples: list[CodeExample] = field(default_factory=list)
    repos: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)


@register_agent
class CodeResearchAgent(BaseAgent):
    """
    kod araştırması Agent

    Özellikler:
    - kullanmak Sourcegraph Genel kod depolarında arama yapın
    - Gerek yok API Key, kamuya açık kullan streaming API
    - Geliştiricilere referans uygulamaları ve en iyi uygulamaları sağlayın
    """

    name = "code-research"
    description = "kod araştırma temsilcisi - Referans uygulamaları için genel kod tabanlarını arayın"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "🔎"
    tools = ["web_search", "web_fetch"]  # İsteğe bağlı ek arama

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sg_client: Optional[SourcegraphClient] = None

    @property
    def sg_client(self) -> SourcegraphClient:
        """Elde etmek Sourcegraph müşteri"""
        if self._sg_client is None:
            self._sg_client = SourcegraphClient()
        return self._sg_client

    @property
    def system_prompt(self) -> str:
        return """Profesyonel bir kod araştırma temsilcisisiniz.

## Rol
Sorumluluğunuz, geliştiricilere referans uygulamaları ve en iyi uygulamaları sağlamak için genel kod havuzlarını araştırmaktır.

## yetenek
1. **kod arama** - kullanmak Sourcegraph aramak GitHub/GitLab Genel kod bekleniyor
2. **Örnek keşif** - Fonksiyonu bulun,API, desen kullanım örnekleri
3. **Proje keşfi** - İlgili açık kaynak projelerini ve kitaplıklarını keşfedin
4. **İçerik çıkarma** - Analiz için ilgili dosya içeriklerini edinin

## Çalışma prensipleri
1. **Önce alaka düzeyi** - Yüksek kaliteli, alaka düzeyi yüksek sonuçları seçin
2. **Çeşitlilik** - Farklı stil ve senaryoların uygulamalarını sağlayın
3. **Çalıştırılabilirlik** - Doğrudan kullanılabilecek kod parçacıklarının çıktısını alır
4. **Kaynak açıklaması** - İzlenebilirliği kolaylaştırmak için kodun kaynağını işaretleyin

## Çıkış formatı
Çıktınız şunları içermelidir:
1. Arama sonucu özeti
2. Kod örnekleri (kaynak ek açıklamalarıyla birlikte)
3. Önerilen ilgili projeler
4. En iyi uygulama önerileri

## Dikkat edilmesi gerekenler
- Telif hakkıyla korunan kodu doğrudan kopyalamayın
- Tavsiye edilen MIT/Apache İzin verilen lisanslara sahip projeler
- Kod kaynağını ve lisans bilgilerini belirtin
"""

    def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        repo_filter: Optional[str] = None,
        limit: int = 10,
    ) -> list[CodeExample]:
        """
        Kodu arayın ve örnekler alın

        Args:
            query: Anahtar kelimeleri arayın
            language: Dil filtresi
            repo_filter: Depo filtreleme
            limit: sonuç sayısı

        Returns:
            CodeExample liste
        """
        result = self.sg_client.search(
            query=query,
            repo_filter=repo_filter,
            lang=language,
            limit=limit,
        )

        examples: list[CodeExample] = []

        for match in result.matches:
            # İçeriğin tamamını almaya çalışın
            content = match.line_content
            if match.repo and match.file_path and len(content) < 200:
                # Daha fazla bağlam elde edin
                file_content = self.sg_client.get_file(match.repo, match.file_path)
                if file_content:
                    content = file_content.content

            examples.append(
                CodeExample(
                    repo=match.repo,
                    file_path=match.file_path,
                    content=content,
                    language=match.language,
                    source_url=match.url,
                    relevance=1.0 if match.repository_stars > 1000 else 0.5,
                )
            )

        return examples

    def find_repos(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        İlgili depoları arayın

        Args:
            query: Anahtar kelimeleri arayın
            language: Dil filtresi
            limit: sonuç sayısı

        Returns:
            Depo bilgi listesi
        """
        search_query = query
        if language:
            search_query = f"{query} lang:{language}"

        repos = self.sg_client.list_repos(search_query, limit=limit)
        return [r.to_dict() for r in repos]

    def research(
        self,
        target: ResearchTarget,
    ) -> ResearchResult:
        """
        Kod araştırması yapın

        Args:
            target: Araştırma hedefleri

        Returns:
            ResearchResult
        """
        # Arama kodu örnekleri
        examples = self.search_code(
            query=target.query,
            language=target.language,
            limit=target.max_results,
        )

        # İlgili depoları arayın
        repos = self.find_repos(
            query=target.query,
            language=target.language,
            limit=5,
        )

        # Özet oluştur
        summary = self._generate_summary(target, examples, repos)

        # Öneriler oluştur
        recommendations = self._generate_recommendations(target, examples, repos)

        return ResearchResult(
            target=target,
            examples=examples,
            repos=repos,
            summary=summary,
            recommendations=recommendations,
        )

    def _generate_summary(
        self,
        target: ResearchTarget,
        examples: list[CodeExample],
        repos: list[dict[str, Any]],
    ) -> str:
        """Araştırma özetleri oluşturun"""
        lines = [f"## Araştırma sonuçları: {target.query}\n"]

        if examples:
            lines.append(f"açmak {len(examples)} kod örnekleri:")
            for i, ex in enumerate(examples[:5], 1):
                lines.append(f"  {i}. [{ex.repo}] {ex.file_path}")
        else:
            lines.append("Eşleşen kod örneği bulunamadı")

        if repos:
            lines.append(f"\nKeşfetmek {len(repos)} ilgili projeler:")
            for repo in repos[:3]:
                lines.append(f"  - {repo.get('name', '')} (⭐{repo.get('stars', 0)})")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        target: ResearchTarget,
        examples: list[CodeExample],
        repos: list[dict[str, Any]],
    ) -> list[str]:
        """Öneriler oluştur"""
        recs: list[str] = []

        if examples:
            # Alaka düzeyine göre sırala
            sorted_examples = sorted(examples, key=lambda x: x.relevance, reverse=True)
            top = sorted_examples[0]
            recs.append(f"Önerilen referans: {top.repo}/{top.file_path}")

        if repos:
            top_repo = max(repos, key=lambda x: x.get("stars", 0))
            recs.append(f"Önerilen öğeler: {top_repo.get('name', '')}")

        if target.language:
            recs.append(f"Kullanımı önerilir {target.language} Ana referans olarak resmi belgeler")

        return recs

    async def execute(self, context: AgentContext, **kwargs) -> AgentOutput:
        """
        Kod araştırma görevlerini gerçekleştirin

        itibaren context.task araştırma hedeflerini ayrıştırın veya kullanın kwargs parametreler.
        """
        # Araştırma hedeflerini analiz edin
        query = kwargs.get("query") or context.metadata.get("query", "")
        language = kwargs.get("language") or context.metadata.get("language")
        max_results = kwargs.get("max_results", 10)

        if not query:
            # baştan başlamayı dene task çıkarmak
            task = context.metadata.get("task", "")
            if task:
                # Anahtar kelimelerin basit çıkarılması
                query = task

        if not query:
            return AgentOutput(agent_name=self.name,
                status=AgentStatus.FAILED,
                summary="Arama anahtar kelimesi sağlanmadı",
                content="Lütfen context.metadata veya kwargs sağlanan query parametre",
            )

        # Araştırma hedeflerini oluşturun
        target = ResearchTarget(
            query=query,
            language=language,
            context=context.metadata.get("context"),
            max_results=max_results,
        )

        # Araştırma yürütün
        try:
            result = self.research(target)

            # Biçimlendirilmiş çıktı
            output_lines = [
                result.summary,
                "",
                "## kod örneği",
                "",
            ]

            for i, ex in enumerate(result.examples[:5], 1):
                output_lines.append(f"### Örnek {i}: {ex.repo}")
                output_lines.append(f"belge: {ex.file_path}")
                output_lines.append(f"kaynak: {ex.source_url}")
                output_lines.append("")
                output_lines.append(f"```{ex.language}")
                # Yalnızca öncekini göster 50 TAMAM
                content_lines = ex.content.splitlines()[:50]
                output_lines.extend(content_lines)
                if len(ex.content.splitlines()) > 50:
                    output_lines.append("... (Kesilmiş)")
                output_lines.append("```")
                output_lines.append("")

            if result.recommendations:
                output_lines.append("## telkin")
                output_lines.append("")
                for rec in result.recommendations:
                    output_lines.append(f"- {rec}")

            return AgentOutput(agent_name=self.name,
                status=AgentStatus.COMPLETED,
                summary=f"açmak {len(result.examples)} kod örnekleri, {len(result.repos)} ilgili projeler",
                content="\n".join(output_lines),
                artifacts={
                    "examples": [ex.to_dict() for ex in result.examples],
                    "repos": result.repos,
                    "recommendations": result.recommendations,
                },
            )

        except Exception as e:
            return AgentOutput(agent_name=self.name,
                status=AgentStatus.FAILED,
                summary="Araştırma başarısız oldu",
                content=f"hata: {e}",
            )

    def cleanup(self) -> None:
        """Kaynakları temizleme"""
        if self._sg_client:
            self._sg_client.close()
            self._sg_client = None


# Kolaylık fonksiyonu
def research_code(
    query: str,
    language: Optional[str] = None,
    limit: int = 10,
) -> ResearchResult:
    """
    Hızlı kod araştırma işlevi

    Örnek:
        result = research_code("http server", language="go")
        for ex in result.examples:
            print(f"{ex.repo}: {ex.file_path}")
    """
    agent = CodeResearchAgent()
    target = ResearchTarget(query=query, language=language, max_results=limit)
    try:
        return agent.research(target)
    finally:
        agent.cleanup()
