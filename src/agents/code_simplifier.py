"""
Code Simplifier Agent - Basitleştirilmiş kod aracısı

Sorumluluklar:
1. Kod netliği iyileştirmeleri
2. karmaşıklığın azaltılması
3. Geliştirilmiş bakım kolaylığı
4. Ölü kod temizleme

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
class CodeSimplifierAgent(BaseAgent):
    """kod basitleştirme Agent - Kod kalitesini ve okunabilirliğini iyileştirin"""

    name = "code-simplifier"
    description = "Basitleştirilmiş kod aracısı - Kodun netliğini ve sürdürülebilirliğini iyileştirin"
    lane = AgentLane.DOMAIN
    default_tier = "high"
    icon = "🧹"
    tools = ["file_read", "file_write", "bash"]

    @property
    def system_prompt(self) -> str:
        return """Kodu basitleştirmeye odaklanan bir kod yeniden düzenleme uzmanısınız.

## Rol
Göreviniz, davranışını değiştirmeden kodu daha anlaşılır ve bakımı daha kolay hale getirmektir.

## yetenek
1. karmaşıklığın azaltılması - Uzun işlevleri bölün ve iç içe geçmeyi azaltın
2. Adlandırma iyileştirmeleri - Daha anlamlı değişken ve fonksiyon adları
3. Tekrarlanan eleme - Ortak mantığı çıkarın
4. Ölü kod temizleme - Kullanılmayan kodu kaldır

## basitleştirme ilkesi
1. **tek sorumluluk** - Her işlev yalnızca tek bir şey yapar
2. **Yuvalamayı azaltın** - erken dön, azalt if-else
3. **Çıkarma işlevi** - Karmaşık mantığı küçük işlevlere ayırın
4. **anlamlı isimlendirme** - Belge olarak kod

## Kod kokusu algılama
- uzun fonksiyon (>50TAMAM)
- Derinden yuvalanmış (>3katman)
- Yinelenen kod
- sihirli sayı
- Parametre listesi çok uzun (>4bireysel)
- Çok fazla yorum

## Çıkış formatı

### 1. Kod kalitesi değerlendirmesi
| dizin | orijinal | Sadeleştirmeden sonra |
|------|------|--------|
| Satır sayısı | X | X |
| Siklomatik karmaşıklık | X | X |
| Fonksiyon sayısı | X | X |

### 2. Bulunan sorunlar
- 🔴 **uzun fonksiyon**: `process_data()` sahip olmak 120 TAMAM
- 🟡 **Derinden yuvalanmış**: HAYIR. 45-80 TAMAM 4 Katman yerleştirme
- 🟢 **Çıkarılabilir**: HAYIR. 50-60 Satırlar bağımsız işlevler olarak çıkarılabilir

### 3. Önerileri basitleştirin

**orijinal kod**:
```python
# sorun kodu
```

**Sadeleştirmeden sonra**:
```python
# Kodu iyileştirin
```

**İyileştirme talimatları**:
- ...

### 4. Daha fazla optimizasyon için öneriler
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Kod azaltma analizi gerçekleştirin"""
        # Analiz etmek için kodu okuyun
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:5]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        lines = len(content.split("\n"))
                        code_parts.append(
                            f"### {file_path.name} ({lines} TAMAM)\n```\n{content}\n```"
                        )
                except Exception:
                    pass

            if code_parts:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## Analiz edilecek kod\n" + "\n\n".join(code_parts),
                    }
                )

        # İpuçlarını basitleştirin
        simplify_hint = """

Lütfen kod kalitesini analiz edin ve basitleştirmeye yönelik önerilerde bulunun:
1. Nerede çok karmaşık?
2. Okunabilirlik nasıl geliştirilir?
3. Yinelenen kod var mı?
4. Ölü kod var mı?
"""
        prompt.append({"role": "user", "content": simplify_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.CODE_REVIEW,
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
                "Basitleştirme Önerilerini Uygulayın",
                "Doğrulamak için testleri çalıştırın",
            ],
        )
