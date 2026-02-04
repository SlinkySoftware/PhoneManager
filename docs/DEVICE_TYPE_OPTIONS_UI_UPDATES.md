# Device Type Options UI Updates

## Overview
Updated the DeviceTypesPage dialog styling to match the application's green color scheme and added support for new input types including multiselect and orderedmultiselect with reordering capabilities.

## Styling Changes

### Color Scheme
- **Dialog Header**: Changed from blue (`bg-blue-9`) to green (`bg-green-9`)
- **Dialog Background**: Set to `bg-grey-9` for slightly lighter appearance against page background
- **Section Headers**: Changed from grey-7 (`bg-grey-7`) to green-9 (`bg-green-9`) with white text
- **Section Borders**: Added 2px solid light green borders (`#1db885`) to section cards
- **Accent Color**: All buttons and interactive elements use `color="green"`

### Dialog Layout
- Main card background: `bg-grey-9` for contrast
- Section cards: `bg-grey-9` with green borders
- Max height: 60vh with scrollable content area
- Actions padding: `q-pa-md` for better spacing

## New Input Types Supported

### 1. Boolean Type (`type: 'boolean'`)
Renders as a checkbox input for true/false configuration values.

**Example Schema:**
```json
{
  "optionId": "enable_sip",
  "friendlyName": "Enable SIP",
  "type": "boolean",
  "default": true
}
```

**Rendering:**
- Uses Quasar `q-checkbox` component
- Color: `color="green"` for consistent theming
- Stores as boolean in optionValues

### 2. Select Type (Enhanced)
Dropdown select for predefined option lists.

**Example Schema:**
```json
{
  "optionId": "sip_mode",
  "friendlyName": "SIP Mode",
  "type": "select",
  "options": ["UDP", "TCP", "TLS"],
  "default": "UDP",
  "mandatory": true
}
```

**Rendering:**
- Uses Quasar `q-select` component
- Dark theme enabled: `dark` prop
- Green accent color: `color="green"`
- Validation support for mandatory fields

### 3. Multi-Select Type (`type: 'multiselect'`)
Renders as a grid of checkboxes for selecting multiple values.

**Example Schema:**
```json
{
  "optionId": "allowed_codecs",
  "friendlyName": "Allowed Codecs",
  "type": "multiselect",
  "choices": ["PCMU", "PCMA", "G722"],
  "default": ["PCMU", "G722"]
}
```

**Rendering:**
- Uses multiple `q-checkbox` controls
- Handles both `options` and `choices` lists
- Stores as array in optionValues

### 4. Ordered Multi-Select Type (`type: 'orderedmultiselect'`)
Dual-list interface for selecting and ordering multiple options.

**Example Schema:**
```json
{
  "optionId": "audio_codecs",
  "friendlyName": "Audio Codecs (Priority Order)",
  "type": "orderedmultiselect",
  "options": ["G.711u", "G.711a", "G.722", "G.729"],
  "default": ["G.711u", "G.722"],
  "mandatory": false
}
```

**Features:**
- **Left List**: Available options (not yet selected)
- **Right List**: Selected options in current order
- **Move Right**: Click item in left list or use right-arrow button
- **Move Left**: Click remove button in right list to deselect
- **Reorder**: Up/Down arrow buttons to change priority
- **Visual Indicators**: 
  - Chevron-right icon in left list
  - Chevron-left icon in right list
  - Arrow-up/down icons for ordering
- **Empty State**: Helpful message when no items selected

**Rendering:**
```vue
<div class="row q-gutter-md">
  <!-- Available Options (Left) -->
  <q-list class="bg-grey-8" style="border: 1px solid #1db885;">
    
  <!-- Selected Options (Right) -->
  <q-list class="bg-grey-8" style="border: 1px solid #1db885;">
```

**Storage:**
Stores as array of selected values in order:
```javascript
optionValues[optionId] = ["option1", "option2", "option3"]
```

## Implementation Details

### Helper Functions

#### availableOptions(option)
Returns list of options not yet selected for orderedmultiselect.
```javascript
const availableOptions = (option) => {
  if (!option.options) return [];
  const selected = optionValues.value[option.optionId] || [];
  return option.options.filter(opt => !selected.includes(opt));
};
```

#### moveToSelected(optionId, value)
Adds an option to the selected list.

#### moveToAvailable(optionId, value)
Removes an option from the selected list.

#### moveUpSelected(optionId, idx)
Moves a selected option up in priority (higher index = lower priority).

#### moveDownSelected(optionId, idx)
Moves a selected option down in priority (lower index = higher priority).

## Input Type Priority
When option.type is evaluated, the following order is used:
1. `text` → q-input text field
2. `number` → q-input with type="number"
3. `select` → q-select dropdown
4. `boolean` or `checkbox` → q-checkbox
5. `textarea` → q-input with textarea
6. `multiselect` → Checkbox grid
7. `orderedmultiselect` → Dual-list with ordering
8. Unsupported → Warning message

## Visual Theme Integration

### Color Palette
- **Primary Dark**: `bg-grey-9` (main backgrounds)
- **Secondary Dark**: `bg-grey-8` (section content areas)
- **Accent**: `bg-green-9` (headers)
- **Highlight**: `#1db885` (borders and dividers)
- **Text**: White on dark backgrounds

### Component Styling
- All inputs: `dark`, `dense`, `outlined`
- Buttons: `flat`, `dense`, `round`, `size="sm"`
- Lists: Bordered, separated items with green borders
- Spacing: Consistent use of `q-gutter-md` and `q-gutter-xs`

### Dialog Behaviors
- **Reset to Defaults**: Confirmation dialog restores schema defaults
- **Read-Only Mode**: Non-admin users can view options with inputs disabled

## Testing Checklist

- [ ] Dialog opens when "Common Options" button clicked
- [ ] Green header displays device type information
- [ ] All input types render correctly
  - [ ] Text fields accept input
  - [ ] Number fields validate numeric input
  - [ ] Checkboxes toggle boolean values
  - [ ] Dropdowns show/select options
  - [ ] Textareas handle multiline input
- [ ] Orderedmultiselect functionality
  - [ ] Left/right lists display correctly
  - [ ] Click left item moves to right list
  - [ ] Click remove button moves back to left
  - [ ] Up/down buttons reorder items
  - [ ] Empty state message displays when no items selected
- [ ] Save button submits values to API
- [ ] Error banner displays if save fails
- [ ] Dialog closes after successful save
- [ ] Styling matches green color scheme

## Migration Notes

### For Device Type Plugins
To support new input types, update your CommonOptions schema:

```python
# Old style (still supported)
"type": "checkbox"

# New style
"type": "boolean"  # More semantically clear

# New capability
"type": "orderedmultiselect"
"options": ["option1", "option2", ...]

# Multi-select capability
"type": "multiselect"
"choices": ["option1", "option2", ...]
```

### Backend Changes
No backend changes required. The frontend handles all new input types and stores values as arrays for orderedmultiselect.

## Files Modified
- `frontend/src/pages/DeviceTypesPage.vue` - Complete dialog rewrite with new styling and input types

## Related Documentation
- [DEVICE_TYPE_OPTIONS.md](./DEVICE_TYPE_OPTIONS.md) - Complete technical guide
- [DEVICE_TYPE_OPTIONS_QUICK_REF.md](./DEVICE_TYPE_OPTIONS_QUICK_REF.md) - Quick reference for developers
- [COPILOT_GUIDELINES.md](../.github/COPILOT_GUIDELINES.md) - Development standards reference
