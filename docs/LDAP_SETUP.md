# LDAP Setup Guide

## Overview

The Phone Provisioning Manager supports three authentication methods:

1. Local Authentication: username/password stored in the application database
2. LDAP Authentication: username/password validated against a central LDAP directory
3. SAML SSO: single sign-on via Microsoft Entra, Okta, or other SAML 2.0 IdPs

LDAP users are auto-provisioned on first successful login and appear in the Users page with type `LDAP`.

## LDAP Authentication Architecture

The LDAP login flow uses a standard three-stage bind process:

1. Service-account bind: the application binds to LDAP using the configured Bind DN and Bind Password.
2. User lookup and authorization: the application searches the configured Base DN using the configured Search Filter, resolves the user DN, and reads group membership from the configured Group Attribute.
3. User bind: the application binds as the resolved user DN with the submitted password to verify credentials.

After successful authentication:

- The user is created locally if needed.
- `email`, `first_name`, and `last_name` are synchronized from `mail`, `givenName`, and `sn`.
- The role is assigned as `Admin` when the user matches `LDAP_ADMIN_GROUP_MAPPING`; otherwise `Read Only` if the user matches `LDAP_USER_GROUP_MAPPING`.

## Configuration

### config.yaml

The LDAP configuration is stored in `config.yaml` at the project root:

```yaml
LDAP_ENABLED: true
LDAP_DISPLAY_NAME: "Central Authentication"
LDAP_SERVER_NAME: "ldap.example.com"
LDAP_PORT: 636
LDAP_ENCRYPTION: "ssl"
LDAP_VALIDATE_CERTIFICATES: true
LDAP_BIND_DN: "CN=svc-phoneprov,OU=Service Accounts,DC=example,DC=com"
LDAP_BIND_PASSWORD: "replace-me"
LDAP_DOMAIN_NAME: "example.com"
LDAP_USERNAME_FORMAT: "%u@example.com"
LDAP_GROUP_ATTRIBUTE: "memberOf"
LDAP_ADMIN_GROUP_MAPPING:
  - "CN=PhoneManager_Admins,OU=Groups,DC=example,DC=com"
LDAP_USER_GROUP_MAPPING:
  - "CN=PhoneManager_Users,OU=Groups,DC=example,DC=com"
LDAP_BASE_DN: "DC=example,DC=com"
LDAP_SEARCH_FILTER: "(|(userPrincipalName=%u)(sAMAccountName=%r)(uid=%r)(cn=%r))"
```

### Configuration Reference

| Key | Description |
| --- | --- |
| `LDAP_ENABLED` | Enables LDAP authentication when `true` |
| `LDAP_DISPLAY_NAME` | Label used in the login-screen drop-down for central authentication |
| `LDAP_SERVER_NAME` | LDAP server hostname or IP |
| `LDAP_PORT` | LDAP listener port |
| `LDAP_ENCRYPTION` | Connection mode: `ssl`, `starttls`, or `none` |
| `LDAP_VALIDATE_CERTIFICATES` | Whether to validate the LDAP server certificate |
| `LDAP_BIND_DN` | Distinguished name of the service account used for the lookup bind |
| `LDAP_BIND_PASSWORD` | Password for the service account |
| `LDAP_DOMAIN_NAME` | Informational directory or domain name |
| `LDAP_USERNAME_FORMAT` | Template applied to the submitted username; `%u` is the entered username |
| `LDAP_GROUP_ATTRIBUTE` | LDAP attribute used to read group membership, for example `memberOf` |
| `LDAP_ADMIN_GROUP_MAPPING` | One or more LDAP groups that grant the Admin role |
| `LDAP_USER_GROUP_MAPPING` | One or more LDAP groups required for application access |
| `LDAP_BASE_DN` | Search base used when locating users |
| `LDAP_SEARCH_FILTER` | LDAP search filter used during user lookup; `%u` resolves to the formatted username and `%r` resolves to the raw username |

### Environment Variable Overrides

The application still supports environment variable overrides for operational deployments:

```bash
export LDAP_ENABLED=true
export LDAP_SERVER_NAME="ldap.example.com"
export LDAP_BIND_PASSWORD="super-secret"
```

If both `config.yaml` and environment variables are present, environment variables take precedence.

## Setup Instructions

