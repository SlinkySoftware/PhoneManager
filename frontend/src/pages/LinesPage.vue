<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">Lines</div>
      <q-space />
      <q-btn color="primary" icon="add" label="Add" @click="openCreate" class="q-ml-sm" />
      <q-btn flat color="secondary" icon="refresh" label="Refresh" @click="loadLines" class="q-ml-sm" />
    </div>

    <q-table
      flat
      bordered
      :rows="lines"
      :columns="columns"
      row-key="id"
      :loading="loading"
      no-data-label="No lines yet"
    >
      <template #body-cell-is_shared="props">
        <q-td>{{ props.value ? 'Yes' : 'No' }}</q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td align="right">
          <q-btn dense flat icon="edit" color="primary" @click="openEdit(props.row)" />
          <q-btn dense flat icon="delete" color="negative" @click="openDeleteConfirm(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 480px">
        <q-card-section class="text-h6">{{ form.id ? 'Edit' : 'Create' }} Line</q-card-section>
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
            v-model="form.directory_number"
            label="Directory Number (+E164)"
            dense
            outlined
            :rules="[
              val => !!val || 'Directory Number is required',
              val => /^\+?[0-9]{7,15}$/.test(val) || 'Invalid E164 format (e.g., +61299999999)'
            ]"
          />
          <q-input
            v-model="form.registration_account"
            label="Registration Account"
            dense
            outlined
            :rules="[val => !!val || 'Registration Account is required']"
          />
          <q-input
            v-model="form.registration_password"
            label="Registration Password"
            dense
            outlined
            type="password"
            :rules="[val => !!val || 'Password is required']"
          />
          <q-toggle v-model="form.is_shared" label="Shared" color="primary" />
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

const lines = ref([]);
const loading = ref(false);
const dialog = ref(false);
const errorMessage = ref('');
const deleteDialog = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');

const emptyForm = () => ({
  id: null,
  name: '',
  directory_number: '',
  registration_account: '',
  registration_password: '',
  is_shared: false
});
const form = ref(emptyForm());

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'directory_number', label: 'Directory Number', field: 'directory_number', align: 'left' },
  { name: 'registration_account', label: 'Reg Account', field: 'registration_account', align: 'left' },
  { name: 'is_shared', label: 'Shared', field: 'is_shared', align: 'left' },
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

const loadLines = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/lines/');
    lines.value = data;
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
  if (!form.value.directory_number || form.value.directory_number.trim() === '') {
    errorMessage.value = 'Directory Number is required';
    return;
  }
  if (!form.value.registration_account || form.value.registration_account.trim() === '') {
    errorMessage.value = 'Registration Account is required';
    return;
  }

  try {
    const payload = { ...form.value };
    if (payload.id) {
      await api.put(`/lines/${payload.id}/`, payload);
    } else {
      await api.post('/lines/', payload);
    }
    dialog.value = false;
    await loadLines();
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
    await api.delete(`/lines/${itemToDelete.value.id}/`);
    deleteDialog.value = false;
    await loadLines();
  } catch (error) {
    deleteError.value = extractErrorMessage(error);
  }
};

onMounted(loadLines);
</script>
