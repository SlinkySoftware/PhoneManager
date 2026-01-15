# Phone Provisioning Manager

High-availability phone provisioning and configuration management system by Slinky Software (Copyright 2026). Licensed under GPLv3.

## Repository Layout
- backend/: Django + DRF backend
- frontend/: Quasar (Vue 3) SPA
- docs/: Documentation (Markdown)
- docker/: Containerisation assets

## Quick Start (Development)

### Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies and migrate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser  # Create admin user

# Start backend server
python manage.py runserver 0.0.0.0:8000
```

**Important:** Always activate the venv with `source .venv/bin/activate` before running any `python` or `pip` commands in the backend directory.

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Docker Setup (All Services)
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
