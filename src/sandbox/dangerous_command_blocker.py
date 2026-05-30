from __future__ import annotations

from typing import Optional

"""
tehlikelikomutengelle - Dangerous Command Blocker

temelde Claude Code Auto Mode riskpuansinifmantikuygula. 
icindekomutyurutonceilerlesatircokboyutdereceguvenlikkontrol, engelleyuksektehlikeislem. 

riskvb.seviye: 
- BLOCK: dogrubaglanreddetyurut
- WARN: uyariancakizin veryurut
- ALLOW: sikkoysatir

beyazisimtekilmod (varsayilanbaslatkullan) : 
- sadecevarbeyazisimtekilicinde base command yetenekizin veryurut
- beyazisimtekilkomuthalayapacakgeckaraisimtekilkontrol (derinlikengellesavunma) 
- ayarlaayarortam degiskenmiktar OMC_DISABLE_WHITELIST=1 olabilirgeçicizamankapatbeyazisimtekil (sadeceacgonderortam) 
"""

import os
import re
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """riskvb.seviye"""

    ALLOW = "allow"  # sikkoysatir
    WARN = "warn"  # uyariancakizin ver
    BLOCK = "block"  # dogrubaglanreddet


@dataclass
class BlockReason:
    """engelleasilneden"""

    risk: RiskLevel
    reason: str
    matched_pattern: Optional[str] = None


class BlockedCommandError(Exception):
    """engellekomutfarklisik"""

    def __init__(self, command: str, reason: str, risk: RiskLevel):
        self.command = command
        self.reason = reason
        self.risk = risk
        # maskele: hayirtamkomutyazgirishatamesaj, kacinhassasbilgisizinti
        safe_cmd = _sanitize_for_error(command)
        super().__init__(f"[{risk.value.upper()}] {reason}\nkomut: {safe_cmd}")


def _sanitize_for_error(text: str) -> str:
    """icinhatamesajicindehassasbilgiilerlesatirmaskeleisle"""
    # basittekilmaskele: egerkomutuzunlukdereceasiri 200 karakter, kes
    if len(text) > 200:
        return text[:200] + "...[kes]"
    return text


# =============================================================================
# beyazisimtekilmod - izin veryurut base command
# =============================================================================

# beyazisimtekil: sadecevarbubazi base command izin veryurut
# ayarlaayarortam degiskenmiktar OMC_DISABLE_WHITELIST=1 olabilirgeçicizamanyasakkullan (sadeceacgonderortam) 
ALLOWED_BASE_COMMANDS: set[str] = {
    # ── dosyaoku ──
    "ls", "cat", "grep", "find", "head", "tail",
    "wc", "sort", "uniq", "file", "stat", "tree", "du",
    # ── dosyaislem (tehlikeliislemtarafindankaraisimtekiluzerine yaz) ──
    "mkdir", "touch", "cp", "mv", "rm", "rmdir",
    "chmod", "chown", "ln",
    # ── cozbas/geribelgeoku ──
    "tar", "unzip", "gunzip", "bunzip2",
    # ── Python ──
    "python3", "python", "pip", "pip3", "pytest",
    # ── Git ──
    "git",
    # ── Node.js ──
    "node", "npm", "npx",
    # ── C/C++ ──
    "gcc", "g++", "make", "cmake",
    # ── Go ──
    "go",
    # ── Rust ──
    "rustc", "cargo",
    # ── Java ──
    "java", "javac",
    # ── metinisle ──
    "sed", "awk", "tr", "cut", "paste",
    # ── Shell icindeolustur/sikkullan ──
    "echo", "printf", "pwd", "whoami", "date", "hostname",
    "uname", "basename", "dirname", "true", "false", "sleep",
    # ── altyukle (alsinir) ──
    "curl", "wget",
    # ── ilerlesurecgoruntule ──
    "ps", "top",
    # ── agtanikes ──
    "ping", "netstat", "ss",
    # ── ortambilgi ──
    "env", "which", "whereis",
    # ── kapasite / orkestrasyon (tehlikeliislemtarafindankaraisimtekiluzerine yaz) ──
    "docker", "docker-compose", "podman", "kubectl", "helm",
    # ── paketyonet / sistemyonet (tehlikeliislemtarafindankaraisimtekiluzerine yaz) ──
    "sudo", "apt-get", "yum", "dnf", "brew", "pacman",
    # ── veritabani CLI (tehlikeliislemtarafindankaraisimtekiluzerine yaz) ──
    "mysql", "psql", "sqlite3",
}


