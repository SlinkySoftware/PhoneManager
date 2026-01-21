<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->

<template>
  <q-page class="flex flex-center bg-dark">
    <q-card class="bg-grey-9" style="width: 100%; max-width: 500px;">
      <q-card-section class="bg-primary text-white">
        <div class="text-h5">Change Password</div>
        <div class="text-subtitle2">You must change your password before continuing</div>
      </q-card-section>

      <q-card-section v-if="errorMessage" class="bg-negative text-white">
        <q-icon name="error" class="q-mr-md" />
        {{ errorMessage }}
      </q-card-section>

      <q-card-section>
        <q-form @submit="changePassword" class="q-gutter-md">
          <q-input
            v-model="form.oldPassword"
            type="password"
            label="Current Password *"
            outlined
            :rules="[val => !!val || 'Current password is required']"
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
          </q-input>

          <q-input
            v-model="form.newPassword"
            type="password"
            label="New Password *"
            outlined
            :rules="[
              val => !!val || 'New password is required',
              val => val.length >= 8 || 'Password must be at least 8 characters'
            ]"
          >
            <template v-slot:prepend>
              <q-icon name="lock_reset" />
            </template>
          </q-input>

          <q-input
            v-model="form.confirmPassword"
            type="password"
            label="Confirm New Password *"
            outlined
            :rules="[
              val => !!val || 'Please confirm your password',
              val => val === form.newPassword || 'Passwords do not match'
            ]"
          >
            <template v-slot:prepend>
              <q-icon name="lock_reset" />
            </template>
          </q-input>

          <div class="q-mt-md">
            <q-btn
              type="submit"
              color="primary"
              label="Change Password"
              :loading="loading"
              unelevated
              class="full-width"
            />
          </div>
        </q-form>
      </q-card-section>

      <q-card-section class="text-caption text-grey-7">
        <q-icon name="info" class="q-mr-xs" />
        Password must be at least 8 characters long.
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import api from '../api';

const router = useRouter();
const authStore = useAuthStore();

const form = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const errorMessage = ref('');
const loading = ref(false);

const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.response?.statusText) {
    return `Operation failed: ${error.response.statusText}`;
  }
  if (error.request) {
    return 'Network error: Unable to reach the server. Please check your connection.';
  }
  return 'An unexpected error occurred. Please try again.';
};

const changePassword = async () => {
  errorMessage.value = '';
  loading.value = true;

  try {
    await api.post('/auth/change-password/', {
      old_password: form.value.oldPassword,
      new_password: form.value.newPassword,
      confirm_password: form.value.confirmPassword
    });

    // Update user object to clear force_password_reset flag
    if (authStore.user) {
      authStore.user.force_password_reset = false;
      authStore.setUser(authStore.user);
    }

    // Redirect to dashboard
    router.push('/');
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    loading.value = false;
  }
};
</script>
