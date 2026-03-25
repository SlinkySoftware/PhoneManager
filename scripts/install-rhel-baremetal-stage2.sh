#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

set -euo pipefail

APP_USER="${APP_USER:-phonemanager}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
ENV_DIR="/etc/phonemanager"
ENV_FILE="$ENV_DIR/backend.env"
NGINX_CONF="/etc/nginx/conf.d/phonemanager.conf"
SYSTEMD_SERVICE="/etc/systemd/system/phonemanager-gunicorn.service"
LOGROTATE_CONF="/etc/logrotate.d/phonemanager"
LOG_DIR_WAS_PROVIDED=0
if [[ -n "${LOG_DIR+x}" ]]; then
  LOG_DIR_WAS_PROVIDED=1
fi
LOG_DIR="${LOG_DIR:-/var/log/phonemanager}"
PYTHON_BIN=""

log() {
  echo "[install-rhel] $*"
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

  if [[ ! -d "$FRONTEND_DIR" || ! -f "$FRONTEND_DIR/package.json" ]]; then
    echo "Frontend directory not found: $FRONTEND_DIR"
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

ensure_python_312() {
  log "Installing Python runtime and build dependencies"

  dnf -y install \
    python3.12 \
    python3.12-devel \
    python3.12-pip \
    gcc \
    gcc-c++ \
    make \
    libffi-devel \
    openssl-devel \
    postgresql-devel \
    libxml2-devel \
    libxslt-devel \
    xmlsec1 \
    xmlsec1-openssl \
    git \
    curl \
    nginx

  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "Python not found after package installation."
    exit 1
  fi

  local detected_version
  detected_version="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "${detected_version%%.*}" -lt 3 ]] || [[ "${detected_version##*.}" -lt 12 && "${detected_version%%.*}" -eq 3 ]]; then
    echo "Python >= 3.12 is required, found $detected_version via $PYTHON_BIN"
    exit 1
  fi

  log "Using Python interpreter: $PYTHON_BIN ($detected_version)"
}

ensure_app_user() {
  if ! id "$APP_USER" >/dev/null 2>&1; then
    log "Creating system user: $APP_USER"
    useradd --system --create-home --shell /bin/bash "$APP_USER"
  fi

  if ! getent group "$APP_GROUP" >/dev/null 2>&1; then
    log "Creating system group: $APP_GROUP"
    groupadd "$APP_GROUP"
  fi

  usermod -a -G "$APP_GROUP" "$APP_USER" || true
}

ensure_app_ownership() {
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

setup_backend_venv() {
  log "Creating backend virtual environment"
  run_as_app_user "$PYTHON_BIN -m venv '$BACKEND_DIR/.venv'"

  log "Installing backend Python dependencies"
  run_as_app_user "'$BACKEND_DIR/.venv/bin/pip' install --upgrade pip wheel setuptools"
  run_as_app_user "'$BACKEND_DIR/.venv/bin/pip' install -r '$BACKEND_DIR/requirements.txt' gunicorn"
}

setup_frontend() {
  log "Installing frontend Node.js dependencies"
  run_as_app_user "cd '$FRONTEND_DIR' && npm ci"

  if [[ ! -f "$FRONTEND_DIR/.env.production" ]]; then
    log "Creating frontend production env file"
    cat > "$FRONTEND_DIR/.env.production" <<'EOF'
VITE_API_BASE=/api
EOF
    chown "$APP_USER:$APP_GROUP" "$FRONTEND_DIR/.env.production"
  fi

  log "Building Quasar frontend"
  run_as_app_user "cd '$FRONTEND_DIR' && npm run build"

  if [[ ! -d "$FRONTEND_DIR/dist/spa" ]]; then
    echo "Quasar build output not found at $FRONTEND_DIR/dist/spa"
    exit 1
  fi
}

write_backend_env() {
  log "Writing externalized backend environment file: $ENV_FILE"
  mkdir -p "$ENV_DIR"
  chmod 750 "$ENV_DIR"
  chown root:"$APP_GROUP" "$ENV_DIR"

  if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<EOF
DJANGO_SECRET_KEY=change-this-to-a-strong-random-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=phonemanager
DJANGO_DB_USER=phonemanager
DJANGO_DB_PASSWORD=change-this-db-password
DJANGO_DB_HOST=127.0.0.1
DJANGO_DB_PORT=5432
LOG_DIR=$LOG_DIR
LDAP_ENABLED=False
LDAP_DISPLAY_NAME="Central Authentication"
LDAP_SERVER_NAME=
LDAP_PORT=389
LDAP_ENCRYPTION=none
LDAP_VALIDATE_CERTIFICATES=True
LDAP_BIND_DN=
LDAP_BIND_PASSWORD=
LDAP_DOMAIN_NAME=
LDAP_USERNAME_FORMAT=%u
LDAP_GROUP_ATTRIBUTE=memberOf
LDAP_ADMIN_GROUP_MAPPING=
LDAP_USER_GROUP_MAPPING=
LDAP_BASE_DN=
LDAP_SEARCH_FILTER='(|(userPrincipalName=%u)(sAMAccountName=%r)(uid=%r)(cn=%r))'
EOF
    chmod 640 "$ENV_FILE"
    chown root:"$APP_GROUP" "$ENV_FILE"
  else
    log "Existing backend env file detected, leaving unchanged"
  fi

  ensure_log_dir_env_key
  ensure_ldap_env_keys

  if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    ln -s "$ENV_FILE" "$BACKEND_DIR/.env"
    chown -h "$APP_USER:$APP_GROUP" "$BACKEND_DIR/.env"
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

write_systemd_service() {
  log "Writing systemd gunicorn service: $SYSTEMD_SERVICE"
  cat > "$SYSTEMD_SERVICE" <<EOF
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

  chmod 644 "$SYSTEMD_SERVICE"
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

reload_services() {
  log "Reloading systemd and enabling services"
  systemctl daemon-reload
  systemctl enable --now phonemanager-gunicorn.service
  systemctl enable --now nginx

  log "Validating Nginx configuration"
  nginx -t
  systemctl restart nginx
}

run_migrations() {
  log "Running Django migrations"
  if ! run_as_app_user "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$BACKEND_DIR/.venv/bin/python' manage.py migrate"; then
    log "Migrations failed (often due to placeholder DB credentials)."
    log "Update $ENV_FILE and rerun migrations manually."
  fi
}

main() {
  require_root
  validate_paths

  log "Starting stage 2 installation execution"
  ensure_python_312
  ensure_app_user
  ensure_app_ownership
  setup_backend_venv
  write_backend_env
  load_log_dir_from_env_file
  validate_log_dir
  ensure_log_dir
  run_migrations
  setup_frontend
  write_systemd_service
  write_nginx_config
  write_logrotate_config
  reload_services

  cat <<EOF

Installation completed.

Next steps:
1. Edit $ENV_FILE with real production values.
2. If DB settings changed, rerun migrations:
   sudo -u $APP_USER -H bash -lc "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$BACKEND_DIR/.venv/bin/python' manage.py migrate"
3. Optionally create an admin user:
   sudo -u $APP_USER -H bash -lc "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$BACKEND_DIR/.venv/bin/python' manage.py createadmin"
4. Restart backend after env changes:
   sudo systemctl restart phonemanager-gunicorn

EOF
}

main "$@"