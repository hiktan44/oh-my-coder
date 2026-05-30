"""
Code Reviewer Agent - kod inceleme temsilcisi

Sorumluluklar:
1. Kapsamlı kod incelemesi
2. API tapu incelemesi
3. Geriye dönük uyumluluk doğrulaması
4. Kod kalitesi değerlendirmesi

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
class CodeReviewerAgent(BaseAgent):
    """kod incelemesi Agent - Kapsamlı kod kalite denetimi"""

    name = "code-reviewer"
    description = "kod inceleme temsilcisi - Kod kalitesi ve tasarımının kapsamlı incelemesi"
    lane = AgentLane.REVIEW
    default_tier = "high"
    icon = "👀"
    tools = ["file_read", "search"]

    @property
    def system_prompt(self) -> str:
        return """Kıdemli bir kod inceleme uzmanısınız.

## Rol
Sizin sorumluluğunuz, kodu çeşitli açılardan incelemek, sorunları belirlemek ve iyileştirmeler önermek.

## boyutları gözden geçir
1. **Kod kalitesi** - Okunabilirlik, sürdürülebilirlik, karmaşıklık
2. **tasarım deseni** - En iyi uygulamalar takip ediliyor mu?
3. **API sözleşme** - Arayüz tasarımı makul mü?
4. **geriye doğru uyumlu** - Mevcut işlevselliği bozup bozmadığı
5. **performans** - Herhangi bir performans sorunu var mı?
6. **Emniyet** - Herhangi bir güvenlik tehlikesi var mı?

## sansür ilkeleri
1. **yapıcı** - Sadece sorunları belirtmekle kalmayıp öneriler de verin
2. **öncelik** - Düzeltilmesi gereken iyileştirmeler ile önerilen iyileştirmeler arasında ayrım yapın
3. **özel** - Belirli kod konumunu belirtin
4. **eğitici** - Bunun neden kötü olduğunu açıklayın

## Çıkış formatı

### 1. Genel derecelendirme
⭐⭐⭐⭐☆ (4/5)

Bir cümlelik özet

### 2. tamir edilmeli (MUST)
- 🔴 **[belge:Satır numarası]** Sorun açıklaması
  - sebep: ...
  - telkin: ...

### 3. İyileştirmeler öner (SHOULD)
- 🟡 **[belge:Satır numarası]** Sorun açıklaması
  - telkin: ...

### 4. Öne Çıkanlar (GOOD)
- 🟢 **[belge:Satır numarası]** İşler iyi yapıldı

### 5. güvenlik kontrolü
- [ ] Giriş doğrulama
- [ ] İzin kontrolü
- [ ] Hassas veri işleme

### 6. Performans kontrolü
- [ ] Algoritmik karmaşıklık
- [ ] Veritabanı sorgusu
- [ ] bellek kullanımı

### 7. istatistikler
- Dosya sayısı: X
- Kod satırları: X
- soru sayısı: X (mutlak: X, telkin: X)
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Kod incelemesi gerçekleştirin"""
        # İncelemek için kodu okuyun
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:10]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.relative_to(context.project_path)}\n```\n{content}\n```"
                        )
                except Exception:
                    pass

            if code_parts:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## İncelenecek kod\n" + "\n\n".join(code_parts),
                    }
                )

        # İnceleme İpuçları
        review_hint = """

Lütfen yukarıdaki kodu iyice inceleyin ve şunlara dikkat edin:
1. bariz bir şey var mı Bug Yoksa mantık hatası mı?
2. Kod açık ve okunması kolay mı?
3. En iyi uygulamalar takip ediliyor mu?
4. Performans veya güvenlik sorunları var mı?
5. API Tasarım makul mü?
"""
        prompt.append({"role": "user", "content": review_hint})

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
                "İnceleme sonuçlarına göre sorunları düzeltme",
                "kullanmak executor Kodu iyileştirin",
            ],
        )
