<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">Device Types</div>
      <q-badge v-if="isReadOnly" color="orange" label="Read Only Mode" class="q-ml-md" />
    </div>
    <q-card flat bordered class="bg-dark">
      <q-card-section>
        <q-btn color="primary" flat icon="refresh" label="Refresh" @click="loadTypes" :loading="loading" />
      </q-card-section>
      <q-separator />
      <q-card-section>
        <q-linear-progress v-if="loading" indeterminate color="primary" />
        <q-list v-else bordered separator>
          <q-item v-for="dt in deviceTypes" :key="dt.typeId">
            <q-item-section>
              <q-item-label class="text-subtitle1">{{ dt.manufacturer }} {{ dt.model }}</q-item-label>
              <q-item-label caption>TypeID: {{ dt.typeId }} · Lines: {{ dt.numberOfLines }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row q-gutter-xs">
                <q-btn 
                  dense 
                  flat 
                  icon="settings" 
                  color="secondary" 
                  @click="openOptions(dt)"
                >
                  <q-tooltip>{{ isReadOnly ? 'View Options' : 'Common Options' }}</q-tooltip>
                </q-btn>
                <q-btn 
                  dense 
                  flat 
                  icon="tune" 
                  color="orange" 
                  @click="openDeviceDefaults(dt)"
                >
                  <q-tooltip>{{ isReadOnly ? 'View Defaults' : 'Edit Device Defaults' }}</q-tooltip>
                </q-btn>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <!-- Common Options Dialog -->
    <q-dialog v-model="showOptionsDialog" class="q-gutter-md">
      <q-card style="min-width: 600px; max-width: 800px" class="bg-grey-9">
        <!-- Header -->
        <q-card-section class="bg-green-10 text-white">
          <div class="text-h6">{{ selectedType?.manufacturer }} {{ selectedType?.model }} - {{ isReadOnly ? 'View' : 'Common' }} Options</div>
          <div class="text-caption text-green-2">TypeID: {{ selectedType?.typeId }}</div>
        </q-card-section>

        <!-- Error Banner -->
        <q-card-section v-if="optionsError" class="bg-negative text-white">
          <q-icon name="error" class="q-mr-md" />
          {{ optionsError }}
        </q-card-section>

        <!-- Options Sections -->
        <q-card-section class="q-gutter-md scroll" style="max-height: 60vh">
          <q-card
            v-for="section in sortedSections"
            :key="section.friendlyName"
            flat
            class="bg-grey-8"
            style="border: 2px solid #1db885;"
          >
            <q-card-section class="bg-green-9 text-white">
              <div class="text-subtitle1">{{ section.friendlyName }}</div>
            </q-card-section>

            <q-card-section class="q-gutter-md">
              <template v-for="option in sortedOptions(section.options)" :key="option.optionId">
                <!-- Text Input -->
                <q-input
                  v-if="option.type === 'text'"
                  v-model="optionValues[option.optionId]"
                  :label="option.friendlyName"
                  outlined
                  dense
                  dark
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                />

                <!-- Number Input -->
                <q-input
                  v-else-if="option.type === 'number'"
                  v-model.number="optionValues[option.optionId]"
                  type="number"
                  :label="option.friendlyName"
                  outlined
                  dense
                  dark
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => val !== null && val !== '' || `${option.friendlyName} is required`] : []"
                />

                <!-- Select/Dropdown -->
                <q-select
                  v-else-if="option.type === 'select' && (option.options || option.choices)"
                  v-model="optionValues[option.optionId]"
                  :options="option.options || option.choices"
                  :label="option.friendlyName"
                  outlined
                  dense
                  dark
                  emit-value
                  map-options
                  color="green"
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => val !== null && val !== '' || `${option.friendlyName} is required`] : []"
                />

                <!-- Boolean Checkbox -->
                <q-checkbox
                  v-else-if="option.type === 'boolean' || option.type === 'checkbox'"
                  v-model="optionValues[option.optionId]"
                  :label="option.friendlyName"
                  dense
                  color="green"
                  :disable="isReadOnly"
                />

                <!-- Textarea -->
                <q-input
                  v-else-if="option.type === 'textarea'"
                  v-model="optionValues[option.optionId]"
                  type="textarea"
                  :label="option.friendlyName"
                  outlined
                  rows="3"
                  dense
                  dark
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                />

                <!-- Multi-Select (Checkboxes) -->
                <div v-else-if="option.type === 'multiselect'" class="q-mt-md">
                  <q-card flat style="border: 2px solid #1db885;" class="bg-grey-7">
                    <q-card-section class="bg-green-9 text-white q-py-sm">
                      <div class="text-subtitle2">{{ option.friendlyName }}</div>
                    </q-card-section>
                    <q-card-section class="q-gutter-sm">
                      <div class="row q-col-gutter-md">
                        <template v-for="choice in (option.choices || option.options || [])" :key="choice">
                          <div class="col-12 col-sm-6 col-md-4">
                            <q-checkbox
                              :model-value="(Array.isArray(optionValues[option.optionId]) ? optionValues[option.optionId] : []).includes(choice)"
                              @update:model-value="toggleMultiselectChoice(option.optionId, choice)"
                              :label="choice"
                              color="green"
                              :disable="isReadOnly"
                              dense
                              class="text-white"
                            />
                          </div>
                        </template>
                      </div>
                      <div v-if="(!option.choices && !option.options) || (option.choices || option.options || []).length === 0" class="text-caption text-grey-5">
                        No options available
                      </div>
                    </q-card-section>
                  </q-card>
                </div>

                <!-- Ordered Multi-Select -->
                <div v-else-if="option.type === 'orderedmultiselect'" class="q-gutter-md">
                  <div class="text-subtitle2 text-white">{{ option.friendlyName }}</div>
                  <div class="row q-gutter-md">
                    <!-- Available Options -->
                    <div class="col">
                      <div class="text-caption text-green-3">Available</div>
                      <q-list bordered separator style="border: 1px solid #1db885;" class="bg-grey-8 q-mt-xs">
                        <q-item
                          v-for="avail in availableOptions(option)"
                          :key="avail"
                          :clickable="!isReadOnly"
                          @click="!isReadOnly && moveToSelected(option.optionId, avail)"
                        >
                          <q-item-section avatar>
                            <q-icon name="chevron_right" :color="isReadOnly ? 'grey' : 'green'" />
                          </q-item-section>
                          <q-item-section class="text-white">{{ avail }}</q-item-section>
                        </q-item>
                      </q-list>
                    </div>

                    <!-- Selected Options -->
                    <div class="col">
                      <div class="text-caption text-green-3">Selected (Ordered)</div>
                      <q-list bordered separator style="border: 1px solid #1db885;" class="bg-grey-8 q-mt-xs">
                        <q-item
                          v-for="(selected, idx) in (optionValues[option.optionId] || [])"
                          :key="selected"
                          class="q-pa-xs"
                        >
                          <q-item-section avatar>
                            <div class="column q-gutter-xs">
                              <q-btn
                                v-if="idx > 0 && !isReadOnly"
                                flat
                                dense
                                round
                                size="sm"
                                icon="arrow_upward"
                                color="green"
                                @click="moveUpSelected(option.optionId, idx)"
                              />
                              <q-btn
                                v-if="idx < (optionValues[option.optionId] || []).length - 1 && !isReadOnly"
                                flat
                                dense
                                round
                                size="sm"
                                icon="arrow_downward"
                                color="green"
                                @click="moveDownSelected(option.optionId, idx)"
                              />
                            </div>
                          </q-item-section>
                          <q-item-section class="text-white">{{ selected }}</q-item-section>
                          <q-item-section avatar>
                            <q-btn
                              v-if="!isReadOnly"
                              flat
                              dense
                              round
                              size="sm"
                              icon="chevron_left"
                              color="green"
                              @click="moveToAvailable(option.optionId, selected)"
                            />
                          </q-item-section>
                        </q-item>
                      </q-list>
                      <div v-if="!optionValues[option.optionId] || optionValues[option.optionId].length === 0" class="text-caption text-grey-6 q-mt-md">
                        Click items on the left to select
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Unsupported type fallback -->
                <div v-else class="text-warning">
                  <q-icon name="warning" />
                  Unsupported option type: {{ option.type }}
                </div>
              </template>
            </q-card-section>
          </q-card>

          <!-- Empty state -->
          <q-banner v-if="!selectedType?.commonOptions?.sections || selectedType.commonOptions.sections.length === 0" class="bg-info text-white">
            <q-icon name="info" />
            This device type has no configurable common options.
          </q-banner>
        </q-card-section>

        <!-- Actions -->
        <q-card-actions class="q-pa-md">
          <q-btn v-if="!isReadOnly" flat label="Reset to Defaults" color="warning" @click="confirmReset" />
          <q-space />
          <q-btn flat :label="isReadOnly ? 'Close' : 'Cancel'" color="primary" v-close-popup />
          <q-btn
            v-if="!isReadOnly"
            unelevated
            label="Save"
            color="positive"
            @click="saveOptions"
            :loading="savingOptions"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Device Defaults Dialog -->
    <q-dialog v-model="showDefaultsDialog" class="q-gutter-md">
      <q-card style="min-width: 700px; max-width: 1000px" class="bg-grey-9">
        <!-- Header -->
        <q-card-section class="bg-teal-8 text-white">
          <div class="text-h6">{{ selectedType?.manufacturer }} {{ selectedType?.model }} - {{ isReadOnly ? 'View Device Defaults' : 'Device Defaults' }}</div>
          <div class="text-caption text-teal-2">TypeID: {{ selectedType?.typeId }}</div>
        </q-card-section>

        <!-- Error Banner -->
        <q-card-section v-if="defaultsError" class="bg-negative text-white">
          <q-icon name="error" class="q-mr-md" />
          {{ defaultsError }}
        </q-card-section>

        <!-- Options Sections -->
        <q-card-section class="q-gutter-md scroll" style="max-height: 60vh">
          <q-card
            v-for="section in sortedDefaultSections"
            :key="section.friendlyName"
            flat
            class="bg-grey-8"
            style="border: 2px solid #1db885;"
          >
            <q-card-section class="bg-teal-8 text-white">
              <div class="text-subtitle1">{{ section.friendlyName }}</div>
            </q-card-section>

            <q-card-section class="q-gutter-md">
              <template v-for="option in sortedDefaultOptions(section.options)" :key="option.optionId">
                <!-- Text Input -->
                <q-input
                  v-if="option.type === 'text'"
                  v-model="defaultsValues[option.optionId]"
                  :label="option.friendlyName"
                  outlined
                  dense
                  dark
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                />

                <!-- Number Input -->
                <q-input
                  v-else-if="option.type === 'number'"
                  v-model.number="defaultsValues[option.optionId]"
                  type="number"
                  :label="option.friendlyName"
                  outlined
                  dense
                  dark
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => val !== null && val !== '' || `${option.friendlyName} is required`] : []"
                />

                <!-- Password Input -->
                <q-input
                  v-else-if="option.type === 'password'"
                  v-model="defaultsValues[option.optionId]"
                  type="password"
                  :label="option.friendlyName"
                  outlined
                  dense
                  dark
                  :disable="isReadOnly"
                  :placeholder="defaultPasswordHasValue[option.optionId] ? '••••••••' : ''"
                  @update:model-value="onDefaultPasswordChange(option.optionId, $event)"
                  :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                >
                  <template v-slot:append>
                    <q-icon v-if="defaultPasswordChanged[option.optionId]" name="warning" color="orange">
                      <q-tooltip>Default password will be changed</q-tooltip>
                    </q-icon>
                  </template>
                  <template v-slot:hint>
                    <span v-if="defaultPasswordHasValue[option.optionId] && !defaultPasswordChanged[option.optionId]" class="text-grey-6">
                      Leave blank to keep current default password
                    </span>
                    <span v-if="defaultPasswordChanged[option.optionId]" class="text-orange" style="font-weight: 500;">
                      <q-icon name="warning" size="xs" /> Default password will be changed
                    </span>
                  </template>
                </q-input>

                <!-- Select/Dropdown -->
                <q-select
                  v-else-if="option.type === 'select' && (option.options || option.choices)"
                  v-model="defaultsValues[option.optionId]"
                  :options="option.options || option.choices"
                  :label="option.friendlyName"
                  outlined
                  dense
                  dark
                  emit-value
                  map-options
                  color="teal"
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => val !== null && val !== '' || `${option.friendlyName} is required`] : []"
                />

                <!-- Boolean Checkbox -->
                <q-checkbox
                  v-else-if="option.type === 'boolean' || option.type === 'checkbox'"
                  v-model="defaultsValues[option.optionId]"
                  :label="option.friendlyName"
                  dense
                  color="teal"
                  :disable="isReadOnly"
                />

                <!-- Textarea -->
                <q-input
                  v-else-if="option.type === 'textarea'"
                  v-model="defaultsValues[option.optionId]"
                  type="textarea"
                  :label="option.friendlyName"
                  outlined
                  rows="3"
                  dense
                  dark
                  :disable="isReadOnly"
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                />

                <!-- Multi-Select (Checkboxes) -->
                <div v-else-if="option.type === 'multiselect'" class="q-mt-md">
                  <q-card flat style="border: 2px solid #1db885;" class="bg-grey-7">
                    <q-card-section class="bg-teal-8 text-white q-py-sm">
                      <div class="text-subtitle2">{{ option.friendlyName }}</div>
                    </q-card-section>
                    <q-card-section class="q-gutter-sm">
                      <div class="row q-col-gutter-md">
                        <template v-for="choice in (option.choices || option.options || [])" :key="choice">
                          <div class="col-12 col-sm-6 col-md-4">
                            <q-checkbox
                              :model-value="(Array.isArray(defaultsValues[option.optionId]) ? defaultsValues[option.optionId] : []).includes(choice)"
                              @update:model-value="toggleDefaultMultiselectChoice(option.optionId, choice)"
                              :label="choice"
                              color="teal"
                              :disable="isReadOnly"
                              dense
                              class="text-white"
                            />
                          </div>
                        </template>
                      </div>
                      <div v-if="(!option.choices && !option.options) || (option.choices || option.options || []).length === 0" class="text-caption text-grey-5">
                        No options available
                      </div>
                    </q-card-section>
                  </q-card>
                </div>

                <!-- Ordered Multi-Select -->
                <div v-else-if="option.type === 'orderedmultiselect'" class="q-gutter-md">
                  <div class="text-subtitle2 text-white">{{ option.friendlyName }}</div>
                  <div class="row q-gutter-md">
                    <!-- Available Options -->
                    <div class="col">
                      <div class="text-caption text-teal-3">Available</div>
                      <q-list bordered separator style="border: 1px solid #1db885;" class="bg-grey-8 q-mt-xs">
                        <q-item
                          v-for="avail in availableDefaultChoices(option)"
                          :key="avail"
                          :clickable="!isReadOnly"
                          @click="!isReadOnly && moveDefaultToSelected(option.optionId, avail)"
                        >
                          <q-item-section avatar>
                            <q-icon name="chevron_right" :color="isReadOnly ? 'grey' : 'teal'" />
                          </q-item-section>
                          <q-item-section class="text-white">{{ avail }}</q-item-section>
                        </q-item>
                      </q-list>
                    </div>

                    <!-- Selected Options -->
                    <div class="col">
                      <div class="text-caption text-teal-3">Selected (Ordered)</div>
                      <q-list bordered separator style="border: 1px solid #1db885;" class="bg-grey-8 q-mt-xs">
                        <q-item
                          v-for="(selected, idx) in (defaultsValues[option.optionId] || [])"
                          :key="selected"
                          class="q-pa-xs"
                        >
                          <q-item-section avatar>
                            <div class="column q-gutter-xs">
                              <q-btn
                                v-if="idx > 0 && !isReadOnly"
                                flat
                                dense
                                round
                                size="sm"
                                icon="arrow_upward"
                                color="teal"
                                @click="moveDefaultUpSelected(option.optionId, idx)"
                              />
                              <q-btn
                                v-if="idx < (defaultsValues[option.optionId] || []).length - 1 && !isReadOnly"
                                flat
                                dense
                                round
                                size="sm"
                                icon="arrow_downward"
                                color="teal"
                                @click="moveDefaultDownSelected(option.optionId, idx)"
                              />
                            </div>
                          </q-item-section>
                          <q-item-section class="text-white">{{ selected }}</q-item-section>
                          <q-item-section avatar>
                            <q-btn
                              v-if="!isReadOnly"
                              flat
                              dense
                              round
                              size="sm"
                              icon="chevron_left"
                              color="teal"
                              @click="moveDefaultToAvailable(option.optionId, selected)"
                            />
                          </q-item-section>
                        </q-item>
                      </q-list>
                      <div v-if="!defaultsValues[option.optionId] || defaultsValues[option.optionId].length === 0" class="text-caption text-grey-6 q-mt-md">
                        Click items on the left to select
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Unsupported type fallback -->
                <div v-else class="text-warning">
                  <q-icon name="warning" />
                  Unsupported option type: {{ option.type }}
                </div>
              </template>
            </q-card-section>
          </q-card>

          <!-- Empty state -->
          <q-banner v-if="!selectedType?.deviceSpecificOptions?.sections || selectedType.deviceSpecificOptions.sections.length === 0" class="bg-info text-white">
            <q-icon name="info" />
            This device type has no configurable device defaults.
          </q-banner>
        </q-card-section>

        <!-- Actions -->
        <q-card-actions class="q-pa-md">
          <q-btn v-if="!isReadOnly" flat label="Reset to Defaults" color="warning" @click="confirmDefaultReset" />
          <q-space />
          <q-btn flat :label="isReadOnly ? 'Close' : 'Cancel'" color="primary" v-close-popup />
          <q-btn
            v-if="!isReadOnly"
            unelevated
            label="Save"
            color="positive"
            @click="saveDeviceDefaults"
            :loading="savingDefaults"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Device Defaults Reset Confirmation Dialog -->
    <q-dialog v-model="showDefaultsResetConfirm">
      <q-card style="min-width: 400px" class="bg-grey-9">
        <q-card-section class="bg-warning text-white">
          <div class="text-h6">Reset Defaults?</div>
        </q-card-section>
        <q-card-section class="text-white">
          <p>Are you sure you want to reset all device defaults to the renderer defaults?</p>
          <p class="text-caption text-grey-5">This will overwrite all changes you've made.</p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn unelevated label="Reset" color="warning" @click="performDefaultReset" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reset Confirmation Dialog -->
    <q-dialog v-model="showResetConfirm">
      <q-card style="min-width: 400px" class="bg-grey-9">
        <q-card-section class="bg-warning text-white">
          <div class="text-h6">Reset to Defaults?</div>
        </q-card-section>
        <q-card-section class="text-white">
          <p>Are you sure you want to reset all options to their default values?</p>
          <p class="text-caption text-grey-5">This will overwrite all changes you've made.</p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn unelevated label="Reset" color="warning" @click="performReset" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import api from '../api';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();
