#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

while true; do
  echo
  echo "=============================="
  echo " My Clients Leads"
  echo "=============================="
  echo "1) Установить все"
  echo "2) Запустить Yandex"
  echo "3) Запустить Google"
  echo "4) Выход"
  echo
  read -r -p "Выбери пункт [1-4]: " choice

  case "$choice" in
    1)
      bash "$ROOT_DIR/1_install.sh"
      ;;
    2)
      bash "$ROOT_DIR/2_run_yandex.sh"
      ;;
    3)
      bash "$ROOT_DIR/3_run_google.sh"
      ;;
    4)
      exit 0
      ;;
    *)
      echo "Нужно ввести 1, 2, 3 или 4."
      ;;
  esac
done
