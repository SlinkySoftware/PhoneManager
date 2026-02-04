<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">Dial Plans</div>
      <q-badge v-if="isReadOnly" color="orange" label="Read Only Mode" class="q-ml-md" />
      <q-space />
      <q-btn v-if="!isReadOnly" color="primary" icon="add" label="Add" @click="openCreate" class="q-ml-sm" />
      <q-btn flat color="secondary" icon="refresh" label="Refresh" @click="loadDialPlans" class="q-ml-sm" />
    </div>

    <q-table
      flat
      bordered
      :rows="dialPlans"
      :columns="columns"
      row-key="id"
      :loading="loading"
      no-data-label="No dial plans yet"
      :pagination="{ rowsPerPage: 20, rowsPerPageOptions: [20, 50, 100, 0] }"
    >
      <template #body-cell-in_use="props">
        <q-td align="center">
          <q-btn
            v-if="dialPlanUsage(props.row.id).length"
            dense
            flat
            round
            icon="search"
            color="light-blue-5"
            size="sm"
          >
            <q-tooltip>In use by {{ dialPlanUsage(props.row.id).length }} site(s)</q-tooltip>
            <q-menu anchor="bottom left" self="top left">
              <q-list dense style="min-width: 240px">
                <q-item v-for="siteName in dialPlanUsage(props.row.id)" :key="siteName">
                  <q-item-section>{{ siteName }}</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </q-btn>
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td align="right">
          <q-btn v-if="!isReadOnly" dense flat icon="edit" color="primary" @click="openEdit(props.row)" />
          <q-btn v-if="isReadOnly" dense flat icon="visibility" color="info" @click="openEdit(props.row)">
            <q-tooltip>View</q-tooltip>
          </q-btn>
          <q-btn v-if="!isReadOnly" dense flat icon="delete" color="negative" @click="openDeleteConfirm(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Create/Edit Dialog -->
    <q-dialog v-model="dialog" @hide="resetForm">
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section class="text-h6">{{ isReadOnly && form.id ? 'View' : form.id ? 'Edit' : 'Create' }} Dial Plan</q-card-section>
        <q-card-section v-if="errorMessage" class="bg-negative text-white q-mb-md">
          <q-icon name="error" class="q-mr-md" />
          {{ errorMessage }}
        </q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input
            v-model="form.name"
            label="Name"
            dense
            outlined
            :disable="isReadOnly"
            :rules="[val => !!val || 'Name is required']"
          />
          <q-input
            v-model="form.description"
            label="Description"
            type="textarea"
            rows="2"
            dense
            outlined
            :disable="isReadOnly"
          />

          <!-- Rules Section -->
          <div class="text-subtitle1 q-mt-md q-mb-sm">Transformation Rules</div>
          <div class="text-caption text-grey-7 q-mb-md">
            Rules are applied in sequence order. First match wins.<br>
            Syntax: X=[0-9], *=.+, []=literal, ()=capture group, $1/$2=replacement
          </div>

          <q-table
            flat
            bordered
            dense
            :rows="form.rules"
            :columns="ruleColumns"
            row-key="sequence_order"
            hide-pagination
            :rows-per-page-options="[0]"
            no-data-label="No rules yet"
          >
            <template #body-cell-order="props">
              <q-td align="center">
                <div class="row items-center q-gutter-xs">
                  <q-btn
                    v-if="!isReadOnly"
                    dense
                    flat
                    round
                    size="xs"
                    icon="arrow_upward"
                    color="grey-6"
                    :disable="props.rowIndex === 0"
                    @click="moveRuleUp(props.rowIndex)"
                  >
                    <q-tooltip>Move up</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="!isReadOnly"
                    dense
                    flat
                    round
                    size="xs"
                    icon="arrow_downward"
                    color="grey-6"
                    :disable="props.rowIndex === form.rules.length - 1"
                    @click="moveRuleDown(props.rowIndex)"
                  >
                    <q-tooltip>Move down</q-tooltip>
                  </q-btn>
                  <span class="q-ml-sm">{{ props.rowIndex + 1 }}</span>
                </div>
              </q-td>
            </template>
            <template #body-cell-input_regex="props">
              <q-td>
                <q-input
                  v-model="props.row.input_regex"
                  dense
                  outlined
                  :disable="isReadOnly"
                  :rules="[
                    val => !!val || 'Input pattern is required',
                    val => countCaptureGroups(val) <= 1 || 'Only one capture group is allowed',
                    val => validateInputPattern(val)
                  ]"
                />
              </q-td>
            </template>
            <template #body-cell-output_regex="props">
              <q-td>
                <q-input
                  v-model="props.row.output_regex"
                  dense
                  outlined
                  :disable="isReadOnly"
                  :rules="[
                    val => !!val || 'Output pattern is required',
                    val => validateOutputPattern(val),
                    val => hasOnlyAllowedDollar(val) || 'Only $1 is allowed in output',
                    val => validateOutputAgainstInput(props.row.input_regex, val)
                  ]"
                />
              </q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td align="right">
                <q-btn
                  v-if="!isReadOnly"
                  dense
                  flat
                  round
                  size="sm"
                  icon="delete"
                  color="negative"
                  @click="deleteRule(props.rowIndex)"
                >
                  <q-tooltip>Delete rule</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>

          <q-btn
            v-if="!isReadOnly"
            flat
            dense
            icon="add"
            label="Add Rule"
            color="teal"
            @click="addRule"
            class="q-mt-sm"
          />

          <!-- Test Section -->
          <q-separator class="q-my-md" />
          <div class="text-subtitle1 q-mb-sm">Test Transformation</div>
          <div class="row q-gutter-sm items-start">
            <q-input
              v-model="testInput"
              label="Input Number"
              dense
              outlined
              style="flex: 1"
              :disable="!form.id"
              placeholder="e.g., 0288553311"
            />
            <q-btn
              unelevated
              color="teal"
              label="Test"
              icon="play_arrow"
              :loading="testLoading"
              :disable="!form.id || !testInput"
              @click="testDialPlan"
            />
          </div>
          <div v-if="testResult" class="q-mt-sm">
            <q-banner
              v-if="testResult.matched"
              class="bg-positive text-white"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="check_circle" />
              </template>
              <div class="text-subtitle2">Matched Rule {{ testResult.matched_rule_index + 1 }}</div>
              <div class="text-caption">Pattern: {{ testResult.matched_rule_pattern }}</div>
              <div class="text-body1 q-mt-xs">Output: <strong>{{ testResult.output }}</strong></div>
            </q-banner>
            <q-banner
              v-else
              class="bg-warning text-dark"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="info" />
              </template>
              <div class="text-subtitle2">No Match</div>
              <div class="text-body1">Output: <strong>{{ testResult.output }}</strong> (unchanged)</div>
            </q-banner>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="isReadOnly ? 'Close' : 'Cancel'" color="primary" v-close-popup />
          <q-btn v-if="!isReadOnly" unelevated label="Save" color="positive" @click="save" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Delete Confirmation Dialog -->
    <q-dialog v-model="showDeleteConfirm">
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
          <q-btn unelevated label="Delete" color="negative" @click="confirmDelete" :loading="deleting" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { dialPlanService } from '../services/dialPlanService';
