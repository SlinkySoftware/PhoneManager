# Validation & Error Handling Implementation Summary

## Overview
Comprehensive validation, error handling, and delete confirmation patterns have been implemented across all frontend data pages following the standards defined in FRONTEND_GUIDELINES.md.

## Recent Improvements (2026-01-20)

### Backend Error Handling
**Problem:** Users were seeing generic "Error: Internal Server Error" messages when attempting to delete items with foreign key constraints, providing no guidance on why the operation failed.

**Solution:** Implemented comprehensive error handling in Django backend viewsets:

#### Changes Made:
1. **Added imports** to `backend/core/views.py`:
   - `ProtectedError` from `django.db.models`
   - `IntegrityError` from `django.db`

2. **Override `destroy()` method** in all ViewSets:
   - `SIPServerViewSet` - detects when server is used by sites
   - `SiteViewSet` - detects when site has devices assigned
   - `LineViewSet` - detects when line is assigned to devices
   - `DeviceViewSet` - detects when device has related records

3. **Error Response Format**:
   ```json
   {
     "detail": "Cannot delete this SIP Server as it is currently used by 3 site(s). Please reassign or delete those sites first.",
     "error_code": "foreign_key_constraint"
   }
   ```

4. **HTTP Status Codes**:
   - `409 Conflict` - for foreign key constraint violations
   - `204 No Content` - for successful deletions
   - Generic `IntegrityError` also returns 409

### Frontend Error Handling
**Enhanced `extractErrorMessage()` helper function** in all pages:

#### Improvements:
- **Prioritizes backend messages**: Checks `error.response.data.detail` first
- **Status-specific messages**: Provides context for common HTTP codes:
  - `409`: Foreign key constraint message from backend
  - `404`: "Item not found. It may have been deleted."
  - `403`: "You do not have permission..."
  - `401`: "Your session has expired..."
- **Network error handling**: Separate message for connection failures
- **Improved fallback messages**: More helpful than generic errors

#### Updated Files:
- `/frontend/src/pages/SIPServersPage.vue`
- `/frontend/src/pages/SitesPage.vue`
- `/frontend/src/pages/LinesPage.vue`
- `/frontend/src/pages/DevicesPage.vue`

### Documentation Updates

#### FRONTEND_GUIDELINES.md
- Expanded error handling section with full extractErrorMessage implementation
- Added HTTP status code handling examples
- Documented backend error response format
- Clarified delete confirmation dialog behavior (stays open on error)

#### COPILOT_GUIDELINES.md
- Added comprehensive "Error Handling in Views" section
- Documented the destroy() method override pattern
- Specified HTTP 409 for constraint violations (not 500)
- Emphasized user-friendly error messages with guidance

## Recent Improvements (2026-02-04)

### Dial Plans Validation
**Problem:** Dial plan rules could be saved with malformed input/output patterns or unsupported capture groups.

**Solution:** Added strict input/output validation in the Dial Plans UI to prevent invalid rules:

- **Input validation**
  - Requires non-empty pattern
  - Enforces at most one capture group
  - Validates standard syntax (X, *, [], (), ^, $)
- **Output validation**
  - Requires non-empty pattern
  - Allows only `$1` replacements
  - Ensures `$1` usage matches the input capture group

### Dial Plans UI Enhancements
- Rule ordering controls with up/down buttons
- In-use indicator for sites that reference a dial plan
- Read-only view for non-admin users

### Updated Files
- [frontend/src/pages/DialPlansPage.vue](frontend/src/pages/DialPlansPage.vue)

## Implementation Status

### ✅ SitesPage.vue
**Validation Rules:**
- Name: Required
- Primary SIP Server: Required (null check)
- Secondary SIP Server: Optional

**Error Handling:**
- Real-time field validation with :rules prop
- Error message banner in save dialog
- API error extraction and display
- Delete confirmation dialog with FK error handling

**Features:**
- Delete confirmation dialog with item name
- Error display in deletion confirmation
- `extractErrorMessage()` helper for consistent API error handling

### ✅ SIPServersPage.vue
**Validation Rules:**
- Name: Required
- Host: Required, valid hostname format (alphanumeric, dots, hyphens)
- Port: Required, range 1-65535
- Transport: Required (TLS/UDP/TCP)

**Error Handling:**
- All fields validated before submission
- Error banner in dialog shows validation errors
- API errors extracted and displayed
- Delete confirmation with error handling

**New Features:**
- Hostname format validation regex
- Port range validation (1-65535)
- Transport enum selection

### ✅ LinesPage.vue
**Validation Rules:**
- Name: Required
- Directory Number: Required, E164 format validation (+[0-9]{7,15})
- Registration Account: Required
- Registration Password: Required
- Shared: Optional toggle

**Error Handling:**
- E164 format validation with helpful error message
- Password field marked as required
- Delete confirmation with error display
- Consistent error message extraction

**New Features:**
- E164 format validation for phone numbers
- Password validation requirement
- Error messages specific to field type

