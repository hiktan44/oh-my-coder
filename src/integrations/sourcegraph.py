# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Sourcegraph setolmodul - ortakac API istemci

kullan Sourcegraph ortakac streaming API, yokgerek API Key. 
destekkodara, dosyaal, depokutuphaneara. 

API dokumantasyon: https://sourcegraph.com/docs/api
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

# =============================================================================
# yapilandirma
# =============================================================================

SG_API_BASE = "https://sourcegraph.com/.api"
SG_CACHE_DIR = Path.home() / ".omc" / "cache" / "sourcegraph"
SG_CACHE_TTL = 300  # 5 puandakikaonbellek


# =============================================================================
# sayigoremodel
# =============================================================================


@dataclass
class SearchMatch:
    """tekilarasonuc"""

    repo: str
    file_path: str
    line_number: int = 0
    line_content: str = ""
    language: str = ""
    repository_stars: int = 0
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content,
            "language": self.language,
            "repository_stars": self.repository_stars,
            "url": self.url,
        }


@dataclass
class FileContent:
    """dosyaiceriksonuc"""

    repo: str
    path: str
    content: str
    language: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "path": self.path,
            "content": self.content,
            "language": self.language,
            "url": self.url,
        }


@dataclass
class RepoInfo:
    """depokutuphanebilgi"""

    name: str
    description: str = ""
    stars: int = 0
    language: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "stars": self.stars,
            "language": self.language,
            "url": self.url,
        }


@dataclass
class SearchResult:
    """arasonuc"""

    query: str
    total: int
    matches: list[SearchMatch]
    elapsed_ms: float = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "total": self.total,
            "elapsed_ms": self.elapsed_ms,
            "matches": [m.to_dict() for m in self.matches],
            "warnings": self.warnings,
        }


# =============================================================================
# Sourcegraph Client
# =============================================================================


