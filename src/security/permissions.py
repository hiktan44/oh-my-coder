from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
izinyonetakilmodul

Islev:
- temeldeyapilandirma dosyasikuralizinkontrol
- beyazisimtekil/karaisimtekilregexeslestir
- yuksekriskkomutinceletoplucaengelle
- omc security check <cmd> onkontrolkomut
"""


import contextlib
import re
from dataclasses import dataclass, field
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────
# sayigoremodel
# ─────────────────────────────────────────────────────────────


@dataclass
class PermissionRule:
    """izinkural"""

    allowed_patterns: list[str] = field(default_factory=list)
    denied_patterns: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)
    max_command_length: int = 10000

    def compile_patterns(self) -> None:
        """onduzenleceviriregex (saglaricindekisimcagri) """
        self._allowed_re = [re.compile(p) for p in self.allowed_patterns]
        self._denied_re = [re.compile(p) for p in self.denied_patterns]
        self._approval_re = [re.compile(p) for p in self.require_approval]

    @classmethod
    def from_dict(cls, data: dict[str, list[str]]) -> PermissionRule:
        """ dict olusturkural"""
        return cls(
            allowed_patterns=data.get("allowed_patterns", []),
            denied_patterns=data.get("denied_patterns", []),
            require_approval=data.get("require_approval", []),
            max_command_length=data.get("max_command_length", 10000),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "allowed_patterns": self.allowed_patterns,
            "denied_patterns": self.denied_patterns,
            "require_approval": self.require_approval,
            "max_command_length": self.max_command_length,
        }


@dataclass
class CheckResult:
    """kontrolsonuc"""

    allowed: bool
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None
    requires_approval: bool = False

    def to_tuple(self) -> tuple[bool, Optional[str]]:
        """uyumlueskibaglanagiz"""
        return (self.allowed, self.reason)


# ─────────────────────────────────────────────────────────────
# izinkoruma
# ─────────────────────────────────────────────────────────────


class PermissionGuard:
    """izinkoruma"""

    # icindeayaryuksekriskkomutmod (yaniizinhenuzyapilandirmaayricaengelle) 
    BUILTIN_DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/\s*",
        r"rm\s+-rf\s+/[a-zA-Z]+\s*",
        r":\(\)\{.*:\|.*:.*\}",
        r">\s*/dev/sd[a-z]",
        r"dd\s+if=.*of=/dev/",
        r"mkfs\s+",
        r":(){ :|:& };:",
    ]

    def __init__(self, rules: Optional[PermissionRule] = None) -> None:
        self.rules = rules or PermissionRule()
        self._compiled = False
        self._compile()

    def _compile(self) -> None:
        """duzenleceviriregextabloulastarz (atlayoketkiregex) """
        if self._compiled:
            return

        def safe_compile(patterns: list[str]) -> list[re.Pattern[str]]:
            compiled: list[re.Pattern[str]] = []
            for p in patterns:
                with contextlib.suppress(re.error):
                    compiled.append(re.compile(p, re.IGNORECASE))
            return compiled

        self._allowed_re = safe_compile(self.rules.allowed_patterns)
        self._denied_re = safe_compile(self.rules.denied_patterns)
        self._approval_re = safe_compile(self.rules.require_approval)
        self._builtin_re = [
            re.compile(p, re.IGNORECASE) for p in self.BUILTIN_DANGEROUS_PATTERNS
        ]
        self._compiled = True

    def check(self, command: str) -> CheckResult:
        """
        kontrolkomutolup olmadigiizin veryurut

        Returns:
            CheckResult(allowed, reason, matched_pattern, requires_approval)
        """
        if not command or not command.strip():
            return CheckResult(allowed=False, reason="komuticinbos")

        if len(command) > self.rules.max_command_length:
            return CheckResult(
                allowed=False,
                reason=f"komutuzunlukderece {len(command)} asirisinir {self.rules.max_command_length}",
            )

        # 1. icindeayarkaraisimtekil (enyuksekoncelikseviye) 
        for compiled in self._builtin_re:
            if compiled.search(command):
                return CheckResult(
                    allowed=False,
                    reason="komuteslestiricindeayartehlikelimod",
                    matched_pattern=compiled.pattern,
                )

        # 2. yapilandirma dosyasikaraisimtekil
        for pattern, compiled in zip(self.rules.denied_patterns, self._denied_re):
            if compiled.search(command):
                return CheckResult(
                    allowed=False,
                    reason=f"komuteslestirkaraisimtekil: {pattern}",
                    matched_pattern=pattern,
                )

        # 3. beyazisimtekilmod
        if self._allowed_re:
            for pattern, compiled in zip(self.rules.allowed_patterns, self._allowed_re):
                if compiled.search(command):
                    return CheckResult(allowed=True, reason=f"eslestirbeyazisimtekil: {pattern}")
            return CheckResult(
                allowed=False,
                reason="komuthayiricindebeyazisimtekilicinde",
            )

        return CheckResult(allowed=True, reason=None)

    def needs_approval(self, command: str) -> bool:
        """kontrololup olmadigigerekisterinceletopluca"""
        return any(compiled.search(command) for compiled in self._approval_re)

    def validate_rules(self) -> list[str]:
        """dogrulamakuralbirlestiryontem"""
        errors: list[str] = []

        for pattern in self.rules.allowed_patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"allowed_patterns regexhata '{pattern}': {e}")

        for pattern in self.rules.denied_patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"denied_patterns regexhata '{pattern}': {e}")

        for pattern in self.rules.require_approval:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"require_approval regexhata '{pattern}': {e}")

        return errors

    @classmethod
    def from_agent_config(cls, config: dict[str, Any]) -> PermissionGuard:
        """ Agent yapilandirmasozlukolustur PermissionGuard"""
        perm_data = config.get("permissions", {})
        rules = PermissionRule(
            allowed_patterns=perm_data.get("allowed_patterns", []),
            denied_patterns=perm_data.get("denied_patterns", []),
            require_approval=perm_data.get("require_approval", []),
        )
        return cls(rules)


# ─────────────────────────────────────────────────────────────
# kullanislifonksiyon
# ─────────────────────────────────────────────────────────────


def check_command(command: str, rules: Optional[PermissionRule] = None) -> CheckResult:
    """kontrolkomutizin (kullanislifonksiyon) """
    guard = PermissionGuard(rules)
    return guard.check(command)


def needs_approval(command: str, rules: Optional[PermissionRule] = None) -> bool:
    """kontrolkomutolup olmadigigerekisterinceletopluca (kullanislifonksiyon) """
    guard = PermissionGuard(rules)
    return guard.needs_approval(command)
