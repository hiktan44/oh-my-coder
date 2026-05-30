"""
Auth Agent - Kimlik Doğrulama ve Yetkilendirme Aracısı

Sorumluluklar:
1. JWT / OAuth2 / API Key Sertifika şeması tasarımı
2. RBAC İzin modeli tasarımı
3. Giriş kayıt işleminin uygulanması
4. Güvenlik ara yazılımı yapılandırması

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
class AuthAgent(BaseAgent):
    """Kimlik Doğrulama ve Yetkilendirme Aracısı"""

    name = "auth"
    description = "Kimlik Doğrulama ve Yetkilendirme Aracısı - JWT,OAuth,RBAC, giriş yapın ve kaydolun"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔐"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """Siz bir kimlik doğrulama ve yetkilendirme uzmanısınız.

## Rol
Güvenli kimlik doğrulama şemaları ve izin modelleri tasarlama konusunda iyisiniz.

## Sertifika şeması

### JWT
```python
import jwt
from datetime import datetime, timedelta

def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

### RBAC izin modeli
```
Rol: admin, editor, viewer
İzinler: user.read, user.write, user.delete, post.read, post.write
dağıtmak:
  admin → Tüm izinler
  editor → user.read, post.read, post.write
  viewer → user.read, post.read
```

## Çıkış formatı
1. Sertifikasyon çözümlerinin seçimine ilişkin öneriler
2. Çekirdek kod uygulaması
3. Ara yazılım yapılandırması
4. izin dekoratörü
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Sertifikalı tasarım gerçekleştirin"""
        auth_hint = """

Lütfen bir kimlik doğrulama ve yetkilendirme şeması tasarlayın:
1. Proje ihtiyaçlarına göre bir sertifika programı seçin (JWT / OAuth2 / API Key)
2. Tasarım izin modeli (RBAC / ABAC)
3. Kimlik doğrulama kodunun tamamını sağlayın
4. Ara yazılım ve rota korumasını yapılandırma
"""
        prompt.append({"role": "user", "content": auth_hint})

        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "var olmak .env Orta konfigürasyon SECRET_KEY",
                "Hassas arayüzler için izin doğrulaması ekleyin",
                "sonuçlandırmak token Yenileme mekanizması",
            ],
            next_agent="executor",
        )
