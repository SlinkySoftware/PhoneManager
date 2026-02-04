# Deployment Guide

## Development Setup

### Initial One-Time Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createadmin

# Frontend
cd ../frontend
npm install
cd ..
```

### Start Development Services

```bash
# Using the service management script (recommended)
./manage-services.sh start

# Check status
./manage-services.sh status

# Stop services
./manage-services.sh stop

# Restart services
./manage-services.sh restart
```

**Service URLs:**
- Backend API: http://localhost:8000/api
- Frontend: http://localhost:5173
- Admin: http://localhost:8000/admin

**Log Files:**
- Backend: `var/logs/backend.log`
- Frontend: `var/logs/frontend.log`

### Manual Development (if manage-services.sh not used)

**Terminal 1 - Backend:**
```bash
cd backend
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Docker Compose (Recommended for Testing)

### Setup

```bash
cd docker
cp .env.example .env

# Edit .env to customize ports if needed
# Default: Backend 8000, Frontend 9000, Postgres 5432
nano .env

# Build and start all services
docker compose up --build
```

### Service Access

- Backend API: http://localhost:8000/api
- Frontend: http://localhost:9000
- Admin: http://localhost:8000/admin
- Database: postgres://localhost:5432

### Environment Variables

Key variables in `docker/.env`:

```env
DJANGO_DEBUG=false                    # Disable debug mode in production
DJANGO_SECRET_KEY=<strong-random>     # Set to random value
DATABASE_URL=postgresql://...         # Postgres connection string
POSTGRES_PASSWORD=<strong-password>   # DB password
PROVISIONING_BASE_URL=https://your.domain.com/provision  # Base URL used by renderers
ENCRYPTION_KEY=<strong-random>         # Used for reversible encryption at rest
VITE_API_BASE=http://localhost:8000   # Frontend API base URL
```

## Production Deployment (Bare Metal)

### Prerequisites

- Ubuntu 20.04 LTS or similar
- Python 3.10+
- Node.js 18+
- PostgreSQL 13+
- systemd for process management

### Backend Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash phonemanager
sudo su - phonemanager

# Clone repository and setup
git clone <repo> /opt/phonemanager
cd /opt/phonemanager

# Setup Python environment
python3 -m venv /opt/phonemanager/backend/.venv
source /opt/phonemanager/backend/.venv/bin/activate
pip install -r /opt/phonemanager/backend/requirements.txt
pip install gunicorn

# Setup database
cd /opt/phonemanager/backend
cp .env.example .env
# Edit .env with production settings
nano .env
python manage.py migrate
python manage.py createadmin
```

### Frontend Setup

```bash
cd /opt/phonemanager/frontend
npm install
npm run build

# Serve with nginx (see nginx config below)
```

### Create systemd Services

**Backend Service: `/etc/systemd/system/phonemanager-backend.service`**

```ini
[Unit]
Description=Phone Provisioning Manager Backend
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=phonemanager
Group=www-data
WorkingDirectory=/opt/phonemanager/backend
EnvironmentFile=/opt/phonemanager/backend/.env

# Activate venv and run gunicorn
ExecStart=/opt/phonemanager/backend/.venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 60 \
    --bind 127.0.0.1:8000 \
    phone_manager.wsgi:application

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Frontend Service: `/etc/systemd/system/phonemanager-frontend.service`**

```ini
[Unit]
Description=Phone Provisioning Manager Frontend
After=network.target

[Service]
Type=simple
User=phonemanager
WorkingDirectory=/opt/phonemanager/frontend

# Using Node.js directly (production build)
ExecStart=/usr/bin/node -e "require('http').createServer(require('connect-history-api-fallback')(), require('serve-static')('dist')).listen(5173)"

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable phonemanager-backend
sudo systemctl enable phonemanager-frontend
sudo systemctl start phonemanager-backend
sudo systemctl start phonemanager-frontend

# Check status
sudo systemctl status phonemanager-backend
sudo systemctl status phonemanager-frontend

# View logs
sudo journalctl -u phonemanager-backend -f
sudo journalctl -u phonemanager-frontend -f
```

### Nginx Configuration

