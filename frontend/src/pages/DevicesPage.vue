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

    <q-dialog v-model="dialog">
      <q-card style="min-width: 480px">
        <q-card-section class="text-h6">{{ form.id ? 'Edit' : 'Create' }} Device</q-card-section>
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
            :rules="[val => !!val || 'Name is required']"
          />
          <q-input
            v-model="form.mac_address"
            label="MAC Address"
            dense
            outlined
            :rules="[
              val => !!val || 'MAC Address is required',
              val => /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/.test(val) || 'Invalid MAC format (e.g., 00:11:22:33:44:55)'
            ]"
          />
          <q-select
            v-model="form.device_type"
            :options="deviceTypes"
            option-value="id"
            option-label="label"
            label="Device Type"
            dense
            outlined
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
            :rules="[val => val !== null || 'Site is required']"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn unelevated color="primary" label="Save" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>

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
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import api from '../api';

const devices = ref([]);
const deviceTypes = ref([]);
const sites = ref([]);
const loading = ref(false);
const dialog = ref(false);
const errorMessage = ref('');
const deleteDialog = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');

const emptyForm = () => ({
  id: null,
  name: '',
  mac_address: '',
  device_type: null,
  site: null
});
const form = ref(emptyForm());

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'mac_address', label: 'MAC Address', field: 'mac_address', align: 'left' },
  { name: 'device_type', label: 'Type', field: 'device_type', align: 'left' },
  { name: 'site', label: 'Site', field: 'site', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' }
];

const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;
  if (error.response?.statusText) return `Error: ${error.response.statusText}`;
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
    id: dt.typeId,
    label: `${dt.manufacturer} ${dt.model}`
  }));
};

const loadSites = async () => {
  const { data } = await api.get('/sites/');
  sites.value = data;
};

const openCreate = () => {
  form.value = emptyForm();
  errorMessage.value = '';
  dialog.value = true;
};

const openEdit = (row) => {
  form.value = { ...row };
  errorMessage.value = '';
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
  if (form.value.device_type === null) {
    errorMessage.value = 'Device Type is required';
    return;
  }
  if (form.value.site === null) {
    errorMessage.value = 'Site is required';
    return;
  }

  try {
    const payload = { ...form.value };
    if (payload.id) {
      await api.put(`/devices/${payload.id}/`, payload);
    } else {
      await api.post('/devices/', payload);
    }
    dialog.value = false;
    await loadDevices();
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
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
  await Promise.all([loadDevices(), loadDeviceTypes(), loadSites()]);
});
</script>
