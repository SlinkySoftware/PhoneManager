# Phone Provisioning Manager Architecture

## System Overview

The Phone Provisioning Manager is a high-availability system for managing and provisioning SIP devices. It follows a stateless, horizontally scalable architecture with clear separation between configuration management through the admin API and device provisioning through phone-facing endpoints.

### Core Principles

1. **Stateless Backend**: No local file storage; all state persists in the database.
2. **Deterministic Rendering**: The same configuration produces the same output every time.
3. **Horizontal Scaling**: Multiple backend instances work independently behind a load balancer.
4. **Single Source of Truth**: PostgreSQL or SQLite holds all configuration state.
5. **Security**: Provisioning endpoints are intentionally unauthenticated, while admin endpoints require DRF token authentication.

## Technology Stack

### Backend

- **Framework**: Django 6.0.1 and Django REST Framework 3.15+
- **Database**: PostgreSQL 17 in production, SQLite 3 in development
- **Authentication**: Token-based authentication with DRF tokens
- **Python**: 3.10+
- **Key Libraries**: `pytz` for timezone support and `openpyxl` for bulk XLSX template generation and import parsing

### Frontend

- **Framework**: Vue 3 with Quasar v2.18
- **State Management**: Pinia
- **HTTP Client**: Axios
- **Build Tool**: Vite
- **Node**: 18+

### Infrastructure

- **Containerization**: Docker Compose
- **Process Management**: Shell scripts for development and `systemd` for production
- **Logging**: File-based logs under `var/logs/`

## Data Model

```text
Device
├── mac_address (unique, case-insensitive)
├── description (CharField, optional)
├── device_type_id (CharField)
├── site (FK → Site)
├── line_1 (FK → Line, primary)
├── lines (M2M → Line, additional lines beyond line_1)
├── line_configuration (JSON, per-line overrides and imported line order metadata)
├── device_specific_configuration (JSON)
├── enabled (boolean)
├── last_provisioned_at (DateTimeField, optional)
└── timestamps (created, updated)

Site
├── name (unique)
├── primary_sip_server (FK → SIPServer)
├── secondary_sip_server (FK → SIPServer, optional)
├── timezone (CharField, pytz choice)
├── primary_ntp_ip (GenericIPAddressField, optional)
├── secondary_ntp_ip (GenericIPAddressField, optional)
├── dial_plan (FK → DialPlan, optional)
└── timestamps (created, updated)

DialPlan
├── name (unique)
├── description (TextField, optional)
├── rules (O2M → DialPlanRule)
└── timestamps (created, updated)

DialPlanRule
├── dial_plan (FK → DialPlan)
├── input_regex (CharField, standard pattern)
├── output_regex (CharField, replacement with $1, $2)
├── sequence_order (PositiveIntegerField, execution order)
└── timestamps (implicit)

Line
├── name
├── directory_number (import workflows treat as unique; the current model does not enforce DB uniqueness)
├── registration_account
├── registration_password
├── phone_label (CharField, optional display label on phone)
├── is_shared (boolean)
└── timestamps (created, updated)

SIPServer
├── name (unique)
├── host (hostname or IP)
├── port (default 5060)
├── transport (TCP, UDP, or TLS)
└── timestamps (created, updated)

DeviceTypeConfig
├── type_id (unique device type identifier)
├── common_options (JSON schema plus saved values)
├── device_defaults (JSON per-device default values copied into new devices)
└── timestamps (created, updated)

UserProfile
├── user (OneToOne → auth.User)
├── role (CharField: 'admin' or 'readonly')
├── is_sso (BooleanField: SSO versus local authentication)
├── auth_source (CharField: local, ldap, or saml)
├── force_password_reset (BooleanField: requires password change)
└── timestamps (created, updated)
```

## Authentication And Authorization

### Authentication Methods

The system supports these authentication methods:

1. **Local Authentication**: Username and password stored in Django's auth system.
2. **LDAP Authentication**: Username and password validated against a central directory.
3. **SAML SSO**: Single Sign-On via SAML 2.0 for providers such as Microsoft Entra and Okta.