const isReadOnly = computed(() => authStore.user?.role === 'readonly');

const deviceTypes = ref([]);
const selectedType = ref(null);
const showOptionsDialog = ref(false);
const showResetConfirm = ref(false);
const showDefaultsDialog = ref(false);
const showDefaultsResetConfirm = ref(false);
const loading = ref(false);
const savingOptions = ref(false);
const optionsError = ref('');
const defaultsError = ref('');
const optionValues = ref({});
const defaultsValues = ref({});
const savingDefaults = ref(false);
const defaultPasswordChanged = ref({});
const defaultPasswordHasValue = ref({});

const extractErrorMessage = (error, fallback) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;
  if (error.response?.status === 409) {
    return 'Cannot complete this operation: The item is currently in use by other records. Please remove dependencies first.';
  }
  if (error.response?.status === 404) {
    return 'The requested item was not found. It may have been deleted.';
  }
  if (error.response?.status === 403) {
    return 'You do not have permission to perform this action.';
  }
  if (error.response?.status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  if (error.request) {
    return 'Network error: Unable to reach the server. Please check your connection.';
  }
  return fallback || 'An unexpected error occurred. Please try again.';
};

const loadTypes = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/device-types/');
    deviceTypes.value = data;
  } finally {
    loading.value = false;
  }
};

