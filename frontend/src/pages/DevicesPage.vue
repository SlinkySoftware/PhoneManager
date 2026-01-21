<!-- SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (c) 2026 Slinky Software -->
<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">Devices</div>
      <q-badge v-if="isReadOnly" color="orange" label="Read Only Mode" class="q-ml-md" />
      <q-space />
      <q-btn v-if="!isReadOnly" color="primary" icon="add" label="Add" @click="openCreate" class="q-ml-sm" />
      <q-btn flat color="secondary" icon="refresh" label="Refresh" @click="loadDevices" class="q-ml-sm" />
    </div>

    <q-table
      flat
      bordered
      :rows="devices"
      :columns="columns"
      row-key="id"
      :loading="loading"
      no-data-label="No devices yet"
      :pagination="{ rowsPerPage: 20, rowsPerPageOptions: [20, 50, 100, 0] }"
    >
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
    <q-dialog v-model="dialog" class="q-gutter-md" :persistent="true" :no-esc="true">
      <q-card style="min-width: 800px; max-width: 1000px" class="bg-grey-9">
        <q-card-section class="bg-teal-9 text-white">
          <div class="text-h6">{{ isReadOnly && form.id ? 'View' : form.id ? 'Edit' : 'Create' }} Device</div>
        </q-card-section>

        <q-card-section v-if="errorMessage" class="bg-negative text-white">
          <q-icon name="error" class="q-mr-md" />
          {{ errorMessage }}
        </q-card-section>

        <q-scroll-area style="height: 60vh" class="q-mb-md">
          <q-card-section class="q-gutter-md">
            <!-- Standard Settings Card -->
            <q-card flat class="bg-grey-8" style="border: 2px solid #1db885;">
              <q-card-section class="bg-teal-8 text-white">
                <div class="text-subtitle1">Standard Settings</div>
              </q-card-section>
              <q-card-section class="q-gutter-md">
                <q-input
                  v-model="form.name"
                  label="Name"
                  dense
                  outlined
                  dark
                  :disable="isReadOnly"
                  :rules="[val => !!val || 'Name is required']"
                />
                <q-input
                  v-model="form.mac_address"
                  label="MAC Address"
                  dense
                  outlined
                  dark
                  :disable="isReadOnly"
                  :rules="[
                    val => !!val || 'MAC Address is required',
                    val => isValidMac(val) || 'Invalid MAC format'
                  ]"
                />
                <q-select
                  v-model="form.device_type_id"
                  :options="deviceTypes"
                  option-value="typeId"
                  option-label="label"
                  label="Device Type"
                  dense
                  outlined
                  dark
                  emit-value
                  map-options
                  color="teal"
                  :disable="isReadOnly"
                  :rules="[val => val !== null || 'Device Type is required']"
                />
                <q-select
                  v-model="form.site"
                  :options="sites"
                  option-value="id"
                  option-label="name"
                  label="Site"
                  dense
                  outlined
                  dark
                  emit-value
                  map-options
                  color="teal"
                  :disable="isReadOnly"
                  :rules="[val => val !== null || 'Site is required']"
                />
              </q-card-section>
            </q-card>

            <!-- Lines Card -->
            <q-card v-if="selectedDeviceType" flat class="bg-grey-8" style="border: 2px solid #1db885;">
              <q-card-section class="bg-teal-8 text-white">
                <div class="text-subtitle1">Lines ({{ selectedDeviceType.numberOfLines }} line{{ selectedDeviceType.numberOfLines !== 1 ? 's' : '' }})</div>
              </q-card-section>
              <q-card-section v-if="lineDisassociationWarning" class="bg-amber-8 text-black">
                <q-icon name="warning" class="q-mr-sm" />
                {{ lineDisassociationWarning }}
              </q-card-section>
              <q-card-section class="q-gutter-md">
                <q-select
                  v-for="lineIdx in selectedDeviceType.numberOfLines"
                  :key="`line-${lineIdx}`"
                  v-model="formLines[lineIdx - 1]"
                  :options="lineOptions(lineIdx - 1)"
                  option-value="id"
                  option-label="label"
                  emit-value
                  map-options
                  clearable
                  clear-icon="close"
                  :label="`Line ${lineIdx}`"
                  dense
                  outlined
                  dark
                  color="teal"
                  :disable="isReadOnly"
                  :rules="lineIdx === 1 ? [val => val !== null || 'Line 1 is required'] : []"
                />
              </q-card-section>
            </q-card>

            <!-- Device-Specific Options Card -->
            <template v-if="selectedDeviceType?.deviceSpecificOptions?.sections">
              <q-card
                v-for="section in sortedDeviceSections"
                :key="section.friendlyName"
                flat
                class="bg-grey-8"
                style="border: 2px solid #1db885;"
              >
                <q-card-section class="bg-teal-8 text-white">
                  <div class="text-subtitle1">{{ section.friendlyName }}</div>
                </q-card-section>
                <q-card-section class="q-gutter-md">
                  <template v-for="option in sortedDeviceOptions(section.options)" :key="option.optionId">
                    <!-- Text Input -->
                    <q-input
                      v-if="option.type === 'text'"
                      v-model="deviceConfigValues[option.optionId]"
                      :label="option.friendlyName"
                      outlined
                      dense
                      dark
                      :disable="isReadOnly"
                      :hint="option.mandatory ? 'Required' : 'Optional'"
                      :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                    />

                    <!-- Number Input -->
                    <q-input
                      v-else-if="option.type === 'number'"
                      v-model.number="deviceConfigValues[option.optionId]"
                      type="number"
                      :label="option.friendlyName"
                      outlined
                      dense
                      dark
                      :disable="isReadOnly"
                      :hint="option.mandatory ? 'Required' : 'Optional'"
                      :rules="option.mandatory ? [val => val !== null && val !== '' || `${option.friendlyName} is required`] : []"
                    />

                    <!-- Password Input -->
                    <q-input
                      v-else-if="option.type === 'password'"
                      v-model="deviceConfigValues[option.optionId]"
                      type="password"
                      :label="option.friendlyName"
                      outlined
                      dense
                      dark
                      :disable="isReadOnly"
                      :placeholder="form.id ? '••••••••' : ''"
                      @update:model-value="onPasswordFieldChange(option.optionId, $event)"
                      :rules="option.mandatory && !form.id ? [val => !!val || `${option.friendlyName} is required`] : []"
                    >
                      <template v-slot:append>
                        <q-icon v-if="passwordFieldsChanged[option.optionId]" name="warning" color="orange">
                          <q-tooltip>Password will be changed</q-tooltip>
                        </q-icon>
                      </template>
                      <template v-slot:hint>
                        <span v-if="form.id && !passwordFieldsChanged[option.optionId]" class="text-grey-6">
                          Leave blank to keep current password
                        </span>
                        <span v-if="form.id && passwordFieldsChanged[option.optionId]" class="text-orange" style="font-weight: 500;">
                          <q-icon name="warning" size="xs" /> Password will be changed
                        </span>
                      </template>
                    </q-input>

                    <!-- Select/Dropdown -->
                    <q-select
                      v-else-if="option.type === 'select' && (option.options || option.choices)"
                      v-model="deviceConfigValues[option.optionId]"
                      :options="option.options || option.choices"
                      :label="option.friendlyName"
                      outlined
                      dense
                      dark
                      emit-value
                      map-options
                      color="teal"
                      :disable="isReadOnly"
                      :hint="option.mandatory ? 'Required' : 'Optional'"
                      :rules="option.mandatory ? [val => val !== null && val !== '' || `${option.friendlyName} is required`] : []"
                    />

                    <!-- Boolean Checkbox -->
                    <q-checkbox
                      v-else-if="option.type === 'boolean' || option.type === 'checkbox'"
                      v-model="deviceConfigValues[option.optionId]"
                      :label="option.friendlyName"
                      dense
                      color="teal"
                      :disable="isReadOnly"
                    />

                    <!-- Textarea -->
                    <q-input
                      v-else-if="option.type === 'textarea'"
                      v-model="deviceConfigValues[option.optionId]"
                      type="textarea"
                      :label="option.friendlyName"
                      outlined
                      rows="3"
                      dense
                      dark
                      :disable="isReadOnly"
                      :hint="option.mandatory ? 'Required' : 'Optional'"
                      :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                    />

                    <!-- Ordered Multi-Select -->
                    <div v-else-if="option.type === 'orderedmultiselect'" class="q-gutter-md">
                      <div class="text-subtitle2 text-white">{{ option.friendlyName }}</div>
                      <div class="row q-gutter-md">
                        <!-- Available Options -->
                        <div class="col">
                          <div class="text-caption text-teal-3">Available</div>
                          <q-list bordered separator style="border: 1px solid #1db885;" class="bg-grey-8 q-mt-xs">
                            <q-item
                              v-for="avail in availableDeviceChoices(option)"
                              :key="avail"
                              :clickable="!isReadOnly"
                              @click="!isReadOnly && moveDeviceToSelected(option.optionId, avail)"
                            >
                              <q-item-section avatar>
                                <q-icon name="chevron_right" :color="isReadOnly ? 'grey' : 'teal'" />
                              </q-item-section>
                              <q-item-section class="text-white">{{ avail }}</q-item-section>
                            </q-item>
                          </q-list>
                        </div>

                        <!-- Selected Options -->
                        <div class="col">
                          <div class="text-caption text-teal-3">Selected (Ordered)</div>
                          <q-list bordered separator style="border: 1px solid #1db885;" class="bg-grey-8 q-mt-xs">
                            <q-item
                              v-for="(selected, idx) in (deviceConfigValues[option.optionId] || [])"
                              :key="selected"
                              class="q-pa-xs"
                            >
                              <q-item-section avatar>
                                <div class="column q-gutter-xs">
                                  <q-btn
                                    v-if="idx > 0 && !isReadOnly"
                                    flat
                                    dense
                                    round
                                    size="sm"
                                    icon="arrow_upward"
                                    color="teal"
                                    @click="moveDeviceUpSelected(option.optionId, idx)"
                                  />
                                  <q-btn
                                    v-if="idx < (deviceConfigValues[option.optionId] || []).length - 1 && !isReadOnly"
                                    flat
                                    dense
                                    round
                                    size="sm"
                                    icon="arrow_downward"
                                    color="teal"
                                    @click="moveDeviceDownSelected(option.optionId, idx)"
                                  />
                                </div>
                              </q-item-section>
                              <q-item-section class="text-white">{{ selected }}</q-item-section>
                              <q-item-section avatar>
                                <q-btn
                                  v-if="!isReadOnly"
                                  flat
                                  dense
                                  round
                                  size="sm"
                                  icon="chevron_left"
                                  color="teal"
                                  @click="moveDeviceToAvailable(option.optionId, selected)"
                                />
                              </q-item-section>
                            </q-item>
                          </q-list>
                          <div v-if="!deviceConfigValues[option.optionId] || deviceConfigValues[option.optionId].length === 0" class="text-caption text-grey-6 q-mt-md">
                            Click items on the left to select
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>
                </q-card-section>
              </q-card>
            </template>
          </q-card-section>
        </q-scroll-area>

        <!-- Actions -->
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat :label="isReadOnly ? 'Close' : 'Cancel'" color="primary" @click="handleCancel" />
          <q-btn v-if="!isReadOnly" unelevated label="Save" color="positive" @click="save" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Delete Confirmation Dialog -->
    <q-dialog v-model="deleteDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">Confirm Deletion</q-card-section>
        <q-card-section>
          <p>Are you sure you want to delete: <strong>{{ itemToDelete?.name }} ({{ itemToDelete?.mac_address }})</strong>?</p>
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

    <!-- Cancel Confirmation Dialog -->
    <q-dialog v-model="cancelConfirmDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">Discard Changes?</q-card-section>
        <q-card-section>
          <p>Changes will be lost if you proceed without saving.</p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Keep Editing" color="primary" v-close-popup />
          <q-btn unelevated label="Discard" color="negative" @click="discardAndClose" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useAuthStore } from '../stores/auth';
