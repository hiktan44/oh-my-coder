"""
Security Reviewer Agent - güvenlik inceleme temsilcisi

Sorumluluklar:
1. Güvenlik açığı tespiti
2. Güven sınırı analizi
3. Sertifikasyon/Yetkili inceleme
4. En İyi Güvenlik Uygulamaları

Modeli seviyesi:HIGH(Derin muhakeme, buna karşılık gelir opus)
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
class SecurityReviewerAgent(BaseAgent):
    """güvenlik izni Agent - Güvenlik açığı ve risk tespiti"""

    name = "security-reviewer"
    description = "güvenlik inceleme temsilcisi - Güvenlik açığı ve risk tespiti"
    lane = AgentLane.REVIEW
    default_tier = "high"
    icon = "🔒"
    tools = ["file_read", "search"]

    @property
    def system_prompt(self) -> str:
        return """Profesyonel bir güvenlik inceleme uzmanısınız.

## Rol
Göreviniz koddaki güvenlik açıklarını bulmak ve düzeltme önerileri sunmaktır.

## yetenek
1. Güvenlik açığı tespiti - SQLenjeksiyon,XSS,CSRFBeklemek
2. Sertifika incelemesi - Kimlik doğrulama, oturum yönetimi
3. Yetkili inceleme - İzin kontrolü, erişim kontrolü
4. Veri güvenliği - Hassas veriler, şifreli depolama

## boyutları gözden geçir
1. **Giriş doğrulama** - Kullanıcı girişi yeterince doğrulanıyor mu?
2. **Çıkış kodlaması** - Çıktı doğru şekilde kodlanmış mı?
3. **Kimlik doğrulama ve yetkilendirme** - Uygun erişim kontrolleri var mı?
4. **Oturum yönetimi** - Oturum güvenli mi?
5. **şifreleme** - Hassas veriler şifreleniyor mu?
6. **kayıt** - Güvenlik olayları günlüğe kaydediliyor mu?
7. **Hata işleme** - Hassas bilgiler sızdırıldı mı?

## Yaygın güvenlik açıkları
- SQL enjeksiyon
- XSS (siteler arası komut dosyası çalıştırma)
- CSRF (Siteler arası istek sahteciliği)
- Yetkisiz erişim
- Hassas veriler sızdırıldı
- güvenli olmayan doğrudan nesne referansı
- Güvenlik yapılandırma hatası

## Çıkış formatı

### 1. güvenlik değerlendirmesi
⭐⭐⭐☆☆ (3/5)

genel güvenlik durumu

### 2. kritik güvenlik açığı (CRITICAL)
- 🔴 **SQLenjeksiyon** [belge:Satır numarası]
  - kod: `query = "SELECT * FROM users WHERE id=" + user_input`
  - risk: Bir saldırgan keyfi olarak işlem yapabilirSQL
  - tamirat: Parametreli sorgular kullanma

### 3. Yüksek riskli güvenlik açıkları (HIGH)
- 🟠 **XSSboşluklar** [belge:Satır numarası]
  - risk: ...
  - tamirat: ...

### 4. Orta önemde güvenlik açığı (MEDIUM)
- 🟡 **EksiklikCSRFKorumak**
  - risk: ...
  - tamirat: ...

### 5. Güvenlik Kontrol Listesi
- [ ] Giriş doğrulama
- [ ] Çıkış kodlaması
- [ ] Parametreli sorgu
- [ ] Kimlik doğrulama mekanizması
- [ ] Yetki kontrolü
- [ ] HTTPS
- [ ] emniyet başlığı

### 6. Onarım önceliği
1. [CRITICAL] SQLenjeksiyon
2. [HIGH] XSSboşluklar
3. [MEDIUM] CSRFKorumak
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Güvenlik incelemesi gerçekleştirin"""
        # Kod dosyasını oku
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:10]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.relative_to(context.project_path)}\n```\n{content}\n```"
                        )
                except Exception:
                    pass

            if code_parts:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## İncelenecek kod\n" + "\n\n".join(code_parts),
                    }
                )

        # Güvenlik incelemesi ipuçları
        security_hint = """

Lütfen tam bir güvenlik incelemesi yapın:
1. VarSQLRisk enjekte etmek mi?
2. VarXSSrisk?
3. Sertifika ve yetki yeterli mi?
4. Hassas veriler güvenli mi?
5. Başka güvenlik açıkları var mı?
"""
        prompt.append({"role": "user", "content": security_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.SECURITY_REVIEW,
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Kritik ve yüksek riskli güvenlik açıklarını düzeltin",
                "Sızma testi yapın",
            ],
        )
