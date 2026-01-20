<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">Devices</div>
      <q-space />
      <q-btn color="primary" icon="add" label="Add" @click="openCreate" class="q-ml-sm" />
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
    >
      <template #body-cell-actions="props">
        <q-td align="right">
          <q-btn dense flat icon="edit" color="primary" @click="openEdit(props.row)" />
          <q-btn dense flat icon="delete" color="negative" @click="openDeleteConfirm(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Create/Edit Dialog -->
    <q-dialog v-model="dialog" class="q-gutter-md">
      <q-card style="min-width: 600px; max-width: 800px" class="bg-grey-9">
        <q-card-section class="bg-teal-9 text-white">
          <div class="text-h6">{{ form.id ? 'Edit' : 'Create' }} Device</div>
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
                  :rules="[val => !!val || 'Name is required']"
                />
                <q-input
                  v-model="form.mac_address"
                  label="MAC Address"
                  dense
                  outlined
                  dark
                  :rules="[
                    val => !!val || 'MAC Address is required',
                    val => /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/.test(val) || 'Invalid MAC format'
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
                  @update:model-value="onDeviceTypeChange"
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
                  color="teal"
                  :rules="[val => val !== null || 'Site is required']"
                />
              </q-card-section>
            </q-card>

            <!-- Lines Card -->
            <q-card v-if="selectedDeviceType" flat class="bg-grey-8" style="border: 2px solid #1db885;">
              <q-card-section class="bg-teal-8 text-white">
                <div class="text-subtitle1">Lines ({{ selectedDeviceType.numberOfLines }} line{{ selectedDeviceType.numberOfLines !== 1 ? 's' : '' }})</div>
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
                      :hint="option.mandatory ? 'Required' : 'Optional'"
                      :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                    />

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
                              clickable
                              @click="moveDeviceToSelected(option.optionId, avail)"
                            >
                              <q-item-section avatar>
                                <q-icon name="chevron_right" color="teal" />
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
                                    v-if="idx > 0"
                                    flat
                                    dense
                                    round
                                    size="sm"
                                    icon="arrow_upward"
                                    color="teal"
                                    @click="moveDeviceUpSelected(option.optionId, idx)"
                                  />
                                  <q-btn
                                    v-if="idx < (deviceConfigValues[option.optionId] || []).length - 1"
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
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn unelevated label="Save" color="positive" @click="save" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Delete Confirmation Dialog -->
    <q-dialog v-model="deleteDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">Confirm Deletion</q-card-section>
        <q-card-section>
          <p>Are you sure you want to delete: <strong>{{ itemToDelete?.mac_address }}</strong>?</p>
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
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import api from '../api';

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

const selectedDeviceType = computed(() => {
  if (!form.value.device_type_id) return null;
  return deviceTypes.value.find(dt => dt.typeId === form.value.device_type_id);
});

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'mac_address', label: 'MAC Address', field: 'mac_address', align: 'left' },
  { name: 'device_type_id', label: 'Type', field: 'device_type_id', align: 'left' },
  { name: 'site', label: 'Site', field: 'site', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' }
];

const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;
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
      label: `${line.name} (${line.directory_number})`
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

const onDeviceTypeChange = () => {
  // Reset device-specific configuration and lines when device type changes
  deviceConfigValues.value = {};
  formLines.value = Array(selectedDeviceType.value?.numberOfLines || 0).fill(null);
};

const openCreate = () => {
  form.value = emptyForm();
  formLines.value = [];
  deviceConfigValues.value = {};
  errorMessage.value = '';
  dialog.value = true;
};

const openEdit = async (row) => {
  form.value = { ...row };
  errorMessage.value = '';
  
  // Wait for selectedDeviceType to compute
  await new Promise(resolve => setTimeout(resolve, 0));
  
  // Load line assignments
  if (selectedDeviceType.value) {
    formLines.value = Array(selectedDeviceType.value.numberOfLines).fill(null);
    if (row.line_1) formLines.value[0] = row.line_1;
    if (row.lines) {
      row.lines.forEach((lineId, idx) => {
        if (idx < formLines.value.length) {
          formLines.value[idx] = lineId;
        }
      });
    }
  }
  
  // Load device-specific configuration
  deviceConfigValues.value = row.device_specific_configuration || {};
  
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
  if (!/^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/.test(form.value.mac_address)) {
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
    const payload = {
      ...form.value,
      line_1: formLines.value[0],
      lines: formLines.value.slice(1),
      device_specific_configuration: deviceConfigValues.value
    };
    
    if (payload.id) {
      await api.put(`/devices/${payload.id}/`, payload);
    } else {
      await api.post('/devices/', payload);
    }
    dialog.value = false;
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

onMounted(async () => {
  await Promise.all([loadDevices(), loadDeviceTypes(), loadSites(), loadLines()]);
});
</script>
