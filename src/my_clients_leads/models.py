from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LeadRow:
    source: str
    query: str
    name: str
    source_url: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    hours: str = ""
    category: str = ""
    lat: str = ""
    lon: str = ""
    yandex_id: str = ""
    google_place_id: str = ""
    website_source: str = ""
    search_query: str = ""
    contact_email: str = ""
    contact_phone_from_site: str = ""
    instagram_url: str = ""
    facebook_url: str = ""
    linkedin_url: str = ""
    tiktok_url: str = ""
    telegram_url: str = ""
    youtube_url: str = ""
    x_url: str = ""
    site_status: str = ""
    site_title: str = ""
    site_platform: str = ""
    lead_score: int = 0
    score_reasons: str = ""
    dedupe_key: str = ""
    checked_at: str = ""


@dataclass
class SiteCheckResult:
    status: str = ""
    title: str = ""
    platform: str = ""
    score_delta: int = 0
    reasons: list[str] = field(default_factory=list)
    contact_email: str = ""
    contact_phone: str = ""
    social_links: dict[str, str] = field(default_factory=dict)


@dataclass
class BrowserOptions:
    browser_limit: int
    scroll_steps: int
    timeout: float
    headless: bool
    query_delay_ms: int = 0
    result_delay_ms: int = 0
    snapshot_dir: str = ""
    detail_workers: int = 1
