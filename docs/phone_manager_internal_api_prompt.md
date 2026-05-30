# LLM Implementation Prompt 2: Phone Manager Internal API Extension

You are to extend the existing Phone Manager Django application with localhost-only internal endpoints required by a separate Yealink Phone Services application.

The Phone Services application is a standalone Django service mounted externally under `/services/`. It calls Phone Manager over localhost only to validate handset requests and to normalise user-entered call diversion destinations using Phone Manager's existing device, line, SIP credential, MAC normalisation, and dial-plan data.

This prompt is complete enough to start implementation. Do **not** make assumptions. If a critical detail is missing, stop and ask a precise clarifying question before coding.

---

## 1. Non-negotiable requirements

- Framework: Django, inside the existing Phone Manager application.
- Add localhost-only internal endpoints under `/internal/`.
- Do not expose these endpoints under `/api/`.
- Nginx must not proxy `/internal/` publicly.
- The endpoints are for server-to-server calls from the local Phone Services app only.
- Reuse existing Phone Manager models and helper functions wherever possible.
- Reuse the existing MAC normalisation function.
- Reuse existing device-to-line mapping.
- Reuse existing ordered regex dial-plan transformation model.
- Do not return SIP passwords or secret material.
- Do not modify device, line, or dial-plan data from these endpoints.
- Endpoints may be implemented as read-only POST/GET views even if the wider application has write capability.
- The implementation must include tests.

---

## 2. Background and integration context

Phone Manager provisions Yealink SIP-T33G handsets. Each SIP-T33G has a single configured line for this use case.

Phone Manager is authoritative for:

- MAC address normalisation
- whether a device exists
- whether the device is a SIP-T33G
- the line configured on that SIP-T33G
- the DN associated with that line
- the SIP registration password associated with that line
- the site/device dial plan
- ordered regex number transformation rules

A separate Phone Services app will call these internal endpoints using:

- MAC address
- DN
- token

The `token` is the first 8 characters of the configured line's SIP registration password. Token validation is case-sensitive.

The token is a lightweight validation guard, not a strong cryptographic authentication mechanism.

---

## 3. Endpoint 1: device context

Canonical URI:

```text
GET http://127.0.0.1:8000/internal/device-context/?mac=<MAC>&dn=<DN>&token=<TOKEN>
```

### 3.1 Purpose

Validate that a Phone Services request is associated with a known SIP-T33G device and known configured line.

### 3.2 Query parameters

Required:

```text
mac
dn
token
```

### 3.3 Validation rules

The endpoint must:

- normalise the supplied MAC using the existing Phone Manager MAC normalisation function
- find the device by normalised MAC
- verify the device exists
- verify the device model is `SIP-T33G`
- verify the device has exactly one configured line for this use case
- verify the supplied DN matches the configured line DN, allowing for known formatting differences if existing Phone Manager logic already supports them
- verify `token` equals the first 8 characters of the configured line's SIP registration password
- perform token comparison case-sensitively
- return `valid: false` if validation fails
- never return the SIP registration password
- never return the expected token

### 3.4 Successful response

Return JSON.

Suggested schema:

```json
{
  "valid": true,
  "mac": "805EC0ABCDEF",
  "model": "SIP-T33G",
  "dn": "+61288836500",
  "sip_username": "optional-if-useful",
  "line_count": 1,
  "device_name": "optional-phone-manager-name",
  "site": "2SYA",
  "dial_plan_id": "optional",
  "message": "OK"
}
```

Notes:

- `sip_username` may be returned if it is useful to the Phone Services application for cross-checking CUCM lookup context.
- Do not return SIP password, digest password, or token prefix.
- Include stable field names. Do not rename fields without updating the Phone Services prompt/contract.

### 3.5 Invalid response

For expected validation failures, return JSON with `valid: false`.

Suggested response:

```json
{
  "valid": false,
  "message": "Invalid device context"
}
```

Recommended HTTP status handling:

