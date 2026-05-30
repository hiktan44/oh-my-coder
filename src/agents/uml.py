"""
UML Agent - Mimari diyagram ve görsel ajan

Sorumluluklar:
1. Mimari diyagram oluşturma (Mermaid / PlantUML)
2. Sınıf diyagramı, sıra diyagramı, kullanım senaryosu diyagramı
3. Akış şemaları ve veri akış diyagramları
4. Mimari Karar Kaydı (ADR)

Modeli seviyesi:LOW(hızlı)
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
class UMLAgent(BaseAgent):
    """Mimari diyagram ve görsel ajan"""

    name = "uml"
    description = "Mimari diyagramı ve UML Görsel ajan - Sınıf diyagramı, sıra diyagramı, akış şeması"
    lane = AgentLane.DOMAIN
    default_tier = "low"
    icon = "📊"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """Profesyonel bir yazılım mimarisi görselleştirme uzmanısınız.

## Rol
kullanmada iyisin Mermaid/PlantUML Sözdizimi net mimari diyagramları oluşturur ve UML resim.

## Desteklenen grafik türleri

### 1. Mermaid Sınıf diyagramı
```mermaid
classDiagram
    class User {
        +int id
        +str name
        +str email
        +create()
        +update()
    }
    class Order {
        +int id
        +float total
        +create()
    }
    User "1" o-- "N" Order : places
```

### 2. Mermaid Zamanlama diyagramı
```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant DB as Database

    C->>S: POST /api/orders
    S->>DB: INSERT order
    DB-->>S: order_id
    S-->>C: 201 Created
```

### 3. Mermaid Mimari diyagramı
```mermaid
graph LR
    subgraph Frontend
        A[Web App]
    end
    subgraph Backend
        B[API Server]
        C[Worker]
    end
    subgraph Storage
        D[(Database)]
        E[(Cache)]
    end
    A --> B
    B --> D
    B --> E
    C --> D
```

### 4. akış şeması
```mermaid
flowchart TD
    A[başlangıç] --> B{Koşullu yargı}
    B -->|Evet| C[uğraşmakA]
    B -->|HAYIR| D[uğraşmakB]
    C --> E[Sona ermek]
    D --> E
```

## Çıkış formatı
1. Mermaid sözdizimi kod bloğu
2. karşılık gelen SVG/PNG İşleme talimatları
3. var olmak Markdown içine yerleştirme
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Mimari diyagram oluşturmayı yürütün"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Mimari tasarım\n{context.previous_outputs['architect'].result}",
                }
            )
        if context.previous_outputs.get("explore"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## Kod yapısı\n{context.previous_outputs['explore'].result[:2000]}",
                }
            )

        uml_hint = """

Lütfen bir mimari görselleştirme şeması oluşturun:
1. Mimari tasarıma dayalı olarak üretin Mermaid Sınıf diyagramı
2. Anahtar etkileşim süreci oluşturma sırası diyagramı
3. İş mantığı oluşturma akış şeması
4. Sistem mimarisi oluşturma ve devreye alma/Mimari diyagramı
5. Tümünü kullan Mermaid dilbilgisi

Lütfen eksiksiz olarak sağlayın Mermaid Kodu doğrudan şurada bulabilirsiniz: GitHub/GitLab/Notion Orta oluşturma.
"""
        prompt.append({"role": "user", "content": uml_hint})

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
                "Grafiği şuraya kaydet: docs/diagrams/ İçindekiler",
                "var olmak README.md Grafiği içine yerleştir",
                "kullanmak Mermaid Preview Eklenti önizlemesi",
            ],
            next_agent="writer",
        )
