<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">SIP Servers</div>
      <q-badge v-if="isReadOnly" color="orange" label="Read Only Mode" class="q-ml-md" />
      <q-space />
      <q-btn v-if="!isReadOnly" color="primary" icon="add" label="Add" @click="openCreate" class="q-ml-sm" />
      <q-btn flat color="secondary" icon="refresh" label="Refresh" @click="loadServers" class="q-ml-sm" />
    </div>

    <q-table
      flat
      bordered
      :rows="servers"
      :columns="columns"
      row-key="id"
      :loading="loading"
      no-data-label="No SIP servers yet"
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

    <q-dialog v-model="dialog">
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">{{ isReadOnly && form.id ? 'View' : form.id ? 'Edit' : 'Create' }} SIP Server</q-card-section>
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
            v-model="form.host"
            label="Host"
            dense
            outlined
            :disable="isReadOnly"
            :rules="[
              val => !!val || 'Host is required',
              val => /^[a-zA-Z0-9.\-]+$/.test(val) || 'Invalid hostname format'
            ]"
          />
          <q-input
            v-model.number="form.port"
            type="number"
            label="Port"
            dense
            outlined
            :disable="isReadOnly"
            :rules="[
              val => val !== null && val !== '' || 'Port is required',
              val => val > 0 && val <= 65535 || 'Port must be between 1 and 65535'
            ]"
          />
          <q-select
            v-model="form.transport"
            :options="transports"
            label="Transport"
            dense
            outlined
            :disable="isReadOnly"
            :rules="[val => !!val || 'Transport is required']"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="isReadOnly ? 'Close' : 'Cancel'" color="primary" v-close-popup />
          <q-btn v-if="!isReadOnly" unelevated color="primary" label="Save" @click="save" />
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
import { computed, onMounted, ref } from 'vue';
import api from '../api';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();
const isReadOnly = computed(() => authStore.user?.role === 'readonly');

const servers = ref([]);
const loading = ref(false);
const dialog = ref(false);
const errorMessage = ref('');
const deleteDialog = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');
const transports = ['TLS', 'UDP', 'TCP'];

const emptyForm = () => ({ id: null, name: '', host: '', port: 5060, transport: 'UDP' });
const form = ref(emptyForm());

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'host', label: 'Host', field: 'host', align: 'left' },
  { name: 'port', label: 'Port', field: 'port', align: 'left' },
  { name: 'transport', label: 'Transport', field: 'transport', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' }
];

const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;
  
  if (error.response?.status === 409) {
    return 'Cannot complete this operation: The item is currently in use by other records. Please remove dependencies first.';
  }
  if (error.response?.status === 404) return 'The requested item was not found. It may have been deleted.';
  if (error.response?.status === 403) return 'You do not have permission to perform this action.';
  if (error.response?.status === 401) return 'Your session has expired. Please log in again.';
  
  if (error.response?.statusText) return `Operation failed: ${error.response.statusText}`;
  if (error.request) return 'Network error: Unable to reach the server. Please check your connection.';
  
  return 'An unexpected error occurred. Please try again or contact support if the problem persists.';
};

const loadServers = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/sip-servers/');
    servers.value = data;
  } finally {
    loading.value = false;
  }
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
  if (!form.value.host || form.value.host.trim() === '') {
    errorMessage.value = 'Host is required';
    return;
  }
  if (!form.value.port || form.value.port <= 0 || form.value.port > 65535) {
    errorMessage.value = 'Port must be between 1 and 65535';
    return;
  }
  if (!form.value.transport) {
    errorMessage.value = 'Transport is required';
    return;
  }

  try {
    const payload = { ...form.value };
    if (payload.id) {
      await api.put(`/sip-servers/${payload.id}/`, payload);
    } else {
      await api.post('/sip-servers/', payload);
    }
    dialog.value = false;
    await loadServers();
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
    await api.delete(`/sip-servers/${itemToDelete.value.id}/`);
    deleteDialog.value = false;
    await loadServers();
  } catch (error) {
    deleteError.value = extractErrorMessage(error);
  }
};

onMounted(loadServers);
</script>
