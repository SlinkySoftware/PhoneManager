import { createRouter, createWebHistory } from 'vue-router';
import DeviceTypesPage from '../pages/DeviceTypesPage.vue';
import DevicesPage from '../pages/DevicesPage.vue';
import SIPServersPage from '../pages/SIPServersPage.vue';
import SitesPage from '../pages/SitesPage.vue';
import LinesPage from '../pages/LinesPage.vue';

const routes = [
  { path: '/', redirect: '/device-types' },
  { path: '/device-types', component: DeviceTypesPage },
  { path: '/devices', component: DevicesPage },
  { path: '/sip-servers', component: SIPServersPage },
  { path: '/sites', component: SitesPage },
  { path: '/lines', component: LinesPage }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
