from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"

"""
Skill kendiilerlesistem - SkillManager

Sorumluluk:
1. yonet .omc/skills/ dizinalt Skill dosya (CRUD) 
2. bakim .omc/skills/index.json zamanindeks
3. saglararayetenek (gore name/description/tags/category) 
4. patch oncelikde create (bolumatla token) 
5. otomatikbiriktirtetikgonderdegerlendir

dizinyapi: 
.omc/skills/
├── index.json          # tummiktarindeks
├── debugging/
│   ├── slow-query-fix/
│   │   └── SKILL.md    # YAML frontmatter + Markdown metin
│   └── ...
├── workflow/
├── corrections/
└── best-practices/

SKILL.md format: 
---
name: slow-query-fix
description: iyi SQL sorguperformansadim
category: debugging
tags: [sql, performance, database]
triggers:
  - sorguyavas
  - database timeout
created_at: 2026-04-12
updated_at: 2026-04-12
---

# Slow Query Fix

ne zamankesfet SQL sorguyanityavaszaman...
"""


import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Optional

import yaml

# olabilirsec: tiktoken kullandekesin token hesapla
try:
    import tiktoken

    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False


class SkillManager:
    """Skill dosyayonet"""

    # birlestiryontem categories
    CATEGORIES = ["debugging", "workflow", "corrections", "best-practices"]

    def __init__(self, skills_dir: Optional[Path] = None):
        """
        Args:
            skills_dir: Skills kokdizin, varsayilanicin .omc/skills
        """
        self.skills_dir = skills_dir or Path(".omc/skills")
        self.index_file = self.skills_dir / "index.json"
        self._index: dict[str, dict[str, Any]] = {}
        self._init()
        self._load_index()

    # ------------------------------------------------------------------
    # baslat
    # ------------------------------------------------------------------

    def _init(self) -> None:
        """baslatdizinyapi"""
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        for cat in self.CATEGORIES:
            (self.skills_dir / cat).mkdir(exist_ok=True)

    def _load_index(self) -> None:
        """yukleindeksdosya"""
        if self.index_file.exists():
            try:
                self._index = json.loads(self.index_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        """kaydetindeksdosya"""
        self.index_file.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # indekstekrarolustur (kullandeduzeltmezararkotuindeks) 
    # ------------------------------------------------------------------

    def rebuild_index(self) -> int:
        """taravar SKILL.md dosya, tekrarolustur index.json"""
        self._index = {}
        count = 0
        for cat in self.CATEGORIES:
            cat_dir = self.skills_dir / cat
            if not cat_dir.exists():
                continue
            for skill_dir in cat_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                meta = self._parse_frontmatter(skill_md)
                if meta:
                    skill_id = skill_dir.name
                    self._index[skill_id] = {
                        "name": meta.get("name", skill_id),
                        "description": meta.get("description", ""),
                        "category": cat,
                        "tags": meta.get("tags", []),
                        "triggers": meta.get("triggers", []),
                        "created_at": meta.get("created_at", ""),
                        "updated_at": meta.get("updated_at", ""),
                        "path": str(skill_md),
                    }
                    count += 1
        self._save_index()
        return count

    # ------------------------------------------------------------------
    # Frontmatter ayristir
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(skill_md: Path) -> Optional[dict[str, Any]]:
        """ SKILL.md ayristir YAML frontmatter"""
        try:
            content = skill_md.read_text(encoding="utf-8")
        except OSError:
            return None

        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return None

    @staticmethod
    def _serialize_frontmatter(meta: dict[str, Any]) -> str:
        """sira frontmatter icin YAML karakter dizisi"""
        # sadecekoru frontmatter alan
        keys = [
            "name",
            "description",
            "category",
            "tags",
            "triggers",
            "created_at",
            "updated_at",
        ]
        fm = {k: meta[k] for k in keys if k in meta}
        return yaml.dump(
            fm, allow_unicode=True, default_flow_style=False, sort_keys=False
        )

    # ------------------------------------------------------------------
    # cekirdek CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        body: str,
        category: str = "workflow",
        tags: Optional[list[str]] = None,
        triggers: Optional[list[str]] = None,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        olusturyeni Skill

        Args:
            name: Skill ad (kullandedizinisim, otomatik slugify) 
            body: Markdown metin
            category: puansinif (debugging/workflow/corrections/best-practices) 
            tags: etiketliste
            triggers: tetikgonderanahtar kelimeliste
            description: bircumlekonusmaaciklama (otomatik body ilksatircikaregericinbos) 

        Returns:
            olustur Skill bilgi dict (icerir skill_id) 
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"yoketki category '{category}', olabilirsec: {self.CATEGORIES}")

        # Slugify dizinisim
        skill_id = self._slugify(name)
        if not skill_id:
            raise ValueError(f"yokyontem name '{name}' olusturvaretki slug")

        skill_dir = self.skills_dir / category / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = skill_dir / "SKILL.md"

        # kontrololup olmadigikaydeticinde
        if skill_md.exists():
            raise FileExistsError(
                f"Skill '{skill_id}' kaydeticinde, lutfenkullan patch() veolmayan create()"
            )

        # otomatikcikar description
        if description is None:
            # al body incibirsatirolmayanbossatiryapicinaciklama
            first_line = ""
            for line in body.strip().split("\n"):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    first_line = stripped
                    break
            description = first_line[:200] if first_line else name

        now = time.strftime("%Y-%m-%d")
        meta = {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags or [],
            "triggers": triggers or [],
            "created_at": now,
            "updated_at": now,
        }

        full_content = (
            f"---\n{self._serialize_frontmatter(meta)}---\n\n{body.strip()}\n"
        )
        skill_md.write_text(full_content, encoding="utf-8")

        self._index[skill_id] = {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags or [],
            "triggers": triggers or [],
            "created_at": now,
            "updated_at": now,
            "path": str(skill_md),
        }
        self._save_index()

        return {"skill_id": skill_id, **meta}

    def patch(
        self,
        skill_id: str,
        body: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        triggers: Optional[list[str]] = None,
        name: Optional[str] = None,
        category: str = "workflow",
    ) -> dict[str, Any]:
        """
        artmiktarguncelle Skill (oncelikde create) 

        sadeceguncelleiletgirisalan, koruasilvardeger. 
        eger Skill mevcut degil, otomatikdonusturicin create. 

        Args:
            skill_id: Skill ID (dizinisim) 
            body: Markdown metin (sadecedegistir --- sonrakisimpuan) 
            description: bircumlekonusmaaciklama
            tags: etiketliste (degistir) 
            triggers: tetikgonderanahtar kelimeliste (degistir) 
            name: Skill ad

        Returns:
            guncellesonra Skill bilgi
        """
        # oncearaasildosya
        skill_path = self._find_skill_path(skill_id)

        if skill_path is None:
            # mevcut degil, otomatik create (body gereklidoldur) 
            if body is None:
                raise ValueError(f"Skill '{skill_id}' mevcut degil, vehenuzsaglar body, yokyontemolustur")
            return self.create(
                name=name or skill_id,
                body=body,
                category=category,
                tags=tags,
                triggers=triggers,
                description=description,
            )

        # okuasilvar frontmatter
        old_meta = self._parse_frontmatter(skill_path) or {}
        category = old_meta.get("category", "workflow")

        # birlestirveguncelle
        now = time.strftime("%Y-%m-%d")
        new_meta = {**old_meta}
        if description is not None:
            new_meta["description"] = description
        if tags is not None:
            new_meta["tags"] = tags
        if triggers is not None:
            new_meta["triggers"] = triggers
        if name is not None:
            new_meta["name"] = name
        new_meta["updated_at"] = now

        # egersadeceguncelle body veolmayan frontmatter, koruasilvar meta
        if body is not None:
            # okuasilvar body
            content = skill_path.read_text(encoding="utf-8")
            match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
            match.group(1).strip() if match else content.strip()
            new_body = body.strip()

            full_content = (
                f"---\n{self._serialize_frontmatter(new_meta)}---\n\n{new_body}\n"
            )
        else:
            # sadeceguncelle frontmatter
            full_content = skill_path.read_text(encoding="utf-8")
            full_content = re.sub(
                r"^---\n.*?\n---",
                f"---\n{self._serialize_frontmatter(new_meta)}---",
                full_content,
                count=1,
                flags=re.DOTALL,
            )

        skill_path.write_text(full_content, encoding="utf-8")

        # guncelleindeks
        self._index[skill_id] = {
            "name": new_meta.get("name", skill_id),
            "description": new_meta.get("description", ""),
            "category": category,
            "tags": new_meta.get("tags", []),
            "triggers": new_meta.get("triggers", []),
            "created_at": new_meta.get("created_at", now),
            "updated_at": now,
            "path": str(skill_path),
        }
        self._save_index()

        return {"skill_id": skill_id, **self._index[skill_id]}

    def delete(self, skill_id: str) -> bool:
        """sil Skill veonundizin"""
        skill_path = self._find_skill_path(skill_id)
        if skill_path is None:
            return False

        # sildizin
        skill_dir = skill_path.parent
        shutil.rmtree(skill_dir)

        # indekskaldir
        if skill_id in self._index:
            del self._index[skill_id]
            self._save_index()

        return True

    # ------------------------------------------------------------------
    # sorgu
    # ------------------------------------------------------------------

    def list_skills(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        listele Skills

        Args:
            category: gorepuansiniffiltrele
            tag: goreetiketfiltrele
            limit: donusustsinir

        Returns:
            Skill bilgiliste (hayiricerir body) 
        """
        results = []
        for sid, info in self._index.items():
            if category and info.get("category") != category:
                continue
            if tag and tag not in (info.get("tags") or []):
                continue
            results.append({**info, "skill_id": sid})

        # gore updated_at ters sira
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results[:limit]

    def get_skill(
        self,
        skill_id: str,
        include_body: bool = False,
    ) -> Optional[dict[str, Any]]:
        """
        altekil Skill

        Args:
            skill_id: Skill ID
            include_body: olup olmadigiicerir Markdown metin

        Returns:
            Skill bilgi dict, icerir skill_id; mevcut degildonus None
        """
        info = self._index.get(skill_id)
        if info is None:
            return None

        result = {"skill_id": skill_id, **info}

        if include_body:
            path = Path(info["path"])
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # kaldir frontmatter
                match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
                result["body"] = match.group(1).strip() if match else content.strip()
            else:
                result["body"] = ""

        return result

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        tummetinara Skills

        Args:
            query: arama anahtar kelimeleri (bospuankelime, AND mantik) 
            category: gorepuansiniffiltrele
            tags: goreetiketfiltrele (gorevbireslestir) 
            limit: donusustsinir

        Returns:
            eslestir Skill bilgiliste
        """
        query_terms = query.lower().split()
        results = []

        for sid, info in self._index.items():
            if category and info.get("category") != category:
                continue
            if tags and not any(t in (info.get("tags") or []) for t in tags):
                continue

            # birlestirbaglanarametin
            searchable = " ".join(
                [
                    info.get("name", ""),
                    info.get("description", ""),
                    " ".join(info.get("tags", [])),
                    " ".join(info.get("triggers", [])),
                ]
            ).lower()

            # AND eslestirvar term
            if all(term in searchable for term in query_terms):
                results.append({**info, "skill_id": sid})

        # ilgiliderecesirala: tamamtumeslestir > adicerir > aciklamaicerir
        def score(x: dict[str, Any]) -> int:
            s = 0
            full = f"{x.get('name', '')} {x.get('description', '')}".lower()
            for term in query_terms:
                if term in x.get("name", "").lower():
                    s += 3
                elif term in full:
                    s += 1
            return s

        results.sort(key=score, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # aracyontem
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(text: str) -> str:
        """herhangimetindonusturicinbirlestiryontemdizinisim"""
        # kucukyaz
        s = text.lower()
        # degistirbos/ozelkarakter
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[_\s]+", "-", s)
        s = re.sub(r"-+", "-", s)
        s = s.strip("-")
        # siniruzunlukderece
        if len(s) > 48:
            s = s[:48].rstrip("-")
        return s

    def _find_skill_path(self, skill_id: str) -> Optional[Path]:
        """icindevar category icindeara skill_id karsilik gelen SKILL.md yol"""
        for cat in self.CATEGORIES:
            path = self.skills_dir / cat / skill_id / "SKILL.md"
            if path.exists():
                return path
        return None

    def get_skill_inventory(self, max_tokens: int = 500) -> str:
        """
        olustur Tier 0 enjektemetin: Skill isimharf + bircumlekonusmaaciklama. 

        ciddisinirciktihayirasiri max_tokens. 
        format: [skill-name]: aciklama (hersatirbir, hayirister Markdown liste) 

        Args:
            max_tokens: enbuyuk token sayi (varsayilan 500) 

        Returns:
            sekilornegin "skill_id: description\n..." karakter dizisi
        """
        has_tiktoken = _HAS_TIKTOKEN

        if has_tiktoken:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
            except Exception:
                has_tiktoken = False

        if not has_tiktoken:
            # gerigeri: kabacatahmin 1 token ≈ 4 karakter
            max_chars = max_tokens * 4
            return self._get_inventory_fallback(max_chars)

        lines = []
        total_tokens = 0

        # gore updated_at sirala, enyenioncelik
        sorted_skills = sorted(
            self._index.items(),
            key=lambda x: x[1].get("updated_at", ""),
            reverse=True,
        )

        for sid, info in sorted_skills:
            # hersatirformat: skill_id: description
            line = f"{sid}: {info.get('description', '')}"
            line_tokens = len(enc.encode(line))
            newline_tokens = 1  # degissatirsembol

            if total_tokens + line_tokens + newline_tokens > max_tokens:
                break

            lines.append(line)
            total_tokens += line_tokens + newline_tokens

        count = len(self._index)
        header = f"[{count} Skills]\n"

        if lines:
            result = header + "\n".join(lines)
            if count > len(lines):
                result += f"\n... (+{count - len(lines)} more)"
            return result
        return f"[{count} Skills] (none)"

    def _get_inventory_fallback(self, max_chars: int) -> str:
        """gerigeriplan: gorekaraktersayikes"""
        lines = []
        total = 0
        sorted_skills = sorted(
            self._index.items(),
            key=lambda x: x[1].get("updated_at", ""),
            reverse=True,
        )
        for sid, info in sorted_skills:
            line = f"{sid}: {info.get('description', '')}"
            if total + len(line) + 1 > max_chars:
                break
            lines.append(line)
            total += len(line) + 1

        count = len(self._index)
        header = f"[{count} Skills]\n"
        if lines:
            result = header + "\n".join(lines)
            if count > len(lines):
                result += f"\n... (+{count - len(lines)} more)"
            return result
        return f"[{count} Skills] (none)"

    # ------------------------------------------------------------------
    # otomatikbiriktirdegerlendir
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_skill_worthy(
        tool_call_count: int,
        had_error: bool,
        had_fix: bool,
        had_user_correction: bool,
        is_nontrivial_workflow: bool,
    ) -> bool:
        """
        karar vermevcutyurutolup olmadigidegerbiriktiricin Skill

        tetikgonderkosul (doluyeterligorevbir) : 
        1. araccagri ≥5 kezvebasarili
        2. hata → coz
        3. kullaniciduzelt
        4. olmayansiradanis akisi (cokadim) 

        Args:
            tool_call_count: araccagrikezsayi
            had_error: olup olmadigiyanlis
            had_fix: olup olmadigihataicindekurtar
            had_user_correction: kullaniciolup olmadigiduzelt
            is_nontrivial_workflow: olup olmadigiicincokadimis akisi

        Returns:
            True = degerbiriktir
        """
        if tool_call_count >= 5:
            return True
        if had_error and had_fix:
            return True
        if had_user_correction:
            return True
        return bool(is_nontrivial_workflow)

    @staticmethod
    def build_skill_from_execution(
        agent_name: str,
        task_description: str,
        workflow_name: str,
        final_result: str,
        key_steps: Optional[list[str]] = None,
        error_context: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        birkezyurutolustur Skill taslak

        kullandeotomatikbiriktirzamanolustur SKILL.md icerik. 

        Args:
            agent_name: kullan Agent isim
            task_description: gorev aciklamasi
            workflow_name: is akisiisim
            final_result: ensonsonucalintiister
            key_steps: anahtaradimliste
            error_context: hatabaglam (egervar) 

        Returns:
            olabilirdogrubaglaniletver create()  dict (icerir name, body, category, tags, triggers) 
        """
        # cikaranahtar kelimeyapicin triggers
        triggers = []
        for word in task_description.split():
            if len(word) >= 3 and word.lower() not in {
                "the",
                "and",
                "for",
                "with",
                "from",
            }:
                triggers.append(word.strip(".,!?;:"))

        # karar ver category
        if error_context or "error" in task_description.lower():
            category = "debugging"
        elif workflow_name in {"build", "refactor", "test"}:
            category = "workflow"
        elif bool(error_context):
            category = "corrections"
        else:
            category = "workflow"

        # olustur name
        name = f"{workflow_name}-{agent_name}"[:48]

        # olustur body
        body_lines = [
            f"# {workflow_name.title()} with {agent_name.title()}",
            "",
            f"**gorev**: {task_description}",
            f"**is akisi**: {workflow_name}",
            f"**Agent**: {agent_name}",
            "",
            "## anahtaradim",
        ]

        if key_steps:
            for i, step in enumerate(key_steps, 1):
                body_lines.append(f"{i}. {step}")
        else:
            body_lines.append(f"1. tanigorevtip: {workflow_name}")
            body_lines.append("2. planlayurutadim")
            body_lines.append("3. goreplanyurut")
            body_lines.append("4. dogrulama sonucu")

        body_lines.extend(
            [
                "",
                "## yurutme sonucu",
                final_result[:300],
            ]
        )

        if error_context:
            body_lines.extend(
                [
                    "",
                    "## hata isleme",
                    error_context[:200],
                ]
            )

        body_lines.extend(
            [
                "",
                "## uygunkullankosul",
                f"- gorevtip: {workflow_name}",
                f"- tetikgonderkelime: {', '.join(triggers[:5])}",
            ]
        )

        return {
            "name": name,
            "body": "\n".join(body_lines),
            "category": category,
            "tags": [workflow_name, agent_name, *triggers[:3]],
            "triggers": triggers[:5],
            "description": task_description[:120].strip(),
        }
