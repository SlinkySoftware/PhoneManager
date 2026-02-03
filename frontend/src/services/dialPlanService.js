/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

import api from '../api';

/**
 * Dial Plan API service.
 * Provides CRUD operations and test functionality for dial plans.
 */
export const dialPlanService = {
  /**
   * List all dial plans.
   * @returns {Promise} Axios response with array of dial plans
   */
  list() {
    return api.get('/dial-plans/');
  },

  /**
   * Get a specific dial plan by ID.
   * @param {number} id - Dial plan ID
   * @returns {Promise} Axios response with dial plan details
   */
  get(id) {
    return api.get(`/dial-plans/${id}/`);
  },

  /**
   * Create a new dial plan.
   * @param {Object} data - Dial plan data
   * @param {string} data.name - Dial plan name (unique)
   * @param {string} data.description - Dial plan description
   * @param {Array} data.rules - Array of rule objects with input_regex, output_regex, sequence_order
   * @returns {Promise} Axios response with created dial plan
   */
  create(data) {
    return api.post('/dial-plans/', data);
  },

  /**
   * Update an existing dial plan.
   * @param {number} id - Dial plan ID
   * @param {Object} data - Updated dial plan data
   * @returns {Promise} Axios response with updated dial plan
   */
  update(id, data) {
    return api.patch(`/dial-plans/${id}/`, data);
  },

  /**
   * Delete a dial plan.
   * @param {number} id - Dial plan ID
   * @returns {Promise} Axios response
   */
  delete(id) {
    return api.delete(`/dial-plans/${id}/`);
  },

  /**
   * Test a dial plan against a phone number.
   * @param {number} dialPlanId - Dial plan ID to test
   * @param {string} inputNumber - Phone number to transform
   * @returns {Promise} Axios response with test results:
   *   - output: Transformed phone number
   *   - matched: Boolean indicating if a rule matched
   *   - matched_rule_index: Index of matched rule (if matched)
   *   - matched_rule_pattern: Input pattern of matched rule (if matched)
   */
  test(dialPlanId, inputNumber) {
    return api.post('/dial-plans/test/', {
      dial_plan_id: dialPlanId,
      input_number: inputNumber
    });
  }
};