# gerekistertamyoleslestir base command (engellekar realizkullan PATH etrafinda) 
# ornekornegin: /usr/bin/rm ayricayapacak extract_base_command cikaricin rm, yokgerekkotadisindaisle


def is_whitelist_enabled() -> bool:
    """beyazisimtekilmodolup olmadigibaslatkullan (olabiliraraciligiylaortam degiskenmiktaryasakkullan) """
    return os.environ.get("OMC_DISABLE_WHITELIST", "0") != "1"


def extract_base_command(command: str) -> str:
    """
    tamkomuticindecikar base command (gityol, git flags onceek) 

    ornek: 
        "python3 script.py" → "python3"
        "/usr/bin/python3 -c 'print(1)'" → "python3"
        "git log --oneline" → "git"
        "PYTHONPATH=/foo python3 -c '...'" → "python3" (atlaortam degiskenmiktaronceek) 
        "sudo python3 script.py" → "sudo" (sudo gerekistertekiltekisle) 
    """
    import shlex

    normalized = " ".join(command.split())

    # kaldirortam degiskenmiktaronceek (KEY=VALUE cmd ...) 
    # islecokortam degiskenmiktaronceekdurum
    while re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S+\s+", normalized):
        normalized = re.sub(r"^[A-Za-z_][A-Za-z0-9_]*=\S+\s+", "", normalized, count=1)

    # kaldir sudo / doas vb.yetki yukseltmeonceek (bubazihayirolmalisu anicindesandboxicinde) 
    tokens = shlex.split(normalized)
    if not tokens:
        return ""

    first = tokens[0]

    # kaldiryolonceek
    base = first.rsplit("/", 1)[-1]

    return base


# =============================================================================
# tehlikelimodtanim (regex + anahtar kelime) 
# referans Claude Code Auto Mode riskpuansinif
# =============================================================================

# P0 - asiriyuksektehlike: dogrubaglansilsistemdosya, kirkotuislem
CRITICAL_PATTERNS: list[tuple[str, str]] = [
    # rekursifsilkokdizin
    (r"rm\s+-rf\s+/(?:\s|$|&&|;|\|)", "rekursifsilkokdizin, yapacaktemizlebostamsistem"),
    (r"rm\s+-rf\s+/\*", "rekursifsilkokdizinvardosya"),
    (r"rm\s+-rf\s+\.", "rekursifsilmevcutdizinveonunvaraltdizin"),
    # formatdisk
    (r"dd\s+if=.*\s+of=/dev/", "dogrubaglanyazgirisdiskayarlahazirla, olabiliredebilirneden olursayigorekayip"),
    (r"mkfs", "formatdosyasistem"),
    (r"mke2fs", "olustur ext2/3/4 dosyasistem"),
    # tehlikelitekrarayarlayonuzerine yazsistemdosya
    (r">\s*/etc/", "deneuzerine yazsistemyapilandirma dosyasi"),
    (r">\s*/usr/", "deneuzerine yazsistemdizin"),
    (r">\s*/bin/", "deneuzerine yazsistemikiilerleyapdosya"),
    # Fork bomb (fork mermisi) 
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;:", "Fork Bomb - yapacaktukettumsistemkaynak"),
    (r"fork\(\)\s*;\s*fork\(\)", "icice fork cagri - olabiliredebilirneden olurkaynaktukettum"),
    # sil SSH gizlianahtar
    (r"rm\s+-rf\s+.*\.ssh", "sil SSH gizlianahtardizin"),
    # yasakkullanguvenlik duvari
    (r"iptables\s+-F", "temizlebos iptables kural"),
    (r"ufw\s+disable", "yasakkullan UFW guvenlik duvari"),
    # Wipe disk
    (r"shred\s+-f", "parçaladosya"),
    # tehlikeliagaltyukleyurut
    (r"(curl|wget).*\|.*(bash|sh)", "altyuklevedogrubaglanyurutayak (Pipe to Bash) "),
    (r"bash\s+<\(", "Process Substitution yurutuzaksurecayak"),
    (r"curl.*>.*&&.*bash", "altyukleayaksonrayurut"),
    (r"wget.*>.*&&.*bash", "altyukleayaksonrayurut"),
    # degistir /etc/hosts
    (r"echo.*>>\s*/etc/hosts", "degistir hosts dosya"),
    # ekleolabilirsupheli cron
    (r"crontab\s+-r", "silkullanici crontab"),
    # olabilirsupheli Python yurut
    (r"python.*exec", "dinamikkodyurut"),
    # tehlikeli sudo
    (r"chmod\s+777\s+/etc/sudoers", "degistir sudoers izin"),
    (r"sudo\s+su\s+-", "yetki yukseltmekadar root hizlihizliyontem"),
]

