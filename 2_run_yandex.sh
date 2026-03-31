#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

bash "$ROOT_DIR/1_install.sh"
source ".venv/bin/activate"

OUTPUT_FILE="out/yandex_$(date +%Y-%m-%d_%H-%M-%S).csv"

python -m my_clients_leads \
  --yandex-maps \
  --queries-file queries_yerevan.txt \
  --browser-limit 60 \
  --scroll-steps 35 \
  --query-delay-ms 3000 \
  --result-delay-ms 1800 \
  --search-results 10 \
  --snapshot-dir snapshots \
  --output "$OUTPUT_FILE" \
  --verbose \
  --headful

echo
echo "Готово. CSV сохранен сюда:"
echo "  $OUTPUT_FILE"