import api from '../api';

const authStore = useAuthStore();
const isReadOnly = computed(() => authStore.user?.role !== 'admin');

// Table data
const dialPlans = ref([]);
const sites = ref([]);
const loading = ref(false);

// Dialog state
const dialog = ref(false);
const form = ref({
  id: null,
  name: '',
  description: '',
  rules: []
});
const errorMessage = ref('');
const saving = ref(false);

// Delete state
const showDeleteConfirm = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');
const deleting = ref(false);

// Test state
const testInput = ref('');
const testResult = ref(null);
const testLoading = ref(false);

// Table columns
const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'description', label: 'Description', field: 'description', align: 'left', sortable: true },
  { name: 'rules_count', label: 'Rules', field: 'rules_count', align: 'center', sortable: true },
  { name: 'in_use', label: 'In Use', field: 'site_count', align: 'center', sortable: true },
  { name: 'actions', label: 'Actions', align: 'right' }
];

const ruleColumns = [
  { name: 'order', label: '#', align: 'center', style: 'width: 100px' },
  { name: 'input_regex', label: 'Input Pattern', align: 'left' },
  { name: 'output_regex', label: 'Output Pattern', align: 'left' },
  { name: 'actions', label: '', align: 'right', style: 'width: 60px' }
];

const countCaptureGroups = (pattern) => {
  if (!pattern) return 0;
  let count = 0;
  let escaped = false;
  for (const char of pattern) {
    if (escaped) {
      escaped = false;
      continue;
    }
    if (char === '\\') {
      escaped = true;
      continue;
    }
    if (char === '(') {
      count += 1;
    }
  }
  return count;
};

