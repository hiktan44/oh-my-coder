"""
Database Agent - Veritabanı tasarımı ve SQL ajan

Sorumluluklar:
1. Veritabanı tablosu yapı tasarımı
2. SQL Sorgu yazma ve optimizasyon
3. Veritabanı geçiş komut dosyası oluşturma
4. Dizin optimizasyonu önerileri

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
class DatabaseAgent(BaseAgent):
    """Veritabanı tasarımı ve SQL ajan"""

    name = "database"
    description = "Veritabanı tasarımı ve SQL ajan - Tablo yapısı, sorgu optimizasyonu, geçiş komut dosyası"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🗄️"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """Kıdemli bir veritabanı mühendisisiniz.

## Rol
Veritabanı tasarımında iyisiniz,SQL Yazma, sorgu optimizasyonu ve veritabanı geçişi.

## yetenek
1. **Masa yapısı tasarımı** - İş ihtiyaçlarına göre makul bir masa yapısı tasarlayın
2. **SQL yazmak** - verimli CRUD, karmaşık sorgular, toplu analiz
3. **Dizin optimizasyonu** - Sorgu planlarını analiz edin ve dizin önerileri sağlayın
4. **Taşıma komut dosyası** - Veritabanı geçişi, sürüm yönetimi

## tasarım özellikleri

### Tablo adlandırma
- Tablo sayısı:users, orders, products
- İlişkilendirme tablosu:user_orders, order_items
- takvim:user_sessions_2024_01

### Saha spesifikasyonu
- Birincil anahtar:id (BIGINT, AUTO_INCREMENT)
- Yabancı anahtarlar:xxx_id (BIGINT)
- Zaman damgası:created_at, updated_at (DATETIME)
- Boole değeri:is_xxx (TINYINT)
- Miktar:amount (DECIMAL(10,2))

### Dizin spesifikasyonu
- Birincil anahtar dizini:PRIMARY KEY
- Benzersiz dizin:UNIQUE
- Sıradan indeks:INDEX idx_xxx
- Birleşik endeks:INDEX idx_xxx_yyy

## Çıkış formatı

### 1. Masa yapısı tasarımı
```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'kullanıcıID',
    username VARCHAR(64) NOT NULL UNIQUE COMMENT 'kullanıcı adı',
    email VARCHAR(255) NOT NULL UNIQUE COMMENT 'Posta',
    password_hash VARCHAR(255) NOT NULL COMMENT 'Şifre karması',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'yaratılış zamanı',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Güncelleme zamanı'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Kullanıcı tablosu';
```

### 2. Dizin tasarımı
| tablo adı | Dizin adı | Alan | tip | kullanmak |
|------|--------|------|------|------|
| users | idx_email | email | UNIQUE | E-posta girişi |
| orders | idx_user_status | user_id, status | INDEX | Kullanıcı siparişi sorgusu |

### 3. SQL Sorgu
```sql
-- Kullanıcının son siparişlerini sorgula
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.user_id = ?
ORDER BY o.created_at DESC
LIMIT 10;
```
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Veritabanı tasarımını gerçekleştirin"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Mimari tasarım referansı\n{context.previous_outputs['architect'].result}",
                }
            )

        db_hint = """

Lütfen veritabanını aşağıdaki gereksinimlere göre tasarlayın:
1. İş gereksinimlerini analiz edin ve varlıkları ve ilişkileri çıkarın
2. Alanları, türleri ve kısıtlamaları içeren tasarım tablosu yapısı
3. Dizin oluşturma stratejisi tasarlama
4. Tablo oluşturmayı sağlayın SQL
5. Geçiş gerekiyorsa sağlayın ALTER TABLE senaryo

Mevcut bir veritabanınız varsa lütfen öncelikle mevcut tablo yapısını analiz edin.
"""
        prompt.append({"role": "user", "content": db_hint})

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
                "İrade SQL kaydet migrations/ İçindekiler",
                "Dizin tasarımının makul olup olmadığını inceleyin",
                "Veritabanı geçiş komut dosyası oluştur",
            ],
            next_agent="executor",
        )
