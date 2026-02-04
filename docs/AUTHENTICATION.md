# Authentication Flow

This document describes the authentication system implemented for the Phone Provisioning Manager.

## Overview

The application uses **Token-based Authentication** with the following components:

### Frontend
- **Login Page** (`src/pages/LoginPage.vue`): User login form with username/password
- **Auth Store** (`src/stores/auth.js`): Pinia store managing authentication state with localStorage persistence
- **API Client** (`src/api.js`): Axios instance with auto-token injection and 403 error handling
- **Router Guards** (`src/router/index.js`): Automatic redirection to login for unauthenticated users

### Backend
- **Login Endpoint** (`/api/auth/login/`): POST endpoint accepting username/password
- **Token Authentication**: Django REST Framework Token Auth for protected endpoints
- **Permission Classes**: `IsAdminOrReadOnly` (read for authenticated users, write for admins)
- **SSO Endpoints**: `/api/auth/saml/*` with SAML login and ACS callback

## Setup Instructions

### 1. Backend Configuration

The backend is already configured with:
- `rest_framework.authtoken` app installed
- Token authentication enabled in `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`
- Login endpoint implemented in `core/views.py`

Verify by checking `backend/phone_manager/settings.py` includes:
```python
INSTALLED_APPS = [
    ...
    "rest_framework.authtoken",
    ...
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    ...
}
```

### 2. Create Admin User

Create an admin account for testing:
```bash
cd backend
python manage.py createadmin
```

This command creates an admin user and profile (role=admin) in one step.

### 3. Frontend Configuration (Optional)

If your frontend dev server runs on a different port, set the environment variable:
```bash
export VITE_API_BASE=http://localhost:8000/api
```

Default is `http://localhost:8000/api`.

## Login Workflow

1. User navigates to `http://localhost:5173/` (or similar)
2. Router guard detects unauthenticated user and redirects to `/login`
3. LoginPage component displays username/password form
4. User submits credentials
5. Frontend POSTs to `/api/auth/login/` with credentials
6. Backend validates and returns:
   ```json
   {
     "token": "abc123xyz...",
     "user": {
       "id": 1,
       "username": "admin",
       "email": "admin@example.com",
       "is_staff": true,
       "role": "admin",
       "is_sso": false,
       "force_password_reset": false,
       ...
     }
   }
   ```
7. Auth store saves token and user to localStorage
8. Router redirects to `/devices`
9. All subsequent API requests include `Authorization: Token abc123xyz...` header

## API Requests

### Authenticated Request Example
```javascript
// All requests automatically include the token
const api = api.get('/device-types/');

// Header sent automatically:
// Authorization: Token abc123xyz...
```

### Response Handling
- **401/403**: Token expired or invalid → User redirected to login
- **200**: Normal response with data
- **4xx/5xx**: Standard error handling

## Logout

Users can logout by:
1. Clicking the logout button (circular icon) in the top-right toolbar
2. Token is cleared from localStorage
3. Router redirects to `/login`

## Security Notes

- Tokens are stored in localStorage (accessible to JavaScript)
- For production, consider:
  - HTTPS-only communication
  - HttpOnly cookie storage (requires backend changes)
  - Token refresh mechanism
  - CSRF protection headers
- Session tokens are tied to user accounts
- Implement token expiration for better security

## SSO Authentication

The backend supports SAML 2.0 SSO when enabled via config.

**Endpoints:**
- `GET /api/auth/config/` - Returns `{ "sso_enabled": true|false }`
- `GET /api/auth/saml/login/` - Initiate SSO flow
- `POST /api/auth/saml/acs/` - Assertion consumer service callback
- `GET /api/auth/saml/metadata/` - Service Provider metadata XML

See [docs/SSO_SETUP.md](SSO_SETUP.md) for complete SSO configuration.

## Testing the Authentication

### Via cURL
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# Use token in subsequent requests
curl http://localhost:8000/api/device-types/ \
  -H "Authorization: Token <token_from_login>"
```

### Via Frontend
1. Load http://localhost:5173/
2. Login with your superuser credentials
3. Navigate between pages
4. Check browser DevTools Network tab to see `Authorization` header

## Files Modified

- `frontend/src/pages/LoginPage.vue` - New login component
- `frontend/src/stores/auth.js` - Updated with token persistence
- `frontend/src/api.js` - New API client with auth interceptor
- `frontend/src/router/index.js` - Added auth guards
- `frontend/src/layouts/MainLayout.vue` - Added logout button
- `frontend/src/pages/*.vue` - Updated to use shared API client
- `backend/phone_manager/settings.py` - Added authtoken app
- `backend/phone_manager/urls.py` - Added login endpoint
- `backend/core/views.py` - Added login view

## Troubleshooting

### 403 Forbidden on API calls
- Verify user is logged in (check localStorage)
- Check that token is being sent in Authorization header
- Ensure user has appropriate permissions (must be authenticated at minimum)

### Login fails with "Invalid username or password"
- Verify user exists: `python manage.py shell` → `User.objects.all()`
- Verify password is correct
- Check browser console for error messages

### CORS errors
- Verify frontend URL is in `CORS_ALLOWED_ORIGINS` in settings.py
- Common origins: `http://localhost:5173`, `http://localhost:3000`, `http://127.0.0.1:9000`

### Token not working
- Ensure migrations ran: `python manage.py migrate`
- Check Token table exists: `python manage.py shell` → `Token.objects.all()`
- Regenerate token if needed: Delete token and login again

### Forced password reset
- If `force_password_reset` is true, user must change password via `POST /api/auth/change-password/`
- SSO users cannot change passwords via this endpoint
