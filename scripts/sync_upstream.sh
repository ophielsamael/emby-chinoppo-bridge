#!/usr/bin/env bash
set -euo pipefail

DEFAULT_REMOTE_NAME="xnoppo"
DEFAULT_UPSTREAM_URL="https://github.com/siberian-git/Xnoppo.git"

remote_name="$DEFAULT_REMOTE_NAME"
upstream_url="$DEFAULT_UPSTREAM_URL"
fetch_enabled=1
list_branches=1

usage() {
  cat <<USAGE
Usage:
  ./scripts/sync_upstream.sh [options] [upstream_url]

Options:
  -r, --remote <name>    Remote name to create/update (default: $DEFAULT_REMOTE_NAME)
  -u, --url <url>        Upstream URL (default: $DEFAULT_UPSTREAM_URL)
      --no-fetch         Skip git fetch
      --no-list          Do not list remote branches after fetch
  -h, --help             Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -r|--remote) [[ $# -ge 2 ]] || { echo "Missing value for $1"; exit 1; }; remote_name="$2"; shift 2 ;;
    -u|--url) [[ $# -ge 2 ]] || { echo "Missing value for $1"; exit 1; }; upstream_url="$2"; shift 2 ;;
    --no-fetch) fetch_enabled=0; shift ;;
    --no-list) list_branches=0; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown option: $1"; exit 1 ;;
    *) upstream_url="$1"; shift ;;
  esac
done

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Run inside a git repository"; exit 1; }

if git remote get-url "$remote_name" >/dev/null 2>&1; then
  git remote set-url "$remote_name" "$upstream_url"
else
  git remote add "$remote_name" "$upstream_url"
fi

if [[ "$fetch_enabled" -eq 1 ]]; then
  git fetch "$remote_name" --prune
fi

if [[ "$list_branches" -eq 1 ]]; then
  git branch -r | grep "${remote_name}/" || true
fi
