# SAML SSO Setup Guide

## Overview

The Phone Provisioning Manager supports three authentication methods:
1. **Local Authentication**: Username/password stored in application database
2. **LDAP Authentication**: Username/password validated against a central LDAP directory
3. **SAML SSO**: Single Sign-On via Microsoft Entra, Okta, or other SAML 2.0 IdPs

Both methods support role-based access control with Admin and Read-Only roles.

---

## Authentication Architecture

### Local Users
- Managed via Users page (admin-only access)
- Passwords stored with Django's PBKDF2 hasher
- Temporary password generation on creation with forced reset on first login
- Self-service password change via User Settings page

### SSO Users
- Auto-provisioned on first SAML login
- Role assigned based on SAML claims
- Password management handled by identity provider
- Account deactivated (not deleted) when removed to prevent auto-recreation

### Roles

| Role | Capabilities |
|------|--------------|
| **Admin** | Full access: Create, read, update, delete all resources. Manage users. |
| **Read Only** | View-only access: Can browse all pages but cannot create, edit, or delete. |

---

## Configuration

### config.yaml

The SAML configuration is stored in `config.yaml` at the project root:

```yaml
# Enable/disable SSO
SSO_ENABLED: false  # Set to true to enable SAML SSO

# Service Provider (SP) Settings - This Application
SAML_SP_ENTITY_ID: "http://localhost:8000/api/auth/saml/metadata/"
SAML_SP_ACS_URL: "http://localhost:8000/api/auth/saml/acs/"

# Identity Provider (IdP) Settings - Your SSO Provider
SAML_IDP_ENTITY_ID: ""  # From IdP metadata
SAML_IDP_SSO_URL: ""    # From IdP metadata
SAML_IDP_SLO_URL: ""    # Optional: Single Logout URL
SAML_IDP_X509_CERT: ""  # Base64-encoded certificate

# Claim Mapping
USER_CLAIM: "groups"  # SAML attribute name for user access
USER_CLAIM_VALUE: "PhoneManager_Users"  # Required value for access

ADMIN_CLAIM: "groups"  # SAML attribute name for admin role
ADMIN_CLAIM_VALUE: "PhoneManager_Admins"  # Value that grants admin role
```

### Environment Variable Overrides

Sensitive values can be overridden via environment variables:

```bash
export SSO_ENABLED=true
export SAML_IDP_ENTITY_ID="https://sts.windows.net/your-tenant-id/"
export SAML_IDP_SSO_URL="https://login.microsoftonline.com/your-tenant-id/saml2"
export SAML_IDP_X509_CERT="MIIC...base64cert..."
```

---

## Setup Instructions

### Step 1: Configure Identity Provider

#### Microsoft Entra (Azure AD)

1. **Create Enterprise Application**:
   - Navigate to Azure Portal → Azure Active Directory → Enterprise Applications
   - Click "New application" → "Create your own application"
   - Name: "Phone Provisioning Manager"
   - Select "Integrate any other application you don't find in the gallery (Non-gallery)"

2. **Configure SAML**:
   - Go to "Single sign-on" → Select "SAML"
   - **Basic SAML Configuration**:
     - Entity ID: `http://your-domain.com/api/auth/saml/metadata/`
     - Reply URL (ACS): `http://your-domain.com/api/auth/saml/acs/`
   - **User Attributes & Claims**:
     - Add group claim: "groups" (return Security groups as sAMAccountName)
   - **SAML Certificates**:
     - Download Base-64 certificate
     - Copy "Login URL" and "Azure AD Identifier"

3. **Create Security Groups**:
   - Azure Active Directory → Groups
   - Create "PhoneManager_Users" (all users)
   - Create "PhoneManager_Admins" (admin users)
   - Add users to appropriate groups

4. **Assign Users**:
   - Enterprise Application → Users and groups
   - Add users/groups to the application

#### Okta

1. **Create SAML Application**:
   - Admin Console → Applications → Create App Integration
   - Sign-in method: "SAML 2.0"
   - App name: "Phone Provisioning Manager"

