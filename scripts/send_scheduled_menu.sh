#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ] || [ "$1" != "--meal" ] || [ "$3" != "--base-time" ]; then
  echo "Usage: $0 --meal MEAL --base-time HH:MM" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
meal="$2"
base_time="$4"

cd "${PROJECT_DIR}"
status=0
/usr/bin/env python3 -m dormitory_bot.menu_schedule \
  --mode base \
  --meal "${meal}" \
  --base-time "${base_time}" || status=$?

case "${status}" in
  0) exec "${SCRIPT_DIR}/send_menu.sh" --meal "${meal}" ;;
  1) exit 0 ;;
  *) exit "${status}" ;;
esac