import api from '../api';

const authStore = useAuthStore();

const devices = ref([]);
const deviceTypes = ref([]);
const sites = ref([]);
const lines = ref([]);
const loading = ref(false);
const saving = ref(false);
const dialog = ref(false);
const errorMessage = ref('');
const deleteDialog = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');
const cancelConfirmDialog = ref(false);
const formHasChanges = ref(false);
const originalForm = ref(null);
const originalLines = ref(null);
const originalConfig = ref(null);
const lineDisassociationWarning = ref('');

// Compute if user is read-only
const isReadOnly = computed(() => authStore.user?.role === 'readonly');

const emptyForm = () => ({
  id: null,
  name: '',
  mac_address: '',
  device_type_id: null,
  site: null
});
const form = ref(emptyForm());
const formLines = ref([]);
const deviceConfigValues = ref({});
const passwordFieldsChanged = ref({});
const isValidMac = (val) => {
  if (!val) return false;
  const patterns = [
    /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/,   // aa:bb:cc:dd:ee:ff or aa-bb-cc-dd-ee-ff
    /^[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}$/, // aabb.ccdd.eeff
    /^[0-9A-Fa-f]{12}$/ // aabbccddeeff
  ];
  return patterns.some(rx => rx.test(val));
};

const normalizeMac = (val) => {
  if (!val) return val;
  const cleaned = val.replace(/[^0-9A-Fa-f]/g, '').toUpperCase();
  if (cleaned.length !== 12) return val;
  return cleaned.match(/.{1,2}/g).join(':');
};


