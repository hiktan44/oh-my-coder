# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

tarayicibaglamhisbil - Browser Context Awareness

araciligiylatarayicigenislet/API almevcutetiketsayfabaglam, destek: 
- almevcutetiketsayfabaslik, URL, icerikalintiister
- arailgilibaglam
- ile AI Agent setol

dikkat: buislevgerekistertarayicigenisletveya Playwright/Selenium destek. 
ne zamanyokolabilirkullantarayicizaman, islevdusurseviyeiciniyizarifbosuygula. 
"""

import asyncio
import os
from dataclasses import dataclass, field


@dataclass
class BrowserContext:
    """
    tarayicibaglam

    depolamamevcuttarayicietiketsayfabilgi. 
    """

    title: str = ""
    url: str = ""
    content: str = ""  # sayfayuzicerikalintiister
    links: list[str] = field(default_factory=list)
    timestamp: str = ""
    available: bool = False  # tarayiciolup olmadigiolabilirkullan

    def to_context_string(self) -> str:
        """olusturbaglamkarakter dizisi"""
        if not self.available:
            return "[tarayicibaglamhayirolabilirkullan]"

        parts = [
            f"baslik: {self.title}",
            f"URL: {self.url}",
        ]

        if self.content:
            parts.append(f"icerikalintiister: {self.content[:500]}")

        if self.links:
            parts.append(f"baglanti ({len(self.links)}): {', '.join(self.links[:10])}")

        return "\n".join(parts)


class BrowserAwareness:
    """
    tarayicihisbilmodul

    araciligiylacokturyontemaltarayicibaglam: 
    1. Playwright (oner, destek Chromium/Chrome/Edge) 
    2. Selenium (hazirlasec, destekcokturtarayici) 
    3. OpenClaw Browser CDP (egervar) 

    ne zamanvaryontemtumhayirolabilirkullanzaman, donusbos BrowserContext. 
    """

    def __init__(self):
        self._playwright = None
        self._selenium = None
        self._cdp_client = None
        self._browser_type = self._detect_browser()

    def _detect_browser(self) -> str:
        """algilamaolabilirkullantarayiciotomatikyontem"""
        # oncelikalgilama OpenClaw Browser CDP
        if os.getenv("OPENCLAW_BROWSER_ENABLED") == "1":
            return "openclaw"

        # algilama Playwright
        try:
            import playwright

            self._playwright = playwright
            return "playwright"
        except ImportError:
            pass

        # algilama Selenium
        try:
            import selenium

            self._selenium = selenium
            return "selenium"
        except ImportError:
            pass

        return "none"

    async def get_current_tab(self) -> BrowserContext:
        """
        almevcuttarayicietiketsayfabaglam

        Returns:
            BrowserContext: mevcutetiketsayfabaglam
        """
        if self._browser_type == "none":
            return BrowserContext(available=False)

        try:
            if self._browser_type == "playwright":
                return await self._get_current_tab_playwright()
            if self._browser_type == "selenium":
                return await self._get_current_tab_selenium()
            if self._browser_type == "openclaw":
                return await self._get_current_tab_openclaw()
        except Exception as e:
            return BrowserContext(
                available=False,
                content=f"[tarayicialbasarisiz: {e}]",
            )

        return BrowserContext(available=False)

    async def _get_current_tab_playwright(self) -> BrowserContext:
        """araciligiyla Playwright almevcutetiketsayfa"""
        from playwright.async_api import async_playwright

        ctx = BrowserContext(available=True)

        async with async_playwright() as p:
            # denebaglabaglanvartarayiciveyabaslatyenitarayici
            browser = None
            try:
                # denebaglabaglan Chrome DevTools Protocol
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            except Exception:
                try:
                    browser = await p.chromium.launch(headless=True)
                except Exception:
                    return BrowserContext(
                        available=False,
                        content="[yokyontembaslat Chromium tarayici]",
                    )

            try:
                page = browser.contexts[0].pages[0] if browser.contexts else None
                if page is None:
                    return BrowserContext(
                        available=False,
                        content="[henuzbulkadartarayicietiketsayfa]",
                    )

                ctx.title = page.title()
                ctx.url = page.url

                # alsayfayuzmetinmetin (basitsurum) 
                try:
                    body_text = await page.inner_text("body")
                    ctx.content = body_text[:1000] if body_text else ""
                except Exception:
                    pass

                # albaglanti
                try:
                    links = await page.query_selector_all("a")
                    ctx.links = [
                        await link.get_attribute("href")
                        for link in links[:20]
                        if await link.get_attribute("href")
                    ]
                except Exception:
                    pass

            finally:
                await browser.close()

        return ctx

    async def _get_current_tab_selenium(self) -> BrowserContext:
        """araciligiyla Selenium almevcutetiketsayfa"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        ctx = BrowserContext(available=True)

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            ctx.title = driver.title
            ctx.url = driver.current_url

            # al body metin
            try:
                body = driver.find_element("tag name", "body")
                ctx.content = body.text[:1000]
            except Exception:
                pass

            # albaglanti
            try:
                links = driver.find_elements("tag name", "a")
                ctx.links = [
                    link.get_attribute("href")
                    for link in links[:20]
                    if link.get_attribute("href")
                ]
            except Exception:
                pass

        finally:
            if driver:
                driver.quit()

        return ctx

    async def _get_current_tab_openclaw(self) -> BrowserContext:
        """araciligiyla OpenClaw Browser CDP almevcutetiketsayfa"""
        import json
        import subprocess

        ctx = BrowserContext(available=True)

        # kullan openclaw browser snapshot komut
        try:
            result = subprocess.run(
                ["openclaw", "browser", "snapshot", "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                ctx.title = data.get("title", "")
                ctx.url = data.get("url", "")
                ctx.content = data.get("text", "")[:1000]
                ctx.links = data.get("links", [])[:20]
        except Exception:
            pass

        return ctx

    async def search_context(self, query: str) -> BrowserContext:
        """
        arailgilibaglam

        icindemevcuttarayicisayfayuzicindearailgiliicerik. 

        Args:
            query: arama anahtar kelimeleri

        Returns:
            BrowserContext: arasonucbaglam
        """
        if self._browser_type == "none":
            return BrowserContext(
                available=False,
                content=f"[ara '{query}' - tarayicihayirolabilirkullan]",
            )

        # icinde Playwright, olabilirileicindesayfayuzicindeyurutara
        if self._browser_type == "playwright":
            return await self._search_in_page_playwright(query)

        return BrowserContext(
            available=False,
            content=f"[ara '{query}' - mevcuttarayicitiphayirdestek]",
        )

    async def _search_in_page_playwright(self, query: str) -> BrowserContext:
        """icinde Playwright sayfayuzicindeara"""
        from playwright.async_api import async_playwright

        ctx = BrowserContext(available=True)
        ctx.content = f"ara '{query}' sonucicindesayfayuzicindegoster"

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = browser.contexts[0].pages[0] if browser.contexts else None

                if page:
                    # icindesayfayuzicindearaeslestirmetin
                    matches = await page.locator(f"text={query}").count()
                    ctx.content = f"icindemevcutsayfayuzbulkadar {matches} yereslestir '{query}'"
                    ctx.url = page.url
                    ctx.title = page.title()
                else:
                    ctx.content = "[henuzbulkadaryasahareketetiketsayfa]"

                await browser.close()
            except Exception as e:
                ctx.content = f"[arabasarisiz: {e}]"

        return ctx

    def to_context_string(self) -> str:
        """olusturbaglamkarakter dizisi (esitlesurum, almevcutetiketsayfa) """
        try:
            asyncio.get_running_loop()
            # icinde async context icindeyokyontemkullan asyncio.run(), donusvarsayilandeger
            return "[tarayicibaglam: lutfenicindeesitleortamicindecagri]"
        except RuntimeError:
            return asyncio.run(self.get_current_tab()).to_context_string()
