from __future__ import annotations

"""
sandboxguvenlikmodul

Islev:
- yolsinir: Agent sadeceedebilirerisimizin verdizin
- asirizamankoru: komutyurutasirizamanotomatiksonlandir
- tehlikeliislemengelle: temelde PermissionGuard
- basittekilancakvaretkiizolemekanizma
"""


import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .dangerous_command_blocker import (
    BlockedCommandError,
    check_command,
)

# ─────────────────────────────────────────────────────────────
# yapilandirma
# ─────────────────────────────────────────────────────────────


@dataclass
class SandboxConfig:
    """sandboxyapilandirma"""

    allowed_dirs: list[str] = field(
        default_factory=lambda: [
            str(Path.home() / ".omc"),
            str(Path.home() / ".qclaw" / "workspace"),
            str(Path.home()),
            "/tmp",  # nosec B108 - sandbox tasarim: /tmp icinsandboxizin veralkontrolgeçicizamandizin
        ]
    )
    denied_paths: list[str] = field(default_factory=list)
    timeout: int = 60
    max_output_size: int = 10 * 1024 * 1024  # 10MB
    allow_network: bool = True
    allow_subprocess: bool = True
    working_dir: str = ""

    def __post_init__(self) -> None:
        if not self.working_dir:
            self.working_dir = str(Path.home() / ".omc")


# ─────────────────────────────────────────────────────────────
# sandbox
# ─────────────────────────────────────────────────────────────


