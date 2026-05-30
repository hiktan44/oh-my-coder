"""
Analyst Agent - Gereksinim Analizi Aracısı

Sorumluluklar:
1. Kullanıcı ihtiyaçlarının derinlemesine anlaşılması
2. Gizli kısıtlamaları ve uç durumları keşfedin
3. Belirsiz gereksinimleri netleştirin
4. Yapılandırılmış gereksinim belgeleri oluşturun

Modeli seviyesi:HIGH(Derin muhakeme, buna karşılık gelir opus)

İş akışı:
1. Kullanıcı girişini analiz edin
2. Temel ihtiyaç noktalarını belirleyin
3. Potansiyel sorunları keşfedin
4. Açıklayıcı sorular sorun
5. Gereksinimler belgesini oluştur
"""

from dataclasses import dataclass
from typing import Optional

from ..core.router import TaskType
from ..tools.sourcegraph import SearchResult, search
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@dataclass
class Requirement:
    """Gereksinimler"""

    id: str
    description: str
    priority: str  # high, medium, low
    category: str  # functional, non-functional, constraint
    dependencies: list[str]
    acceptance_criteria: list[str]


@dataclass
class AnalysisResult:
    """Sonuçları analiz edin"""

    summary: str
    requirements: list[Requirement]
    questions: list[str]  # Açıklığa kavuşturulması gereken sorular
    constraints: list[str]  # keşfedilen kısıtlamalar
    risks: list[str]  # Potansiyel riskler


@register_agent
class AnalystAgent(BaseAgent):
    """
    ihtiyaç analizi Agent

    Özellikler:
    - kullanmak HIGH tier Model (derin çıkarım)
    - İhtiyaçları açıklığa kavuşturmak için Sokratik sorular
    - Çıktı yapılandırılmış gereksinimler belgesi
    - İsteğe bağlı Sourcegraph Kod arama geliştirmeleri
    """

    name = "analyst"
    description = "Gereksinim Analizi Aracısı - Gereksinimleri derinlemesine anlayın ve gizli kısıtlamaları keşfedin"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "📊"
    tools = ["file_read", "search", "sourcegraph", "web_fetch"]

    # Sourcegraph Yapılandırma
    use_sourcegraph: bool = False
    sourcegraph_limit: int = 10

    def search_code(
        self,
        query: str,
        language: Optional[str] = None,  # noqa: UP045
        repo: Optional[str] = None,  # noqa: UP045
    ) -> SearchResult:
        """
        Genel kod depolarında arama yapın (üzerinden Sourcegraph)

        Args:
            query: Anahtar kelimeleri arayın veya Sourcegraph Sorgu sözdizimi
            language: Dil filtreleme (ör. rust/python/go)
            repo: Depo filtreleme (destekler) glob modeli)

        Returns:
            SearchResult: Arama sonuçları
        """
        return search(
            query=query,
            language=language,
            repo=repo,
            limit=self.sourcegraph_limit,
        )

    @property
    def system_prompt(self) -> str:
        return """Kıdemli bir gereksinim analistisiniz.

## Rol
İşiniz kullanıcı ihtiyaçlarını derinlemesine anlamak, gizli kısıtlamaları ve uç durumları ortaya çıkarmak ve geliştirme ekibinin net bir yöne sahip olmasını sağlamaktır.

## yetenek
1. Gereksinim çıkarma - Belirsiz açıklamalardan özel gereksinimleri çıkarın
2. kısıtlama keşfi - Teknik, zaman ve kaynak kısıtlamalarını belirleyin
3. Risk tanımlama - Potansiyel tuzakları ve risk noktalarını keşfedin
4. sokratik soru - Gereksinimleri netleştirmek için sorular sorun
5. kod arama - geçmek Sourcegraph Genel kod tabanında arama yapın ve mevcut uygulamalara bakın

## Çalışma prensipleri
1. **Tahmin etme** - Şüpheye düştüğünüzde sorun, varsaymayın
2. **Yapılandırılmış çıktı** - kullanmak Markdown ve bilgileri tablolar halinde organize edin
3. **Öncelikleri netleştirin** - Zorunlu, gerekir ve yapılabilir arasındaki farkı ayırt edin
4. **Doğrulanabilirlik** - Her gereksinimin kabul kriterleri vardır
5. **Referans uygulaması** - Sektördeki en iyi uygulamalar hakkında bilgi edinmek için genel kod havuzlarını arayın

## Çıkış formatı

### 1. Gereksinimlerin özeti
kullanmak 2-3 Temel ihtiyaçları tek cümleyle özetleyin

### 2. İşlevsel gereksinimler
| ID | betimlemek | öncelik | Kabul kriterleri |
|----|------|--------|----------|
| F1 | ... | high | ... |

### 3. işlevsel olmayan gereksinimler
| ID | betimlemek | tip | kısıtlama |
|----|------|------|------|
| NF1 | ... | performans | ... |

### 4. Kısıtlamalar
- Teknik kısıtlamalar:...
- Zaman kısıtlamaları:...
- Kaynak kısıtlamaları:...

### 5. Açıklığa kavuşturulması gereken sorular
1. ...
2. ...

### 6. Risk uyarısı
- ⚠️ ...
- ⚠️ ...

### 7. Sonraki adımlar için öneriler
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """
        İhtiyaç analizi yapın

        adım:
        1. Kullanıcı girişini analiz edin
        2. Proje bağlamı ile birleştirilmiş
        3. İsteğe bağlı: İlgili kodu arayın (Sourcegraph)
        4. Çağrı modelinin derinlemesine analizi
        """
        # Proje bağlamı ekle
        if context.previous_outputs.get("explore"):
            explore_result = context.previous_outputs["explore"].result
            prompt.append(
                {"role": "user", "content": f"## Proje keşif sonuçları\n\n{explore_result}"}
            )

        # Sourcegraph Kod arama geliştirmeleri (isteğe bağlı)
        if self.use_sourcegraph and kwargs.get("search_query"):
            search_query = kwargs["search_query"]
            search_lang = kwargs.get("search_language")
            search_repo = kwargs.get("search_repo")

            result = self.search_code(
                search_query, language=search_lang, repo=search_repo
            )

            if result.total_matches > 0:
                code_context = result.format_code(limit=5)
                prompt.append(
                    {
                        "role": "user",
                        "content": f"## İlgili kod referansı (Sourcegraph aramak)\n\n{code_context}",
                    }
                )
            elif result.warnings:
                # Uyarıları günlüğe kaydedin ancak sözünü kesmeyin
                context.metadata["sourcegraph_warnings"] = result.warnings

        # Analiz ipuçları ekleyin
        analysis_hint = """

Lütfen yukarıdaki bilgilere dayanarak bir ihtiyaç analizi yapın. Özel dikkat:
1. Belirsiz veya çelişkili gereksinimler var mı?
2. Herhangi bir gizli teknik kısıtlama var mı?
3. Herhangi bir potansiyel performans veya güvenlik sorunu var mı?
4. Hangi ek bilgilere ihtiyaç var?
"""
        prompt.append({"role": "user", "content": analysis_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.ARCHITECTURE,  # kullanmak HIGH tier
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """İşlem sonrası - Önemli bilgileri çıkarın"""
        # İşlem sonrası - Anahtar bilgileri çıkarın (şu anda kural eşleştirme kullanılıyor, henüz bağlanmadı LLM)
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "kullanmak planner Agent Bir yürütme planı geliştirin",
                "kullanmak architect Agent Tasarım sistemi mimarisi",
            ],
            next_agent="planner",
        )
