# Phone Provisioning Manager Architecture

## Overview
- Backend: Django + DRF, stateless, PostgreSQL preferred (SQLite for dev)
- Frontend: Quasar (Vue 3) SPA, dark mode + green theme
- Provisioning: HTTP endpoints keyed by MAC address returning deterministic config
- Deployment: Bare metal or Docker Compose (frontend + backend + Postgres)

## Data Model (Backend)
- Device (MAC, description, device_type_id, site, primary line, extra lines M2M, device_specific_configuration JSON, enabled)
- DeviceTypeConfig (type_id, common_options JSON)
- Line (name, directory_number, registration_account, registration_password, is_shared)
- Site (name, primary_sip_server, secondary_sip_server)
- SIPServer (name, host, port, transport)

## Device Type Rendering
- Each renderer is a Python class exposing TypeID, Manufacturer, Model, NumberOfLines, CommonOptions, DeviceSpecificOptions, render()
- Registry lives in backend/provisioning/registry.py
- Example renderer: ExampleSIPPhone

## API Surface
- CRUD: devices, lines, sites, sip-servers
- Device types: list renderers; read/write common options via type_id
- Provisioning: GET /provision/<MAC> returns text config

## Frontend (Planned)
- Quasar SPA with Pinia store for auth/session
- Axios for API calls
- Dynamic forms driven by options JSON (sections/options ordered by uiOrder)

## Deployment
- Environment-driven configuration via .env files (backend/.env, docker/.env)
- Docker Compose includes backend, frontend, postgres
- GPLv3 licensed; ensure headers and docs reference licensing
