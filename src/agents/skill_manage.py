from __future__ import annotations

"""
Skill kişisel gelişim Agent

Enstrümantal sağlayın Skill CRUD diğerleri için operasyon Agent Arama.

Araçlar (modele kayıtlı):
- create: yeni oluştur Skill
- patch: artımlı güncelleme Skill(öncelik)
- delete: silmek Skill
- list: liste Skills(Destek category/tag filtre)
- view: tekli görüntüle Skill(İçermek body)

Tasarım ilkeleri:
- patch öncelik almak create(kaydetmek token)
- Tüm işlemlere devam edilir .omc/skills/
- geçmek SkillManager Temel dosyaları yönetin
"""

from pathlib import Path
from typing import Any, Optional

from ..memory.skill_manager import SkillManager
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@register_agent
class SkillManageAgent(BaseAgent):
    """
    Skill üstesinden gelmek Agent

    Sorumluluklar:
    1. tedarik Skill CRUD Araçlar (model çağrıları için)
    2. sürdürmek .omc/skills/ İçindekiler ve Dizin
    3. Arama ve sorgulamayı destekleyin
    """

    name = "skill-manage"
    description = "Skill kişisel gelişim yönetimi — yaratmak/yenilemek/silmek/Sorgu .omc/skills/ Biriktirme dosyalarını deneyimleyin"
    lane = AgentLane.COORDINATION
    default_tier = "low"  # En düşük maliyet modelini kullanan saf yönetim işlemleri
    icon = "🧩"
    tools: list[str] = []  # Harici araçlara gerek yok, aracın kendisi

    def __init__(self, model_router, config: Optional[dict[str, Any]] = None):
        super().__init__(model_router, config)
        # SkillManager Örnekler paylaşılabilir
        skills_dir = None
        if config:
            skills_dir = config.get("skills_dir")
        if skills_dir:
            skills_dir = Path(skills_dir)
        self.sm = SkillManager(skills_dir=skills_dir)

    @property
    def system_prompt(self) -> str:
        return """sen bir Skill Kendini geliştiren yönetici.

## sorumluluklarınız
sürdürmek .omc/skills/ Aşağıdaki deneyim yağış dosyası başkalarına yardımcı olacaktır Agent Tarihsel deneyimi yeniden kullanın.

## Dosya yapısı
.omc/skills/
├── index.json
├── debugging/      # Hata ayıklama deneyimi (bug fix,troubleshooting)
├── workflow/       # İş akışı deneyimi (yeniden düzenleme, test etme vb.)
├── corrections/    # Düzeltildikten sonra onarım (kullanıcı hatası düzeltme çökelmesi)
└── best-practices/ # en iyi uygulamalar

## SKILL.md Biçim
```markdown
---
name: Beceri adı
description: Bir cümlelik açıklama
category: debugging|workflow|corrections|best-practices
tags: [python, refactor]
triggers: [Yeniden düzenleme, flask]
created_at: 2026-04-12
updated_at: 2026-04-12
---

# Metin içeriği
...
```

## alet

### list — liste Skills
filtre:category(Hata ayıklama deneyimi/İş akışı/doğru/en iyi uygulamalar),tag
parametre yok = hepsini listele

### view — tekli görüntüle Skill
parametre:skill_id(gerekli)
İsteğe bağlı:include_body=true

### create — yeni oluştur Skill
parametre:name, body(metin), category, description, tags, triggers
⚠️ İlk önce kullan patch! sadece Skill mevcut olmadığında create

### patch — Artımlı güncellemeler (öncelik)
parametre:skill_id(gerekli), body, description, tags, triggers
- Yalnızca değiştirilecek alanları geçin ve diğerlerini koruyun.
- eğer Skill yok, var body ne zaman otomatik olarak oluşturulur

### delete — silmek Skill
parametre:skill_id(gerekli)

### search — Tam metin araması
parametre:query(anahtar kelime, boşluk katılımcısı,AND mantık)
İsteğe bağlı:category, tags

## karar kuralları
- **patch öncelik**:Mevcut olanı değiştir Skill her zaman kullan patch,HAYIR create
- **Önce kontrol et sonra yaz**: Oluşturmadan önce list Var olmadığını doğrulayın
- **Açıklama gerekli**:description Başkalarına yardım edin Agent bunu buldum Skill

## Çıkış formatı
Her alet çağrısından sonra sonuçlar kısaca raporlanır (başarılı/hata/İçerik özeti).
"""

    # ------------------------------------------------------------------
    # araç uygulaması (doğrudan yöntem,BaseAgent.execute modele maruz kalacak)
    # ------------------------------------------------------------------

    def tool_list(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Araçlar: liste Skills"""
        skills = self.sm.list_skills(category=category, tag=tag, limit=limit)
        if not skills:
            return "(sonuç yok)"

        lines = []
        for s in skills:
            lines.append(
                f"- **{s['skill_id']}** [{s.get('category', '')}] "
                f"{s.get('description', '')} "
                f"[{' / '.join(s.get('tags', [])[:3])}]"
            )
        return "\n".join(lines) or "(sonuç yok)"

    def tool_view(
        self,
        skill_id: str,
        include_body: bool = False,
    ) -> str:
        """Araçlar: Tek bir tanesini görüntüleyin Skill"""
        skill = self.sm.get_skill(skill_id, include_body=include_body)
        if skill is None:
            return f"Skill '{skill_id}' mevcut değil"

        parts = [
            f"## {skill['name']} (`{skill['skill_id']}`)",
            f"**sınıflandırma**: {skill.get('category', '')}",
            f"**betimlemek**: {skill.get('description', '')}",
            f"**Etiket**: {', '.join(skill.get('tags', []))}",
            f"**kelimeleri tetiklemek**: {', '.join(skill.get('triggers', []))}",
            f"**yaratmak**: {skill.get('created_at', '')} | **yenilemek**: {skill.get('updated_at', '')}",
        ]
        if include_body and skill.get("body"):
            parts.append("\n---\n\n" + skill["body"])

        return "\n".join(parts)

    def tool_create(
        self,
        name: str,
        body: str,
        category: str = "workflow",
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        triggers: Optional[list[str]] = None,
    ) -> str:
        """
        Araçlar: Yeni oluştur Skill(otomatik patch öncelik)

        İlk önce aynı adı kontrol edin Skill Var mı:
        - Zaten var → otomatik olarak olarak değiştirildi patch(artımlı güncelleme)
        - mevcut değil → yeni oluştur Skill
        """
        skill_id = self.sm._slugify(name)

        # Var olup olmadığını kontrol edin (patch öncelik)
        existing = self.sm.get_skill(skill_id)
        if existing:
            # otomatik olarak dönüştürülür patch
            try:
                result = self.sm.patch(
                    skill_id=skill_id,
                    body=body,
                    description=description,
                    tags=tags,
                    triggers=triggers,
                    name=name,
                    category=category,
                )
                return (
                    f"✅ Skill Zaten mevcut, otomatik olarak şuna dönüştürüldü: patch: `{skill_id}`\n"
                    f"   betimlemek: {result.get('description', '')}"
                )
            except Exception as e:
                return f"❌ Patch hata: {e}"

        # Mevcut değil, yeni oluştur Skill
        try:
            result = self.sm.create(
                name=name,
                body=body,
                category=category,
                description=description,
                tags=tags,
                triggers=triggers,
            )
            return (
                f"✅ Skill Başarıyla oluşturuldu: `{result['skill_id']}`\n"
                f"   yol: {self.sm.skills_dir}/{category}/{result['skill_id']}/SKILL.md"
            )
        except Exception as e:
            return f"❌ Oluşturma başarısız oldu: {e}"

    def tool_patch(
        self,
        skill_id: str,
        body: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        triggers: Optional[list[str]] = None,
        name: Optional[str] = None,
        category: str = "workflow",
    ) -> str:
        """Araçlar: Artımlı Güncellemeler Skill(öncelik alır create)"""
        try:
            existed_before = self.sm.get_skill(skill_id) is not None
            result = self.sm.patch(
                skill_id=skill_id,
                body=body,
                description=description,
                tags=tags,
                triggers=triggers,
                name=name,
                category=category,
            )
            action = "yenilemek" if existed_before else "yaratmak"
            return (
                f"✅ Skill {action}: `{result['skill_id']}`\n"
                f"   betimlemek: {result.get('description', '')}"
            )
        except Exception as e:
            return f"❌ İşlem başarısız oldu: {e}"

    def tool_delete(self, skill_id: str) -> str:
        """Araçlar: Sil Skill"""
        ok = self.sm.delete(skill_id)
        if ok:
            return f"✅ Skill silmek: `{skill_id}`"
        return f"⚠️ Skill mevcut değil: `{skill_id}`"

    def tool_search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 10,
    ) -> str:
        """Araçlar: Tam metin araması Skills"""
        results = self.sm.search(
            query=query,
            category=category,
            tags=tags,
            limit=limit,
        )
        if not results:
            return f"(Eşleşen sonuç yok for: {query})"

        lines = [f"**{len(results)} sonuçlar** (for: {query}):\n"]
        for s in results:
            lines.append(
                f"- **{s['skill_id']}** [{s.get('category', '')}] "
                f"{s.get('description', '')}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # yaşam döngüsü yöntemleri
    # ------------------------------------------------------------------

    async def _run(
        self,
        context: AgentContext,
        prompt: list[dict[str, str]],
        **kwargs,
    ) -> str:
        """
        uygulamak Skill Yönetim görevleri

        itibaren prompt Son kullanıcı mesajı ayrıştırma aracı çağrı isteği,
        İlgili işlemleri yürütün tool_* Yöntem, sonucu döndürür.
        """
        # Son kullanıcı mesajını çıkart
        user_msg = ""
        for msg in reversed(prompt):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        # Ayrıştırma aracı çağrısı
        action = self._parse_action(user_msg)
        params = self._parse_params(user_msg)

        # İlgili aracı çalıştırın
        if action == "list":
            return self.tool_list(**params)
        if action == "view":
            return self.tool_view(**params)
        if action == "create":
            return self.tool_create(**params)
        if action == "patch":
            return self.tool_patch(**params)
        if action == "delete":
            return self.tool_delete(**params)
        if action == "search":
            return self.tool_search(**params)
        # Varsayılan: tümünü listele + Önerileri ara
        return self.tool_list() + "\n\n💡 İpucu: Kullanın search <anahtar kelimeler> Zaten ara Skill"

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Skill güncellendi/Oluştur, diğer Agent Geçilebilir skill_manage Araç sorgusu",
            ],
        )

    # ------------------------------------------------------------------
    # Yardımcı: basit amaç tanıma (model gerekmez, doğrudan kurallar)
    # ------------------------------------------------------------------

    def _parse_action(self, text: str) -> str:
        """Metinden işlem türünü tanımlayın"""
        text_lower = text.lower()
        if "aramak" in text or "search" in text_lower:
            return "search"
        if "liste" in text or "list" in text_lower or "Tüm beceriler" in text:
            return "list"
        if "Kontrol etmek" in text or "view" in text_lower or "Detaylar" in text:
            return "view"
        if "yenilemek" in text or "patch" in text_lower or "Tekrar düzeltme yapmak" in text:
            return "patch"
        if "yaratmak" in text or "create" in text_lower or "Yeni" in text:
            return "create"
        if "silmek" in text or "delete" in text_lower:
            return "delete"
        return ""

    def _parse_params(self, text: str) -> dict[str, Any]:
        """Parametreleri metinden ayrıştırma (kolay sürüm)"""
        params: dict[str, Any] = {}

        # category
        for cat in SkillManager.CATEGORIES:
            if cat in text:
                params["category"] = cat
                break

        # skill_id
        import re

        id_match = re.search(r"`([^`]+)`", text)
        if id_match:
            params["skill_id"] = id_match.group(1)

        return params