const selectedDeviceType = computed(() => {
  if (!form.value.device_type_id) return null;
  return deviceTypes.value.find(dt => dt.typeId === form.value.device_type_id);
});

const siteNameById = computed(() => {
  const map = {};
  sites.value.forEach(s => {
    map[s.id] = s.name;
  });
  return map;
});

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'mac_address', label: 'MAC Address', field: 'mac_address', align: 'left', sortable: true },
  { name: 'device_type_id', label: 'Type', field: 'device_type_id', align: 'left', sortable: true },
  { name: 'site', label: 'Site', field: 'site', format: val => siteNameById.value[val] || val, align: 'left', sortable: true },
  {
    name: 'line_directory_numbers',
    label: 'DNs',
    field: row => row.line_directory_numbers || [],
    format: val => (val || []).join(', '),
    align: 'left',
    sortable: true
  },
  {
    name: 'last_provisioned_at',
    label: 'Last Config Time',
    field: 'last_provisioned_at',
    format: val => val ? new Date(val).toLocaleString() : 'Never',
    align: 'left',
    sortable: true
  },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' }
];

const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;
  // Handle field-specific validation errors (e.g., {"mac_address": ["device with this mac address already exists."]})
  if (error.response?.data && typeof error.response.data === 'object') {
    const fieldErrors = Object.entries(error.response.data)
      .filter(([, val]) => Array.isArray(val) && val.length > 0)
      .map(([field, msgs]) => `${field}: ${msgs[0]}`)
      .join('; ');
    if (fieldErrors) return fieldErrors;
  }
  if (error.response?.status === 409) {
    return 'Cannot complete this operation: The item is currently in use by other records.';
  }
  if (error.response?.status === 404) return 'The requested item was not found.';
  if (error.response?.status === 403) return 'You do not have permission to perform this action.';
  if (error.response?.status === 401) return 'Your session has expired. Please log in again.';
  if (error.response?.statusText) return `Operation failed: ${error.response.statusText}`;
  if (error.request) return 'Network error: Unable to reach the server.';
  return 'An unexpected error occurred. Please try again.';
};

