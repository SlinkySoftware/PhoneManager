# Authentication Flow

This document describes the authentication system implemented for the Phone Provisioning Manager.

## Overview

The application uses token-based authentication for API access and supports three authentication sources:

1. Local authentication
2. LDAP authentication
3. SAML SSO authentication

All three sources return the same API token format after successful login. User records remain visible in the Users page with an `auth_source` of `local`, `ldap`, or `saml`.

### Frontend

- Login Page (`src/pages/LoginPage.vue`): user login form with a password-authentication method selector
- Auth Store (`src/stores/auth.js`): Pinia store managing authentication state with localStorage persistence
- API Client (`src/api.js`): Axios instance with automatic token injection and auth-error handling
- Router Guards (`src/router/index.js`): automatic redirection to login for unauthenticated users

### Backend

- Local Login Endpoint (`/api/auth/login/`): POST endpoint accepting locally managed username/password credentials
- LDAP Login Endpoint (`/api/auth/ldap/login/`): POST endpoint accepting central-directory username/password credentials
- Token Authentication: Django REST Framework token auth for protected endpoints
- Permission Classes: `IsAdminOrReadOnly` for resource APIs and `IsAdmin` for user-management APIs
- SSO Endpoints: `/api/auth/saml/*` for SAML login, ACS callback, and metadata

## Setup Instructions

### Backend Configuration

The backend requires:

- `rest_framework.authtoken` in `INSTALLED_APPS`
- Token authentication in `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`
- The authentication endpoints in `backend/core/views.py`

### Create an Admin User

Create an admin account for testing:

```bash
cd backend
python manage.py createadmin
```

### Frontend Configuration

If your frontend dev server runs on a different port, set the API base URL:

```bash
export VITE_API_BASE=http://localhost:8000/api
```

The default remains `http://localhost:8000/api`.

## Login Workflow

1. The user navigates to <http://localhost:5173/>.
2. The router redirects unauthenticated users to `/login`.
3. The login page shows a password-authentication selector with `Local Authentication` and `Central Authentication`.
4. The user submits credentials.
5. The frontend posts to `/api/auth/login/` for Local auth or `/api/auth/ldap/login/` for Central auth.
6. The backend validates credentials and returns a token plus user metadata.
7. The auth store saves the token and user data in localStorage.
8. The frontend redirects the user to `/devices`.
9. Subsequent API requests include `Authorization: Token <token>`.

Example login response:

```json
{
  "token": "abc123xyz...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "is_staff": true,
    "role": "admin",
    "auth_source": "local",
    "auth_type_label": "Local",
    "force_password_reset": false
  }
}
```

## Authentication Sources

### Local

- Credentials are stored in Django's user database.
- Password changes and forced password resets are supported in-app.
- Admins can create, edit, reset, and delete Local users.

### LDAP

- Credentials are validated against the configured LDAP directory.
- The backend uses a three-stage LDAP flow: service bind, user lookup and group validation, then user bind.
- LDAP users are auto-provisioned on first successful login.
- Password changes are handled by the directory, not by the application.

See [LDAP_SETUP.md](LDAP_SETUP.md) for the full LDAP configuration guide.

### SAML

- Authentication is delegated to a SAML 2.0 identity provider.
- SAML users are auto-provisioned on first successful login.
- Password changes are handled by the identity provider.

See [SSO_SETUP.md](SSO_SETUP.md) for the full SAML setup guide.

## Auth Configuration Endpoint

The frontend uses `GET /api/auth/config/` to decide which login methods to expose.

Example response:

```json
{
  "sso_enabled": true,
  "ldap_enabled": true,
  "ldap_display_name": "Central Authentication",
  "default_password_auth_method": "ldap"
}
```

When LDAP is enabled, the password-authentication selector defaults to `Central Authentication`.

## API Requests

All authenticated API requests include the token automatically:

```javascript
const response = await api.get('/device-types/');
```

The client sends:

```text
Authorization: Token abc123xyz...
```

## Logout

Users can log out from the toolbar. Logout clears the stored token and user data, then redirects back to `/login`.

## Testing Authentication

### cURL Examples

```bash
# Local login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# LDAP login
curl -X POST http://localhost:8000/api/auth/ldap/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "j.smith", "password": "your_password"}'

# Authenticated request
curl http://localhost:8000/api/device-types/ \
  -H "Authorization: Token <token_from_login>"
```

### Frontend Verification

1. Load <http://localhost:5173/>.
2. Verify the correct login methods are shown.
3. Log in with a test Local, LDAP, or SAML account.
4. Confirm the token is stored and protected APIs succeed.

## Troubleshooting

### 403 Forbidden On API Calls

- Verify the user is logged in and the token is present in localStorage.
- Verify the API client is sending the `Authorization` header.
- Verify the user has the necessary role for the requested action.

### Login Fails With Invalid Username Or Password

- Verify the user exists in the expected identity source.
- Verify the password is correct.
- Check the backend logs for Local, LDAP, or SAML-specific failures.

### CORS Errors

- Verify the frontend origin is present in `CORS_ALLOWED_ORIGINS`.
- Common development origins are `http://localhost:5173`, `http://localhost:3000`, and `http://127.0.0.1:9000`.

### Token Not Working

- Ensure migrations have been applied.
- Verify the DRF token table exists.
- Delete the stale token and log in again if needed.

### Forced Password Reset

- If `force_password_reset` is true, a Local user must change their password via `POST /api/auth/change-password/`.
- LDAP and SAML users cannot change passwords through the application.
