/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

import process from 'node:process';

export default function (ctx) {
  return {
    framework: {
      config: {
        dark: true,
        brand: {
          primary: '#0fa36b',
          secondary: '#0b6e4f',
          accent: '#8af3c4',
          negative: '#ef5030'
        }
      },
      lang: 'en-US',
      iconSet: 'material-icons',
      plugins: []
    },
    build: {
      vueRouterMode: 'history',
      // Quasar manages dotenv loading itself rather than using Vite's defaults.
      env: {
        clientPrefix: 'VITE_',
        file: ctx.prod
          ? ['.env.production', '.env.production.local']
          : ['.env.development', '.env.development.local']
      }
    },
    devServer: {
      port: 9000,
      open: false,
      proxy: {
        '/api/': {
          target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true
        }
      }
    }
  };
}