2. **Configure SAML Settings**:
   - **General**:
     - Single sign-on URL: `http://your-domain.com/api/auth/saml/acs/`
     - Audience URI: `http://your-domain.com/api/auth/saml/metadata/`
     - Name ID format: "Unspecified"
   - **Attribute Statements** (optional):
     - Name: email, Value: user.email
     - Name: firstName, Value: user.firstName
     - Name: lastName, Value: user.lastName
   - **Group Attribute Statements**:
     - Name: groups
     - Filter: Matches regex `PhoneManager_.*`

3. **Create Groups**:
   - Directory → Groups
   - Create "PhoneManager_Users"
   - Create "PhoneManager_Admins"
   - Add users to groups

4. **Get IdP Metadata**:
   - View Setup Instructions
   - Copy "Identity Provider Issuer", "Identity Provider Single Sign-On URL"
   - Download X.509 Certificate

### Step 2: Update config.yaml

Update your `config.yaml` with values from IdP:

```yaml
SSO_ENABLED: true

SAML_SP_ENTITY_ID: "https://your-domain.com/api/auth/saml/metadata/"
SAML_SP_ACS_URL: "https://your-domain.com/api/auth/saml/acs/"

SAML_IDP_ENTITY_ID: "https://sts.windows.net/your-tenant-id/"  # From IdP
SAML_IDP_SSO_URL: "https://login.microsoftonline.com/your-tenant-id/saml2"  # From IdP
SAML_IDP_X509_CERT: "MIIC8DCCAdigAwIBAgIQf..."  # From IdP certificate (one line, no headers)

USER_CLAIM: "groups"
USER_CLAIM_VALUE: "PhoneManager_Users"

ADMIN_CLAIM: "groups"
ADMIN_CLAIM_VALUE: "PhoneManager_Admins"
```

**Important**: 
- Remove newlines, `-----BEGIN CERTIFICATE-----`, and `-----END CERTIFICATE-----` from certificate
- Ensure URLs match your deployment domain (use `https://` in production)

### Step 3: Restart Application

```bash
./manage-services.sh restart
```

Or for Docker:

```bash
cd docker
docker compose restart
```

### Step 4: Test SSO Login

1. Navigate to login page: `http://your-domain.com/login`
2. Click "Log in via SSO" button (should now be visible)
3. Redirected to IdP login page
4. After successful authentication:
   - User auto-created in application
   - Role assigned based on group membership
   - Redirected to dashboard

---

## Role Assignment Logic

### Access Control

**User Access (Required for any login)**:
- User MUST have `USER_CLAIM_VALUE` in their SAML assertion
- Without this claim, login is rejected with 403 Forbidden
- Example: User must be in "PhoneManager_Users" group

**Admin Role Assignment**:
- If user has both `USER_CLAIM_VALUE` AND `ADMIN_CLAIM_VALUE`: Assigned **Admin** role
- If user has only `USER_CLAIM_VALUE`: Assigned **Read Only** role
- Example: User in both "PhoneManager_Users" and "PhoneManager_Admins" → Admin

### Examples

| Groups | Access | Role |
|--------|--------|------|
| None | ❌ Denied | N/A |
| PhoneManager_Users | ✅ Granted | Read Only |
| PhoneManager_Admins (only) | ❌ Denied | N/A |
| PhoneManager_Users + PhoneManager_Admins | ✅ Granted | Admin |

---

## Frontend Changes

### Login Page

- **SSO Button**: Appears when `SSO_ENABLED=true`
- **Local Login**: Always available for local users
- Clicking "Log in via SSO" redirects to IdP

### User Interface

**For Read-Only Users**:
- Orange "Read Only" badge in header
- Add/Create buttons hidden
- Edit/Delete actions hidden in tables
- Dialog forms disabled (view-only mode)

**For Admin Users**:
- Full access to all features
- "Users" menu tab visible
- User management page accessible

---

## User Management (Admin Only)

### Creating Local Users

1. Navigate to Users page (admin-only menu item)
2. Click "Add User"
3. Enter username and select role
4. Click "Create User"
5. **Copy temporary password** (displayed once)
6. Communicate password to user out-of-band

### Password Management

