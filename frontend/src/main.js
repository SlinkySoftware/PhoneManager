import { createApp } from 'vue';
import { Quasar } from 'quasar';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';

import 'quasar/src/css/index.sass';
import '@quasar/extras/material-icons/material-icons.css';

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
app.use(createPinia());
app.use(router);
app.mount('#q-app');
