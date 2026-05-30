"""bagimlilikayristir - olusturkodicindeotomatikalgilamavekurulumbagimlilik"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

# sikkullanmodulisimkadar pip paketisimesle
MODULE_TO_PACKAGE: dict[str, str] = {
    # sikgorinciucyonkutuphane
    "requests": "requests",
    "urllib": "urllib3",
    "urllib3": "urllib3",
    "bs4": "beautifulsoup4",
    "beautifulsoup4": "beautifulsoup4",
    "PIL": "Pillow",
    "pillow": "Pillow",
    "numpy": "numpy",
    "np": "numpy",
    "pandas": "pandas",
    "pd": "pandas",
    "matplotlib": "matplotlib",
    "plt": "matplotlib",
    "seaborn": "seaborn",
    "sklearn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "tensorflow": "tensorflow",
    "tf": "tensorflow",
    "torch": "torch",
    "keras": "keras",
    "openai": "openai",
    "anthropic": "anthropic",
    "yaml": "pyyaml",
    "jsonschema": "jsonschema",
    "pydantic": "pydantic",
    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",
    "sqlalchemy": "sqlalchemy",
    "psycopg2": "psycopg2-binary",
    "pymongo": "pymongo",
    "redis": "redis",
    "celery": "celery",
    "aiohttp": "aiohttp",
    "httpx": "httpx",
    "tqdm": "tqdm",
    "dotenv": "python-dotenv",
    "pytest": "pytest",
    "cryptography": "cryptography",
    "python-jose": "python-jose[cryptography]",
    "passlib": "passlib",
    "alembic": "alembic",
    "click": "click",
    "typer": "typer",
    "rich": "rich",
    "toml": "toml",
    "tomli": "tomli",
    "black": "black",
    "ruff": "ruff",
    "mypy": "mypy",
    "isort": "isort",
    # sayigoreisle
    "cv2": "opencv-python",
    "opencv-python": "opencv-python",
    "torchvision": "torchvision",
    "transformers": "transformers",
    "diffusers": "diffusers",
    "accelerate": "accelerate",
    "peft": "peft",
    "trl": "trl",
    # icindemetinisle
    "jieba": "jieba",
    "pkuseg": "pkuseg",
    "hanlp": "hanlp",
    # Agent iskelet
    "langchain": "langchain",
    "langchain_core": "langchain-core",
    "langchain_community": "langchain-community",
    "langchain_openai": "langchain-openai",
    "autogen": "pyautogen",
    "crewai": "crewai",
    # onunosikkullan
    "tiktoken": "tiktoken",
    "aiofiles": "aiofiles",
    "websockets": "websockets",
    "python-multipart": "python-multipart",
}


@dataclass
class DependencyInfo:
    """bagimlilikbilgi"""

    module_name: str  # import X icinde X
    package_name: str  # karsilik gelen pip paketisim
    is_standard_lib: bool = False  # olup olmadigidirstandartkutuphane


@dataclass
class ResolutionResult:
    """bagimlilikayristirsonuc"""

    needed: list[DependencyInfo] = field(default_factory=list)
    missing: list[DependencyInfo] = field(default_factory=list)
    installed: list[DependencyInfo] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (package, error)


class DependencyResolver:
    """bagimlilikayristir"""

    # Python standartkutuphanemodul (hayirgerekisterkurulum) 
    STANDARD_LIBS = {
        "os",
        "sys",
        "re",
        "json",
        "html",
        "xml",
        "csv",
        "io",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "operator",
        "math",
        "random",
        "statistics",
        "logging",
        "warnings",
        "threading",
        "multiprocessing",
        "asyncio",
        "concurrent",
        "subprocess",
        "queue",
        "socket",
        "ssl",
        "base64",
        "hashlib",
        "hmac",
        "secrets",
        "platform",
        "locale",
        "argparse",
        "getopt",
        "configparser",
        "optparse",
        "shutil",
        "tempfile",
        "pathlib",
        "glob",
        "fnmatch",
        "linecache",
        "tokenize",
        "keyword",
        "ast",
        "dis",
        "types",
        "copy",
        "pickle",
        "marshal",
        "gc",
        "weakref",
        "typing",
        "abc",
        "contextlib",
        "dataclasses",
        "enum",
        "graphlib",
        "pprint",
        "textwrap",
        "unicodedata",
        "string",
        "struct",
        "codecs",
        "encoding",
        "formatter",
        "atexit",
        "traceback",
        "sysconfig",
        "builtins",
        "__future__",
    }

    # sikgorstandartkutuphanealtmodul (gerekistertekiltekisle) 
    STANDARD_LIB_SUBMODULES = {
        "urllib.parse",
        "urllib.request",
        "urllib.error",
        "urllib.response",
        "http.server",
        "http.client",
        "http.cookies",
        "http.cookiejar",
        "xml.etree",
        "xml.dom",
        "xml.sax",
        "html.parser",
        "collections.abc",
        "concurrent.futures",
        "configparser",
        "dataclasses",
        "contextlib",
        "typing",
        "tkinter",
    }

    def __init__(self):
        self._package_cache: dict[
            str, bool | None
        ] = {}  # package_name -> True/False/None

    def extract_from_code(self, code: str) -> list[DependencyInfo]:
        """kodkarakter dizisiicindecikarbagimlilik"""
        dependencies: list[DependencyInfo] = []
        seen: set[str] = set()

        # regexeslestir import dilcumle
        # eslestir: import x, import x as y, from x import y, from x import y as z
        patterns = [
            r"^from\s+([a-zA-Z_][a-zA-Z0-9_.]*)",
            r"^import\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        ]

        for line in code.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    module = match.group(1)
                    # githaric as sonrayuzayriisim
                    if " as " in module:
                        module = module.split(" as ")[0]

                    # sadecealustkatmanmodulisim
                    root_module = module.split(".")[0]

                    if root_module and root_module not in seen:
                        seen.add(root_module)
                        pkg = self._map_to_package(root_module)
                        is_std = self._is_standard_lib(root_module)
                        dependencies.append(
                            DependencyInfo(
                                module_name=root_module,
                                package_name=pkg,
                                is_standard_lib=is_std,
                            )
                        )
                    break

        return dependencies

    def _map_to_package(self, module_name: str) -> str:
        """modulisimeslekadar pip paketisim"""
        return MODULE_TO_PACKAGE.get(module_name, module_name)

    def _is_standard_lib(self, module_name: str) -> bool:
        """kontrololup olmadigidirstandartkutuphane"""
        # dogrubaglankontrol
        if module_name in self.STANDARD_LIBS:
            return True

        # kontrololup olmadigidirstandartkutuphanealtmodul
        for submod in self.STANDARD_LIB_SUBMODULES:
            if module_name.startswith(submod.split(".")[0]):
                return True

        return False

    def check_installed(self, package_name: str) -> bool:
        """kontrolpaketolup olmadigikurulum"""
        if package_name in self._package_cache:
            return self._package_cache[package_name] is True

        try:
            result = subprocess.run(
                ["pip", "show", package_name],
                capture_output=True,
                timeout=10,
            )
            installed = result.returncode == 0
            self._package_cache[package_name] = installed
            return installed
        except Exception:
            self._package_cache[package_name] = False
            return False

    def check_dependencies(
        self, dependencies: list[DependencyInfo]
    ) -> ResolutionResult:
        """kontrolbagimlilikolup olmadigikurulum"""
        result = ResolutionResult()

        for dep in dependencies:
            if dep.is_standard_lib:
                continue

            result.needed.append(dep)

            if self.check_installed(dep.package_name):
                result.installed.append(dep)
            else:
                result.missing.append(dep)

        return result

    def install_missing(
        self, missing: list[DependencyInfo], quiet: bool = True
    ) -> ResolutionResult:
        """kurulumeksikbagimlilik"""
        result = ResolutionResult()
        result.missing = missing

        for dep in missing:
            try:
                cmd = ["pip", "install", dep.package_name]
                if quiet:
                    cmd.append("-q")

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=120,
                )

                if proc.returncode == 0:
                    result.installed.append(dep)
                    self._package_cache[dep.package_name] = True
                else:
                    error = proc.stderr.decode("utf-8", errors="replace")
                    result.failed.append((dep.package_name, error))
            except subprocess.TimeoutExpired:
                result.failed.append((dep.package_name, "Installation timeout"))
            except Exception as e:
                result.failed.append((dep.package_name, str(e)))

        # guncelle missing liste
        result.needed = missing
        result.missing = [d for d in missing if d not in result.installed]

        return result

    def resolve(self, code: str, auto_install: bool = True) -> ResolutionResult:
        """ayristirkodbagimlilikveolabilirseckurulum"""
        # cikarbagimlilik
        deps = self.extract_from_code(code)

        # kontrolhangilerieksik
        result = self.check_dependencies(deps)

        # kurulumeksik
        if auto_install and result.missing:
            install_result = self.install_missing(result.missing)
            result.installed.extend(install_result.installed)
            result.failed.extend(install_result.failed)
            result.missing = install_result.missing

        return result


# globalornek
_default_resolver: Optional[DependencyResolver] = None


def get_resolver() -> DependencyResolver:
    """alvarsayilanayristir"""
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = DependencyResolver()
    return _default_resolver


def resolve_dependencies(code: str, auto_install: bool = True) -> ResolutionResult:
    """kolayfaydafonksiyon: ayristirkodbagimlilik"""
    return get_resolver().resolve(code, auto_install)