# P1 - yuksektehlike: olabiliredebiliryapolsayigorekayipancakvarbirayarlabirlestirakil
HIGH_RISK_PATTERNS: list[tuple[str, str]] = [
    # buyukaraliksil
    (r"rm\s+-rf\s+/tmp", "rekursifsil /tmp dizin"),
    (r"rm\s+-rf\s+/var/log", "rekursifsillogdizin"),
    (r"rm\s+-rf\s+/home", "rekursifsilkullanicidizin"),
    (r"rm\s+-rf\s+/opt", "rekursifsilolabilirsecyumusakogredizin"),
    # zorunlusil
    (r"rm\s+-f\s+/\S+", "zorunlusildosya"),
    # chmod 777
    (r"chmod\s+777", "ayarlaayarenbuyukizin 777"),
    (r"chmod\s+-R\s+777", "rekursifayarlaayar 777 izin"),
    (r"chmod\s+0", "kaldirvarizin"),
    # uzerine yazdosya
    (r">\s*~/.bashrc", "uzerine yaz shell yapilandirma dosyasi"),
    (r">\s*~/.zshrc", "uzerine yaz shell yapilandirma dosyasi"),
    # killall zorunlusonlandir
    (r"killall\s+-9", "zorunlusonlandirvarilerlesurec"),
    (r"kill\s+-9\s+-1", "sonlandirvarilerlesurec"),
    # agucagizislem
    (r"nc\s+-l\s+-p", "icindeucagizustdinlebaglabaglan"),
    (r"nc\s+-e", "yurutuzaksureckomut"),
    # Docker tehlikeliislem
    (r"docker\s+run\s+--privileged", "ayricalikmodsatirkapasite"),
    (r"docker\s+exec\s+--privileged", "ayricalikmodilerlegiriskapasite"),
    (r"docker\s+rm\s+-f\s+\$\(", "silvarkapasite"),
]

# P2 - icindetehlike: gerekisteronaylaislem
MEDIUM_RISK_PATTERNS: list[tuple[str, str]] = [
    # sistemyapilandirmadegistir
    (r"systemctl\s+stop", "durdursistemservis"),
    (r"service\s+stop", "durdursistemservis"),
    # veritabaniislem
    (r"mysql.*DROP\s+DATABASE", "sil MySQL veritabani"),
    (r"psql.*DROP\s+DATABASE", "sil PostgreSQL veritabani"),
    (r"redis-cli\s+FLUSHALL", "temizlebos Redis varsayigore"),
    # Git tehlikeliislem
    (r"git\s+push\s+--force", "zorunluitgonderkadaruzaksurec"),
    (r"git\s+push\s+-f", "zorunluitgonderkadaruzaksurec"),
    # agislem
    (r"curl\s+-X\s+DELETE", "gondergonder DELETE istek"),
    (r"wget\s+-r\s+-np", "rekursifaltyukleagsite"),
]

# gerekisteruyariancakizin verislem
WARN_PATTERNS: list[tuple[str, str]] = [
    # kirkotu Git islem
    (r"git\s+reset\s+--hard", "serttekrarayar Git isbolge"),
    (r"git\s+clean\s+-fd", "temizlehenuzizleizledosya"),
    # globalpaketkurulum
    (r"npm\s+install\s+-g", "globalkurulum npm paket"),
    (r"pip\s+install\s+--user", "kullaniciseviyekurulum pip paket"),
]


# =============================================================================
# anaengelle
# =============================================================================


