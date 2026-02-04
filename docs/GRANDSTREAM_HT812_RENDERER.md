```markdown
# Grandstream HT812 Configuration Renderer

**Device Type ID:** `GrandstreamHT812`  
**Manufacturer:** Grandstream  
**Model:** HT812  
**Max Lines:** 2  
**Config Format:** XML (`text/xml`) - Grandstream provisioning XML with numbered P-parameters

## Overview

This document describes the Grandstream HT812 renderer: the UI-configurable options, mappings to Grandstream P-parameters, codec p-value mapping and dial-plan conversion rules used by the renderer.

---

## Common Options (UI)

Renderer exposes sections for SIP Parameters, Session Timer, RTP & Codecs, DTMF, Syslog, Regional, and SNMP. Key options include:

- `sip_transport` (UDP/TCP/TLS)
- `session_expiration` (s)
- `sip_keepalive_interval` (s)
- `preferred_codecs` (orderedmultiselect) → mapped to Grandstream p-values via `_codec_pvalues()`
- `dtmf_payload_id` and per-method selections (`dtmf_method_1..3`)
- `syslog_server` and `syslog_level`

These options are rendered into specific P-codes in the generated XML when applicable.

---

## Key P-Parameters & Mappings

The renderer sets a focused subset of Grandstream P-parameters (P-codes) used for provisioning. Examples included in output:

- Provisioning / server info: `P192`, `P237`, `P212` (provisioning server and protocol)
- Transport & RTP: `P130` (SIP transport), `P5004` (local RTP start port), `P84` (keepalive interval), `P2397` (enable keepalive)
- SIP servers: `P47` (primary SIP host), `P967` (secondary SIP host)
- DSCP: `P5046` (SIP DSCP), `P5050` (RTP DSCP)
- DTMF: `P79` (payload id), `P850`/`P851`/`P852` (method values)
- Codec tags: a series of P-codes (e.g., `P57...P62`, `P46`, `P98`) are filled with codec p-values derived from `preferred_codecs`
- DHCP and web UI ports: `P146` (DHCP hostname), `P901` (http port), `P27010` (https port)
- Dial plan application: `P2396` (FXS1 dial plan), `P2398` (FXS2 dial plan)
- SNMP: `P21896`, `P21897`, `P21898`, `P21902`, `P21900` when SNMP enabled

Refer to the configuration XML examples for exact P-parameter placements.

---

## Codec p-values

The renderer maps codec names to Grandstream internal p-values via `_codec_pvalues()` (example mapping):

- `PCMU` → `0`
- `PCMA` → `8`
- `G723` → `4`
- `G729` → `18`
- `G726-32` → `2`
- `iLBC` → `97`
- `OPUS` → `123`
- `G722` → `9`

These p-values populate the corresponding P-codes in priority order.

---

## DTMF Mapping

DTMF methods configured in the UI map to numeric codes used in the XML:

- `In-audio` → `100`
- `RFC2833` → `101`
- `SIP INFO` → `102`

Payload id is written to `P79`.

---

## Dial Plan Conversion

The renderer converts application-style regex rules into Grandstream dial-plan expressions:

- `X` → `x` (lowercase)
- `*` → `+` to indicate variable-length patterns (combined with `x+`)
- Capture groups `(pattern)` with `$1` in output are handled by output prefixing: produces constructs like `<0=+61>[23478]xxxxxxxxT` or `<=+61>000`
- Variable-length patterns receive a trailing `T` (inter-digit timeout marker)

When a site has a `DialPlan` configured, the renderer applies the converted rules to `P2396` and `P2398` for FXS ports.

---

## Regional Tones & Misc

- Optional AU regional tones are embedded into the XML when `region_tones` is enabled.
- Offhook autodial per-port fields (`P4210`, `P4211`) populated from device options `offhook_autodial_1/2`.

---

## Implementation Notes

- **Provisioning base URL**: The renderer includes provisioning server URL and protocol (`P192`, `P237`, `P212`) derived from `get_provisioning_base_url()`.
- **MAC formatting**: MAC is uppercased and emitted without separators in the `<mac>` tag.
- **Content-Type**: `text/xml` is returned for Grandstream configurations.
- **Partial P-coverage**: The renderer intentionally sets a compact, maintainable subset of P-codes — additional P-parameters can be added later as needed.

---

## Examples

See `configuration/examples/grandstream-ht812.xml` for a complete sample of the generated XML payload and `configuration/examples/grandstream-ht812-options.json` for sample CommonOptions values.

---

## Related Documentation

- [Device Type Options](DEVICE_TYPE_OPTIONS.md)
- [Device Type Options - Quick Reference](DEVICE_TYPE_OPTIONS_QUICK_REF.md)
- [Dial Plans](DIAL_PLANS.md)

```
