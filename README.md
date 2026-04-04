# My Clients Leads

Отдельный Python-проект для сбора лидов из Google Maps и Yandex Maps, с CSV-выгрузкой, добором сайта/соцсетей и скорингом сайта.

## Запуск в 1 кнопку

Самый простой вариант:

```bash
bash start.sh
```

Там будет меню:

- `1` установить все
- `2` запустить сбор через Yandex
- `3` запустить сбор через Google

Если хочешь без меню, запускай прямо по номерам:

```bash
bash 1_install.sh
bash 2_run_yandex.sh
bash 3_run_google.sh
```

Для большого сбора по Yandex скрипт сам открывает браузер. Если Yandex покажет `Вы не робот?`, просто пройди проверку вручную в окне, и сбор продолжится дальше.
`2_run_yandex.sh` использует расширенный файл `queries_yerevan_1000.txt`, пишет сырой CSV в `out/yandex_1000_raw.csv` и сохраняет прогресс в `out/yandex_1000_raw.state.txt`, чтобы при повторном запуске продолжить с непройденных запросов.
`3_run_google.sh` работает так же: использует `queries_google_1000.txt`, пишет в `out/google_1000_raw.csv` и продолжает по `out/google_1000_raw.state.txt`.

## Ручная установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Для режимов `--google-maps` и `--yandex-maps` нужен браузерный extra:

```bash
pip install -e .[browser]
playwright install chromium
```

## Быстрый запуск

CLI можно запускать и как модуль:

```bash
PYTHONPATH=src python3 -m my_clients_leads --help
```

По поисковому запросу в Yandex Maps:

```bash
my-clients-leads \
  --yandex-maps \
  --query "салон красоты Ереван" \
  --browser-limit 30 \
  --output yandex_maps.csv
```

По прямой ссылке организации Yandex:

```bash
my-clients-leads \
  --yandex-org-url "https://yandex.com/maps/org/65816015425/" \
  --output perfect_smile.csv
```

По поисковому запросу в Google Maps:

```bash
my-clients-leads \
  --google-maps \
  --query "beauty salon yerevan" \
  --browser-limit 30 \
  --output google_maps.csv
```

## Полезные флаги

- `--headful` открыть браузер с UI
- `--scroll-steps 15` сильнее прокрутить выдачу
- `--query-delay-ms 2500` дольше ждать после открытия выдачи
- `--result-delay-ms 1500` пауза перед открытием каждой карточки
- `--snapshot-dir snapshots` сохранять HTML выдачи и карточек локально
- `--search-results 10` сколько ссылок брать из fallback web search
- `--skip-site-check` только собрать карточки без проверки сайта
- `--no-dedupe` сохранить сырой список без схлопывания дублей
- `--queries-file queries.txt` список запросов
- `--yandex-org-urls-file urls.txt` список прямых ссылок Yandex org

## CSV поля

- `source`, `query`, `name`, `source_url`
- `address`, `phone`, `website`, `hours`, `category`
- `contact_email`, `contact_phone_from_site`
- `instagram_url`, `facebook_url`, `linkedin_url`, `tiktok_url`, `telegram_url`, `youtube_url`, `x_url`
- `site_status`, `site_title`, `site_platform`, `lead_score`, `score_reasons`