/**
 * Open the common options dialog for a device type.
 * Load current values from the database or use defaults from schema.
 */
const openOptions = async (deviceType) => {
  selectedType.value = deviceType;
  optionsError.value = '';
  optionValues.value = {};

  // Try to load saved common options from database
  try {
    const { data } = await api.get(`/device-type-config/${deviceType.typeId}/`);
    // Merge saved values with defaults from schema
    if (data.common_options?.sections) {
      data.common_options.sections.forEach(section => {
        section.options?.forEach(option => {
          const savedValue = data.saved_values?.[option.optionId];
          const defaultValue = option.default ?? (option.type === 'orderedmultiselect' || option.type === 'multiselect' ? [] : '');
          optionValues.value[option.optionId] = savedValue ?? defaultValue;
        });
      });
    }
  } catch (error) {
    // If no config exists yet, initialize with defaults from schema
    if (deviceType.commonOptions?.sections) {
      deviceType.commonOptions.sections.forEach(section => {
        section.options?.forEach(option => {
          const defaultValue = option.default ?? (option.type === 'orderedmultiselect' || option.type === 'multiselect' ? [] : '');
          optionValues.value[option.optionId] = defaultValue;
        });
      });
    }
  }

  showOptionsDialog.value = true;
};

const onDefaultPasswordChange = (optionId, value) => {
  defaultPasswordChanged.value[optionId] = value !== undefined && value !== null && String(value).length > 0;
};

