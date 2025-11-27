import { createRouter, createWebHistory } from 'vue-router';

// Import views
import DashboardView from '@/views/DashboardView.vue';
import AnalysisWizardView from '@/views/AnalysisWizardView.vue';
import ReportsView from '@/views/ReportsView.vue';
import RoundtableView from '@/views/RoundtableView.vue';
import AgentsView from '@/views/AgentsView.vue';
import KnowledgeView from '@/views/KnowledgeView.vue';
import SettingsView from '@/views/SettingsView.vue';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: DashboardView
  },
  {
    path: '/analysis',
    name: 'AnalysisWizard',
    component: AnalysisWizardView
  },
  {
    path: '/reports',
    name: 'ReportsView',
    component: ReportsView
  },
  {
    path: '/roundtable',
    name: 'Roundtable',
    component: RoundtableView
  },
  {
    path: '/agents',
    name: 'Agents',
    component: AgentsView
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: KnowledgeView
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView
  },
  // Fallback
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