### Authentication Flow

#### Local Authentication Flow

```text
User enters credentials → POST /api/auth/login/
    ↓
Django validates username/password
    ↓
Check force_password_reset flag
    ↓ (if true)
Return token + redirect to /change-password
    ↓ (if false)
Return token + user profile
    ↓
Frontend stores token in localStorage
    ↓
Frontend includes token in Authorization header for all API calls
```

#### SAML SSO Flow

```text
User clicks "Sign in with SSO" → GET /api/auth/saml/login/
    ↓
Backend generates SAML AuthnRequest
    ↓
Redirect to IdP login page
    ↓
User authenticates with IdP
    ↓
IdP POSTs SAML assertion to POST /api/auth/saml/acs/
    ↓
Backend validates assertion
    ↓
Extract USER_CLAIM and ADMIN_CLAIM
    ↓
Auto-provision or update user in database
    ↓
Generate token
    ↓
Redirect to frontend with token as query parameter
    ↓
Frontend extracts token and stores it in localStorage
```

### Role-Based Access Control

Two user roles define API and UI behavior:

| Role | Access Level | UI Behavior | API Enforcement |
| ---- | ------------ | ----------- | --------------- |
| **Admin** | Full CRUD access to all resources | All forms and action buttons enabled; Users and Imports pages accessible | All protected HTTP methods allowed |
| **Read Only** | View-only access to all resources | Add, edit, delete, and import actions hidden or disabled; orange Read Only badge shown | Only `GET`, `HEAD`, and `OPTIONS` allowed |

#### Read-Only Viewing Mode

Read-only users can still inspect full configuration data through a dedicated view mode.

- **View Button**: An eye icon replaces the edit button.
- **Dialog Title**: Forms show `View` instead of `Edit`.
- **All Fields Disabled**: Inputs remain visible but cannot be changed.
- **No Save Button**: The dialog exposes only `Close`.
- **Applies To**: Devices, Lines, Sites, SIP Servers, and Device Types.

### Password Security

Password-bearing fields implement a consistent update pattern.

- **Blank on View**: Existing passwords display as placeholders such as `••••••••`.
- **Change Detection**: The UI tracks whether the password field was modified.
- **Visual Indicators**: A warning icon and helper message appear when a password will change.
- **Conditional Updates**: The API only writes password fields if the user provided a new value.
- **Applies To**: Line `registration_password` and device-specific password options.

### Permission Classes

#### IsAuthenticated

- Requires a valid token.
- Used for authenticated read access.

#### IsAdmin

- Requires `role='admin'`.
- Used for admin-only pages and actions such as user management and bulk import.

#### IsAdminOrReadOnly

- Allows read for all authenticated users and write only for admins.
- Used by resource ViewSets such as Devices, Lines, Sites, SIP Servers, Dial Plans, and Device Type Config.

Implementation pattern:

```python
def has_permission(self, request, view):
    if not request.user.is_authenticated:
        return False
    if request.method in SAFE_METHODS:
        return True
    return request.user.profile.role == 'admin'
```

### User Management

#### Admin-only capabilities

- Create new local users and generate temporary passwords.
- Edit user details such as name, email, role, and force-password-reset state.
- Reset local-user passwords.
- Delete local users or deactivate externally managed users.
- View all users with role and authentication source.
- Prevent self-modification for destructive or privilege-changing actions.

#### All users

- Change their own password if they are locally managed.
- View their own account details.
- See a `You` marker beside their row in the Users table.

#### Temporary password system

- New users receive a generated temporary password displayed once.
- `force_password_reset` is set to `true`.
- On first login, the user is redirected to `/change-password`.
- After a successful password change, `force_password_reset` is set to `false`.

### SSO User Auto-Provisioning

When a user authenticates via SAML:

1. Extract claims.
   - `USER_CLAIM` supplies the username, for example `john.doe@example.com`.
   - `ADMIN_CLAIM` supplies role or group data.
2. Determine role.
   - If `ADMIN_VALUE` is present, assign `admin`.
   - Otherwise assign `readonly`.
