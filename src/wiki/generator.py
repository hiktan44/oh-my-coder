from __future__ import annotations

from typing import Optional

"""
Wiki Generator - Markdown dokumantasyonolustur

ayristirmodulbilgiolusturyapi Markdown dokumantasyon. 
"""

from pathlib import Path

from .parser import ClassInfo, FunctionInfo, ModuleInfo, PythonParser


class WikiGenerator:
    """Wiki dokumantasyonolustur"""

    def __init__(
        self,
        project_name: str,
        project_path: Path | str,
        parser: Optional[PythonParser] = None,
    ):
        """
        baslatolustur

        Args:
            project_name: projead
            project_path: proje yolu
            parser: Python ayristir
        """
        self.project_name = project_name
        self.project_path = Path(project_path)
        self.parser = parser or PythonParser(project_path)

    def generate(self, output_path: Path | Optional[str] = None) -> str:
        """
        olustur Wiki dokumantasyon

        Args:
            output_path: ciktidosyayol, varsayilanciktikadar REPO_WIKI.md

        Returns:
            olustur Markdown icerik
        """
        modules = self.parser.scan_directory(self.project_path)

        # goredizinyapigrupduzen
        content = self._generate_header()
        content += self._generate_summary(modules)
        content += self._generate_project_structure(modules)
        content += self._generate_module_details(modules)
        content += self._generate_footer()

        # egerbelirtciktiyol, yazgirisdosya
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            print(f"✅ Wiki dokumantasyonolustur: {output_path}")

        return content

    def _generate_header(self) -> str:
        """olusturdokumantasyonbaskisim"""
        return f"""# {self.project_name}

> ⚠️ **dikkat**: budokumantasyontarafindan oh-my-coder otomatikolustur, lutfenyapmamanuelduzenleduzenle. 
> olusturzamanarasinda: <!-- GENERATED_AT -->

---

## dizin

- [projegenel bakis](#projegenel bakis)
- [proje yapisi](#proje yapisi)
- [moduldetaycoz](#moduldetaycoz)
- [API referans](#api-referans)

---

"""

    def _generate_summary(self, modules: list[ModuleInfo]) -> str:
        """olusturprojealintiister"""
        total_files = len(modules)
        total_classes = sum(len(m.classes) for m in modules)
        total_functions = sum(len(m.functions) for m in modules)

        # istatistikiceri aktaren fazlamodul
        top_imports = sorted(
            modules,
            key=lambda m: len(m.imports),
            reverse=True,
        )[:5]

        content = "## projegenel bakis\n\n"

        if modules and modules[0].docstring:
            content += f"{modules[0].docstring}\n\n"

        content += f"""| isaretisaret | sayideger |
|------|------|
| toplamdosya sayisi | {total_files} |
| toplamsinifsayi | {total_classes} |
| toplamfonksiyonsayi | {total_functions} |

"""

        if top_imports:
            content += "### cekirdekbagimlilik\n\n"
            content += "```python\n"
            for mod in top_imports[:3]:
                for imp in mod.imports[:3]:
                    if imp.module:
                        content += f"import {imp.module}\n"
            content += "```\n\n"

        return content

    def _generate_project_structure(self, modules: list[ModuleInfo]) -> str:
        """olusturproje yapisiagac"""
        content = "## proje yapisi\n\n"
        content += "```\n"

        # goreyolpuangrup
        by_dir: dict[str, list[ModuleInfo]] = {}
        for mod in modules:
            dir_name = str(mod.relative_path.parent)
            if dir_name not in by_dir:
                by_dir[dir_name] = []
            by_dir[dir_name].append(mod)

        # olusturagacsekilyapi
        for dir_name in sorted(by_dir.keys()):
            if dir_name == ".":
                content += f"{self.project_path.name}/\n"
                prefix = "├── "
            else:
                parts = dir_name.split("/")
                indent = "│   " * (len(parts) - 1)
                content += f"{indent}├── {parts[-1]}/\n"
                prefix = indent + "│   "

            for i, mod in enumerate(
                sorted(by_dir[dir_name], key=lambda m: m.relative_path.name)
            ):
                is_last = i == len(by_dir[dir_name]) - 1
                file_prefix = "└── " if is_last else "├── "
                content += f"{prefix}{file_prefix}{mod.relative_path.name}\n"

        content += "```\n\n"

        # dizinaciklama
        if "src" in [str(m.relative_path.parent) for m in modules]:
            content += "### dizinaciklama\n\n"
            content += "| dizin | aciklama |\n|------|------|\n"
            content += "| src/ | kaynakkoddizin |\n"
            content += "| tests/ | testdosya |\n"
            content += "| docs/ | dokumantasyon |\n\n"

        return content

    def _generate_module_details(self, modules: list[ModuleInfo]) -> str:
        """olusturmoduldetay"""
        content = "## moduldetaycoz\n\n"

        for module in sorted(modules, key=lambda m: str(m.relative_path)):
            content += self._generate_module_section(module)

        return content

    def _generate_module_section(self, module: ModuleInfo) -> str:
        """olusturtekilmoduldokumantasyon"""
        rel_path = module.relative_path

        content = f"### `{rel_path}`\n\n"

        if module.docstring:
            content += f"{module.docstring}\n\n"

        # sinifliste
        if module.classes:
            content += "#### sinif\n\n"
            for cls in module.classes:
                content += self._generate_class(cls)

        # fonksiyonliste
        if module.functions:
            content += "#### fonksiyon\n\n"
            for func in module.functions:
                content += self._generate_function(func)

        return content

    def _generate_class(self, cls: ClassInfo) -> str:
        """olustursinifdokumantasyon"""
        content = f"##### `{cls.name}`\n\n"

        if cls.docstring:
            # kesaldokumantasyonkarakter dizisiincibirsatiryapicinbasitkisaaciklama
            doc_lines = cls.docstring.strip().split("\n")
            content += f"{doc_lines[0].strip()}\n\n"

        if cls.base_classes:
            content += f"**devamustlen**: {', '.join(cls.base_classes)}\n\n"

        # ortakacyontem
        public_methods = cls.public_methods
        if public_methods:
            content += "| yontem | aciklama |\n|------|------|\n"
            for method in public_methods:
                desc = (
                    method.docstring.split("\n")[0].strip() if method.docstring else ""
                )
                content += f"| `{method.signature}` | {desc} |\n"
            content += "\n"

        return content

    def _generate_function(self, func: FunctionInfo) -> str:
        """olusturfonksiyondokumantasyon"""
        content = f"##### `{func.signature}`\n\n"

        if func.docstring:
            # kesaldokumantasyonkarakter dizisiincibirblok
            doc_lines = func.docstring.strip().split("\n")
            content += f"{doc_lines[0].strip()}\n\n"

        return content

    def _generate_footer(self) -> str:
        """olusturdokumantasyonkuyrukkisim"""
        return """---

*budokumantasyontarafindan [oh-my-coder](https://github.com/VOBC/oh-my-coder) otomatikolustur*
"""
