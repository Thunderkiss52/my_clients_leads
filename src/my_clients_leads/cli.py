from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .constants import DEFAULT_BROWSER_LIMIT, DEFAULT_CITY_HINT, DEFAULT_OUTPUT, DEFAULT_QUERIES, DEFAULT_QUERY_DELAY_MS, DEFAULT_RESULT_DELAY_MS, DEFAULT_SCROLL_STEPS, DEFAULT_SEARCH_RESULTS, DEFAULT_TIMEOUT
from .google_maps import scrape_google_maps_queries
from .models import BrowserOptions
from .output import apply_site_check, deduplicate, write_csv
from .search import enrich_row_with_search_fallback
from .text import clean_text
from .yandex_maps import scrape_yandex_maps_queries, scrape_yandex_org_urls

LOGGER = logging.getLogger("my_clients_leads")


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def parse_file_lines(path: str | None) -> list[str]:
    if not path:
        return []
    result: list[str] = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = clean_text(raw_line)
        if line and not line.startswith("#"):
            result.append(line)
    return result


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape client leads from Google Maps and Yandex Maps.")
    parser.add_argument("--query", action="append", default=[], help="Search query. Can be repeated.")
    parser.add_argument("--queries-file", help="Text file with one query per line.")
    parser.add_argument("--google-maps", action="store_true", help="Scrape Google Maps search results.")
    parser.add_argument("--yandex-maps", action="store_true", help="Scrape Yandex Maps search results.")
    parser.add_argument("--yandex-org-url", action="append", default=[], help="Direct Yandex org URL.")
    parser.add_argument("--yandex-org-urls-file", help="Text file with Yandex org URLs.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"CSV output path. Default: {DEFAULT_OUTPUT}")
    parser.add_argument("--city-hint", default=DEFAULT_CITY_HINT, help="Fallback city for web-search enrichment.")
    parser.add_argument("--browser-limit", type=int, default=DEFAULT_BROWSER_LIMIT, help="Max places per query.")
    parser.add_argument("--scroll-steps", type=int, default=DEFAULT_SCROLL_STEPS, help="Scroll passes for map results.")
    parser.add_argument("--query-delay-ms", type=int, default=DEFAULT_QUERY_DELAY_MS, help="Delay after opening each search results page.")
    parser.add_argument("--result-delay-ms", type=int, default=DEFAULT_RESULT_DELAY_MS, help="Delay before opening each place page.")
    parser.add_argument("--search-results", type=int, default=DEFAULT_SEARCH_RESULTS, help="Max fallback search results.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Network timeout in seconds.")
    parser.add_argument("--snapshot-dir", default="", help="Directory to save fetched HTML snapshots.")
    parser.add_argument("--headful", action="store_true", help="Open browser with UI.")
    parser.add_argument("--skip-site-check", action="store_true", help="Skip website checks and scoring.")
    parser.add_argument("--no-dedupe", action="store_true", help="Write raw rows without deduplication.")
    parser.add_argument("--verbose", action="store_true", help="Verbose logs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    queries = unique([clean_text(value) for value in args.query if clean_text(value)] + parse_file_lines(args.queries_file))
    if not queries and (args.google_maps or args.yandex_maps):
        queries = DEFAULT_QUERIES.copy()

    yandex_org_urls = unique([clean_text(value) for value in args.yandex_org_url if clean_text(value)] + parse_file_lines(args.yandex_org_urls_file))
    if not queries and not yandex_org_urls:
        parser.error("Provide --query/--queries-file or --yandex-org-url/--yandex-org-urls-file.")

    browser_options = BrowserOptions(
        browser_limit=args.browser_limit,
        scroll_steps=args.scroll_steps,
        timeout=args.timeout,
        headless=not args.headful,
        query_delay_ms=args.query_delay_ms,
        result_delay_ms=args.result_delay_ms,
        snapshot_dir=args.snapshot_dir,
    )

    rows = []
    if args.google_maps:
        rows.extend(scrape_google_maps_queries(queries, options=browser_options))
    if args.yandex_maps:
        rows.extend(scrape_yandex_maps_queries(queries, options=browser_options))
    if yandex_org_urls:
        rows.extend(scrape_yandex_org_urls(yandex_org_urls, timeout=args.timeout))

    enriched_rows = []
    for row in rows:
        row = enrich_row_with_search_fallback(
            row,
            city_hint=args.city_hint,
            timeout=args.timeout,
            max_results=args.search_results,
        )
        if not args.skip_site_check:
            row = apply_site_check(row, timeout=args.timeout)
        enriched_rows.append(row)

    LOGGER.info("collected raw rows=%d", len(enriched_rows))
    final_rows = enriched_rows if args.no_dedupe else deduplicate(enriched_rows)
    if not args.no_dedupe:
        LOGGER.info("rows after dedupe=%d", len(final_rows))
    final_rows.sort(key=lambda item: (-item.lead_score, item.name.lower(), item.address.lower()))
    output_path = Path(args.output)
    write_csv(final_rows, output_path)
    LOGGER.info("saved rows=%d file=%s", len(final_rows), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
