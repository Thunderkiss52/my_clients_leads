from __future__ import annotations

import json
import logging
import re
from html import unescape
from typing import Any, Callable
from urllib.parse import quote

from .browser import collect_hrefs, first_locator_href, first_locator_text, import_playwright, scroll_results, try_click
from .models import BrowserOptions, LeadRow
from .snapshots import snapshot_path, write_snapshot
from .text import clean_text, normalize_phone, normalize_website

LOGGER = logging.getLogger("my_clients_leads")


def extract_json_ld_objects(html: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    matches = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw in matches:
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            objects.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            objects.append(parsed)
    return objects


def extract_business_from_json_ld(html: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in extract_json_ld_objects(html):
        item_type = item.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        lowered = {str(value).lower() for value in types if value}
        if not lowered.intersection({"organization", "localbusiness", "store", "medicalbusiness", "restaurant"}):
            continue
        if item.get("name") and not result.get("name"):
            result["name"] = clean_text(item["name"])
        if item.get("url") and not result.get("website"):
            result["website"] = normalize_website(item["url"])
        if item.get("telephone") and not result.get("phone"):
            result["phone"] = clean_text(item["telephone"])
        address = item.get("address")
        if isinstance(address, dict) and not result.get("address"):
            parts = [clean_text(address.get(key)) for key in ("streetAddress", "addressLocality", "addressRegion")]
            result["address"] = clean_text(", ".join(part for part in parts if part))
    return result


def extract_google_cid(url: str) -> str:
    match = re.search(r"!3d[-\d.]+!4d[-\d.]+", url)
    return match.group(0) if match else ""


def scrape_google_maps_place(context: Any, url: str, *, query: str, timeout_ms: int, snapshot_dir: str = "") -> LeadRow:
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2500)
        try_click(
            page,
            [
                "button[aria-label='Accept all']",
                "button[aria-label='Принять все']",
                "button:has-text('Accept all')",
                "button:has-text('Принять все')",
            ],
        )
        html = page.content()
        write_snapshot(
            snapshot_path(snapshot_dir, bucket="google_place", label=extract_google_cid(url) or url),
            html,
        )
        structured = extract_business_from_json_ld(html)
        row = LeadRow(
            source="google_maps_scrape",
            query=query,
            name=structured.get("name", "") or first_locator_text(page, ["h1", "h1 span"]),
            source_url=url,
            address=structured.get("address", "")
            or first_locator_text(page, ["button[data-item-id='address']", "button[data-item-id^='address']"]),
            phone=structured.get("phone", "")
            or first_locator_text(page, ["button[data-item-id^='phone:tel:']", "a[href^='tel:']"]),
            website=structured.get("website", "")
            or first_locator_href(
                page,
                ["a[data-item-id='authority']", "a[data-item-id*='authority']", "a[aria-label*='Website']"],
                exclude_domains={"google.com"},
            ),
            google_place_id=extract_google_cid(url),
        )
        row.phone = normalize_phone(row.phone)
        row.website = normalize_website(row.website) if row.website else ""
        if row.website:
            row.website_source = "google_maps_scrape"
        return row
    finally:
        page.close()


def collect_google_result_urls(page: Any, *, browser_limit: int, scroll_steps: int) -> tuple[list[str], int]:
    seen: set[str] = set()
    locator_count = 0
    stable_rounds = 0
    previous_total = -1

    selectors = [
        "a[href*='/maps/place/']",
        "div[role='feed'] a[href*='/maps/place/']",
    ]

    for _ in range(scroll_steps):
        current_urls = collect_hrefs(
            page,
            selectors,
            base_url="https://www.google.com",
            href_substring="/maps/place/",
            limit=browser_limit,
        )
        for url in current_urls:
            seen.add(url)

        try:
            locator_count = max(locator_count, page.locator("a[href*='/maps/place/']").count())
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


def scrape_google_maps_queries(
    queries: list[str],
    *,
    options: BrowserOptions,
    on_query_complete: Callable[[str, list[LeadRow]], None] | None = None,
) -> list[LeadRow]:
    sync_playwright = import_playwright()
    rows: list[LeadRow] = []
    timeout_ms = int(options.timeout * 1000)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=options.headless)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        try:
            total_queries = len(queries)
            for index, query in enumerate(queries, start=1):
                LOGGER.info("google progress %d/%d query='%s'", index, total_queries, query)
                query_rows: list[LeadRow] = []
                search_url = f"https://www.google.com/maps/search/{quote(query)}"
                page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(3500)
                if options.query_delay_ms > 0:
                    page.wait_for_timeout(options.query_delay_ms)
                try_click(
                    page,
                    [
                        "button[aria-label='Accept all']",
                        "button[aria-label='Принять все']",
                        "button:has-text('Accept all')",
                        "button:has-text('Принять все')",
                    ],
                )
                urls, count = collect_google_result_urls(
                    page,
                    browser_limit=options.browser_limit,
                    scroll_steps=options.scroll_steps,
                )
                write_snapshot(
                    snapshot_path(options.snapshot_dir, bucket="google_search", label=query),
                    page.content(),
                )
                LOGGER.info("google query='%s' locator_count=%d collected_urls=%d", query, count, len(urls))
                for url in urls:
                    if options.result_delay_ms > 0:
                        page.wait_for_timeout(options.result_delay_ms)
                    query_rows.append(
                        scrape_google_maps_place(
                            context,
                            url,
                            query=query,
                            timeout_ms=timeout_ms,
                            snapshot_dir=options.snapshot_dir,
                        )
                    )
                rows.extend(query_rows)
                if on_query_complete:
                    on_query_complete(query, query_rows)
        finally:
            context.close()
            browser.close()
    return rows
