from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

from .constants import SOCIAL_DOMAINS
from .models import LeadRow


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_phone(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return text.replace(" ,", ",")


def normalize_website(url: str | None) -> str:
    text = clean_text(url)
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    return text


def extract_domain(url: str | None) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(normalize_website(url))
    except ValueError:
        return ""
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def root_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def social_field_for_url(url: str) -> str:
    domain = extract_domain(url)
    if not domain:
        return ""
    return SOCIAL_DOMAINS.get(root_domain(domain), "")


def assign_social_link(row: LeadRow, url: str) -> None:
    field_name = social_field_for_url(url)
    if field_name and not getattr(row, field_name):
        setattr(row, field_name, url)


def extract_first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return clean_text(unescape(match.group(1)))
