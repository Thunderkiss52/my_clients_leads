from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote

from .browser import collect_hrefs, first_locator_href, first_locator_text, import_playwright, scroll_results
from .http import request_bytes
from .models import BrowserOptions, LeadRow
from .snapshots import snapshot_path, write_snapshot
from .text import assign_social_link, clean_text, extract_first_match, normalize_phone, normalize_website

LOGGER = logging.getLogger("my_clients_leads")


def extract_yandex_org_id(url: str) -> str:
    match = re.search(r"/org/(\d+)", url)
    return match.group(1) if match else ""


def parse_yandex_org_html(html: str, *, url: str, query: str, name_hint: str = "") -> LeadRow:
    website = extract_first_match(r'itemprop="url"[^>]+href="([^"]+)"', html)
    phone = extract_first_match(r'itemprop="telephone"[^>]*>([^<]+)<', html)
    address = extract_first_match(r'"address":"([^"]+)"', html)
    hours = extract_first_match(r'business-card-working-status-view__text"[^>]*title="([^"]+)"', html)
    if not hours:
        hours = extract_first_match(r'business-card-working-status-view__text"[^>]*>([^<]+)<', html)

    meta_title = extract_first_match(r'"meta":\{"title":"([^"]+?)\s+—\s+Yandex', html)
    name = name_hint
    if not name:
        name = extract_first_match(r"<h1[^>]*>(.*?)</h1>", html)
    if not name:
        name = extract_first_match(r'"name":"([^"]+)"', html)
    if not name and meta_title:
        name = clean_text(meta_title.split(",")[0])

    category = ""
    if meta_title and "," in meta_title:
        parts = [clean_text(part) for part in meta_title.split(",")]
        if len(parts) >= 2:
            category = parts[1]

    row = LeadRow(
        source="yandex_maps_scrape",
        query=query,
        name=name,
        source_url=url,
        address=address,
        phone=phone,
        website=website,
        hours=hours,
        category=category,
        yandex_id=extract_yandex_org_id(url),
    )

    social_matches = re.findall(
        r'itemprop="sameAs"[^>]+href="([^"]+)"[^>]+aria-label="Social networks,\s*([^"]+)"',
        html,
        flags=re.IGNORECASE,
    )
    for social_url, _social_name in social_matches:
        assign_social_link(row, social_url)

    row.phone = normalize_phone(row.phone)
    row.website = normalize_website(row.website) if row.website else ""
    if row.website:
        row.website_source = "yandex_maps_scrape"
    return row


def scrape_yandex_maps_place(context: Any, url: str, *, query: str, timeout_ms: int, snapshot_dir: str = "") -> LeadRow:
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2500)
        html = page.content()
        write_snapshot(
            snapshot_path(snapshot_dir, bucket="yandex_org", label=extract_yandex_org_id(url) or url),
            html,
        )
        name_hint = first_locator_text(page, ["h1", "[class*='card-title-view__title']", "[class*='business-title']"])
        row = parse_yandex_org_html(html, url=url, query=query, name_hint=name_hint)
        if not row.website:
            row.website = first_locator_href(
                page,
                ["a[itemprop='url']", ".business-urls-view__link", "a[href^='http']", "a[rel='noopener noreferrer']"],
                exclude_domains={"yandex.com", "yandex.ru"},
            )
            row.website = normalize_website(row.website) if row.website else ""
            if row.website:
                row.website_source = "yandex_maps_scrape"
        if not row.phone:
            row.phone = normalize_phone(first_locator_text(page, ["[itemprop='telephone']", "a[href^='tel:']"]))
        if not row.address:
            row.address = first_locator_text(
                page,
                [
                    "[itemprop='address']",
                    "[class*='business-contacts-view__address-link']",
                    "[class*='card-contacts-view__address']",
                    "[class*='card-subtitle-view']",
                ],
            )
        return row
    finally:
        page.close()


def scrape_yandex_org_urls(urls: list[str], *, timeout: float) -> list[LeadRow]:
    rows: list[LeadRow] = []
    for url in urls:
        html_bytes = request_bytes(url, timeout=timeout, max_bytes=2_000_000)
        html = html_bytes.decode("utf-8", errors="ignore")
        rows.append(parse_yandex_org_html(html, url=url, query=url))
    return rows


def collect_yandex_result_urls(page: Any, *, browser_limit: int, scroll_steps: int) -> tuple[list[str], int]:
    seen: set[str] = set()
    locator_count = 0
    stable_rounds = 0
    previous_total = -1

    selectors = [
        "a[href*='/org/']",
        "[class*='search-business-snippet-view'] a[href*='/org/']",
        "[class*='scroll__container'] a[href*='/org/']",
    ]

    for _ in range(scroll_steps):
        current_urls = collect_hrefs(
            page,
            selectors,
            base_url="https://yandex.com",
            href_substring="/org/",
            limit=browser_limit,
        )
        for url in current_urls:
            seen.add(url)

        try:
            locator_count = max(locator_count, page.locator("a[href*='/org/']").count())
        except Exception:
            pass

        if len(seen) >= browser_limit:
            break
        if len(seen) == previous_total:
            stable_rounds += 1
        else:
            stable_rounds = 0
            previous_total = len(seen)
        if stable_rounds >= 3:
            break
        scroll_results(page, steps=1)

    return list(seen)[:browser_limit], locator_count


def scrape_yandex_maps_queries(queries: list[str], *, options: BrowserOptions) -> list[LeadRow]:
    sync_playwright = import_playwright()
    rows: list[LeadRow] = []
    timeout_ms = int(options.timeout * 1000)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=options.headless)
        context = browser.new_context(locale="ru-RU")
        page = context.new_page()
        try:
            for query in queries:
                search_url = f"https://yandex.com/maps/?mode=search&text={quote(query)}"
                page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(3500)
                if options.query_delay_ms > 0:
                    page.wait_for_timeout(options.query_delay_ms)
                urls, count = collect_yandex_result_urls(
                    page,
                    browser_limit=options.browser_limit,
                    scroll_steps=options.scroll_steps,
                )
                write_snapshot(
                    snapshot_path(options.snapshot_dir, bucket="yandex_search", label=query),
                    page.content(),
                )
                LOGGER.info("yandex query='%s' locator_count=%d collected_urls=%d", query, count, len(urls))
                for url in urls:
                    if options.result_delay_ms > 0:
                        page.wait_for_timeout(options.result_delay_ms)
                    rows.append(
                        scrape_yandex_maps_place(
                            context,
                            url,
                            query=query,
                            timeout_ms=timeout_ms,
                            snapshot_dir=options.snapshot_dir,
                        )
                    )
        finally:
            context.close()
            browser.close()
    return rows
