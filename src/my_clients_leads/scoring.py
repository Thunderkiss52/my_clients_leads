from __future__ import annotations

import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from .http import request_bytes
from .models import LeadRow, SiteCheckResult
from .text import assign_social_link, clean_text, extract_domain, normalize_website, social_field_for_url


def detect_platform(html: str) -> str:
    lowered = html.lower()
    for label in ("tilda", "wix", "wordpress", "shopify", "bitrix", "webflow"):
        if label in lowered:
            return label
    return ""


def extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return clean_text(unescape(match.group(1)))


def extract_emails(text: str) -> str:
    matches = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.IGNORECASE)
    emails: list[str] = []
    seen: set[str] = set()
    for value in matches:
        lower = value.lower()
        if lower in seen:
            continue
        seen.add(lower)
        emails.append(value)
    return ", ".join(emails[:3])


def extract_phone_candidates(text: str) -> str:
    matches = re.findall(r"(?<!\d)(?:\+?\d[\d\s().-]{6,}\d)", text)
    phones: list[str] = []
    seen: set[str] = set()
    for value in matches:
        phone = clean_text(value)
        if len(re.sub(r"\D", "", phone)) < 7:
            continue
        if phone in seen:
            continue
        seen.add(phone)
        phones.append(phone)
    return ", ".join(phones[:3])


def extract_href_links(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    return [urljoin(base_url, href.strip()) for href in hrefs if href.strip() and not href.startswith(("#", "javascript:"))]


def score_website(website: str, *, timeout: float) -> SiteCheckResult:
    result = SiteCheckResult()
    original = clean_text(website)
    normalized = normalize_website(original)
    if not normalized:
        result.status = "missing"
        result.score_delta += 4
        result.reasons.append("no_website")
        return result

    domain = extract_domain(normalized)
    social_field = social_field_for_url(normalized)
    if social_field:
        result.status = "social_only"
        result.score_delta += 3
        result.reasons.append("social_only")
        result.social_links[social_field] = normalized
        return result

    urls_to_try = [normalized]
    if original and "://" not in original and normalized.startswith("https://"):
        urls_to_try.append(f"http://{original}")

    raw = b""
    last_status = ""
    for candidate_url in urls_to_try:
        try:
            raw = request_bytes(candidate_url, timeout=timeout)
            normalized = candidate_url
            last_status = "ok"
            break
        except HTTPError as exc:
            last_status = f"http_{exc.code}"
        except URLError:
            last_status = "unreachable"
        except ValueError:
            last_status = "invalid_url"

    if last_status != "ok":
        result.status = last_status or "unreachable"
        result.score_delta += 3
        result.reasons.append("invalid_website" if result.status == "invalid_url" else "site_unreachable")
        return result

    if normalized.startswith("http://"):
        result.score_delta += 2
        result.reasons.append("no_https")

    html = raw.decode("utf-8", errors="ignore")
    result.status = "ok"
    result.title = extract_title(html)
    result.platform = detect_platform(html)
    result.contact_email = extract_emails(html)
    result.contact_phone = extract_phone_candidates(html)

    dummy = LeadRow(source="", query="", name="")
    for link in extract_href_links(html, normalized):
        assign_social_link(dummy, link)
    for field_name in (
        "instagram_url",
        "facebook_url",
        "linkedin_url",
        "tiktok_url",
        "telegram_url",
        "youtube_url",
        "x_url",
    ):
        value = getattr(dummy, field_name)
        if value:
            result.social_links[field_name] = value

    if result.platform in {"wix", "tilda"}:
        result.score_delta += 2
        result.reasons.append(f"platform_{result.platform}")
    if not result.title:
        result.score_delta += 1
        result.reasons.append("no_title")
    if not result.social_links:
        result.score_delta += 1
        result.reasons.append("no_social_links")
    return result
