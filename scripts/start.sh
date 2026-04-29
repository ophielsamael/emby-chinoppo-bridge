#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/volume1/docker/xnoppo}"
APP_DIR="${APP_DIR:-/volume1/docker/xnoppo/project}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
ENV_FILE="${ENV_FILE:-$BASE_DIR/config/.env}"
LOG_DIR="${LOG_DIR:-$BASE_DIR/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/stdout.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/xnoppo.pid}"
ENTRYPOINT="${ENTRYPOINT:-main.py}"

[[ -d "$APP_DIR" ]] || { echo "App directory not found: $APP_DIR" >&2; exit 1; }
[[ -d "$LOG_DIR" ]] || { echo "Log directory not found: $LOG_DIR (create it manually)" >&2; exit 1; }

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Xnoppo already running with PID $(cat "$PID_FILE")."
  exit 0
fi

[[ -f "$APP_DIR/$ENTRYPOINT" ]] || { echo "Entrypoint not found: $APP_DIR/$ENTRYPOINT" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "Env file not found: $ENV_FILE" >&2; exit 1; }

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

cd "$APP_DIR"
nohup python3 "$ENTRYPOINT" --env "$ENV_FILE" >> "$LOG_FILE" 2>&1 &
echo "$!" > "$PID_FILE"

echo "Xnoppo started. PID: $(cat "$PID_FILE")"
echo "Logs: $LOG_FILE"
