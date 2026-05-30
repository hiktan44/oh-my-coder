from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
omc review -kod inceleme komutu

İki inceleme modu desteklenir:
- omc review pr <url>    #gözden geçirmekGitHub PR
- omc review diff <file> #yerel sansürdiffbelge
"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel

from ..core.router import ModelRouter, RouterConfig

app = typer.Typer(help="kod incelemesi-Kod değişikliklerinin akıllı analizi")
console = Console()

#Sistem istemi sözcük yolu
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "review_system.txt"


def _init_router() -> ModelRouter:
    """Model yönlendiriciyi başlat"""
    config = RouterConfig.from_env()
    return ModelRouter(config)


def _check_env() -> bool:
    """Ortam yapılandırmasını kontrol edin"""

    keys = [
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OLLAMA_BASE_URL",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "XAI_API_KEY",
        "ZHIPUAI_API_KEY",
    ]
    if not any(os.getenv(k) for k in keys):
        console.print(
            "[red]❌Hiçbiri tespit edilmediAPI Key, lütfen önce yapılandırın:[/red]\n"
            "  [cyan]omc self-config set deepseek.api_key sk-xxx[/cyan]"
        )
        return False
    return True


def _fetch_pr_diff(pr_url: str) -> tuple[bool, str]:
    """
sürünmekGitHub PR diff

geri dönmek: (başarı, diffiçerik veya hata mesajı)
    """
    import re

    #ayrıştırmakPR URL
    #Biçim: https://github.com/{owner}/{repo}/pull/{number}
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url.strip("/")
    )
    if not match:
        return False, f"GeçersizGitHub PR URL: {pr_url}"

    owner, repo, pr_number = match.groups()

    #kullanmakghkomut edinimidiff
    try:
        result = subprocess.run(
            ["gh", "pr", "diff", pr_number, "--repo", f"{owner}/{repo}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            return True, result.stdout
        #eğerghBaşarısız oldu, kullanmayı deneyincurl
        diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"

        resp = httpx.get(diff_url, timeout=15.0)
        if resp.status_code == 200:
            return True, resp.text
        return False, f"AlınamıyorPR diff: HTTP {resp.status_code}"
    except FileNotFoundError:
        # ghYüklü değil, doğrudan kullanınHTTP
        diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"

        try:
            resp = httpx.get(diff_url, timeout=15.0)
            if resp.status_code == 200:
                return True, resp.text
            return False, f"AlınamıyorPR diff: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Ağ isteği başarısız oldu: {e}"
    except subprocess.TimeoutExpired:
        return False, "Elde etmekPR diffzaman aşımı"
    except Exception as e:
        return False, f"Alınamadı: {e}"


def _read_local_diff(diff_file: str) -> tuple[bool, str]:
    """
Yerel okudiffbelge

geri dönmek: (başarı, diffiçerik veya hata mesajı)
    """
    diff_path = Path(diff_file)

    #Bu bir dosya yoluysa ve mevcutsa dosyayı okuyun
    if diff_path.exists() and diff_path.is_file():
        try:
            content = diff_path.read_text(encoding="utf-8")
            return True, content
        except Exception as e:
            return False, f"Dosya okunamadı: {e}"

    #Aksi halde şu şekilde deneyin:git diffParametre yürütme
    try:
        result = subprocess.run(
            ["git", "diff", diff_file],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout
        # git diffBaşarısızlık, hata mesajı döndür
        return False, f"git diffhata: {result.stderr}"
    except Exception as e:
        return False, f"uygulamakgit diffhata: {e}"


def _load_system_prompt() -> str:
    """Sistem istemi sözcüklerini yükle"""
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    #ipucu kelimesi
    return """Kıdemli bir kod inceleme uzmanısınız. Lütfen kod değişikliklerini önem derecesine göre sıralanmış şekilde inceleyin (yüksek/orta/Düşük) sorunu kategorilere ayırır ve düzeltme önerileri sunar."""


async def _review_with_llm(diff_content: str, model_name: str = "deepseek") -> str:
    """
kullanmakLLManaliz etmekdiffiçerik

geri dönmek:inceleme raporu
    """
    router = _init_router()
    system_prompt = _load_system_prompt()

    #Mesaj oluştur
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Lütfen aşağıdaki kod değişikliklerini inceleyin:\n\n```\n{diff_content}\n```",
        },
    ]

    #çağrı modeli
    try:
        response = await router.complete(
            messages=messages,
            task_type="code_review",
            model_override=model_name,
        )
        return response.content
    except Exception as e:
        return f"❌ LLMçağrı başarısız oldu: {type(e).__name__}: {e}"


@app.command("pr")
def review_pr(
    pr_url: str = typer.Argument(..., help="GitHub PR URL"),
    model: str = typer.Option("deepseek", "--model", "-m", help="Kullanılan model"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Raporu dosyaya kaydet"
    ),
) -> None:
    """
gözden geçirmekGitHub PRiçerik

    Examples:
        omc review pr https://github.com/user/repo/pull/123
        omc review pr https://github.com/user/repo/pull/456 --model gpt4
    """
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]🔍kod incelemesi[/bold cyan]\n"
            f"PR: [yellow]{pr_url}[/yellow]\n"
            f"Modeli: [dim]{model}[/dim]",
            title="📋 PR Review",
        )
    )

    #Elde etmekdiff
    console.print("\n[bold]📥Elde etmekPR diff...[/bold]")
    success, diff = _fetch_pr_diff(pr_url)
    if not success:
        console.print(f"[red]❌ {diff}[/red]")
        raise typer.Exit(1)

    if not diff.strip():
        console.print("[yellow]⚠️ PRDeğişiklik yok[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]✓Elde etmek{len(diff.splitlines())}TAMAMdiff[/green]")

    #AramaLLManaliz etmek
    console.print("\n[bold]🤖Analiz ediliyor...[/bold]")

    try:
        report = asyncio.run(_review_with_llm(diff, model))
    except Exception as e:
        console.print(f"[red]❌Analiz başarısız oldu: {e}[/red]")
        raise typer.Exit(1)

    #Çıktı raporu
    console.print("\n" + "=" * 80)
    console.print(report)
    console.print("=" * 80)

    #dosyaya kaydet
    if output:
        output.write_text(report, encoding="utf-8")
        console.print(f"\n[green]✓Rapor şuraya kaydedildi::[/green] [dim]{output}[/dim]")


