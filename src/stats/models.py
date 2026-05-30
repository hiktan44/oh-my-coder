# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

dosyaistatistiksonucsayigoremodeltanim. 
"""

from dataclasses import dataclass, field


@dataclass
class FileStats:
    """goretipistatistikdosyabilgi. """

    count: int = 0
    """dosya sayisimiktar"""

    size: int = 0
    """dosyatoplambuyukkucuk (byte) """

    files: list[str] = field(default_factory=list)
    """dosyayolliste (icindeprojekokdizin) """


@dataclass
class StatsResult:
    """dosyaistatistiksonuc. """

    total_files: int = 0
    """toplamdosya sayisi"""

    total_dirs: int = 0
    """toplamdizinsayi"""

    total_size: int = 0
    """toplambuyukkucuk (byte) """

    by_type: dict[str, FileStats] = field(default_factory=dict)
    """goredosyatippuansinifistatistiksonuc"""

    by_directory: dict[str, int] = field(default_factory=dict)
    """goredizinpuansinifdosya sayisimiktar"""

    errors: list[str] = field(default_factory=list)
    """istatistiksurecicindekarsilaskadarhataliste"""

    root_path: str = ""
    """istatistikkokdizin yolu"""

    def to_dict(self) -> dict:
        """istatistiksonucdonusturicinsozluk. 

        Returns:
            olabilirsirasozluk
        """
        return {
            "total_files": self.total_files,
            "total_dirs": self.total_dirs,
            "total_size": self.total_size,
            "total_size_human": self._format_size(self.total_size),
            "by_type": {
                k: {
                    "count": v.count,
                    "size": v.size,
                    "size_human": self._format_size(v.size),
                    "files": v.files,
                }
                for k, v in self.by_type.items()
            },
            "by_directory": self.by_directory,
            "errors": self.errors,
            "root_path": self.root_path,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """bytebuyukkucukformaticinkisisinifolabilirokukarakter dizisi. 

        Args:
            size_bytes: bytebuyukkucuk

        Returns:
            formatsonrabuyukkucukkarakter dizisi, ornegin "1.23 MB"
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def __str__(self) -> str:
        """olusturkisisinifolabilirokuistatistikrapor. """
        lines = []
        lines.append("=" * 50)
        lines.append("📊 projedosyaistatistikrapor")
        lines.append("=" * 50)
        lines.append(f"kokdizin: {self.root_path}")
        lines.append("")
        lines.append(f"📁 toplamdizinsayi: {self.total_dirs}")
        lines.append(f"📄 toplamdosya sayisi: {self.total_files}")
        lines.append(f"💾 toplambuyukkucuk:   {self._format_size(self.total_size)}")
        lines.append("")

        if self.by_type:
            lines.append("📂 goredosyatipistatistik:")
            lines.append(f"{'tip':<25} {'sayimiktar':>8} {'buyukkucuk':>12}")
            lines.append("-" * 47)
            for file_type, stats in self.by_type.items():
                lines.append(
                    f"{file_type:<25} {stats.count:>8} {self._format_size(stats.size):>12}"
                )
            lines.append("")

        if self.by_directory:
            lines.append("📁 goredizinistatistik (Top 20):")
            lines.append(f"{'dizin':<40} {'sayimiktar':>8}")
            lines.append("-" * 48)
            for i, (directory, count) in enumerate(self.by_directory.items()):
                if i >= 20:
                    lines.append(f"{'... (dahacok)':<40}")
                    break
                lines.append(f"{directory:<40} {count:>8}")
            lines.append("")

        if self.errors:
            lines.append(f"⚠️ istatistiksurecicindehata ({len(self.errors)}):")
            for err in self.errors[:5]:
                lines.append(f"  - {err}")
            if len(self.errors) > 5:
                lines.append(f"  ... halavar {len(self.errors) - 5} hata")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)
