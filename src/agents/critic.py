"""
Critic Agent - eleştirmen ajanı

Sorumluluklar:
1. Planlama ve tasarım için boşluk analizi
2. çok açılı inceleme
3. Potansiyel sorunları keşfedin
4. İyileştirmeler için önerilerde bulunun

Modeli seviyesi:HIGH(Derin muhakeme, buna karşılık gelir opus)
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
class CriticAgent(BaseAgent):
    """eleştirmen Agent - Çok açılı inceleme ve boşluk analizi"""

    name = "critic"
    description = "eleştirmen ajanı - Program incelemesi ve boşluk analizi"
    lane = AgentLane.COORDINATION
    default_tier = "high"
    icon = "🎯"
    tools = ["file_read", "search"]

    @property
    def system_prompt(self) -> str:
        return """Keskin ama yapıcı bir eleştirmensiniz.

## Rol
Sizin sorumluluğunuz, boşlukları ve potansiyel sorunları belirlemek için planları ve tasarımları birden fazla perspektiften incelemek olacaktır.

## sansür açısı
1. **bütünlük** - Herhangi bir eksiklik var mı?
2. **fizibilite** - Bu başarılabilir mi?
3. **tutarlılık** - Herhangi bir çatışma var mı?
4. **sürdürülebilirlik** - Gelecekte bakımı kolay olacak mı?
5. **Ölçeklenebilirlik** - Genişletmek kolay mı?
6. **performans** - Herhangi bir performans sorunu var mı?
7. **Emniyet** - Herhangi bir güvenlik riski var mı?

## kritik prensip
1. **yapıcı** - Sadece sorunları belirtmekle kalmayıp öneriler de verin
2. **özel** - Belirli bir yeri ve nedenini belirtin
3. **öncelik** - Ciddi ve küçük sorunlar arasında ayrım yapın
4. **Çalıştırılabilir** - Öneriler spesifik ve uygulanabilir olmalıdır

## Çıkış formatı

### 1. Genel derecelendirme
⭐⭐⭐☆☆ (3/5)

Bir cümlelik özet

### 2. anahtar sorular (CRITICAL)
- 🔴 **[bütünlük]** Eksiklik XXX uğraşmak
  - Etkilemek: ...
  - telkin: ...

### 3. potansiyel sorunlar (WARNING)
- 🟡 **[performans]** XXX darboğaz haline gelebilir
  - sebep: ...
  - telkin: ...

### 4. İyileştirme önerileri (IMPROVEMENT)
- 🟢 **[sürdürülebilirlik]** Yeniden düzenlemeyi öner XXX
  - telkin: ...

### 5. boşluk analizi
| Boyutlar | durum | göstermek |
|------|------|------|
| bütünlük | ⚠️ | Eksik hata işleme |
| fizibilite | ✅ | Teknik çözüm mümkün |
| performans | ⚠️ | Optimizasyona ihtiyaç var |
| Emniyet | ✅ | Belirgin bir sorun yok |

### 6. Önerilen iyileştirme sırası
1. [CRITICAL] tamirat XXX
2. [WARNING] optimizasyon YYY
3. [IMPROVEMENT] Yeniden düzenleme ZZZ

### 7. Sonraki adımlar için öneriler
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Kritik inceleme gerçekleştirin"""
        # Ön sipariş çıktısını topla
        context_parts = []

        for agent_name in ["planner", "architect"]:
            if context.previous_outputs.get(agent_name):
                context_parts.append(
                    f"## {agent_name.title()}\n{context.previous_outputs[agent_name].result}"
                )

        if context_parts:
            prompt.append({"role": "user", "content": "\n\n".join(context_parts)})

        # Eleştiri ipuçları
        critic_hint = """

Lütfen birden çok açıdan inceleyin:
1. Gözden kaçan önemli noktalar var mı?
2. Herhangi bir çelişki veya tutarsızlık var mı?
3. Herhangi bir potansiyel risk var mı?
4. Bunu uygulamanın daha iyi bir yolu var mı?
"""
        prompt.append({"role": "user", "content": critic_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.ARCHITECTURE,
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Eleştirilere yanıt olarak planları ayarlayın",
                "Mimari tasarımı yeniden inceleyin",
            ],
        )
