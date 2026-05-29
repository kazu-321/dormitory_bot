#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${PROJECT_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${PROJECT_DIR}/.env"
  set +a
fi

cd "${PROJECT_DIR}"

exec /usr/bin/env python3 -m dormitory_bot.cleaning_rotation_notify "$@"