const loadDevices = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/devices/');
    devices.value = data;
  } finally {
    loading.value = false;
  }
};

const loadDeviceTypes = async () => {
  const { data } = await api.get('/device-types/');
  deviceTypes.value = data.map(dt => ({
    ...dt,
    label: `${dt.manufacturer} ${dt.model}`
  }));
};

const loadSites = async () => {
  const { data } = await api.get('/sites/');
  sites.value = data;
};

const loadLines = async () => {
  const { data } = await api.get('/lines/');
  lines.value = data;
};

const lineOptions = (index) => {
  // Lines in use by other devices (respect shared flag for other devices)
  const assignedLineIds = new Set();
  devices.value.forEach(device => {
    if (device.line_1 !== null && device.id !== form.value.id) {
      assignedLineIds.add(device.line_1);
    }
    if (device.lines) {
      device.lines.forEach(lineId => {
        if (device.id !== form.value.id) {
          assignedLineIds.add(lineId);
        }
      });
    }
  });

  // Sort lines alphabetically by name (fallback to directory_number)
  const sorted = [...lines.value].sort((a, b) => {
    const labelA = `${a.name} (${a.directory_number})`.toLowerCase();
    const labelB = `${b.name} (${b.directory_number})`.toLowerCase();
    return labelA.localeCompare(labelB);
  });

  return sorted
    .filter(line => {
      // Exclude if selected in another slot on this form (handles id or object)
      const selectedElsewhere = formLines.value.some((val, idx) => {
        if (idx === index) return false;
        const selectedId = typeof val === 'object' ? val?.id : val;
        return selectedId === line.id;
      });
      if (selectedElsewhere) return false;

      // If line is assigned to another device and not shared, exclude
      const assignedElsewhere = assignedLineIds.has(line.id);
      if (assignedElsewhere && !line.is_shared) return false;

      return true;
    })
    .map(line => ({
      ...line,
      label: `${line.name} (${line.directory_number})${line.is_shared ? ' [Shared]' : ''}`
    }));
};

