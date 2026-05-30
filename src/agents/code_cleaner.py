from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
kod temizleme Agent - Bakım kolaylığını artırmak için gereksiz kodu otomatik olarak temizleyin

Temiz politika beyaz listesi:
1. kullanılmayan import / işlev / değişken(ruff tespit edilebilir)
2. Kod pasajını tekrarlayın (>5 Aynı satırlar kopya olarak kabul edilir)
3. Ölü kod dosyaları (başvurulan modül yok)
4. boş dosya / yer tutucu dosyası
5. Güncel olmayan yapılandırma dosyası

Silmeyin:
- Açıklamalı iş mantığı dosyaları
- test dosyası
- Yapılandırma dosyası
- Dokümantasyon dosyası
"""


import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CleanerStrategy:
    """Temiz politika beyaz listesi"""

    # Bu politikanın etkinleştirilip etkinleştirilmeyeceği
    enabled: bool = True

    # 1. Kullanılmıyor import/işlev/değişken
    unused_imports: bool = True  # ruff check --fix
    unused_functions: bool = True
    unused_variables: bool = True

    # 2. Yinelenen kod tespiti
    detect_duplicates: bool = True
    duplicate_min_lines: int = 5  # Bu satır sayısını aşan kopyalar kabul edilecektir

    # 3. Ölü kod tespiti
    detect_dead_code: bool = True
    dead_code_safe_mode: bool = True  # İşaretle ancak otomatik olarak kaldırılmıyor

    # 4. Boş dosya tespiti
    detect_empty_files: bool = True
    auto_delete_empty: bool = False  # Boş dosyaların otomatik olarak silinip silinmeyeceği

    # 5. Güncel olmayan yapılandırma dosyası
    detect_outdated_configs: bool = True
    outdated_patterns: list[str] = field(
        default_factory=lambda: [
            r"\.env\.example\.bak",
            r"config\.old",
            r"\.pyc$",
            r"__pycache__",
        ]
    )


@dataclass
class CleaningIssue:
    """Tek temizleme sorunu"""

    file_path: str
    issue_type: str  # unused_import, duplicate, dead_code, empty, outdated
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    content: str = ""  # Sorun içeriğinin özeti
    severity: str = "warning"  # info/warning/error
    auto_fixable: bool = False
    fix_suggestion: str = ""


@dataclass
class CleanerReport:
    """temizleme raporu"""

    timestamp: str = ""
    project_path: str = ""

    # istatistikler
    total_issues: int = 0
    files_scanned: int = 0

    # Türe göre istatistikler
    by_type: dict[str, int] = field(default_factory=dict)

    # Soru listesi
    issues: list[CleaningIssue] = field(default_factory=list)

    # Sabit
    fixed_count: int = 0
    fixed_files: list[str] = field(default_factory=list)

    # Onaylanacak (manuel inceleme gerektirir)
    pending_count: int = 0
    pending_issues: list[CleaningIssue] = field(default_factory=list)

    # token Tasarruf tahmini
    lines_removed: int = 0
    estimated_token_savings: int = 0


class CodeCleaner:
    """kod temizleyici

    Politika beyaz listesini kullanarak gereksiz kodu otomatik olarak algılayın ve temizleyin.
    """

    def __init__(
        self,
        project_path: Path,
        strategy: Optional[CleanerStrategy] = None,
    ):
        self.project_path = Path(project_path)
        self.strategy = strategy or CleanerStrategy()

        # Tarandı Python belge
        self.python_files: list[Path] = []

        # Sonuçları analiz edin
        self.issues: list[CleaningIssue] = []

    def scan(self) -> CleanerReport:
        """Projeyi tarayın ve temizleme raporunu geri gönderin"""
        report = CleanerReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_path=str(self.project_path),
        )

        # 1. TOPLAMAK Python belge
        self.python_files = self._collect_python_files()
        report.files_scanned = len(self.python_files)

        # 2. Çeşitli testler gerçekleştirin
        if self.strategy.unused_imports or self.strategy.unused_functions:
            self._check_unused_code()

        if self.strategy.detect_duplicates:
            self._check_duplicate_code()

        if self.strategy.detect_dead_code:
            self._check_dead_code()

        if self.strategy.detect_empty_files:
            self._check_empty_files()

        if self.strategy.detect_outdated_configs:
            self._check_outdated_configs()

        # 3. Rapor oluştur
        self.issues = self.issues
        report.issues = self.issues
        report.total_issues = len(self.issues)

        # Türe göre istatistikler
        for issue in self.issues:
            report.by_type[issue.issue_type] = (
                report.by_type.get(issue.issue_type, 0) + 1
            )

        # Kategori: Otomatik tamir vs Onaylanacak
        auto_fixable = [i for i in self.issues if i.auto_fixable]
        pending = [i for i in self.issues if not i.auto_fixable]

        report.pending_issues = pending
        report.pending_count = len(pending)

        # hesaplamak token kaydetmek
        report.lines_removed = sum(
            (i.line_end or 0) - (i.line_start or 0) + 1 for i in auto_fixable
        )
        report.estimated_token_savings = report.lines_removed * 10  # Tahmin etmek

        return report

    def _collect_python_files(self) -> list[Path]:
        """hepsini topla Python Dosyalar (testleri, sanal ortamları vb. hariç tutun)"""
        files = []
        exclude_dirs = {
            ".git",
            ".venv",
            "venv",
            "env",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            "build",
            "dist",
            ".tox",
        }

        for path in self.project_path.rglob("*.py"):
            # Hariç tutulan dizinleri atla
            if any(ex in path.parts for ex in exclude_dirs):
                continue
            # Test dosyalarını atla (isteğe bağlı)
            if "test_" in path.name or path.name.startswith("test_"):
                continue
            files.append(path)

        return files

    def _check_unused_code(self):
        """Kullanılmayanları tespit et import/işlev/değişken"""
        # kullanmak ruff Algılama
        try:
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "ruff",
                    "check",
                    "--select",
                    "F401,F841,F821",
                    "--output-format",
                    "json",
                    str(self.project_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                try:
                    errors = json.loads(result.stdout)
                except json.JSONDecodeError:
                    return

                for err in errors:
                    location = err.get("location", {})
                    file_path = err.get("filename", "")

                    if not file_path:
                        continue

                    # Soru türünü belirleyin
                    code = err.get("code", "")
                    if code == "F401":
                        issue_type = "unused_import"
                    elif code == "F841":
                        issue_type = "unused_variable"
                    else:
                        issue_type = "unused_code"

                    self.issues.append(
                        CleaningIssue(
                            file_path=file_path,
                            issue_type=issue_type,
                            line_start=location.get("row"),
                            line_end=location.get("row"),
                            content=err.get("message", "")[:100],
                            severity="warning",
                            auto_fixable=True,
                            fix_suggestion="Kullanılmayan kodu kaldır",
                        )
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # ruff Yüklenmedi veya zaman aşımına uğradı, atlandı

    def _check_duplicate_code(self):
        """Yinelenen kod parçacıklarını algılama"""
        # Basitleştirilmiş versiyon: fonksiyona göre/Yöntem karma tespiti
        # Tam uygulama daha karmaşık gerektirir AST analiz etmek

        code_hashes: dict[str, list[tuple[Path, int]]] = {}

        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                # İşleve göre bölme (basitleştirilmiş: büyüktür ile ayrılmış boş satır)5satır kodu bloğu)
                current_block = []
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    current_block.append(line)

                    # Bir fonksiyon tanımıyla karşılaşılırsa önceki bloğu işleyin
                    if re.match(r"^def\s+", stripped) or re.match(
                        r"^class\s+", stripped
                    ):
                        if len(current_block) >= self.strategy.duplicate_min_lines:
                            block_text = "\n".join(current_block)
                            block_hash = hash(block_text)
                            if block_hash not in code_hashes:
                                code_hashes[block_hash] = []
                            code_hashes[block_hash].append(
                                (py_file, i - len(current_block))
                            )

                        current_block = []

                # Son bloğu işle
                if len(current_block) >= self.strategy.duplicate_min_lines:
                    block_text = "\n".join(current_block)
                    block_hash = hash(block_text)
                    if block_hash not in code_hashes:
                        code_hashes[block_hash] = []
                    code_hashes[block_hash].append(
                        (py_file, len(lines) - len(current_block))
                    )

            except Exception:
                continue

        # Yinelenen kod bloklarını bulma
        for locations in code_hashes.values():
            if len(locations) >= 2:
                locations_str = ", ".join(
                    f"{p.name}:{line}" for p, line in locations[:3]
                )
                self.issues.append(
                    CleaningIssue(
                        file_path=locations[0][0].name,
                        issue_type="duplicate_code",
                        line_start=locations[0][1],
                        line_end=locations[0][1] + self.strategy.duplicate_min_lines,
                        content=f"Yinelenen kod olduğundan şüpheleniliyor, başka yerde görünebilir: {locations_str}",
                        severity="info",
                        auto_fixable=False,
                        fix_suggestion="Genel işlev olarak çıkar",
                    )
                )

    def _check_dead_code(self):
        """Ölü kodu tespit et (referanssız işlevler/tür)"""
        # Referans grafiği oluşturun
        all_names: set[str] = set()  # Tanımlanan tüm adlar
        referenced_names: set[str] = set()  # başvurulan ad

        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")

                # Tanımlanmış işlevleri çıkar/Sınıf adı
                for match in re.finditer(
                    r"^(?:def|class)\s+(\w+)", content, re.MULTILINE
                ):
                    all_names.add(match.group(1))

                # Alıntılanan adları çıkarın (basitleştirilmiş)
                for match in re.finditer(r"\b(\w+)\b", content):
                    name = match.group(1)
                    if name in all_names:
                        referenced_names.add(name)

            except Exception:
                continue

        # Alıntı yapılmayan tanımları bulun
        dead_names = all_names - referenced_names

        # Yalnızca açıkça kullanılmayanları bildirin (ihtiyatlı)
        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                for name in dead_names:
                    # Dosyada tanımlı olup olmadığını kontrol edin
                    if re.search(
                        rf"^(?:def|class)\s+{re.escape(name)}", content, re.MULTILINE
                    ):
                        self.issues.append(
                            CleaningIssue(
                                file_path=str(py_file),
                                issue_type="dead_code",
                                content=f"işlev/tür '{name}' Alıntı yapılmadı",
                                severity="info",
                                auto_fixable=False,
                                fix_suggestion="Onaylandıktan sonra amacını açıklayan belgeleri silin veya ekleyin.",
                            )
                        )
            except Exception:
                continue

    def _check_empty_files(self):
        """Boş dosyaları tespit et"""
        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                stripped = content.strip()

                # Boş dosya veya yalnızca yorum içeren dosya
                if not stripped or (
                    stripped
                    and all(
                        line.strip().startswith(("#", '"""', "'''"))
                        for line in stripped.split("\n")
                    )
                ):
                    self.issues.append(
                        CleaningIssue(
                            file_path=str(py_file),
                            issue_type="empty_file",
                            content="Boş dosya veya yalnızca yorumlar",
                            severity="info",
                            auto_fixable=self.strategy.auto_delete_empty,
                            fix_suggestion="İçerik kaldırma veya ekleme",
                        )
                    )
            except Exception:
                continue

    def _check_outdated_configs(self):
        """Güncelliğini yitirmiş yapılandırma dosyalarını tespit edin"""
        patterns = self.strategy.outdated_patterns

        for pattern in patterns:
            for path in self.project_path.rglob("*"):
                if re.search(pattern, path.name):
                    self.issues.append(
                        CleaningIssue(
                            file_path=str(path),
                            issue_type="outdated_config",
                            content=f"Güncelliğini yitirdiğinden şüphelenilen yapılandırma dosyası: {path.name}",
                            severity="info",
                            auto_fixable=False,
                            fix_suggestion="Onaylandıktan sonra silin veya arşivleyin",
                        )
                    )

    def fix(self, issue: CleaningIssue) -> bool:
        """Tek bir sorunu otomatik olarak düzeltmeyi deneyin"""
        if not issue.auto_fixable:
            return False

        try:
            if issue.issue_type in ("unused_import", "unused_variable", "unused_code"):
                # kullanmak ruff auto-fix
                result = subprocess.run(
                    [
                        "python3",
                        "-m",
                        "ruff",
                        "--fix",
                        issue.file_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.returncode == 0

            if issue.issue_type == "empty_file" and self.strategy.auto_delete_empty:
                # Boş dosyaları sil
                Path(issue.file_path).unlink()
                return True

        except Exception:
            pass

        return False

    def fix_all_auto(self) -> CleanerReport:
        """Düzeltilebilir tüm sorunları otomatik olarak düzeltin"""
        report = CleanerReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_path=str(self.project_path),
        )

        # Önce tarayın
        self.scan()

        fixed_files = set()

        for issue in self.issues:
            if issue.auto_fixable and self.fix(issue):
                fixed_files.add(issue.file_path)
                report.fixed_count += 1

        report.fixed_files = list(fixed_files)
        return report

    def generate_report_md(self, report: CleanerReport) -> str:
        """oluşturmak Markdown Temizleme raporunu biçimlendir"""
        lines = [
            "# Kod Temizleme Raporu",
            "",
            f"**zaman**: {report.timestamp}",
            f"**proje**: {report.project_path}",
            f"**Taranan dosya sayısı**: {report.files_scanned}",
            "",
            "---",
            "",
            "## istatistikler",
            "",
            f"- **toplam soru sayısı**: {report.total_issues}",
            f"- **Otomatik olarak onarıldı**: {report.fixed_count}",
            f"- **Onaylanacak**: {report.pending_count}",
            f"- **Satır sayısında beklenen azalma**: {report.lines_removed}",
            f"- **Tahmini tasarruf Token**: ~{report.estimated_token_savings}",
            "",
        ]

        if report.by_type:
            lines.extend(["## Soru türü dağılımı", ""])
            for issue_type, count in sorted(report.by_type.items()):
                lines.append(f"- {issue_type}: {count}")
            lines.append("")

        if report.fixed_files:
            lines.extend(["## Otomatik olarak onarıldı", ""])
            lines.extend([f"- {f}" for f in report.fixed_files])
            lines.append("")

        if report.pending_issues:
            lines.extend(["## Onaylanacak (manuel inceleme gerektirir)", ""])
            for issue in report.pending_issues:
                lines.append(f"### {issue.file_path}")
                lines.append(f"- tip: {issue.issue_type}")
                lines.append(f"- içerik: {issue.content}")
                lines.append(f"- telkin: {issue.fix_suggestion}")
                lines.append("")

        return "\n".join(lines)


# ------------------------------------------------------------------
# CLI Giriş
# ------------------------------------------------------------------


def main():
    """CLI Giriş"""
    import argparse

    parser = argparse.ArgumentParser(description="kod temizleme araçları")
    parser.add_argument("path", nargs="?", default=".", help="Proje yolu")
    parser.add_argument("--strategy", choices=["safe", "aggressive"], default="safe")
    parser.add_argument("--fix", action="store_true", help="Otomatik onarım")
    parser.add_argument("--output", "-o", help="Rapor çıktı yolu")

    args = parser.parse_args()

    # Strateji
    strategy = CleanerStrategy()
    if args.strategy == "aggressive":
        strategy.auto_delete_empty = True
        strategy.dead_code_safe_mode = False

    # Temizlemek
    cleaner = CodeCleaner(Path(args.path), strategy)

    report = cleaner.fix_all_auto() if args.fix else cleaner.scan()

    # Çıktı raporu
    report_md = cleaner.generate_report_md(report)
    print(report_md)

    if args.output:
        Path(args.output).write_text(report_md, encoding="utf-8")
        print(f"\nRapor şuraya kaydedildi:: {args.output}")


if __name__ == "__main__":
    main()
