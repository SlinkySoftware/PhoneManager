<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">SIP Servers</div>
      <q-space />
      <q-btn color="primary" icon="add" label="Add" @click="openCreate" class="q-ml-sm" />
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
    >
      <template #body-cell-actions="props">
        <q-td align="right">
          <q-btn dense flat icon="edit" color="primary" @click="openEdit(props.row)" />
          <q-btn dense flat icon="delete" color="negative" @click="remove(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">{{ form.id ? 'Edit' : 'Create' }} SIP Server</q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="form.name" label="Name" dense outlined />
          <q-input v-model="form.host" label="Host" dense outlined />
          <q-input v-model.number="form.port" type="number" label="Port" dense outlined />
          <q-select
            v-model="form.transport"
            :options="transports"
            label="Transport"
            dense
            outlined
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
import { onMounted, ref } from 'vue';
import axios from 'axios';

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api' });

const servers = ref([]);
const loading = ref(false);
const dialog = ref(false);
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
  dialog.value = true;
};

const openEdit = (row) => {
  form.value = { ...row };
  dialog.value = true;
};

const save = async () => {
  const payload = { ...form.value };
  if (payload.id) {
    await api.put(`/sip-servers/${payload.id}/`, payload);
  } else {
    await api.post('/sip-servers/', payload);
  }
  dialog.value = false;
  await loadServers();
};

const remove = async (row) => {
  await api.delete(`/sip-servers/${row.id}/`);
  await loadServers();
};

onMounted(loadServers);
</script>
