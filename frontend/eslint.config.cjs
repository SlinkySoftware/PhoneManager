/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

const pluginVue = require('eslint-plugin-vue');

module.exports = [
  {
    ignores: ['dist/**', 'node_modules/**', '.quasar/**', 'eslint.config.*']
  },
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.{js,mjs,cjs,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        navigator: 'readonly',
        console: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly'
      }
    },
    rules: {
      'no-undef': 'error',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'vue/no-side-effects-in-computed-properties': 'off',
      'vue/multi-word-component-names': 'off'
    }
  }
];