3. Create or update the local user record.
   - If the user is new, create `User` and `UserProfile`.
   - If the user already exists, update the role when required.
4. Generate a Django token and return control to the frontend.

### API Security

#### Protected endpoints

- All `/api/*` endpoints except the public auth endpoints require `Authorization: Token <token>`.
- The token is validated against the database.

#### Provisioning endpoints

- `/provision/<MAC>` is intentionally unauthenticated because phones identify by MAC address.
- Additional vendor-compatibility URL formats are accepted:
  - `/provision/<MAC>.cfg`
  - `/provision/<MAC>-phone.cfg`
  - `/provision/cfg<MAC>.xml`

#### CORS configuration

- Only the frontend origin should be allowed.
- Authenticated requests may include credentials where needed.

## API Architecture

### REST API Endpoints

#### Authentication (public)

- `POST /api/auth/login/`: Exchange credentials for a token.
- `POST /api/auth/ldap/login/`: Exchange LDAP credentials for a token.
- `GET /api/auth/config/`: Retrieve authentication configuration.
- `GET /api/auth/saml/login/`: Initiate SAML login.
- `POST /api/auth/saml/acs/`: SAML Assertion Consumer Service callback.
- `GET /api/auth/saml/metadata/`: Return SP metadata XML.

#### User management (admin only)

- `GET /api/users/`: List users.
- `POST /api/users/`: Create a local user.
- `DELETE /api/users/{id}/`: Delete or deactivate a user.
- `POST /api/users/{id}/reset_password/`: Reset a local-user password.
- `GET /api/imports/template/`: Download the bulk import workbook template.
- `POST /api/imports/upload/`: Upload a populated workbook for line and device creation.

#### Password management (authenticated)

- `POST /api/auth/change-password/`: Change the current user's password when locally managed.

#### Admin APIs (authenticated, write requires admin)

- `GET/POST /api/devices/`: List or create devices.
- `GET/PUT/DELETE /api/devices/{id}/`: Retrieve, update, or delete a device.
- `GET/POST /api/lines/`: List or create lines.
- `GET/POST /api/sites/`: List or create sites.
- `GET/POST /api/sip-servers/`: List or create SIP servers.
- `GET/POST /api/dial-plans/`: List or create dial plans.
- `GET/PUT /api/device-type-config/{type_id}/`: Manage device type configuration.

#### Provisioning endpoints (public)

- `GET /provision/<MAC>`: Return the rendered device configuration.
- `GET /provision/<MAC>.cfg`: Vendor compatibility format.
- `GET /provision/<MAC>-phone.cfg`: Polycom-style format.
- `GET /provision/cfg<MAC>.xml`: XML provisioning format.
- `GET /api/device-types/`: List available device types and option schemas.

#### Utility endpoints (public)

- `GET /api/timezones/`: List supported timezones with UTC offsets.

### Bulk Import Flow

The bulk import feature provides an admin-only onboarding path for batched line and device creation.

1. The frontend downloads a generated `.xlsx` template from `GET /api/imports/template/`.
2. The administrator populates the `Devices` and `Lines` sheets.
3. The frontend uploads the workbook with `POST /api/imports/upload/` as `multipart/form-data`.
4. The backend validates workbook structure, headers, row counts, and file size.
5. Line rows are validated and created first.
6. Device rows are validated against normalized MAC uniqueness, known Sites, known device `TypeID` values, line references from the same workbook, and per-model line capacity.
7. Each imported device is seeded from `DeviceTypeConfig.device_defaults`.
8. The backend returns imported and skipped counts plus row-level reasons for any skipped rows.

This flow is intentionally partial-success. Invalid rows are skipped instead of aborting the entire workbook.

### Device Rendering Pipeline

1. **Device Request**: A phone requests its configuration using a MAC address.
2. **Lookup**: The backend finds the device by MAC address.
3. **Validation**: The backend checks whether the device is enabled and supports the requested provisioning path.
4. **Renderer Selection**: The backend resolves the renderer class from the device `TypeID`.
5. **Configuration Generation**:
   - Load site configuration such as SIP servers, NTP servers, and timezone.
   - Load merged device-specific configuration.
   - Load assigned lines in their effective order.
   - Call the renderer's `render()` method.
