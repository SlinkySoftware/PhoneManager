<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">Device Types</div>
    <q-card flat bordered class="bg-dark">
      <q-card-section>
        <q-btn color="primary" flat icon="refresh" label="Refresh" @click="loadTypes" />
      </q-card-section>
      <q-separator />
      <q-card-section>
        <q-list bordered separator>
          <q-item v-for="dt in deviceTypes" :key="dt.typeId">
            <q-item-section>
              <q-item-label class="text-subtitle1">{{ dt.manufacturer }} {{ dt.model }}</q-item-label>
              <q-item-label caption>TypeID: {{ dt.typeId }} · Lines: {{ dt.numberOfLines }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn color="secondary" flat label="Common Options" @click="select(dt)" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <q-dialog v-model="showDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="text-h6">{{ selected?.manufacturer }} {{ selected?.model }}</q-card-section>
        <q-card-section>
          <pre class="text-body2">{{ selected }}</pre>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import axios from 'axios';

const deviceTypes = ref([]);
const selected = ref(null);
const showDialog = ref(false);
const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api' });

const loadTypes = async () => {
  const { data } = await api.get('/device-types/');
  deviceTypes.value = data;
};

const select = (dt) => {
  selected.value = dt;
  showDialog.value = true;
};

onMounted(loadTypes);
</script>
