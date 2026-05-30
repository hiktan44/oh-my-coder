"""
Architect Agent - Sistem mimarisi tasarım temsilcisi

Sorumluluklar:
1. Sistem mimarisi tasarımı
2. Teknoloji seçimi ve ödünleşim analizi
3. Arayüz tanımı
4. Mimari Karar Kaydı (ADR)

Modeli seviyesi:HIGH(Derin muhakeme, buna karşılık gelir opus)

İş akışı:
1. Gereksinimleri ve kısıtlamaları analiz edin
2. Genel mimariyi tasarlayın
3. Teknoloji seçimi
4. Arayüzleri ve veri akışlarını tanımlayın
5. Çıkış şeması belgesi
"""

from dataclasses import dataclass

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@dataclass
class ArchitectureDecision:
    """mimari kararlar"""

    title: str
    status: str  # proposed, accepted, deprecated
    context: str
    decision: str
    consequences: str


@register_agent
class ArchitectAgent(BaseAgent):
    """
    Mimar Agent

    Özellikler:
    - kullanmak HIGH tier Modeli
    - sistematik düşünme
    - Takas analizi
    - çıktı ADR
    """

    name = "architect"
    description = "mimar ajan - Sistem mimarisi tasarımı ve teknoloji seçimi"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "🏗️"
    tools = ["file_read", "file_write", "diagram", "web_fetch"]

    @property
    def system_prompt(self) -> str:
        return """Kıdemli bir yazılım mimarısınız.

## Rol
Sizin sorumluluğunuz sistem mimarisini tasarlamak, teknoloji seçimleri yapmak ve mimari kararları belgelemektir.

## yetenek
1. Mimari tasarım - Katmanlama, mikro hizmetler, olay odaklı vb.
2. Teknoloji seçimi - Dil, çerçeve, veritabanı, ara katman yazılımı
3. Takas analizi - CAP, tutarlılık, performans, maliyet
4. Arayüz tanımı - API Tasarım, veri modeli, sözleşme

## Çalışma prensipleri
1. **KISS** - Basit tutun ve aşırı tasarımdan kaçının
2. **YAGNI** - Gereksiz özellikleri önceden tasarlamayın
3. **Takaslarda şeffaflık** - Her seçimin artılarını ve eksilerini belirleyin
4. **Evrimleşebilir** - Mimari değişikliklere uyum sağlayabilmelidir

## Çıkış formatı

### 1. Mimariye genel bakış
- Genel mimari tarz (katmanlı/mikro hizmetler/monomer)
- çekirdek bileşenler
- Veri akış şeması (metin açıklaması)

### 2. teknoloji yığını
| Hiyerarşi | teknoloji | sebep |
|------|------|------|
| başlangıç ​​aşaması | ... | ... |
| arka uç | ... | ... |
| veritabanı | ... | ... |

### 3. çekirdek modül
```
project/
├── module1/     # betimlemek
├── module2/     # betimlemek
└── module3/     # betimlemek
```

### 4. Arayüz tasarımı
#### API uç nokta
- `GET /api/resource` - betimlemek
- `POST /api/resource` - betimlemek

#### veri modeli
```json
{
  "field": "type",
  "description": "göstermek"
}
```

### 5. Mimari Karar Kaydı (ADR)

#### ADR-001: [Karar başlığı]
- **durum**: proposed / accepted
- **arka plan**: ...
- **karar verme**: ...
- **Etkilemek**: ...

### 6. Riskler ve Azaltmalar
- ⚠️ risk1 → Azaltıcı önlemler
- ⚠️ risk2 → Azaltıcı önlemler

### 7. Sonraki adım
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """
        Mimari tasarımı yürütmek
        """
        # Ön sipariş çıktısı ekle
        context_parts = []

        if context.previous_outputs.get("explore"):
            context_parts.append(
                f"## Proje keşfi\n{context.previous_outputs['explore'].result}"
            )

        if context.previous_outputs.get("analyst"):
            context_parts.append(
                f"## ihtiyaç analizi\n{context.previous_outputs['analyst'].result}"
            )

        if context_parts:
            prompt.append({"role": "user", "content": "\n\n".join(context_parts)})

        # Mimari Tasarım İpuçları
        design_hint = """

Lütfen sistem mimarisini yukarıdaki bilgilere göre tasarlayın. Odaklan:
1. Mimari tarz projenin ölçeğine uygun mu?
2. Teknoloji seçimi makul mü?
3. Aşırı mühendislik mi yapıldı?
4. Ölçeklenebilirlik nasıl sağlanır?
"""
        prompt.append({"role": "user", "content": design_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.ARCHITECTURE,
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "kullanmak executor Agent farkına varmaya başla",
                "kullanmak critic Agent Mimari tasarımı inceleyin",
            ],
            next_agent="executor",
        )