- `200` with `valid: true` for valid context.
- `200` with `valid: false` for expected validation failures, to simplify caller behaviour.
- `400` for malformed requests missing required parameters.
- `500` only for unexpected server faults.
- `503` only if a required internal dependency is unavailable.

---

## 4. Endpoint 2: normalise number

Canonical URI:

```text
POST http://127.0.0.1:8000/internal/normalize-number/
```

Use American spelling in the endpoint path exactly as shown: `normalize-number`.

### 4.1 Purpose

Normalise a user-entered call diversion destination using the configured device/site dial plan and ordered regex transformation rules.

The Phone Services app must not implement dial-plan transformation logic locally. This endpoint is the authority.

### 4.2 Request body

Canonical request JSON:

```json
{
  "mac": "805EC0ABCDEF",
  "dn": "+61288836500",
  "token": "abcd1234",
  "entered_destination": "0288836500"
}
```

Required fields:

```text
mac
dn
token
entered_destination
```

### 4.3 Validation rules

The endpoint must:

- validate device context using the same logic as `/internal/device-context/`
- reject invalid MAC/DN/token combinations
- apply existing ordered regex transformation rules associated with the device/site/line dial plan
- return the CUCM-ready `normalized_destination`
- ensure the result is suitable for CUCM Call Forward All destination use
- use `+E164` output format
- treat the supplied token case-sensitively
- never return SIP password or token prefix

### 4.4 Basic destination constraints

The Phone Services app will perform basic checks before calling this endpoint, but this endpoint must still validate defensively.

Apply at least:

- destination is not empty
- minimum length: 5 digits
- maximum length: 20 digits

If existing Phone Manager dial-plan validation has more precise constraints, use the existing model.

### 4.5 Successful response

Canonical response JSON:

```json
{
  "normalized_destination": "+61288836500"
}
```

Optional field:

```json
{
  "normalized_destination": "+61288836500",
  "matched": true
}
```

`matched` means whether an ordered regex transformation rule changed the number. If the number passed through unchanged, `matched` may be false.

### 4.6 Invalid response

For invalid destination:

```json
{
  "error": "Invalid Destination Specified"
}
```

Recommended HTTP status handling:

- `200` for successful normalisation.
- `400` for malformed request or invalid destination.
- `403` for invalid MAC/DN/token context.
- `500` for unexpected server faults.
- `503` for required internal dependency unavailable.

---

## 5. Routing and exposure requirements

Add Django routes:

```text
GET  /internal/device-context/
POST /internal/normalize-number/
```

The endpoints must be accessible from:

```text
http://127.0.0.1:8000/internal/device-context/
http://127.0.0.1:8000/internal/normalize-number/
```

They must not be exposed by Nginx publicly.

If there is existing middleware or routing that exposes `/api/`, do not place these views under `/api/`.

If possible, add an explicit localhost-only guard in Django so that requests from non-loopback addresses are rejected even if the reverse proxy is misconfigured.

Suggested behaviour for non-loopback request:

```json
{
  "error": "Not found"
}
```

or:

```json
{
  "error": "Forbidden"
}
```

Use whichever pattern is already standard in Phone Manager.

---

## 6. Security requirements

- Do not expose `/internal/` via public Nginx routes.
- Restrict internal endpoint access to loopback where practical.
- Do not return SIP password.
- Do not return token prefix.
- Do not log full SIP password.
- Avoid logging the supplied token unless existing debug logging policy explicitly allows it.
- If token must be logged for troubleshooting, mask it.
- Token comparison must be case-sensitive.
- Use constant-time comparison for token validation if practical.
- The token is the first 8 characters of the configured line's SIP registration password.

---

## 7. Data model expectations

Use existing Phone Manager concepts. Do not invent new persistent models unless strictly required.

The existing model is expected to include or be able to derive:

- Device
- MAC address
- Device model
- One or more Lines
- SIP credentials per line
- DN per line
- Site or site-equivalent context
- Dial plan associated with the device/site/line
- Ordered regex transformation rules