const sortedDeviceSections = computed(() => {
  if (!selectedDeviceType.value?.deviceSpecificOptions?.sections) return [];
  return [...selectedDeviceType.value.deviceSpecificOptions.sections].sort(
    (a, b) => (a.uiOrder || 999) - (b.uiOrder || 999)
  );
});

const sortedDeviceOptions = (options) => {
  if (!options) return [];
  return [...options].sort((a, b) => (a.uiOrder || 999) - (b.uiOrder || 999));
};

const availableDeviceChoices = (option) => {
  const choicesArray = option.choices || option.options;
  if (!choicesArray || !Array.isArray(choicesArray)) return [];
  const selected = deviceConfigValues.value[option.optionId];
  const selectedArray = Array.isArray(selected) ? selected : (selected ? [selected] : []);
  return choicesArray.filter(opt => !selectedArray.includes(opt));
};

const moveDeviceToSelected = (optionId, value) => {
  if (!deviceConfigValues.value[optionId]) {
    deviceConfigValues.value[optionId] = [];
  }
  if (!deviceConfigValues.value[optionId].includes(value)) {
    deviceConfigValues.value[optionId].push(value);
  }
};

const moveDeviceToAvailable = (optionId, value) => {
  if (deviceConfigValues.value[optionId]) {
    deviceConfigValues.value[optionId] = deviceConfigValues.value[optionId].filter(v => v !== value);
  }
};

const moveDeviceUpSelected = (optionId, idx) => {
  if (idx > 0 && deviceConfigValues.value[optionId]) {
    const temp = deviceConfigValues.value[optionId][idx - 1];
    deviceConfigValues.value[optionId][idx - 1] = deviceConfigValues.value[optionId][idx];
    deviceConfigValues.value[optionId][idx] = temp;
  }
};

