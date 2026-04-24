<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->

<template>
  <q-page padding>
    <div class="q-mb-md row items-center">
      <div class="text-h4">Users</div>
      <q-space />
      <q-btn
        color="primary"
        icon="add"
        label="Add User"
        @click="openCreateDialog"
        unelevated
      />
      <q-btn
        class="q-ml-sm"
        icon="refresh"
        flat
        round
        @click="loadUsers"
        dense
      >
        <q-tooltip>Refresh</q-tooltip>
      </q-btn>
    </div>

    <q-table
      :rows="users"
      :columns="columns"
      row-key="id"
      :loading="loading"
      flat
      bordered
      :pagination="{ rowsPerPage: 20, rowsPerPageOptions: [20, 50, 100, 0] }"
    >
      <template v-slot:body-cell-username="props">
        <q-td :props="props">
          {{ props.row.username }}
          <q-chip v-if="props.row.username === authStore.currentUser?.username" dense size="sm" color="info" text-color="white" class="q-ml-sm">
            You
          </q-chip>
        </q-td>
      </template>

      <template v-slot:body-cell-role="props">
        <q-td :props="props">
          <q-badge
            :color="props.row.role === 'admin' ? 'primary' : 'orange'"
            :label="props.row.role === 'admin' ? 'Administrator' : 'Read Only'"
          />
        </q-td>
      </template>

      <template v-slot:body-cell-auth_source="props">
        <q-td :props="props">
          <q-badge
            :color="getAuthBadgeColor(props.row.auth_source)"
            :label="props.row.auth_type_label || getAuthTypeLabel(props.row.auth_source)"
          />
        </q-td>
      </template>

      <template v-slot:body-cell-force_password_reset="props">
        <q-td :props="props">
          <q-icon
            v-if="props.row.force_password_reset"
            name="warning"
            color="orange"
            size="sm"
          >
            <q-tooltip>Password reset required</q-tooltip>
          </q-icon>
        </q-td>
      </template>

      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
          <!-- Hide action buttons for current user -->
          <template v-if="props.row.username !== authStore.currentUser?.username">
            <q-btn
              v-if="props.row.auth_source !== 'ldap'"
              dense
              flat
              icon="edit"
              color="primary"
              @click="openEditDialog(props.row)"
            >
              <q-tooltip>Edit User</q-tooltip>
            </q-btn>
            <q-btn
              v-if="props.row.auth_source === 'local'"
              dense
              flat
              icon="lock_reset"
              color="orange"
              @click="openResetPasswordDialog(props.row)"
            >
              <q-tooltip>Reset Password</q-tooltip>
            </q-btn>
            <q-btn
              dense
              flat
              icon="delete"
              color="negative"
              @click="openDeleteDialog(props.row)"
            >
              <q-tooltip>Delete User</q-tooltip>
            </q-btn>
          </template>
        </q-td>
      </template>
    </q-table>

    <!-- Create User Dialog -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="text-h6">Add User</q-card-section>

        <q-card-section v-if="errorMessage" class="bg-negative text-white q-mb-md">
          <q-icon name="error" class="q-mr-md" />
          {{ errorMessage }}
        </q-card-section>

        <q-card-section v-if="temporaryPassword" class="bg-green-10 text-white">
          <div class="text-h6 q-mb-md">Temporary Password Created</div>
          <div class="q-mb-sm">Username: <strong>{{ newUser.username }}</strong></div>
          <div class="q-mb-md">
            Temporary Password: <strong class="text-h6">{{ temporaryPassword }}</strong>
          </div>
          <div class="text-caption">
            <q-icon name="info" class="q-mr-xs" />
            Please save this password securely. The user will be required to change it on first login.
          </div>
        </q-card-section>

        <q-card-section v-if="!temporaryPassword" class="q-pt-none">
          <q-input
            v-model="newUser.username"
            label="Username *"
            outlined
            dense
            class="q-mb-md"
            :rules="[val => !!val || 'Username is required']"
          />

          <q-input
            v-model="newUser.first_name"
            label="First Name"
            outlined
            dense
            class="q-mb-md"
          />

          <q-input
            v-model="newUser.last_name"
            label="Last Name"
            outlined
            dense
            class="q-mb-md"
          />

          <q-input
            v-model="newUser.email"
            label="Email Address"
            outlined
            dense
            class="q-mb-md"
          />

          <q-select
            v-model="newUser.role"
            :options="roleOptions"
            label="Role *"
            outlined
            dense
            emit-value
            map-options
            :rules="[val => !!val || 'Role is required']"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            v-if="temporaryPassword"
            label="Close"
            color="primary"
            @click="closeCreateDialog"
          />
          <template v-else>
            <q-btn flat label="Cancel" color="primary" v-close-popup />
            <q-btn
              unelevated
              label="Create User"
              color="primary"
              @click="createUser"
              :loading="saving"
            />
          </template>
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit User Dialog -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="text-h6">Edit User</q-card-section>

        <q-card-section v-if="editError" class="bg-negative text-white q-mb-md">
          <q-icon name="error" class="q-mr-md" />
          {{ editError }}
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input
            v-model="editingUser.username"
            label="Username"
            outlined
            dense
            readonly
            class="q-mb-md"
            bg-color="grey-8"
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
          </q-input>

          <q-input
            v-model="editingUser.first_name"
            label="First Name"
            outlined
            dense
            class="q-mb-md"
          />

          <q-input
            v-model="editingUser.last_name"
            label="Last Name"
            outlined
            dense
            class="q-mb-md"
          />

          <q-input
            v-model="editingUser.email"
            label="Email Address"
            outlined
            dense
            class="q-mb-md"
          />

          <q-select
            v-model="editingUser.role"
            :options="roleOptions"
            label="Role *"
            outlined
            dense
            emit-value
            map-options
            :disable="editingUser.auth_source !== 'local'"
            class="q-mb-md"
            :rules="[val => !!val || 'Role is required']"
          >
            <template v-if="editingUser.auth_source !== 'local'" v-slot:append>
              <q-icon name="lock" color="grey">
                <q-tooltip>Role managed by external authentication</q-tooltip>
              </q-icon>
            </template>
          </q-select>

          <q-checkbox
            v-if="editingUser.auth_source === 'local'"
            v-model="editingUser.force_password_reset"
            label="Force Password Reset on Next Login"
            class="q-mb-md"
          />

          <q-banner v-if="editingUser.auth_source !== 'local'" dense class="bg-info text-white q-mb-md">
            <q-icon name="info" class="q-mr-sm" />
            {{ getEditBannerMessage(editingUser) }}
          </q-banner>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="closeEditDialog" />
          <q-btn
            unelevated
            label="Save Changes"
            color="primary"
            @click="saveUserChanges"
            :loading="saving"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reset Password Dialog -->
    <q-dialog v-model="showResetPasswordDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="text-h6">Reset Password</q-card-section>

        <q-card-section v-if="resetError" class="bg-negative text-white q-mb-md">
          <q-icon name="error" class="q-mr-md" />
          {{ resetError }}
        </q-card-section>

        <q-card-section v-if="resetPassword" class="bg-green-10 text-white">
          <div class="text-h6 q-mb-md">New Temporary Password</div>
          <div class="q-mb-sm">Username: <strong>{{ userToReset?.username }}</strong></div>
          <div class="q-mb-md">
            New Password: <strong class="text-h6">{{ resetPassword }}</strong>
          </div>
          <div class="text-caption">
            <q-icon name="info" class="q-mr-xs" />
            Please save this password securely. The user will be required to change it on next login.
          </div>
        </q-card-section>

        <q-card-section v-if="!resetPassword">
          <p>Are you sure you want to reset the password for: <strong>{{ userToReset?.username }}</strong>?</p>
          <p class="text-caption text-grey-7">A new temporary password will be generated.</p>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            v-if="resetPassword"
            label="Close"
            color="primary"
            @click="closeResetPasswordDialog"
          />
          <template v-else>
            <q-btn flat label="Cancel" color="primary" v-close-popup />
            <q-btn
              unelevated
              label="Reset Password"
              color="orange"
              @click="resetUserPassword"
              :loading="resetting"
            />
          </template>
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Delete Confirmation Dialog -->
    <q-dialog v-model="showDeleteDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">Confirm Deletion</q-card-section>

        <q-card-section v-if="deleteError" class="bg-negative text-white q-mb-md">
          <q-icon name="error" class="q-mr-md" />
          {{ deleteError }}
        </q-card-section>

        <q-card-section>
          <p>Are you sure you want to delete user: <strong>{{ userToDelete?.username }}</strong>?</p>
          <p v-if="userToDelete && userToDelete.auth_source !== 'local'" class="text-caption text-info">
            <q-icon name="info" class="q-mr-xs" />
            This is a {{ getAuthTypeLabel(userToDelete.auth_source) }} user. The account will be deleted. If the user attempts to log in again, the account may be recreated if the external identity provider allows it.
          </p>
          <p v-else class="text-caption text-grey-7">This action cannot be undone.</p>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn
            unelevated
            label="Delete"
            color="negative"
            @click="deleteUser"
            :loading="deleting"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api';
