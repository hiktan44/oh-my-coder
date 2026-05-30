from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
kodkutuphaneindeks

Islev:
1. taraprojedosya
2. ayristirkodyapi
3. olusturgomuyonmiktar
4. olusturyonmiktarindeks
"""

import ast
import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class CodeElementType(str, Enum):
    """kodogreogretip"""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    CONSTANT = "constant"
    OTHER = "other"


class ProgrammingLanguage(str, Enum):
    """duzenlesurecdil"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    C = "c"
    UNKNOWN = "unknown"


@dataclass
class CodeElement:
    """kodogreogre"""

    id: str
    name: str
    type: CodeElementType
    file_path: str
    start_line: int
    end_line: int
    source_code: str
    docstring: Optional[str] = None
    signature: Optional[str] = None
    parent: Optional[str] = None  # ustogreogre ID
    children: list[str] = field(default_factory=list)
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileIndex:
    """dosyaindeks"""

    file_path: str
    language: ProgrammingLanguage
    elements: list[CodeElement]
    imports: list[str]
    exports: list[str]
    dependencies: list[str]
    hash: str
    last_modified: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexConfig:
    """indeksyapilandirma"""

    root_path: Path
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "*.pyc",
            "*.pyo",
            "*.so",
            "*.dylib",
            "*.dll",
            "dist",
            "build",
            ".eggs",
            "*.egg-info",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
        ]
    )
    include_patterns: list[str] = field(
        default_factory=lambda: [
            "*.py",
            "*.js",
            "*.ts",
            "*.java",
            "*.go",
            "*.rs",
            "*.cpp",
            "*.c",
            "*.h",
            "*.hpp",
            "*.json",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.md",
        ]
    )
    max_file_size: int = 100 * 1024  # 100KB
    max_elements: int = 10000
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 500
    chunk_overlap: int = 50


class PythonParser:
    """Python kodayristir"""

    def parse(self, source: str, file_path: str) -> list[CodeElement]:
        """ayristir Python kaynakkod"""
        elements = []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return elements

        source_lines = source.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                element = self._parse_function(node, source_lines, file_path)
                if element:
                    elements.append(element)

            elif isinstance(node, ast.ClassDef):
                element = self._parse_class(node, source_lines, file_path)
                if element:
                    elements.append(element)

        return elements

    def _parse_function(
        self, node: ast.FunctionDef, source_lines: list[str], file_path: str
    ) -> Optional[CodeElement]:
        """ayristirfonksiyontanim"""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        source_code = "\n".join(source_lines[start_line - 1 : end_line])

        # olusturimzaisim
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        signature = f"def {node.name}({', '.join(args)}){returns}"

        # cikar docstring
        docstring = ast.get_docstring(node)

        return CodeElement(
            id=self._generate_id(file_path, node.name, start_line),
            name=node.name,
            type=CodeElementType.FUNCTION,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            source_code=source_code,
            docstring=docstring,
            signature=signature,
        )

    def _parse_class(
        self, node: ast.ClassDef, source_lines: list[str], file_path: str
    ) -> Optional[CodeElement]:
        """ayristirsiniftanim"""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        source_code = "\n".join(source_lines[start_line - 1 : end_line])

        # olusturimzaisim
        bases = [ast.unparse(base) for base in node.bases]
        signature = f"class {node.name}"
        if bases:
            signature += f"({', '.join(bases)})"

        # cikar docstring
        docstring = ast.get_docstring(node)

        return CodeElement(
            id=self._generate_id(file_path, node.name, start_line),
            name=node.name,
            type=CodeElementType.CLASS,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            source_code=source_code,
            docstring=docstring,
            signature=signature,
        )

    def _generate_id(self, file_path: str, name: str, line: int) -> str:
        """olusturogreogre ID (olmayangizlikodkullanyol) """
        hash_input = f"{file_path}:{name}:{line}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]


