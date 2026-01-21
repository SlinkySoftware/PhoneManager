# GitHub Copilot AI Coding Guidelines

**Project:** Phone Provisioning Manager
**Developer:** Slinky Software  
**License:** GPL-3.0-or-later

## Project Overview

This is a high-availability phone provisioning and configuration management system designed for stateless, multi-instance deployment. The system provisions SIP devices by serving vendor-specific configuration files over HTTP and provides a web UI for administrative management.

### Tech Stack
- **Backend:** Django 6.0.1, Django REST Framework, PostgreSQL 17 (SQLite3 for dev)
- **Frontend:** Quasar v2.18, Vue 3, Pinia, Axios
- **Authentication:** JWT (local users), SAML 2.0
- **Deployment:** Docker Compose, bare-metal Linux

### Architecture Principles
1. **Stateless Backend:** All Django instances must be stateless. No local file storage, all state in PostgreSQL.
2. **Deterministic Configuration:** Device configs generated on-demand from database state, never cached on disk.
3. **Horizontal Scaling:** Application must work with multiple backend instances behind a load balancer.
4. **Database-Driven:** Single source of truth is PostgreSQL/SQLite database.

---

## Development Environment Setup

### Python Virtual Environment
**IMPORTANT:** Always use the Python virtual environment when executing Python or pip commands in the backend.

**Before any backend Python/pip commands, activate the venv:**
```bash
cd backend
source .venv/bin/activate
```

Or use the venv Python directly without activation:
```bash
.venv/bin/python manage.py migrate
.venv/bin/pip install -r requirements.txt
```

---

## Code Standards

### General Rules
- **All source files MUST include GPL v3 header:**
  ```python
  # SPDX-License-Identifier: GPL-3.0-or-later
  # Copyright (c) <year> Slinky Software
  ```
  ```javascript
  /* SPDX-License-Identifier: GPL-3.0-or-later
   * Copyright (c) <year> Slinky Software
   */
  ```
- **Environment Variables:** Never hardcode secrets. Use environment variables with sensible defaults.
- **Logging:** Log all significant actions, especially provisioning requests and errors.
- **Error Handling:** Graceful error handling with meaningful messages for debugging.

### Python/Django Standards
- Follow PEP 8 style guide
- Use type hints where appropriate
- Maximum line length: 120 characters
- Use Django ORM exclusively (no raw SQL unless absolutely necessary)
- Database queries should use `select_related()` and `prefetch_related()` to avoid N+1 problems
- All models require `__str__()` methods
- Use Django's validation framework

**Example:**
```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) <year> Slinky Software

from django.db import models
from typing import Optional

class Device(models.Model):
    """Represents a physical SIP device."""
    mac_address = models.CharField(max_length=17, unique=True)
    friendly_name = models.CharField(max_length=255)
    
    def __str__(self) -> str:
        return f"{self.friendly_name} ({self.mac_address})"
```

### Vue/JavaScript Standards
- Use Vue 3 Composition API (not Options API)
- Use `<script setup>` syntax
- Follow ESLint and Prettier configurations
- Component names: PascalCase for files, kebab-case in templates
- Props and events should be documented with JSDoc comments
- Use Pinia stores for state management (not Vuex)
- API calls should go through centralized service modules
- **IMPORTANT:** Follow validation, error handling, and user feedback patterns documented in `docs/FRONTEND_GUIDELINES.md`
  - All form fields must have validation rules
  - All API errors must be displayed to users
  - All delete operations must have confirmation dialogs
  - Use consistent error message extraction patterns

**Example:**
```vue
<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) <year> Slinky Software -->

<template>
  <q-card>
    <q-card-section>{{ device.friendly_name }}</q-card-section>
  </q-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { deviceService } from '@/services/deviceService';

const device = ref(null);

onMounted(async () => {
  // Load device data
});
</script>
```

---

## Django Backend Guidelines

### Models (phoneprov/api/models.py)
- Use explicit field names (avoid ambiguous abbreviations)
- Include `help_text` for all fields
- Use `related_name` for foreign keys
- Add database indexes for frequently queried fields
- Use `choices` for enums instead of magic strings
- All timestamps: `auto_now_add=True` for created, `auto_now=True` for updated

### Serializers (phoneprov/api/serializers.py)
- One serializer per model (may have detail/list variants)
- Use `read_only_fields` for computed or auto-generated fields
- Validate data in `validate()` or `validate_<field>()` methods
- Keep business logic in models/views, not serializers