/**
 * Open the device defaults dialog for a device type.
 * Load current defaults from the database or use defaults from schema.
 */
const openDeviceDefaults = async (deviceType) => {
  selectedType.value = deviceType;
  defaultsError.value = '';
  defaultsValues.value = {};
  defaultPasswordChanged.value = {};
  defaultPasswordHasValue.value = {};

  try {
    const { data } = await api.get(`/device-type-config/${deviceType.typeId}/`);
    const savedDefaults = data.device_defaults || {};

    if (deviceType.deviceSpecificOptions?.sections) {
      deviceType.deviceSpecificOptions.sections.forEach(section => {
        section.options?.forEach(option => {
          const savedValue = savedDefaults?.[option.optionId];
          const baseDefault = option.default ?? (option.type === 'orderedmultiselect' || option.type === 'multiselect' ? [] : '');

          if (option.type === 'password') {
            if (savedValue) {
              defaultPasswordHasValue.value[option.optionId] = true;
              defaultsValues.value[option.optionId] = '';
            } else {
              defaultPasswordHasValue.value[option.optionId] = false;
              defaultsValues.value[option.optionId] = savedValue ?? baseDefault;
            }
            return;
          }

          const resolvedValue = savedValue ?? baseDefault;
          if (option.type === 'orderedmultiselect' || option.type === 'multiselect') {
            if (resolvedValue === undefined || resolvedValue === null) {
              defaultsValues.value[option.optionId] = [];
            } else if (!Array.isArray(resolvedValue)) {
              defaultsValues.value[option.optionId] = [resolvedValue];
            } else {
              defaultsValues.value[option.optionId] = [...resolvedValue];
            }
          } else {
            defaultsValues.value[option.optionId] = resolvedValue;
          }
        });
      });
    }
  } catch (error) {
    if (error.response?.status && error.response.status !== 404) {
      defaultsError.value = extractErrorMessage(error, 'Failed to load device defaults.');
    }
    if (deviceType.deviceSpecificOptions?.sections) {
      deviceType.deviceSpecificOptions.sections.forEach(section => {
        section.options?.forEach(option => {
          const baseDefault = option.default ?? (option.type === 'orderedmultiselect' || option.type === 'multiselect' ? [] : '');
          if (option.type === 'password') {
            defaultPasswordHasValue.value[option.optionId] = false;
            defaultsValues.value[option.optionId] = baseDefault;
            return;
          }
          if (option.type === 'orderedmultiselect' || option.type === 'multiselect') {
            defaultsValues.value[option.optionId] = Array.isArray(baseDefault) ? [...baseDefault] : (baseDefault ? [baseDefault] : []);
          } else {
            defaultsValues.value[option.optionId] = baseDefault;
          }
        });
      });
    }
  }

  showDefaultsDialog.value = true;
};

