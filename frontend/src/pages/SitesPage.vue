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
          <q-btn dense flat icon="delete" color="negative" @click="remove(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 520px">
        <q-card-section class="text-h6">{{ form.id ? 'Edit' : 'Create' }} Site</q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="form.name" label="Name" dense outlined />
          <q-select
            v-model="form.primary_sip_server"
            :options="serverOptions"
            label="Primary SIP Server"
            dense
            outlined
            emit-value
            map-options
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
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import api from '../api';

const sites = ref([]);
const sipServers = ref([]);
const loading = ref(false);
const dialog = ref(false);

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
  dialog.value = true;
};

const openEdit = (row) => {
  form.value = { ...row };
  dialog.value = true;
};

const save = async () => {
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
};

const remove = async (row) => {
  await api.delete(`/sites/${row.id}/`);
  await loadSites();
};

onMounted(async () => {
  await loadSipServers();
  await loadSites();
});
</script>
