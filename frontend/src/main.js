/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

import { createApp } from 'vue';
import { Dark, Quasar } from 'quasar';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';

import 'quasar/src/css/index.sass';
import '@quasar/extras/material-icons/material-icons.css';
import './styles/theme.css';

const app = createApp(App);
app.use(Quasar, {
  plugins: [],
  config: {
    dark: true,
    brand: {
      primary: '#0fa36b',
      secondary: '#0b6e4f',
      accent: '#8af3c4'
    }
  }
});
Dark.set(true);
app.use(createPinia());
app.use(router);
app.mount('#q-app');
