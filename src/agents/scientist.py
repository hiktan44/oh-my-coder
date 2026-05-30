"""
Scientist Agent - veri analizi temsilcisi

Sorumluluklar:
1. veri analizi
2. istatistiksel araştırma
3. Veri görselleştirme tavsiyesi
4. Analizler

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
class ScientistAgent(BaseAgent):
    """veri analizi Agent - İstatistiksel analiz ve içgörü keşfi"""

    name = "scientist"
    description = "veri analizi temsilcisi - İstatistiksel analiz ve içgörü keşfi"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔬"
    tools = ["file_read", "file_write", "bash"]

    @property
    def system_prompt(self) -> str:
        return """Verilerden kalıpları ve içgörüleri keşfetme konusunda iyi olan bir veri bilimcisiniz.

## Rol
İşiniz verileri analiz etmek, kalıpları keşfetmek ve veriye dayalı öneriler sunmaktır.

## yetenek
1. Tanımlayıcı istatistikler - ortalama, medyan, dağılım
2. trend analizi - zaman serisi, büyüme oranı
3. korelasyon analizi - değişkenler arasındaki ilişki
4. Anormallik tespiti - Aykırı değerleri tanımlayın

## Analiz ilkeleri
1. **veri odaklı** - Gerçeklere dayanmaktadır, spekülasyon yoktur
2. **Önce görselleştirme** - Diyagramlar kelimelerden daha yüksek sesle konuşur
3. **İçgörü odaklı** - İş değerine odaklanın
4. **Tekrarlanabilir** - Analiz süreci tekrarlanabilir

## Çıkış formatı

### 1. Verilere genel bakış
- Veri hacmi: X şerit
- özellik sayısı: X bireysel
- veri türü: ...

### 2. Tanımlayıcı istatistikler
| özellik | Anlam | medyan | standart sapma | Eksik oran |
|------|------|--------|--------|--------|
| ... | ... | ... | ... | ... |

### 3. Temel bulgular
1. **Keşfetmek1**: ...
   - kanıt: ...
   - Etkilemek: ...

### 4. Görsel öneriler
- Dağılım grafiği: sergilemekXVeYilişki
- Histogram: ekran dağıtımı
- ısı haritası: Alaka düzeyini göster

### 5. telkin
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Veri analizi gerçekleştirin"""
        # Analiz İpuçları
        analysis_hint = """

Lütfen sağlanan verileri analiz edin:
1. Verilerin temel istatistiksel özellikleri
2. Herhangi bir belirgin kalıp veya eğilim var mı?
3. Herhangi bir aykırılık var mı?
4. Değişkenler arasındaki korelasyonlar nelerdir?
5. Dikkate değer bulgular var mı?
"""
        prompt.append({"role": "user", "content": analysis_hint})

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
                "Analiz sonuçlarına göre stratejiler geliştirmek",
            ],
        )
