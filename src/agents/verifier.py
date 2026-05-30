"""
Verifier Agent - Temsilciyi doğrula

Sorumluluklar:
1. Kodun işlevsel doğruluğunu doğrulayın
2. Test kapsamını kontrol edin
3. Test paketini çalıştırın
4. Görevin tamamlandığını onayla

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
class VerifierAgent(BaseAgent):
    """doğrulamak Agent - Kod kalitesinin ve işlevselliğinin doğru olduğundan emin olun"""

    name = "verifier"
    description = "Temsilciyi doğrula - İşlevsel doğruluğu ve test kapsamını kontrol edin"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "✅"
    tools = ["bash", "file_read", "test"]

    @property
    def system_prompt(self) -> str:
        return """Siz ciddi bir kalite güvence mühendisisiniz.

## Rol
Sizin sorumluluğunuz, kodun gereksinimleri doğru bir şekilde uyguladığını doğrulamak ve kalitenin standartlara uygun olmasını sağlamaktır.

## yetenek
1. İşlevsel doğrulama - Testi çalıştırın ve sonuçları kontrol edin
2. kapsam kontrolü - Testin yeterli olduğundan emin olun
3. Entegrasyon testi - Uçtan uca doğrulama
4. regresyon kontrolü - Mevcut işlevselliği bozmadığınızdan emin olun

## Doğrulama standartları
- ✅ BUILD: Kod derlendi ve aktarıldı
- ✅ TEST: Tüm testler geçti
- ✅ LINT: hiçbiri lint hata
- ✅ FUNCTIONALITY: İşlev beklendiği gibi çalışıyor
- ✅ NO_TODO: Miras yok TODO
- ✅ ERROR_FREE: Çözülmemiş hata yok

## Çıkış formatı

### 1. Doğrulama sonuçları
| Öğeleri kontrol et | durum | göstermek |
|--------|------|------|
| BUILD | ✅/❌ | ... |
| TEST | ✅/❌ | ... |

### 2. test kapsamı
- Toplam test sayısı: X
- geçmek: X
- hata: X
- Kapsam: X%

### 3. Bulunan sorunlar
- soru1: ...
- soru2: ...

### 4. telkin
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Doğrulamayı gerçekleştir"""
        # Ön sipariş çıktısı ekle
        if context.previous_outputs.get("executor"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Kodu uygulama\n{context.previous_outputs['executor'].result}",
                }
            )

        # Test dosyasını oku
        test_dir = context.project_path / "tests"
        if test_dir.exists():
            test_files = list(test_dir.glob("test_*.py"))
            if test_files:
                tests_info = f"## Mevcut testler\nyaygın {len(test_files)} test dosyaları"
                prompt.append({"role": "user", "content": tests_info})

        # Doğrulama istemi
        verify_hint = """

Lütfen uygulamanın doğru olduğunu doğrulayın:
1. Kod derlenebilir mi?/koşmak?
2. Test geçti mi?
3. Fonksiyon ihtiyaçları karşılıyor mu?
4. Gözden kaçan uç durumlar var mı?
"""
        prompt.append({"role": "user", "content": verify_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.TESTING,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Doğrulama başarılı olursa kodu gönderebilirsiniz",
                "Doğrulama başarısız olursa geri dönün executor tamirat",
            ],
        )
