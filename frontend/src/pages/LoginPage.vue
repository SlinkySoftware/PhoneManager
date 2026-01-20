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

      <q-card-section class="text-center text-caption text-grey-7">
        <p class="q-my-sm">Demo credentials:</p>
        <p class="q-my-xs">Username: admin</p>
        <p class="q-my-xs">Password: (set during setup)</p>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import axios from 'axios';

const router = useRouter();
const authStore = useAuthStore();

const credentials = ref({
  username: '',
  password: ''
});

const isLoading = ref(false);
const errorMessage = ref('');

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

    // Redirect to dashboard
    router.push('/device-types');
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
</script>

<style scoped>
.login-page {
  background: #1a1a1a;
  min-height: 100vh;
}
</style>
