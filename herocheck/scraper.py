"""Firecrawl-based web scraping with screenshot support."""

import base64
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx
from firecrawl import FirecrawlApp

MAX_CONTENT_CHARS = 50_000

_firecrawl: FirecrawlApp | None = None


def get_firecrawl() -> FirecrawlApp:
    global _firecrawl
    if _firecrawl is None:
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            print(
                "Fatal: FIRECRAWL_API_KEY environment variable is not set.",
                file=sys.stderr,
            )
            sys.exit(1)
        _firecrawl = FirecrawlApp(api_key=api_key)
    return _firecrawl


@dataclass
class ScrapeResult:
    url: str
    markdown: str | None = None
    screenshot_b64: str | None = None


def scrape_page(url: str, *, screenshot: bool = True) -> ScrapeResult:
    """Scrape a URL via Firecrawl. Returns markdown and optional screenshot."""
    formats = ["markdown"]
    if screenshot:
        formats.append("screenshot")

    try:
        result = get_firecrawl().scrape(url, formats=formats)
        markdown = None
        screenshot_b64 = None

        if result and result.markdown:
            markdown = result.markdown
            if len(markdown) > MAX_CONTENT_CHARS:
                markdown = markdown[:MAX_CONTENT_CHARS]
                print(
                    f"  [WARN] Content truncated to {MAX_CONTENT_CHARS:,} chars",
                    file=sys.stderr,
                )

        if screenshot and result and hasattr(result, "screenshot") and result.screenshot:
            raw = result.screenshot
            if raw.startswith("data:"):
                screenshot_b64 = raw.split(",", 1)[-1]
            elif raw.startswith("http"):
                try:
                    resp = httpx.get(raw, timeout=30)
                    resp.raise_for_status()
                    screenshot_b64 = base64.b64encode(resp.content).decode()
                except Exception as e:
                    print(f"  [WARN] Failed to download screenshot: {e}", file=sys.stderr)
            else:
                screenshot_b64 = raw

        if not markdown:
            print(
                f"  [WARN] Firecrawl returned no markdown for {url}",
                file=sys.stderr,
            )

        return ScrapeResult(url=url, markdown=markdown, screenshot_b64=screenshot_b64)
    except Exception as e:
        print(f"  [WARN] Firecrawl error for {url}: {e}", file=sys.stderr)
        return ScrapeResult(url=url)


def scrape_pages(urls: list[str], *, screenshot: bool = True) -> list[ScrapeResult]:
    """Scrape multiple URLs in parallel."""
    results: list[ScrapeResult] = []
    with ThreadPoolExecutor(max_workers=min(len(urls), 5)) as executor:
        futures = {
            executor.submit(scrape_page, url, screenshot=screenshot): url
            for url in urls
        }
        for future in as_completed(futures):
            results.append(future.result())
    # Preserve input order
    url_order = {url: i for i, url in enumerate(urls)}
    results.sort(key=lambda r: url_order.get(r.url, 0))
    return results
