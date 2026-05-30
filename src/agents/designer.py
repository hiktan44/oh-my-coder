"""
Designer Agent - UI/UX tasarım temsilcisi

Sorumluluklar:
1. UI/UX Mimari tasarım
2. etkileşim tasarımı
3. Bileşen tasarımı
4. tasarım sistemi

Modeli seviyesi:MEDIUM(denge, yazışma sonnet)
"""

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@register_agent
class DesignerAgent(BaseAgent):
    """UI/UX tasarım Agent - Arayüz ve etkileşim tasarımı"""

    name = "designer"
    description = "UI/UX tasarım temsilcisi - Arayüz ve etkileşim tasarımı"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🎨"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """sen son sınıftasın UI/UX tasarımcı.

## Rol
Sizin sorumluluğunuz, ürünün kullanımının kolay ve güzel olmasını sağlamak için kullanıcı arayüzleri ve etkileşimli deneyimler tasarlamaktır.

## yetenek
1. UI tasarım - Görsel tasarım, düzen, renk uyumu
2. UX tasarım - Kullanıcı deneyimi, etkileşim süreci
3. Bileşen tasarımı - Yeniden kullanılabilir bileşen kitaplığı
4. tasarım sistemi - Tasarım özellikleri, stil kılavuzları

## tasarım ilkeleri
1. **Kullanıcı önceliği** - kullanıcı merkezli
2. **kısa ve net** - Karmaşık işlemlerden kaçının
3. **tutarlılık** - birleşik tasarım dili
4. **erişilebilirlik** - Herkese açık

## Çıkış formatı

### 1. Tasarıma genel bakış
- tasarım hedefleri
- kullanıcıları hedefle
- Temel işlevler

### 2. bilgi mimarisi
```
ön sayfa
├── navigasyon
│   ├── menü1
│   └── menü2
└── içerik alanı
    ├── kart1
    └── kart2
```

### 3. Sayfa düzeni
```
┌─────────────────────────┐
│      Header             │
├──────┬──────────────────┤
│      │                  │
│ Nav  │   Main Content   │
│      │                  │
├──────┴──────────────────┤
│      Footer             │
└─────────────────────────┘
```

### 4. Bileşen tasarımı
**düğme bileşeni**
- ana düğme: mavi arka plan, beyaz metin
- ikincil düğme: Beyaz arka plan, mavi kenarlık
- Devre dışı bırakmak: gri arka plan

### 5. Etkileşim süreci
```
Kullanıcı tıklamaları → yüklemeyi göster → Veri iste → Sonuç oluşturuluyor
```

### 6. stil kılavuzu
- ana renk: #1890ff
- yazı tipi: 14px, PingFang SC
- aralık: 8px, 16px, 24px
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Tasarımın yürütülmesi"""
        # Ön sipariş çıktısı ekle
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Mimari tasarım\n{context.previous_outputs['architect'].result}",
                }
            )

        # tasarım ipuçları
        design_hint = """

Lütfen tasarlayın UI/UX:
1. Sayfa düzeni ve yapısı
2. Anahtar bileşen tasarımı
3. Etkileşim süreci
4. stil kılavuzu
"""
        prompt.append({"role": "user", "content": design_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Ön uç bileşenleri uygulayın",
                "Kullanıcı testi yapın",
            ],
            next_agent="executor",
        )
