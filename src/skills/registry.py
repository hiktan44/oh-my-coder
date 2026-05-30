from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Skill kayiticindekalp - biryonetveyurut Skill

tasarim: 
- Skill dirbaglanal (code, context) donus SkillResult  Python fonksiyon
- icindeayar Skill: /review, /test, /doc
- kullaniciozel Skill: ~/.omc/skills/*.py, otomatikyukle
- destek CLI cagri: omc skill list / omc skill run <name>
"""


import importlib.util
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


# ─── sayigoreyapi ────────────────────────────────────────────────────────────────


@dataclass
class Skill:
    """Skill tanim"""

    name: str
    description: str
    func: Callable[[str, dict[str, Any]], SkillResult]
    source: str = "builtin"  # builtin | custom
    file_path: Optional[Path] = None

    def __post_init__(self) -> None:
        # otomatikfonksiyon docstring doldurdoldur description
        if not self.description and self.func.__doc__:
            first_line = self.func.__doc__.strip().split("\n")[0]
            self.description = first_line.strip()


@dataclass
class SkillResult:
    """Skill yurutme sonucu"""

    success: bool
    output: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }


# ─── icindeayar Skill uygula ─────────────────────────────────────────────────────────


def _review_skill(code: str, context: dict[str, Any]) -> SkillResult:
    """kodinceleme Skill"""
    import time

    start = time.perf_counter()
    lines = code.splitlines()
    issues: list[str] = []
    suggestions: list[str] = []

    # temeltemelkodkalitemiktarkontrol
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # TODO yorumkontrol (mevcutsadecekontrolsatiruzunlukderece, TODO isaretgerektekiltekkural) 
        if len(stripped) > 120 and not stripped.startswith("#"):
            issues.append(f"L{i}: satiruzunluk ({len(stripped)} chars)")

        if stripped.endswith(",") and i < len(lines):
            next_line = lines[i].strip()
            if not next_line:
                issues.append(f"L{i}: olabiliredebilireksikazdegissatir")

        # algilamabelirginguvenliksorun
        if "eval(" in stripped:
            issues.append(f"L{i}: kullan eval() olabiliredebilirneden olurkodenjekte")
        if "shell=True" in stripped and "subprocess" in stripped:
            issues.append(f"L{i}: subprocess shell=True olabiliredebilirneden olurkomutenjekte")

    # algilamatekrartekrarkodblok (basitsurum) 
    line_hashes: dict[str, list[int]] = {}
    for i, line in enumerate(lines, 1):
        h = hash(line.strip())
        if h in line_hashes:
            line_hashes[h].append(i)
        else:
            line_hashes[h] = [i]

    duplicates = {h: idx for h, idx in line_hashes.items() if len(idx) >= 3}
    suggestions.extend(
        [
            f"bagladevambenzersatir L{idx_list[0]}-{idx_list[-1]}: dusuncikaricinfonksiyon"
            for idx_list in duplicates.values()
        ]
    )

    suggestions.append(f"kodtoplamsatirsayi: {len(lines)}")
    suggestions.append(f"incelemezamanarasinda: {(time.perf_counter() - start) * 1000:.1f}ms")

    return SkillResult(
        success=True,
        output=f"kesfet {len(issues)} sorun, {len(suggestions)} ogreoneri",
        metadata={"issues": issues, "suggestions": suggestions},
        duration_ms=(time.perf_counter() - start) * 1000,
    )


def _test_skill(code: str, context: dict[str, Any]) -> SkillResult:
    """testolustur Skill"""
    import time

    start = time.perf_counter()
    test_cases: list[str] = []
    lines = code.splitlines()
    functions: list[str] = []

    # algilamafonksiyontanim
    for _i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("def test_", "async def test_")):
            functions.append(stripped)
        elif (stripped.startswith(("def ", "async def "))) and not stripped.startswith(
            "def __"
        ):
            # cikarfonksiyonisim
            import re

            m = re.match(r"(?:async\s+)?def\s+(\w+)", stripped)
            if m:
                fname = m.group(1)
                functions.append(stripped)
                test_cases.append(
                    f"def test_{fname}():\n"
                    f'    """Test {fname}"""'
                    f"\n    # {{ uygulatestmantik }}\n    pass\n"
                )

    # olusturtestiskelet
    test_content = (
        '"`python"\n'
        + "# otomatikolusturtestdosya\n"
        + "# satir: python -m pytest tests/\n\n"
        + "import pytest\n"
        + "from pathlib import Path\n\n"
    )

    for tc in test_cases:
        test_content += tc + "\n"

    duration_ms = (time.perf_counter() - start) * 1000
    return SkillResult(
        success=True,
        output=test_content,
        metadata={
            "functions_found": len(functions),
            "test_cases_generated": len(test_cases),
        },
        duration_ms=duration_ms,
    )


def _doc_skill(code: str, context: dict[str, Any]) -> SkillResult:
    """dokumantasyonolustur Skill"""
    import time

    start = time.perf_counter()
    lines = code.splitlines()
    doc_parts: list[str] = []
    in_docstring = False
    current_doc: list[str] = []
    module_name = context.get("module_name", "module")
    file_path = context.get("file_path", "")

    doc_parts.append(f"# {Path(file_path).stem if file_path else module_name}\n")
    doc_parts.append("> otomatikolusturmoduldokumantasyon\n")

    # alset docstring
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(('"""', "'''")):
            if not in_docstring:
                in_docstring = True
                current_doc = []
            else:
                in_docstring = False
                if current_doc:
                    doc_parts.append("\n## modulaciklama\n")
                    doc_parts.append("\n".join(current_doc) + "\n")
                    current_doc = []

        elif in_docstring and stripped:
            current_doc.append(f"{i}: {stripped}")

    # alsetfonksiyonimzaisim
    funcs: list[str] = []
    for _i, line in enumerate(lines, 1):
        stripped = line.strip()
        if (stripped.startswith(("def ", "async def "))) and not stripped.startswith(
            "def _"
        ):
            import re

            m = re.match(r"(async\s+)?def\s+(\w+)\((.*?)\)", stripped)
            if m:
                fname = m.group(2)
                params = m.group(3)
                funcs.append(f"- `{fname}({params})`")

    if funcs:
        doc_parts.append("\n## ortakac API\n\n")
        doc_parts.append("\n".join(funcs) + "\n")

    doc_parts.append(
        f"\n<!-- otomatikolusturde {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n"
    )

    duration_ms = (time.perf_counter() - start) * 1000
    return SkillResult(
        success=True,
        output="".join(doc_parts),
        metadata={"functions_documented": len(funcs)},
        duration_ms=duration_ms,
    )


# ─── SkillRegistry ────────────────────────────────────────────────────────────


class SkillRegistry:
    """Skill kayitveyoneticindekalp"""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._custom_skills_dir: Optional[Path] = None
        self._loaded_custom: bool = False
        self._init_builtins()

    def _init_builtins(self) -> None:
        """kayiticindeayar Skill"""
        builtins = [
            Skill(
                name="review",
                description="kodinceleme - kontrolkodkalitemiktarveguvenliksorun",
                func=_review_skill,
            ),
            Skill(
                name="test",
                description="olusturtest - icinkod uretimi pytest test durumu",
                func=_test_skill,
            ),
            Skill(
                name="doc",
                description="olusturdokumantasyon - icinmodulolustur Markdown dokumantasyon",
                func=_doc_skill,
            ),
        ]
        for skill in builtins:
            self.register(skill)

    # ─── kayit/sorgu ───────────────────────────────────────────────────────────

    def register(self, skill: Skill) -> None:
        """kayitbir Skill"""
        self._skills[skill.name] = skill
        logger.debug("Registered skill: %s (source=%s)", skill.name, skill.source)

    def unregister(self, name: str) -> bool:
        """yorumiptalbir Skill"""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def get(self, name: str) -> Optional[Skill]:
        """al Skill"""
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        """tumunu listelevar Skill (icindeayaroncelik) """
        return list(self._skills.values())

    def list_builtin(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.source == "builtin"]

    def list_custom(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.source == "custom"]

    # ─── yukleozel Skill ────────────────────────────────────────────────────

    def set_custom_dir(self, path: Path) -> None:
        """ayarlaayarozel Skill dizin"""
        self._custom_skills_dir = path
        self._loaded_custom = False  # tekrarayar, altkezyurutzamantekraryeniyukle

    def load_custom_skills(self) -> int:
        """ozeldizinyukle Skill"""
        if self._custom_skills_dir is None:
            # varsayilan ~/.omc/skills/
            self._custom_skills_dir = Path.home() / ".omc" / "skills"

        skill_dir = self._custom_skills_dir
        if not skill_dir.is_dir():
            logger.debug("Custom skills dir does not exist: %s", skill_dir)
            return 0

        count = 0
        for py_file in skill_dir.glob("*.py"):
            # atla __init__.py
            if py_file.name.startswith("__"):
                continue
            try:
                self._load_skill_from_file(py_file)
                count += 1
            except Exception as exc:
                logger.warning("Failed to load custom skill %s: %s", py_file.name, exc)

        self._loaded_custom = True
        logger.info("Loaded %d custom skills from %s", count, skill_dir)
        return count

    def _load_skill_from_file(self, file_path: Path) -> None:
        """ Python dosyayukletekil Skill"""
        module_name = f"omc_custom_skill_{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # ara skill_xxx fonksiyonveya SKILL sikmiktar
        if hasattr(module, "SKILL") and isinstance(module.SKILL, Skill):
            skill = module.SKILL
            skill.source = "custom"
            skill.file_path = file_path
            self.register(skill)
        else:
            # alsetvar skill_ acbasfonksiyon
            for attr_name in dir(module):
                if attr_name.startswith("skill_"):
                    func = getattr(module, attr_name)
                    if callable(func):
                        skill_name = attr_name[6:]  # kaldir skill_ onceek
                        skill = Skill(
                            name=skill_name,
                            description=func.__doc__ or attr_name,
                            func=func,
                            source="custom",
                            file_path=file_path,
                        )
                        self.register(skill)

    # ─── yurut ────────────────────────────────────────────────────────────────

    def run(
        self, name: str, code: str = "", context: Optional[dict[str, Any]] = None
    ) -> SkillResult:
        """yurutbelirt Skill"""
        # saglarozel Skill yukle
        if not self._loaded_custom:
            self.load_custom_skills()

        skill = self._skills.get(name)
        if skill is None:
            return SkillResult(
                success=False,
                error=f"Skill '{name}' not found. Run 'omc skill list' to see available skills.",
            )

        ctx = context or {}
        try:
            return skill.func(code, ctx)
        except Exception as exc:
            logger.exception("Skill %s failed: %s", name, exc)
            return SkillResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def run_interactive(
        self, skill_name: str, code: str = "", context: Optional[dict[str, Any]] = None
    ) -> SkillResult:
        """etkilesimmodyurut Skill (destek /name dilyontem) """
        # kaldiracbas /
        name = skill_name.lstrip("/")
        return self.run(name, code, context)

    # ─── goster ────────────────────────────────────────────────────────────────

    def display_list(self) -> None:
        """iletablosekiltarzgostervar Skill"""
        table = Table(title="Available Skills")
        table.add_column("Name", style="cyan bold")
        table.add_column("Source", style="dim")
        table.add_column("Description", style="white")

        for skill in self.list_all():
            table.add_row(
                f"/{skill.name}",
                skill.source,
                skill.description or "",
            )

        console.print(table)


# ─── globaltekilornek ────────────────────────────────────────────────────────────────
_default_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """alglobal Skill kayittablo (gecikmebaslat) """
    global _default_registry
    if _default_registry is None:
        _default_registry = SkillRegistry()
        # deneyuklekullaniciozel Skill
        _default_registry.load_custom_skills()
    return _default_registry
