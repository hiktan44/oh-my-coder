# Yeni LLM Sağlayıcısı Ekleme Rehberi

Bu rehber, Oh My Coder'a yeni bir LLM sağlayıcısı (Claude, GPT-5, Mistral, vb.) eklemek
için tüm adımları gösterir. Örnek olarak `src/models/gemini.py` referans alınabilir.

## Adımlar

### 1. Adaptör dosyası oluştur

`src/models/<sağlayıcı_adı>.py` dosyasını oluştur ve `BaseModel`'i implement et.
En kolay yol, OpenAI uyumlu bir endpoint varsa onu kullanmak (`gemini.py`'a bak).

Gerekli alanlar:
- `MODELS` sözlüğü: low / medium / high tier'lar için model adları + maliyet.
- `provider` property → `ModelProvider` enum değeri döner.
- `model_name` property → seçilen tier'ın model adını döner.
- `async generate()` ve `async stream()` metotları.

### 2. `ModelProvider` enum'ına ekle

`src/models/base.py`:
```python
class ModelProvider(Enum):
    ...
    CLAUDE = "claude"   # ← yeni sağlayıcı
```

### 3. `src/models/__init__.py`'da kayıt et

```python
from .claude import ClaudeAPIError, ClaudeModel
...
__all__ = [..., "ClaudeModel", "ClaudeAPIError"]
```

### 4. `RouterConfig`'e API key alanı ekle

`src/core/router.py`:
```python
@dataclass
class RouterConfig:
    ...
    claude_api_key: Optional[str] = None
```

Sonra `__post_init__` içinde env'den oku:
```python
self.claude_api_key = self.claude_api_key or os.getenv("CLAUDE_API_KEY")
```

### 5. Router'ın init bloğuna ekle

Aynı dosyada GLM/Gemini bloklarının yanına:
```python
if self.config.claude_api_key:
    try:
        from ..models.claude import ClaudeModel
        for tier in ["low", "medium", "high"]:
            cfg = ModelConfig(api_key=self.config.claude_api_key)
            self._models.setdefault("claude", {})[tier] = ClaudeModel(
                cfg, ModelTier(tier)
            )
    except Exception as e:
        logger.warning(f"Claude başlatma hatası: {mask_api_key(str(e))}")
```

### 6. `_key_map` ve `cloud_fallback` listelerini güncelle

Aynı dosyada `_load_from_config_file` içindeki `_key_map`:
```python
"claude": "claude_api_key",
```

Ve `cloud_fallback` listesine `"claude"` ekle (fallback sırasında nerede olsun istersen).

### 7. Ayar dosyalarına ekle

**`~/.omc/.env`**:
```
CLAUDE_API_KEY=your_api_key
```

**`~/.omc/config.json`** (opsiyonel — Web UI ayarlar sekmesinden de girilebilir):
```json
"claude": {
  "api_key": "",
  "base_url": "https://api.anthropic.com/v1",
  "temperature": 0.6
}
```

### 8. Test

```bash
.venv/bin/python -c "from src.models import ClaudeModel; print('OK')"
omc doctor run
omc run "merhaba" -m claude --simple
```

## OpenAI uyumlu endpoint kısayolu

Birçok sağlayıcı OpenAI uyumlu uç nokta sunar (Gemini, Together, Groq, Anyscale, DeepInfra…).
Bu durumda `gemini.py` neredeyse aynısı kullanılır — sadece `base_url`, model adları ve
maliyetler değişir. Authentication `Bearer <key>` header'ı standarttır.

## Model adı/tier eşlemesi

`src/models/<sağlayıcı>.py` içindeki `MODELS` sözlüğünde:
- `low`  → ucuz/hızlı (sıralı görevler, explore agent)
- `medium` → dengeli (varsayılan)
- `high` → en kaliteli (kritik mantık, kod review)

Tier seçimi `BaseModel.tier` üzerinden otomatik yapılır; uygulamada `-m <sağlayıcı>` yeter.
