from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
isdizintara - Workspace Scanner

taraisdizin, olusturdosyaagacyapi, kullandeicin AI Agent saglarprojebaglam. 
destekdilalgilama, dosyaalintiister, derinlikkontrol. 
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

# harir tutdizinvedosya (ile .gitignore sinifbenzermantik) 
EXCLUDE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
    ".egg-info",
    ".coverage",
    ".hypothesis",
    "assets",
    "static",
    "public",
    ".idea",
    ".vscode",
    ".DS_Store",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".dat",
    ".log",
    ".lock",
    ".swp",
    ".swo",
    ".tmp",
    ".temp",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".svg",
    ".mp3",
    ".mp4",
    ".wav",
    ".flac",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".pdf",
    ".class",
    ".o",
    ".obj",
}


@dataclass
class FileNode:
    """
    dosyaagacdugum

    kullandetablogosterdizinveyadosyaagacsekilyapi. 
    """

    name: str
    path: Path
    is_dir: bool
    size: int = 0
    modified: str = ""
    language: Optional[str] = None  # koddil
    summary: Optional[str] = None  # dosyaalintiister
    children: list[FileNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        """donusturicinsozluk (kullande JSON sira) """
        return {
            "name": self.name,
            "path": str(self.path),
            "is_dir": self.is_dir,
            "size": self.size,
            "modified": self.modified,
            "language": self.language,
            "summary": self.summary,
            "children": [c.to_dict() for c in self.children],
        }


class WorkspaceScanner:
    """
    isdizintara

    tarabelirtdizin, olusturdosyaagacyapi, vesaglardosyaalintiisterislev. 

    kullanornek: 
        scanner = WorkspaceScanner(Path("/path/to/project"))
        tree = scanner.scan(max_depth=3)
        print(scanner.to_context_string())
    """

    # destekdilvedosyagenisletisim
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".pyw": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".swift": "swift",
        ".rb": "ruby",
        ".php": "php",
        ".md": "markdown",
        ".rst": "rst",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".fish": "bash",
        ".sql": "sql",
        ".graphql": "graphql",
        ".proto": "protobuf",
        ".dockerfile": "dockerfile",
        ".vue": "vue",
        ".svelte": "svelte",
        ".r": "r",
        ".lua": "lua",
        ".pl": "perl",
        ".hs": "haskell",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".jl": "julia",
        ".scala": "scala",
        ".groovy": "groovy",
        ".gradle": "groovy",
        ".tf": "hcl",
        ".tfvars": "hcl",
    }

    # ozeldosyaisimdilesle
    LANGUAGE_FILENAMES = {
        "dockerfile": "dockerfile",
        "makefile": "makefile",
        "gemfile": "ruby",
        "rakefile": "ruby",
        ".gitignore": "gitignore",
        ".dockerignore": "dockerignore",
        ".env.example": "bash",
        "cmakelists.txt": "cmake",
        "package.json": "json",
        "tsconfig.json": "json",
        "pyproject.toml": "toml",
        "setup.py": "python",
        "requirements.txt": "python",
        "pipfile": "toml",
        "poetry.lock": "json",
    }

    def __init__(self, root: Path):
        """
        baslattara

        Args:
            root: kokdizin yolu
        """
        self.root = Path(root)
        self._cache: dict = {}
        self._scan_stats = {
            "files_scanned": 0,
            "dirs_scanned": 0,
            "bytes_scanned": 0,
            "errors": [],
        }

    def scan(self, max_depth: int = 3) -> FileNode:
        """
        taraisdizin, donusdosyaagac

        Args:
            max_depth: enbuyukrekursifderinlik (0 = sadecekokdizindosya) 

        Returns:
            FileNode: kokdugum
        """
        self._scan_stats = {
            "files_scanned": 0,
            "dirs_scanned": 0,
            "bytes_scanned": 0,
            "errors": [],
        }
        return self._scan_recursive(self.root, depth=0, max_depth=max_depth)

    def _scan_recursive(self, path: Path, depth: int, max_depth: int) -> FileNode:
        """rekursiftara"""
        node = FileNode(
            name=path.name or str(path),
            path=path,
            is_dir=path.is_dir(),
        )

        if not path.exists():
            return node

        try:
            stat = path.stat()
            node.size = stat.st_size
            node.modified = time.strftime(
                "%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)
            )
        except OSError:
            pass

        if not path.is_dir():
            node.language = self._detect_language(path)
            return node

        # dizin
        self._scan_stats["dirs_scanned"] += 1
        node.is_dir = True

        # ulaskadarenbuyukderinlik, hayirtekrarrekursifaltdizin (ancakhalalistelemevcutdugum) 
        # max_depth=0: sadecegosterkokdugum; max_depth=1: gosterkok+birkatmanaltdizin
        if depth >= max_depth:
            return node

        try:
            entries = list(path.iterdir())
        except PermissionError:
            self._scan_stats["errors"].append(f"Permission denied: {path}")
            return node
        except OSError as e:
            self._scan_stats["errors"].append(f"{path}: {e}")
            return node

        # oncealset, tekrarsirala (dizinoncelik, aynitipgoreisimharfsirala) 
        children: list[FileNode] = []
        for entry in entries:
            name = entry.name

            # atlagizledosya (ancakkoru .gitignore vb.ozeldosya) 
            if name.startswith(".") and name not in (
                ".gitignore",
                ".dockerignore",
                ".env.example",
                ".env",
            ):
                continue

            # atlaharir tutdizin
            if entry.is_dir() and name in EXCLUDE_DIRS:
                continue

            # atlaharir tutgenisletisim
            if entry.is_file():
                ext = entry.suffix.lower()
                if ext in EXCLUDE_EXTENSIONS:
                    continue
                # gizledosya (ancakkoru .gitignore vb.ozeldosya) 
                if name.startswith(".") and name not in (
                    ".gitignore",
                    ".dockerignore",
                    ".env.example",
                    ".env",
                ):
                    continue

            child = self._scan_recursive(entry, depth=depth + 1, max_depth=max_depth)
            children.append(child)

            if entry.is_file():
                self._scan_stats["files_scanned"] += 1
                self._scan_stats["bytes_scanned"] += child.size
            else:
                self._scan_stats["dirs_scanned"] += 1

        # sirala: dizinoncelik, tekrargoreisimharf
        def sort_key(n: FileNode) -> tuple:
            return (not n.is_dir, n.name.lower())

        children.sort(key=sort_key)
        node.children = children

        return node

    def _detect_language(self, path: Path) -> Optional[str]:
        """algilamadosyadil"""
        name = path.name.lower()
        ext = path.suffix.lower()

        # oncelikkontrolozeldosyaisim
        if name in self.LANGUAGE_FILENAMES:
            return self.LANGUAGE_FILENAMES[name]

        # tekrarkontrolgenisletisim
        return self.LANGUAGE_EXTENSIONS.get(ext)

    def get_file_summary(self, path: Path, max_lines: int = 50) -> str:
        """
        aldosyaalintiister (kullandebaglam) 

        icindekoddosya, cikaronce N satiryapicinalintiister. 
        icindebuyuktipdosya, sadeceokuyapilandirmaveyayorum. 

        Args:
            path: dosyayol
            max_lines: enbuyukokusatirsayi

        Returns:
            str: dosyaalintiisterkarakter dizisi
        """
        path = Path(path)

        if not path.exists():
            return f"[dosyamevcut degil: {path}]"

        if path.is_dir():
            return f"[dizin: {path}]"

        try:
            stat = path.stat()
        except OSError:
            return f"[yokyontemoku: {path}]"

        # kucukdosyadogrubaglanokutumkisim
        if stat.st_size < 10 * 1024:  # < 10KB
            lines = self._read_file_lines(path, max_lines)
        else:
            # buyukdosyasadeceokuonceyuzkisimpuan
            lines = self._read_file_lines(path, max_lines)

        if not lines:
            return f"[bosdosya: {path.name}]"

        # olusturalintiister
        language = self._detect_language(path)
        lines[0] if lines else ""

        # algilamadosyatipvecikaranahtarbilgi
        summary_parts = []

        if language == "python":
            summary_parts = self._summarize_python(lines, path)
        elif language in ("javascript", "typescript"):
            summary_parts = self._summarize_js_ts(lines, path)
        elif language == "json":
            summary_parts = self._summarize_json(path)
        elif language in ("yaml", "toml"):
            summary_parts = self._summarize_config(lines, path)
        elif language in ("markdown", "rst"):
            summary_parts = self._summarize_doc(lines, path)
        elif language == "dockerfile":
            summary_parts = self._summarize_dockerfile(lines, path)
        else:
            # kullanalintiister: oncebirkacsatir
            summary_parts = lines[: max_lines // 2]

        # grupbirlestiralintiister
        if isinstance(summary_parts, list) and summary_parts:
            body = "\n".join(summary_parts)
        else:
            body = str(summary_parts)

        return f"""[{language or "unknown"}] {path.name}
yol: {path.relative_to(self.root) if path.is_relative_to(self.root) else path}
buyukkucuk: {self._format_size(stat.st_size)}
degistir: {time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))}

--- icerikalintiister ---
{body}"""

    def _read_file_lines(self, path: Path, max_lines: int) -> list[str]:
        """guvenlikokudosyasatir"""
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip("\n\r"))
                return lines
        except OSError:
            return []

    def _summarize_python(self, lines: list[str], path: Path) -> list[str]:
        """Python dosyaalintiister: cikariceri aktar, sinif, fonksiyontanim"""
        result = []
        imports = []
        classes = []
        functions = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                if len(imports) < 10:
                    imports.append(stripped)
            elif stripped.startswith("class "):
                # cikarsinifisim
                parts = stripped.split()
                if len(parts) >= 2:
                    classes.append(parts[1].split("(")[0])
            elif stripped.startswith("def "):
                # cikarfonksiyonisim
                parts = stripped.split("(", 1)
                if len(parts) >= 1:
                    fname = parts[0].replace("async ", "").replace("def ", "")
                    functions.append(fname)

        if imports:
            result.append(
                f"iceri aktar: {', '.join(imports[:5])}" + (" ..." if len(imports) > 5 else "")
            )
        if classes:
            result.append(f"sinif: {', '.join(classes)}")
        if functions:
            result.append(
                f"fonksiyon: {', '.join(functions[:10])}"
                + (" ..." if len(functions) > 10 else "")
            )

        # egeryokcikarkadar, donusoncebirkacsatir
        if not result:
            result = lines[:10]

        return result

    def _summarize_js_ts(self, lines: list[str], path: Path) -> list[str]:
        """JS/TS dosyaalintiister: cikariceri aktar, disa aktar, fonksiyon"""
        result = []
        imports = []
        exports = []
        functions = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import "):
                if len(imports) < 10:
                    imports.append(stripped[:80])
            elif stripped.startswith("export "):
                if len(exports) < 10:
                    exports.append(stripped[:80])
            elif "function " in stripped or "=> {" in stripped:
                if len(functions) < 10:
                    # cikarfonksiyonisim
                    fn_match = (
                        stripped.split("function")[1].split("(")[0].strip()
                        if "function" in stripped
                        else ""
                    )
                    functions.append(fn_match or stripped[:50])

        if imports:
            result.append(f"iceri aktar: {len(imports)} bagimlilik")
        if exports:
            result.append(
                f"disa aktar: {', '.join(exports[:5])}" + (" ..." if len(exports) > 5 else "")
            )
        if functions:
            result.append(
                f"fonksiyon: {', '.join(functions[:10])}"
                + (" ..." if len(functions) > 10 else "")
            )

        if not result:
            result = lines[:10]

        return result

    def _summarize_json(self, path: Path) -> list[str]:
        """JSON dosyaalintiister"""
        try:
            import json

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                keys = list(data.keys())[:20]
                return [f"anahtar: {', '.join(keys)}" + (" ..." if len(data) > 20 else "")]
            if isinstance(data, list):
                return [
                    f"sayigrup: {len(data)} ogre, ornek: {str(data[0])[:100] if data else '[]'}"
                ]
            return [str(data)[:200]]
        except Exception:
            return ["[JSON ayristirma basarisiz]"]

    def _summarize_config(self, lines: list[str], path: Path) -> list[str]:
        """YAML/TOML yapilandirmaalintiister"""
        result = []
        for line in lines[:30]:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                if stripped.startswith("["):
                    result.append(f"bolum: {stripped}")
                elif ":" in stripped:
                    key = stripped.split(":")[0].strip()
                    if key:
                        result.append(f"  {key}")
        return result[:20]

    def _summarize_doc(self, lines: list[str], path: Path) -> list[str]:
        """Markdown/RST dokumantasyonalintiister"""
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                result.append(stripped)
            elif stripped.startswith(("===", "---")):
                continue
            elif result and len(result) < 10:
                result.append(stripped[:100])

        if result:
            return result[:15]
        return lines[:10]

    def _summarize_dockerfile(self, lines: list[str], path: Path) -> list[str]:
        """Dockerfile alintiister"""
        result = ["FROM / isaretkomut:"]
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("FROM ", "RUN ", "COPY ", "WORKDIR ")):
                result.append(f"  {stripped}")
        return result[:15]

    def _format_size(self, size: int) -> str:
        """formatdosyabuyukkucuk"""
        if size < 1024:
            return f"{size}B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.1f}GB"

    def to_context_string(self, max_depth: int = 3) -> str:
        """
        olusturolabilirkullande Prompt baglamkarakter dizisi

        taramevcutisdizin, olusturkisisinifolabilirokudosyaagac. 

        Args:
            max_depth: taraderinlik

        Returns:
            str: baglamkarakter dizisi
        """
        tree = self.scan(max_depth=max_depth)
        lines = self._render_tree(tree, prefix="", is_last=True)
        lines.append("")

        # ekleistatistikbilgi
        stats = self._scan_stats
        lines.append(
            f"ortaktara {stats['files_scanned']} dosya, {stats['dirs_scanned']} dizin"
        )
        lines.append(f"toplambuyukkucuk: {self._format_size(stats['bytes_scanned'])}")

        if stats["errors"]:
            lines.append(f"tarazamangonderyarat {len(stats['errors'])} hata")

        return "\n".join(lines)

    def _render_tree(self, node: FileNode, prefix: str, is_last: bool) -> list[str]:
        """renderdosyaagac"""
        lines = []

        # mevcutdugum
        connector = "└── " if is_last else "├── "
        size_str = f" ({self._format_size(node.size)})" if node.size > 0 else ""
        lang_str = f" [{node.language}]" if node.language else ""
        modified_str = f" {node.modified}" if node.modified else ""

        lines.append(
            f"{prefix}{connector}{node.name}{size_str}{lang_str}{modified_str}"
        )

        # altdugum
        if node.children:
            child_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(node.children):
                is_child_last = i == len(node.children) - 1
                child_lines = self._render_tree(child, child_prefix, is_child_last)
                lines.extend(child_lines)

        return lines
