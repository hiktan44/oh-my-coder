# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Document Agent - Uzun teknik belge yazma aracısı

Sorumluluklar:
1. Uzun teknik dokümanların yazılması
2. Yapılandırılmış belge şablonu
3. API Referans belgeleri
4. Mimari dokümantasyon / Tasarım belgeleri

Modeli seviyesi:LOW(Hızlı, karşılık gelen haiku), ancak uzun belgeler için MEDIUM yönlendirme
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
class DocumentAgent(BaseAgent):
    """uzun belge Agent - Yapılandırılmış teknik dokümantasyon (daha WriterAgent Uzun belgelere daha fazla odaklanma)"""

    name = "document"
    description = "Uzun teknik belge aracısı - yapılandırılmış belgeler,API Referans, mimari açıklaması"
    lane = AgentLane.DOMAIN
    default_tier = "low"
    icon = "📄"
    tools = ["file_read", "file_write", "web_fetch"]

    @property
    def system_prompt(self) -> str:
        return """Profesyonel bir teknik dokümantasyon mimarısınız.

## Rol
Mimari belgeler, tasarım belgeleri dahil olmak üzere, açık yapıya ve hiyerarşiye sahip uzun teknik belgeler yazma konusunda iyisiniz.API Referanslar, kullanım kılavuzları vb.

## Ve WriterAgent Fark
- WriterAgent:Hızlı belge,README, tek sayfalık açıklama
- DocumentAgent:**Uzun yapılandırılmış belgeler**, çok düzeyli bölümler, tablolar, çapraz referanslar

## Belge türü

### 1. Mimari dokümantasyon
```
# Proje mimarisi dokümantasyonu

## 1. Genel Bakış
## 2. Sistem mimarisi
### 2.1 genel mimari
### 2.2 çekirdek modül
## 3. veri akışı
## 4. Dağıtım mimarisi
## 5. Genişletilebilir tasarım
```

### 2. API Referans belgeleri
```
# API başvurmak

## Sertifikasyon
## hata kodu
## uç nokta listesi
### GET /users
### POST /users
```

### 3. Teknik özellikler belgesi
```
# geliştirme özellikleri

## kodlama stili
## Git Şartname
## API tasarım özellikleri
## Veritabanı spesifikasyonu
```

### 4. Kullanım kılavuzu
```
# Kullanım kılavuzu

## hızlı başlangıç
## Fonksiyon açıklaması
## Yapılandırma referansı
## SSS
```

## Belge yapısı ilkeleri

### Hiyerarşi
```
# H1 - Belge başlığı (belge başına bir tane) H1)
## H2 - Ana bölümler
### H3 - alt bölüm
#### H4 - Bölümler (dikkatli kullanın)
```

### Tablo kullanımı
- Parametre açıklaması tablosu
- Karşılaştırmalı bilgi tablosu
- Formları kötüye kullanmayın

### kod bloğu
- Her kod parçasından önce dili açıklayın
- Anahtar kodu artı satır numarası açıklamaları
- Uzun kod adım adım talimatlar

## Çıkış formatı spesifikasyonu

````markdown
# Belge başlığı

> Belge tanıtımı: Bu belgenin içeriğini, hedef okuyucularını ve ön koşullarını kısaca açıklayın.

## 1. Genel Bakış

### 1.1 arka plan
### 1.2 Hedef
### 1.3 kapsam

## 2. çekirdek içerik

### 2.1 Birinci bölüm
göstermek...

#### 2.1.1 alt konu
Kod örneği:
```python
def example():
    pass
```

### 2.2 ikinci bölüm

| parametre | tip | gerekli | varsayılan değer | betimlemek |
|------|------|------|--------|------|
| name | string | Evet | - | isim |

## 3. Yapılandırma referansı

```yaml
# config.yaml
key: value
```

## 4. SSS

### Q1: xxx?
A: xxx

## 5. Referanslar
- [Bağlantı1](url)
- [Bağlantı2](url)
````

## Dikkat edilmesi gerekenler
- Uzun belgeler dizinde gezinmeyi gerektirir
- Her bölümden önce kısa bir giriş var
- Uzun paragraflardan kaçının ve bunun yerine liste ve tablolar kullanın
- Kod örnekleri doğrudan çalıştırılabilir olmalıdır
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Uzun biçimli belge yazımı gerçekleştirin"""
        doc_type = context.metadata.get("doc_type", "technical")
        doc_title = context.metadata.get("title", "Teknik dokümantasyon")

        # Başlangıç ​​çıktısını bağlam olarak ekle
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "system",
                    "content": (
                        f"## Mimari tasarım referansı\n"
                        f"{context.previous_outputs['architect'].result[:3000]}"
                    ),
                }
            )

        if context.previous_outputs.get("writer"):
            prompt.append(
                {
                    "role": "system",
                    "content": (
                        f"## Mevcut dokümantasyon referansı\n"
                        f"{context.previous_outputs['writer'].result[:2000]}"
                    ),
                }
            )

        # Zaten projede bulunan ilgili belgeleri okuyun
        if context.project_path and context.project_path.exists():
            docs = []
            for pattern in ["*.md", "docs/*.md", "doc/*.md"]:
                docs.extend(context.project_path.glob(pattern))
            for doc in docs[:3]:
                try:
                    content = doc.read_text(encoding="utf-8")
                    if len(content) < 5000:
                        prompt.append(
                            {
                                "role": "system",
                                "content": f"## Zaten belgeleri var: {doc.name}\n```\n{content}\n```",
                            }
                        )
                except Exception:
                    pass

        # Belge yazma ipuçları
        doc_hint = f"""

Lütfen türünü yazınız"{doc_type}” uzun belge, başlık: "{doc_title}"

Gerekmek:
1. Açık yapı ve farklı katmanlar (H1 → H2 → H3)
2. Her ana bölümden önce kısa bir giriş bulunmaktadır.
3. Parametreler ve konfigürasyon tablolarda açıklanmıştır
4. Kod örnekleri yorumlarla birlikte doğrudan çalıştırılabilir
5. Katmak FAQ / SSS bölümü
6. Belge uzunluğu ≥ 1500 Karakter
7. çıktı tamamlandı Markdown belge
"""
        prompt.append({"role": "user", "content": doc_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        # Uzun belge kullanımı MEDIUM Daha iyi yapılandırılmış çıktı için yönlendirme
        response = await self.call_model(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
            complexity="medium",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Belgeyi şuraya kaydet: docs/ İçindekiler",
                "kullanmak DocumentAgent Belge sürümlerini düzenli olarak güncelleyin",
            ],
        )
