/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 Slinky Software
 */

import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '../pages/LoginPage.vue';
import DeviceTypesPage from '../pages/DeviceTypesPage.vue';
import DevicesPage from '../pages/DevicesPage.vue';
import DialPlansPage from '../pages/DialPlansPage.vue';
import ImportsPage from '../pages/ImportsPage.vue';
import SIPServersPage from '../pages/SIPServersPage.vue';
import SitesPage from '../pages/SitesPage.vue';
import LinesPage from '../pages/LinesPage.vue';
import UsersPage from '../pages/UsersPage.vue';
import ChangePasswordPage from '../pages/ChangePasswordPage.vue';
import UserSettingsPage from '../pages/UserSettingsPage.vue';

const routes = [
  { path: '/login', component: LoginPage, meta: { requiresAuth: false } },
  { path: '/change-password', component: ChangePasswordPage, meta: { requiresAuth: true } },
  { path: '/', redirect: '/devices', meta: { requiresAuth: true } },
  { path: '/device-types', component: DeviceTypesPage, meta: { requiresAuth: true } },
  { path: '/devices', component: DevicesPage, meta: { requiresAuth: true } },
  { path: '/imports', component: ImportsPage, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/dial-plans', component: DialPlansPage, meta: { requiresAuth: true } },
  { path: '/sip-servers', component: SIPServersPage, meta: { requiresAuth: true } },
  { path: '/sites', component: SitesPage, meta: { requiresAuth: true } },
  { path: '/lines', component: LinesPage, meta: { requiresAuth: true } },
  { path: '/users', component: UsersPage, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/settings', component: UserSettingsPage, meta: { requiresAuth: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Navigation guard to check authentication
// Check localStorage directly to avoid Pinia initialization issues
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token');
  const userStr = localStorage.getItem('auth_user');
  const user = userStr ? JSON.parse(userStr) : null;
  const isAuthenticated = !!token;
  const requiresAuth = to.meta.requiresAuth !== false;
  const requiresAdmin = to.meta.requiresAdmin === true;

  if (requiresAuth && !isAuthenticated) {
    // Redirect to login if not authenticated
    next('/login');
  } else if (to.path === '/login' && isAuthenticated) {
    // Redirect to home if already authenticated and trying to access login
    next('/devices');
  } else if (requiresAdmin && user?.role !== 'admin') {
    // Redirect non-admin users away from admin-only pages
    next('/device-types');
  } else {
    next();
  }
});

export default router;