### Views (phoneprov/api/views.py)
- Use Django REST Framework ViewSets
- Authenticated endpoints require `permission_classes = [IsAuthenticated]`
- Use `@action` decorator for custom endpoints
- Return appropriate HTTP status codes (200, 201, 400, 404, 409, 500)
- Optimize queries with `select_related()`, `prefetch_related()`
- **Override `destroy()` method** to handle foreign key constraint violations gracefully

#### Error Handling in Views
All ViewSets should override the `destroy()` method to catch and handle database constraint violations:

```python
from django.db.models import ProtectedError
from django.db import IntegrityError

def destroy(self, request, *args, **kwargs):
    """Handle delete with foreign key constraint checking."""
    instance = self.get_object()
    try:
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    except ProtectedError as e:
        protected_objects = e.protected_objects
        count = len(protected_objects)
        return Response(
            {
                'detail': f'Cannot delete this {ModelName} as it is currently used by {count} related record(s). '
                          'Please reassign or delete those records first.',
                'error_code': 'foreign_key_constraint'
            },
            status=status.HTTP_409_CONFLICT
        )
    except IntegrityError as e:
        return Response(
            {
                'detail': 'Cannot delete this item due to database constraints. '
                          'It may be referenced by other records.',
                'error_code': 'integrity_error'
            },
            status=status.HTTP_409_CONFLICT
        )
```

**Key Points:**
- Use **HTTP 409 Conflict** for constraint violations (not 500)
- Always include a `detail` field with user-friendly message explaining WHY the operation failed
- Count and mention the number of related objects when possible
- Include an `error_code` for frontend categorization
- Messages should guide users toward resolution (e.g., "delete those records first")

