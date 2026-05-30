# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

projedosyaistatistikcekirdekmodul. 

saglardosyadolas, puansinifistatistik, harir tutkuralvb.islev. 
"""

import os
from pathlib import Path
from typing import Optional, Union

from .models import FileStats, StatsResult


def _is_excluded(
    path: Path,
    exclude_dirs: set[str],
    exclude_files: set[str],
    exclude_extensions: set[str],
) -> bool:
    """kontrolyololup olmadigiolmaliharir tut. 

    Args:
        path: isterkontrolyol
        exclude_dirs: isterharir tutdizinisimsetbirlestir (hayirbolgepuanbuyukkucukyaz) 
        exclude_files: isterharir tutdosyaisimsetbirlestir (hayirbolgepuanbuyukkucukyaz) 
        exclude_extensions: isterharir tutdosyagenisletisimsetbirlestir (hayirbolgepuanbuyukkucukyaz) 

    Returns:
        egeryololmaliharir tutkuraldonus True
    """
    name_lower = path.name.lower()

    # kontrololup olmadigiicindeharir tutdosyaisimlisteicinde
    if path.is_file() and name_lower in exclude_files:
        return True

    # kontrololup olmadigiicindeharir tutdizinisimlisteicinde
    if path.is_dir() and name_lower in exclude_dirs:
        return True

    # kontroldosyagenisletisim
    if path.is_file():
        ext = path.suffix.lower()
        if ext in exclude_extensions:
            return True

    return False


def _get_file_type(path: Path) -> str:
    """goredosyagenisletisimaldosyatippuansinif. 

    Args:
        path: dosyayol

    Returns:
        dosyatipaciklamakarakter dizisi
    """
    ext = path.suffix.lower()
    type_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript React",
        ".jsx": "JavaScript React",
        ".md": "Markdown",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".less": "LESS",
        ".rs": "Rust",
        ".go": "Go",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".h": "C/C++ Header",
        ".sh": "Shell Script",
        ".bash": "Bash Script",
        ".ps1": "PowerShell",
        ".bat": "Batch",
        ".dockerfile": "Dockerfile",
        ".xml": "XML",
        ".svg": "SVG",
        ".png": "PNG Image",
        ".jpg": "JPEG Image",
        ".jpeg": "JPEG Image",
        ".gif": "GIF Image",
        ".ico": "Icon",
        ".txt": "Text",
        ".cfg": "Config",
        ".ini": "Config",
        ".conf": "Config",
        ".lock": "Lock File",
        ".env": "Environment",
        ".gitignore": "Git Ignore",
        ".gitkeep": "Git Keep",
        ".editorconfig": "Editor Config",
        ".prettierrc": "Prettier Config",
        ".eslintrc": "ESLint Config",
        ".babelrc": "Babel Config",
    }

    # ozelisleyokgenisletisimdosya (ornegin Dockerfile, Makefile) 
    if not ext:
        name_lower = path.name.lower()
        special_files = {
            "dockerfile": "Dockerfile",
            "makefile": "Makefile",
            "gemfile": "Gemfile",
            "rakefile": "Rakefile",
            "procfile": "Procfile",
        }
        return special_files.get(name_lower, "Other")

    return type_map.get(ext, f"Other ({ext})")


def count_files(
    root_path: Union[str, Path],
    exclude_dirs: Optional[set[str]] = None,
    exclude_files: Optional[set[str]] = None,
    exclude_extensions: Optional[set[str]] = None,
    follow_symlinks: bool = False,
    max_depth: Optional[int] = None,
) -> StatsResult:
    """rekursifistatistikprojedosya sayisimiktar. 

    Args:
        root_path: projekokdizin yolu
        exclude_dirs: isterharir tutdizinisimsetbirlestir (hayirbolgepuanbuyukkucukyaz) , varsayilanharir tutsikgorolustururetobje
        exclude_files: isterharir tutdosyaisimsetbirlestir (hayirbolgepuanbuyukkucukyaz) 
        exclude_extensions: isterharir tutdosyagenisletisimsetbirlestir (hayirbolgepuanbuyukkucukyaz) 
        follow_symlinks: olup olmadigiizlerastgelesembolnobaglanti
        max_depth: enbuyukrekursifderinlik, None tablogosterhayirsinir

    Returns:
        StatsResult icinnesne, iceriristatistiksonuc

    Raises:
        FileNotFoundError: egerkokdizinmevcut degil
        PermissionError: egeryokvarizinerisimkokdizin
    """
    root = Path(root_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"dizinmevcut degil: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"yolhayirdirdizin: {root}")
    if not os.access(root, os.R_OK):
        raise PermissionError(f"yokvarizinerisimdizin: {root}")

    # varsayilanharir tutdizin
    default_exclude_dirs = {
        "node_modules",
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        ".idea",
        ".vscode",
        ".vs",
        ".github",
        "site",
        "dist",
        "build",
        ".egg-info",
        ".tox",
        "venv",
        ".venv",
        "env",
        ".env",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".cache",
        ".next",
        ".nuxt",
        ".output",
        "coverage",
        ".coverage",
        "htmlcov",
        ".sass-cache",
        ".DS_Store",
        "thumbs.db",
        "__MACOSX",
        "target",  # Rust build
        "bin",
        "obj",  # .NET build
        ".serverless",
        ".terraform",
        ".serverless_nextjs",
        "cdk.out",
    }

    # varsayilanharir tutdosya
    default_exclude_files = {
        ".ds_store",
        "thumbs.db",
        "desktop.ini",
        ".gitkeep",
    }

    # varsayilanharir tutgenisletisim
    default_exclude_extensions = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".dylib",
        ".class",
        ".o",
        ".obj",
        ".lib",
        ".exe",
        ".msi",
        ".app",
        ".dmg",
        ".deb",
        ".rpm",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".iso",
        ".img",
        ".log",
        ".tmp",
        ".temp",
        ".swp",
        ".swo",
        ".bak",
        ".orig",
    }

    # birlestirveharir tutliste (varsayilan + ozel) 
    final_exclude_dirs = default_exclude_dirs | (exclude_dirs or set())
    final_exclude_files = default_exclude_files | (exclude_files or set())
    final_exclude_extensions = default_exclude_extensions | (
        exclude_extensions or set()
    )

    # istatistiksonuc
    total_files = 0
    total_dirs = 0
    total_size = 0
    by_type: dict[str, FileStats] = {}
    by_directory: dict[str, int] = {}
    errors: list[str] = []

    # kullanyiginilerlesatirderinlikoncelikdolas (kacinrekursifderinliksinir) 
    # yiginogreogre: (yol, mevcutderinlik)
    stack: list[tuple[Path, int]] = [(root, 0)]

    while stack:
        current_path, current_depth = stack.pop()

        # kontrolenbuyukderinlik
        if max_depth is not None and current_depth >= max_depth:
            continue

        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    entry_path = Path(entry.path)

                    # kontrololup olmadigiolmaliharir tut
                    if _is_excluded(
                        entry_path,
                        final_exclude_dirs,
                        final_exclude_files,
                        final_exclude_extensions,
                    ):
                        continue

                    if entry.is_dir(follow_symlinks=follow_symlinks):
                        total_dirs += 1
                        stack.append((entry_path, current_depth + 1))
                    elif entry.is_file(follow_symlinks=follow_symlinks):
                        total_files += 1
                        file_size = entry.stat(follow_symlinks=follow_symlinks).st_size
                        total_size += file_size

                        # goredosyatipistatistik
                        file_type = _get_file_type(entry_path)
                        if file_type not in by_type:
                            by_type[file_type] = FileStats(count=0, size=0, files=[])
                        by_type[file_type].count += 1
                        by_type[file_type].size += file_size
                        by_type[file_type].files.append(
                            str(entry_path.relative_to(root))
                        )

                        # goredizinistatistik
                        parent_dir = str(entry_path.parent.relative_to(root))
                        if parent_dir == ".":
                            parent_dir = "/"
                        if parent_dir not in by_directory:
                            by_directory[parent_dir] = 0
                        by_directory[parent_dir] += 1

        except PermissionError:
            errors.append(f"izinhayiryeterli, atladizin: {current_path}")
        except OSError as e:
            errors.append(f"erisimhata, atladizin: {current_path} - {e}")

    return StatsResult(
        total_files=total_files,
        total_dirs=total_dirs,
        total_size=total_size,
        by_type=dict(sorted(by_type.items(), key=lambda x: x[1].count, reverse=True)),
        by_directory=dict(
            sorted(by_directory.items(), key=lambda x: x[1], reverse=True)
        ),
        errors=errors,
        root_path=str(root),
    )
