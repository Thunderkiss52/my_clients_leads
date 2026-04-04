USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)

DEFAULT_OUTPUT = "leads.csv"
DEFAULT_TIMEOUT = 20.0
DEFAULT_CITY_HINT = "Yerevan"
DEFAULT_SEARCH_RESULTS = 8
DEFAULT_BROWSER_LIMIT = 30
DEFAULT_SCROLL_STEPS = 12
DEFAULT_QUERY_DELAY_MS = 1500
DEFAULT_RESULT_DELAY_MS = 1200
DEFAULT_DETAIL_WORKERS = 6
DEFAULT_QUERIES = [
    "salon yerevan",
    "dentist yerevan",
    "car service yerevan",
]

SOCIAL_DOMAINS = {
    "instagram.com": "instagram_url",
    "facebook.com": "facebook_url",
    "fb.com": "facebook_url",
    "tiktok.com": "tiktok_url",
    "linkedin.com": "linkedin_url",
    "t.me": "telegram_url",
    "telegram.me": "telegram_url",
    "youtube.com": "youtube_url",
    "x.com": "x_url",
    "twitter.com": "x_url",
}

DIRECTORY_DOMAINS = {
    "google.com",
    "maps.google.com",
    "yandex.ru",
    "yandex.com",
    "ya.ru",
    "2gis.com",
    "tripadvisor.com",
    "yellowpages.com",
    "list.am",
    "spyur.am",
}
