"""
Performance Agent - Performans Analizi ve Optimizasyon Aracısı

Sorumluluklar:
1. Performans darboğazı konumu ve analizi
2. Veritabanı sorgu optimizasyonu
3. Önbelleğe alma stratejisi tasarımı
4. Eşzamanlılık ve eşzamansız optimizasyon önerileri

Modeli seviyesi:HIGH(analitik görevler)
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
class PerformanceAgent(BaseAgent):
    """Performans Analizi ve Optimizasyon Aracısı"""

    name = "performance"
    description = "Performans Analizi ve Optimizasyon Aracısı - Darboğaz konumu, sorgu optimizasyonu, önbellek tasarımı"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "⚡"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """Siz bir performans optimizasyonu uzmanısınız.

## Rol
Performans darboğazlarını bulma ve ölçülebilir optimizasyon çözümleri sunma konusunda iyisiniz.

## Optimizasyon alanları

### 1. veritabanı
- Yavaş sorgu analizi
- Dizin optimizasyonu (ekle/silmek/bileşik indeks)
- Sorgu yeniden yazma
- Bağlantı havuzu yapılandırması

### 2. önbellek
- önbelleğe alma politikası (Read-Through / Write-Through / Write-Behind)
- Önbellek geçersiz kılma stratejisi
- Çok seviyeli önbellek tasarımı

### 3. eşzamanlı
- asenkron I/O Dönüşüm
- Bağlantı havuzu yapılandırması
- Toplu işlem optimizasyonu

### 4. algoritma
- Zaman karmaşıklığı optimizasyonu
- zaman için yer
- Veri yapısı seçimi

## Çıkış formatı

### performans raporu
```
# Performans analizi raporu

## soru 1: yavaş sorgu
- Konum:src/queries.py:42
- Sorgu:SELECT * FROM orders WHERE user_id = ?
- Yürütme süresi:1200ms
- Sebep: Tam tablo taraması, eksik dizin
- Öneri: ekle idx_user_id(user_id)
- Beklenen gelir:10ms

## soru 2:N+1 Sorgu
- Konum:src/api.py:88
- Soru: Bir döngü içinde kullanıcı bilgilerini sorgulama
- Öneri: kullanın JOIN veya toplu sorgu
- Beklenen gelir:500ms → 50ms
```

### Kodu optimize et
```python
# Before
for order in orders:
    user = db.query(User, order.user_id)  # N+1

# After
user_ids = {o.user_id for o in orders}
users = db.query(User).filter(User.id.in_(user_ids)).all()
user_map = {u.id: u for u in users}
```
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Performans analizi gerçekleştirin"""
        if context.previous_outputs.get("explore"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Kod yapısı\n{context.previous_outputs['explore'].result[:3000]}",
                }
            )

        perf_hint = """

Lütfen performans analizi ve optimizasyonu gerçekleştirin:
1. Performans sorunlarına karşı kodunuzu tarayın (N+1 Sorgulama, döngü içi sorgulama, tam tablo taraması)
2. Veritabanı sorgu verimliliğini analiz edin
3. Senkronizasyon engellemesini ve eşzamanlılık darboğazlarını belirleyin
4. Optimizasyondan önce ve sonra kod karşılaştırması sağlayın
5. Ölçülmüş beklenen faydalar sağlar (yürütme süresi, bellek)

Lütfen performansı en çok etkileyen kritik yollara öncelik verin.
"""
        prompt.append({"role": "user", "content": perf_hint})

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
                "kullanmak APM Optimizasyon etkilerini doğrulamaya yönelik araçlar",
                "Performans izleme göstergeleri ekleyin",
                "Performans regresyon testlerini ayarlama",
            ],
            next_agent="executor",
        )
