```markdown
# Polycom SoundPoint IP650 Configuration Renderer

**Device Type ID:** `PolycomSoundPointIP650`  
**Manufacturer:** Polycom  
**Model:** SoundPoint IP650  
**Max Lines:** 6  
**Config Format:** XML (attributes on single <ALL> tag, Content-Type: `application/xml`)

## Overview

This document describes the configuration parameters produced by the Polycom SoundPoint IP650 renderer, where each parameter is rendered as an attribute (or P-code style element) inside the generated XML payload. It documents parameter keys, their sources (site, device, line, or UI CommonOptions), and notes about defaults.

---

## Regional & Date/Time

| Configuration Parameter | Value | Source | Notes |
|---|---:|---|---|
| `lcl.datetime.time.24HourClock` | `1` / `0` | Common Option: `clock_24hour` | 24/12 hour clock control |
| `lcl.datetime.date.format` | `DD/MM/YYYY`, `MM/DD/YYYY`, etc. | Common Option: `date_format` | Maps friendly label to Polycom format string |
| `lcl.ml.lang.clock.5.longFormat` | `1` / `0` | Common Option: `use_long_format` | Use long month/day names |
| `tcpIpApp.sntp.gmtOffset` | Seconds from GMT | Calculated from Site `timezone` | Renderer computes standard offset via `_get_gmt_offset()` |
| `tcpIpApp.sntp.daylightSavings.*` | Various DST fields | Calculated from Site `timezone` | `_calculate_dst_rules()` derives start/stop rules for device |
| `tcpIpApp.sntp.address` | IP | Site: `primary_ntp_ip` | Overrides DHCP when provided |

---

## Syslog

| Configuration Parameter | Value | Source | Notes |
|---|---:|---|---|
| `device.syslog.serverName` | IP/hostname | Device Common Option: `syslog_server` | Only included when set |
| `device.syslog.transport` | `1`/`2`/`3` | Device Option: `syslog_transport` | UDP/TCP/TLS mapped to numeric values |
| `device.syslog.facility` | Integer | Device Option: `syslog_facility` | Syslog facility number |
| `device.syslog.renderLevel` | Integer | Device Option: `syslog_renderLevel` | Friendly logging level mapped to numeric value |

---

## SIP & Registration

| Configuration Parameter | Value | Source | Notes |
|---|---:|---|---|
| `voIpProt.SIP.local.port` | e.g. `5060` | Common Option: `sip_local_port` | Local SIP port |
| `voIpProt.SIP.useRFC2543hold` | `1`/`0` | Common Option: `sip_use_rfc2543_hold` | RFC2543 hold support |
| `reg.X.server.1.register` | `1` | Assigned line | Registration enabled for line X |
| `reg.X.server.1.expires` | Seconds | Common Option: `sip_register_expires` | Registration expiry per account |
| `reg.X.server.1.retryTimeOut` | Milliseconds | Common Option: `sip_retry_timeout` | Retry timeout converted to ms |
| `reg.X.displayName` | From Line: `name` | Line | Display name for account |
| `reg.X.address` | From Line: `directory_number` | Line | SIP user / extension |

---

## Codecs & Priorities

The renderer accepts an ordered list `codec_priority_order` (Common Option) and maps it to Polycom-specific priority attributes:

- `audio.codecs.G722.priority`
- `audio.codecs.G711_A.priority`
- `audio.codecs.G711_Mu.priority`
- `audio.codecs.G729_AB.priority`

Unspecified codecs default to priority 0. The renderer assigns incremental priorities starting at 1 according to the orderedmultiselect.

---

## Device-Specific Options (Per-device UI schema)

- Administrative passwords: `device.auth.localAdminPassword`, `device.auth.localUserPassword` from `admin_password` / `user_password` options.
- Line ring tones and keys: `line_N_ring_tone`, `line_N_keys` exposed in `DeviceSpecificOptions` and mapped into per-line attributes.
- Dial plan inter-digit timeout: `inter_digit_timeout` controls digitmap timeout behavior.

Ring tone and date-format choices are provided by the renderer's `DEVICE_OPTIONS` schema; the UI presents friendly labels which the renderer maps to device strings.

---

## Dial Plan Conversion

The renderer converts the application's standard regex-style dial plan rules into a Polycom digitmap entry. Key points:

- Removes `^` / `$` anchors
- Supports capture groups `prefix(pattern)` and `$1` replacements
- Converts `X` → `x` and supports `*` as variable-length marker; results may include a trailing `T` to request inter-digit timeout
- When output requires a prefix replacement, the renderer emits replacement blocks using a `R<find>R<replace>R` convention before the digitmap pattern

Use the site-level `DialPlan` model to author rules; the renderer will transform them into device-ready entries.

---

## Timezone & DST Logic

The renderer determines standard GMT offset and DST transitions by sampling localized times across the year using `pytz`.

- `_get_gmt_offset(timezone_str)`: returns standard offset in hours (may be fractional)
- `_calculate_dst_rules(timezone_str)`: returns start/stop month, week, day-of-week and hour fields used by Polycom's daylight savings attributes

Fallback values default to disabling DST if rules cannot be reliably derived.

---

## Implementation Notes

- **Encryption**: Line passwords are stored encrypted in the DB and decrypted for rendering using the project's encryption utilities.
- **Content-Type**: `application/xml` is returned for Polycom configs.
- **Line Limit**: Supports up to 6 lines; unused slots are explicitly disabled.
- **MAC Normalization**: MACs normalized to lowercase with colons when used for hostnames or provisioning tracking.
- **Deterministic**: Same database input produces identical output; no randomness.

---

## Related Documentation

- [Device Type Options](DEVICE_TYPE_OPTIONS.md)
- [Device Type Options - Quick Reference](DEVICE_TYPE_OPTIONS_QUICK_REF.md)

```
