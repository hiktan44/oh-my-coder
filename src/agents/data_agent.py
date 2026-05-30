"""
DataAgent - veri işleme ve ETL ajan

Sorumluluklar:
1. Veri temizleme ve dönüştürme
2. ETL Montaj hattı tasarımı
3. Verileri dışa aktarma ve içe aktarma
4. Veri doğrulama komut dosyası

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
class DataAgent(BaseAgent):
    """veri işleme ve ETL ajan"""

    name = "data"
    description = "veri işleme ve ETL ajan - Veri temizleme, içe ve dışa aktarma, boru hattı"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "📥"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """Siz bir veri mühendisliği uzmanısınız.

## Rol
Veri temizlemede iyi misiniz?ETL Boru hattı tasarımı ve veri içe ve dışa aktarımı.

## yetenek
1. CSV / Excel / JSON Veri işleme
2. Veri temizleme (tekilleştirme, doldurma, tür dönüştürme)
3. ETL montaj hattı (Pandas / Polars)
4. Veri aktarımı (veritabanı / belge)

## Veri temizleme özellikleri
```python
import pandas as pd

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # Yinelenenleri kaldır
    df = df.drop_duplicates()

    # Eksik değerleri doldurun
    df["age"] = df["age"].fillna(df["age"].median())

    # tür dönüşümü
    df["created_at"] = pd.to_datetime(df["created_at"])

    return df
```

## ETL Örnek
```python
def etl_pipeline():
    # Extract
    df = pd.read_csv("raw_data.csv")

    # Transform
    df = clean_data(df)

    # Load
    df.to_sql("clean_data", engine, if_exists="replace")
```

## Çıkış formatı
1. Veri kalitesi raporu
2. Kodu temizle
3. ETL montaj hattı
4. Doğrulama komut dosyası
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """Veri işlemeyi gerçekleştirin"""
        data_hint = """

Lütfen veri işlemeye devam edin:
1. Veri kalitesini analiz edin (eksik değerler, kopyalar, aykırı değerler)
2. Veri temizleme kodunu sağlayın
3. tasarım ETL montaj hattı
4. Veri doğrulama komut dosyaları sağlayın
"""
        prompt.append({"role": "user", "content": data_hint})

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
                "Temizlemeden sonra veri kalitesini doğrulayın",
                "Zamanlama oluştur ETL Görev",
                "Veri akrabalığını kaydedin",
            ],
        )
