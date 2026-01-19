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
          <q-btn dense flat icon="delete" color="negative" @click="remove(props.row)" />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialog">
      <q-card style="min-width: 480px">
        <q-card-section class="text-h6">{{ form.id ? 'Edit' : 'Create' }} Line</q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="form.name" label="Name" dense outlined />
          <q-input v-model="form.directory_number" label="Directory Number (+E164)" dense outlined />
          <q-input v-model="form.registration_account" label="Registration Account" dense outlined />
          <q-input v-model="form.registration_password" label="Registration Password" dense outlined type="password" />
          <q-toggle v-model="form.is_shared" label="Shared" color="primary" />
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
import api from '../api';

const lines = ref([]);
const loading = ref(false);
const dialog = ref(false);
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
  dialog.value = true;
};

const openEdit = (row) => {
  form.value = { ...row };
  dialog.value = true;
};

const save = async () => {
  const payload = { ...form.value };
  if (payload.id) {
    await api.put(`/lines/${payload.id}/`, payload);
  } else {
    await api.post('/lines/', payload);
  }
  dialog.value = false;
  await loadLines();
};

const remove = async (row) => {
  await api.delete(`/lines/${row.id}/`);
  await loadLines();
};

onMounted(loadLines);
</script>
