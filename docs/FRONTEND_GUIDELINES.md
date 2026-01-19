# Frontend Development Guidelines

## Overview

This document outlines the standards and requirements for all frontend components in the Phone Provisioning Manager application.

## Core Requirements

### 1. Form Validation

All input fields must include validation to ensure:
- **Mandatory fields** are clearly marked and enforced
- **Data type validation** (email format, numeric values, etc.)
- **Field constraints** are enforced (min/max length, allowed characters)
- **Real-time feedback** via error messages displayed below fields
- **Save operation prevention** if any validation rule fails

#### Implementation Pattern

```vue
<q-input
  v-model="form.fieldName"
  label="Field Label"
  outlined
  dense
  :rules="[
    val => !!val || 'Field name is required',
    val => val.length >= 3 || 'Minimum 3 characters',
    val => /^[a-zA-Z0-9]+$/.test(val) || 'Only alphanumeric characters allowed'
  ]"
/>
```

### 2. Error Handling & User Feedback

All API operations must include comprehensive error handling:

#### Requirements
- **API errors** must be caught and displayed to the user
- **Error messages** should be shown in a persistent dialog/banner
- **Error details** from backend should be surfaced (not just HTTP status codes)
- **User-friendly messages** for common errors - which detail WHY the error occurred and how the user can fix it. For example "Missing Device Type", instead of just "400 Bad Request"
- **Network errors** should be handled gracefully

#### Implementation Pattern

**Error Extraction Helper Function:**
```vue
<script setup>
const errorMessage = ref('');

/**
 * Extract meaningful error message from API error response.
 * Prioritizes backend error messages over generic HTTP status text.
 * 
 * @param {Error} error - Axios error object
 * @returns {string} User-friendly error message
 */
const extractErrorMessage = (error) => {
  // Check for detailed backend error message (preferred)
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  
  // Check for alternative message field
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  
  // Handle specific HTTP status codes with meaningful messages
  if (error.response?.status === 409) {
    return 'Cannot complete this operation: The item is currently in use by other records. ' +
           'Please remove dependencies first.';
  }
  
  if (error.response?.status === 404) {
    return 'The requested item was not found. It may have been deleted.';
  }
  
  if (error.response?.status === 403) {
    return 'You do not have permission to perform this action.';
  }
  
  if (error.response?.status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  
  // Fall back to status text, but make it more user-friendly
  if (error.response?.statusText) {
    return `Operation failed: ${error.response.statusText}`;
  }
  
  // Generic network error
  if (error.request) {
    return 'Network error: Unable to reach the server. Please check your connection.';
  }
  
  // Unknown error
  return 'An unexpected error occurred. Please try again or contact support if the problem persists.';
};

const handleOperation = async () => {
  errorMessage.value = '';
  try {
    await api.post('/endpoint/', data);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  }
};
</script>

<template>
  <!-- Error display banner in dialogs -->
  <q-card-section v-if="errorMessage" class="bg-negative text-white q-mb-md">
    <q-icon name="error" class="q-mr-md" />
    {{ errorMessage }}
  </q-card-section>
</template>
```

**Key Points:**
- **Always check `error.response.data.detail` first** - this contains backend-generated error messages
- **Provide context-specific messages** for HTTP status codes (409, 404, 403, 401)
- **Handle network errors** separately from API errors
- **Display errors prominently** in dialogs with error icon
- **Clear errors** at the start of new operations

### 3. Delete Operations

All delete operations must follow a three-step confirmation process:

#### Requirements
- **Confirmation dialog** must be shown before any deletion
- **Item identification** should be clearly shown in the confirmation
- **Foreign key constraint errors** are handled by backend (returns 409 Conflict with detail message)
- **Success/failure feedback** after deletion attempt
- **Automatic list refresh** after successful deletion
- **Error display in confirmation dialog** - errors should NOT close the dialog

#### Backend Behavior
The backend detects foreign key constraint violations and returns:
- **HTTP 409 Conflict** status code
- **JSON response** with `detail` field explaining which records are preventing deletion
- **Example**: `{"detail": "Cannot delete this SIP Server as it is currently used by 3 site(s). Please reassign or delete those sites first.", "error_code": "foreign_key_constraint"}`

#### Implementation Pattern

