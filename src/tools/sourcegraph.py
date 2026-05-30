from __future__ import annotations

"""
Sourcegraph setol - izin ver AI edebiliraraortakackodkutuphane

destekikiturmod: 
1. Sourcegraph API (gerekister API Key, ucretsiz tier yeterliyeterligunsikkullan) 
2. src CLI (yerelkurulum, yokgerek API Key) 

Dokumantasyon:https://sourcegraph.com/docs
ucretsiz API Key: https://sourcegraph.com/user/settings/tokens
"""


import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

# =============================================================================
# yapilandirma
# =============================================================================

SG_API_KEY = os.getenv("SOURCEGRAPH_API_KEY", "")
SG_ENDPOINT = os.getenv("SOURCEGRAPH_ENDPOINT", "https://sourcegraph.com/.api")
SG_CLI_PATH = os.getenv("SRC_CLI_PATH", "src")  # src veyatamyol

# src CLI kurulum: brew install sourcegraph/tap/src
SRC_CLI_INSTALL_CMD = "brew install sourcegraph/tap/src"

# =============================================================================
# sayigoremodel
# =============================================================================


@dataclass
class SearchMatch:
    """tekilarasonuc"""

    repo: str
    file_path: str
    repository_stars: int = 0
    repo_description: str = ""
    content_preview: str = ""  # eslestirsatirbaglam
    line_number: int = 0
    language: str = ""
    url: str = ""
    symbols: list[str] = field(default_factory=list)  # fonksiyon/sinifisim

    def format_code(self) -> str:
        """formatkodparca"""
        lines = [f"[{self.repo}:{self.file_path}:{self.line_number}]"]
        if self.symbols:
            lines.append(f"  # tanim: {', '.join(self.symbols[:3])}")
        if self.content_preview:
            for line in self.content_preview.splitlines()[:8]:
                lines.append(f"  {line}")
        return "\n".join(lines)