const hasCaptureGroup = (pattern) => countCaptureGroups(pattern) > 0;

const hasOnlyAllowedDollar = (output) => {
  if (!output) return true;
  const dollars = output.match(/\$/g);
  if (!dollars) return true;
  return /^(?:[^$]*\$1)*[^$]*$/.test(output);
};

const validateOutputAgainstInput = (input, output) => {
  const inputHasCapture = hasCaptureGroup(input);
  const outputHasCapture = /\$1/.test(output || '');
  if (inputHasCapture && !outputHasCapture) {
    return 'Output must reference $1 when input uses a capture group';
  }
  if (!inputHasCapture && outputHasCapture) {
    return 'Output cannot reference $1 without a capture group';
  }
  return true;
};

const validateInputPattern = (pattern) => {
  if (!pattern) return true;
  const caretCount = (pattern.match(/\^/g) || []).length;
  if (caretCount > 1 || (caretCount === 1 && !pattern.startsWith('^'))) {
    return 'Caret (^) is only allowed at the start';
  }
  const dollarCount = (pattern.match(/\$/g) || []).length;
  if (dollarCount > 1 || (dollarCount === 1 && !pattern.endsWith('$'))) {
    return 'Dollar ($) is only allowed at the end';
  }

  const openParenCount = (pattern.match(/\(/g) || []).length;
  const closeParenCount = (pattern.match(/\)/g) || []).length;
  if (openParenCount !== closeParenCount) {
    return 'Capture group parentheses must be balanced';
  }
  if (openParenCount > 1) {
    return 'Only one capture group is allowed';
  }

  const starCount = (pattern.match(/\*/g) || []).length;
  if (starCount > 1) {
    return 'Only one * is allowed';
  }
  if (starCount === 1) {
    const normalized = pattern.replace(/[()]/g, '');
    if (!normalized.endsWith('*')) {
      return '* must be the last character (excluding grouping)';
    }
  }

  const allowedChars = /^[0-9+\[\]^\-\$()*]+$/;
  if (!allowedChars.test(pattern)) {
    return 'Only digits, +, [], ^, $, *, and () are allowed';
  }

  const hasLettersOrSymbols = /[A-Za-z]|[#%{};:'"?\\/|,\.<>]/.test(pattern);
  if (hasLettersOrSymbols) {
    return 'Letters and special symbols are not allowed';
  }

  const bracketContent = pattern.match(/\[[^\]]*\]/g) || [];
  for (const chunk of bracketContent) {
    const inner = chunk.slice(1, -1);
    if (!/^[0-9\-^]+$/.test(inner)) {
      return 'Only digits, hyphen, or ^ are allowed inside []';
    }
  }

  return true;
};

const validateOutputPattern = (output) => {
  if (!output) return true;
  if (/[^0-9+$]/.test(output)) {
    return 'Output can only contain digits, +, and $1';
  }
  return true;
};

