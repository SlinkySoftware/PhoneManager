<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated>
      <q-toolbar>
        <q-toolbar-title>Phone Provisioning Manager</q-toolbar-title>
        <q-tabs shrink stretch class="text-white">
          <q-route-tab to="/device-types" label="Device Types" icon="schema" />
          <q-route-tab to="/devices" label="Devices" icon="devices" />
          <q-route-tab to="/sip-servers" label="SIP Servers" icon="router" />
          <q-route-tab to="/sites" label="Sites" icon="business" />
          <q-route-tab to="/lines" label="Lines" icon="call" />
        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
</script>