6. **Response**: Return deterministically generated configuration text using the renderer's declared content type.

### Device Type System

Device types are Python classes implementing a common interface.

```python
class DeviceType:
    TypeID = "VendorModel"
    Manufacturer = "Vendor"
    Model = "Model X"
    NumberOfLines = 4
    ContentType = "text/xml"
    UserAgentPatterns = (
        r"VendorPattern1",
        r"VendorPattern2",
    )

    CommonOptions = {
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
                        "uiOrder": 1,
                    }
                ],
            }
        ]
    }

    DeviceSpecificOptions = {"sections": [...]} 

    def render(self, device: Device) -> str:
        config = device.get_decrypted_device_config()
        output = ""
        return output
```

## Frontend Architecture

### Page Structure

- **Pages**: Devices, Lines, Imports, Sites, Dial Plans, Device Types, Users, Change Password, and User Settings.
- **Components**: Reusable tables, dialogs, and forms.
- **Stores**: Pinia stores for auth state and session persistence.
- **Services**: Axios-based API client modules.
- **Default Landing Page**: Devices after successful login.

### Dial Plans Page

The Dial Plans page allows administrators to:

- Create named dial plans with ordered transformation rules.
- Configure input and output regex pairs for phone number transformations.
- Apply dial plans to sites during provisioning.
- Test renderer-specific conversions of dial plan logic.

### Table Features

- **Pagination**: Default 20 items per page.
- **Per-Page Options**: 20, 50, 100, or All.
- **Sortable Columns**: Click headers to sort.
- **Loading States**: Progress indicators during data fetch.
- **Action Buttons**: Context-aware actions such as Edit, View, Clone, and Delete.
- **Clone Operation**: Duplicate device configurations with shared-line preservation and `doNotClone` handling.

### Form Patterns

- Real-time validation with error messages.
- Change detection to prevent unintended data loss.
- Confirmation dialogs for destructive operations.
- Consistent backend error extraction and display.
- Loading states during asynchronous operations.
- **Password Security**: Blank placeholder fields, change tracking, and warning indicators.
- **Read-Only Mode**: Disabled fields, `View` title, no Save button, and Close instead of Cancel.
- **Bulk Upload Summary**: The Imports page shows imported counts, skipped counts, and row-level failure reasons.

### UI And UX Conventions

- **Color Coding**:
  - Primary blue for main actions and admin affordances.
  - Orange for read-only state, local auth labels, and password warnings.
  - Info cyan for SSO indicators and the `You` marker.
  - Teal or green for configuration sections and success states.
  - Negative red for destructive actions and error banners.
- **User Identification**: A `You` chip marks the current user.
- **Self-Protection**: The current user cannot edit, reset, or delete their own account.
- **Role Indicators**: Badges distinguish Administrator, Read Only, Local, LDAP, and SSO states.

### State Management

- **Auth Store**: Holds token, user metadata, and login or logout actions.
- **Session**: Persists auth state in `localStorage`.
- **Data Fetching**: Resource data is fetched on demand rather than duplicated in stores.

## Deployment Architecture

### Development

- `manage-services.sh` starts both services.
- Django `runserver` serves the backend.
- Vite serves the frontend.
- SQLite is used by default for local simplicity.

### Docker Compose

- Three main containers: backend, frontend, and PostgreSQL.
- Environment-driven configuration.
- Volume mounts for persistent state.
- Private network bridge for service communication.

### Production (Bare Metal)

- `systemd` service for backend application processes.
- Frontend served via Node.js or nginx depending on deployment strategy.
- TLS termination at a load balancer such as nginx or HAProxy.
- Dedicated database host or managed service with backups.
- Centralized or file-based log aggregation.

## Security Considerations

### Encryption

- **Fernet Symmetric Encryption**: Reversible encryption for stored credentials where provisioning needs plaintext at render time.
- **Password Storage**: Line registration passwords are encrypted in the database.
- **Decryption at Render**: Passwords are decrypted only when device configuration is generated.
- **Encryption Key**: Configured through `ENCRYPTION_KEY` or application config; development defaults must not be used in production.

