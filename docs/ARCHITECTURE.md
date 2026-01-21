# Phone Provisioning Manager Architecture

## System Overview

The Phone Provisioning Manager is a high-availability system for managing and provisioning SIP devices. It follows a stateless, horizontally-scalable architecture with clear separation between configuration management (admin API) and device provisioning (phone endpoints).

### Core Principles
1. **Stateless Backend**: No local file storage; all state persists in database
2. **Deterministic Rendering**: Same configuration produces same output every time
3. **Horizontal Scaling**: Multiple backend instances work independently behind a load balancer
4. **Single Source of Truth**: PostgreSQL/SQLite database holds all configuration
5. **Security**: Provisioning endpoints are unauthenticated (phones use MAC addresses), admin endpoints require JWT tokens

## Technology Stack

### Backend
- **Framework**: Django 6.0.1 + Django REST Framework 3.15+
- **Database**: PostgreSQL 17 (production) / SQLite 3 (development)
- **Authentication**: Token-based JWT
- **Python**: 3.10+
- **Key Libraries**: pytz (timezone support), Pillow (image handling)

### Frontend
- **Framework**: Vue 3 with Quasar v2.18
- **State Management**: Pinia
- **HTTP Client**: Axios
- **Build Tool**: Vite
- **Node**: 18+

### Infrastructure
- **Containerization**: Docker Compose
- **Process Management**: Shell scripts for development, systemd for production
- **Logging**: File-based (var/logs/)

## Data Model

```
Device
├── mac_address (unique, case-insensitive)
├── friendly_name
├── site (FK → Site)
├── line_1 (FK → Line, primary)
├── lines (M2M → Line, includes line_1)
├── device_specific_configuration (JSON)
├── enabled (boolean)
└── timestamps (created, updated)

Site
├── name (unique)
├── primary_sip_server (FK → SIPServer)
├── secondary_sip_server (FK → SIPServer, optional)
├── timezone (CharField, pytz choice)
├── primary_ntp_ip (GenericIPAddressField, optional)
├── secondary_ntp_ip (GenericIPAddressField, optional)
└── timestamps (created, updated)

Line
├── name
├── directory_number (unique)
├── registration_account
├── registration_password
├── is_shared (boolean)
└── timestamps (created, updated)

SIPServer
├── name (unique)
├── host (hostname/IP)
├── port (default 5060)
├── transport (TCP/UDP/TLS)
└── timestamps (created, updated)

DeviceTypeConfig
├── type_id (unique, device type identifier)
├── common_options (JSON schema + saved values)
└── timestamps (created, updated)

UserProfile
├── user (OneToOne → auth.User)
├── first_name (CharField: User's first name)
├── last_name (CharField: User's last name)
├── role (CharField: 'admin' or 'readonly')
├── is_sso (BooleanField: SSO vs local authentication)
├── force_password_reset (BooleanField: requires password change)
└── timestamps (created, updated)
```

## Authentication & Authorization

### Authentication Methods

The system supports two authentication methods:

1. **Local Authentication** - Username/password stored in Django's auth system
2. **SAML SSO** - Single Sign-On via SAML 2.0 (Microsoft Entra, Okta, etc.)

### Authentication Flow

#### Local Authentication Flow

```
User enters credentials → POST /api/auth/login/
    ↓
Django validates username/password
    ↓
Check force_password_reset flag
    ↓ (if true)
Return token + redirect to /change-password
    ↓ (if false)
Return token + user profile (username, role, is_sso)
    ↓
Frontend stores token in localStorage
    ↓
Frontend includes token in Authorization header for all API calls
```

#### SAML SSO Flow

```
User clicks "Sign in with SSO" → GET /api/auth/saml/login/
    ↓
Backend generates SAML AuthnRequest
    ↓
Redirect to IdP login page (Microsoft/Okta)
    ↓
User authenticates with IdP
    ↓
IdP POSTs SAML assertion to ACS endpoint → POST /api/auth/saml/acs/
    ↓
Backend validates SAML assertion
    ↓
Extract USER_CLAIM (username) and ADMIN_CLAIM (role)
    ↓
Auto-provision/update user in database
    ↓
Generate token
    ↓
Redirect to frontend with token as query parameter
    ↓
Frontend extracts token and stores in localStorage
```

