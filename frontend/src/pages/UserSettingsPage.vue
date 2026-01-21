<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->

<template>
  <q-page padding>
    <div class="q-mb-md">
      <div class="text-h4">User Settings</div>
    </div>

    <q-card>
      <q-card-section>
        <div class="text-h6 q-mb-md">Account Information</div>

        <div class="row q-col-gutter-md q-mb-md">
          <div class="col-12 col-md-6">
            <q-input
              v-model="user.username"
              label="Username"
              outlined
              dense
              readonly
            >
              <template v-slot:prepend>
                <q-icon name="person" />
              </template>
            </q-input>
          </div>

          <div class="col-12 col-md-6">
            <q-input
              v-model="user.email"
              label="Email"
              outlined
              dense
              readonly
            >
              <template v-slot:prepend>
                <q-icon name="email" />
              </template>
            </q-input>
          </div>
        </div>

        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-input
              :model-value="getRoleLabel(user.role)"
              label="Role"
              outlined
              dense
              readonly
            >
              <template v-slot:prepend>
                <q-icon name="badge" />
              </template>
            </q-input>
          </div>

          <div class="col-12 col-md-6">
            <q-input
              :model-value="user.is_sso ? 'SSO' : 'Local'"
              label="Authentication Type"
              outlined
              dense
              readonly
            >
              <template v-slot:prepend>
                <q-icon name="security" />
              </template>
            </q-input>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Password Change Section (local users only) -->
    <q-card v-if="!user.is_sso" class="q-mt-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">Change Password</div>

        <q-card-section v-if="errorMessage" class="bg-negative text-white q-mb-md">
          <q-icon name="error" class="q-mr-md" />
          {{ errorMessage }}
        </q-card-section>

        <q-card-section v-if="successMessage" class="bg-positive text-white q-mb-md">
          <q-icon name="check_circle" class="q-mr-md" />
          {{ successMessage }}
        </q-card-section>

        <q-form @submit="changePassword" class="q-gutter-md">
          <q-input
            v-model="passwordForm.oldPassword"
            type="password"
            label="Current Password *"
            outlined
            dense
            :rules="[val => !!val || 'Current password is required']"
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
          </q-input>

          <q-input
            v-model="passwordForm.newPassword"
            type="password"
            label="New Password *"
            outlined
            dense
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
            v-model="passwordForm.confirmPassword"
            type="password"
            label="Confirm New Password *"
            outlined
            dense
            :rules="[
              val => !!val || 'Please confirm your password',
              val => val === passwordForm.newPassword || 'Passwords do not match'
            ]"
          >
            <template v-slot:prepend>
              <q-icon name="lock_reset" />
            </template>
          </q-input>

          <div>
            <q-btn
              type="submit"
              color="primary"
              label="Change Password"
              :loading="loading"
              unelevated
            />
          </div>
        </q-form>
      </q-card-section>

      <q-card-section class="text-caption text-grey-7">
        <q-icon name="info" class="q-mr-xs" />
        Password must be at least 8 characters long.
      </q-card-section>
    </q-card>

    <!-- SSO User Notice -->
    <q-card v-else class="q-mt-md">
      <q-card-section class="bg-info text-white">
        <div class="text-h6 q-mb-sm">
          <q-icon name="info" class="q-mr-sm" />
          SSO Authentication
        </div>
        <div>
          Your account uses Single Sign-On (SSO) authentication. Password management is handled by your identity provider.
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import api from '../api';

const authStore = useAuthStore();
const user = computed(() => authStore.user || {});

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const errorMessage = ref('');
const successMessage = ref('');
const loading = ref(false);

const getRoleLabel = (role) => {
  return role === 'admin' ? 'Administrator' : 'Read Only';
};

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
  successMessage.value = '';
  loading.value = true;

  try {
    await api.post('/auth/change-password/', {
      old_password: passwordForm.value.oldPassword,
      new_password: passwordForm.value.newPassword,
      confirm_password: passwordForm.value.confirmPassword
    });

    successMessage.value = 'Password changed successfully!';
    
    // Clear form
    passwordForm.value = {
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    };

    // Update user object to clear force_password_reset flag if set
    if (authStore.user && authStore.user.force_password_reset) {
      authStore.user.force_password_reset = false;
      authStore.setUser(authStore.user);
    }
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    loading.value = false;
  }
};
</script>
