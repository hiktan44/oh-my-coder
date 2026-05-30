# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Explore Agent - Kod tabanı keşif aracısı

Sorumluluklar:
1. Kod tabanını hızla tarayın ve dosyalar oluşturun/sembol eşleme
2. Proje yapısını ve teknoloji yığınını tanımlama
3. Anahtar dosyaları ve bağımlılıkları keşfedin
4. Takip için Agent bağlam sağlamak

Modeli seviyesi:LOW(Hızlı ve ucuz, karşılık gelen haiku)

İş akışı:
1. Dizin yapısını tara
2. Dosya türlerini ve dağıtımını tanımlama
3. Anahtar sembolleri çıkarın (fonksiyonlar, sınıflar, modüller)
4. Proje haritası oluştur
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@dataclass
class FileInfo:
    """Dosya bilgileri"""

    path: str
    type: str  # python, javascript, markdown, etc.
    size: int
    lines: int
    importance: float  # 0-1, konum ve adlandırma çıkarımına dayalı


@dataclass
class ProjectMap:
    """proje haritası"""

    root_path: str
    language_distribution: dict[str, int]  # dil -> Dosya sayısı
    key_directories: list[str]
    entry_points: list[str]  # Giriş dosyası
    config_files: list[str]
    test_files: list[str]
    dependencies: list[str]  # bağımlılık (dan package.json/requirements.txt çıkarmak)
    structure_tree: str  # dizin ağacı


@register_agent
class ExploreAgent(BaseAgent):
    """
    Kod tabanı keşfi Agent

    Özellikler:
    - kullanmak LOW tier Model (hızlı ve ucuz)
    - Kodu derinlemesine anlamanıza gerek yok, sadece yapıyı tanıyın
    - Yapılandırılmış proje haritasını dışa aktar
    """

    name = "explore"
    description = "Kod tabanı keşif aracısı - Proje haritalarını hızla tarayın ve oluşturun"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "low"
    icon = "🔍"
    tools = ["file_read", "directory_scan"]

    @property
    def system_prompt(self) -> str:
        return """Profesyonel bir kod tabanı keşif ajanısınız.

## Rol
Sizin sorumluluğunuz, kod tabanını hızlı bir şekilde taramak ve sonraki analizlere temel oluşturmak üzere dosyalar ile semboller arasındaki eşleme ilişkisini oluşturmaktır.

## yetenek
1. Dizin yapısı taraması - Projenin nasıl organize edildiğini belirleyin
2. Teknoloji yığını tanımlama - Dosya türlerinden ve yapılandırmalardan teknoloji yığınını çıkarın
3. Anahtar dosya konumu - Giriş dosyasını, yapılandırma dosyasını ve çekirdek modülü bulun
4. Bağımlılık analizi - itibaren package.json,requirements.txt Bağımlılıkların çıkarılmasını bekleyin

## Çalışma prensipleri
1. **hızlı öncelik** - Kodu derinlemesine okumayın, sadece yapıyı tanımlayın
2. **Yapılandırılmış çıktı** - kullanmak Markdown Tablolar ve kod blokları bilgileri düzenler
3. **Öne Çıkanlar** - En önemli dosya ve dizinleri işaretleyin
4. **dil tarafsız** - Birden fazla programlama dilini destekleyin

## Çıkış formatı
Çıktınız şunları içermelidir:
1. Projeye genel bakış (dil, çerçeve, ölçek)
2. dizin yapısı ağacı
3. Anahtar dosyaların listesi (açıklamayla birlikte)
4. Teknoloji yığını özeti
5. Önerilen ileri keşif yolları

## Dikkat edilmesi gerekenler
- Öğenin işlevselliği hakkında tahminde bulunmayın, yalnızca gözlemlenen gerçekleri açıklayın
- Anahtar bilgi bulunamıyorsa açıkça belirtin
- Basit tutun ve fazlalıktan kaçının
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """
        Kod tabanı keşfi gerçekleştirin

        adım:
        1. Dizin yapısını tara
        2. Dosya istatistiklerini toplayın
        3. Proje haritasını oluşturmak için modeli çağırın
        """
        project_path = context.project_path

        # 1. Dizin yapısını tara
        structure = self._scan_directory(project_path)

        # 2. Dosya istatistiklerini toplayın
        file_stats = self._collect_file_stats(project_path)

        # 3. Bağımlılık bilgilerini çıkarın
        dependencies = self._extract_dependencies(project_path)

        # 4. Yapıyı tamamla prompt
        exploration_context = f"""
## Tarama sonuçları

### Dizin yapısı
```
{structure}
```

### Dosya istatistikleri
{self._format_file_stats(file_stats)}

### Bilgiye bağlı
{self._format_dependencies(dependencies)}