```vue
<script setup>
const showDeleteConfirm = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');

const openDeleteConfirm = (item) => {
  itemToDelete.value = item;
  deleteError.value = '';  // Clear previous errors
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  deleteError.value = '';  // Clear errors before attempt
  try {
    await api.delete(`/endpoint/${itemToDelete.value.id}/`);
    showDeleteConfirm.value = false;  // Only close on success
    await loadData(); // Refresh list
  } catch (error) {
    // Extract error but keep dialog open so user can read it
    deleteError.value = extractErrorMessage(error);
  }
};
</script>

<template>
  <!-- Delete button -->
  <q-btn 
    dense 
    flat 
    icon="delete" 
    color="negative" 
    @click="openDeleteConfirm(row)" 
  />

  <!-- Confirmation dialog -->
  <q-dialog v-model="showDeleteConfirm">
    <q-card style="min-width: 400px">
      <q-card-section class="text-h6">Confirm Deletion</q-card-section>
      <q-card-section>
        <p>Are you sure you want to delete: <strong>{{ itemToDelete?.name }}</strong>?</p>
        <p class="text-caption text-grey-7">This action cannot be undone.</p>
      </q-card-section>
      
      <!-- Error section - only shown when deleteError has value -->
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
</template>
```

### 4. Loading States

All asynchronous operations must provide visual feedback:
- Show **loading spinners** during API calls
- **Disable buttons/inputs** while operations are in progress
- Display **progress indicators** for long operations
- Update **user expectations** about operation duration

### 5. Form State Management

- **Prevent unintended data loss** by clearing form only after successful save
- **Show success messages** after successful operations
- **Reset form state** after operations complete
- **Handle loading states** on submit buttons during API calls

---

## Required Validations by Data Type

### Text Fields (Name, Title, Label)
- Required (cannot be empty)
- Minimum length: 1 character
- Maximum length: 255 characters (or specified limit)
- No leading/trailing whitespace

### Email Fields
- Required
- Must match email format: `/.+@.+\..+/`

### Numeric Fields (Port, Count, ID)
- Required
- Must be a valid integer
- Min/max range validation

### Select Fields (Dropdowns)
- Required (unless explicitly marked optional)
- Must have a value from available options
- Clear feedback when no options available

### URL Fields
- Must be valid URL format when provided
- Protocol validation (http:// or https://)

---

## Error Message Patterns

| Error Type | User Message | Backend Check |
|-----------|--------------|----------------|
| Validation Error | Show specific field error | 400 Bad Request |
| Conflict | "Item already exists" / "Cannot delete: in use" | 409 Conflict |
| Unauthorized | "You don't have permission for this action" | 403 Forbidden |
| Not Found | "Item not found or has been deleted" | 404 Not Found |
| Server Error | "Server error occurred. Please contact support" | 500+ |
| Network Error | "Unable to reach server. Check connection." | Network timeout |

---

## Component Structure

Every data management page should include:

```
Page.vue
├── Header with title and action buttons (Add, Refresh)
├── Table/List view with data
│   └── Row actions (Edit, Delete)
├── Create/Edit dialog
│   ├── Form fields with validation
│   ├── Error banner
│   └── Action buttons
├── Delete confirmation dialog
└── Success/status messages
```

---

## Testing Checklist

Before marking a page as complete:

- [ ] All mandatory fields have validation rules
- [ ] Error messages appear for invalid inputs
- [ ] API errors display in user-friendly dialogs
- [ ] Delete operations require confirmation
- [ ] Delete prevents cascade deletes (foreign key errors shown)
- [ ] Form clears only after successful save
- [ ] Loading states show during API calls
- [ ] Buttons are disabled during async operations
- [ ] Success messages appear after operations
- [ ] List refreshes after create/update/delete
- [ ] No unhandled promise rejections in console

---

## File Organization

All pages should follow this script organization:

```vue
<template>
  <!-- Template structure -->
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import api from '../api';

// State
const data = ref([]);
const loading = ref(false);
const dialog = ref(false);
const errorMessage = ref('');
const deleteDialog = ref(false);
const itemToDelete = ref(null);

// Computed
const computedValue = computed(() => {
  // computation
});

// Methods
const loadData = async () => {};
const save = async () => {};
const deleteItem = async () => {};

// Lifecycle
onMounted(async () => {
  await loadData();
});
</script>
```

---

## Accessibility Requirements

- Use semantic HTML elements
- Provide labels for all form inputs
- Ensure color contrast meets WCAG AA standards
- Use title attributes for icon-only buttons
- Support keyboard navigation (Tab, Enter, Escape)

---

## Performance Considerations

- Implement pagination for large datasets
- Use table sorting when data exceeds 50 rows
- Debounce search/filter operations
- Lazy load dialogs and heavy components
- Cache API responses where appropriate
