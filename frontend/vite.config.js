import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { quasar, transformAssetUrls } from '@quasar/vite-plugin';

export default defineConfig({
  plugins: [
    vue({ template: { transformAssetUrls } }),
    quasar({
      sassVariables: 'src/styles/quasar-variables.sass'
    })
  ],
  server: {
    port: 9000,
    host: '0.0.0.0'
  },
  preview: {
    port: 9000,
    host: '0.0.0.0'
  }
});
