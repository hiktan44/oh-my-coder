"""
Test Engineer Agent - test mühendisi temsilcisi

Sorumluluklar:
1. Test stratejisi tasarımı
2. Test senaryosu yazımı
3. kapsam analizi
4. Flaky test Takviye

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
class TestEngineerAgent(BaseAgent):
    """test mühendisi Agent - Test stratejisi ve kullanım senaryosu yazımı"""

    name = "test-engineer"
    description = "test mühendisi temsilcisi - Test stratejisi tasarımı ve kullanım senaryosu yazımı"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🧪"
    tools = ["file_read", "file_write", "bash", "test"]

    @property
    def system_prompt(self) -> str:
        return """Siz profesyonel bir test mühendisisiniz.

## Rol
Sizin sorumluluğunuz test stratejileri tasarlamak, test senaryoları yazmak ve kod kalitesini sağlamaktır.

## yetenek
1. test stratejisi - Birim testi, entegrasyon testi,E2E test
2. test çerçevesi - pytest, unittest, jest, mocha
3. Mock Yetenek - Bağımlılıkları izole edin ve test hızını artırın
4. kapsam analizi - Testin yeterli olduğundan emin olun

## Test ilkeleri
1. **FAST** - Testin sık sık hızlı ve kolay çalıştırılması gerekir
2. **ISOLATED** - Testler birbirinden bağımsızdır ve herhangi bir sırayla çalıştırılabilir
3. **REPEATABLE** - Sonuçlar tekrarlanabilir ve çevresel etkilerden bağımsızdır
4. **SELF-VERIFYING** - Otomatik karar verildi/hata
5. **TIMELY** - Zamanında yazılmış,TDD öncelik

## Çıkış formatı

### 1. test stratejisi
- Test türü: Birim testi / Entegrasyon testi / E2E
- test çerçevesi: pytest / jest
- kapsama hedefleri: X%

### 2. test senaryosu
```python
# test_xxx.py

import pytest

class TestXXX:
    '''test XXX İşlev'''

    def test_case_1(self):
        '''normallik testi'''
        # Arrange
        ...
        # Act
        ...
        # Assert
        ...

    def test_case_2(self):
        '''Uç vakaları test edin'''
        ...

    def test_case_3(self):
        '''İstisnaları test edin'''
        ...
```

### 3. Mock veri
```python
# mock Veri örneği
```

### 4. kapsama raporu
- toplam kapsam: X%
- Açık şube: ...

### 5. telkin
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Test tasarımını yürütün"""
        # Ön sipariş çıktısı ekle
        if context.previous_outputs.get("executor"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Kodu uygulama\n{context.previous_outputs['executor'].result}",
                }
            )

        # Mevcut testleri kontrol edin
        test_dir = context.project_path / "tests"
        if test_dir.exists():
            test_files = list(test_dir.glob("test_*.py"))
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Mevcut testler\nyaygın {len(test_files)} test dosyaları",
                }
            )

        # Test İpuçları
        test_hint = """

Lütfen bir test tasarlayın:
1. Hangi test senaryolarına ihtiyaç var?
2. Nasıl Mock Dış bağımlılıklar mı?
3. Kapsama nasıl sağlanır?
4. Hangi uç durumların ele alınması gerekiyor?
"""
        prompt.append({"role": "user", "content": test_hint})

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
                "Doğrulamak için testleri çalıştırın",
                "Kapsam raporunu kontrol edin",
            ],
            next_agent="verifier",
        )
