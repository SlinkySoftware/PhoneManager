<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">Device Types</div>
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
              <q-btn color="secondary" flat label="Common Options" @click="openOptions(dt)" />
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
          <div class="text-h6">{{ selectedType?.manufacturer }} {{ selectedType?.model }} - Common Options</div>
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
                  :hint="option.mandatory ? 'Required' : 'Optional'"
                  :rules="option.mandatory ? [val => !!val || `${option.friendlyName} is required`] : []"
                />

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
                          clickable
                          @click="moveToSelected(option.optionId, avail)"
                        >
                          <q-item-section avatar>
                            <q-icon name="chevron_right" color="green" />
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
                                v-if="idx > 0"
                                flat
                                dense
                                round
                                size="sm"
                                icon="arrow_upward"
                                color="green"
                                @click="moveUpSelected(option.optionId, idx)"
                              />
                              <q-btn
                                v-if="idx < (optionValues[option.optionId] || []).length - 1"
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
          <q-btn flat label="Reset to Defaults" color="warning" @click="confirmReset" />
          <q-space />
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn
            unelevated
            label="Save"
            color="positive"
            @click="saveOptions"
            :loading="savingOptions"
          />
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

const deviceTypes = ref([]);
const selectedType = ref(null);
const showOptionsDialog = ref(false);
const showResetConfirm = ref(false);
const loading = ref(false);
const savingOptions = ref(false);
const optionsError = ref('');
const optionValues = ref({});

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
          const defaultValue = option.default ?? (option.type === 'orderedmultiselect' ? [] : '');
          optionValues.value[option.optionId] = savedValue ?? defaultValue;
        });
      });
    }
  } catch (error) {
    // If no config exists yet, initialize with defaults from schema
    if (deviceType.commonOptions?.sections) {
      deviceType.commonOptions.sections.forEach(section => {
        section.options?.forEach(option => {
          const defaultValue = option.default ?? (option.type === 'orderedmultiselect' ? [] : '');
          optionValues.value[option.optionId] = defaultValue;
        });
      });
    }
  }

  showOptionsDialog.value = true;
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
    optionsError.value = error.response?.data?.detail ||
                        error.response?.data?.message ||
                        'Failed to save options. Please try again.';
  } finally {
    savingOptions.value = false;
  }
};

/**
 * Show the reset confirmation dialog.
 */
const confirmReset = () => {
  showResetConfirm.value = true;
};

/**
 * Reset all options to their default values from the schema.
 */
const performReset = () => {
  showResetConfirm.value = false;
  if (selectedType.value?.commonOptions?.sections) {
    selectedType.value.commonOptions.sections.forEach(section => {
      section.options?.forEach(option => {
        const defaultValue = option.default ?? (option.type === 'orderedmultiselect' ? [] : '');
        optionValues.value[option.optionId] = defaultValue;
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

/**
 * Sort options within a section by uiOrder.
 */
const sortedOptions = (options) => {
  if (!options) return [];
  return [...options].sort((a, b) => (a.uiOrder || 999) - (b.uiOrder || 999));
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

/**
 * Move an option from selected to available for orderedmultiselect.
 */
const moveToAvailable = (optionId, value) => {
  if (optionValues.value[optionId]) {
    optionValues.value[optionId] = optionValues.value[optionId].filter(v => v !== value);
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

onMounted(loadTypes);
</script>
