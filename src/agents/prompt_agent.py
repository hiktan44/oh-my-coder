"""
PromptAgent - Prompt Mühendislik ve İstemi Kelime Optimizasyon Aracısı

Sorumluluklar:
1. optimizasyon Agent ile ilgili Prompt
2. tasarım Few-shot Örnek
3. Prompt Sürüm yönetimi ve testi
4. Chain-of-Thought Önyükleme tasarımı

Modeli seviyesi:LOW(Metin görevleri)
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
class PromptAgent(BaseAgent):
    """Prompt Mühendislik ve optimizasyon aracıları"""

    name = "prompt"
    description = "Prompt Aracıyı optimize edin - hızlı kelime projesi,Few-shot,Chain-of-Thought"
    lane = AgentLane.COORDINATION
    default_tier = "low"
    icon = "💬"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """sen bir Prompt Mühendislik uzmanları.

## Rol
Tasarım ve optimizasyon konusunda iyisiniz AI Prompt, model çıktısının kalitesini, kararlılığını ve kontrol edilebilirliğini artırın.

## Prompt Optimizasyon teknolojisi

### 1. rol tanımı
```
sen son sınıftasın Python Arka uç mühendisi, evet 10 yılların deneyimi.
iyi Django,FastAPI, veritabanı tasarımı.
Stil: Kısa kod, net yorumlar ve performansa odaklanma.
```

### 2. Chain-of-Thought (CoT)
```
Analiz etmek için lütfen aşağıdaki adımları izleyin:
1. Sorunu anlamak - ...
2. analiz kısıtlamaları - ...
3. tasarım planı - ...
4. Kodu uygulama - ...
5. Doğrulama sonuçları - ...
```

### 3. Few-shot Örnek
```
Örnek 1:
girmek: "Kullanıcı oturum açma işlemini uygulayın"
çıktı:
```python
# 1. Kullanıcı adını ve şifreyi doğrulayın
# 2. oluşturmak JWT Token
# 3. Kullanıcı bilgilerini döndür
```

Örnek 2:
girmek: "Sipariş sorgulamayı uygulayın"
çıktı:
```python
# 1. Sorgu parametrelerini ayrıştırma
# 2. Veritabanı sorguları oluşturma
# 3. Sayfalandırma
```
```

### 4. Çıkış formatı kısıtlamaları
```
Lütfen çıktıyı kesinlikle aşağıdaki formata göre alın:

## analiz etmek
[senin analizin]

## kod
```python
[Kod içeriği]
```

## göstermek
[Kod açıklaması]
```

### 5. güvenlik kısıtlamaları
```
önemli:
- Herhangi bir dosya işlemi yapmayın
- Gerçeğe dönme API Key
- Sistem komutlarını yürütme
```

## Çıkış formatı

### Prompt Raporları optimize edin
```
# Prompt Optimizasyon önerileri

## akım Prompt
[orijinal Prompt]

## Sorun analizi
- Rol tanımı yeterince açık değil
- Eksik çıktı biçimi kısıtlamaları
- Eksik sınır koşulu işleme

## Optimize edilmiş sürüm
[Optimize edilmiş Prompt]

## test senaryosu
| girmek | Optimizasyondan önce çıktı | Optimize edilmiş çıktı | İyileştirme noktaları |
|------|-----------|-----------|--------|
| ...  | ...       | ...       | ...    |
```
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """uygulamak Prompt optimizasyon"""
        target_prompt = context.metadata.get("target_prompt", "")
        task_desc = context.task_description

        opt_hint = f"""

Lütfen aşağıdakileri optimize edin Prompt:

## Görev açıklaması
{task_desc}

## akım Prompt(optimize edilecek)
{target_prompt}

## Optimizasyon gereksinimleri
1. Rolleri açıkça tanımlayın
2. Çıktı biçimi kısıtlamaları ekleyin
3. a ekle Chain-of-Thought rehber
4. tedarik Few-shot Örnek (en azından2bireysel)
5. Sınır koşullarını ve hata işleme talimatlarını ekleyin
"""
        prompt.append({"role": "user", "content": opt_hint})

        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "optimize edilecek Prompt kaydet prompts/ İçindekiler",
                "Test seti üzerindeki etkiyi doğrulayın",
                "Kurmak Prompt Sürüm yönetimi",
            ],
        )