class CodebaseIndexer:
    """
    kodkutuphaneindeks

    Islev:
    1. taraprojedosya
    2. ayristirkodyapi
    3. olusturgomuyonmiktar
    4. olusturyonmiktarindeks
    """

    LANGUAGE_EXTENSIONS = {
        ".py": ProgrammingLanguage.PYTHON,
        ".js": ProgrammingLanguage.JAVASCRIPT,
        ".ts": ProgrammingLanguage.TYPESCRIPT,
        ".java": ProgrammingLanguage.JAVA,
        ".go": ProgrammingLanguage.GO,
        ".rs": ProgrammingLanguage.RUST,
        ".cpp": ProgrammingLanguage.CPP,
        ".cxx": ProgrammingLanguage.CPP,
        ".cc": ProgrammingLanguage.CPP,
        ".c": ProgrammingLanguage.C,
        ".h": ProgrammingLanguage.C,
        ".hpp": ProgrammingLanguage.CPP,
    }

    def __init__(self, config: IndexConfig, embedding_client=None):
        """
        Args:
            config: indeksyapilandirma
            embedding_client: gomuyonmiktaristemci (olabilirsec) 
        """
        self.config = config
        self.embedding_client = embedding_client
        self.file_indices: dict[str, FileIndex] = {}
        self.element_index: dict[str, CodeElement] = {}
        self._parsers = {
            ProgrammingLanguage.PYTHON: PythonParser(),
        }

    def should_index(self, file_path: Path) -> bool:
        """karar verolup olmadigiolmalibuindeksbudosya"""
        # kontroldosyabuyukkucuk
        if file_path.stat().st_size > self.config.max_file_size:
            return False

        # kontrolharir tutmod
        for pattern in self.config.exclude_patterns:
            if pattern in str(file_path):
                return False

        # kontrolicerirmod
        return any(file_path.match(pattern) for pattern in self.config.include_patterns)

    def detect_language(self, file_path: Path) -> ProgrammingLanguage:
        """algilamadosyadil"""
        ext = file_path.suffix.lower()
        return self.LANGUAGE_EXTENSIONS.get(ext, ProgrammingLanguage.UNKNOWN)

    def index_file(self, file_path: Path) -> Optional[FileIndex]:
        """indekstekildosya"""
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        language = self.detect_language(file_path)
        file_hash = hashlib.sha256(source.encode()).hexdigest()  # olmayangizlikodkullanyol
        relative_path = str(file_path.relative_to(self.config.root_path))

        # ayristirkodogreogre
        elements = []
        parser = self._parsers.get(language)
        if parser:
            elements = parser.parse(source, relative_path)

        # cikariceri aktar
        imports = self._extract_imports(source, language)

        # guncelleogreogreindeks
        for element in elements:
            self.element_index[element.id] = element

        file_index = FileIndex(
            file_path=relative_path,
            language=language,
            elements=elements,
            imports=imports,
            exports=[],  # disa aktarcikarbekleuygula (gerek AST analiz) 
            dependencies=[],
            hash=file_hash,
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
        )

        self.file_indices[relative_path] = file_index
        return file_index

    def index_directory(self, progress_callback=None) -> dict[str, FileIndex]:
        """indekstamdizin"""
        root = self.config.root_path

        # alsetvardosya
        files = []
        for ext in self.config.include_patterns:
            files.extend(root.rglob(ext.lstrip("*.")))

        # filtreledosya
        valid_files = [f for f in files if self.should_index(f)]

        # indeksdosya
        total = len(valid_files)
        for i, file_path in enumerate(valid_files):
            self.index_file(file_path)

            if progress_callback:
                progress_callback(i + 1, total, file_path)

        return self.file_indices

    async def generate_embeddings(self, batch_size: int = 100) -> None:
        """icinvarogreogreolusturgomuyonmiktar"""
        if not self.embedding_client:
            return

        elements = list(self.element_index.values())

        for i in range(0, len(elements), batch_size):
            batch = elements[i : i + batch_size]
            texts = [self._element_to_text(e) for e in batch]

            # toplucamiktarolusturgomu
            embeddings = await self._batch_embed(texts)

            for j, element in enumerate(batch):
                element.embedding = embeddings[j]

            # kacin API sinirakis
            await asyncio.sleep(0.1)

    def _element_to_text(self, element: CodeElement) -> str:
        """ogreogredonusturicingomumetin"""
        parts = [
            f"File: {element.file_path}",
            f"Type: {element.type.value}",
            f"Name: {element.name}",
        ]

        if element.signature:
            parts.append(f"Signature: {element.signature}")

        if element.docstring:
            parts.append(f"Docstring: {element.docstring}")

        # eklekaynakkod (kes) 
        source = element.source_code
        if len(source) > 500:
            source = source[:500] + "..."
        parts.append(f"Source:\n{source}")

        return "\n".join(parts)

    async def _batch_embed(self, texts: list[str]) -> list[list[float]]:
        """toplucamiktarolusturgomu. yok embedding_client zamandonusbosyonmiktarliste. """
        if not self.embedding_client:
            return [[] for _ in texts]

        # cagri embedding_client olusturgomu
        return [[] for _ in texts]

    def _extract_imports(self, source: str, language: ProgrammingLanguage) -> list[str]:
        """cikariceri aktardilcumle"""
        imports = []

        if language == ProgrammingLanguage.PYTHON:
            # cikar Python import
            pattern = r"^(?:from|import)\s+([^\s]+)"
            matches = re.findall(pattern, source, re.MULTILINE)
            imports.extend(matches)

        return imports

    def get_stats(self) -> dict[str, Any]:
        """alindeksistatistik"""
        return {
            "files_indexed": len(self.file_indices),
            "elements_indexed": len(self.element_index),
            "languages": self._count_by_language(),
            "element_types": self._count_by_type(),
        }

    def _count_by_language(self) -> dict[str, int]:
        """goredilistatistik"""
        counts = {}
        for file_index in self.file_indices.values():
            lang = file_index.language.value
            counts[lang] = counts.get(lang, 0) + 1
        return counts

    def _count_by_type(self) -> dict[str, int]:
        """goreogreogretipistatistik"""
        counts = {}
        for element in self.element_index.values():
            type_name = element.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def save(self, path: Path) -> None:
        """kaydetindeks"""
        path.mkdir(parents=True, exist_ok=True)

        # kaydetdosyaindeks
        file_index_path = path / "files.json"
        with open(file_index_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    fp: {
                        "file_path": fi.file_path,
                        "language": fi.language.value,
                        "imports": fi.imports,
                        "hash": fi.hash,
                        "last_modified": fi.last_modified.isoformat(),
                    }
                    for fp, fi in self.file_indices.items()
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        # kaydetogreogreindeks
        element_index_path = path / "elements.json"
        with open(element_index_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    eid: {
                        "id": e.id,
                        "name": e.name,
                        "type": e.type.value,
                        "file_path": e.file_path,
                        "start_line": e.start_line,
                        "end_line": e.end_line,
                        "source_code": e.source_code,
                        "docstring": e.docstring,
                        "signature": e.signature,
                    }
                    for eid, e in self.element_index.items()
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    def load(self, path: Path) -> None:
        """yukleindeks"""
        file_index_path = path / "files.json"
        if file_index_path.exists():
            with open(file_index_path, encoding="utf-8") as f:
                _files_data = json.load(f)

        element_index_path = path / "elements.json"
        if element_index_path.exists():
            with open(element_index_path, encoding="utf-8") as f:
                _elements_data = json.load(f)