### Provisioning Endpoints (phoneprov/provisioning/)
- **MUST be unauthenticated** (phones don't have credentials)
- **MUST log every request** to `ProvisioningLog` table
- Return 404 for unknown MACs, 403 for disabled devices, 200 with config for success
- Use `@csrf_exempt` decorator (phones don't have CSRF tokens)
- Handle MAC address normalization (case-insensitive, : vs - separators)

### Renderer System (phoneprov/provisioning/renderers/)
- Each vendor has a dedicated renderer class inheriting `DeviceType`
- Renderers MUST be deterministic (same input = same output)
- Configuration generated from database only, no external files
- Register new renderers in `RendererFactory.RENDERERS`
- Each renderer defines:
  - `TypeID` - Unique identifier for the device type
  - `Manufacturer` - Display name of vendor
  - `Model` - Display name of model
  - `NumberOfLines` - Maximum concurrent calls supported
  - `ContentType` - HTTP content-type for rendered output (e.g., `"text/xml"`, `"text/plain"`)
  - `CommonOptions` - JSON schema describing UI fields for user configuration

#### CommonOptions JSON Schema

Device types expose configuration options through a JSON schema that describes how to render UI controls:

```python
EXAMPLE_COMMON_OPTIONS = {
    "sections": [
        {
            "friendlyName": "SIP Registration",      # Display name for section
            "uiOrder": 1,                             # Sort order (ascending)
            "options": [
                {
                    "optionId": "outbound_proxy",    # Database key (stored in saved_values)
                    "friendlyName": "Outbound Proxy", # UI label
                    "default": "",                    # Default value
                    "mandatory": False,               # Required field
                    "type": "text",                   # Input type: text, number, select, textarea, checkbox
                    "uiOrder": 1,                     # Sort order within section
                    "options": []                     # For select type: available choices
                }
            ]
        }
    ]
}
```

**Frontend Implementation:**
- Parse `commonOptions` schema and render dynamic forms
- Group options by section
- Sort sections and options by `uiOrder`
- Support input types: `text`, `number`, `select`, `textarea`, `checkbox`
- Store user-entered values in `DeviceTypeConfig.common_options['_saved_values']`
- Values are accessible to renderers via `device.device_specific_configuration`

**Adding a New Renderer:**
```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) <year> Slinky Software

from phoneprov.provisioning.renderers.base import BaseRenderer
from phoneprov.api.models import Device

class CiscoRenderer(BaseRenderer):
    """Configuration renderer for Cisco SIP devices."""
    
    TypeID = "CiscoSIPPhone"
    Manufacturer = "Cisco"
    Model = "CP-7841"
    NumberOfLines = 4
    
    # Define configuration UI schema
    CommonOptions = {
        "sections": [
            {
                "friendlyName": "SIP Profile 1",
                "uiOrder": 1,
                "options": [
                    {
                        "optionId": "sip_server_1",
                        "friendlyName": "SIP Server",
                        "default": "",
                        "mandatory": True,
                        "type": "text",
                        "uiOrder": 1
                    }
                ]
            }
        ]
    }
    
    # HTTP Content-Type for rendered configuration
    # Set based on configuration format:
    # - "text/xml" for XML-based configs (Grandstream, Cisco, etc.)
    # - "text/plain" for key=value or ini-format configs (Yealink, Polycom, etc.)
    ContentType = "text/xml"
    
    def render(self, device: Device) -> str:
        # Get user-configured options
        sip_server = device.device_specific_configuration.get("sip_server_1", "")
        
        # ... generate config based on ContentType
        return config_xml
```

---

## Frontend Guidelines

### Project Structure
- **pages/**: Route components (one per page)
- **components/**: Reusable UI components
- **layouts/**: Page layouts (MainLayout, LoginLayout, etc.)
- **stores/**: Pinia state stores
- **services/**: API client modules
- **router/**: Vue Router configuration

### Routing (src/router/index.js)
- Protected routes require `meta: { requiresAuth: true }`
- Use lazy loading for page components: `component: () => import('@/pages/Dashboard.vue')`
- Redirect to `/login` if unauthenticated user accesses protected route

### State Management (src/stores/)
- Use Pinia with Composition API syntax
- Store JWT tokens in localStorage
- Auth store provides: `isAuthenticated`, `token`, `user`, `setToken()`, `logout()`
- Don't duplicate API data in stores (fetch on-demand)

### API Services (src/services/)
- Centralized in `deviceService.js`, `apiClient.js`
- All API calls use Axios with interceptors for auth headers
- Return raw Axios response (component handles data extraction)
- Handle errors gracefully with try/catch

**Example Service:**
```javascript
/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) <year> Slinky Software
 */

import apiClient from './api';

export const deviceService = {
  list: (params = {}) => apiClient.get('/api/devices/', { params }),
  
  get: (id) => apiClient.get(`/api/devices/${id}/`),
  
  create: (data) => apiClient.post('/api/devices/', data),
  
  update: (id, data) => apiClient.patch(`/api/devices/${id}/`, data),
  
  delete: (id) => apiClient.delete(`/api/devices/${id}/`)
};
```

### UI Components
- Use Quasar components (q-btn, q-table, q-card, etc.)
- Show loading states with `q-loading` or `:loading` props
- Display errors/success with `$q.notify()`
- Use `$q.dialog()` for confirmations (e.g., before delete)

---

## Database Guidelines

### Migrations
- Run `python manage.py makemigrations` after model changes
- Review generated migrations before committing
- Never edit existing migrations (create new ones)
- Test migrations on fresh database before production

### Queries
- Avoid N+1 queries: use `select_related()` for ForeignKey, `prefetch_related()` for ManyToMany
- Filter in database, not Python: `Model.objects.filter()` not list comprehension
- Use `only()` and `defer()` for large models if not all fields needed
- Add indexes to fields used in `filter()`, `order_by()`

---

## Security Guidelines

### Authentication & Authorization

**Authentication Methods:**
- **Local Users:** Username/password stored in Django's auth system
- **SAML SSO:** Single Sign-On via SAML 2.0 (Microsoft Entra, Okta, etc.)
- JWT tokens expire after 1 hour (refresh tokens after 7 days)
- Passwords stored with Django's PBKDF2 hasher (default)
- Never log passwords or tokens

**Role-Based Access Control:**

The system implements two user roles with different permission levels:

| Role | Access Level | API Permissions | UI Behavior |
|------|--------------|-----------------|-------------|
| **Admin** | Full CRUD access | All HTTP methods (GET, POST, PUT, PATCH, DELETE) | All buttons/forms enabled; Users page accessible; Edit/Delete buttons visible |
| **Read Only** | View-only access | Only safe methods (GET, HEAD, OPTIONS) | Add/Edit/Delete buttons hidden; Users page hidden; Orange "Read Only Mode" badge; View button with eye icon |

**Permission Classes:**

- `IsAuthenticated` - Requires valid JWT token (both roles can access)
  - Used for: Read endpoints (GET requests)
  
- `IsAdmin` - Requires `role='admin'` in UserProfile
  - Used for: User management page, admin-only actions
  
- `IsAdminOrReadOnly` - Allows read for all authenticated users, write only for admins
  - Used for: All resource ViewSets (Devices, Lines, Sites, SIPServers, DeviceTypeConfig)
  - Implementation checks `request.method in SAFE_METHODS` for read-only users
  - POST/PUT/PATCH/DELETE requests from read-only users return **HTTP 403 Forbidden**

**API Enforcement:**

All protected endpoints must use appropriate permission classes:

```python
from core.permissions import IsAdminOrReadOnly

class DeviceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]  # Read for all, write for admin only
    # ... rest of viewset
```

**Frontend Enforcement:**

- Read-only mode detected via: `authStore.user?.role !== 'admin'`
- All form fields: `:disable="isReadOnly"` to prevent editing
- Action buttons conditionally rendered based on role
- View button (eye icon) replaces Edit button for read-only users
- Save/Delete operations hidden when `isReadOnly === true`

**User Self-Protection:**

Users cannot modify their own accounts to prevent privilege loss:
- Edit/Reset Password/Delete buttons hidden for current user
- Comparison: `props.row.username === authStore.currentUser?.username`
- "You" chip displayed next to current user's username in Users table

### Provisioning Endpoint Security
- Provisioning endpoints are **intentionally unauthenticated** (phones identify by MAC)
- Log all requests with MAC, IP, User-Agent to `ProvisioningLog`
- Return generic errors to prevent information leakage
- Rate limiting recommended (future enhancement)

### CORS
- Whitelist frontend origin only in `CORS_ALLOWED_ORIGINS`
- Never use `CORS_ALLOW_ALL_ORIGINS = True` in production

### Environment Variables
- Store secrets in `.env` file (never commit `.env`)
- Provide `.env.example` with dummy values
- Use `os.getenv('KEY', 'default')` pattern

---

## Documentation Guidelines

### Code Comments
- Document WHY, not WHAT (code should be self-explanatory)
- Use docstrings for all functions/classes (Python)
- Use JSDoc for complex functions (JavaScript)

### API Documentation
- Keep [docs/API.md](../docs/API.md) updated with endpoint changes
- Include request/response examples
- Document all query parameters, request body fields, response fields

### Architecture Documentation
- Update [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for major design changes
- Document deployment changes in [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)

### Readme Documentation
- Update [README.md](../README.md) with high-level project infromation

---

## Deployment Considerations

### Docker
- All services defined in `docker-compose.yml`
- Use environment variables for configuration
- Volumes for persistence (Postgres data)
- Health checks for dependencies

### Bare Metal
- Scripts in `scripts/` for start/stop operations
- Use `venv` for Python dependencies
- Run gunicorn for production (not `runserver`)
- Use supervisor or systemd for process management

### Stateless Design
- Never store files on local filesystem (except logs)
- All state in database
- Configuration generated on-demand
- Can add/remove Django instances without coordination

---

## Common Patterns

### Python Commands in Backend
**Always use the venv when running Python or pip commands:**
```bash
# Option 1: Activate venv first
cd backend && source .venv/bin/activate && python manage.py migrate

# Option 2: Use venv Python directly (preferred for scripts)
.venv/bin/python manage.py migrate
```

### Adding a Device Type
1. Create renderer in `phoneprov/provisioning/renderers/<vendor>.py`
2. Ensure rendered exports the required fields
3. Register renderer in `RendererFactory`
4. Test with sample device

### Adding an API Endpoint
1. Create model (if needed) in `phoneprov/api/models.py`
2. Create serializer in `phoneprov/api/serializers.py`
3. Create viewset in `phoneprov/api/views.py`
4. Register in router in `phoneprov/api/urls.py`
5. Add frontend service method in `src/services/deviceService.js`
6. Create UI component/page to consume endpoint

### Adding a Frontend Page
1. Create Vue component in `src/pages/MyPage.vue`
2. Add route in `src/router/index.js`
3. Add navigation link in `src/layouts/MainLayout.vue`
4. Add API service calls as needed

---

## Questions to Ask Before Coding

1. **Does this maintain stateless backend?** (No local files, all DB)
2. **Is this secure?** (Auth required? Secrets in env?)
3. **Does this scale horizontally?** (Works with multiple instances?)
4. **Is this deterministic?** (Same input = same output?)
5. **Are GPL headers included?** (All source files)
6. **Are errors logged appropriately?** (Debugging info)
7. **Is documentation updated?** (API docs, architecture docs)

---

## Resources

- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design and architecture
- [docs/API.md](../docs/API.md) - REST API reference
- [docs/INSTALLATION.md](../docs/INSTALLATION.md) - Setup instructions
- [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Production deployment guide
- [docs/FRONTEND_GUIDELINES.md](../docs/FRONTEND_GUIDELINES.md) - Frontend validation, error handling, and UI patterns
- [docs/DEVICE_TYPE_OPTIONS.md](../docs/DEVICE_TYPE_OPTIONS.md) - Device type configuration schema and rendering
- [docs/DEVICE_TYPE_OPTIONS_QUICK_REF.md](../docs/DEVICE_TYPE_OPTIONS_QUICK_REF.md) - Quick reference for device type options
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [README.md](../README.md) - Project overview

---

**Remember:** This system must be stateless, scalable, and deterministic. All source code is GPL v3, copyright Slinky Software.