import { useAuthStore } from '../stores/auth';

// Auth store to check current user
const authStore = useAuthStore();

// State
const users = ref([]);
const loading = ref(false);
const showCreateDialog = ref(false);
const showEditDialog = ref(false);
const showResetPasswordDialog = ref(false);
const showDeleteDialog = ref(false);
const errorMessage = ref('');
const editError = ref('');
const resetError = ref('');
const deleteError = ref('');
const saving = ref(false);
const resetting = ref(false);
const deleting = ref(false);
const temporaryPassword = ref('');
const resetPassword = ref('');
const userToReset = ref(null);
const userToDelete = ref(null);
const editingUser = ref(null);

const newUser = ref({
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  role: 'readonly'
});

const roleOptions = [
  { label: 'Administrator', value: 'admin' },
  { label: 'Read Only', value: 'readonly' }
];

const columns = [
  { name: 'username', label: 'Username', field: 'username', align: 'left', sortable: true },
  { name: 'full_name', label: 'Full Name', field: 'full_name', align: 'left', sortable: true },
  { name: 'email', label: 'Email', field: 'email', align: 'left', sortable: true },
  { name: 'role', label: 'Role', field: 'role', align: 'left', sortable: true },
  { name: 'auth_source', label: 'Type', field: 'auth_source', align: 'center', sortable: true },
  { name: 'force_password_reset', label: 'Status', field: 'force_password_reset', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' }
];

const getAuthTypeLabel = (authSource) => {
  if (authSource === 'ldap') {
    return 'LDAP';
  }
  if (authSource === 'saml') {
    return 'SAML';
  }
  return 'Local';
};

const getAuthBadgeColor = (authSource) => {
  if (authSource === 'ldap') {
    return 'deep-orange';
  }
  if (authSource === 'saml') {
    return 'info';
  }
  return 'orange';
};

const getEditBannerMessage = (user) => {
  if (user.auth_source === 'ldap') {
    return 'LDAP users are managed by the central directory and can only be disabled locally.';
  }
  return 'SAML users have their role managed by the identity provider.';
};

// Helper function to extract error messages
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

// Load users
const loadUsers = async () => {
  loading.value = true;
  try {
    const response = await api.get('/users/');
    users.value = response.data;
  } catch (error) {
    console.error('Error loading users:', error);
  } finally {
    loading.value = false;
  }
};

// Create user
const openCreateDialog = () => {
  newUser.value = { username: '', first_name: '', last_name: '', email: '', role: 'readonly' };
  errorMessage.value = '';
  temporaryPassword.value = '';
  showCreateDialog.value = true;
};

const createUser = async () => {
  errorMessage.value = '';
  saving.value = true;
  try {
    const response = await api.post('/users/', newUser.value);
    temporaryPassword.value = response.data.temporary_password;
    await loadUsers();
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    saving.value = false;
  }
};

const closeCreateDialog = () => {
  showCreateDialog.value = false;
  newUser.value = { username: '', first_name: '', last_name: '', email: '', role: 'readonly' };
  errorMessage.value = '';
  temporaryPassword.value = '';
};

// Edit user
const openEditDialog = (user) => {
  editingUser.value = {
    id: user.id,
    username: user.username,
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    email: user.email || '',
    role: user.role,
    auth_source: user.auth_source,
    auth_type_label: user.auth_type_label,
    force_password_reset: user.force_password_reset
  };
  editError.value = '';
  showEditDialog.value = true;
};

const saveUserChanges = async () => {
  editError.value = '';
  saving.value = true;
  try {
    await api.patch(`/users/${editingUser.value.id}/`, {
      first_name: editingUser.value.first_name,
      last_name: editingUser.value.last_name,
      email: editingUser.value.email,
      role: editingUser.value.role,
      force_password_reset: editingUser.value.force_password_reset
    });
    showEditDialog.value = false;
    await loadUsers();
  } catch (error) {
    editError.value = extractErrorMessage(error);
  } finally {
    saving.value = false;
  }
};

const closeEditDialog = () => {
  showEditDialog.value = false;
  editingUser.value = null;
  editError.value = '';
};

// Reset password
const openResetPasswordDialog = (user) => {
  userToReset.value = user;
  resetPassword.value = '';
  resetError.value = '';
  showResetPasswordDialog.value = true;
};

const resetUserPassword = async () => {
  resetError.value = '';
  resetting.value = true;
  try {
    const response = await api.post(`/users/${userToReset.value.id}/reset_password/`);
    resetPassword.value = response.data.temporary_password;
    await loadUsers();
  } catch (error) {
    resetError.value = extractErrorMessage(error);
  } finally {
    resetting.value = false;
  }
};

const closeResetPasswordDialog = () => {
  showResetPasswordDialog.value = false;
  userToReset.value = null;
  resetPassword.value = '';
  resetError.value = '';
};

// Delete user
const openDeleteDialog = (user) => {
  userToDelete.value = user;
  deleteError.value = '';
  showDeleteDialog.value = true;
};

const deleteUser = async () => {
  deleteError.value = '';
  deleting.value = true;
  try {
    await api.delete(`/users/${userToDelete.value.id}/`);
    showDeleteDialog.value = false;
    await loadUsers();
  } catch (error) {
    deleteError.value = extractErrorMessage(error);
  } finally {
    deleting.value = false;
  }
};

// Load users on mount
onMounted(async () => {
  await loadUsers();
});
</script>
