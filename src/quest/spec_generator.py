from __future__ import annotations

from typing import Optional

"""
SPEC olustur

gorekullanicigerekisteaciklama, kullan AI modelolusturdetayli SPEC.md kuraldokumantasyon. 
"""

import re
from pathlib import Path

from ..core.router import TaskType
from ..models.base import Message
from .models import AcceptanceCriteria, Quest, QuestSpec, SpecSection

SYSTEM_PROMPT = """sendirbirdeneyimliteknikteknikmimariuzman, uzmanuzunlukgerekistedonusturicindetaylikuraldokumantasyon. 

## sengorev
gorekullanicigerekisteaciklama, olusturbirparcatam, temizlenet, olabiliryurut SPEC.md kuraldokumantasyon. 

## ciktiisteriste

### zorunluicerirbolum
1. **genel bakis** - bircumlekonusmaaciklamabugorevdirne
2. **motivasyon** - icinneisteryapbu? coznesorun? 
3. **kapsam ici** - araçisteruygulahangileriislev (kullanliste) 
4. **kapsam disi** - netharir tuthangileri (kullanliste) 
5. **kabul kriterleri** - kadaraz 5 ogreolabilirtestkabul kriterleri (herogreformat: [ ] **[AC1]** araçaciklama) 
6. **riskipucu** - olabiliredebilirkarsilaskadarsorunvecozplan
7. **teknikteknikplan** - basitisterteknikteknikuyguladusunceyol
8. **dosyaplanla** - gerekisteryeniolusturveyadegistirdosyaliste

### ruzgaristeriste
- basittemiz, net, olabiliryurut
- kabul kriterlerizorunluolabilirtest (edebiliryaztest durumugeldogrulama) 
- hayiristerderecetasarim, koru MVP asilkural
- kullanicindemetincikti

### kabul kriterleriformat
```
- [ ] **[AC1]** standartaciklama (olabilirtest) 
- [ ] **[AC2]** standartaciklama
```

### ornek
```
## kapsam ici
- kullanicikayitvegiris
- JWT kimlik dogrulama
- gizlikodtekrarayar

## kabul kriterleri
- [ ] **[AC1]** kullaniciolabilirilekullanepostakayityenihesapno
- [ ] **[AC2]** kullaniciolabilirilekullangizlikodgirissistem
- [ ] **[AC3]** girissonraalvaretkidonemicin 7 gun JWT token
```

## tekraristerasilkural
1. kabul kriterleri = test durumuaciklama (edebilirdogrubaglandonusturicintestkod) 
2. araliknet = azaltazsonradonemcekderi
3. MVP = onceyapcekirdekislev, hayiryapipekusteklecicek
"""