**File: `/etc/nginx/sites-available/phonemanager`**

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your.domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your.domain.com;

    # SSL configuration (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your.domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Static files (frontend dist)
    location / {
        root /opt/phonemanager/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1h;
    }

    # API endpoints (backend)
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Provisioning endpoints
    location /provision/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # No auth required for provisioning
        access_log /var/log/nginx/phonemanager_provision.log;
    }

    # Admin panel
    location /admin/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Logging
    access_log /var/log/nginx/phonemanager_access.log;
    error_log /var/log/nginx/phonemanager_error.log;
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/phonemanager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### PostgreSQL Setup

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE phonemanager;
CREATE USER phonemanager WITH PASSWORD '<strong-password>';
ALTER ROLE phonemanager SET client_encoding TO 'utf8';
ALTER ROLE phonemanager SET default_transaction_isolation TO 'read committed';
ALTER ROLE phonemanager SET default_transaction_deferrable TO on;
ALTER ROLE phonemanager SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE phonemanager TO phonemanager;
\q
EOF
```

Add to backend `.env`:

```env
DATABASE_URL=postgresql://phonemanager:<password>@localhost:5432/phonemanager
```

### SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your.domain.com
sudo certbot renew --dry-run  # Test auto-renewal
```

## SSO Configuration (Optional)

### Prerequisites for SSO