const moveDeviceDownSelected = (optionId, idx) => {
  if (idx < (deviceConfigValues.value[optionId] || []).length - 1 && deviceConfigValues.value[optionId]) {
    const temp = deviceConfigValues.value[optionId][idx + 1];
    deviceConfigValues.value[optionId][idx + 1] = deviceConfigValues.value[optionId][idx];
    deviceConfigValues.value[optionId][idx] = temp;
  }
};

const optionIdsForType = (deviceType) => {
  if (!deviceType?.deviceSpecificOptions?.sections) return new Set();
  const ids = new Set();
  deviceType.deviceSpecificOptions.sections.forEach(section => {
    (section.options || []).forEach(option => {
      if (option.optionId) ids.add(option.optionId);
    });
  });
  return ids;
};

const preserveConfigForType = (newType) => {
  const allowedIds = optionIdsForType(newType);
  const currentConfig = { ...deviceConfigValues.value };
  const filtered = {};
  allowedIds.forEach(key => {
    if (currentConfig[key] !== undefined) {
      filtered[key] = currentConfig[key];
    }
  });
  deviceConfigValues.value = filtered;
};

watch(
  () => form.value.device_type_id,
  (newTypeId) => {
    if (!newTypeId) {
      formLines.value = [];
      deviceConfigValues.value = {};
      lineDisassociationWarning.value = '';
      return;
    }
    const newType = deviceTypes.value.find(dt => dt.typeId === newTypeId);
    const prevLines = [...formLines.value];
    const newCount = newType?.numberOfLines || 0;
    const maxKeep = Math.min(prevLines.length, newCount);
    const kept = prevLines.slice(0, maxKeep);
    const removed = prevLines.slice(newCount).filter(val => val !== null && val !== undefined);

    // Preserve overlapping config values
    preserveConfigForType(newType);

    // Pad or trim line assignments based on new device type
    const updatedLines = [...kept];
    while (updatedLines.length < newCount) {
      updatedLines.push(null);
    }
    formLines.value = updatedLines;

    lineDisassociationWarning.value = removed.length
      ? `${removed.length} number of lines will be disassociated from this device`
      : '';
  }
);

const openCreate = () => {
  form.value = emptyForm();
  formLines.value = [];
  deviceConfigValues.value = {};
  passwordFieldsChanged.value = {};
  errorMessage.value = '';
  lineDisassociationWarning.value = '';
  originalForm.value = null;
  originalLines.value = null;
  originalConfig.value = null;
  formHasChanges.value = false;
  dialog.value = true;
};

const onPasswordFieldChange = (optionId, value) => {
  passwordFieldsChanged.value[optionId] = form.value.id && value && value.length > 0;
};

const openEdit = async (row) => {
  form.value = { ...row };
  errorMessage.value = '';
  lineDisassociationWarning.value = '';
  passwordFieldsChanged.value = {};
  
  // Wait for selectedDeviceType to compute
  await new Promise(resolve => setTimeout(resolve, 0));
  
  // Load line assignments
  if (selectedDeviceType.value) {
    formLines.value = Array(selectedDeviceType.value.numberOfLines).fill(null);
    if (row.line_1) formLines.value[0] = row.line_1;
    if (row.lines && Array.isArray(row.lines)) {
      row.lines.forEach((lineId, idx) => {
        const formIdx = idx + 1; // lines array starts at slot 1 (slot 0 is line_1)
        if (formIdx < formLines.value.length) {
          formLines.value[formIdx] = lineId;
        }
      });
    }
  }
  
  // Load device-specific configuration
  deviceConfigValues.value = row.device_specific_configuration || {};
  
  // Clear password fields for security - user must enter new ones if they want to change them
  if (selectedDeviceType.value?.deviceSpecificOptions?.sections) {
    selectedDeviceType.value.deviceSpecificOptions.sections.forEach(section => {
      section.options?.forEach(option => {
        if (option.type === 'password') {
          deviceConfigValues.value[option.optionId] = '';
        }
      });
    });
  }
  
  // Track original state for changes detection
  originalForm.value = JSON.parse(JSON.stringify(form.value));
  originalLines.value = JSON.parse(JSON.stringify(formLines.value));
  originalConfig.value = JSON.parse(JSON.stringify(deviceConfigValues.value));
  formHasChanges.value = false;
  
  dialog.value = true;
};