class SpecGenerator:
    """SPEC dokumantasyonolustur"""

    def __init__(
        self,
        model_router,  # ModelRouter instance
        project_path: Optional[Path] = None,
    ):
        self.model_router = model_router
        self.project_path = project_path or Path(".")

    async def generate(self, quest: Quest) -> QuestSpec:
        """
        olustur SPEC dokumantasyon

        Args:
            quest: Quest gorevicinnesne

        Returns:
            QuestSpec kuraldokumantasyonicinnesne
        """
        # olustur prompt
        context_info = await self._gather_context(quest)

        prompt = f"""## kullanicigerekiste
{quest.description}

{context_info}

lutfengoreileustgerekiste, olusturtam SPEC.md kuraldokumantasyon. 
"""

        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ]

        response = await self.model_router.route_and_call(
            task_type=TaskType.PLANNING,
            messages=messages,
            complexity="high",
        )

        return self._parse_spec(response.content, quest.title)

    async def _gather_context(self, quest: Quest) -> str:
        """alsetprojebaglambilgi"""
        parts = []

        # projebilgi
        project_path = Path(quest.project_path)
        parts.append(f"### proje yolu\n{project_path}")

        # pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()[:500]
                parts.append(f"### pyproject.toml\n```\n{content}\n```")
            except Exception:
                pass

        # dizinyapi (en fazla 3 katman) 
        try:
            tree_lines = []
            for p in sorted(project_path.iterdir())[:15]:
                if p.is_dir() and not p.name.startswith("."):
                    tree_lines.append(f"  📁 {p.name}/")
                    for pp in sorted(p.iterdir())[:5]:
                        if not pp.name.startswith("."):
                            tree_lines.append(f"    └─ {pp.name}")
                elif p.is_file() and not p.name.startswith("."):
                    tree_lines.append(f"  📄 {p.name}")
            if tree_lines:
                parts.append("### proje yapisi\n```\n" + "\n".join(tree_lines) + "\n```")
        except Exception:
            pass

        # README
        readme = project_path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text()[:800]
                parts.append(f"### README.md\n{content}")
            except Exception:
                pass

        return "\n\n".join(parts) if parts else ""

    def _parse_spec(self, content: str, fallback_title: str) -> QuestSpec:
        """ayristirmodelcikti, olustur QuestSpec icinnesne"""
        lines = content.split("\n")

        # cikarbaslik
        title = fallback_title
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # cikarbolum
        sections: list[SpecSection] = []
        current_title = ""
        seen_first_heading = False
        current_content: list[str] = []
        in_acceptance = False
        acceptance_criteria: list[AcceptanceCriteria] = []
        scope: list[str] = []
        out_of_scope: list[str] = []
        motivation = ""
        overview = ""
        risks: list[str] = []
        estimated_time = "1h"

        for line in lines:
            stripped = line.strip()

            # algilamabolumbaslik
            if stripped.startswith("##"):
                # kaydetustbirbolum
                if current_content:
                    content_text = "\n".join(current_content).strip()
                    if content_text:
                        sections.append(
                            SpecSection(
                                title=current_title,
                                content=content_text,
                                order=len(sections),
                            )
                        )
                    current_content = []

                section_title = stripped[2:].strip()
                current_title = section_title
                seen_first_heading = True

                if "genel bakis" in section_title:
                    in_acceptance = False
                elif "kabul kriterleri" in section_title:
                    in_acceptance = True
                elif "motivasyon" in section_title or "kapsam ici" in section_title or "risk" in section_title:
                    in_acceptance = False
                continue

            # alseticerik
            if in_acceptance:
                # ayristirkabul kriterleri
                match = re.search(r"\[AC?\d+\]", stripped, re.IGNORECASE)
                if match or stripped.startswith(("- [ ]", "-[**")):
                    # cikarstandartaciklama
                    desc = re.sub(r"^-\s*\[[\sx]\]\s*", "", stripped).strip()
                    desc = re.sub(r"\*\*\[AC\d+\]\*\*\s*", "", desc).strip()
                    if desc:
                        ac_id = f"AC{len(acceptance_criteria) + 1}"
                        acceptance_criteria.append(
                            AcceptanceCriteria(id=ac_id, description=desc)
                        )
            else:
                if not seen_first_heading:
                    # atlaincibir ## onceicerik (ornegin # baslik satir) 
                    continue
                if current_title == "genel bakis" and overview == "":
                    overview = stripped
                elif current_title == "motivasyon" and motivation == "":
                    motivation = stripped
                elif current_title == "kapsam ici" and stripped.startswith("-"):
                    scope.append(stripped.lstrip("- ").lstrip("• "))
                elif current_title == "kapsam disi" and stripped.startswith("-"):
                    out_of_scope.append(stripped.lstrip("- ").lstrip("• "))
                elif current_title == "riskipucu" and stripped.startswith("-"):
                    risks.append(stripped.lstrip("- ⚠️").lstrip("- ").lstrip("• "))
                elif current_title == "ontahmintuketzaman" or "tuketzaman" in current_title:
                    if stripped and not stripped.startswith("#"):
                        estimated_time = (
                            stripped.split()[0] if stripped.split() else "1h"
                        )
                else:
                    if stripped:
                        current_content.append(stripped)

        # kaydetensonrabirbolum
        if current_content:
            content_text = "\n".join(current_content).strip()
            if content_text:
                sections.append(
                    SpecSection(
                        title=current_title,
                        content=content_text,
                        order=len(sections),
                    )
                )

        # temizle sections, githaricayristirbolum
        excluded_titles = {
            "genel bakis",
            "motivasyon",
            "kapsam ici",
            "kapsam disi",
            "kabul kriterleri",
            "riskipucu",
        }
        sections = [s for s in sections if s.title not in excluded_titles]

        # egeryokvar acceptance_criteria, olusturvarsayilandeger
        if not acceptance_criteria:
            acceptance_criteria = [
                AcceptanceCriteria(
                    id="AC1",
                    description=f"tamamla {title} islevuygula",
                ),
                AcceptanceCriteria(
                    id="AC2",
                    description="varyeniartkodaraciligiylakodinceleme",
                ),
            ]

        return QuestSpec(
            title=title or fallback_title,
            overview=overview or title or fallback_title,
            motivation=motivation or "yukseltyukseltprojekalitemiktarveacgonderetkioran",
            scope=scope,
            out_of_scope=out_of_scope,
            acceptance_criteria=acceptance_criteria,
            risks=risks,
            estimated_time=estimated_time,
            sections=sections,
        )
