# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

QA Tester Agent - QA test acentesi

Sorumluluklar:
1. etkileşimli CLI test
2. Hizmet çalışma zamanı doğrulaması
3. Uçtan uca test
4. Regresyon testi

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
class QATesterAgent(BaseAgent):
    """QA test Agent - Etkileşimli test ve uçtan uca doğrulama"""

    name = "qa-tester"
    description = "QA test acentesi - Etkileşimli test ve uçtan uca doğrulama"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🛠️"
    tools = ["bash", "file_read"]

    @property
    def system_prompt(self) -> str:
        return """sen bir QA Uçtan uca test etme ve etkileşimli doğrulama konusunda uzmanlaşmış test uzmanı.

## Rol
Sizin sorumluluğunuz, programı gerçekten çalıştırarak işlevselliğin beklendiği gibi olduğunu doğrulamaktır.

## yetenek
1. CLI test - Aslında komut satırı aracını çalıştırma
2. API test - test HTTP arayüz
3. Entegrasyon testi - Bileşenler arasındaki işbirliğini test etme
4. Regresyon testi - Değişikliklerin mevcut işlevselliği bozmadığından emin olun

## Test ilkeleri
1. **Gerçek operasyon** - Sadece koda bakmayın, onu gerçekten çalıştırın
2. **sınır testi** - Normal ve anormal koşulları test edin
3. **uçtan uca** - Tüm süreci test edin
4. **Tekrarlanabilir** - Test sonuçları tekrarlanabilir

## Çıkış formatı

### 1. test ortamı
- Python: 3.x
- sistem: macOS/Linux
- test komutu: ...

### 2. test senaryosu

#### TC-01: Temel işlevler
```
girmek: command --arg value
beklemek: Başarılı yürütme, çıktı...
gerçek: [PASS/FAIL]
```

#### TC-02: sınır durumu
```
girmek: command --edge-case
beklemek: İncelikle kullanın
gerçek: [PASS/FAIL]
```

### 3. Test sonuçları
| kullanım durumu | durum | göstermek |
|------|------|------|
| TC-01 | ✅ PASS | ... |
| TC-02 | ❌ FAIL | ... |

### 4. Bulunan sorunlar
- soru1: ...
- soru2: ...

### 5. dönüş riski
- ⚠️ yüksek risk: ...
- 🟡 orta risk: ...
- 🟢 düşük risk: ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """uygulamak QA test"""
        # Proje bilgilerini alın
        project_path = context.project_path

        # Yürütülebilir dosyayı kontrol edin
        executables = []
        for pattern in ["*.sh", "start*.sh", "run*.py"]:
            executables.extend(project_path.glob(pattern))

        # Giriş dosyasını kontrol edin
        main_files = []
        for name in ["main.py", "app.py", "cli.py", "__main__.py"]:
            main_files.extend(project_path.glob(f"**/{name}"))

        test_info = f"""## test ortamı

Proje yolu: {project_path}
yürütülebilir komut dosyası: {[e.name for e in executables]}
Giriş dosyası: {[m.name for m in main_files]}

Lütfen uçtan uca test senaryoları tasarlayın ve işlevi doğrulamak için programı gerçekten çalıştırın:
1. Temel işlevler normal şekilde çalışıyor mu?
2. Parametreler doğru şekilde ayrıştırıldı mı?
3. Hata işleme zarif mi?
4. Çıktı formatı beklendiği gibi mi?
"""
        prompt.append({"role": "user", "content": test_info})

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
                "Bulunan sorunları düzeltin",
                "Otomatik testler ekleyin",
            ],
        )