@dataclass
class SearchResult:
    """tamarasonuc"""

    query: str
    total_matches: int
    matches: list[SearchMatch]
    elapsed_ms: int
    source: str  # "api" | "cli"
    warnings: list[str] = field(default_factory=list)

    def format_table(self, limit: int = 10) -> str:
        """formattablocikti"""
        lines = [
            f"[cyan]Query:[/] {self.query}  "
            f"[green]Matches:[/] {self.total_matches}  "
            f"[dim]Time:[/] {self.elapsed_ms}ms  "
            f"[dim]Source:[/] {self.source}"
        ]
        if self.warnings:
            for w in self.warnings:
                lines.append(f"[yellow]⚠ {w}[/yellow]")
        lines.append("")
        for i, m in enumerate(self.matches[:limit], 1):
            stars = f"⭐{m.repository_stars}" if m.repository_stars else ""
            lang = f"[blue]{m.language}[/blue]" if m.language else ""
            lines.append(
                f"  {i}. [green]{m.repo}[/green]{stars} {m.file_path}:{m.line_number} {lang}"
            )
            if m.symbols:
                lines.append(f"     └─ {' | '.join(m.symbols[:3])}")
            if m.content_preview:
                for ln in m.content_preview.splitlines()[:3]:
                    lines.append(f"     {ln[:120]}")
        if len(self.matches) > limit:
            lines.append(
                f"\n  [dim]... halavar {len(self.matches) - limit} sonuc, kullan --limit ayartam[/dim]"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        """JSON cikti"""
        return json.dumps(
            {
                "query": self.query,
                "total": self.total_matches,
                "elapsed_ms": self.elapsed_ms,
                "source": self.source,
                "matches": [
                    {
                        "repo": m.repo,
                        "file": m.file_path,
                        "line": m.line_number,
                        "language": m.language,
                        "stars": m.repository_stars,
                        "symbols": m.symbols,
                        "preview": m.content_preview[:200],
                        "url": m.url,
                    }
                    for m in self.matches
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    def format_code(self, limit: int = 5) -> str:
        """AI arkadasiyikodcikti"""
        lines = [f"# Search: {self.query} ({self.total_matches} matches)\n"]
        for m in self.matches[:limit]:
            lines.append(m.format_code())
            lines.append("")
        return "\n".join(lines)


# =============================================================================
# Sourcegraph API istemci
# =============================================================================


def _sg_api_search(query: str, **kwargs: Any) -> Optional[SearchResult]:
    """araciligiyla Sourcegraph API ara"""
    if not SG_API_KEY:
        return None

    # olustur GraphQL sorgu
    variables = {
        "query": query,
        "first": min(kwargs.get("limit", 20), 100),
    }
    if kwargs.get("repo"):
        variables["query"] = f"{query} repo:{kwargs['repo']}"
    if kwargs.get("language"):
        variables["query"] = f"{query} lang:{kwargs['language']}"
    if kwargs.get("after"):
        variables["query"] = f"{variables['query']} after:{kwargs['after']}"
    if kwargs.get("before"):
        variables["query"] = f"{variables['query']} before:{kwargs['before']}"

    gql_query = """
    query Search($query: String!, $first: Int!) {
        search(query: $query, version: V3) {
            results {
                matchCount
                timedOut { timedOut }
                __typename
                ... on SearchConnection {
                    results {
                        __typename
                        ... on Repository {
                            name
                            url
                            stars { totalCount }
                            description
                        }
                        ... on FileMatch {
                            repository { name url stars { totalCount } description }
                            file { path url }
                            lineMatches {
                                preview
                                lineNumber
                                offsetAndLengths { offset length }
                            }
                            symbols {
                                name
                                kind
                                containerName
                                url
                            }
                        }
                    }
                }
            }
            elapsedMilliseconds
        }
    }
    """

    body = {"query": gql_query, "variables": variables}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {SG_API_KEY}",
    }

    try:
        resp = httpx.post(
            f"{SG_ENDPOINT}/graphql",
            json=body,
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="api",
            warnings=[f"API hata: {e.response.status_code}"],
        )
    except Exception as e:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="api",
            warnings=[f"baglabaglanbasarisiz: {e}"],
        )

    search_data = data.get("data", {}).get("search", {})
    results_conn = search_data.get("results", {})
    raw_results = results_conn.get("results", [])
    elapsed = search_data.get("elapsedMilliseconds", 0)

    matches: list[SearchMatch] = []
    total = 0

    for item in raw_results:
        typename = item.get("__typename", "")
        if typename == "Repository":
            continue  # atlasafdepokutuphanesonuc
        if typename == "FileMatch":
            repo_info = item.get("repository", {})
            file_info = item.get("file", {})
            repo_name = repo_info.get("name", "")
            file_path = file_info.get("path", "")

            for lm in item.get("lineMatches", []):
                [
                    (
                        f"{s['containerName']}.{s['name']}"
                        if s.get("containerName")
                        else s.get("name", "")
                    )
                    for s in item.get("symbols", [])
                    if s.get("name")
                ]
                match = SearchMatch(
                    repo=repo_name,
                    file_path=file_path,
                    repository_stars=repo_info.get("stars", {}).get("totalCount", 0),
                    repo_description=repo_info.get("description", ""),
                    content_preview=lm.get("preview", ""),
                    line_number=lm.get("lineNumber", 0),
                    url=f"https://sourcegraph.com/{repo_name}/-{file_path}",
                )
                matches.append(match)

    # tahmin total
    match_count = results_conn.get("matchCount", 0)
    if isinstance(match_count, int):
        total = match_count

    return SearchResult(
        query=query,
        total_matches=total,
        matches=matches,
        elapsed_ms=int(elapsed),
        source="api",
    )


# =============================================================================
# src CLI istemci
# =============================================================================


def _check_src_cli() -> bool:
    """kontrol src CLI olup olmadigiolabilirkullan"""
    try:
        result = subprocess.run(
            [SG_CLI_PATH, "version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _src_cli_search(query: str, **kwargs: Any) -> Optional[SearchResult]:
    """araciligiyla src CLI ara"""
    if not _check_src_cli():
        return None

    cmd = [SG_CLI_PATH, "search", "-json", "-limit", str(kwargs.get("limit", 20))]
    if kwargs.get("language"):
        cmd.extend(["-pattern", f"lang:{kwargs['language']}"])
    if kwargs.get("repo"):
        cmd.extend(["-pattern", f"repo:{kwargs['repo']}"])

    cmd.append(query)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
            env={**os.environ, "SRC_ENDPOINT": SG_ENDPOINT},
        )
        if result.returncode != 0:
            return SearchResult(
                query=query,
                total_matches=0,
                matches=[],
                elapsed_ms=0,
                source="cli",
                warnings=[result.stderr.decode().strip()[:200]],
            )
        output = result.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="cli",
            warnings=[f"src CLI hata: {e}"],
        )

    matches: list[SearchMatch] = []
    try:
        for line in output.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("type") == "content":
                match = SearchMatch(
                    repo=item.get("repo", ""),
                    file_path=item.get("path", ""),
                    content_preview=item.get("content", {}).get("preview", ""),
                    line_number=item.get("line", 0),
                    language=item.get("language", ""),
                    url=item.get("url", ""),
                )
                matches.append(match)
            elif item.get("type") == "symbol":
                # sembolnoarasonuc
                context = item.get("context", {})
                match = SearchMatch(
                    repo=item.get("repo", ""),
                    file_path=context.get("file", {}).get("path", ""),
                    content_preview=item.get("symbol", {}).get("name", ""),
                    symbols=[item.get("symbol", {}).get("name", "")],
                    url=item.get("url", ""),
                )
                matches.append(match)
    except json.JSONDecodeError:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="cli",
            warnings=["src CLI ciktiayristirma basarisiz"],
        )

    return SearchResult(
        query=query,
        total_matches=len(matches),
        matches=matches,
        elapsed_ms=0,
        source="cli",
    )


# =============================================================================
# anaarafonksiyon
# =============================================================================


def search(
    query: str,
    language: Optional[str] = None,
    repo: Optional[str] = None,
    limit: int = 20,
    after: Optional[str] = None,
    before: Optional[str] = None,
    prefer_api: bool = True,
) -> SearchResult:
    """
    arakod. otomatiksecsecolabilirkullansonrauc: 
    1. Sourcegraph API (var API Key) 
    2. src CLI (yerelkurulum) 
    """
    kwargs: dict[str, Any] = {
        "limit": limit,
        "language": language,
        "repo": repo,
        "after": after,
        "before": before,
    }

    # oncelik API
    if prefer_api and SG_API_KEY:
        result = _sg_api_search(query, **kwargs)
        if result:
            return result

    # gerigerikadar CLI
    result = _src_cli_search(query, **kwargs)
    if result:
        return result

    # yedek: donusarkadasiyihata mesaji
    return SearchResult(
        query=query,
        total_matches=0,
        matches=[],
        elapsed_ms=0,
        source="none",
        warnings=[
            "Sourcegraph API Key henuzayarlaayar (SOURCEGRAPH_API_KEY) ",
            "src CLI ayricakurulu degil",
            f"kurulum src CLI: {SRC_CLI_INSTALL_CMD}",
            "veyaal API Key: https://sourcegraph.com/user/settings/tokens",
        ],
    )


def install_src_cli() -> tuple[bool, str]:
    """kurulum src CLI, donus (basarili, mesaj)"""
    import platform

    system = platform.system()
    if system == "Darwin":
        cmd = ["brew", "install", "sourcegraph/tap/src"]
    elif system == "Linux":
        cmd = ["sh", "-c", "curl -L https://sourcegraph.com/.api/src-cli.sh | sh"]
    elif system == "Windows":
        cmd = ["scoop", "install", "src"]
    else:
        return False, f"hayirdesteksistem: {system}"

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0:
            return True, "src CLI kurulumbasarili"
        stderr = result.stderr.decode(errors="replace")
        return False, f"kurulumbasarisiz: {stderr[:200]}"
    except Exception as e:
        return False, f"kurulumfarklisik: {e}"


def setup_api_key(api_key: str) -> tuple[bool, str]:
    """yapilandirma Sourcegraph API Key"""

    if not api_key:
        return False, "API Key hayiredebiliricinbos"

    # yazgiris .env dosya
    env_file = Path.home() / ".omc" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)

    content = env_file.read_text(errors="replace") if env_file.exists() else ""
    lines = content.splitlines()
    # degistirveyaizleekle
    found = False
    new_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("SOURCEGRAPH_API_KEY"):
            new_lines.append(f"SOURCEGRAPH_API_KEY={api_key}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"SOURCEGRAPH_API_KEY={api_key}")

    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True, f"kaydetkadar {env_file}"


def check_status() -> dict[str, Any]:
    """kontrolhersonraucdurum"""
    has_api = bool(SG_API_KEY)
    has_cli = _check_src_cli()

    return {
        "api": {
            "available": has_api,
            "endpoint": SG_ENDPOINT if has_api else None,
            "key_prefix": f"{SG_API_KEY[:4]}..." if has_api else None,
        },
        "cli": {
            "available": has_cli,
            "path": SG_CLI_PATH,
        },
        "recommendation": "api" if has_api else ("cli" if has_cli else "none"),
    }
