#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"
due_meals=$(/usr/bin/env python3 -m dormitory_bot.menu_schedule --mode due)
while IFS= read -r meal; do
  [ -n "${meal}" ] || continue
  "${SCRIPT_DIR}/send_menu.sh" --meal "${meal}"
done <<< "${due_meals}"
