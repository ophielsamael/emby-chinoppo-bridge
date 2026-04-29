#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/volume1/docker/xnoppo}"
APP_DIR="${APP_DIR:-/volume1/docker/xnoppo/project}"
LOG_DIR="${LOG_DIR:-$BASE_DIR/logs}"
PID_FILE="${PID_FILE:-$LOG_DIR/xnoppo.pid}"
START_SCRIPT="${START_SCRIPT:-$APP_DIR/scripts/start.sh}"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "OK: Xnoppo running (PID $(cat "$PID_FILE"))."
  exit 0
fi

echo "WARN: Xnoppo not running. Restarting..."
[[ -x "$START_SCRIPT" ]] || { echo "Start script not executable: $START_SCRIPT" >&2; exit 1; }
"$START_SCRIPT"
