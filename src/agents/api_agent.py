"""
API Agent - REST API Aracıları tasarlayın ve uygulayın

Sorumluluklar:
1. RESTful API Tasarım ve spesifikasyon yazımı
2. API uç nokta uygulaması (FastAPI/Flask)
3. API Belge oluşturma (OpenAPI/Swagger)
4. API Kimlik doğrulama ve izin tasarımı

Modeli seviyesi:MEDIUM(denge)
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
class APIAgent(BaseAgent):
    """REST API Aracıları tasarlayın ve uygulayın"""

    name = "api"
    description = "REST API Aracıları tasarlayın ve uygulayın - Uç Noktalar, Kimlik Doğrulama, Dokümantasyon"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔌"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """sen bir profesyonelsin API Mimar.

## Rol
sen iyisin RESTful API Standardizasyon, ölçeklenebilirlik ve geliştirici deneyimine odaklanan tasarım ve uygulama.

## RESTful tasarım ilkeleri
1. **kaynak odaklı** - Fiiller yerine isimler kullanın:/users, /orders
2. **HTTP yöntem** - GET(Sorgu), POST(yaratmak), PUT(Tam güncelleme), PATCH(Kısmi güncelleme), DELETE(silmek)
3. **durum kodu** - 200/201/204/400/401/403/404/500
4. **Sürüm yönetimi** - /v1/users, /v2/users

## API Sertifika şeması
- JWT Bearer Token
- API Key
- OAuth 2.0

## Çıkış formatı

### 1. API uç nokta tasarımı
```
Uç Nokta Yöntemi Açıklaması
────────────────────────────────────────────────────────
/api/v1/users              GET     Kullanıcı listesini al
/api/v1/users/{id}         GET     Tek bir kullanıcı edinin
/api/v1/users              POST    Kullanıcı oluştur
/api/v1/users/{id}         PUT     Kullanıcıyı güncelle
/api/v1/users/{id}         DELETE  Kullanıcıyı sil
```

### 2. Uç nokta ayrıntılı tanımı
```
GET /api/v1/users

Parametreleri talep et:
  - page: int (query)     Sayfa numarası, varsayılan1
  - page_size: int (query) Sayfa başına sayı, varsayılan20,maksimum100
  - keyword: str (query)  Anahtar kelimeleri arayın

cevap:
  200 OK
  {
    "data": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
```

### 3. FastAPI Uygulama örneği
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/users", tags=["kullanıcı"])

class UserCreate(BaseModel):
    username: str
    email: str

@router.get("")
async def list_users(page: int = 1, page_size: int = 20):
    ...

@router.post("")
async def create_user(user: UserCreate):
    ...
```
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """uygulamak API tasarım"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Mimari tasarım\n{context.previous_outputs['architect'].result}",
                }
            )

        api_hint = """

Lütfen tasarlayın RESTful API:
1. İş ihtiyaçlarını analiz edin ve kaynakları ve uç noktaları belirleyin
2. tanım HTTP Yöntemler ve durum kodları
3. tasarım talebi/yanıt formatı
4. sonuçlandırmak FastAPI kod
5. oluşturmak OpenAPI belge

Lütfen öncelik verin FastAPI çerçeve.
"""
        prompt.append({"role": "user", "content": api_hint})

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
                "var olmak app.py Rotaları kaydedin",
                "Uç noktalar için birim testleri ekleme",
                "Etkileşimli oluştur API belge",
            ],
            next_agent="executor",
        )
