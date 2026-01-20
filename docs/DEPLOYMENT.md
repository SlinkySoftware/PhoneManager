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
python manage.py createsuperuser

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
python manage.py createsuperuser
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

## Security Checklist

- [ ] Set strong `DJANGO_SECRET_KEY` in .env
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
