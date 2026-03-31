#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Не найден python3. Сначала установи Python 3."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Создаю виртуальное окружение..."
  python3 -m venv .venv
fi

source ".venv/bin/activate"

echo "Обновляю pip..."
python -m pip install --upgrade pip

echo "Ставлю проект и браузер..."
python -m pip install -e ".[browser]"

echo "Ставлю Chromium для Playwright..."
python -m playwright install chromium

mkdir -p out snapshots

echo
echo "Готово."
echo "Дальше запускай:"
echo "  bash 2_run_yandex.sh"
echo "или"
echo "  bash 3_run_google.sh"
