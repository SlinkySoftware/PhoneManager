# Device Type Options - Quick Reference

## User Interface

### Accessing Device Type Options

1. **Navigate to Device Types page**
2. **Click "Common Options" button** next to a device type
3. **A dialog opens** displaying all configurable options organized by section

### Understanding the Interface

**Sections** - Grouped areas for related options (e.g., "SIP Registration", "Regional Settings")
- Appear as separate cards
- Ordered by `uiOrder` value
- Each section has a header with the friendly name

**Options** - Individual configuration fields
- Text input for string values
- Number input for numeric values
- Checkboxes for boolean settings
- Dropdowns for predefined choices
- Text areas for longer text

**Mandatory vs Optional**
- Fields marked "Required" cannot be saved if empty
- Optional fields can be left blank
- Validation happens before submission

### Saving Configuration

1. **Enter values** in all required fields
2. **Click "Save"** button
3. **Dialog closes** on success
4. **Values persist** to database

### Error Handling

- **Validation errors** - Field-level validation messages
- **Save errors** - Error banner displayed in dialog
- **Dialog stays open** on error so you can correct and retry

---

## Developer Reference

### Adding Device Type Options

Add `CommonOptions` to your device type renderer class:

```python
from .base import DeviceType

class MyDeviceType(DeviceType):
    TypeID = "MyDevice"
    Manufacturer = "Vendor"
    Model = "Model X"
    NumberOfLines = 4
    
    CommonOptions = {
        "sections": [
            {
                "friendlyName": "Basic Settings",
                "uiOrder": 1,
                "options": [
                    {
                        "optionId": "device_name",
                        "friendlyName": "Device Name",
                        "default": "",
                        "mandatory": True,
                        "type": "text",
                        "uiOrder": 1
                    }
                ]
            }
        ]
    }
    
    def render(self, device):
        # Access saved values here
        name = device.device_specific_configuration.get("device_name", "")
        # ... use in config generation
```

### Schema Structure

```
CommonOptions {
  sections: [
    {
      friendlyName: string         // Display name
      uiOrder: number              // Sort order (ascending)
      options: [
        {
          optionId: string          // Database key
          friendlyName: string      // UI label
          default: any              // Default value
          mandatory: boolean        // Required field
          type: string              // Input type
          uiOrder: number           // Sort order
          options?: string[]        // For select/multi-select (also accepts choices)
          choices?: string[]        // Alternate list name (supported by UI)
          doNotClone?: boolean      // Optional: If true, uses default instead of copying when device is cloned
        }
      ]
    }
  ]
}
```

### Device Defaults

Administrators can set per-device-type defaults for `DeviceSpecificOptions` via the "Edit Device Defaults" dialog. These values are stored in `device_defaults` on `DeviceTypeConfig` and applied when creating devices, changing device types, or resetting defaults in the Devices page.

### Input Types

| Type | Input Widget | Notes |
|------|--------------|-------|
| `text` | Text input | String values, default validators |
| `number` | Number input | Numeric values only |
| `textarea` | Multi-line text | For longer text content |
| `checkbox` / `boolean` | Boolean toggle | True/false values |
| `select` | Dropdown | Requires `options` or `choices` array |
| `multiselect` | Multi-select | Multiple selectable values |
| `orderedmultiselect` | Ordered multi-select | Priority ordering with up/down controls |
| `password` | Password input | Always cleared when device is cloned |

### Accessing Saved Values in Renderer

```python
def render(self, device):
    # Values saved by user via UI
    config = device.device_specific_configuration
    
    # Get with default fallback
    proxy = config.get("outbound_proxy", "")
    port = config.get("sip_port", 5060)
    enabled = config.get("snmp_enabled", False)
    
    # Use in config generation
    return f"proxy={proxy}:{port}\nenabled={enabled}"
```

### API Endpoints

**Get Current Configuration:**
```
GET /api/device-type-config/{typeId}/
Response: { common_options: {...}, saved_values: {...} }
```

**Save Configuration:**
```
POST /api/device-type-config/{typeId}/
Body: {
  "common_options": { /* schema */ },
  "saved_values": { /* user values */ }
}
```

---

## Examples

### Example 1: Simple Text Field

```python
{
    "optionId": "outbound_proxy",
    "friendlyName": "Outbound Proxy Server",
    "default": "",
    "mandatory": True,
    "type": "text",
    "uiOrder": 1
}
```

Frontend renders: Required text input with label "Outbound Proxy Server"

### Example 2: Number Field

```python
{
    "optionId": "port",
    "friendlyName": "SIP Port",
    "default": 5060,
    "mandatory": False,
    "type": "number",
    "uiOrder": 2
}
```

Frontend renders: Optional number input with default 5060

### Example 3: Dropdown Selection

```python
{
    "optionId": "time_zone",
    "friendlyName": "Time Zone",
    "default": "UTC",
    "mandatory": True,
    "type": "select",
    "uiOrder": 1,
    "options": ["UTC", "EST", "PST", "CST"]
}
```

Frontend renders: Required dropdown with 4 options

### Example 4: Boolean Checkbox

```python
{
    "optionId": "dhcp_enabled",
    "friendlyName": "Enable DHCP",
    "default": True,
    "mandatory": False,
    "type": "checkbox",
    "uiOrder": 3
}
```

Frontend renders: Optional checkbox with label "Enable DHCP"

---

## Troubleshooting

### Options Not Showing

- Verify `CommonOptions` is defined in device type class
- Check schema JSON is valid
- Clear browser cache and reload

### Values Not Saving

- Check browser console for error messages
- Verify mandatory fields have values
- Check backend logs: `tail var/logs/backend.log`

### Values Not Available in Renderer

- Verify saved values were submitted via API
- Check `device.device_specific_configuration` dict in renderer
- Use `.get()` with fallback defaults

---

## See Also

- [docs/DEVICE_TYPE_OPTIONS.md](DEVICE_TYPE_OPTIONS.md) - Full technical documentation
- [.github/COPILOT_GUIDELINES.md](.github/COPILOT_GUIDELINES.md) - Backend/frontend standards
- [docs/FRONTEND_GUIDELINES.md](FRONTEND_GUIDELINES.md) - UI component patterns

## New Renderer Docs

- [docs/POLYCOM_SOUNDPOINT_IP650_RENDERER.md](POLYCOM_SOUNDPOINT_IP650_RENDERER.md) - Polycom SoundPoint IP650 renderer
- [docs/GRANDSTREAM_HT812_RENDERER.md](GRANDSTREAM_HT812_RENDERER.md) - Grandstream HT812 renderer
