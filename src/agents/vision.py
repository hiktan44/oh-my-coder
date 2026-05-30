from __future__ import annotations

from typing import Optional

"""
Vision Agent - görsel analiz ve UI Temsilci oluştur

Sorumluluklar:
1. ekran görüntüsü / UI Görüntü analizi
2. Düzen sorunu tespiti
3. Görsel değişiklik önerileri
4. UI kod oluşturma (HTML/CSS/React bileşenler vb.)
5. Tasarım kodu incelemesi

Modeli seviyesi:MEDIUM(denge, yazışma sonnet)
"""

from pathlib import Path

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


def _load_image_meta(image_path: Path) -> Optional[dict]:
    """Görüntü meta bilgilerini (genişlik, yükseklik, boyut) olmadan çıkarın Pillow Ayrıca çalışıyor."""
    try:
        import struct

        with open(image_path, "rb") as f:
            data = f.read(64)

        # PNG: IHDR chunk starts at offset 16
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w = struct.unpack(">I", data[16:20])[0]
            h = struct.unpack(">I", data[20:24])[0]
            return {"format": "PNG", "width": w, "height": h, "path": str(image_path)}

        # JPEG: SOF0 at offset 2+7 ~ 160
        if data[:2] == b"\xff\xd8":
            with open(image_path, "rb") as f:
                f.read(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2:
                        break
                    m = struct.unpack(">H", marker)[0]
                    if m == 0xFFC0 or m == 0xFFC2:
                        f.read(1)
                        h = struct.unpack(">H", f.read(2))[0]
                        w = struct.unpack(">H", f.read(2))[0]
                        return {
                            "format": "JPEG",
                            "width": w,
                            "height": h,
                            "path": str(image_path),
                        }
                    length = struct.unpack(">H", f.read(2))[0]
                    f.read(length - 2)
            return {"format": "JPEG", "path": str(image_path)}

        # WebP: RIFF....WEBP
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return {"format": "WEBP", "path": str(image_path)}

        return {"format": "unknown", "path": str(image_path)}

    except Exception:
        return None


def _extract_code_blocks(text: str) -> list[dict[str, str]]:
    """
    Kod bloklarını metinden çıkarın.

    Desteklenen formatlar:
    ```language
    code
    ```
    veya
    ```lang:filename
    code
    ```

    Returns:
        List[Dict]: [{"language": str, "filename": str, "code": str}]
    """
    import re

    blocks = []
    # Match ```language or ```language:filename
    pattern = re.compile(
        r"```(\w+)?(?::([\w./\\-]+))?\n(.*?)```",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        language = match.group(1) or "text"
        filename = match.group(2) or _default_filename(language)
        code = match.group(3).rstrip("\n")
        blocks.append({"language": language, "filename": filename, "code": code})
    return blocks


def _default_filename(language: str) -> str:
    """Dile göre varsayılan dosya adını döndürür."""
    defaults = {
        "html": "index.html",
        "css": "style.css",
        "javascript": "script.js",
        "js": "script.js",
        "jsx": "Component.jsx",
        "tsx": "Component.tsx",
        "typescript": "script.ts",
        "ts": "script.ts",
        "vue": "Component.vue",
        "svelte": "Component.svelte",
        "python": "generated.py",
        "py": "generated.py",
        "json": "data.json",
        "svg": "icon.svg",
    }
    return defaults.get(language.lower(), f"generated.{language}")


def _infer_output_dir(context: AgentContext) -> Path:
    """Çıkış dizinini çıkarın."""
    if context.working_directory and Path(context.working_directory).exists():
        return Path(context.working_directory)
    if context.project_path and Path(context.project_path).exists():
        return Path(context.project_path)
    return Path.cwd() / "vision_output"


@register_agent
class VisionAgent(BaseAgent):
    """
    görsel analiz ve UI kod üretimi Agent

    İki mod desteklenir:
    1. **görsel inceleme**(varsayılan)- Ekran görüntülerini analiz edin ve düzen verin/renk eşleştirme/Etkileşim sorunları ve değişiklik önerileri
    2. **UI kod üretimi** - Ekran görüntülerine dayalı olarak karşılık gelen görselleri otomatik olarak oluşturun HTML/CSS/React bileşen kodu
    """

    name = "vision"
    description = "görsel analiz ve UI kod oluşturma aracısı - Ekran görüntüsü düzeni analizi ve UI Kod otomatik olarak oluşturuldu"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "👁️"
    tools = ["file_read", "file_write", "web_search"]

    # Desen listesi
    MODE_ANALYSIS = "analysis"
    MODE_UI_CODE = "ui_code"

    @property
    def system_prompt(self) -> str:
        base = """sen son sınıftasın UI/UX Tasarımcılar ve ön uç geliştiriciler.

## Rol
Ekran görüntülerini analiz etme konusunda iyisiniz ve UI görüntüler, görsel sorunları tanımlayın ve değişiklikler için özel öneriler verin.
Aynı zamanda şunları yapabilirsiniz: UI ekran görüntüsü**İlgili kodu otomatik olarak oluştur**.

## yetenek
1. **düzen analizi** - aralık, hizalama, hiyerarşi
2. **renk yolu incelemesi** - Renk kontrastı, erişilebilirlik
3. **Etkileşim analizi** - Düğme konumu, tıklama alanı, yanıt alanı
4. **Sorun tanımlama** - Görsel tutarsızlık, beyaz alan sorunları, tipografi sorunları
5. **Değişiklik önerileri** - spesifik CSS mülk / bileşen kodu
6. **UI kod üretimi** - Ekran görüntülerine göre oluşturuldu HTML/CSS/React/Vue Kodu bekleyin

## Analiz Boyutları (Görsel İnceleme Modu)

### 1. Düzen sorunları
- [ ] Öğeler tutarlı bir şekilde hizalanmış mı?
- [ ] Aralıklar eşit mi?
- [ ] Görsel hiyerarşi açık mı?
- [ ] Öğelerin örtüşmesinin olup olmadığı

### 2. Renk eşleştirme sorunu
- [ ] Metin ve arka plan arasındaki kontrast mı ≥ 4.5:1
- [ ] Birincil ve ikincil renkler açıkça ayırt ediliyor mu?
- [ ] Marka renk özelliklerine uygun mu?

### 3. Dizgi sorunları
- [ ] Yazı tipi boyutu açıkça katmanlı mı?
- [ ] Sıra yüksekliği rahat mı (önerilir) 1.5-1.8)
- [ ] Başlık, gövde metni ve açıklama metni açıkça farklılaştırılmış mı?

### 4. Etkileşim sorunları
- [ ] Tuş düğmeleri belirgin mi?
- [ ] Tıklanabilir alanın yeterince büyük olup olmadığı (≥ 44px)
- [ ] Yeterli görsel geri bildirim var mı?

## Görsel İnceleme Raporu Formatı

```
# görsel inceleme raporu

## 📊 Resim bilgileri
- boyut: 1920×1080
- Biçim: PNG

## 🎯 Temel sorunlar (önceliğe göre)

### P0 - ciddi sorun
1. **Yetersiz metin kontrastı**
   - Konum: Gezinme çubuğunun sağ tarafındaki yardımcı metin
   - akım: #999999 var olmak #FFFFFF arka plan
   - Zıtlık: 2.8:1(Gerekmek ≥ 4.5:1)
   - Tekrar düzeltme yapmak: Şuna değiştir: #666666 → Zıtlık 5.9:1

### P1 - önemli sorular
1. **Düğme boyutu çok küçük**
   - Konum: Alt işlem çubuğu
   - akım: yüksek 28px
   - Tekrar düzeltme yapmak: ≥ 44px
   - CSS: `height: 44px; min-height: 44px;`

### P2 - Optimizasyon önerileri
1. Aralığın şu şekilde birleştirilmesi tavsiye edilir: 8px katları
2. Simge boyutu önerileri 20×20px
3. Hiyerarşi duygusunu geliştirmek için kart gölgesi derinleştirilebilir

## ✅ Önceliği değiştir
| öncelik | soru | Değişiklik maliyeti |
|--------|------|---------|
| P0 | metin kontrastı | 1TAMAM CSS |
| P1 | düğme boyutu | 2TAMAM CSS |
| P2 | Aralık optimizasyonu | yapısal uyum |
```
"""

        ui_code_prompt = """
---

## UI kod oluşturma modu (output_format=ui_code)

Kullanıcı oluşturma isteğinde bulunduğunda UI Kodlama yaparken şunları yapmanız gerekir:
1. **Ekran görüntülerini dikkatlice analiz edin**: hepsini tanımla UI Öğeler (düğmeler, formlar, gezinme, kartlar vb.)
2. **Tasarım ayrıntılarını çıkarın**: Renk, yazı tipi boyutu, aralık, yuvarlatılmış köşeler, gölge, simge
3. **Yüksek kaliteli kod oluşturun**: Çıkış formatı için ```language:filename kod ``` işaret

### Desteklenen çıktı formatları

| Biçim | göstermek | Tipik kullanımlar |
|------|------|---------|
| `html` | saf HTML + satır içi stiller | hızlı prototipleme |
| `css` | bağımsız CSS belge | Ve HTML İşbirliği yapın |
| `javascript` / `js` | etkileşim mantığı | Form doğrulama, animasyon |
| `jsx` / `tsx` | React bileşenler | React proje |
| `vue` | Vue bileşenler | Vue proje |
| `svelte` | Svelte bileşenler | Svelte proje |

### üretken prensip

**Doğru restorasyon**:
- Renk değerleri mümkün olduğu kadar doğrudur (ekran görüntülerinden alınmıştır) hex/rgb)
- Yazı tipi boyutu ve aralığı, ekran görüntüsündeki gerçek piksel değerlerini kullanır
- Görsel orantıyı ve hiyerarşiyi koruyun

**Kod kalitesi**:
- HTML anlamsal (header/nav/main/section/article/footer)
- CSS kullanmak Flexbox/Grid düzen,BEM isim
- React Bileşenler için fonksiyon bileşenleri + hooks stil

**aşamalı geliştirme**:
- Temel sürüm:HTML + CSS(en yaygın)
- Geliştirilmiş sürüm:React/Vue Bileşenler (isteğe bağlı)

### Çıkış örneği

```
Ekran görüntüsünü analiz ettim ve aşağıdakileri belirledim UI yapı:

**Sayfa düzeni**:Üst gezinme + kenar çubuğu + Ana içerik alanı + Alt işlem çubuğu
**renk sistemi**:
- ana renk: #3B82F6(mavi)
- arka plan: #F9FAFB(açık gri)
- Kelime: #111827(koyu gri)
**Bileşen listesi**:
- Gezinme çubuğu (logo + menü öğesi + Kullanıcı avatarı)
- Arama kutusu (yuvarlak giriş kutusu + arama simgesi)
- Kart Listesi (Resim) + başlık + betimlemek + çalıştırma düğmesi)
- alt TabBar(ön sayfa/Keşfetmek/bilgi/bana ait)

İşte oluşturulan kod:

```html:index.html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated UI</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="navbar">
    <div class="navbar-logo">Logo</div>
    <nav class="navbar-menu">...</nav>
  </header>
  <!-- tüm HTML yapı -->
</body>
</html>
```

```css:style.css
/* Ekran görüntülerinin stilini doğru bir şekilde geri yükleyin */
.navbar {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 16px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
/* Daha fazla stil */
*/
```

```tsx:components/PageLayout.tsx
import React from "react";

export const PageLayout: React.FC = () => {
  return (
    <header className="navbar">
      {/* ... */}
    </header>
  );
};
```

---

**önemli**: Her kod bloğu şununla bitmelidir: `language:filename` başlangıç ​​(örneğin `html:index.html`),
Dosyaları otomatik olarak kolayca çıkarın ve kaydedin.
"""
        return base + ui_code_prompt

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """görsel analiz yapın veya UI kod üretimi"""
        image_path: Optional[Path] = context.metadata.get("image_path")
        output_format: str = context.metadata.get("output_format", self.MODE_ANALYSIS)

        extra_context = ""

        if image_path:
            path = Path(image_path)
            if path.exists():
                meta = _load_image_meta(path)
                if meta:
                    size_info = (
                        f"{meta['width']}×{meta['height']}"
                        if meta.get("width")
                        else "bilinmiyor"
                    )
                    extra_context = (
                        f"\n## 📊 Resim bilgileri\n"
                        f"- yol: `{path}`\n"
                        f"- Biçim: {meta.get('format', 'unknown')}\n"
                        f"- boyut: {size_info}\n\n"
                    )

        # Projelerdeki görüntüleri tarayın
        if context.project_path and context.project_path.exists():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
            images = [
                str(p)
                for p in context.project_path.rglob("*")
                if p.suffix.lower() in image_extensions and p.is_file()
            ]
            if images:
                extra_context += (
                    "## 📁 Projedeki görüntü dosyaları\n"
                    + "\n".join(f"- {i}" for i in images[:10])
                    + "\n"
                )

        # Mod kararı: öncelikli kullanım metadata içinde output_format
        mode_hint: str
        if output_format == self.MODE_UI_CODE:
            mode_hint = """

## 🎯 Mevcut mod:UI kod üretimi

Lütfen yukarıdaki ekran görüntülerini kapsamlı bir şekilde inceleyin UI analiz etmek ve**İlgili kodu otomatik olarak oluştur**:

1. **tanımlamak UI eleman**: Gezinme çubuğu, düğme, giriş kutusu, kart, liste vb.
2. **Tasarım ayrıntılarını çıkarın**: Renk, yazı tipi, aralık, yuvarlatılmış köşeler, gölge
3. **Kod dosyaları oluştur**:kullanmak ```language:filename kod ``` çıktı biçimi

Lütfen aşağıdaki dosyaları oluşturun (gerektiği gibi seçin):
- `html:index.html` - Sayfa yapısı
- `css:style.css` - stil sayfası
- `tsx:components/*.tsx` - React Bileşenler (isteğe bağlı)

**Gerekmek**:
- Kod doğrudan çalıştırılabilir (bir dosyaya kopyalayın ve önizlemek için bir tarayıcıda açın)
- Renk değerleri mümkün olduğu kadar doğrudur (ekran görüntülerinden alınmıştır)
- Duyarlı kalın
- HTML anlamsal,CSS kullanmak Flexbox/Grid
"""
        else:
            mode_hint = """

## 🎯 Mevcut Mod: Görsel İnceleme

Lütfen yukarıdakilerin ekran görüntüsünü alın/UI Kapsamlı bir görsel analiz için resimler:
1. Tüm düzen ve görsel sorunları tanımlayın
2. Her sorunun ciddiyetini belirtin (P0/P1/P2)
3. Özel değişiklik önerileri sağlayın (kodla birlikte)/CSS)
4. Eksiksiz bir görsel inceleme raporunun çıktısını alın

Birden fazla görsel sağlanmışsa lütfen bunları tek tek analiz edip karşılaştırın.
"""

        if extra_context:
            prompt.append(
                {
                    "role": "system",
                    "content": f"## Ek Bilgiler\n{extra_context}",
                }
            )
        prompt.append({"role": "user", "content": mode_hint})

        # çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
        )

        # UI Kod oluşturma modu: kod bloklarını çıkarın ve kaydedin
        if output_format == self.MODE_UI_CODE:
            blocks = _extract_code_blocks(response.content)
            if blocks:
                output_dir = _infer_output_dir(context)
                saved_files: dict[str, str] = {}
                for block in blocks:
                    file_path = output_dir / block["filename"]
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(block["code"], encoding="utf-8")
                    saved_files[block["filename"]] = str(file_path)
                # Kaydetme yolunu sonuca enjekte et
                file_list = "\n".join(
                    f"- `{fn}` → `{fp}`" for fn, fp in saved_files.items()
                )
                response.content += (
                    f"\n\n---\n"
                    f"**📁 Oluşturuldu {len(saved_files)} dosyalar**:\n{file_list}\n"
                    f"**Çıkış dizini**: `{output_dir}`"
                )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """İşlem sonrası"""
        output_format: str = context.metadata.get("output_format", self.MODE_ANALYSIS)
        recommendations: list[str]
        if output_format == self.MODE_UI_CODE:
            recommendations = [
                "Oluşturulanı aç HTML Dosya önizleme efekti",
                "Ayrıntıları gerçek oluşturma efektine göre ayarlayın",
                "Oluşturulan bileşenler mevcut projelere entegre edilebilir",
            ]
        else:
            recommendations = [
                "Kodlara görsel değişiklik önerileri uygulayın",
                "kullanmak VisionAgent Değiştirilen efektleri tekrar gözden geçirin",
            ]

        # Kaydedilen dosya yollarını çıkarın (sonuçların sonundaki listeden)
        artifacts: dict[str, str] = {}
        if output_format == self.MODE_UI_CODE:
            blocks = _extract_code_blocks(result)
            for block in blocks:
                filename = block["filename"]
                # Sonuçlardan tam yolu bulmaya çalışın
                for line in result.split("\n"):
                    if f"`{filename}`" in line:
                        import re

                        m = re.search(r"`(/[^`]*)`", line)
                        if m:
                            artifacts[filename] = m.group(1)
                        break
                if filename not in artifacts:
                    output_dir = _infer_output_dir(context)
                    artifacts[filename] = str(output_dir / filename)

        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            artifacts=artifacts,
            recommendations=recommendations,
        )