### Role-Based Access Control

Two user roles with different permissions:

| Role | Access Level | UI Behavior | API Enforcement |
|------|--------------|-------------|------------------|
| **Admin** | Full CRUD access to all resources | All buttons/forms enabled; Users page accessible; View button shows "Edit" | All HTTP methods allowed on protected endpoints |
| **Read Only** | View-only access to all resources | Add/Edit/Delete buttons hidden; Users page hidden; Orange "Read Only Mode" badge shown; View button with eye icon allows viewing disabled forms | Only GET/HEAD/OPTIONS allowed; POST/PUT/PATCH/DELETE return 403 Forbidden |

#### Read-Only Viewing Mode

Read-only users can view complete configuration details through a "View" mode:
- **View Button**: Eye icon replaces Edit button for read-only users
- **Dialog Title**: Shows "View" instead of "Edit" when opened by read-only user
- **All Fields Disabled**: Form inputs are visible but cannot be modified (greyed out)
- **No Save Button**: Only "Close" button is available, not "Save"
- **Applies To**: All data pages (Devices, Lines, Sites, SIP Servers, Device Types)
- **Includes**: Device-specific configuration options and ordered multi-select fields

### Password Security

Password fields implement security best practices:
- **Blank on View**: When editing existing records, password fields show placeholder "••••••••" instead of actual values
- **Change Detection**: System tracks if password field has been modified
- **Visual Indicators**: Orange warning icon and "Password will be changed" message when modification detected
- **Conditional Updates**: API only updates passwords if user entered new value
- **Helper Text**: Shows "Leave blank to keep current password" for existing records
- **Applies To**: Lines (registration_password), Devices (device-specific password fields)

### Role-Based Access Control

Two user roles with different permissions:

| Role | Access Level | UI Behavior | API Enforcement |
|------|--------------|-------------|-----------------|
| **Admin** | Full CRUD access to all resources | All buttons/forms enabled; Users page accessible | All HTTP methods allowed on protected endpoints |
| **Read Only** | View-only access to all resources | Add/Edit/Delete buttons hidden; Users page hidden; Orange "Read Only Mode" badge shown | Only GET/HEAD/OPTIONS allowed; POST/PUT/PATCH/DELETE return 403 Forbidden |

### Permission Classes

**IsAuthenticated** - Requires valid token (both roles can access)
- Used for: Read endpoints (GET)

**IsAdmin** - Requires role='admin'
- Used for: User management page, admin-only actions

**IsAdminOrReadOnly** - Allows read for all authenticated users, write only for admins
- Used for: All resource ViewSets (Devices, Lines, Sites, SIPServers, DeviceTypeConfig)
- Implementation:
  ```python
  def has_permission(self, request, view):
      if not request.user.is_authenticated:
          return False
      if request.method in SAFE_METHODS:  # GET, HEAD, OPTIONS
          return True
      return request.user.profile.role == 'admin'
  ```

### User Management

**Admin-Only Capabilities:**
- Create new local users (generates 16-character temporary password)
- Edit existing users (change full name, email, role, force password reset)
- Reset user passwords (generates new temporary password)
- Delete/deactivate users (SSO users are deactivated, local users are deleted)
- View all users with role and authentication type
- **Self-Protection**: Cannot edit, reset password, or delete own account

**All Users:**
- Change their own password (local users only)
- View their account information
- See "You" chip next to their username in Users table

**User Interface Features:**
- Full Name field (first_name + last_name) displayed in user listings
- Edit User dialog for updating user details without changing password
- Force Password Reset checkbox (requires password change on next login)
- "You" chip indicator for current user in table
- Orange badges for "Local" and "Read Only" designations
- Action buttons hidden for current user (prevents self-modification)

**Temporary Password System:**
- New users receive a temporary password (displayed once)
- `force_password_reset` flag set to `true`
- On first login, user redirected to `/change-password`
- Must enter old password + new password (min 8 chars)
- After successful change, `force_password_reset` set to `false`

### SSO User Auto-Provisioning

When a user authenticates via SAML:

1. **Extract Claims:**
   - `USER_CLAIM` → Username (e.g., "john.doe@example.com")
   - `ADMIN_CLAIM` → Group membership or role claim