For SIP-T33G devices in this integration, there should be exactly one configured line.

If multiple lines are found for a SIP-T33G, return invalid context rather than guessing.

---

## 8. Number normalisation behaviour

Use existing ordered regex rules.

Expected behaviour:

1. Receive `entered_destination`.
2. Validate context using MAC, DN, and token.
3. Retrieve the associated dial plan for the device/site/line.
4. Apply ordered regex rules in configured order.
5. Return first successful transformation result.
6. If no rule changes the number but pass-through is valid according to the dial plan, return the original or canonicalised destination as `normalized_destination` and `matched: false`.
7. If no rule matches and pass-through is invalid, return `Invalid Destination Specified`.

Output format:

```text
+E164
```

Example output:

```text
+61288836500
```

---

## 9. Error messages

The Phone Services app displays only simple handset-facing messages. Keep API error messages stable.

Use this exact invalid destination text:

```text
Invalid Destination Specified
```

Use this exact invalid context text where applicable:

```text
Invalid device context
```

Avoid leaking internal model details to callers.

---

## 10. Logging

Log internal API requests sufficiently for troubleshooting.

Log at least:

- timestamp
- endpoint
- normalised MAC
- DN
- result
- validation failure reason category
- matched dial-plan rule ID/name if available
- whether normalisation changed the number

Do not log:

- SIP password
- token prefix
- full token unless masked and explicitly acceptable by existing logging policy

Destination numbers may be logged if this is already acceptable in Phone Manager logging policy.

---

## 11. Tests

Add tests for:

- successful device context validation
- invalid MAC
- unknown MAC
- non-SIP-T33G model
- DN mismatch
- invalid token
- token case sensitivity
- multiple-line SIP-T33G rejection
- MAC normalisation formats
- successful number normalisation
- ordered regex rule precedence
- pass-through unchanged number if valid
- invalid destination
- malformed JSON
- missing required fields
- non-loopback guard if implemented

Use existing Phone Manager test factories/patterns if available.

---

## 12. Suggested implementation shape

Suggested files, adapt to the existing project layout:

```text
phone_manager/
  internal_services/
    __init__.py
    urls.py
    views.py
    serializers.py
    services.py
    tests/
      test_device_context.py
      test_normalize_number.py
```

Suggested service functions:

```python
def get_device_context(mac: str, dn: str, token: str) -> DeviceContextResult:
    ...


def normalize_destination(mac: str, dn: str, token: str, entered_destination: str) -> NormalizeNumberResult:
    ...
```

Do not create a public REST API viewset unless that is the established internal pattern. These endpoints should be intentionally narrow.

---

## 13. Deliverables

Produce production-ready code including:

- Django URL routes for `/internal/device-context/` and `/internal/normalize-number/`
- view functions or class-based views
- service-layer validation logic
- reuse of MAC normalisation helper
- reuse of ordered regex dial-plan transformation logic
- tests
- short README or developer note describing the internal API contract
- Nginx note stating `/internal/` must not be proxied publicly

---

## 14. Explicitly do not implement

Do not implement:

- public `/api/` endpoints for this feature
- any UI
- persistent audit database
- modification of Phone Manager device, line, credential, or dial-plan records
- CUCM AXL integration
- Yealink XML rendering
- handset-facing `/services/` routes
- token generation beyond deriving the first 8 characters of the SIP registration password
- new dial-plan language if an ordered regex model already exists

---

## 15. Stop conditions

Stop and ask a clarifying question if any of these are missing or cannot be satisfied:

- existing MAC normalisation helper cannot be found
- line model does not expose SIP registration password
- device-to-line mapping is ambiguous
- SIP-T33G model identification is ambiguous
- DN comparison rules are unclear
- ordered regex dial-plan model cannot be identified
- +E164 output cannot be generated using existing rules
- localhost-only endpoint protection conflicts with existing deployment architecture