// Error extraction helper
const extractErrorMessage = (error) => {
  // Check for nested rule validation errors (array of error objects)
  if (error.response?.data?.rules && Array.isArray(error.response.data.rules)) {
    const ruleErrors = error.response.data.rules
      .map((rule, idx) => {
        if (rule.detail) {
          const detailMsg = Array.isArray(rule.detail) ? rule.detail.join(', ') : rule.detail;
          return `Rule ${idx + 1}: ${detailMsg}`;
        }
        return null;
      })
      .filter(msg => msg !== null);
    
    if (ruleErrors.length > 0) {
      return 'Validation failed:\n' + ruleErrors.join('\n');
    }
  }
  
  // Check for detailed backend error message (preferred)
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (Array.isArray(detail)) {
      return detail.join('; ');
    }
    return detail;
  }
  
  // Check for alternative message field
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  
  // Handle specific HTTP status codes with meaningful messages
  if (error.response?.status === 409) {
    return 'Cannot complete this operation: The item is currently in use by other records. Please remove dependencies first.';
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
  if (error.response?.status === 400) {
    return 'Bad Request: Please check your input and try again.';
  }
  
  // Fall back to status text
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

// Load dial plans
const loadDialPlans = async () => {
  loading.value = true;
  try {
    const response = await dialPlanService.list();
    dialPlans.value = response.data;
  } catch (error) {
    console.error('Error loading dial plans:', error);
  } finally {
    loading.value = false;
  }
};

// Load sites
const loadSites = async () => {
  try {
    const response = await api.get('/sites/');
    sites.value = response.data;
  } catch (error) {
    console.error('Error loading sites:', error);
  }
};

// Compute dial plan usage map
const dialPlanUsageMap = computed(() => {
  const usage = {};
  sites.value.forEach(site => {
    const siteName = site.name || `Site ${site.id}`;
    if (site.dial_plan) {
      if (!usage[site.dial_plan]) usage[site.dial_plan] = [];
      usage[site.dial_plan].push(siteName);
    }
  });
  return usage;
});

// Get usage for a specific dial plan
const dialPlanUsage = (dialPlanId) => dialPlanUsageMap.value[dialPlanId] || [];

// Open create dialog
const openCreate = () => {
  form.value = {
    id: null,
    name: '',
    description: '',
    rules: []
  };
  errorMessage.value = '';
  testInput.value = '';
  testResult.value = null;
  dialog.value = true;
};

// Open edit dialog
const openEdit = async (row) => {
  try {
    const response = await dialPlanService.get(row.id);
    form.value = {
      ...response.data,
      rules: response.data.rules || []
    };
    errorMessage.value = '';
    testInput.value = '';
    testResult.value = null;
    dialog.value = true;
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  }
};

// Reset form
const resetForm = () => {
  form.value = {
    id: null,
    name: '',
    description: '',
    rules: []
  };
  errorMessage.value = '';
  testInput.value = '';
  testResult.value = null;
};

// Rule management
const addRule = () => {
  form.value.rules.push({
    input_regex: '',
    output_regex: ''
  });
};

const deleteRule = (index) => {
  form.value.rules.splice(index, 1);
};

const moveRuleUp = (index) => {
  if (index === 0) return;
  const temp = form.value.rules[index];
  form.value.rules[index] = form.value.rules[index - 1];
  form.value.rules[index - 1] = temp;
};

const moveRuleDown = (index) => {
  if (index === form.value.rules.length - 1) return;
  const temp = form.value.rules[index];
  form.value.rules[index] = form.value.rules[index + 1];
  form.value.rules[index + 1] = temp;
};

// Test dial plan
const testDialPlan = async () => {
  if (!form.value.id || !testInput.value) return;
  
  testLoading.value = true;
  testResult.value = null;
  try {
    const response = await dialPlanService.test(form.value.id, testInput.value);
    testResult.value = response.data;
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    testLoading.value = false;
  }
};

// Save dial plan
const save = async () => {
  errorMessage.value = '';
  saving.value = true;
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description,
      rules: form.value.rules
    };

    if (form.value.id) {
      await dialPlanService.update(form.value.id, payload);
    } else {
      await dialPlanService.create(payload);
    }

    dialog.value = false;
    await loadDialPlans();
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    saving.value = false;
  }
};

// Delete operations
const openDeleteConfirm = (row) => {
  itemToDelete.value = row;
  deleteError.value = '';
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  deleteError.value = '';
  deleting.value = true;
  try {
    await dialPlanService.delete(itemToDelete.value.id);
    showDeleteConfirm.value = false;
    await loadDialPlans();
  } catch (error) {
    deleteError.value = extractErrorMessage(error);
  } finally {
    deleting.value = false;
  }
};

// Load data on mount
onMounted(async () => {
  await Promise.all([loadDialPlans(), loadSites()]);
});
</script>