/**
 * Save common options to the database.
 */
const saveOptions = async () => {
  optionsError.value = '';
  savingOptions.value = true;
  try {
    await api.put(`/device-type-config/${selectedType.value.typeId}/`, {
      common_options: selectedType.value.commonOptions,
      saved_values: optionValues.value
    });
    showOptionsDialog.value = false;
  } catch (error) {
    optionsError.value = extractErrorMessage(error, 'Failed to save options. Please try again.');
  } finally {
    savingOptions.value = false;
  }
};

/**
 * Save device defaults to the database.
 */
const saveDeviceDefaults = async () => {
  defaultsError.value = '';
  savingDefaults.value = true;
  try {
    const payload = { ...defaultsValues.value };
    if (selectedType.value?.deviceSpecificOptions?.sections) {
      selectedType.value.deviceSpecificOptions.sections.forEach(section => {
        section.options?.forEach(option => {
          if (option.type === 'password' && !defaultPasswordChanged.value[option.optionId]) {
            delete payload[option.optionId];
          }
        });
      });
    }

    await api.put(`/device-type-config/${selectedType.value.typeId}/`, {
      device_defaults: payload
    });
    showDefaultsDialog.value = false;
  } catch (error) {
    defaultsError.value = extractErrorMessage(error, 'Failed to save device defaults. Please try again.');
  } finally {
    savingDefaults.value = false;
  }
};

