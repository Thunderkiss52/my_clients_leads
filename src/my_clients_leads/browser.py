from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin


def import_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required. Install it with 'pip install playwright' and run 'playwright install chromium'."
        ) from exc
    return sync_playwright


def first_locator_text(page: Any, selectors: list[str]) -> str:
    from .text import clean_text

    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() > 0:
                text = clean_text(locator.inner_text(timeout=1500))
                if text:
                    return text
        except Exception:
            continue
    return ""


def first_locator_href(page: Any, selectors: list[str], *, exclude_domains: set[str] | None = None) -> str:
    from .text import extract_domain, normalize_website, root_domain

    excluded = exclude_domains or set()
    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
        except Exception:
            continue
        for index in range(count):
            try:
                href = locator.nth(index).get_attribute("href", timeout=1500)
            except Exception:
                continue
            if not href:
                continue
            normalized = normalize_website(href) if href.startswith("www.") else href
            domain = root_domain(extract_domain(normalized))
            if domain and domain not in excluded:
                return normalized
    return ""


def collect_hrefs(
    page: Any,
    selectors: list[str],
    *,
    base_url: str,
    href_substring: str,
    limit: int,
) -> list[str]:
    hrefs: list[str] = []
    seen: set[str] = set()

    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
        except Exception:
            continue
        for index in range(count):
            try:
                href = locator.nth(index).get_attribute("href", timeout=1500)
            except Exception:
                continue
            if not href or href_substring not in href:
                continue
            full_url = urljoin(base_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            hrefs.append(full_url)
            if len(hrefs) >= limit:
                return hrefs

    try:
        html = page.content()
    except Exception:
        html = ""
    if html:
        pattern = re.compile(r'href=["\']([^"\']*%s[^"\']*)["\']' % re.escape(href_substring), flags=re.IGNORECASE)
        for match in pattern.findall(html):
            full_url = urljoin(base_url, match)
            if full_url in seen:
                continue
            seen.add(full_url)
            hrefs.append(full_url)
            if len(hrefs) >= limit:
                break

    return hrefs


def try_click(page: Any, selectors: list[str]) -> None:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() > 0:
                locator.click(timeout=1500)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def scroll_results(page: Any, *, steps: int, pause_ms: int = 1200) -> None:
    for _ in range(steps):
        for selector in ["div[role='feed']", "[class*='scroll__container']", "body"]:
            try:
                page.locator(selector).evaluate("(el) => { el.scrollTop = el.scrollHeight; }")
            except Exception:
                continue
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
            pass
        try:
            page.mouse.wheel(0, 3000)
        except Exception:
            pass
        page.wait_for_timeout(pause_ms)
