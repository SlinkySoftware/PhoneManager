/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

import api from '../api';

/**
 * Bulk import API service.
 */
export const importService = {
  /**
   * Download the workbook template for bulk import.
   * @returns {Promise} Axios response containing the workbook blob
   */
  downloadTemplate() {
    return api.get('/imports/template/', {
      responseType: 'blob'
    });
  },

  /**
   * Upload a populated workbook for processing.
   * @param {File} file - XLSX workbook selected by the user
   * @returns {Promise} Axios response with import summary data
   */
  uploadWorkbook(file) {
    const formData = new window.FormData();
    formData.append('file', file);

    return api.post('/imports/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }
};