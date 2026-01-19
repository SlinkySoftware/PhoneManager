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
- **User-friendly messages** for common errors (e.g., 409 Conflict, 400 Bad Request)
- **Network errors** should be handled gracefully

#### Implementation Pattern

```vue
<script setup>
const errorMessage = ref('');

const handleOperation = async () => {
  errorMessage.value = '';
  try {
    // API call
  } catch (error) {
    if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail;
    } else if (error.response?.data?.message) {
      errorMessage.value = error.response.data.message;
    } else if (error.response?.statusText) {
      errorMessage.value = `Error: ${error.response.statusText}`;
    } else {
      errorMessage.value = 'An unexpected error occurred. Please try again.';
    }
  }
};
</script>

<template>
  <q-banner v-if="errorMessage" class="bg-negative text-white q-mb-md">
    {{ errorMessage }}
    <template #avatar>
      <q-icon name="error" />
    </template>
  </q-banner>
</template>
```

### 3. Delete Operations

All delete operations must follow a three-step confirmation process:

#### Requirements
- **Confirmation dialog** must be shown before any deletion
- **Item identification** should be clearly shown in the confirmation
- **Foreign key constraint checking** before attempting deletion
- **Success/failure feedback** after deletion attempt
- **Automatic list refresh** after successful deletion

#### Implementation Pattern

```vue
<script setup>
const showDeleteConfirm = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');

const openDeleteConfirm = (item) => {
  itemToDelete.value = item;
  showDeleteConfirm.value = true;
  deleteError.value = '';
};

const confirmDelete = async () => {
  try {
    await api.delete(`/endpoint/${itemToDelete.value.id}/`);
    showDeleteConfirm.value = false;
    await loadData(); // Refresh list
  } catch (error) {
    deleteError.value = extractErrorMessage(error);
  }
};

const extractErrorMessage = (error) => {
  if (error.response?.status === 409) {
    return 'Cannot delete: This item is in use. Check related records.';
  }
  return error.response?.data?.detail || 'Delete failed. Please try again.';
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
      <q-card-section v-if="deleteError" class="bg-negative text-white">
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