const save = async () => {
  errorMessage.value = '';
  
  if (!form.value.name || form.value.name.trim() === '') {
    errorMessage.value = 'Name is required';
    return;
  }
  if (!form.value.mac_address || form.value.mac_address.trim() === '') {
    errorMessage.value = 'MAC Address is required';
    return;
  }
  if (!isValidMac(form.value.mac_address)) {
    errorMessage.value = 'Invalid MAC Address format';
    return;
  }
  if (form.value.device_type_id === null) {
    errorMessage.value = 'Device Type is required';
    return;
  }
  if (form.value.site === null) {
    errorMessage.value = 'Site is required';
    return;
  }
  if (!formLines.value.length || formLines.value[0] === null || formLines.value[0] === undefined) {
    errorMessage.value = 'Line 1 is required';
    return;
  }

  saving.value = true;
  try {
    form.value.mac_address = normalizeMac(form.value.mac_address);
    
    // Prepare device config, removing password fields that haven't been changed
    const configToSend = { ...deviceConfigValues.value };
    if (form.value.id) {
      Object.keys(configToSend).forEach(key => {
        if (!passwordFieldsChanged.value[key]) {
          // Check if this is a password field that wasn't changed
          const isPasswordField = selectedDeviceType.value?.deviceSpecificOptions?.sections?.some(section =>
            section.options?.some(opt => opt.optionId === key && opt.type === 'password')
          );
          if (isPasswordField && (!configToSend[key] || configToSend[key] === '')) {
            delete configToSend[key];
          }
        }
      });
    }
    
    const payload = {
      ...form.value,
      line_1: formLines.value[0],
      lines: formLines.value.slice(1).filter(v => v !== null && v !== undefined),
      device_specific_configuration: configToSend
    };
    
    if (payload.id) {
      await api.put(`/devices/${payload.id}/`, payload);
    } else {
      await api.post('/devices/', payload);
    }
    dialog.value = false;
    passwordFieldsChanged.value = {};
    await loadDevices();
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    saving.value = false;
  }
};

const openDeleteConfirm = (row) => {
  itemToDelete.value = row;
  deleteError.value = '';
  deleteDialog.value = true;
};

const confirmDelete = async () => {
  try {
    await api.delete(`/devices/${itemToDelete.value.id}/`);
    deleteDialog.value = false;
    await loadDevices();
  } catch (error) {
    deleteError.value = extractErrorMessage(error);
  }
};

const checkFormChanges = () => {
  if (!originalForm.value) return false;
  const formChanged = JSON.stringify(form.value) !== JSON.stringify(originalForm.value);
  const linesChanged = JSON.stringify(formLines.value) !== JSON.stringify(originalLines.value);
  const configChanged = JSON.stringify(deviceConfigValues.value) !== JSON.stringify(originalConfig.value);
  formHasChanges.value = formChanged || linesChanged || configChanged;
  return formHasChanges.value;
};

const handleCancel = () => {
  if (checkFormChanges()) {
    cancelConfirmDialog.value = true;
  } else {
    dialog.value = false;
  }
};

const discardAndClose = () => {
  cancelConfirmDialog.value = false;
  dialog.value = false;
};

watch(
  () => [form.value, formLines.value, deviceConfigValues.value],
  () => checkFormChanges(),
  { deep: true }
);

onMounted(async () => {
  await Promise.all([loadDevices(), loadDeviceTypes(), loadSites(), loadLines()]);
});
</script>
