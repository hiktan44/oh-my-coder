"""
Tracer Agent - Nedensel izleme ajanı

Sorumluluklar:
1. Kanıta dayalı nedensel izleme
2. Rekabetçi What-If Analizi
3. Sorunun temel nedeninin konumu
4. Çağrı zinciri analizi

Modeli seviyesi:MEDIUM(denge, yazışma sonnet)
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
class Hypothesis:
    """hipotez"""

    description: str
    evidence_for: list[str]
    evidence_against: list[str]
    confidence: float  # 0-1


@register_agent
class TracerAgent(BaseAgent):
    """izlemek Agent - Sebep-sonuç analizi ve kök neden tespiti"""

    name = "tracer"
    description = "takip temsilcisi - Kanıta dayalı nedensel analiz"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "🔍"
    tools = ["file_read", "search", "bash"]

    @property
    def system_prompt(self) -> str:
        return """Uzman bir sorun analizcisisiniz ve bir sorunun temel nedenini bulma konusunda iyisiniz.

## Rol
İşiniz kanıta dayalı analiz yoluyla sorunun gerçek nedenini bulmaktır.

## yetenek
1. Sebep ve sonuç takibi - Olay dizisini analiz edin
2. Hipotez doğrulama - Hipotezleri formüle edin ve test edin
3. kanıt toplama - Kod ve günlüklerden kanıt bulun
4. Kök neden konumu - Sorunun başlangıç ​​noktasını bulun

## Analitik yöntemler
1. **gözlemlemek** - Ne gördün?
2. **hipotez** - Olası nedenler nelerdir?
3. **doğrulamak** - Bu hipotez nasıl test edilir?
4. **Sonuç olarak** - Temel sebep nedir?

## Analiz ilkeleri
1. **kanıta dayalı** - Tahmin yok, gerçeklere dayanıyor
2. **rakip hipotezler** - Birden fazla olasılığı göz önünde bulundurun
3. **Occam'ın usturası** - En basit açıklama çoğu zaman doğru olanıdır
4. **tam bağlantı** - Olgudan temel nedene giden tam yol

## Çıkış formatı

### 1. Sorun olgusu
```
hata mesajı
yığın izleme
```

### 2. Rekabetçi What-If Analizi

| hipotez | destekleyici kanıtlar | Aleyhte kanıt | Kendinden emin |
|------|----------|----------|--------|
| H1: ... | ... | ... | 0.8 |
| H2: ... | ... | ... | 0.3 |

### 3. kanıt zinciri
```
fenomenA
  ↓ Çünkü
kodB
  ↓ Çünkü
YapılandırmaC
  ↓ Çünkü
ana nedenD
```

### 4. kök neden analizi
**ana neden**: ...

**doğrudan sebep**: ...

**Katkıda bulunan faktörler**: ...

### 5. Doğrulama adımları
```bash
# Doğrulama adımları1
# Doğrulama adımları2
```

### 6. Onarım önerileri
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Sebep ve sonuç takibi gerçekleştirin"""
        # Hata mesajı ekle
        error_info = context.metadata.get("error")
        if error_info:
            prompt.append(
                {"role": "user", "content": f"## Sorun olgusu\n```\n{error_info}\n```"}
            )

        # İlgili kodu ekleyin
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:5]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.name}\n```\n{content[:2000]}\n```"
                        )
                except Exception:
                    pass

            if code_parts:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## İlgili kod\n" + "\n\n".join(code_parts),
                    }
                )

        # Takip İpuçları
        trace_hint = """

Lütfen sorunun temel nedenini analiz edin:
1. Olası nedenler nelerdir? (Rakip hipotez)
2. Her hipotez için hangi destek var?/Kanıtlara karşı mı?
3. En olası temel neden nedir?
4. Sonucunuzu nasıl doğrulayabilirsiniz?
"""
        prompt.append({"role": "user", "content": trace_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.DEBUGGING,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Analiz sonuçlarına göre sorunları düzeltme",
                "Tekrarlamayı önlemek için test ekleyin",
            ],
            next_agent="debugger",
        )
