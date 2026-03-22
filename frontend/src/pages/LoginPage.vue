<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <div class="login-page flex flex-center">
    <q-card style="width: 100%; max-width: 400px" class="bg-grey-9 text-white">
      <q-card-section class="bg-grey-10 text-white">
        <div class="text-h5">Phone Provisioning Manager</div>
        <div class="text-subtitle2">Login to continue</div>
      </q-card-section>

      <q-card-section class="q-pt-lg">
        <q-form @submit.prevent="handleLogin" class="q-gutter-md">
          <q-select
            v-model="selectedPasswordAuthMethod"
            :options="passwordAuthOptions"
            label="Authentication Method"
            outlined
            filled
            dark
            emit-value
            map-options
          />

          <q-input
            v-model="credentials.username"
            label="Username"
            outlined
            filled
            autofocus
            dark
            :rules="[val => !!val || 'Username is required']"
            @keyup.enter="handleLogin"
          />

          <q-input
            v-model="credentials.password"
            label="Password"
            type="password"
            outlined
            filled
            dark
            :rules="[val => !!val || 'Password is required']"
            @keyup.enter="handleLogin"
          />

          <q-btn
            type="submit"
            color="primary"
            :label="submitLabel"
            class="full-width"
            :loading="isLoading"
            :disable="isLoading"
          />
        </q-form>

        <!-- SSO Login Button (conditionally shown) -->
        <div v-if="ssoEnabled" class="q-mt-md">
          <q-separator dark class="q-mb-md" />
          <q-btn
            color="secondary"
            label="Log in via SSO"
            icon="cloud"
            class="full-width"
            @click="handleSSOLogin"
            unelevated
          />
        </div>

        <q-linear-progress
          v-if="isLoading"
          indeterminate
          color="primary"
          class="q-mt-md"
        />
      </q-card-section>

      <q-card-section v-if="errorMessage" class="q-pt-none">
        <q-banner class="bg-negative text-white">
          {{ errorMessage }}
        </q-banner>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import axios from 'axios';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const credentials = ref({
  username: '',
  password: ''
});

const isLoading = ref(false);
const errorMessage = ref('');
const ssoEnabled = ref(false);
const ldapEnabled = ref(false);
const ldapDisplayName = ref('Central Authentication');
const selectedPasswordAuthMethod = ref('local');
const passwordAuthOptions = ref([
  { label: 'Local Authentication', value: 'local' },
  { label: 'Central Authentication', value: 'ldap', disable: true }
]);

const submitLabel = computed(() => (
  selectedPasswordAuthMethod.value === 'ldap' ? 'Log in with Central Authentication' : 'Log in with Local Authentication'
));

// Check if SSO is enabled
const checkSSOConfig = async () => {
  try {
    const api = axios.create({
      baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'
    });
    const response = await api.get('/auth/config/');
    ssoEnabled.value = response.data.sso_enabled;
    ldapEnabled.value = response.data.ldap_enabled;
    ldapDisplayName.value = response.data.ldap_display_name || 'Central Authentication';
    passwordAuthOptions.value = [
      { label: 'Local Authentication', value: 'local' },
      { label: ldapDisplayName.value, value: 'ldap', disable: !ldapEnabled.value }
    ];
    selectedPasswordAuthMethod.value = response.data.default_password_auth_method || 'local';
  } catch (error) {
    console.error('Error fetching auth config:', error);
  }
};

const handleLogin = async () => {
  errorMessage.value = '';
  isLoading.value = true;

  try {
    const api = axios.create({
      baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'
    });

    const endpoint = selectedPasswordAuthMethod.value === 'ldap' ? '/auth/ldap/login/' : '/auth/login/';
    const response = await api.post(endpoint, {
      username: credentials.value.username,
      password: credentials.value.password
    });

    const { token, user } = response.data;

    authStore.setToken(token);
    authStore.setUser(user);

    // Check if user needs to change password
    if (user.force_password_reset) {
      router.push('/change-password');
    } else {
      // Redirect to dashboard
      router.push('/devices');
    }
  } catch (error) {
    if (error.response?.status === 401) {
      errorMessage.value = 'Invalid username or password';
    } else if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail;
    } else {
      errorMessage.value = 'Login failed. Please try again.';
    }
  } finally {
    isLoading.value = false;
  }
};

const handleSSOLogin = () => {
  // Redirect to SAML login endpoint
  const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';
  window.location.href = `${baseURL}/auth/saml/login/`;
};

// Handle SSO callback with token in URL
onMounted(async () => {
  await checkSSOConfig();
  
  // Check if token is in URL query (SSO callback)
  const token = route.query.token;
  if (token) {
    try {
      authStore.setToken(token);
      
      // For SSO, we'll redirect and let the app fetch user info
      router.push('/devices');
    } catch {
      errorMessage.value = 'SSO login failed. Please try again.';
    }
  }
});
</script>

<style scoped>
.login-page {
  background: #1a1a1a;
  min-height: 100vh;
}
</style>