class DangerousCommandBlocker:
    """
    tehlikelikomutengelle

    icindekomutyurutonceilerlesatircokboyutdereceguvenlikkontrol. 

    kullanornek: 
        blocker = DangerousCommandBlocker()
        result = blocker.check("rm -rf /tmp/test")
        if result.risk == RiskLevel.BLOCK:
            raise BlockedCommandError("rm -rf /tmp/test", result.reason, result.risk)
    """

    def __init__(self) -> None:
        self._critical_re = [
            (re.compile(p, re.IGNORECASE), msg) for p, msg in CRITICAL_PATTERNS
        ]
        self._high_re = [
            (re.compile(p, re.IGNORECASE), msg) for p, msg in HIGH_RISK_PATTERNS
        ]
        self._medium_re = [
            (re.compile(p, re.IGNORECASE), msg) for p, msg in MEDIUM_RISK_PATTERNS
        ]
        self._warn_re = [
            (re.compile(p, re.IGNORECASE), msg) for p, msg in WARN_PATTERNS
        ]

    def check(self, command: str) -> BlockReason:
        """
        kontrolkomutolup olmadigitehlikeli

        Args:
            command: beklekontrolkomutkarakter dizisi

        Returns:
            BlockReason: icerirriskvb.seviyeveasilnedenkontrolsonuc
        """
        if not command or not command.strip():
            return BlockReason(RiskLevel.ALLOW, "")

        # githariccokkalanbosbeyaz, normkomut
        normalized = " ".join(command.split())

        # ── beyazisimtekilkontrol (enyuksekoncelikseviye, icindekaraisimtekilonce) ──
        if is_whitelist_enabled():
            base_cmd = extract_base_command(command)
            if base_cmd and base_cmd not in ALLOWED_BASE_COMMANDS:
                return BlockReason(
                    risk=RiskLevel.BLOCK,
                    reason=f"base command '{base_cmd}' hayiricindebeyazisimtekilicinde, yasakduryurut",
                    matched_pattern=None,
                )

        # incibironcelikseviye: kontrolasiriyuksektehlikemod (dogrubaglanreddet) 
        for pattern, msg in self._critical_re:
            if pattern.search(normalized):
                return BlockReason(
                    risk=RiskLevel.BLOCK,
                    reason=msg,
                    matched_pattern=pattern.pattern,
                )

        # inciikioncelikseviye: kontrolyuksektehlikemod (dogrubaglanreddet) 
        for pattern, msg in self._high_re:
            if pattern.search(normalized):
                return BlockReason(
                    risk=RiskLevel.BLOCK,
                    reason=msg,
                    matched_pattern=pattern.pattern,
                )

        # inciuconcelikseviye: kontrolicindetehlikemod (uyari) 
        for pattern, msg in self._medium_re:
            if pattern.search(normalized):
                return BlockReason(
                    risk=RiskLevel.WARN,
                    reason=msg,
                    matched_pattern=pattern.pattern,
                )

        # incidortoncelikseviye: kontroluyarimod (sadeceuyari) 
        for pattern, msg in self._warn_re:
            if pattern.search(normalized):
                return BlockReason(
                    risk=RiskLevel.WARN,
                    reason=msg,
                    matched_pattern=pattern.pattern,
                )

        return BlockReason(RiskLevel.ALLOW, "")

    def validate(self, command: str, strict: bool = True) -> None:
        """
        dogrulamakomut, tehlikelizamanfirlatfarklisik

        Args:
            command: beklekontrolkomut
            strict: True=BLOCK/WARN tumfirlatfarklisik, False=sadece BLOCK firlatfarklisik

        Raises:
            BlockedCommandError: komutengellezamanfirlat
        """
        result = self.check(command)

        if result.risk == RiskLevel.BLOCK:
            raise BlockedCommandError(command, result.reason, result.risk)

        if strict and result.risk == RiskLevel.WARN:
            raise BlockedCommandError(command, result.reason, result.risk)


# =============================================================================
# globaltekilornek
# =============================================================================

_default_blocker: Optional[DangerousCommandBlocker] = None


def get_blocker() -> DangerousCommandBlocker:
    """alglobalengelletekilornek"""
    global _default_blocker
    if _default_blocker is None:
        _default_blocker = DangerousCommandBlocker()
    return _default_blocker


def check_command(command: str) -> BlockReason:
    """hizlihizlifonksiyon: kontrolkomut"""
    return get_blocker().check(command)


def validate_command(command: str, strict: bool = True) -> None:
    """hizlihizlifonksiyon: dogrulamakomut"""
    return get_blocker().validate(command, strict=strict)
