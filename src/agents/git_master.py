"""
Git Master Agent - Git Temsilciyi çalıştır

Sorumluluklar:
1. Git İşlem yürütme
2. Yönetimi gönder
3. şube yönetimi
4. geçmiş yönetimi

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
class GitMasterAgent(BaseAgent):
    """Git işletmek Agent - Sürüm kontrol yönetimi"""

    name = "git-master"
    description = "Git Temsilciyi çalıştır - Sürüm kontrolü ve taahhüt yönetimi"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔀"
    tools = ["bash", "file_read"]

    @property
    def system_prompt(self) -> str:
        return """sen bir Git Sürüm kontrol uzmanı.

## Rol
senin işin yürütmek Git Operasyonlar, kod versiyonlarının yönetilmesi.

## yetenek
1. Yönetimi gönder - commit, amend, message
2. şube yönetimi - branch, merge, rebase
3. geçmiş yönetimi - log, diff, blame
4. uzaktan çalıştırma - push, pull, fetch

## Git en iyi uygulamalar
1. **Atomik taahhüt** - Her taahhüt yalnızca bir şey yapar
2. **anlamsal mesaj** - feat/fix/docs/refactor/test
3. **Sık sık gönder** - Hızlı koş
4. **iyi haberler yaz** - Başlığı kısa, metni ayrıntılı tutun

## Commit Mesaj formatı
```
<type>(<scope>): <subject>

<body>

<footer>
```

tip:
- feat: yeni özellikler
- fix: Bug tamirat
- docs: Dokümantasyon güncellemeleri
- refactor: kodu yeniden düzenleme
- test: Testle ilgili
- chore: inşa etmek/alet

## Çıkış formatı

### 1. Mevcut durum
```
On branch main
Changes to be committed:
  modified:   src/xxx.py

Changes not staged for commit:
  modified:   src/yyy.py

Untracked files:
  src/zzz.py
```

### 2. Önerilen eylem
```bash
# Değişiklik ekle
git add src/xxx.py

# göndermek
git commit -m "feat(core): Yeni özellikler ekleyin"

# İtmek
git push origin main
```

### 3. Kaydetme geçmişi
```
abc123 feat(core): Yeni özellikler ekleyin
def456 fix: tamirat Bug
...
```

### 4. Şube stratejisi önerileri
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """uygulamak Git işletmek"""
        import subprocess

        # elde etmek Git durum
        try:
            status_result = subprocess.run(
                ["git", "status", "--short"],
                cwd=context.project_path,
                capture_output=True,
                text=True,
            )
            status = status_result.stdout
        except Exception:
            status = "Alınamıyor Git durum"

        # En son taahhüdü alın
        try:
            log_result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                cwd=context.project_path,
                capture_output=True,
                text=True,
            )
            recent_commits = log_result.stdout
        except Exception:
            recent_commits = "Taahhüt geçmişi alınamıyor"

        prompt.append(
            {
                "role": "user",
                "content": f"""## akım Git durum
```
{status}
```

## Yakın zamanda gönderildi
```
{recent_commits}
```

Lütfen durumu analiz edin ve verin Git Operasyon önerileri:
1. Hangi belgeler sunulmalıdır?
2. Taahhüt mesajı nasıl yazılır?
3. Şube oluşturmam gerekiyor mu?
""",
            }
        )

        # çağrı modeli
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
                "önerilenleri uygula Git Emir",
                "Uzak depoya aktar",
            ],
        )
