# Deployment Guide

## Bare Metal (Development)
1. Backend
   - `cd backend`
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `cp .env.example .env` and adjust DB settings
   - `python manage.py migrate`
   - `python manage.py runserver 0.0.0.0:8000`
2. Frontend
   - `cd frontend`
   - `npm install`
   - `npm run dev`

## Docker Compose (Recommended)
1. `cd docker`
2. `cp .env.example .env` and update secrets
3. `docker compose up --build`
4. Backend exposed on 8000, frontend on 9000, Postgres on 5432 (override in .env)

## Systemd Sketch (Backend)
```
[Unit]
Description=Phone Provisioning Manager Backend
After=network.target

[Service]
WorkingDirectory=/opt/phoneManager/backend
EnvironmentFile=/opt/phoneManager/backend/.env
ExecStart=/opt/phoneManager/backend/.venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

## Security Checklist
- Set strong `DJANGO_SECRET_KEY`
- Use PostgreSQL in production with distinct DB user
- Terminate TLS at load balancer
- Ensure provisioning endpoints are rate-limited and logged
- Never commit real secrets; use .env files
