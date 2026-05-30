# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""
projedosyaistatistikmodul. 

saglardosyadolas, puansinifistatistik, harir tutkuralvb.islev. 
"""

from .counter import count_files
from .models import FileStats, StatsResult

__all__ = [
    "count_files",
    "FileStats",
    "StatsResult",
]
