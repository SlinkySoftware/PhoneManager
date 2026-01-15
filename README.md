# Phone Provisioning Manager

High-availability phone provisioning and configuration management system by Slinky Software (Copyright 2026). Licensed under GPLv3.

## Repository Layout
- backend/: Django + DRF backend
- frontend/: Quasar (Vue 3) SPA
- docs/: Documentation (Markdown)
- docker/: Containerisation assets

## Quick Start (Development)
1. Create Python virtualenv and install backend deps:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   python manage.py migrate
   python manage.py runserver 0.0.0.0:8000
   ```
2. Setup frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Containers (backend + frontend + Postgres):
   ```bash
   cd docker
   cp .env.example .env
   docker compose up --build
   ```

## Key Features (scaffolded)
- REST APIs for devices, lines, sites, SIP servers
- Provisioning endpoints keyed by MAC address
- Device type renderer framework with example implementation
- Quasar SPA with dark mode + green theme

## Next Steps
- Implement remaining serializers, viewsets, and provisioning renderers
- Hook frontend forms to backend schemas and endpoints
- Harden auth (session/token), RBAC, and logging

## License
GPL-3.0-only. See LICENSE.md for full text.
