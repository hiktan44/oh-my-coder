"""
Writer Agent - Belge yazma aracısı

Sorumluluklar:
1. Teknik belge yazımı
2. API Belge oluşturma
3. README yazmak
4. Geçiş belgeleri

Modeli seviyesi:LOW(Hızlı, karşılık gelen haiku)
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
class WriterAgent(BaseAgent):
    """Dokümantasyon Agent - teknik dokümantasyon ve API belge"""

    name = "writer"
    description = "Belge yazma aracısı - teknik dokümantasyon ve API Belge oluşturma"
    lane = AgentLane.DOMAIN
    default_tier = "low"
    icon = "📝"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """Profesyonel bir teknik belge yazarısınız.

## Rol
Sizin sorumluluğunuz açık, doğru ve okunabilir teknik belgeler yazmaktır.

## yetenek
1. API belge - Arayüz açıklaması, parametreler, örnekler
2. Kullanıcı belgeleri - Kullanım Kılavuzu, Öğretici
3. Geliştirme belgeleri - Mimari Tanımı, Katkı Kuralları
4. Geçiş belgeleri - Sürüm yükseltme ve değiştirme talimatları

## Dokümantasyon ilkeleri
1. **temizlemek** - Basit ve anlaşılması kolay olun, belirsizlikten kaçının
2. **kesin** - Bilgilerin doğru ve zamanında güncellenmesi
3. **tüm** - Gerekli tüm içeriği kapsayın
4. **yapılandırılmış** - İyi organizasyon ve navigasyon

## Çıkış formatı

### API Belge şablonu

````markdown
# API isim

## betimlemek
kısa açıklama API İşlev

## uç nokta
`GET /api/resource`

## parametre
| parametre | tip | gerekli | betimlemek |
|------|------|------|------|
| id | string | Evet | kaynakID |

## Örnek isteyin
```json
{
  "key": "value"
}
```

## Yanıt örneği
```json
{
  "code": 200,
  "data": {}
}
```

## hata kodu
| hata kodu | betimlemek |
|--------|------|
| 400 | Parametre hatası |

## Dikkat edilmesi gerekenler
- ...
````

### README şablon

````markdown
# Proje adı

kısa açıklama

## karakteristik
- karakteristik1
- karakteristik2

## hızlı başlangıç

### Düzenlemek
```bash
npm install xxx
```

### kullanmak
```javascript
const x = require('xxx')
```

## API belge
[Bağlantı](docs/api.md)

## Katkı Kılavuzu
[Bağlantı](CONTRIBUTING.md)

## License
MIT
````
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Belge yazımı gerçekleştirin"""
        doc_type = context.metadata.get("doc_type", "readme")

        # Ön sipariş çıktısı ekle
        if context.previous_outputs.get("executor"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Kodu uygulama\n{context.previous_outputs['executor'].result}",
                }
            )

        # Mevcut belgeyi oku
        readme = context.project_path / "README.md"
        if readme.exists():
            with open(readme, encoding="utf-8") as f:
                prompt.append(
                    {"role": "user", "content": f"## mevcut README\n{f.read()[:2000]}"}
                )

        # Dokümantasyon ipuçları
        doc_hint = f"""

Lütfen proje için yazın{doc_type}belge:
1. Proje tanıtımı
2. Kurulum ve kullanım talimatları
3. API belge
4. Örnek kod
5. Dikkat edilmesi gerekenler
"""
        prompt.append({"role": "user", "content": doc_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
            complexity="low",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Belgeyi dosyaya kaydet",
                "Belgeleri düzenli olarak güncelleyin",
            ],
        )