/**
 * Show the reset confirmation dialog.
 */
const confirmReset = () => {
  showResetConfirm.value = true;
};

/**
 * Show the reset confirmation dialog for device defaults.
 */
const confirmDefaultReset = () => {
  showDefaultsResetConfirm.value = true;
};

/**
 * Reset all options to their default values from the schema.
 */
const performReset = () => {
  showResetConfirm.value = false;
  if (selectedType.value?.commonOptions?.sections) {
    selectedType.value.commonOptions.sections.forEach(section => {
      section.options?.forEach(option => {
        const defaultValue = option.default ?? (option.type === 'orderedmultiselect' || option.type === 'multiselect' ? [] : '');
        optionValues.value[option.optionId] = defaultValue;
      });
    });
  }
};

/**
 * Reset device defaults to renderer defaults.
 */
const performDefaultReset = () => {
  showDefaultsResetConfirm.value = false;
  if (selectedType.value?.deviceSpecificOptions?.sections) {
    selectedType.value.deviceSpecificOptions.sections.forEach(section => {
      section.options?.forEach(option => {
        const baseDefault = option.default ?? (option.type === 'orderedmultiselect' || option.type === 'multiselect' ? [] : '');
        if (option.type === 'password') {
          defaultPasswordHasValue.value[option.optionId] = false;
          defaultsValues.value[option.optionId] = baseDefault;
          defaultPasswordChanged.value[option.optionId] = false;
          return;
        }
        if (option.type === 'orderedmultiselect' || option.type === 'multiselect') {
          defaultsValues.value[option.optionId] = Array.isArray(baseDefault) ? [...baseDefault] : (baseDefault ? [baseDefault] : []);
        } else {
          defaultsValues.value[option.optionId] = baseDefault;
        }
      });
    });
  }
};

