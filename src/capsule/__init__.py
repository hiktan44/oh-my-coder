"""
Capsule - GEP protokolyetenekpaketsistem

uygula EvoMap GEP protokolsayigoreyapivekayittablo, destekyetenekkayit, kesfetvekarsi. 
"""

from .capsule import Capsule as Capsule
from .gene import Gene as Gene
from .registry import GEPRegistry as GEPRegistry

__all__ = ["Capsule", "GEPRegistry", "Gene"]
