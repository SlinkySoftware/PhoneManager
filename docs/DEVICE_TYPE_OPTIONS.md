# Device Type Common Options Rendering Implementation

## Overview
Implemented dynamic, schema-driven rendering of device type configuration options on the Device Types page. The frontend now interprets the `CommonOptions` JSON schema from device type plugins and renders appropriate UI controls.

Device-specific defaults are also configurable per device type. Administrators can set default values for `DeviceSpecificOptions` through an "Edit Device Defaults" dialog, which the Devices page uses when creating devices, changing device types, or resetting defaults.

## Architecture

### Data Flow
```
DeviceTypePlugin.CommonOptions (JSON schema)
    ↓
Frontend parses schema
    ↓
Renders sections and options dynamically
    ↓
User enters values
    ↓
Saved to DeviceTypeConfig.saved_values
    ↓
Available to renderer via device.device_specific_configuration
```

### Device Defaults Flow
```
DeviceTypePlugin.DeviceSpecificOptions (JSON schema)
  ↓
Frontend renders "Edit Device Defaults" dialog
  ↓
Administrator saves defaults
  ↓
Saved to DeviceTypeConfig.device_defaults
  ↓
Devices page applies defaults on create / type change / reset defaults
```

## Frontend Implementation

### DeviceTypesPage.vue Changes

**New Dialog Structure:**
- Opens common options dialog when "Common Options" button clicked
- Parses `selectedType.commonOptions.sections` array
- Dynamically renders form fields based on option type

**Schema Interpretation:**

```json
{
  "sections": [
    {
      "friendlyName": "SIP Registration",
      "uiOrder": 1,
      "options": [
        {
          "optionId": "outbound_proxy",        // Key for saving/loading
          "friendlyName": "Outbound Proxy",   // UI label
          "default": "",                       // Default value
          "mandatory": false,                  // Validation requirement
          "type": "text",                      // Input type
          "uiOrder": 1,                        // Sort order
          "doNotClone": false                  // Optional: If true, uses default instead of copying when device is cloned
        }
      ]
    }
  ]
}
```

**Supported Input Types:**
- `text` - Single-line text input (q-input)
- `number` - Numeric input with validation (q-input type="number")
- `textarea` - Multi-line text (q-input type="textarea")
- `checkbox` / `boolean` - Boolean toggle (q-checkbox)
- `select` - Dropdown with `options` or `choices` (q-select)
- `multiselect` - Multi-select list of options
- `orderedmultiselect` - Ordered dual-list selection with priority controls
- `password` - Password input with security features (always cleared on clone)

**Optional Schema Flags:**
- `doNotClone` - When `true`, this option will use its `default` value instead of copying from source device during Clone operation. Useful for device-specific settings like hostname, serial number, or MAC-dependent configurations that should not be duplicated.

**Key Features:**
- Sections sorted by `uiOrder`
- Options within sections sorted by `uiOrder`
- Mandatory field validation before save
- Default values loaded from schema or database
- Error display banner with extractErrorMessage pattern
- Loading state during save operation
- Reset to defaults action (restores schema defaults)
- Read-only view for non-admin users

### API Integration

**Endpoints:**
- `GET /device-type-config/{type_id}/` - Retrieve saved configuration
- `POST /device-type-config/{type_id}/` - Save configuration

**Request/Response:**
```javascript
POST /device-type-config/ExampleSIPPhone/
{
  "common_options": { /* full schema from device type */ },
  "saved_values": {
    "outbound_proxy": "proxy.example.com",
    "sip_profile_1_server": "sip.example.com",
    /* ... all configured values */
  },
  "device_defaults": {
    "sip_server": "sip.example.com",
    "codec_priority": ["g722", "g711u"],
    /* ... device-specific default values */
  }
}
```

## Backend Implementation

### DeviceTypeConfigSerializer Changes

**New Fields:**
- `saved_values` - JSON field storing user-entered configuration values
- `device_defaults` - JSON field storing per-device-type defaults for DeviceSpecificOptions
- Internal storage: values saved within `common_options['_saved_values']`

**Create/Update Behavior:**
- `POST` with `type_id` in URL creates or updates configuration
- Merges schema with saved values
- Returns both schema and current values in response

### DeviceTypeConfigViewSet

**Custom Logic:**
- `get_object()` - Lookup by `type_id` (not numeric ID)
- `create()` - Handles both create and update based on type_id existence
- Graceful handling of missing configurations (returns 404 with helpful message)

### URL Routes

Added to router:
```python
router.register(r"device-type-config", core_views.DeviceTypeConfigViewSet, basename="devicetypeconfig")
```

Supports:
- `GET /api/device-type-config/ExampleSIPPhone/`
- `POST /api/device-type-config/ExampleSIPPhone/`
- `PUT /api/device-type-config/ExampleSIPPhone/`

## Renderer Plugin Integration

### How Renderers Define Options

