#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

bash "$ROOT_DIR/1_install.sh"
source ".venv/bin/activate"

OUTPUT_FILE="out/google_1000_raw.csv"
STATE_FILE="out/google_1000_raw.state.txt"

python -m my_clients_leads \
  --google-maps \
  --queries-file queries_google_1000.txt \
  --browser-limit 30 \
  --scroll-steps 18 \
  --query-delay-ms 2000 \
  --result-delay-ms 800 \
  --search-results 10 \
  --snapshot-dir snapshots \
  --state-file "$STATE_FILE" \
  --output "$OUTPUT_FILE" \
  --skip-search-fallback \
  --skip-site-check \
  --no-dedupe \
  --verbose \
  --headful

echo
echo "Готово. CSV сохранен сюда:"
echo "  $OUTPUT_FILE"
echo "Файл прогресса:"
echo "  $STATE_FILE"