2. **Determine Role:**
   - If `ADMIN_VALUE` in user's claims → role='admin'
   - Otherwise → role='readonly'

3. **Create/Update User:**
   - Check if user exists (by username)
   - If new: Create User + UserProfile with is_sso=True
   - If existing: Update role if changed
   - No password required (SSO users can't use local login)

4. **Generate Token:**
   - Create Django Token for API authentication
   - Return token to frontend

### API Security

**Protected Endpoints:**
- All `/api/*` endpoints except `/api/auth/login/`, `/api/auth/config/`, `/api/auth/saml/*`
- Require `Authorization: Token <token>` header
- Token validated against database

**Provisioning Endpoints:**
- `/provision/<MAC>` is **intentionally unauthenticated** (phones use MAC address for identification)
- All requests logged to ProvisioningLog table

**CORS Configuration:**
- Whitelist frontend origin only
- Credentials allowed for authenticated requests

## API Architecture

### REST API Endpoints

**Authentication** (Public)
- `POST /api/auth/login/` - Exchange credentials for token
- `GET /api/auth/config/` - Get SSO configuration status
- `GET /api/auth/saml/login/` - Initiate SAML login flow
- `POST /api/auth/saml/acs/` - SAML Assertion Consumer Service (IdP callback)
- `GET /api/auth/saml/metadata/` - Service Provider metadata XML

**User Management** (Requires Admin Role)
- `GET /api/users/` - List all users
- `POST /api/users/` - Create new local user
- `DELETE /api/users/{id}/` - Delete local user or deactivate SSO user
- `POST /api/users/{id}/reset_password/` - Reset user password

**Password Management** (Requires Authentication)
- `POST /api/auth/change-password/` - Change own password (local users only)

**Admin APIs** (Requires Authentication, Write requires Admin Role)
- `GET/POST /api/devices/` - List/create devices
- `GET/PUT/DELETE /api/devices/{id}/` - Retrieve/update/delete device
- `GET/POST /api/lines/` - Manage phone lines
- `GET/POST /api/sites/` - Manage sites
- `GET/POST /api/sip-servers/` - Manage SIP servers
- `GET/PUT /api/device-type-config/{type_id}/` - Manage device type configurations

**Provisioning Endpoints** (Public, unauthenticated)
- `GET /provision/<MAC>` - Returns device configuration file
- `GET /api/device-types/` - List available device types with options

**Utility Endpoints** (Public)
- `GET /api/timezones/` - List all timezones with UTC offsets

### Device Rendering Pipeline

1. **Device Request**: Phone requests config with MAC address
2. **Lookup**: Backend finds device by MAC in database
3. **Validation**: Check if device is enabled and assigned to site
4. **Renderer Selection**: Look up device type and load renderer class
5. **Configuration Generation**:
   - Load site configuration (SIP servers, NTP servers, timezone)
   - Load device-specific configuration (user-entered options)
   - Load assigned lines
   - Call renderer's `render()` method with all data
6. **Response**: Return deterministically-generated configuration file

### Device Type System

Device types are Python classes implementing a common interface:

```python
class DeviceType:
    TypeID = "VendorModel"           # Unique identifier
    Manufacturer = "Vendor"           # Display name
    Model = "Model X"                 # Display model
    NumberOfLines = 4                 # Max concurrent calls
    
    CommonOptions = {                 # User-configurable options
        "sections": [
            {
                "friendlyName": "SIP Settings",
                "uiOrder": 1,
                "options": [
                    {
                        "optionId": "sip_server",
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
    
    def render(self, device: Device) -> str:
        """Generate configuration file content."""
        config = ""
        # Build device config using device properties
        return config
```

## Frontend Architecture

### Page Structure
- **Pages**: Route components (Devices, Lines, Sites, Device Types, Users, Change Password, User Settings)
- **Components**: Reusable UI elements (tables, dialogs, forms)
- **Stores**: Pinia stores for auth state and session
- **Services**: API client modules with Axios
- **Default Landing Page**: Devices page after login

### Table Features
- **Pagination**: Default 20 items per page
- **Per-Page Options**: 20, 50, 100, All
- **Sortable Columns**: Click headers to sort
- **Loading States**: Progress indicators during data fetch
- **Action Buttons**: Context-aware based on user role (Edit/View/Delete)
- **Row Selection**: Unique ID-based selection

### Form Patterns
- Real-time validation with error messages
- Change detection to prevent unintended data loss
- Confirmation dialogs for destructive operations
- Proper error extraction and display
- Loading states during async operations
- **Password Security**: Blank placeholder fields ("••••••••"), change tracking with visual warnings
- **Read-Only Mode**: Disabled fields, "View" title, no Save button, Close instead of Cancel

### UI/UX Conventions
- **Color Coding**:
  - Primary (blue): Admin role, primary actions
  - Orange: Read Only role, Local auth type, password change warnings
  - Info (cyan): SSO auth type, "You" chip for current user
  - Teal/Green: Device configuration sections, success states
  - Negative (red): Delete actions, error messages
- **User Identification**: "You" chip displayed next to current user's username
- **Self-Protection**: Current user cannot modify their own account (no Edit/Reset/Delete buttons)
- **Role Indicators**: Badges show Administrator/Read Only and SSO/Local

### State Management
- **Auth Store**: JWT token, user info, login/logout
- **Session**: localStorage persistence of token
- **Data**: Fetch on-demand (no duplication in stores)

## Deployment Architecture

### Development
- `manage-services.sh` script starts both services
- Django runserver for backend
- Vite dev server for frontend
- SQLite database for simplicity

### Docker Compose
- Three containers: backend, frontend, PostgreSQL
- Environment-driven configuration
- Volume mounts for data persistence
- Network bridge for service communication

### Production (Bare Metal)
- systemd service for backend (gunicorn + PostgreSQL)
- systemd service for frontend (Node.js or served by nginx)
- Load balancer (nginx/HAProxy) terminating TLS
- Separate database server with backups
- Log aggregation from var/logs/

## Security Considerations

### Provisioning Endpoint Security
- **Intentionally unauthenticated**: Phones cannot handle OAuth
- **MAC-based identification**: Device identified by MAC address
- **Logging**: All provisioning requests logged to ProvisioningLog
- **Rate limiting**: Recommended at load balancer level
- **Error masking**: Generic 404/403 to prevent info leakage

### Admin API Security
- **Token authentication**: Required for all write operations
- **CORS whitelist**: Only frontend origin allowed
- **HTTPS required**: Use TLS termination at load balancer
- **Password hashing**: Django's PBKDF2 hasher for auth
- **Environment variables**: Secrets in .env, never committed

## High Availability

### Stateless Design Enables:
- Add/remove backend instances without coordination
- Load balancer can route requests to any instance
- Database is single point of consistency (not availability)
- Caching feasible since config is deterministic

### Scaling Considerations
- **Vertical**: Increase server resources
- **Horizontal**: Add backend instances behind load balancer
- **Database**: PostgreSQL replication for HA
- **Caching**: Frontend caching of device configs possible
- **CDN**: Configuration files could be served from CDN

## Extensibility

### Adding Device Types
1. Create renderer class in `backend/provisioning/device_types/`
2. Define `CommonOptions` schema for configuration UI
3. Implement `render()` method
4. Register in `RendererFactory.RENDERERS` dict
5. UI automatically generates configuration forms

### Adding API Endpoints
1. Create/update model in `backend/core/models.py`
2. Create serializer in `backend/core/serializers.py`
3. Create viewset in `backend/core/views.py`
4. Register in router in `backend/phone_manager/urls.py`
5. Frontend service calls and UI automatically work

## Monitoring & Logging

### Backend Logging
- All requests logged to var/logs/backend.log
- Provisioning requests logged with MAC, IP, outcome
- Failed authentication/authorization logged
- Database errors logged with context

### Frontend Logging
- Browser console errors captured
- API errors displayed to user
- Service worker logs for offline capability (future)

## Documentation Structure

- **ARCHITECTURE.md**: This file - system design and flow
- **AUTHENTICATION.md**: Login flow and JWT token management
- **DEPLOYMENT.md**: Production deployment checklist (includes SSO setup)
- **SSO_SETUP.md**: Comprehensive SAML SSO configuration guide
- **FRONTEND_GUIDELINES.md**: UI development patterns
- **DEVICE_TYPE_OPTIONS.md**: Configuration schema system
- **.github/copilot-instructions.md**: Development standards
