# Device Type Common Options Rendering Implementation

## Overview
Implemented dynamic, schema-driven rendering of device type configuration options on the Device Types page. The frontend now interprets the `CommonOptions` JSON schema from device type plugins and renders appropriate UI controls.

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
          "uiOrder": 1                        // Sort order
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
- `checkbox` - Boolean toggle (q-checkbox)
- `select` - Dropdown with options (q-select)

**Key Features:**
- Sections sorted by `uiOrder`
- Options within sections sorted by `uiOrder`
- Mandatory field validation before save
- Default values loaded from schema or database
- Error display banner with extractErrorMessage pattern
- Loading state during save operation

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
  }
}
```

## Backend Implementation

### DeviceTypeConfigSerializer Changes

**New Fields:**
- `saved_values` - JSON field storing user-entered configuration values
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
