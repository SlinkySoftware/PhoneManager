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
SYSTEMD_SERVICE_PATH="${SYSTEMD_SERVICE_PATH:-/etc/systemd/system/${GUNICORN_SERVICE}}"
NGINX_CONF="${NGINX_CONF:-/etc/nginx/conf.d/phonemanager.conf}"
LOGROTATE_CONF="${LOGROTATE_CONF:-/etc/logrotate.d/phonemanager}"
LOG_DIR_WAS_PROVIDED=0
if [[ -n "${LOG_DIR+x}" ]]; then
  LOG_DIR_WAS_PROVIDED=1
fi
LOG_DIR="${LOG_DIR:-/var/log/phonemanager}"

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

load_log_dir_from_env_file() {
  if [[ "$LOG_DIR_WAS_PROVIDED" -eq 1 || ! -f "$ENV_FILE" ]]; then
    return
  fi

  local env_log_dir
  env_log_dir="$(sed -n 's/^LOG_DIR=//p' "$ENV_FILE" | tail -n 1)"
  env_log_dir="${env_log_dir#\"}"
  env_log_dir="${env_log_dir%\"}"
  env_log_dir="${env_log_dir#\'}"
  env_log_dir="${env_log_dir%\'}"

  if [[ -n "$env_log_dir" ]]; then
    LOG_DIR="$env_log_dir"
  fi
}

validate_log_dir() {
  if [[ "$LOG_DIR" != /* ]]; then
    echo "LOG_DIR must be an absolute path: $LOG_DIR"
    exit 1
  fi
}

ensure_log_dir_env_key() {
  local escaped_log_dir
  escaped_log_dir="$(printf '%s' "$LOG_DIR" | sed 's/[&|]/\\&/g')"

  if grep -q '^LOG_DIR=' "$ENV_FILE"; then
    if [[ "$LOG_DIR_WAS_PROVIDED" -eq 1 ]]; then
      sed -i "s|^LOG_DIR=.*$|LOG_DIR=$escaped_log_dir|" "$ENV_FILE"
      log "Updated LOG_DIR env key: $LOG_DIR"
    fi
  else
    echo "LOG_DIR=$LOG_DIR" >> "$ENV_FILE"
    log "Added missing LOG_DIR env key"
  fi

  chmod 640 "$ENV_FILE"
  chown root:"$APP_GROUP" "$ENV_FILE"
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

ensure_log_dir() {
  log "Ensuring application log directory exists: $LOG_DIR"
  mkdir -p "$LOG_DIR"
  chown root:"$APP_GROUP" "$LOG_DIR"
  chmod 2775 "$LOG_DIR"

  touch \
    "$LOG_DIR/application.log" \
    "$LOG_DIR/gunicorn-access.log" \
    "$LOG_DIR/nginx-access.log" \
    "$LOG_DIR/nginx-error.log"

  chown root:"$APP_GROUP" \
    "$LOG_DIR/application.log" \
    "$LOG_DIR/gunicorn-access.log" \
    "$LOG_DIR/nginx-access.log" \
    "$LOG_DIR/nginx-error.log"

  chmod 664 \
    "$LOG_DIR/application.log" \
    "$LOG_DIR/gunicorn-access.log" \
    "$LOG_DIR/nginx-access.log" \
    "$LOG_DIR/nginx-error.log"
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

write_systemd_service() {
  log "Writing systemd gunicorn service: $SYSTEMD_SERVICE_PATH"
  cat > "$SYSTEMD_SERVICE_PATH" <<EOF
[Unit]
Description=Phone Manager Django Gunicorn Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:$LOG_DIR/application.log
StandardError=append:$LOG_DIR/application.log
ExecStart=$BACKEND_DIR/.venv/bin/gunicorn \
  --workers 4 \
  --worker-class sync \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --timeout 60 \
  --bind 127.0.0.1:8000 \
  --access-logfile $LOG_DIR/gunicorn-access.log \
  --access-logformat '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
  --capture-output \
  --log-level info \
  phone_manager.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  chmod 644 "$SYSTEMD_SERVICE_PATH"
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

  access_log $LOG_DIR/nginx-access.log;
  error_log $LOG_DIR/nginx-error.log;
}
EOF

  chmod 644 "$NGINX_CONF"
}

write_logrotate_config() {
  log "Writing logrotate configuration: $LOGROTATE_CONF"
  cat > "$LOGROTATE_CONF" <<EOF
$LOG_DIR/application.log $LOG_DIR/gunicorn-access.log $LOG_DIR/nginx-access.log $LOG_DIR/nginx-error.log {
    daily
    rotate 13
    dateext
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    su root $APP_GROUP
    create 0640 root $APP_GROUP
}
EOF

  chmod 644 "$LOGROTATE_CONF"
}

reload_nginx() {
  log "Validating Nginx configuration"
  nginx -t
  systemctl enable --now nginx
  systemctl restart nginx
}

reload_systemd() {
  log "Reloading systemd configuration"
  systemctl daemon-reload
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
  load_log_dir_from_env_file
  ensure_log_dir_env_key
  ensure_ldap_env_keys
  validate_log_dir
  ensure_log_dir
  ensure_ownership
  upgrade_backend_dependencies
  upgrade_frontend_dependencies
  run_migrations
  build_frontend
  write_systemd_service
  write_nginx_config
  write_logrotate_config
  reload_systemd
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
7. Rewrote the Gunicorn systemd unit with file logging
8. Rewrote and reloaded nginx configuration
9. Wrote logrotate configuration for application logs
10. Restarted $GUNICORN_SERVICE

EOF
}

main "$@"