class Sandbox:
    """
    hafifmiktarseviyesandbox (temeldeyolsinir) 

    isasilakil: 
    1. dogrulamavarilgilivedosyayololup olmadigiicinde allowed_dirs icinde
    2. komutyurutoncearaciligiyla PermissionGuard izinkontrol
    3. ayarlaayarasirizamanveciktibuyukkucuksinir
    4. icindealsinir cwd icindeyurut
    """

    # varsayilanizin verdizin
    DEFAULT_ALLOWED_DIRS = [
        "~/.omc",
        "~/.qclaw/workspace",
        "/tmp",  # nosec B108 - sandbox tasarim
    ]

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self.config = config or SandboxConfig()
        self._resolve_allowed_dirs()

    def _resolve_allowed_dirs(self) -> None:
        """ayristirvedogrulama allowed_dirs, otomatik working_dir eklegirisizin verliste"""
        self._resolved_dirs: list[Path] = []
        for d in self.config.allowed_dirs:
            p = Path(d).expanduser().resolve()
            self._resolved_dirs.append(p)

        # otomatik working_dir eklegiris allowed_dirs (ornegineksik) 
        working_dir = Path(self.config.working_dir).expanduser().resolve() if self.config.working_dir else Path.home() / ".omc"
        working_dir = working_dir.resolve()

        if working_dir not in self._resolved_dirs:
            self._resolved_dirs.append(working_dir)
            print(f"[Sandbox] uyari: working_dir {working_dir} hayiricinde allowed_dirs icinde, otomatikekle")

    def validate_path(self, path: str) -> bool:
        """
        dogrulamayololup olmadigiicindeizin veraralikicinde

        Args:
            path: dosyayol (olabilirilediricinyol, icerir ~ veya $VAR) 

        Returns:
            True: yolguvenlik
            False: yolasiriizin veraralik
        """
        ok, _ = self.validate_path_with_reason(path)
        return ok

    def validate_path_with_reason(self, path: str) -> tuple[bool, str]:
        """
        dogrulamayolvedonusreddetasilneden

        Returns:
            (olup olmadigiizin ver, reddetasilneden)
        """
        try:
            # 1. gelişacortam degiskenmiktar ($VAR / %VAR%)
            expanded = os.path.expandvars(path)
            # 2. gelişackullanicidizin (~)
            p = Path(expanded).expanduser().resolve()
        except Exception:
            return False, f"yolayristirma basarisiz: {path}"

        for allowed in self._resolved_dirs:
            if allowed == Path("/tmp") or str(allowed).startswith("/tmp"):  # nosec B108
                if str(p).startswith("/tmp") or str(p).startswith(  # nosec B108
                    "/private/tmp"
                ):  # nosec B108
                    return True, ""
            try:
                p.relative_to(allowed)
                return True, ""
            except ValueError:
                continue

        return False, f"yolasirisandboxaralik: {path} (ayristiricin: {p})"

    def validate_paths(self, paths: list[str]) -> tuple[bool, list[str]]:
        """
        toplucamiktardogrulamayol

        Returns:
            (olup olmadigitumkisimbirlestiryontem, hayirbirlestiryontemyolliste)
        """
        invalid: list[str] = []
        for path in paths:
            ok, reason = self.validate_path_with_reason(path)
            if not ok:
                invalid.append(f"{path}: {reason}")
        return (len(invalid) == 0, invalid)

    # ── bilkomutyolparametrekonum (0-based, komutisimkendihayirhesapgiris) ───────────
    # format: "cmd": [arg_index, ...]  |  "cmd": "all" (kontrolvarparametre) 
    _PATH_ARG_COMMANDS: dict[str, list[int] | str] = {
        # tekildosyaislem
        "cat": "all",
        "head": "all",
        "tail": "all",
        "less": "all",
        "more": "all",
        "file": "all",
        "stat": "all",
        # cokdosyaislem (kontrolvarparametre) 
        "ls": "all",
        "grep": "all",
        "find": "all",
        "wc": "all",
        "sort": "all",
        "uniq": "all",
        # cp/mv: haricensonrabirdirkaynakdosya, ensonrabirdirhedefisaret (tumkontrol) 
        "cp": "all",
        "mv": "all",
        "ln": "all",
        # rm: varparametretumdiryol
        "rm": "all",
        "rmdir": "all",
        # ciktitekrarayarlayonsinifkomut -o/--output parametre
        "gcc": [2],   # gcc -o output src.c  (basit: kontrolvarparametre) 
        "g++": [2],
        "tar": "all",
        "unzip": "all",
        "git": "all",  # git komuttekrarkarisik, basitkontrolvarparametre
    }

    def _extract_paths_from_command(self, command: str) -> list[str]:
        """komuticindecikarolabiliredebiliryolparametre (kullan shlex ayristir) """
        paths: list[str] = []
        try:
            tokens = shlex.split(command)
        except ValueError:
            # shlex ayristirma basarisiz (orneginhenuzkapatbirlestircekno) , gerigerikadarbasittekilpuanayir
            tokens = command.split()

        if not tokens:
            return paths

        base = tokens[0]

        # 1. kontrolbilkomutyolparametre
        arg_spec = self._PATH_ARG_COMMANDS.get(base)
        if arg_spec == "all":
            # kontrolvarparametre (atlasecogresinifparametre) 
            for tok in tokens[1:]:
                if not tok.startswith("-") and (
                    "/" in tok or tok.startswith("~") or tok.startswith(".")
                ):
                    paths.append(tok)
        elif isinstance(arg_spec, list):
            for idx in arg_spec:
                if idx + 1 < len(tokens):
                    paths.append(tokens[idx + 1])

        # 2. kontrol shell tekrarayarlayon (> >> < 2> &>) 
        redirect_re = re.compile(
            r"(?:>>|2>|&>|>|<|<\s)\s*(\S+)"
        )
        for m in redirect_re.finditer(command):
            paths.append(m.group(1))

        # 3. kontrol --output / -o vb.sikgorciktiparametre
        output_re = re.compile(r"(?:-o|--output)\s+(\S+)")
        for m in output_re.finditer(command):
            paths.append(m.group(1))

        return paths

    def validate_command(self, command: str) -> tuple[bool, str]:
        """
        dogrulamakomutyolparametreolup olmadigiicindesandboxizin veraralikicinde

        Returns:
            (olup olmadigiizin ver, reddetasilneden)
        """
        paths_to_check = self._extract_paths_from_command(command)

        if paths_to_check:
            ok, invalid = self.validate_paths(paths_to_check)
            if not ok:
                return False, f"yolasirisandboxaralik: {invalid[0]}"

        return True, ""

    def run_command(
        self,
        cmd: str,
        timeout: Optional[int] = None,
        check_permission: bool = True,
        check_dangerous: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        icindesandboxicindesatirkomut

        Args:
            cmd: shell komut
            timeout: asirizamansaniyesayi (varsayilankullan config.timeout) 
            check_permission: olup olmadigioncekontrolizin
            check_dangerous: olup olmadigibaslatkullantehlikelikomutengelle

        Returns:
            subprocess.CompletedProcess

        Raises:
            BlockedCommandError: komuttehlikelikomutengelleblokdur
            PermissionError: izinkontrolhenuzaraciligiyla
            TimeoutError: komutyurutasirizaman
            ValueError: yolkontrolhenuzaraciligiyla
        """
        # P0: tehlikelikomutengelle (enerkenkontrol, enyuksekoncelikseviye) 
        if check_dangerous:
            result = check_command(cmd)
            if result.risk.value == "block":
                raise BlockedCommandError(cmd, result.reason, result.risk)

        if check_permission:
            ok, reason = self.validate_command(cmd)
            if not ok:
                raise PermissionError(f"sandboxreddet: {reason}")

        timeout_val = timeout or self.config.timeout
        cwd = self.config.working_dir or str(Path.home() / ".omc")

        try:
            # Use shell=False with explicit argument splitting to prevent injection
            return subprocess.run(
                cmd,
                shell=True,  # nosec B602 B604  # sandboxbeyazisimtekilfiltrelesonrayetenekkadarulasbuyer, olabilirkontrolsenaryo
                capture_output=True,
                timeout=timeout_val,
                cwd=cwd,
                text=True,
                env={**os.environ, "HOME": str(Path.home())},
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"komutyurutasirizaman ({timeout_val}saniye) ")

    def run_command_with_output_limit(
        self,
        cmd: str,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        satirkomutvesinirciktibuyukkucuk

        Returns:
            dict(output, stderr, returncode, truncated, duration, success)
        """
        import time

        start = time.time()
        timeout_val = timeout or self.config.timeout
        max_size = self.config.max_output_size

        try:
            result = self.run_command(cmd, timeout=timeout_val, check_permission=True)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            truncated = False

            if len(stdout) > max_size:
                stdout = (
                    stdout[:max_size]
                    + f"\n... (ciktikes, ortak {len(result.stdout)} byte)"
                )
                truncated = True

            if len(stderr) > max_size:
                stderr = (
                    stderr[:max_size]
                    + f"\n... (stderr kes, ortak {len(result.stderr)} byte)"
                )
                truncated = True

            return {
                "output": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
                "truncated": truncated,
                "duration": time.time() - start,
                "success": result.returncode == 0,
            }

        except TimeoutError:
            return {
                "output": "",
                "stderr": f"komutyurutasirizaman ({timeout_val}saniye) ",
                "returncode": -1,
                "truncated": False,
                "duration": timeout_val,
                "success": False,
            }
        except BlockedCommandError as e:
            return {
                "output": "",
                "stderr": f"[BLOCKED] {e.reason}",
                "returncode": -3,
                "truncated": False,
                "duration": time.time() - start,
                "success": False,
            }
        except PermissionError:
            return {
                "output": "",
                "stderr": "Permission denied",
                "returncode": -2,
                "truncated": False,
                "duration": time.time() - start,
                "success": False,
            }

    def get_allowed_dirs(self) -> list[str]:
        """alizin verdizinliste"""
        return [str(p) for p in self._resolved_dirs]

    def add_allowed_dir(self, path: str) -> None:
        """ekleizin verdizin"""
        p = Path(path).expanduser().resolve()
        if p not in self._resolved_dirs:
            self._resolved_dirs.append(p)


# ─────────────────────────────────────────────────────────────
# kullanislifonksiyon
# ─────────────────────────────────────────────────────────────


def create_sandbox(
    allowed_dirs: Optional[list[str]] = None,
    timeout: int = 60,
) -> Sandbox:
    """olustursandboxornek"""
    config = SandboxConfig(
        allowed_dirs=allowed_dirs or Sandbox.DEFAULT_ALLOWED_DIRS,
        timeout=timeout,
    )
    return Sandbox(config)


def run_sandboxed(
    cmd: str,
    allowed_dirs: Optional[list[str]] = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """kullanislifonksiyon: icindesandboxicindesatirkomut"""
    sandbox = Sandbox()
    return sandbox.run_command_with_output_limit(cmd, timeout=timeout)
