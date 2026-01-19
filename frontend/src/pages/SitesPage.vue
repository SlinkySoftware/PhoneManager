<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">Sites</div>
      <q-space />
      <q-btn color="primary" icon="add" label="Add" @click="openCreate" class="q-ml-sm" />
      <q-btn flat color="secondary" icon="refresh" label="Refresh" @click="loadSites" class="q-ml-sm" />
    </div>

    <q-table
      flat
      bordered
      :rows="sites"
      :columns="columns"
      row-key="id"
      :loading="loading"
      no-data-label="No sites yet"
    >
      <template #body-cell-primary_sip_server="props">
        <q-td>{{ serverLabel(props.value) }}</q-td>
      </template>
      <template #body-cell-secondary_sip_server="props">
        <q-td>{{ serverLabel(props.value) }}</q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td align="right">
          <q-btn dense flat icon="edit" color="primary" @click="openEdit(props.row)" />
          <q-btn dense flat icon="delete" color="negative" @click="openDeleteConfirm(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 520px">
        <q-card-section class="text-h6">{{ form.id ? 'Edit' : 'Create' }} Site</q-card-section>
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
          <q-select
            v-model="form.primary_sip_server"
            :options="serverOptions"
            label="Primary SIP Server"
            dense
            outlined
            emit-value
            map-options
            :rules="[val => val !== null || 'Primary SIP Server is required']"
          />
          <q-select
            v-model="form.secondary_sip_server"
            :options="serverOptions"
            label="Secondary SIP Server (optional)"
            dense
            outlined
            emit-value
            map-options
            clearable
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
import { computed, onMounted, ref } from 'vue';
import api from '../api';

const sites = ref([]);
const sipServers = ref([]);
const loading = ref(false);
const dialog = ref(false);
const formRef = ref(null);
const errorMessage = ref('');
const deleteDialog = ref(false);
const itemToDelete = ref(null);
const deleteError = ref('');

const emptyForm = () => ({ id: null, name: '', primary_sip_server: null, secondary_sip_server: null });
const form = ref(emptyForm());

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'primary_sip_server', label: 'Primary SIP', field: 'primary_sip_server', align: 'left' },
  { name: 'secondary_sip_server', label: 'Secondary SIP', field: 'secondary_sip_server', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' }
];

const serverOptions = computed(() =>
  sipServers.value.map((s) => ({ label: `${s.name} (${s.host}:${s.port})`, value: s.id }))
);

const serverMap = computed(() => Object.fromEntries(sipServers.value.map((s) => [s.id, s])));

const serverLabel = (id) => {
  if (!id) return '';
  const s = serverMap.value[id];
  return s ? `${s.name} (${s.host}:${s.port}/${s.transport})` : id;
};

const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;
  if (error.response?.statusText) return `Error: ${error.response.statusText}`;
  return 'An unexpected error occurred. Please try again.';
};

const loadSipServers = async () => {
  const { data } = await api.get('/sip-servers/');
  sipServers.value = data;
};

const loadSites = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/sites/');
    sites.value = data;
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
  if (form.value.primary_sip_server === null) {
    errorMessage.value = 'Primary SIP Server is required';
    return;
  }

  try {
    const payload = { ...form.value };
    if (!payload.secondary_sip_server) {
      payload.secondary_sip_server = null;
    }
    if (payload.id) {
      await api.put(`/sites/${payload.id}/`, payload);
    } else {
      await api.post('/sites/', payload);
    }
    dialog.value = false;
    await loadSites();
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
    await api.delete(`/sites/${itemToDelete.value.id}/`);
    deleteDialog.value = false;
    await loadSites();
  } catch (error) {
    deleteError.value = extractErrorMessage(error);
  }
};

onMounted(async () => {
  await loadSipServers();
  await loadSites();
});
</script>