### Provisioning Endpoint Security

- **Intentionally unauthenticated**: Phones cannot handle OAuth-style flows.
- **MAC-based identification**: Devices are identified by MAC address.
- **User-Agent Validation**: Device types can require expected provisioning request patterns.
- **Logging**: User-Agent mismatches and provisioning errors are logged.
- **Rate Limiting**: Recommended at the load balancer layer.
- **Error Masking**: Generic 404 or 403 responses reduce information leakage.

### Admin API Security

- **Token Authentication**: Required for protected write operations.
- **CORS Whitelist**: Only the intended frontend origin should be allowed.
- **HTTPS Required**: TLS termination should be enforced in front of the application.
- **Password Hashing**: Django's password hashing protects auth credentials.
- **Environment Variables**: Secrets live outside the repository.

## High Availability

### Stateless Design Enables

- Adding or removing backend instances without coordination.
- Routing requests to any healthy backend instance.
- Deterministic regeneration of configuration from the database.
- Horizontal scaling without shared local storage.

### Scaling Considerations

- **Vertical Scaling**: Increase server resources.
- **Horizontal Scaling**: Add backend instances behind a load balancer.
- **Database HA**: Use PostgreSQL replication or a managed HA offering.
- **Caching**: Safe where derived data remains deterministic.
- **CDN**: Static frontend assets are good CDN candidates.

## Extensibility

### Supported Device Types

- **Yealink SIP-T33G**: IP phone with 4 lines. See [YEALINK_SIP_T33G_RENDERER.md](YEALINK_SIP_T33G_RENDERER.md).
- **Yealink W70B DECT**: DECT base station with DECT handsets.
- **Polycom SoundPoint IP650**: IP phone with 6 lines. See [POLYCOM_SOUNDPOINT_IP650_RENDERER.md](POLYCOM_SOUNDPOINT_IP650_RENDERER.md).
- **Grandstream HT812**: ATA gateway with 2 FXS ports. See [GRANDSTREAM_HT812_RENDERER.md](GRANDSTREAM_HT812_RENDERER.md).
- **Example SIP Phone**: Reference implementation.

### Adding Device Types

1. Create a renderer class in `backend/provisioning/device_types/`.
2. Define `TypeID`, `Manufacturer`, `Model`, `NumberOfLines`, and `ContentType`.
3. Define `UserAgentPatterns` for provisioning validation.
4. Define `CommonOptions` and `DeviceSpecificOptions` schemas.
5. Implement `render()`.
6. Register the device type in `backend/provisioning/registry.py`.
7. Let the UI discover the new type automatically through the device-type API.

### Adding API Endpoints

1. Create or update the model in `backend/core/models.py`.
2. Create or update the serializer in `backend/core/serializers.py`.
3. Create the view or viewset in `backend/core/views.py`.
4. Register it in `backend/phone_manager/urls.py`.
5. Create the frontend service under `frontend/src/services/`.
6. Wire the frontend page or component that consumes it.

## Monitoring And Logging

### Backend Logging

- Requests are logged to backend log files.
- Provisioning mismatches and failures include device context where available.
- Failed authentication and authorization attempts are logged.
- Database and validation failures are logged with operational context.

### Frontend Logging

- Browser console errors remain available during development.
- API errors are surfaced to the user in the UI.
- Additional offline or service-worker logging is future work.

## Documentation Structure

- **BULK_IMPORTS.md**: Workbook template, endpoint contract, and import rules.
- **ARCHITECTURE.md**: System design and runtime behavior.
- **AUTHENTICATION.md**: Login flow and token handling.
- **DEPLOYMENT.md**: Deployment and operational setup.
- **SSO_SETUP.md**: SAML configuration guidance.
- **FRONTEND_GUIDELINES.md**: UI development patterns.
- **DEVICE_TYPE_OPTIONS.md**: Configuration schema system.
- **.github/copilot-instructions.md**: Development standards.
