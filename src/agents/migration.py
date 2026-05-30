"""
Migration Agent - Veri taşıma ve sürüm yönetimi aracısı

Sorumluluklar:
1. Veritabanı geçiş komut dosyası oluşturma
2. Veri taşıma planı tasarımı
3. Taşıma işlemini geri alma stratejisi
4. Taşıma doğrulama komut dosyası

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
class MigrationAgent(BaseAgent):
    """Veri taşıma ve sürüm yönetimi aracısı"""

    name = "migration"
    description = "veri taşıma aracısı - Geçiş komut dosyaları, geri alma stratejileri, veri doğrulama"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔄"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """Kıdemli bir veri taşıma mühendisisiniz.

## Rol
Geçiş komut dosyaları, geri alma stratejileri ve doğrulama mekanizmaları da dahil olmak üzere güvenli ve güvenilir veri taşıma çözümleri tasarlama konusunda iyisiniz.

## geçiş ilkesi
1. **Tersine çevrilebilirlik** - Tüm geçişlerin bir geri alma planı olmalıdır
2. **Doğrulanabilir** - Geçişten önce ve sonra veri tutarlılığı doğrulaması
3. **Kesintisiz** - Kesme noktası özgeçmiş indirmesini destekleyin
4. **izlenebilir** - Taşıma günlüğü kaydını tamamlayın

## Geçiş planı tasarımı

### 1. Taşıma komut dosyası yapısı
```sql
-- migrations/001_add_user_status.sql

-- geri alma
-- DROP TABLE IF EXISTS user_sessions;

-- göç etmek
ALTER TABLE users ADD COLUMN status TINYINT DEFAULT 1;
CREATE INDEX idx_status ON users(status);
```

### 2. Python Taşıma komut dosyası
```python
# migrations/001_add_user_status.py
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('status', sa.SmallInteger(), default=1))
    op.create_index('idx_status', 'users', ['status'])

def downgrade():
    op.drop_index('idx_status', 'users')
    op.drop_column('users', 'status')
```

### 3. Veri doğrulama
```sql
-- Geçişten önceki ve sonraki satır sayısı aynı
SELECT COUNT(*) FROM users;

-- veri bütünlüğü
SELECT COUNT(*) FROM users WHERE status IS NULL;

-- Örnekleme doğrulaması
SELECT * FROM users ORDER BY RAND() LIMIT 10;
```

## Çıkış formatı
1. Taşıma komut dosyası (geri alma dahil)
2. kontrol etmek SQL
3. Geçiş adımı talimatları
4. Önlemler ve risk noktaları
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Geçiş tasarımını gerçekleştirin"""
        if context.previous_outputs.get("database"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Veritabanı tasarımı\n{context.previous_outputs['database'].result}",
                }
            )

        mig_hint = """

Lütfen bir veri taşıma planı tasarlayın:
1. Taşınması gereken içeriği analiz edin (tablo yapısı/veri/dizin)
2. Geçiş komut dosyalarını tasarlayın (dahil UP/DOWN)
3. Veri doğrulamayı sağlayın SQL
4. Geçiş adımlarını ve önlemlerini açıklama
5. Geri alma seçenekleri sağlayın

Tavsiye edilen Alembic Veritabanı geçiş sürümlerini yönetin.
"""
        prompt.append({"role": "user", "content": mig_hint})

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
                "Geçiş komut dosyasını test ortamında doğrulayın",
                "Çalıştırmadan önce üretim verilerini yedekleyin",
                "Taşıma işlemini gerçekleştirdikten sonra doğrulamayı çalıştırın SQL",
            ],
            next_agent="executor",
        )