@app.command("diff")
def review_diff(
    diff_file: str = typer.Argument(..., help="diffdosya yolu veyagit diffparametre"),
    model: str = typer.Option("deepseek", "--model", "-m", help="Kullanılan model"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Raporu dosyaya kaydet"
    ),
) -> None:
    """
Yerel kodu inceleyindiff

    Examples:
        omc review diff changes.diff
        omc review diff HEAD~1
        omc review diff --cached
    """
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]🔍kod incelemesi[/bold cyan]\n"
            f"Diff: [yellow]{diff_file}[/yellow]\n"
            f"Modeli: [dim]{model}[/dim]",
            title="📋 Diff Review",
        )
    )

    #Okumakdiff
    console.print("\n[bold]📥Okumakdiff...[/bold]")
    success, diff = _read_local_diff(diff_file)
    if not success:
        console.print(f"[red]❌ {diff}[/red]")
        raise typer.Exit(1)

    if not diff.strip():
        console.print("[yellow]⚠️Değişiklik yok[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]✓Okumak{len(diff.splitlines())}TAMAMdiff[/green]")

    #AramaLLManaliz etmek
    console.print("\n[bold]🤖Analiz ediliyor...[/bold]")

    try:
        report = asyncio.run(_review_with_llm(diff, model))
    except Exception as e:
        console.print(f"[red]❌Analiz başarısız oldu: {e}[/red]")
        raise typer.Exit(1)

    #Çıktı raporu
    console.print("\n" + "=" * 80)
    console.print(report)
    console.print("=" * 80)

    #dosyaya kaydet
    if output:
        output.write_text(report, encoding="utf-8")
        console.print(f"\n[green]✓Rapor şuraya kaydedildi::[/green] [dim]{output}[/dim]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Yardımı varsayılan olarak göster"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
