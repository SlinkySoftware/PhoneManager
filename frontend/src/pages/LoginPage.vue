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
            label="Login"
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
import { ref, onMounted } from 'vue';
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

// Check if SSO is enabled
const checkSSOConfig = async () => {
  try {
    const api = axios.create({
      baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'
    });
    const response = await api.get('/auth/config/');
    ssoEnabled.value = response.data.sso_enabled;
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

    const response = await api.post('/auth/login/', {
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
      const api = axios.create({
        baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000/api',
        headers: {
          Authorization: `Token ${token}`
        }
      });
      
      // Fetch user info with the token
      // This assumes the backend stores user info in the session or we need to fetch it
      authStore.setToken(token);
      
      // For SSO, we'll redirect and let the app fetch user info
      router.push('/devices');
    } catch (error) {
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
