from __future__ import annotations

import csv
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import LeadRow
from .scoring import score_website
from .text import clean_text, extract_domain, normalize_phone


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def choose_value(current: str, candidate: str) -> str:
    return current if current else candidate


def merge_source(current: str, candidate: str) -> str:
    if "+" in current:
        return current
    if "+" in candidate:
        return candidate
    return choose_value(current, candidate)


def merge_reasons(current: str, candidate: str) -> str:
    tokens = [item for item in (current.split(",") + candidate.split(",")) if item]
    return ",".join(dict.fromkeys(tokens))


def build_dedupe_key(row: LeadRow) -> str:
    domain = extract_domain(row.website)
    name = clean_text(row.name).lower()
    address = clean_text(row.address).lower()
    phone = normalize_phone(row.phone).lower()
    if domain and name and address:
        return f"domain_name_address:{domain}|{name}|{address}"
    if domain and name:
        return f"domain_name:{domain}|{name}"
    if domain and phone:
        return f"domain_phone:{domain}|{phone}"
    if name and address:
        return f"name_address:{name}|{address}"
    if name and phone:
        return f"name_phone:{name}|{phone}"
    return f"name:{name}"


def merge_rows(existing: LeadRow, candidate: LeadRow) -> LeadRow:
    existing.source = merge_source(existing.source, candidate.source)
    existing.query = choose_value(existing.query, candidate.query)
    existing.source_url = choose_value(existing.source_url, candidate.source_url)
    existing.address = choose_value(existing.address, candidate.address)
    existing.phone = choose_value(existing.phone, candidate.phone)
    existing.website = choose_value(existing.website, candidate.website)
    existing.hours = choose_value(existing.hours, candidate.hours)
    existing.category = choose_value(existing.category, candidate.category)
    existing.lat = choose_value(existing.lat, candidate.lat)
    existing.lon = choose_value(existing.lon, candidate.lon)
    existing.yandex_id = choose_value(existing.yandex_id, candidate.yandex_id)
    existing.google_place_id = choose_value(existing.google_place_id, candidate.google_place_id)
    existing.website_source = choose_value(existing.website_source, candidate.website_source)
    existing.search_query = choose_value(existing.search_query, candidate.search_query)
    existing.contact_email = choose_value(existing.contact_email, candidate.contact_email)
    existing.contact_phone_from_site = choose_value(existing.contact_phone_from_site, candidate.contact_phone_from_site)
    existing.instagram_url = choose_value(existing.instagram_url, candidate.instagram_url)
    existing.facebook_url = choose_value(existing.facebook_url, candidate.facebook_url)
    existing.linkedin_url = choose_value(existing.linkedin_url, candidate.linkedin_url)
    existing.tiktok_url = choose_value(existing.tiktok_url, candidate.tiktok_url)
    existing.telegram_url = choose_value(existing.telegram_url, candidate.telegram_url)
    existing.youtube_url = choose_value(existing.youtube_url, candidate.youtube_url)
    existing.x_url = choose_value(existing.x_url, candidate.x_url)
    existing.site_status = choose_value(existing.site_status, candidate.site_status)
    existing.site_title = choose_value(existing.site_title, candidate.site_title)
    existing.site_platform = choose_value(existing.site_platform, candidate.site_platform)
    existing.score_reasons = merge_reasons(existing.score_reasons, candidate.score_reasons)
    existing.checked_at = choose_value(existing.checked_at, candidate.checked_at)
    existing.lead_score = max(existing.lead_score, candidate.lead_score)
    return existing


def deduplicate(rows: Iterable[LeadRow]) -> list[LeadRow]:
    merged: dict[str, LeadRow] = {}
    for row in rows:
        row.dedupe_key = build_dedupe_key(row)
        if row.dedupe_key in merged:
            merged[row.dedupe_key] = merge_rows(merged[row.dedupe_key], row)
        else:
            merged[row.dedupe_key] = row
    return list(merged.values())


def apply_site_check(row: LeadRow, *, timeout: float) -> LeadRow:
    result = score_website(row.website, timeout=timeout)
    row.site_status = result.status
    row.site_title = result.title
    row.site_platform = result.platform
    row.contact_email = choose_value(row.contact_email, result.contact_email)
    row.contact_phone_from_site = choose_value(row.contact_phone_from_site, result.contact_phone)
    for field_name, social_url in result.social_links.items():
        if not getattr(row, field_name):
            setattr(row, field_name, social_url)
    row.lead_score += result.score_delta
    row.score_reasons = merge_reasons(row.score_reasons, ",".join(result.reasons))
    row.checked_at = now_iso()
    return row


def write_csv(rows: Iterable[LeadRow], output_path: Path) -> None:
    fieldnames = list(asdict(LeadRow(source="", query="", name="")).keys())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def read_csv(output_path: Path) -> list[LeadRow]:
    if not output_path.exists():
        return []

    valid_fields = {field.name for field in fields(LeadRow)}
    rows: list[LeadRow] = []
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row_data = {key: value for key, value in raw_row.items() if key in valid_fields}
            if "lead_score" in row_data:
                try:
                    row_data["lead_score"] = int(row_data["lead_score"] or 0)
                except ValueError:
                    row_data["lead_score"] = 0
            rows.append(LeadRow(**row_data))
    return rows