class SourcegraphClient:
    """
    Sourcegraph ortakac API istemci

    kullan streaming API, yokgerek API Key. 

    ornek:
        client = SourcegraphClient()
        result = client.search("func main() lang:go", limit=10)
        for match in result.matches:
            print(f"{match.repo}:{match.file_path}:{match.line_number}")
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl: int = SG_CACHE_TTL,
        timeout: float = 30.0,
    ):
        self.cache_dir = cache_dir or SG_CACHE_DIR
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """al HTTP istemci"""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "omc-sourcegraph-client/1.0",
                },
            )
        return self._client

    def _cache_get(self, key: str) -> Optional[Any]:
        """onbellekalsayigore"""
        if not self.cache_dir.exists():
            return None

        cache_file = self.cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < self.cache_ttl:
                return data.get("value")
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        """ayarlaayaronbellek"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
        cache_file.write_text(
            json.dumps({"timestamp": time.time(), "value": value}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _build_search_query(
        self,
        query: str,
        repo_filter: Optional[str] = None,
        lang: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """olusturarasorgu"""
        parts = [query]
        if repo_filter:
            parts.append(f"repo:{repo_filter}")
        if lang:
            parts.append(f"lang:{lang}")
        parts.append(f"count:{limit}")
        return " ".join(parts)

    def search(
        self,
        query: str,
        repo_filter: Optional[str] = None,
        lang: Optional[str] = None,
        limit: int = 20,
        use_cache: bool = True,
    ) -> SearchResult:
        """
        arakod

        Args:
            query: arama anahtar kelimeleriveya Sourcegraph sorgudilyontem
            repo_filter: depokutuphanefiltrele, destek glob modornegin "github.com/golang/*"
            lang: dilfiltrele, ornegin "go", "python", "typescript"
            limit: donussonucsayimiktar
            use_cache: olup olmadigikullanonbellek

        Returns:
            SearchResult icerireslestirliste
        """
        full_query = self._build_search_query(query, repo_filter, lang, limit)
        cache_key = f"search:{full_query}"

        # kontrolonbellek
        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                matches = [SearchMatch(**m) for m in cached.get("matches", [])]
                return SearchResult(
                    query=query,
                    total=cached.get("total", len(matches)),
                    matches=matches,
                    elapsed_ms=0,
                    warnings=["from cache"],
                )

        # cagri streaming API
        url = f"{SG_API_BASE}/search/stream"
        client = self._get_client()

        start_time = time.time()
        matches: list[SearchMatch] = []
        warnings: list[str] = []

        try:
            # streaming API kullan POST
            with client.stream(
                "POST",
                url,
                content=full_query,
                headers={"Content-Type": "text/plain"},
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line.strip():
                        continue

                    # ayristir streaming format
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            match = self._parse_search_result(data)
                            if match:
                                matches.append(match)
                                if len(matches) >= limit:
                                    break
                        except json.JSONDecodeError:
                            continue
                    elif line.startswith("error: "):
                        warnings.append(line[7:])

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                warnings.append("API sinirakis, lutfenbirazsonrayeniden dene")
            elif e.response.status_code == 401:
                warnings.append("gerekisterkimlik dogrulama (ortakac API hayirolmalisu anbuhata) ")
            else:
                warnings.append(f"HTTP hata: {e.response.status_code}")
        except httpx.TimeoutException:
            warnings.append("istekasirizaman")
        except Exception as e:
            warnings.append(f"istek başarısız: {e}")

        elapsed = (time.time() - start_time) * 1000

        result = SearchResult(
            query=query,
            total=len(matches),
            matches=matches,
            elapsed_ms=elapsed,
            warnings=warnings,
        )

        # onbelleksonuc
        if use_cache and matches:
            self._cache_set(cache_key, result.to_dict())

        return result

    def _parse_search_result(self, data: dict[str, Any]) -> Optional[SearchMatch]:
        """ayristirarasonuc"""
        # streaming API donusformatolabiliredebilirdircokturtip
        result_type = data.get("__typename") or data.get("type")

        if result_type == "FileMatch" or "file" in data:
            repo_info = data.get("repository", {})
            file_info = data.get("file", {})
            line_matches = data.get("lineMatches", [])

            if line_matches:
                first_line = line_matches[0]
                return SearchMatch(
                    repo=repo_info.get("name", ""),
                    file_path=file_info.get("path", ""),
                    line_number=first_line.get("lineNumber", 0)
                    + 1,  # 0-indexed to 1-indexed
                    line_content=first_line.get("preview", ""),
                    language=file_info.get("language", ""),
                    repository_stars=repo_info.get("stars", {}).get("totalCount", 0)
                    if isinstance(repo_info.get("stars"), dict)
                    else repo_info.get("stars", 0),
                    url=f"https://sourcegraph.com/{repo_info.get('name', '')}/-/{file_info.get('path', '')}",
                )
            else:
                return SearchMatch(
                    repo=repo_info.get("name", ""),
                    file_path=file_info.get("path", ""),
                    url=f"https://sourcegraph.com/{repo_info.get('name', '')}/-/{file_info.get('path', '')}",
                )

        # uyumluonunoformat
        if "repository" in data and "path" in data:
            return SearchMatch(
                repo=data.get("repository", ""),
                file_path=data.get("path", ""),
                line_number=data.get("line", 0),
                line_content=data.get("content", ""),
                url=data.get("url", ""),
            )

        return None

    def get_file(
        self,
        repo: str,
        path: str,
        use_cache: bool = True,
    ) -> Optional[FileContent]:
        """
        aldosyaicerik

        Args:
            repo: depokutuphaneisim, ornegin "github.com/golang/go"
            path: dosyayol, ornegin "src/runtime/proc.go"
            use_cache: olup olmadigikullanonbellek

        Returns:
            FileContent veya None
        """
        cache_key = f"file:{repo}:{path}"

        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                return FileContent(**cached)

        url = f"{SG_API_BASE}/repos/{repo}/-/raw/{path}"
        client = self._get_client()

        try:
            response = client.get(url)
            response.raise_for_status()
            content = response.text

            # cikarimdil
            lang = self._infer_language(path)

            result = FileContent(
                repo=repo,
                path=path,
                content=content,
                language=lang,
                url=f"https://sourcegraph.com/{repo}/-/{path}",
            )

            if use_cache:
                self._cache_set(cache_key, result.to_dict())

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception:
            return None

    def list_repos(
        self,
        query: str,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[RepoInfo]:
        """
        aradepokutuphane

        Args:
            query: arama anahtar kelimeleri
            limit: donussayimiktar
            use_cache: olup olmadigikullanonbellek

        Returns:
            RepoInfo liste
        """
        cache_key = f"repos:{query}:{limit}"

        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                return [RepoInfo(**r) for r in cached]

        # kullanara API  type:repo filtrele
        search_query = f"type:repo {query} count:{limit}"
        url = f"{SG_API_BASE}/search/stream"
        client = self._get_client()

        repos: list[RepoInfo] = []

        try:
            with client.stream(
                "POST",
                url,
                content=search_query,
                headers={"Content-Type": "text/plain"},
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line.strip() or not line.startswith("data: "):
                        continue

                    try:
                        data = json.loads(line[6:])
                        if data.get("__typename") == "Repository" or "name" in data:
                            repo = RepoInfo(
                                name=data.get("name", ""),
                                description=data.get("description", ""),
                                stars=data.get("stars", {}).get("totalCount", 0)
                                if isinstance(data.get("stars"), dict)
                                else data.get("stars", 0),
                                language=data.get("primaryLanguage", {}).get("name", "")
                                if isinstance(data.get("primaryLanguage"), dict)
                                else "",
                                url=f"https://sourcegraph.com/{data.get('name', '')}",
                            )
                            repos.append(repo)
                            if len(repos) >= limit:
                                break
                    except json.JSONDecodeError:
                        continue

        except Exception:
            pass

        if use_cache and repos:
            self._cache_set(cache_key, [r.to_dict() for r in repos])

        return repos

    def _infer_language(self, path: str) -> str:
        """dosyagenisletisimcikarimdil"""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".kt": "Kotlin",
            ".swift": "Swift",
            ".c": "C",
            ".cpp": "C++",
            ".cc": "C++",
            ".h": "C",
            ".hpp": "C++",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".scala": "Scala",
            ".clj": "Clojure",
            ".ex": "Elixir",
            ".erl": "Erlang",
            ".hs": "Haskell",
            ".ml": "OCaml",
            ".fs": "F#",
            ".vue": "Vue",
            ".svelte": "Svelte",
            ".sh": "Shell",
            ".bash": "Shell",
            ".zsh": "Shell",
            ".ps1": "PowerShell",
            ".lua": "Lua",
            ".r": "R",
            ".m": "MATLAB",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".less": "Less",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".xml": "XML",
            ".toml": "TOML",
            ".md": "Markdown",
            ".rst": "reStructuredText",
        }
        ext = Path(path).suffix.lower()
        return ext_map.get(ext, "")

    def close(self) -> None:
        """kapatistemci"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> SourcegraphClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# =============================================================================
# kullanislifonksiyon
# =============================================================================


def search(
    query: str,
    repo: Optional[str] = None,
    lang: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """
    hizlihizliarafonksiyon

    ornek:
        result = search("http.Client", lang="go", limit=5)
        for m in result.matches:
            print(f"{m.repo}:{m.file_path}:{m.line_number}")
    """
    with SourcegraphClient() as client:
        return client.search(query, repo_filter=repo, lang=lang, limit=limit)


def get_file(repo: str, path: str) -> Optional[FileContent]:
    """hizlihizlialdosyaicerik"""
    with SourcegraphClient() as client:
        return client.get_file(repo, path)


def list_repos(query: str, limit: int = 10) -> list[RepoInfo]:
    """hizlihizliaradepokutuphane"""
    with SourcegraphClient() as client:
        return client.list_repos(query, limit=limit)