/**
 * Sort sections by uiOrder.
 */
const sortedSections = computed(() => {
  if (!selectedType.value?.commonOptions?.sections) return [];
  return [...selectedType.value.commonOptions.sections].sort(
    (a, b) => (a.uiOrder || 999) - (b.uiOrder || 999)
  );
});

const sortedDefaultSections = computed(() => {
  if (!selectedType.value?.deviceSpecificOptions?.sections) return [];
  return [...selectedType.value.deviceSpecificOptions.sections].sort(
    (a, b) => (a.uiOrder || 999) - (b.uiOrder || 999)
  );
});

/**
 * Sort options within a section by uiOrder.
 */
const sortedOptions = (options) => {
  if (!options) return [];
  return [...options].sort((a, b) => (a.uiOrder || 999) - (b.uiOrder || 999));
};

const sortedDefaultOptions = (options) => {
  if (!options) return [];
  return [...options].sort((a, b) => (a.uiOrder || 999) - (b.uiOrder || 999));
};

/**
 * Toggle a choice in a multiselect option.
 */
const toggleMultiselectChoice = (optionId, choice) => {
  if (!optionValues.value[optionId]) {
    optionValues.value[optionId] = [];
  }
  const idx = optionValues.value[optionId].indexOf(choice);
  if (idx === -1) {
    // Add choice
    optionValues.value[optionId].push(choice);
  } else {
    // Remove choice
    optionValues.value[optionId].splice(idx, 1);
  }
};

