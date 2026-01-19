<template>
  <q-layout view="hHh lpR fFf">
    <q-header v-if="!isLoginPage" elevated>
      <q-toolbar>
        <q-toolbar-title>Phone Provisioning Manager</q-toolbar-title>
        <q-tabs shrink stretch class="text-white">
          <q-route-tab to="/device-types" label="Device Types" icon="schema" />
          <q-route-tab to="/devices" label="Devices" icon="devices" />
          <q-route-tab to="/sip-servers" label="SIP Servers" icon="router" />
          <q-route-tab to="/sites" label="Sites" icon="business" />
          <q-route-tab to="/lines" label="Lines" icon="call" />
        </q-tabs>
        <q-space />
        <div class="row items-center q-gutter-md q-pr-md">
          <div class="text-subtitle2">{{ username }}</div>
          <q-btn
            flat
            round
            dense
            icon="logout"
            color="white"
            @click="logout"
            title="Logout"
          />
        </div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const username = ref('');

const isLoginPage = computed(() => route.path === '/login');

onMounted(() => {
  // Get username from store after mount when Pinia is ready
  username.value = authStore.currentUser?.username || '';
});

const logout = () => {
  authStore.logout();
  router.push('/login');
};
</script>