- Identity Provider (Microsoft Entra, Okta, or compatible SAML 2.0 IdP)
- Valid SSL certificate (required for SAML ACS endpoint)
- Public domain name (IdPs won't redirect to localhost)

### Enable SSO

1. **Create config.yaml** in repository root:

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

2. **Configure SSO settings:**

```yaml
SSO_ENABLED: true

SAML:
  SP:
    ENTITY_ID: "https://your.domain.com"
    ACS_URL: "https://your.domain.com/api/auth/saml/acs/"
    SLS_URL: "https://your.domain.com/api/auth/saml/sls/"
  
  IDP:
    ENTITY_ID: "https://sts.windows.net/<tenant-id>/"  # For Entra
    SSO_URL: "https://login.microsoftonline.com/<tenant-id>/saml2"
    SLS_URL: ""
    X509_CERT: |
      -----BEGIN CERTIFICATE-----
      MIIDdTCCAl2gAwIBAgILBAAAAAABFUtaw5QwDQYJKoZIhvcNAQEFBQAwVzELMAkG
      ... (full IdP certificate) ...
      -----END CERTIFICATE-----
  
  SECURITY:
    NAME_ID_ENCRYPTED: false
    AUTHN_REQUESTS_SIGNED: false
    LOGOUT_REQUESTS_SIGNED: false
    LOGOUT_RESPONSES_SIGNED: false
    WANT_MESSAGES_SIGNED: false
    WANT_ASSERTIONS_SIGNED: false
    WANT_ASSERTIONS_ENCRYPTED: false
    WANT_NAME_ID_ENCRYPTED: false
  
  CLAIMS:
    USER_CLAIM: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
    ADMIN_CLAIM: "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
    ADMIN_VALUE: "<group-object-id>"  # Entra security group ID
```

3. **Update Nginx configuration** to allow SAML endpoints:

Add to nginx config under `location /api/`:

```nginx
    # SAML endpoints
    location /api/auth/saml/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

4. **Restart services:**

```bash
sudo systemctl restart phonemanager-backend
sudo nginx -t && sudo systemctl reload nginx
```

### IdP Configuration

#### Microsoft Entra ID

1. Create Enterprise Application
2. Configure SAML settings:
   - **Identifier (Entity ID):** `https://your.domain.com`
   - **Reply URL (ACS):** `https://your.domain.com/api/auth/saml/acs/`
3. Download Federation Metadata XML
4. Extract certificate and SSO URL for config.yaml
5. Create security group for admin role
6. Assign users to application

#### Okta

1. Create SAML 2.0 Application
2. Configure SAML settings:
   - **Single sign on URL:** `https://your.domain.com/api/auth/saml/acs/`
   - **Audience URI (SP Entity ID):** `https://your.domain.com`
3. View Setup Instructions to get metadata URL
4. Copy certificate and SSO URL for config.yaml
5. Create groups and map to claims
6. Assign users to application

**Detailed setup instructions:** See [docs/SSO_SETUP.md](SSO_SETUP.md)

### Testing SSO

1. **Access login page:** https://your.domain.com/
2. **SSO button should be visible** (verifies config loaded)
3. **Click "Sign in with SSO"**
4. **Authenticate with IdP** (Microsoft/Okta login page)
5. **Should redirect back** to application with token
6. **Check user role** in top-right menu

### Troubleshooting SSO

**SSO button not visible:**
```bash
# Check config.yaml is readable
sudo -u phonemanager cat /opt/phonemanager/config.yaml

# Check backend logs
sudo journalctl -u phonemanager-backend | grep -i saml

# Test config endpoint
curl https://your.domain.com/api/auth/config/
# Should return: {"ssoEnabled": true}
```

**SAML assertion errors:**
```bash
# Check certificate formatting
grep -A 5 "X509_CERT" config.yaml

# Verify IdP metadata
curl "https://your.domain.com/api/auth/saml/metadata/" | xmllint --format -
```

**User provisioning fails:**
```bash
# Check backend logs for claim extraction
sudo journalctl -u phonemanager-backend | grep -i "saml\|claim"

# Verify USER_CLAIM and ADMIN_CLAIM settings match IdP
# Common Entra claims:
#   - name: http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name
#   - email: http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress
#   - groups: http://schemas.microsoft.com/ws/2008/06/identity/claims/groups
```

**Role assignment not working:**
```bash
# Check user profile in database
sudo -u postgres psql phonemanager -c "SELECT u.username, p.role, p.is_sso FROM auth_user u JOIN core_userprofile p ON u.id=p.user_id WHERE u.username='<username>';"

# Verify ADMIN_VALUE matches group/claim value
# For Entra: Use Group Object ID (not name)
# For Okta: Use exact group name or claim value
```

### Disabling SSO

Set `SSO_ENABLED: false` in config.yaml and restart:

```bash
sudo systemctl restart phonemanager-backend
```

SSO button will disappear from login page, users can only login with local credentials.

## Security Checklist

- [ ] Set strong `DJANGO_SECRET_KEY` in .env
- [ ] Set strong `ENCRYPTION_KEY` in config.yaml or environment
- [ ] Set `PROVISIONING_BASE_URL` for renderer-generated configs
- [ ] Use PostgreSQL in production (not SQLite)
- [ ] Create dedicated database user with minimal privileges
- [ ] Enable SSL/TLS with valid certificate
- [ ] Configure firewall to allow only necessary ports (80, 443)
- [ ] Disable DEBUG mode in production
- [ ] Set ALLOWED_HOSTS to your domain
- [ ] Enable CSRF protection
- [ ] Configure CORS to whitelist frontend origin only
- [ ] Setup log rotation for var/logs/
- [ ] Regular backups of PostgreSQL database
- [ ] Keep dependencies updated
- [ ] Use strong admin password
- [ ] Monitor error logs and API response times
- [ ] Rate limit provisioning endpoints at load balancer
- [ ] Disable Django admin in production (or protect with 2FA)

## Monitoring

### Application Health

```bash
# Check backend service
sudo systemctl status phonemanager-backend

# Check frontend service
sudo systemctl status phonemanager-frontend

# View recent errors
sudo journalctl -u phonemanager-backend -n 50
sudo journalctl -u phonemanager-frontend -n 50

# Check API health
curl https://your.domain.com/api/auth/login/
```

### Log Files

- Backend: `/var/log/journal` (systemd) or `var/logs/backend.log`
- Frontend: `/var/log/journal` (systemd) or `var/logs/frontend.log`
- Nginx: `/var/log/nginx/phonemanager_*.log`

### Database Backups

```bash
# Daily backup
sudo -u postgres pg_dump phonemanager | gzip > /backup/phonemanager_$(date +%Y%m%d).sql.gz

# Automate with cron
0 2 * * * /usr/bin/pg_dump -U phonemanager phonemanager | gzip > /backup/phonemanager_$(date +\%Y\%m\%d).sql.gz
```

## Troubleshooting

### Backend won't start

```bash
# Check Python environment
source /opt/phonemanager/backend/.venv/bin/activate
python manage.py check

# Check database connection
python manage.py dbshell

# Review logs
sudo journalctl -u phonemanager-backend -n 100
```

### Frontend not loading

```bash
# Check if built
ls -la /opt/phonemanager/frontend/dist/

# Rebuild if needed
cd /opt/phonemanager/frontend
npm run build

# Check nginx config
sudo nginx -t
```

### Database connection errors

```bash
# Test connection
psql -U phonemanager -d phonemanager -h localhost

# Check .env DATABASE_URL
cat /opt/phonemanager/backend/.env | grep DATABASE_URL
```