### Step 1: Prepare LDAP Access

1. Create or identify a service account that can bind and search the user directory.
2. Confirm the service account can read the user DN, the attributes `mail`, `givenName`, and `sn`, and the configured group attribute.
3. Create or identify an access group for all allowed users and an admin group for privileged users.

### Step 2: Choose Connection Security

Use one of the following values for `LDAP_ENCRYPTION`:

- `ssl`: connect immediately over LDAPS, usually port `636`
- `starttls`: connect in cleartext and upgrade to TLS, usually port `389`
- `none`: unencrypted LDAP, recommended only for isolated test environments

Set `LDAP_VALIDATE_CERTIFICATES` to `true` in production. Set it to `false` only when testing with self-signed or otherwise untrusted certificates.

### Step 3: Define Username And Search Behavior

Set `LDAP_USERNAME_FORMAT` based on how your directory expects usernames:

- `%u@example.com`
- `cn=%u,ou=people,dc=example,dc=com`
- `%u`

Set `LDAP_SEARCH_FILTER` to match your directory schema. Common examples:

```yaml
LDAP_SEARCH_FILTER: "(userPrincipalName=%u)"
LDAP_SEARCH_FILTER: "(|(sAMAccountName=%r)(userPrincipalName=%u))"
LDAP_SEARCH_FILTER: "(&(objectClass=person)(uid=%r))"
```

Use `%u` when you want the already-formatted username and `%r` when you want the raw username the user typed.

### Step 4: Update config.yaml

Populate the LDAP section in `config.yaml` with your environment-specific values and save the file.

### Step 5: Restart The Application

```bash
./manage-services.sh restart
```

For Docker:

```bash
cd docker
docker compose restart
```

### Step 6: Test LDAP Login

1. Navigate to the login page.
2. Confirm the password-authentication drop-down defaults to `Central Authentication`.
3. Enter an LDAP-backed username and password.
4. Verify the user is redirected into the application.
5. Confirm the user appears in the Users page with type `LDAP`.

## Role Assignment Logic

### Access Control

- The user must match at least one entry in `LDAP_USER_GROUP_MAPPING`.
- If `LDAP_USER_GROUP_MAPPING` is empty, all authenticated LDAP users are allowed.

### Admin Role Assignment

- If the user matches `LDAP_ADMIN_GROUP_MAPPING`, the user is assigned the `Admin` role.
- Otherwise, the user is assigned the `Read Only` role.

Group matching is case-insensitive and supports both full DNs and simple common-name matches.

## Frontend Behavior

### Login Page

- The password-authentication drop-down always includes `Local Authentication`.
- `Central Authentication` is enabled only when `LDAP_ENABLED=true`.
- The drop-down defaults to Central Authentication whenever LDAP is enabled.
- SAML continues to appear as a separate button when `SSO_ENABLED=true`.

### Users Page

- LDAP users appear with type `LDAP`.
- LDAP users cannot have local passwords reset.
- LDAP users are deactivated instead of deleted.
- LDAP users are treated as centrally managed accounts.

## Troubleshooting

### Central Authentication Option Not Available

Check:

```bash
grep LDAP_ENABLED config.yaml
curl http://localhost:8000/api/auth/config/
```

The API response should include:

```json
{
  "ldap_enabled": true,
  "default_password_auth_method": "ldap"
}
```

### LDAP Login Fails With Invalid Username Or Password

Common causes:

1. `LDAP_USERNAME_FORMAT` does not match the target directory logon format.
2. `LDAP_SEARCH_FILTER` does not find the user.
3. The bind account can search the directory, but the user bind fails because the submitted password is wrong.

### Access Denied After Successful Directory Lookup

Common causes:

1. The user is not a member of any configured `LDAP_USER_GROUP_MAPPING` group.
2. `LDAP_GROUP_ATTRIBUTE` is wrong for your directory schema.
3. Group values in the directory do not match the configured mapping strings.

### TLS Or Certificate Errors

Common causes:

1. `LDAP_ENCRYPTION` does not match the server listener.
2. The directory certificate is not trusted by the host.
3. `LDAP_VALIDATE_CERTIFICATES=true` is set while using a self-signed test certificate.

Debug logs:

```bash
tail -f var/logs/backend.log
grep -i ldap var/logs/backend.log
```
