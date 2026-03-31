from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

from .constants import DIRECTORY_DOMAINS
from .http import request_bytes
from .models import LeadRow
from .text import assign_social_link, clean_text, extract_domain, normalize_website, root_domain, social_field_for_url

LOGGER = logging.getLogger("my_clients_leads")


def decode_duckduckgo_link(url: str) -> str:
    parsed = urlsplit(url)
    if "duckduckgo.com" not in parsed.netloc:
        return url
    params = parse_qs(parsed.query)
    redirected = params.get("uddg")
    if redirected:
        return unquote(redirected[0])
    return url


def is_directory_url(url: str) -> bool:
    return root_domain(extract_domain(url)) in DIRECTORY_DOMAINS


def duckduckgo_search(query: str, *, timeout: float, max_results: int) -> list[str]:
    search_url = f"https://html.duckduckgo.com/html/?{urlencode({'q': query})}"
    html = request_bytes(search_url, timeout=timeout, max_bytes=524288).decode("utf-8", errors="ignore")
    links = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"', html, flags=re.IGNORECASE)

    results: list[str] = []
    seen: set[str] = set()
    for raw_link in links:
        link = decode_duckduckgo_link(unescape(raw_link))
        domain = extract_domain(link)
        if not domain or domain in seen:
            continue
        seen.add(domain)
        results.append(link)
        if len(results) >= max_results:
            break
    return results


def yandex_web_search(query: str, *, timeout: float, max_results: int) -> list[str]:
    search_url = f"https://ya.ru/search/?{urlencode({'text': query})}"
    html = request_bytes(search_url, timeout=timeout, max_bytes=524288).decode("utf-8", errors="ignore")
    hrefs = re.findall(r'href=["\'](https?://[^"\']+)["\']', html, flags=re.IGNORECASE)

    results: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        link = unescape(href)
        domain = root_domain(extract_domain(link))
        if not domain or domain in DIRECTORY_DOMAINS or domain in seen:
            continue
        seen.add(domain)
        results.append(link)
        if len(results) >= max_results:
            break
    return results


def combined_web_search(query: str, *, timeout: float, max_results: int) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for search_fn in (yandex_web_search, duckduckgo_search):
        try:
            candidates = search_fn(query, timeout=timeout, max_results=max_results)
        except Exception as exc:
            LOGGER.debug("search backend failed for '%s': %s", query, exc)
            continue
        for link in candidates:
            domain = extract_domain(link)
            if not domain or domain in seen:
                continue
            seen.add(domain)
            links.append(link)
            if len(links) >= max_results:
                return links
    return links


def enrich_row_with_search_fallback(
    row: LeadRow,
    *,
    city_hint: str,
    timeout: float,
    max_results: int,
) -> LeadRow:
    if row.website and row.instagram_url and row.facebook_url:
        return row

    query_parts = [row.name]
    if row.address:
        query_parts.append(row.address)
    elif city_hint:
        query_parts.append(city_hint)
    search_query = clean_text(" ".join(query_parts))
    if not search_query:
        return row

    row.search_query = row.search_query or search_query
    links = combined_web_search(search_query, timeout=timeout, max_results=max_results)
    for link in links:
        if social_field_for_url(link):
            assign_social_link(row, link)
            continue
        if is_directory_url(link):
            continue
        if not row.website:
            row.website = normalize_website(link)
            row.website_source = row.website_source or "web_search_fallback"
    return row