### ✅ DeviceTypesPage.vue
**Changes:**
- Added loading state during API calls
- Loading spinner displays during fetch
- Refresh button shows loading indicator

**Note:** Device Types page is read-only (displays manufacturer/model info), minimal CRUD operations expected

### ✅ DevicesPage.vue
**Complete Implementation (was placeholder):**
- Full CRUD interface created
- Table-based device listing
- Edit and delete operations

**Validation Rules:**
- Name: Required
- MAC Address: Required, valid MAC format (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)
- Device Type: Required (dropdown selection)
- Site: Required (dropdown selection)

**Error Handling:**
- MAC address format validation with regex
- Foreign key validation (Device Type and Site dropdowns)
- Delete confirmation dialog
- API error extraction and display

**Features:**
- Dynamic loading of device types and sites on mount
- MAC address validation regex: `^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$`
- Device type display in dropdown as "Manufacturer Model"

## Common Patterns Implemented

### extractErrorMessage() Helper
```javascript
const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;
  if (error.response?.statusText) return `Error: ${error.response.statusText}`;
  return 'An unexpected error occurred. Please try again.';
};
```

### Validation Rules Pattern
```javascript
<q-input
  v-model="form.name"
  label="Name"
  :rules="[val => !!val || 'Name is required']"
/>
```

### Error Message Display
```javascript
<q-card-section v-if="errorMessage" class="bg-negative text-white q-mb-md">
  <q-icon name="error" class="q-mr-md" />
  {{ errorMessage }}
</q-card-section>
```

### Delete Confirmation Dialog
```javascript
<q-dialog v-model="deleteDialog">
  <q-card style="min-width: 400px">
    <q-card-section class="text-h6">Confirm Deletion</q-card-section>
    <q-card-section>
      <p>Are you sure you want to delete: <strong>{{ itemToDelete?.name }}</strong>?</p>
      <p class="text-caption text-grey-7">This action cannot be undone.</p>
    </q-card-section>
    <q-card-section v-if="deleteError" class="bg-negative text-white">
      <q-icon name="error" class="q-mr-md" />
      {{ deleteError }}
    </q-card-section>
    <q-card-actions align="right">
      <q-btn flat label="Cancel" color="primary" v-close-popup />
      <q-btn unelevated label="Delete" color="negative" @click="confirmDelete" />
    </q-card-actions>
  </q-card>
</q-dialog>
```

## Required State Refs Per Page
All pages include:
- `dialog`: Boolean for form dialog visibility
- `errorMessage`: String for form errors
- `deleteDialog`: Boolean for delete confirmation
- `itemToDelete`: Object for item being deleted
- `deleteError`: String for deletion errors
- `loading`: Boolean for async operations

## Validation Error Messages

| Field | Error Message |
|-------|----------------|
| Name (any) | "Name is required" |
| Host | "Host is required" or "Invalid hostname format" |
| Port | "Port is required" or "Port must be between 1 and 65535" |
| Transport | "Transport is required" |
| Directory Number | "Directory Number is required" or "Invalid E164 format (e.g., +61299999999)" |
| Registration Account | "Registration Account is required" |
| Password | "Password is required" |
| MAC Address | "MAC Address is required" or "Invalid MAC format (e.g., 00:11:22:33:44:55)" |
| Device Type | "Device Type is required" |
| Site | "Site is required" |
| Primary SIP Server | "Primary SIP Server is required" |

## API Integration
All pages use the shared `api` client from `src/api.js` which handles:
- Automatic token-based authentication
- 401/403 error handling with logout redirect
- Consistent axios instance for all requests

## Testing Checklist

### For Each Page:
- [ ] Form validation prevents submission with empty required fields
- [ ] Validation error messages display clearly
- [ ] Format validations (MAC, E164, Port range) work correctly
- [ ] API submission succeeds when validation passes
- [ ] API errors display in error banner
- [ ] Delete button opens confirmation dialog
- [ ] Delete confirmation shows item name
- [ ] Delete confirmation shows FK error if item has dependents
- [ ] Successful delete refreshes the list
- [ ] Cancel buttons close dialogs without saving

### Backend Dependencies:
- All endpoints should validate and return appropriate HTTP status codes
- 409 Conflict for foreign key constraint violations (item still in use)
- 400 Bad Request for validation errors
- 404 Not Found for missing items
- 401/403 for authentication errors

## Files Modified
1. `frontend/src/pages/SitesPage.vue` - ✅ Complete
2. `frontend/src/pages/SIPServersPage.vue` - ✅ Complete
3. `frontend/src/pages/LinesPage.vue` - ✅ Complete
4. `frontend/src/pages/DeviceTypesPage.vue` - ✅ Updated with loading state
5. `frontend/src/pages/DevicesPage.vue` - ✅ Full implementation from scratch

## Next Steps
1. **Backend Validation:** Implement foreign key constraint checks to return 409 Conflict responses
2. **Testing:** Validate all error scenarios work as expected
3. **Accessibility:** Ensure all error messages are screen-reader friendly
4. **Performance:** Consider pagination for large device/site/line lists
