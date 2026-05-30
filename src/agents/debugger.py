"""
Debugger Agent - Hata ayıklama aracıları

Sorumluluklar:
1. kök neden analizi
2. Hata çözümlemesi oluşturma
3. Çalışma zamanı hatası düzeltmeleri
4. Günlük analizi

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
class DebuggerAgent(BaseAgent):
    """hata ayıklama Agent - Bulun ve onarın Bug"""

    name = "debugger"
    description = "Hata ayıklama aracıları - Kök neden analizi ve hata düzeltme"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "🐛"
    tools = ["bash", "file_read", "search", "test"]

    @property
    def system_prompt(self) -> str:
        return """Deneyimli bir hata ayıklama uzmanısınız.

## Rol
Göreviniz sorunun temel nedenini hızlı bir şekilde belirlemek ve bir düzeltme sağlamaktır.

## Hata ayıklama yöntemi
1. **Üreme sorunu** - Hata belirtilerini tanımlayın
2. **Bilgi topla** - Hata günlükleri, yığın izleri
3. **Temel nedeni bulun** - Kod mantığını analiz edin
4. **Düzeltmeyi doğrula** - Sorunun çözüldüğünden emin olun

## Hata ayıklama ilkeleri
1. **kanıta dayalı** - Spekülasyon yerine gerçeklere dayalı
2. **Minimum değişiklik** - Yalnızca gerekli parçaları değiştirin
3. **Tamamen doğrulandı** - Düzeltmenin çalıştığından emin olun
4. **Tekrarı önleyin** - Test senaryosu ekle

## Çıkış formatı

### 1. Sorun analizi
**Hata fenomeni**:
```
hata mesajı
```

**kök neden analizi**:
1. ...
2. ...
3. ...

### 2. Konumlandırma sorunu
- belge: `path/to/file.py`
- işlev: `function_name`
- Satır numarası: XX

### 3. Düzeltmek
```python
# onarımdan önce
sorun kodu

# Onarımdan sonra
onarımdan sonra kod
```

### 4. Doğrulama adımları
1. Testleri çalıştır: `pytest tests/test_xxx.py`
2. Günlükleri kontrol edin: ...

### 5. Önlemler
- Birim testleri ekle
- Hata işleme ekle
- Günlüğe kaydetmeyi iyileştirin
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Hata ayıklamayı gerçekleştir"""
        # Hata mesajı ekle
        error_info = context.metadata.get("error")
        if error_info:
            prompt.append(
                {"role": "user", "content": f"## hata mesajı\n```\n{error_info}\n```"}
            )

        # İlgili kodu okuyun
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:5]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.name}\n```\n{content[:3000]}\n```"
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

        # Hata ayıklama ipuçları
        debug_hint = """

Lütfen sorunu analiz edin ve bir çözüm sağlayın:
1. Temel sebep nedir?
2. Nasıl düzeltilir?
3. Düzeltmenin çalıştığı nasıl doğrulanır?
4. Bunun tekrar yaşanması nasıl önlenir?
"""
        prompt.append({"role": "user", "content": debug_hint})

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
                "Düzeltmeyi uygula",
                "Doğrulamak için testleri çalıştırın",
            ],
            next_agent="verifier",
        )
