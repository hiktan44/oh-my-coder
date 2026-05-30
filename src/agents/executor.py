from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Executor Agent - Aracıyı uygulamaya yönelik kod

Sorumluluklar:
1. Kod uygulaması - Tasarıma göre kod yazın
2. Yeniden düzenleme - Kod yapısını geliştirin
3. Bug tamirat - Sorunları bulun ve düzeltin
4. Kod optimizasyonu - Performans, okunabilirlik, güvenlik

Modeli seviyesi:MEDIUM(Performans ve maliyeti dengelemek)

İş akışı:
1. Görev gereksinimlerini anlayın
2. Referans mimari tasarımı (varsa)
3. Mevcut kodu analiz edin (ilgili belgeler mevcutsa)
4. İşlev kodunu uygulama
5. Kod dosyalarını çıkarın ve kaydedin
6. Birim testleri yaz
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from ..core.dependency_resolver import DependencyResolver
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
class ExecutorAgent(BaseAgent):
    """
    vasi Agent - Çekirdek kod akıllı aracıyı uygular

    Özellikler:
    - kullanmak MEDIUM tier Modeli
    - Birden fazla dili destekleyin (Python/JavaScript/Go/TypeScript Beklemek)
    - otomatik olarak LLM Kod dosyasını çıktıdan çıkarın ve kaydedin
    - Dildeki en iyi uygulamaları ve kodlama kurallarını takip edin
    """

    name = "executor"
    description = "icra memuru - Kod uygulaması, yeniden düzenleme ve optimizasyon"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "💻"
    tools = ["file_read", "file_write", "bash", "test", "git", "web_fetch"]

    # Desteklenen programlama dilleri
    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js"],
        "typescript": [".ts", ".tsx"],
        "jsx": [".jsx", ".tsx"],
        "go": [".go"],
        "rust": [".rs"],
        "java": [".java"],
        "csharp": [".cs"],
        "cpp": [".cpp", ".cc", ".h", ".hpp"],
        "c": [".c", ".h"],
        "ruby": [".rb"],
        "php": [".php"],
        "swift": [".swift"],
        "kotlin": [".kt", ".kts"],
        "shell": [".sh", ".bash"],
        "yaml": [".yaml", ".yml"],
        "json": [".json"],
        "toml": [".toml"],
        "markdown": [".md"],
    }

    @property
    def system_prompt(self) -> str:
        return """Kıdemli bir tam yığın yazılım mühendisisiniz.

## Rol
Sizin sorumluluğunuz, gereksinimlere ve mimari tasarıma dayalı yüksek kaliteli kodu uygulamaktır.

## yetenek
1. **Kod uygulaması** - Tasarıma göre tam işlevsel kodu yazın
2. **Yeniden düzenleme** - Kod yapısını ve okunabilirliğini iyileştirin
3. **Bug tamirat** - Temel nedeni bulun ve düzeltin
4. **deneme yazımı** - Birim testi, entegrasyon testi

## Çalışma prensipleri
1. **Önce okunabilirlik** - Kod anlaşılır olmalı ve yorumlar açık olmalıdır
2. **test odaklı** - Önce testleri yazın, ardından uygulamayı yazın (isteğe bağlı)
3. **Aşamalı** - Küçük adımlarla gönderin ve sık sık doğrulayın
4. **en iyi uygulamalar** - Dil kurallarını ve tasarım kalıplarını takip edin
5. **Önce güvenlik** - Güvenlik açıklarına dikkat edin (SQL enjeksiyon,XSS, şifre düz metni vb.)

## Kodlama standartları
- **Python**: PEP 8 + tip açıklaması + docstring
- **JavaScript/TypeScript**: ESLint + Prettier + JSDoc
- **Go**: gofmt + Effective Go + Hata işleme
- **Rust**: clippy + cargo fmt

## Çıkış formatı (önemli)

### Çözüm açıklaması
Uygulama fikirlerini ve teknoloji seçimini kısaca açıklayın

### kod dosyası
kullanmak markdown Kod bloğu etiketi, format:` ```language:path/to/file.ext `

Örnek:
```python:src/calculator.py
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
```

```javascript:src/utils/helper.js
export function formatDate(date) {
    return date.toISOString().split('T')[0];
}
```

### test kodu
kullanmak `test:` Önek etiketi test dosyaları
```python:tests/test_calculator.py
def test_add():
    calc = Calculator()
    assert calc.add(1, 2) == 3
```

### Dikkat edilmesi gerekenler
- Özel yapılandırma gerektiren tüm bağımlılıklar
- Olası uç durumlar
- Geriye dönük uyumlulukla ilgili hususlar
"""

    async def _run(
        self,
        context: AgentContext,
        prompt: list[dict[str, str]],
        **kwargs,
    ) -> str:
        """Kod uygulamasını yürütün"""
        # 1. Ön sipariş çıktısı ekleyin (mimari tasarım vb.)
        self._inject_previous_outputs(context, prompt)

        # 2. İlgili dosyaları okuyun
        self._inject_relevant_files(context, prompt)

        # 3. Uygulama kılavuzu ekleyin
        prompt.append(
            {
                "role": "user",
                "content": self._build_implementation_hint(context),
            }
        )

        # 4. çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
            complexity="medium",
        )

        return response.content

    def _inject_previous_outputs(
        self, context: AgentContext, prompt: list[dict[str, str]]
    ) -> None:
        """Giriş enjekte et Agent Çıktısı"""
        outputs = context.previous_outputs
        parts = []

        if outputs.get("architect"):
            parts.append(f"## Mimari tasarım\n{outputs['architect'].result}")

        if outputs.get("analyst"):
            parts.append(f"## ihtiyaç analizi\n{outputs['analyst'].result}")

        if parts:
            prompt.append({"role": "user", "content": "\n\n".join(parts)})

    def _inject_relevant_files(
        self, context: AgentContext, prompt: list[dict[str, str]]
    ) -> None:
        """İlgili dosya içeriğini enjekte et"""
        files = context.relevant_files or []
        if not files:
            # İlgili dosyaları otomatik olarak bulun
            files = self._find_relevant_files(
                context.project_path, context.task_description
            )

        if not files:
            return

        parts = ["## İlgili belgeler\n"]
        for file_path in files[:8]:  # en 8 dosyalar
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read(3000)  # dosya başına sınır 3000 karakter
                    rel_path = file_path.relative_to(context.project_path)
                    parts.append(f"\n### {rel_path}\n```\n{content}\n```")
            except Exception:
                pass

        if len(parts) > 1:
            prompt.append({"role": "user", "content": "\n".join(parts)})

    def _find_relevant_files(
        self, project_path: Path, task_description: str
    ) -> list[Path]:
        """Görev açıklamalarına göre ilgili dosyaları akıllıca arayın"""
        relevant = []
        keywords = task_description.lower()

        # Basit anahtar kelime eşleme
        file_patterns = []
        if any(
            k in keywords for k in ["kullanıcı", "user", "Sertifikasyon", "auth", "Giriş yapmak", "login"]
        ):
            file_patterns.extend(["auth", "user", "login", "signup"])
        if any(k in keywords for k in ["api", "rest", "arayüz"]):
            file_patterns.extend(["api", "route", "endpoint"])
        if any(k in keywords for k in ["veritabanı", "db", "veritabanı", "model"]):
            file_patterns.extend(["model", "db", "database", "schema"])

        if not file_patterns:
            return []

        for root, _, files in (
            project_path.walk() if hasattr(project_path, "walk") else []
        ):
            for f in files:
                if any(p in f.lower() for p in file_patterns) and f.endswith(
                    (".py", ".js", ".ts", ".go")
                ):
                    relevant.append(root / f)

        return relevant[:8]

    def _build_implementation_hint(self, context: AgentContext) -> str:
        """Uygulama ipuçları oluşturma"""
        hint = []

        hint.append("\n## Gereksinimleri uygulayın")
        hint.append("Gerekli işlevleri uygulamak için lütfen yukarıdaki bilgileri ve görev açıklamasını kullanın.")
        hint.append("")
        hint.append("Fark etme:")
        hint.append(
            "1. kullanmak markdown Kod blokları dosya yollarını işaretler,"
            "Biçim:` ```language:path/to/file.ext `"
        )
        hint.append("2. Kod bloğundaki ilk satır bir dosya yolu olmalıdır (proje köküne göre)")
        hint.append("3. Her ana dosya için ayrı bir kod bloğu")
        hint.append("4. Test dosyaları için `test:` gibi önek etiketleri `test:tests/test_feature.py`")
        hint.append("5. Kodu basit tutun ve gerekli türdeki açıklamaları ve yorumları ekleyin")
        hint.append("6. dile dayalı PEP/Stil Kodu")

        # Belirli dil gereksinimleri varsa
        task_lower = context.task_description.lower()
        if "fastapi" in task_lower or "python" in task_lower:
            hint.append("\nİpucu: Algılandı Python proje kullanılması tavsiye edilir FastAPI çerçeve.")
        elif "react" in task_lower or "başlangıç ​​aşaması" in task_lower:
            hint.append("\nİpucu: Ön uç proje algılandı, kullanılması önerildi React + TypeScript.")

        return "\n".join(hint)

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """İşlem sonrası - Kodu çıkarın ve dosyaya kaydedin"""
        artifacts: dict[str, Any] = {}
        saved_files: list[str] = []
        errors: list[str] = []

        # 1. Kod dosyalarını çıkarın
        code_blocks = self._extract_code_blocks(result)

        # 2. Kod dosyasını kaydet
        for file_path, code_content in code_blocks:
            try:
                # Yolu temizle
                clean_path = file_path.strip().lstrip("/")
                target_path = context.project_path / clean_path

                # Dizin oluştur
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # dosyayı kaydet
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(code_content)

                saved_files.append(clean_path)
                artifacts[clean_path] = {
                    "type": "code",
                    "path": clean_path,
                    "lines": len(code_content.splitlines()),
                    "size": len(code_content),
                }

            except Exception as e:
                errors.append(f"kaydetmek {file_path} hata: {e}")

        # 3. Bağımlılıkları yüklemeyi deneyin (Python Çanta)
        dep_result = None
        if saved_files:
            dep_result = self._resolve_dependencies(context.project_path, saved_files)

        # 4. Varsa kodu biçimlendirmeyi deneyin
        self._try_format_code(context.project_path, saved_files)

        # 5. Testleri çalıştırmayı deneyin (eğer siz yazdıysanız)
        test_result = self._try_run_tests(context.project_path, saved_files)

        # 6. Önerilen sonraki adımları oluşturun
        recommendations = []
        if saved_files:
            recommendations.append(f"kaydedildi {len(saved_files)} kod dosyaları")
        if dep_result and dep_result.installed:
            recommendations.append(f"📦 Yüklü bağımlılıklar: {', '.join(dep_result.installed)}")
        if test_result["ran"]:
            if test_result["passed"]:
                recommendations.append("✅ Tüm testler geçti")
            else:
                recommendations.append(f"⚠️ Testte sorun var: {test_result['output'][:200]}")
        recommendations.extend(
            [
                "kullanmak verifier Agent Uygulamayı doğrulayın",
                "kullanmak code-reviewer Agent Kodu incele",
            ]
        )

        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            artifacts=artifacts,
            recommendations=recommendations,
            next_agent="verifier",
        )

    def _extract_code_blocks(self, content: str) -> list[tuple[str, str]]:
        """
        itibaren LLM Kod bloklarını çıktıdan çıkarın

        Desteklenen formatlar:
        - ```python:path/to/file.py
        - ```:path/to/file.py
        - ```python
          # path/to/file.py
        """
        blocks: list[tuple[str, str]] = []
        lines = content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Eşleşme kodu bloğu başlıyor
            if line.startswith("```") and not line.startswith("```:"):
                # Biçim: ```python:path/to/file.py veya ```path/to/file.py
                match = re.match(r"```(\w+)?:?\s*(.+)?", line)
                if match:
                    _ = match.group(1) or ""  # lang, unused
                    file_path = match.group(2) or ""
                    if not file_path:
                        # Bir sonraki satırdan yolu almaya çalışın
                        if (
                            i + 1 < len(lines)
                            and not lines[i + 1].startswith("#")
                            and not lines[i + 1].startswith("```")
                        ):
                            file_path = lines[i + 1].strip()
                            i += 1
                else:
                    _, file_path = "", ""

                if file_path and not file_path.startswith("#"):
                    # Kod içeriğini toplayın
                    code_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].startswith("```"):
                        code_lines.append(lines[i])
                        i += 1

                    code_content = "\n".join(code_lines).strip()
                    if code_content:
                        blocks.append((file_path, code_content))
                    continue

            elif line.startswith("```"):
                # Belki ```:path/to/file.py Biçim
                match = re.match(r"```:?\s*(.+)", line)
                if match:
                    file_path = match.group(1).strip()
                    if file_path and not file_path.startswith("```"):
                        code_lines = []
                        i += 1
                        while i < len(lines) and not lines[i].startswith("```"):
                            code_lines.append(lines[i])
                            i += 1
                        code_content = "\n".join(code_lines).strip()
                        if code_content:
                            blocks.append((file_path, code_content))
                        continue

            i += 1

        return blocks

    def _resolve_dependencies(
        self, project_path: Path, saved_files: list[str]
    ) -> Optional[DependencyResolver]:
        """ayrıştır ve yükle Python güvenmek"""
        try:
            resolver = DependencyResolver()
            python_files = [project_path / f for f in saved_files if f.endswith(".py")]
            if not python_files:
                return None

            # hepsini oku Python dosya kodu
            all_code = ""
            for py_file in python_files:
                if py_file.exists():
                    all_code += py_file.read_text(encoding="utf-8") + "\n"

            # Bağımlılıkları çözümle
            result = resolver.resolve(all_code)

            if result.missing:
                print(f"📦 Eksik bağımlılıklar bulundu: {result.missing}")
                install_result = resolver.install_dependencies(result.missing)
                if install_result["installed"]:
                    print(f"✅ Yüklendi: {install_result['installed']}")
                if install_result["failed"]:
                    print(f"⚠️ Kurulum başarısız oldu: {install_result['failed']}")
                return result
            else:
                print("✅ Tüm bağımlılıklar karşılandı")
                return result

        except Exception as e:
            print(f"⚠️ Bağımlılık çözümü başarısız oldu: {e}")
            return None

    def _try_format_code(
        self, project_path: Path, saved_files: list[str]
    ) -> dict[str, Any]:
        """Kodu biçimlendirmeyi deneyin"""
        result = {"formatted": [], "errors": []}

        for file_path in saved_files:
            full_path = project_path / file_path
            if not full_path.exists():
                continue

            ext = full_path.suffix
            formatter: Optional[list[str]] = None

            if ext == ".py":
                formatter = ["black", "--quiet", str(full_path)]
            elif ext in (".js", ".ts", ".jsx", ".tsx"):
                formatter = ["npx", "prettier", "--write", str(full_path)]
            elif ext == ".go":
                formatter = ["gofmt", "-w", str(full_path)]

            if formatter:
                try:
                    subprocess.run(
                        formatter,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )
                    result["formatted"].append(file_path)
                except Exception:
                    pass

        return result

    def _try_run_tests(
        self, project_path: Path, saved_files: list[str]
    ) -> dict[str, Any]:
        """Testi çalıştırmayı deneyin"""
        result = {
            "ran": False,
            "passed": False,
            "output": "",
            "tests_run": 0,
            "tests_failed": 0,
        }

        # Herhangi bir test dosyasının kaydedilip kaydedilmediğini kontrol edin
        test_files = [f for f in saved_files if "test_" in f or f.startswith("tests/")]

        if not test_files:
            return result

        result["ran"] = True

        # incelemek pytest Mevcut mu?
        try:
            subprocess.run(
                ["python3", "-m", "pytest", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
        except Exception:
            return result

        # Testleri çalıştır
        try:
            proc = subprocess.run(
                ["python3", "-m", "pytest", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(project_path),
            )
            result["output"] = proc.stdout + proc.stderr
            result["passed"] = proc.returncode == 0

            # Ayrıştırma testlerinin sayısı
            match = re.search(r"(\d+) passed", proc.stdout)
            if match:
                result["tests_run"] = int(match.group(1))
            match = re.search(r"(\d+) failed", proc.stdout)
            if match:
                result["tests_failed"] = int(match.group(1))

        except Exception as e:
            result["output"] = f"Error: {type(e).__name__}"

        return result
