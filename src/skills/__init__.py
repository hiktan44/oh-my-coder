"""Skills sistem - eklenti Skill iskelet

destekicindeayar Skill vekullaniciozel Skill (~/.omc/skills/) . 
"""

from .registry import Skill, SkillRegistry, SkillResult, get_registry

__all__ = ["SkillRegistry", "Skill", "SkillResult", "get_registry"]
