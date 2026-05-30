from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
Wiki Parser - Python AST ayristir

kullan Python ast modulayristirkodyapi, cikar: 
- moduldokumantasyonkarakter dizisi
- iceri aktardilcumle
- siniftanim (ad, dokumantasyon, yontem) 
- fonksiyontanim (ad, dokumantasyon, parametre) 
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionInfo:
    """fonksiyonbilgi"""

    name: str
    docstring: Optional[str] = None
    args: list[str] = field(default_factory=list)
    returns: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    lineno: int = 0

    @property
    def signature(self) -> str:
        """olusturfonksiyonimzaisim"""
        params = ", ".join(self.args)
        return f"{self.name}({params})"


@dataclass
class ClassInfo:
    """sinifbilgi"""

    name: str
    docstring: Optional[str] = None
    base_classes: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    lineno: int = 0

    @property
    def public_methods(self) -> list[FunctionInfo]:
        """alortakacyontem (hayirile _ acbas) """
        return [m for m in self.methods if not m.name.startswith("_")]

    @property
    def private_methods(self) -> list[FunctionInfo]:
        """alozelvaryontem (ile _ acbas) """
        return [m for m in self.methods if m.name.startswith("_")]


@dataclass
class ImportInfo:
    """iceri aktarbilgi"""

    module: str
    names: list[str] = field(default_factory=list)
    alias: Optional[str] = None


@dataclass
class ModuleInfo:
    """modulbilgi"""

    path: Path
    relative_path: Path
    docstring: Optional[str] = None
    imports: list[ImportInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)


class ASTVisitorWithParent(ast.NodeVisitor):
    """kemerustdugumcekkullan AST erisim"""

    def __init__(self):
        self.parent_stack: list[ast.AST] = []

    def visit(self, node: ast.AST) -> None:
        # oncemevcutdugumyapicinustdugumbasyigin
        self.parent_stack.append(node)
        super().visit(node)
        self.parent_stack.pop()

    def get_parent(self, node: ast.AST) -> Optional[ast.AST]:
        """alustdugum"""
        if len(self.parent_stack) > 1:
            return self.parent_stack[-2]
        return None


class PythonParser:
    """Python kodayristir"""

    # gerekisteryoksaydizin
    IGNORE_DIRS = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        ".eggs",
        "*.egg-info",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".tox",
        "build",
        "dist",
    }

    # gerekisteryoksaydosya
    IGNORE_FILES = {
        "__init__.py",
        "__main__.py",
        "setup.py",
        "conftest.py",
    }

    def __init__(self, root_path: Path | str):
        """
        baslatayristir

        Args:
            root_path: projekokdizin
        """
        self.root_path = Path(root_path)

    def _add_parent_refs(self, tree: ast.AST) -> None:
        """icinvardugumekleustdugumcekkullan"""

        class ParentAdder(ast.NodeVisitor):
            def __init__(self):
                self.parent_map: dict[ast.AST, ast.AST] = {}

            def visit(self, node: ast.AST) -> None:
                for child in ast.iter_child_nodes(node):
                    self.parent_map[child] = node
                    self.visit(child)

        visitor = ParentAdder()
        visitor.visit(tree)

    def parse_file(self, file_path: Path | str) -> Optional[ModuleInfo]:
        """
        ayristirtekil Python dosya

        Args:
            file_path: Python dosyayol

        Returns:
            ModuleInfo veya None (egerayristirma basarisiz) 
        """
        file_path = Path(file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=str(file_path))

            # icinvardugumekleustdugumcekkullan
            self._add_parent_refs(tree)

            # hesaplaicinyol
            try:
                rel_path = file_path.relative_to(self.root_path)
            except ValueError:
                rel_path = file_path

            module = ModuleInfo(
                path=file_path,
                relative_path=rel_path,
                docstring=ast.get_docstring(tree),
            )

            # dolasustkatmandugum
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._visit_import(module, node)
                elif isinstance(node, ast.ClassDef):
                    class_info = self._visit_class(node)
                    if class_info:
                        module.classes.append(class_info)
                elif isinstance(node, ast.FunctionDef):
                    func_info = self._visit_function(node)
                    if func_info:
                        module.functions.append(func_info)

            return module

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"  ⚠️ ayristirma basarisiz {file_path}: {e}")
            return None

    def _visit_import(self, module: ModuleInfo, node: ast.Import | ast.ImportFrom):
        """erisimiceri aktardilcumle"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module.imports.append(
                    ImportInfo(
                        module=alias.name,
                        alias=alias.asname,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            names = [alias.name for alias in node.names]
            module.imports.append(
                ImportInfo(
                    module=module_name,
                    names=names,
                )
            )

    def _visit_class(self, node: ast.ClassDef) -> Optional[ClassInfo]:
        """erisimsiniftanim"""
        # altemel sinif
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_attr_name(base))

        # alyontem
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                func_info = self._visit_function(item)
                if func_info:
                    methods.append(func_info)

        # alsinifozellik (basittekiluygula, sadecealgilamasinifseviyeatadeger) 
        attributes = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attributes.append(item.target.id)

        return ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            base_classes=base_classes,
            methods=methods,
            attributes=attributes,
            lineno=node.lineno or 0,
        )

    def _visit_function(self, node: ast.FunctionDef) -> Optional[FunctionInfo]:
        """erisimfonksiyontanim"""
        # alparametre
        args = []
        args.extend([arg.arg for arg in node.args.args])

        # aldekoratif
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(self._get_attr_name(dec))

        # aldonusdegeryorumcoz
        returns = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = node.returns.id
            elif isinstance(node.returns, ast.Constant):
                returns = str(node.returns.value)

        return FunctionInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            args=args,
            returns=returns,
            decorators=decorators,
            lineno=node.lineno or 0,
        )

    def _get_attr_name(self, node: ast.Attribute) -> str:
        """alozellikdugumad"""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def scan_directory(
        self,
        directory: Path | str,
        pattern: str = "**/*.py",
    ) -> list[ModuleInfo]:
        """
        taradizinaltvar Python dosya

        Args:
            directory: dizin yolu
            pattern: dosyaeslestirmod

        Returns:
            ModuleInfo liste
        """
        directory = Path(directory)
        modules = []

        for py_file in directory.glob(pattern):
            # yoksaytestdosya
            if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
                continue

            # yoksaybelirtdosya
            if py_file.name in self.IGNORE_FILES:
                continue

            # yoksaybelirtdizin
            should_ignore = False
            for part in py_file.parts:
                if part in self.IGNORE_DIRS:
                    should_ignore = True
                    break
            if should_ignore:
                continue

            # ayristirdosya
            module = self.parse_file(py_file)
            if module:
                modules.append(module)

        return modules