const toggleDefaultMultiselectChoice = (optionId, choice) => {
  if (!defaultsValues.value[optionId]) {
    defaultsValues.value[optionId] = [];
  }
  const idx = defaultsValues.value[optionId].indexOf(choice);
  if (idx === -1) {
    defaultsValues.value[optionId].push(choice);
  } else {
    defaultsValues.value[optionId].splice(idx, 1);
  }
};

/**
 * Get available options for orderedmultiselect (not yet selected).
 */
const availableOptions = (option) => {
  const choicesArray = option.choices || option.options;
  if (!choicesArray || !Array.isArray(choicesArray)) return [];
  const selected = optionValues.value[option.optionId];
  // Handle both array and non-array values defensively
  const selectedArray = Array.isArray(selected) ? selected : (selected ? [selected] : []);
  return choicesArray.filter(opt => !selectedArray.includes(opt));
};

const availableDefaultChoices = (option) => {
  const choicesArray = option.choices || option.options;
  if (!choicesArray || !Array.isArray(choicesArray)) return [];
  const selected = defaultsValues.value[option.optionId];
  const selectedArray = Array.isArray(selected) ? selected : (selected ? [selected] : []);
  return choicesArray.filter(opt => !selectedArray.includes(opt));
};

/**
 * Move an option from available to selected for orderedmultiselect.
 */
const moveToSelected = (optionId, value) => {
  if (!optionValues.value[optionId]) {
    optionValues.value[optionId] = [];
  }
  if (!optionValues.value[optionId].includes(value)) {
    optionValues.value[optionId].push(value);
  }
};

const moveDefaultToSelected = (optionId, value) => {
  if (!defaultsValues.value[optionId]) {
    defaultsValues.value[optionId] = [];
  }
  if (!defaultsValues.value[optionId].includes(value)) {
    defaultsValues.value[optionId].push(value);
  }
};

/**
 * Move an option from selected to available for orderedmultiselect.
 */
const moveToAvailable = (optionId, value) => {
  if (optionValues.value[optionId]) {
    optionValues.value[optionId] = optionValues.value[optionId].filter(v => v !== value);
  }
};

const moveDefaultToAvailable = (optionId, value) => {
  if (defaultsValues.value[optionId]) {
    defaultsValues.value[optionId] = defaultsValues.value[optionId].filter(v => v !== value);
  }
};

/**
 * Move a selected option up in the list for orderedmultiselect.
 */
const moveUpSelected = (optionId, idx) => {
  if (idx > 0 && optionValues.value[optionId]) {
    const temp = optionValues.value[optionId][idx - 1];
    optionValues.value[optionId][idx - 1] = optionValues.value[optionId][idx];
    optionValues.value[optionId][idx] = temp;
  }
};

const moveDefaultUpSelected = (optionId, idx) => {
  if (idx > 0 && defaultsValues.value[optionId]) {
    const temp = defaultsValues.value[optionId][idx - 1];
    defaultsValues.value[optionId][idx - 1] = defaultsValues.value[optionId][idx];
    defaultsValues.value[optionId][idx] = temp;
  }
};

/**
 * Move a selected option down in the list for orderedmultiselect.
 */
const moveDownSelected = (optionId, idx) => {
  if (idx < (optionValues.value[optionId] || []).length - 1 && optionValues.value[optionId]) {
    const temp = optionValues.value[optionId][idx + 1];
    optionValues.value[optionId][idx + 1] = optionValues.value[optionId][idx];
    optionValues.value[optionId][idx] = temp;
  }
};

const moveDefaultDownSelected = (optionId, idx) => {
  if (idx < (defaultsValues.value[optionId] || []).length - 1 && defaultsValues.value[optionId]) {
    const temp = defaultsValues.value[optionId][idx + 1];
    defaultsValues.value[optionId][idx + 1] = defaultsValues.value[optionId][idx];
    defaultsValues.value[optionId][idx] = temp;
  }
};

onMounted(loadTypes);
</script>
