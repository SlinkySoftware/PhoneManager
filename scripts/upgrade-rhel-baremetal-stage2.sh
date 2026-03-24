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
NGINX_CONF="${NGINX_CONF:-/etc/nginx/conf.d/phonemanager.conf}"

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

ensure_ldap_env_keys() {
  local missing=0

  append_if_missing() {
    local key="$1"
    local value="$2"
    if ! grep -q "^${key}=" "$ENV_FILE"; then
      echo "${key}=${value}" >> "$ENV_FILE"
      missing=1
      log "Added missing LDAP env key: $key"
    fi
  }

  append_if_missing "LDAP_ENABLED" "False"
  append_if_missing "LDAP_DISPLAY_NAME" "\"Central Authentication\""
  append_if_missing "LDAP_SERVER_NAME" ""
  append_if_missing "LDAP_PORT" "389"
  append_if_missing "LDAP_ENCRYPTION" "none"
  append_if_missing "LDAP_VALIDATE_CERTIFICATES" "True"
  append_if_missing "LDAP_BIND_DN" ""
  append_if_missing "LDAP_BIND_PASSWORD" ""
  append_if_missing "LDAP_DOMAIN_NAME" ""
  append_if_missing "LDAP_USERNAME_FORMAT" "%u"
  append_if_missing "LDAP_GROUP_ATTRIBUTE" "memberOf"
  append_if_missing "LDAP_ADMIN_GROUP_MAPPING" ""
  append_if_missing "LDAP_USER_GROUP_MAPPING" ""
  append_if_missing "LDAP_BASE_DN" ""
  append_if_missing "LDAP_SEARCH_FILTER" "'(|(userPrincipalName=%u)(sAMAccountName=%r)(uid=%r)(cn=%r))'"

  if [[ "$missing" -eq 1 ]]; then
    chmod 640 "$ENV_FILE"
    chown root:"$APP_GROUP" "$ENV_FILE"
  fi
}

ensure_ownership() {
  log "Ensuring file ownership for application directory"
  chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
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

write_nginx_config() {
  log "Writing Nginx configuration: $NGINX_CONF"
  cat > "$NGINX_CONF" <<EOF
upstream phonemanager_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    root $FRONTEND_DIR/dist/spa;
    index index.html;

    # Frontend SPA routes
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Django API endpoints
    location /api/ {
        proxy_pass http://phonemanager_backend;
        proxy_set_header Host localhost;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Provisioning endpoints for phones
    location /provision/ {
        proxy_pass http://phonemanager_backend;
        proxy_set_header Host localhost;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Django admin endpoints
    location /admin/ {
        proxy_pass http://phonemanager_backend;
        proxy_set_header Host localhost;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    access_log /var/log/nginx/phonemanager_access.log;
    error_log /var/log/nginx/phonemanager_error.log;
}
EOF

  chmod 644 "$NGINX_CONF"
}

reload_nginx() {
  log "Validating Nginx configuration"
  nginx -t
  systemctl enable --now nginx
  systemctl restart nginx
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

  log "Starting stage 2 upgrade execution"
  ensure_ldap_env_keys
  ensure_ownership
  upgrade_backend_dependencies
  upgrade_frontend_dependencies
  run_migrations
  build_frontend
  write_nginx_config
  reload_nginx
  restart_gunicorn

  cat <<EOF

Upgrade completed successfully.

Executed steps:
1. Stage 1 refreshed the git checkout
2. Ensured file ownership under APP_DIR
3. Updated Python packages from backend/requirements.txt
4. Updated Node.js packages from frontend/package-lock.json/package.json
5. Ran Django migrations
6. Rebuilt Quasar frontend
7. Rewrote and reloaded nginx configuration
8. Restarted $GUNICORN_SERVICE

EOF
}

main "$@"