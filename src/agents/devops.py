"""
DevOps Agent - CI/CD ve işletme ve bakım otomasyon acenteleri

Sorumluluklar:
1. CI/CD Boru hattı yapılandırması (GitHub Actions / GitLab CI)
2. Dockerfile ve konteynerleştirme
3. Dağıtım komut dosyası oluşturma
4. İzleme ve alarm yapılandırması

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
class DevOpsAgent(BaseAgent):
    """DevOps Ve CI/CD Otomatik aracı"""

    name = "devops"
    description = "CI/CD Ve DevOps ajan - montaj hattıYapılandırma,Konteynerizasyon,dağıt"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🚀"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """sen son sınıftasın DevOps mühendis.

## Rol
sen iyisin CI/CD İşlem hattı tasarımı, kapsayıcıya alma, otomatik dağıtım ve işletme ve bakım komut dosyası oluşturma.

## yetenek
1. **CI/CD Yapılandırma** - GitHub Actions, GitLab CI, Jenkins
2. **Konteynerizasyon** - Dockerfile, docker-compose
3. **Dağıtım betiği** - Shell, Ansible, Terraform
4. **Alarmları izleyin** - Prometheus, Grafana, ELK

## CI/CD en iyi uygulamalar

### GitHub Actions montaj hattı
```yaml
name: CI Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --junitxml=report.xml
```

### Dockerfile en iyi uygulamalar
- Görüntü boyutunu küçültmek için çok aşamalı yapıları kullanın
- birleştirme RUN Katman sayısını azaltma talimatları
- kullanmak .dockerignore Gereksiz dosyaları hariç tutun
- olmayanlarla root Kullanıcı kapsayıcıyı çalıştırır

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "main.py"]
```

## Çıkış formatı

### 1. CI/CD montaj hattı
tamamlamak YAML Yapılandırma dosyası

### 2. Dockerfile
Optimize edilmiş çok aşamalı yapı

### 3. Dağıtım kontrol listesi
- Ortam değişkeni yapılandırması
- durum denetimi uç noktası
- Günlük koleksiyonu
- Uyarı kuralları
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """uygulamak DevOps Yapılandırma"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Mimari tasarım\n{context.previous_outputs['architect'].result}",
                }
            )

        devops_hint = """

Lütfen tasarlayın DevOps planı:
1. Proje diline ve çerçevesine göre seçim yapın CI/CD alet
2. tasarımmontaj hattısahne:lint → test → build → deploy
3. Eksiksiz sağlayın CI/CD Yapılandırma dosyası
4. Gerekirse sağlayın Dockerfile
5. Dağıtım komut dosyaları veya yapılandırmaları sağlayın

tavsiye etmek:Python Proje kullanımı GitHub Actions + Docker
"""
        prompt.append({"role": "user", "content": devops_hint})

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
                "İrade CI/CD Yapılandırmayı şuraya kaydet: .github/workflows/",
                "test Docker Görüntü oluşturma",
                "Yapılandırma Secrets ortam değişkenleri",
            ],
            next_agent="executor",
        )
