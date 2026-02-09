# Phone Provisioning Manager

High-availability phone provisioning and configuration management system by Slinky Software (Copyright 2026). Licensed under GPLv3.

## Repository Layout
- backend/: Django + DRF backend
- frontend/: Quasar (Vue 3) SPA
- docs/: Documentation (Markdown)
- docker/: Containerisation assets

## Quick Start (Development)

### Initial Setup (One-Time)

```bash
# Backend initialization
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createadmin  # Create admin user (replaces createsuperuser)
cd ..

# Frontend initialization
cd frontend
npm install
cd ..
```

### Start Services

Use the service management script to start/stop both backend and frontend:

```bash
# Start all services
./manage-services.sh start

# Check service status
./manage-services.sh status

# Stop all services
./manage-services.sh stop

# Restart all services
./manage-services.sh restart
```

**Service Locations:**
- Backend API: http://localhost:8000/api
- Frontend UI: http://localhost:5173
- Admin Panel: http://localhost:8000/admin
- Backend Logs: `var/logs/backend.log`
- Frontend Logs: `var/logs/frontend.log`

### Manual Service Control (if needed)

**Backend only:**
```bash
cd backend
source .venv/bin/activate
python manage.py migrate  # Run migrations if needed
python manage.py runserver 0.0.0.0:8000
```

**Frontend only:**
```bash
cd frontend
npm run dev
```

### Docker Setup (All Services)

```bash
cd docker
cp .env.example .env
docker compose up --build
```

Backend API will be available at http://localhost:8000/api

## Key Features

- **Device Management**: CRUD operations for SIP devices with flexible provisioning
- **Clone Device**: Rapid device provisioning by cloning existing configurations with intelligent line handling
- **Site & Line Management**: Organize devices into sites with multi-line support
- **Authentication**: Token-based authentication with local users and SAML SSO support
- **Role-Based Access Control**: Admin and Read-Only user roles with UI enforcement
- **User Management**: Admin-only user creation, password reset, and role assignment
- **REST APIs**: Comprehensive REST endpoints for all resources
- **Provisioning**: Deterministic configuration generation keyed by MAC address
- **Device Types**: Pluggable renderer framework with configurable options
- **Web UI**: Quasar SPA with dark mode and intuitive forms
- **Error Handling**: Comprehensive validation and user-friendly error messages
- **SSO Integration**: SAML 2.0 support for Microsoft Entra, Okta, and other IdPs

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and data model
- [Authentication](docs/AUTHENTICATION.md) - Login and token management
- [Deployment](docs/DEPLOYMENT.md) - Production deployment guide
- [Frontend Guidelines](docs/FRONTEND_GUIDELINES.md) - UI development standards
- [Device Type Options](docs/DEVICE_TYPE_OPTIONS.md) - Configuration schema system
- [Copilot Guidelines](.github/copilot-instructions.md) - AI coding standards

## License

GPL-3.0-or-later. See LICENSE.md for full text.
