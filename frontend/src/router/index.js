import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

// Import layouts
import AuthenticatedLayout from '@/components/layout/AuthenticatedLayout.vue';

// Route-level lazy loading improves mobile first-load performance.
const ChatHubView = () => import('@/views/ChatHubView.vue');
const AnalysisWizardView = () => import('@/views/AnalysisWizardView.vue');
const ReportsView = () => import('@/views/ReportsView.vue');
const RoundtableView = () => import('@/views/RoundtableView.vue');
const AgentsView = () => import('@/views/AgentsView.vue');
const KnowledgeView = () => import('@/views/KnowledgeView.vue');
const SettingsView = () => import('@/views/SettingsView.vue');
const AutoTradingView = () => import('@/views/AutoTradingView.vue');
const LoginView = () => import('@/views/LoginView.vue');
const RegisterView = () => import('@/views/RegisterView.vue');

const routes = [
  // Public routes (no authentication required)
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { public: true, guestOnly: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterView,
    meta: { public: true, guestOnly: true }
  },

  // Protected routes (authentication required) - nested under AuthenticatedLayout
  {
    path: '/',
    component: AuthenticatedLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'ChatHub',
        component: ChatHubView
      },
      {
        path: 'analysis',
        name: 'AnalysisWizard',
        component: AnalysisWizardView
      },
      {
        path: 'reports',
        name: 'ReportsView',
        component: ReportsView
      },
      {
        path: 'roundtable',
        name: 'Roundtable',
        component: RoundtableView
      },
      {
        path: 'agents',
        name: 'Agents',
        component: AgentsView
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: KnowledgeView
      },
      {
        path: 'settings',
        name: 'Settings',
        component: SettingsView
      },
      {
        path: 'trading',
        name: 'AutoTrading',
        component: AutoTradingView
      }
    ]
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

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  const isAuthenticated = authStore.isAuthenticated;

  // Check if any matched route requires auth (handles nested routes)
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const guestOnly = to.matched.some(record => record.meta.guestOnly);

  // If route requires auth and user is not authenticated
  if (requiresAuth && !isAuthenticated) {
    // Try to restore session from token
    const token = localStorage.getItem('access_token');
    if (token) {
      // Try to fetch current user
      const success = await authStore.fetchCurrentUser();
      if (success) {
        return next();
      }
    }

    // Redirect to login with return URL
    return next({
      name: 'Login',
      query: { redirect: to.fullPath }
    });
  }

  // If route is for guests only and user is authenticated
  if (guestOnly && isAuthenticated) {
    return next({ name: 'ChatHub' });
  }

  next();
});

export default router;