Lütfen yukarıdaki bilgilere dayanarak proje haritaları ve keşif önerileri oluşturun.
"""

        prompt.append({"role": "user", "content": exploration_context})

        # 5. çağrı modeli
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        # Yönlendirici kullanarak bir model seçin
        response = await self.call_model(
            task_type=TaskType.EXPLORE,
            messages=messages,
            complexity="low",  # Explore kullanmak LOW tier
        )

        return response.content

    def _scan_directory(
        self,
        root_path: Path,
        max_depth: int = 3,
        ignore_dirs: set = None,
    ) -> str:
        """Dizin yapısını tarayın ve bir ağaç gösterimi oluşturun"""
        if ignore_dirs is None:
            ignore_dirs = {
                "__pycache__",
                ".git",
                "node_modules",
                ".venv",
                "venv",
                "build",
                "dist",
                ".idea",
                ".vscode",
                ".pytest_cache",
            }

        lines = []

        def scan(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return

            try:
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                return

            dirs = [x for x in items if x.is_dir() and x.name not in ignore_dirs]
            files = [x for x in items if x.is_file()]

            # Görüntülenen dosya sayısını sınırlayın
            max_files = 20
            if len(files) > max_files:
                shown_files = files[:max_files]
                hidden_count = len(files) - max_files
            else:
                shown_files = files
                hidden_count = 0

            for i, dir_item in enumerate(dirs):
                is_last = (i == len(dirs) - 1) and not shown_files
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{dir_item}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                scan(dir_item, new_prefix, depth + 1)

            for i, file_item in enumerate(shown_files):
                is_last = (i == len(shown_files) - 1) and hidden_count == 0
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{file_item.name}")

            if hidden_count > 0:
                lines.append(f"{prefix}└── ... ({hidden_count} more files)")

        lines.append(f"{root_path.name}/")
        scan(root_path, "", 0)

        return "\n".join(lines)

    # Maksimum taranan dosya sayısı. Limit aşıldıktan sonra sadece dosya türü sayılacak ve satır sayısı artık satır satır okunmayacaktır.
    _MAX_SCAN_FILES = 500

    def _collect_file_stats(
        self,
        root_path: Path,
        ignore_dirs: set = None,
    ) -> dict[str, Any]:
        """Dosya istatistiklerini toplayın"""
        if ignore_dirs is None:
            ignore_dirs = {
                "__pycache__",
                ".git",
                "node_modules",
                ".venv",
                "venv",
                "build",
                "dist",
                ".idea",
                ".vscode",
                ".pytest_cache",
                ".omc",
                ".mypy_cache",
                ".ruff_cache",
                "htmlcov",
                "site-packages",
                ".tox",
                "eggs",
                ".eggs",
            }

        language_map = {}
        total_files = 0
        total_lines = 0
        key_files = []

        # Dil eşleme için dosya uzantısı
        ext_to_lang = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript (React)",
            ".tsx": "TypeScript (React)",
            ".go": "Go",
            ".java": "Java",
            ".md": "Markdown",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".txt": "Text",
            ".sh": "Shell",
        }

        for root, dirs, files in os.walk(root_path):
            # Yoksayılan dizinleri filtrele
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                ext = Path(file).suffix.lower()
                lang = ext_to_lang.get(ext, "Other")

                language_map[lang] = language_map.get(lang, 0) + 1
                total_files += 1

                # Satır sayısını sayın (üst sınırı aştıktan sonra satır satır okumayı atlayın, tahmin etmek için dosya boyutunu kullanın)
                file_path = Path(root) / file
                try:
                    if total_files <= self._MAX_SCAN_FILES:
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            lines = sum(1 for _ in f)
                            total_lines += lines
                    else:
                        # Hızlı tahmin: başına 50 Yaklaşık bayt 1 TAMAM
                        size = file_path.stat().st_size
                        total_lines += size // 50
                except Exception:
                    pass

                # Önemli belgeleri tanımlayın
                if file in ["main.py", "app.py", "index.js", "index.ts", "__init__.py"]:
                    key_files.append(str(Path(root).relative_to(root_path) / file))

        return {
            "language_distribution": language_map,
            "total_files": total_files,
            "total_lines": total_lines,
            "key_files": key_files,
        }

    def _extract_dependencies(
        self,
        root_path: Path,
    ) -> dict[str, list[str]]:
        """Proje bağımlılıklarını ayıklayın"""
        dependencies = {
            "python": [],
            "node": [],
            "other": [],
        }

        # Python güvenmek
        req_file = root_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file) as f:
                    dependencies["python"] = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
            except Exception:
                pass

        # Node güvenmek
        package_file = root_path / "package.json"
        if package_file.exists():
            try:
                import json

                with open(package_file) as f:
                    package = json.load(f)
                    dependencies["node"] = list(package.get("dependencies", {}).keys())
            except Exception:
                pass

        return dependencies

    def _format_file_stats(self, stats: dict[str, Any]) -> str:
        """Biçimlendirilmiş dosya istatistikleri"""
        lines = []

        lines.append(f"- Toplam dosya sayısı:{stats['total_files']}")
        lines.append(f"- Toplam kod satırı:{stats['total_lines']:,}")

        lines.append("\n### Dil dağıtımı")
        for lang, count in sorted(
            stats["language_distribution"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"- {lang}: {count} belge")

        if stats["key_files"]:
            lines.append("\n### anahtar belgeler")
            for file in stats["key_files"]:
                lines.append(f"- {file}")

        return "\n".join(lines)

    def _format_dependencies(self, deps: dict[str, list[str]]) -> str:
        """Bağımlılık bilgilerini biçimlendir"""
        lines = []

        if deps["python"]:
            lines.append("### Python güvenmek")
            for dep in deps["python"][:20]:  # Görüntüleme miktarını sınırlayın
                lines.append(f"- {dep}")
            if len(deps["python"]) > 20:
                lines.append(f"- ... ({len(deps['python']) - 20} more)")

        if deps["node"]:
            lines.append("### Node güvenmek")
            for dep in deps["node"][:20]:
                lines.append(f"- {dep}")
            if len(deps["node"]) > 20:
                lines.append(f"- ... ({len(deps['node']) - 20} more)")

        if not lines:
            lines.append("(Bağımlı dosyalar bulunamadı)")

        return "\n".join(lines)

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """İşlem sonrası - Önemli bilgileri çıkarın"""
        # İşlem sonrası - Anahtar bilgileri çıkarın (şu anda yer tutucu olarak uygulanmaktadır)
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "kullanmak analyst Agent Proje gereksinimlerinin derinlemesine analizi",
                "kullanmak architect Agent Tasarım sistemi mimarisi",
            ],
            next_agent="analyst",
        )