**Admin-Initiated Reset**:
- Click "Reset Password" button for user
- New temporary password displayed (copy it)
- User must change on next login

**User-Initiated Change**:
- User Settings page → "Change Password" section
- Requires current password verification
- Only available for local users (SSO users redirected to IdP)

**Forced Password Reset**:
- Set automatically for new users and admin-reset passwords
- User redirected to Change Password page on next login
- Cannot access application until password changed

### SSO User Management

- SSO users auto-created on first login
- **Cannot delete SSO users** (they will be recreated)
- Instead, click "Delete" → Account is **deactivated** (not deleted)
- Deactivated users cannot log in
- To re-enable: Remove and re-add in Users page

---

## Troubleshooting

### SSO Button Not Showing

**Check**:
```bash
# Verify config
cat config.yaml | grep SSO_ENABLED

# Check API endpoint
curl http://localhost:8000/api/auth/config/
# Should return: {"sso_enabled": true}
```

### SAML Login Fails

**Common Issues**:

1. **Certificate Format Error**:
   - Ensure certificate is base64 string without headers
   - No newlines in certificate value
   
2. **Invalid Signature**:
   - Verify certificate matches IdP
   - Check IdP metadata has not changed

3. **Missing Claims**:
   - Check IdP sends "groups" attribute
   - Verify group names match `USER_CLAIM_VALUE` and `ADMIN_CLAIM_VALUE`

4. **URL Mismatch**:
   - Ensure SP URLs in config match IdP configuration exactly
   - Check protocol (http vs https)

**Debug Logs**:
```bash
# Backend logs
tail -f var/logs/backend.log

# Look for SAML errors
grep -i saml var/logs/backend.log
```

### Access Denied After Login

**Symptoms**: User authenticated by IdP but gets 403 error

**Causes**:
1. User not in `USER_CLAIM_VALUE` group (e.g., not in "PhoneManager_Users")
2. Claim mapping mismatch in config.yaml
3. IdP not sending group claims

**Resolution**:
- Add user to required group in IdP
- Verify IdP sends group claims in SAML assertion
- Check `USER_CLAIM` and `USER_CLAIM_VALUE` in config.yaml match IdP attribute names

### Role Not Updating

SSO user roles update automatically on each login based on current group membership. If role doesn't update:
1. Check user's current groups in IdP
2. Log out and log back in to refresh role
3. Verify claim values in backend logs

---

## API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login/` | POST | Local user login |
| `/api/auth/config/` | GET | Get SSO enabled status |
| `/api/auth/saml/login/` | GET | Initiate SAML login |
| `/api/auth/saml/acs/` | POST | SAML assertion consumer (callback) |
| `/api/auth/saml/metadata/` | GET | SP metadata XML for IdP |
| `/api/auth/change-password/` | POST | Change password (local users) |

### User Management (Admin Only)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/` | GET | List all users |
| `/api/users/` | POST | Create local user |
| `/api/users/{id}/` | DELETE | Delete/deactivate user |
| `/api/users/{id}/reset_password/` | POST | Reset user password |

---

## Security Considerations

1. **HTTPS Required**: SAML should always use HTTPS in production
2. **Certificate Validation**: Ensure IdP certificate is valid and current
3. **Token Expiration**: Tokens expire after configured duration
4. **Password Complexity**: Django validators enforce minimum 8 characters
5. **Temporary Passwords**: 16-character random alphanumeric + special chars
6. **Claim Validation**: Access denied if required claims missing

---

## Migration from Local to SSO

To migrate existing users to SSO:

1. **Enable SSO**: Set `SSO_ENABLED=true`
2. **Configure IdP**: Add users to IdP groups
3. **Users log in via SSO**: Accounts auto-created
4. **Deactivate local accounts**: Admin deletes/deactivates old local users
5. **SSO takes over**: All authentication via IdP

---

## Additional Resources

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) - System architecture with SAML flow
- [docs/DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide
- [config.yaml](../config.yaml) - Configuration file with examples
- [Microsoft Entra SAML Documentation](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-saml-single-sign-on)
- [Okta SAML Documentation](https://help.okta.com/en-us/content/topics/apps/apps_app_integration_wizard_saml.htm)