```python
class ExampleSIPPhone(DeviceType):
    TypeID = "ExampleSIPPhone"
    Manufacturer = "Slinky"
    Model = "Example 100"
    NumberOfLines = 2
    
    # Define UI schema
    CommonOptions = {
        "sections": [
            {
                "friendlyName": "SIP Registration",
                "uiOrder": 1,
                "options": [
                    {
                        "optionId": "outbound_proxy",
                        "friendlyName": "Outbound Proxy",
                        "default": "",
                        "mandatory": False,
                        "type": "text",
                        "uiOrder": 1,
                    }
                ]
            }
        ]
    }
    
    def render(self, device) -> str:
        # Access user-configured values
        proxy = device.device_specific_configuration.get("outbound_proxy")
        # ... use values in config generation
```

### Accessing Saved Values

In renderer's `render()` method:
```python
# Values saved by frontend are available here
outbound_proxy = device.device_specific_configuration.get("outbound_proxy", "")
sip_server = device.device_specific_configuration.get("sip_server_1", "")
speaker_volume = device.device_specific_configuration.get("speaker_volume", 5)
```

## Usage Example: Grandstream Device Type

Expected schema structure for Grandstream device:
```json
{
  "sections": [
    {
      "friendlyName": "SIP Profile 1",
      "uiOrder": 1,
      "options": [
        {
          "optionId": "sip_server_1",
          "friendlyName": "SIP Server",
          "default": "",
          "mandatory": true,
          "type": "text",
          "uiOrder": 1
        },
        {
          "optionId": "sip_port_1",
          "friendlyName": "Port",
          "default": 5060,
          "mandatory": false,
          "type": "number",
          "uiOrder": 2
        }
      ]
    },
    {
      "friendlyName": "Regional",
      "uiOrder": 2,
      "options": [
        {
          "optionId": "time_zone",
          "friendlyName": "Time Zone",
          "default": "UTC",
          "mandatory": false,
          "type": "select",
          "uiOrder": 1,
          "options": ["UTC", "EST", "CST", "PST"]
        }
      ]
    },
    {
      "friendlyName": "SNMP",
      "uiOrder": 3,
      "options": [
        {
          "optionId": "snmp_enabled",
          "friendlyName": "Enable SNMP",
          "default": false,
          "mandatory": false,
          "type": "checkbox",
          "uiOrder": 1
        }
      ]
    }
  ]
}
```

When user clicks "Common Options" on Grandstream device:
1. Frontend renders three sub-cards: "SIP Profile 1", "Regional", "SNMP"
2. Each card contains its configured options
3. User fills in values
4. Values saved to database
5. Next provisioning request includes these values

## Recent Updates

- **2026-02-05**: Added renderer documentation for Polycom SoundPoint IP650 and Grandstream HT812. See the dedicated renderer documents for parameter mappings, P-codes, XML examples and dial-plan conversion notes.
- **2026-02-04**: Dial plan transformation rules improved to support both Polycom digitmap and Grandstream dialplan syntax. Renderer implementations now handle conversion specifics; frontend schema rendering remains unchanged.


## Files Modified

### Frontend
- `frontend/src/pages/DeviceTypesPage.vue` - Complete rewrite with dynamic rendering

### Backend
- `backend/core/serializers.py` - Enhanced DeviceTypeConfigSerializer
- `backend/core/views.py` - Updated DeviceTypeConfigViewSet with custom logic
- `backend/phone_manager/urls.py` - Added device-type-config route

### Documentation
- `.github/COPILOT_GUIDELINES.md` - Added CommonOptions schema documentation

## Testing Checklist

- [ ] Navigate to Device Types page
- [ ] Click "Common Options" on a device type
- [ ] Verify schema renders correctly
- [ ] Sections appear in uiOrder sequence
- [ ] Options appear in uiOrder sequence within sections
- [ ] Text fields render as q-input
- [ ] Number fields render as q-input type="number"
- [ ] Mandatory fields show validation messages
- [ ] Save button submits form to /device-type-config/{typeId}/
- [ ] Configuration persists after reload
- [ ] Error messages display properly if save fails
- [ ] Device-specific_configuration contains saved values during rendering

## Future Enhancements

1. **More Input Types:**
   - `email` - Email validation
   - `url` - URL validation
   - `phone` - Phone number validation
   - `multiselect` - Multiple select with tags
   - `radio` - Radio button groups
   - `date`/`time` - Date/time pickers

2. **Advanced Features:**
   - Conditional options (show/hide based on other values)
   - Field dependencies and validation rules
   - File upload for configuration files
   - Import/export configuration templates
   - Configuration versioning

3. **Renderer Plugin Enhancement:**
   - Device-specific options rendering (separate from common)
   - Per-device configuration overrides
   - Configuration validation in renderer
   - Schema auto-discovery from device types

## Architecture Alignment

✅ **Stateless Backend** - Values stored in database, no session-based state
✅ **Deterministic Rendering** - Same config values produce same output
✅ **Schema-Driven UI** - Frontend controls completely defined by plugin schema
✅ **Frontend Guidelines Compliance** - Uses validation patterns, error handling, dialogs from FRONTEND_GUIDELINES.md
✅ **COPILOT_GUIDELINES** - Documented in backend and frontend guidelines
