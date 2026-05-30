"""
uzunlukdonemhafizasistem

uckatmanmimari: 
1. ShortTermMemory - mevcutyapacakkonusmabaglam (icindekaydet + geçicizamandosya) 
2. LongTermMemory - projeegilimiyi, sikkullanmod (JSON kalici) 
3. LearningsMemory - tuzakkayit, en iyi uygulamalar (Markdown) 

Islev:
- yapacakkonusmabitirotomatiktoplambiriktir
- yeniyapacakkonusmaotomatikcagirgeriilgilihafiza
- manueltetikgonderhafizacagirgeri (ara) 
"""

from .manager import MemoryConfig, MemoryManager

__all__ = [
    "LearningsMemory",
    "LongTermMemory",
    "MemoryConfig",
    "MemoryManager",
    "ShortTermMemory",
]
