import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '../pages/LoginPage.vue';
import DeviceTypesPage from '../pages/DeviceTypesPage.vue';
import DevicesPage from '../pages/DevicesPage.vue';
import SIPServersPage from '../pages/SIPServersPage.vue';
import SitesPage from '../pages/SitesPage.vue';
import LinesPage from '../pages/LinesPage.vue';

const routes = [
  { path: '/login', component: LoginPage, meta: { requiresAuth: false } },
  { path: '/', redirect: '/device-types', meta: { requiresAuth: true } },
  { path: '/device-types', component: DeviceTypesPage, meta: { requiresAuth: true } },
  { path: '/devices', component: DevicesPage, meta: { requiresAuth: true } },
  { path: '/sip-servers', component: SIPServersPage, meta: { requiresAuth: true } },
  { path: '/sites', component: SitesPage, meta: { requiresAuth: true } },
  { path: '/lines', component: LinesPage, meta: { requiresAuth: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Navigation guard to check authentication
// Check localStorage directly to avoid Pinia initialization issues
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token');
  const isAuthenticated = !!token;
  const requiresAuth = to.meta.requiresAuth !== false;

  if (requiresAuth && !isAuthenticated) {
    // Redirect to login if not authenticated
    next('/login');
  } else if (to.path === '/login' && isAuthenticated) {
    // Redirect to home if already authenticated and trying to access login
    next('/device-types');
  } else {
    next();
  }
});

export default router;
