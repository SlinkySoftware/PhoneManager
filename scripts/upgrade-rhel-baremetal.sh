#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

set -euo pipefail

APP_USER="${APP_USER:-phonemanager}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
ENV_FILE="${ENV_FILE:-/etc/phonemanager/backend.env}"
GUNICORN_SERVICE="${GUNICORN_SERVICE:-phonemanager-gunicorn.service}"

log() {
  echo "[upgrade-rhel] $*"
}

run_as_app_user() {
  sudo -u "$APP_USER" -H bash -lc "cd '$APP_DIR' && $*"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "This script must run as root (use sudo)."
    exit 1
  fi
}

validate_paths() {
  if [[ ! -d "$BACKEND_DIR" || ! -f "$BACKEND_DIR/manage.py" ]]; then
    echo "Backend directory not found: $BACKEND_DIR"
    echo "Set APP_DIR if your checkout is in a non-default location."
    exit 1
  fi

  if [[ ! -f "$BACKEND_DIR/.venv/bin/python" || ! -f "$BACKEND_DIR/.venv/bin/pip" ]]; then
    echo "Backend virtual environment not found at $BACKEND_DIR/.venv"
    echo "Run scripts/install-rhel-baremetal.sh first."
    exit 1
  fi

  if [[ ! -d "$FRONTEND_DIR" || ! -f "$FRONTEND_DIR/package.json" ]]; then
    echo "Frontend directory not found: $FRONTEND_DIR"
    exit 1
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Backend environment file not found: $ENV_FILE"
    echo "Set ENV_FILE or run scripts/install-rhel-baremetal.sh first."
    exit 1
  fi
}

upgrade_backend_dependencies() {
  log "Upgrading backend Python tooling"
  run_as_app_user "'$BACKEND_DIR/.venv/bin/pip' install --upgrade pip wheel setuptools"

  log "Installing backend Python dependencies from requirements.txt"
  run_as_app_user "'$BACKEND_DIR/.venv/bin/pip' install -r '$BACKEND_DIR/requirements.txt'"
}

upgrade_frontend_dependencies() {
  log "Installing frontend Node.js dependencies"
  if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
    run_as_app_user "cd '$FRONTEND_DIR' && npm ci"
  else
    run_as_app_user "cd '$FRONTEND_DIR' && npm install"
  fi
}

run_migrations() {
  log "Running Django migrations"
  run_as_app_user "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$BACKEND_DIR/.venv/bin/python' manage.py migrate"
}

build_frontend() {
  log "Building Quasar frontend"
  run_as_app_user "cd '$FRONTEND_DIR' && npm run build"

  if [[ ! -d "$FRONTEND_DIR/dist/spa" ]]; then
    echo "Quasar build output not found at $FRONTEND_DIR/dist/spa"
    exit 1
  fi
}

restart_gunicorn() {
  log "Restarting Gunicorn service: $GUNICORN_SERVICE"
  systemctl restart "$GUNICORN_SERVICE"

  if ! systemctl is-active --quiet "$GUNICORN_SERVICE"; then
    echo "Service did not start successfully: $GUNICORN_SERVICE"
    systemctl status --no-pager "$GUNICORN_SERVICE" || true
    exit 1
  fi

  log "Gunicorn service is active"
}

main() {
  require_root
  validate_paths

  log "Starting application upgrade"
  upgrade_backend_dependencies
  upgrade_frontend_dependencies
  run_migrations
  build_frontend
  restart_gunicorn

  cat <<EOF

Upgrade completed successfully.

Executed steps:
1. Updated Python packages from backend/requirements.txt
2. Updated Node.js packages from frontend/package-lock.json/package.json
3. Ran Django migrations
4. Rebuilt Quasar frontend
5. Restarted $GUNICORN_SERVICE

EOF
}

main "$@"
