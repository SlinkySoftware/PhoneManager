<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <q-layout view="hHh lpR fFf">
    <q-header v-if="!isLoginPage && !isChangePasswordPage" elevated>
      <q-toolbar>
        <q-toolbar-title>Phone Provisioning Manager</q-toolbar-title>
        <q-tabs shrink stretch class="text-white">
          <q-route-tab to="/devices" label="Devices" icon="devices" />
          <q-route-tab to="/lines" label="Lines" icon="call" />
          <q-route-tab to="/device-types" label="Device Types" icon="schema" />
          <q-route-tab to="/sip-servers" label="SIP Servers" icon="router" />
          <q-route-tab to="/dial-plans" label="Dial Plans" icon="transform" />
          <q-route-tab to="/sites" label="Sites" icon="business" />
          <q-route-tab v-if="isAdmin" to="/users" label="Users" icon="people" />
        </q-tabs>
        <q-space />
        <div class="row items-center q-gutter-sm q-pr-md">
          <q-badge v-if="isReadOnly" color="orange" label="Read Only" />
          <div class="text-subtitle2">{{ currentUsername }}</div>
          <q-btn flat round dense icon="settings" color="white">
            <q-menu>
              <q-list style="min-width: 200px">
                <q-item clickable v-close-popup @click="goToSettings">
                  <q-item-section avatar>
                    <q-icon name="person" />
                  </q-item-section>
                  <q-item-section>User Settings</q-item-section>
                </q-item>
                <q-separator />
                <q-item clickable v-close-popup @click="logout">
                  <q-item-section avatar>
                    <q-icon name="logout" />
                  </q-item-section>
                  <q-item-section>Logout</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </q-btn>
        </div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const isLoginPage = computed(() => route.path === '/login');
const isChangePasswordPage = computed(() => route.path === '/change-password');
const isAdmin = computed(() => authStore.user?.role === 'admin');
const isReadOnly = computed(() => authStore.user?.role === 'readonly');
const currentUsername = computed(() => authStore.currentUser?.username || '');

const goToSettings = () => {
  router.push('/settings');
};

const logout = () => {
  authStore.logout();
  router.push('/login');
};
</script>
