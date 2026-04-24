<!-- SPDX-License-Identifier: GPL-3.0-or-later
     Copyright (c) 2026 Slinky Software -->
<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-col-gutter-md q-mb-md">
      <div class="col-12 col-md">
        <div class="text-h5">Bulk Import</div>
        <div class="text-caption text-grey-6">
          Download the template, populate the Devices and Lines sheets, then upload the workbook to create records in bulk.
        </div>
      </div>
      <div class="col-12 col-md-auto row q-gutter-sm">
        <q-btn
          color="secondary"
          icon="download"
          label="Download Template"
          :loading="downloadingTemplate"
          @click="downloadTemplate"
        />
        <q-btn
          color="primary"
          icon="upload_file"
          label="Import Workbook"
          :loading="uploading"
          :disable="!selectedFile"
          @click="uploadWorkbook"
        />
      </div>
    </div>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Workbook</div>
        <q-file
          v-model="selectedFile"
          label="Choose populated XLSX template"
          outlined
          dense
          accept=".xlsx"
          max-file-size="5242880"
          @rejected="onFileRejected"
        >
          <template #prepend>
            <q-icon name="description" />
          </template>
        </q-file>
      </q-card-section>

      <q-card-section v-if="errorMessage" class="bg-negative text-white q-mb-md">
        <q-icon name="error" class="q-mr-md" />
        {{ errorMessage }}
      </q-card-section>

      <q-card-section class="text-caption text-grey-7">
        Required columns are fixed by the template. Devices can only reference line numbers defined in the same workbook.
      </q-card-section>
    </q-card>

    <q-card v-if="results" flat bordered class="q-mt-lg">
      <q-card-section>
        <div class="text-h6">Import Summary</div>
      </q-card-section>
      <q-separator />
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-card flat bordered>
              <q-card-section>
                <div class="text-subtitle1">Lines</div>
                <div class="text-body2">Total: {{ results.lines.total }}</div>
                <div class="text-positive">Imported: {{ results.lines.imported_count }}</div>
                <div class="text-warning">Skipped: {{ results.lines.skipped_count }}</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-12 col-md-6">
            <q-card flat bordered>
              <q-card-section>
                <div class="text-subtitle1">Devices</div>
                <div class="text-body2">Total: {{ results.devices.total }}</div>
                <div class="text-positive">Imported: {{ results.devices.imported_count }}</div>
                <div class="text-warning">Skipped: {{ results.devices.skipped_count }}</div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-card-section>

      <q-card-section v-if="results.lines.skipped_count || results.devices.skipped_count" class="q-gutter-md">
        <q-expansion-item
          v-if="results.lines.skipped_count"
          label="Skipped Lines"
          icon="call"
          default-opened
          header-class="text-negative"
        >
          <q-table
            flat
            bordered
            :rows="results.lines.skipped"
            :columns="skippedColumns"
            row-key="row"
            hide-pagination
          />
        </q-expansion-item>

        <q-expansion-item
          v-if="results.devices.skipped_count"
          label="Skipped Devices"
          icon="devices"
          default-opened
          header-class="text-negative"
        >
          <q-table
            flat
            bordered
            :rows="results.devices.skipped"
            :columns="skippedColumns"
            row-key="row"
            hide-pagination
          />
        </q-expansion-item>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue';
import { importService } from '../services/importService';

const selectedFile = ref(null);
const downloadingTemplate = ref(false);
const uploading = ref(false);
const errorMessage = ref('');
const results = ref(null);

const skippedColumns = [
  { name: 'row', label: 'Row', field: 'row', align: 'left', sortable: true },
  { name: 'identifier', label: 'Identifier', field: 'identifier', align: 'left', sortable: true },
  { name: 'reason', label: 'Reason', field: 'reason', align: 'left', sortable: false }
];

const extractErrorMessage = (error) => {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.response?.data?.message) return error.response.data.message;

  if (error.response?.status === 409) {
    return 'Cannot complete this operation: The item is currently in use by other records. Please remove dependencies first.';
  }
  if (error.response?.status === 404) return 'The requested item was not found. It may have been deleted.';
  if (error.response?.status === 403) return 'You do not have permission to perform this action.';
  if (error.response?.status === 401) return 'Your session has expired. Please log in again.';

  if (error.response?.statusText) return `Operation failed: ${error.response.statusText}`;
  if (error.request) return 'Network error: Unable to reach the server. Please check your connection.';

  return 'An unexpected error occurred. Please try again or contact support if the problem persists.';
};

const downloadTemplate = async () => {
  errorMessage.value = '';
  downloadingTemplate.value = true;

  try {
    const response = await importService.downloadTemplate();
    const blob = new window.Blob([response.data], {
      type: response.headers['content-type'] || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'phone-manager-bulk-import-template.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    downloadingTemplate.value = false;
  }
};

const uploadWorkbook = async () => {
  errorMessage.value = '';
  results.value = null;

  if (!selectedFile.value) {
    errorMessage.value = 'Please choose an XLSX workbook to import.';
    return;
  }

  if (!selectedFile.value.name.toLowerCase().endsWith('.xlsx')) {
    errorMessage.value = 'Only .xlsx workbook files are supported.';
    return;
  }

  uploading.value = true;
  try {
    const response = await importService.uploadWorkbook(selectedFile.value);
    results.value = response.data;
  } catch (error) {
    errorMessage.value = extractErrorMessage(error);
  } finally {
    uploading.value = false;
  }
};

const onFileRejected = () => {
  errorMessage.value = 'Workbook must be an .xlsx file no larger than 5 MB.';
};
</script>