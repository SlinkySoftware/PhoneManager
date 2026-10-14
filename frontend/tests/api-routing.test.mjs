/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

import assert from 'node:assert/strict';
import process from 'node:process';
import { test } from 'node:test';
import { fileURLToPath, URL } from 'node:url';
import { createServer } from 'vite';
import quasarConfig from '../quasar.config.js';

const root = fileURLToPath(new URL('../', import.meta.url));

test('Quasar exposes VITE variables and loads the matching environment files', () => {
  const production = quasarConfig({ prod: true });
  assert.equal(production.build.env.clientPrefix, 'VITE_');
  assert.deepEqual(production.build.env.file, ['.env.production', '.env.production.local']);
  assert.deepEqual(quasarConfig({ prod: false }).build.env.file, ['.env.development', '.env.development.local']);
  assert.equal(production.build.vueRouterMode, 'history');
});

test('development proxy preserves the API prefix and supports a Docker backend', () => {
  const originalTarget = process.env.API_PROXY_TARGET;
  try {
    delete process.env.API_PROXY_TARGET;
    const proxy = quasarConfig({ prod: false }).devServer.proxy['/api/'];
    assert.equal(proxy.target, 'http://127.0.0.1:8000');
    assert.equal(proxy.changeOrigin, true);
    assert.equal(proxy.rewrite, undefined);

    process.env.API_PROXY_TARGET = 'http://backend:8000';
    assert.equal(quasarConfig({ prod: false }).devServer.proxy['/api/'].target, 'http://backend:8000');
    assert.equal(quasarConfig({ prod: false }).devServer.proxy['/internal/'], undefined);
  } finally {
    if (originalTarget === undefined) {
      delete process.env.API_PROXY_TARGET;
    } else {
      process.env.API_PROXY_TARGET = originalTarget;
    }
  }
});

for (const baseURL of ['', 'https://api.example.com/api/']) {
  test(`API and public authentication clients share ${baseURL || 'the same-origin default'}`, async () => {
    const server = await createServer({
      configFile: false,
      root,
      envDir: false,
      define: { 'import.meta.env.VITE_API_BASE': JSON.stringify(baseURL) },
      server: { middlewareMode: true, watch: null, ws: false },
      appType: 'custom'
    });
    try {
      const { default: api, createApiClient } = await server.ssrLoadModule('/src/api.js');
      const publicApi = createApiClient({ authenticated: false });
      assert.equal(api.defaults.baseURL, baseURL || '/api');
      assert.equal(publicApi.defaults.baseURL, api.defaults.baseURL);

      const expectedPrefix = (baseURL || '/api').replace(/\/$/, '');
      for (const endpoint of ['/auth/config/', '/auth/login/', '/auth/ldap/login/', '/auth/saml/login/']) {
        assert.equal(publicApi.getUri({ url: endpoint }), `${expectedPrefix}${endpoint}`);
      }
      assert.equal(api.interceptors.request.handlers.length, 1);
      assert.equal(api.interceptors.response.handlers.length, 1);
      assert.equal(publicApi.interceptors.request.handlers.length, 0);
      assert.equal(publicApi.interceptors.response.handlers.length, 0);

      // Invalid credentials must reach the login form, not trigger session redirects.
      const error = new Error('Invalid credentials');
      error.response = { status: 401 };
      await assert.rejects(
        publicApi.post('/auth/login/', {}, { adapter: () => Promise.reject(error) }),
        (caught) => caught === error
      );
    } finally {
      await server.close();
    }
  });
}