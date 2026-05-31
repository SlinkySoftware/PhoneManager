# Internal API

This document describes the localhost-only integration endpoints exposed by Phone Manager for trusted local services.

These endpoints are intentionally outside `/api/` and must be called directly on the backend listener, for example `http://127.0.0.1:8000/internal/...`.

## Security

- `/internal/` is for server-to-server traffic from the local host only.
- Public nginx configurations must not proxy `/internal/`.
- The Django views reject non-loopback requests and reject requests that carry non-loopback forwarded headers.
- The lightweight `token` check is derived from the first 8 characters of the line SIP registration password.
- SIP passwords and token prefixes are never returned by these endpoints.

## Device Context

Endpoint:

```text
GET /internal/device-context/?mac=<MAC>&dn=<DN>&token=<TOKEN>
```

Required query parameters:

- `mac`
- `dn`
- `token`

Behavior:

- Normalizes the supplied MAC using Phone Manager's existing MAC normalization helper.
- Resolves the device from Phone Manager's device inventory.
- Accepts only enabled `YealinkSIPT33G` devices whose registered renderer model is `SIP-T33G`.
- Requires exactly one configured line, using `Device.get_ordered_lines()`.
- Requires an exact DN match after trimming surrounding whitespace.
- Requires a case-sensitive constant-time comparison between `token` and the first 8 characters of the line registration password.

Successful response:

```json
{
  "valid": true,
  "mac": "805EC0ABCDEF",
  "model": "SIP-T33G",
  "dn": "+61288836500",
  "sip_username": "desk36500",
  "line_count": 1,
  "device_name": "Front Desk",
  "site": "2SYA",
  "dial_plan_id": 1,
  "message": "OK"
}
```

Expected validation failure response:

```json
{
  "valid": false,
  "message": "Invalid device context"
}
```

## Normalize Number

Endpoint:

```text
POST /internal/normalize-number/
```

Required JSON fields:

- `mac`
- `dn`
- `token`
- `entered_destination`

Behavior:

- Reuses the same device-context validation as `/internal/device-context/`.
- Validates and sanitizes the entered destination defensively.
- Applies the site's ordered `DialPlanRule` records through the shared `apply_dial_plan()` utility.
- Always returns the final sanitized destination in `normalized_destination`, whether a dial plan rule changed it or it passed through unchanged.
- Returns digit-only or `+digits` output depending on the dial plan result and the originally entered destination.

Successful response:

```json
{
  "normalized_destination": "+61288836500",
  "matched": true
}
```

Invalid destination response:

```json
{
  "error": "Invalid Destination Specified"
}
```

Invalid context response:

```json
{
  "error": "Invalid device context"
}
```

## Deployment Note

Do not publish `/internal/` through nginx or any other reverse proxy.

Allowed public backend paths are the documented application endpoints such as `/api/`, `/admin/`, and `/provision/`.
`/internal/` is reserved for localhost-only direct backend access.