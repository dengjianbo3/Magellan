<template>
  <div class="page-shell h-full min-h-0 overflow-y-auto">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title page-title-gradient">{{ t('settings.title') }}</h1>
        <p class="page-subtitle">{{ t('settings.subtitle') }}</p>
      </div>
    </div>

    <!-- Settings Sections -->
    <div class="grid grid-cols-1 gap-4 md:gap-6 lg:grid-cols-4 lg:gap-8">
      <!-- Settings Navigation -->
      <div class="lg:col-span-1">
        <div class="glass-panel rounded-2xl p-2.5 md:p-4 lg:sticky lg:top-6">
          <nav class="flex gap-2 overflow-x-auto pb-1 lg:block lg:space-y-2 lg:overflow-visible lg:pb-0">
            <button
              v-for="section in sections"
              :key="section.id"
              @click="activeSection = section.id"
              :class="[
                'flex flex-shrink-0 items-center gap-2.5 rounded-xl px-3 py-2.5 text-left transition-all duration-300 group lg:w-full lg:gap-4 lg:px-4 lg:py-3',
                activeSection === section.id
                  ? 'bg-primary/10 text-primary shadow-[0_0_15px_rgba(56,189,248,0.15)]'
                  : 'text-text-secondary hover:bg-white/5 hover:text-white'
              ]"
            >
              <span class="material-symbols-outlined text-lg transition-transform group-hover:scale-110 lg:text-xl">{{ section.icon }}</span>
              <span class="text-xs font-bold whitespace-nowrap lg:text-sm">{{ section.name }}</span>
            </button>
          </nav>
        </div>
      </div>

      <!-- Settings Content -->
      <div class="space-y-4 md:space-y-6 lg:col-span-3">
        <!-- Profile Settings -->
        <div v-if="activeSection === 'profile'" class="glass-panel rounded-2xl p-4 md:p-6 lg:p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-6 pb-4 border-b border-white/10 md:mb-8">{{ t('settings.sections.profile') }}</h2>
          <div class="space-y-6 md:space-y-8">
            <div class="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:gap-8">
              <div class="relative group cursor-pointer">
                <div class="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-3xl font-bold text-white shadow-glow">
                  {{ userProfile.name ? userProfile.name.slice(0, 2).toUpperCase() : 'U' }}
                </div>
                <div class="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                   <span class="material-symbols-outlined text-white">edit</span>
                </div>
              </div>
              <div>
                <h3 class="text-lg font-bold text-white">{{ userProfile.name || 'User' }}</h3>
                <p class="text-text-secondary text-sm mb-3">{{ userProfile.role === 'admin' ? 'Administrator' : 'Investment Analyst' }}</p>
                <div class="flex items-center gap-2">
                  <button @click="showAvatarChangeInfo" class="px-4 py-2 rounded-lg border border-white/10 text-text-primary hover:bg-white/5 transition-colors text-sm font-bold">
                    {{ t('settings.profile.changeAvatar') }}
                  </button>
                  <button @click="logoutFromSettings" class="px-4 py-2 rounded-lg border border-rose-500/35 text-rose-300 hover:bg-rose-500/15 transition-colors text-sm font-bold flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-base">logout</span>
                    {{ t('common.logout') || 'Logout' }}
                  </button>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-6">
              <div>
                <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.profile.name') || 'Full Name' }}</label>
                <input
                  v-model="userProfile.name"
                  type="text"
                  :placeholder="t('settings.profile.namePlaceholder') || 'Enter your name'"
                  class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                />
              </div>
              <div>
                <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.profile.organization') || 'Organization' }}</label>
                <input
                  v-model="userProfile.organization"
                  type="text"
                  :placeholder="t('settings.profile.organizationPlaceholder') || 'Company name'"
                  class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                />
              </div>
            </div>

            <div>
              <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.profile.email') }}</label>
              <input
                :value="userProfile.email"
                type="email"
                disabled
                class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-text-secondary focus:outline-none cursor-not-allowed"
              />
              <p class="text-xs text-text-secondary mt-1">{{ t('settings.profile.emailHint') || 'Email cannot be changed' }}</p>
            </div>

            <div class="pt-6 border-t border-white/10 flex justify-end">
              <button
                @click="saveProfile"
                :disabled="profileSaving"
                class="px-8 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-bold shadow-glow-sm hover:shadow-glow transition-all disabled:opacity-50"
              >
                <span v-if="profileSaving" class="flex items-center gap-2">
                  <span class="material-symbols-outlined animate-spin text-lg">progress_activity</span>
                  Saving...
                </span>
                <span v-else>{{ t('settings.profile.saveChanges') }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Notification Settings -->
        <div v-if="activeSection === 'notifications'" class="glass-panel rounded-2xl p-4 md:p-6 lg:p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-6 pb-4 border-b border-white/10 md:mb-8">{{ t('settings.sections.notifications') }}</h2>
          <div class="space-y-4">
            <div class="flex items-center justify-between p-5 rounded-xl bg-white/5 border border-white/5">
              <div>
                <p class="font-bold text-white mb-1">{{ t('settings.notifications.analysisComplete.title') }}</p>
                <p class="text-sm text-text-secondary">{{ t('settings.notifications.analysisComplete.description') }}</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="notifications.analysisComplete" @change="saveNotificationPrefs" class="sr-only peer">
                <div class="w-14 h-7 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-5 rounded-xl bg-white/5 border border-white/5">
              <div>
                <p class="font-bold text-white mb-1">{{ t('settings.notifications.agentUpdates.title') }}</p>
                <p class="text-sm text-text-secondary">{{ t('settings.notifications.agentUpdates.description') }}</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="notifications.agentUpdates" @change="saveNotificationPrefs" class="sr-only peer">
                 <div class="w-14 h-7 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-5 rounded-xl bg-white/5 border border-white/5">
              <div>
                <p class="font-bold text-white mb-1">{{ t('settings.notifications.emailNotifications.title') }}</p>
                <p class="text-sm text-text-secondary">{{ t('settings.notifications.emailNotifications.description') }}</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="notifications.emailNotifications" @change="saveNotificationPrefs" class="sr-only peer">
                 <div class="w-14 h-7 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>
          </div>
        </div>

        <!-- Security Settings -->
        <div v-if="activeSection === 'security'" class="glass-panel rounded-2xl p-4 md:p-6 lg:p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-6 pb-4 border-b border-white/10 md:mb-8">{{ t('settings.sections.security') }}</h2>
          <div class="space-y-8">
            <div>
              <h3 class="font-bold text-primary mb-4 text-sm uppercase tracking-wider">{{ t('settings.security.changePassword') }}</h3>
              <div class="space-y-4">
                <div>
                  <label class="block text-xs font-bold text-text-secondary mb-2 uppercase">{{ t('settings.security.currentPassword') }}</label>
                  <input
                    v-model="passwordForm.currentPassword"
                    type="password"
                    class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                  />
                </div>
                <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                        <label class="block text-xs font-bold text-text-secondary mb-2 uppercase">{{ t('settings.security.newPassword') }}</label>
                        <input
                            v-model="passwordForm.newPassword"
                            type="password"
                            class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                        />
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-text-secondary mb-2 uppercase">{{ t('settings.security.confirmPassword') }}</label>
                        <input
                            v-model="passwordForm.confirmPassword"
                            type="password"
                            class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                        />
                    </div>
                </div>
                <div class="flex justify-end pt-2">
                     <button
                        @click="changePassword"
                        :disabled="passwordSaving || !passwordForm.currentPassword || !passwordForm.newPassword"
                        class="px-6 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                     >
                        <span v-if="passwordSaving" class="flex items-center gap-2">
                          <span class="material-symbols-outlined animate-spin text-lg">progress_activity</span>
                          Updating...
                        </span>
                        <span v-else>{{ t('settings.security.updatePassword') }}</span>
                     </button>
                </div>
              </div>
            </div>

            <div class="pt-6 border-t border-white/10">
              <h3 class="font-bold text-primary mb-4 text-sm uppercase tracking-wider">{{ t('settings.security.twoFactorAuth') }}</h3>
              <div class="flex items-center justify-between p-5 rounded-xl bg-white/5 border border-white/5">
                <div>
                  <p class="font-bold text-white mb-1">{{ t('settings.security.enable2FA.title') }}</p>
                  <p class="text-sm text-text-secondary">{{ t('settings.security.enable2FA.description') }}</p>
                </div>
                <button @click="showEnable2FAInfo" class="px-4 py-2 rounded-lg border border-primary/30 text-primary hover:bg-primary/10 transition-colors text-sm font-bold">
                  {{ t('settings.security.enable2FA.button') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- AI Model Settings -->
        <div v-if="activeSection === 'api'" class="glass-panel rounded-2xl p-4 md:p-6 lg:p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-6 pb-4 border-b border-white/10 md:mb-8">{{ t('settings.api.title') }}</h2>
          <div class="space-y-6">
            <div class="p-5 rounded-xl bg-white/5 border border-white/5">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="font-bold text-white mb-1">{{ t('settings.api.useProLabel') }}</p>
                  <p class="text-sm text-text-secondary">{{ t('settings.api.useProDesc') }}</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  :aria-checked="llmUsePro ? 'true' : 'false'"
                  :disabled="llmSaving"
                  class="relative inline-flex h-7 w-14 items-center rounded-full bg-black/40 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                  :class="llmUsePro ? 'bg-primary' : 'bg-black/40'"
                  @click="toggleLlmPreference"
                >
                  <span
                    class="absolute top-[2px] left-[2px] h-6 w-6 rounded-full border border-gray-300 bg-white transition-transform"
                    :class="llmUsePro ? 'translate-x-7 border-white' : 'translate-x-0'"
                  ></span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Membership Plans -->
        <div v-if="activeSection === 'plans'" class="glass-panel rounded-2xl p-4 md:p-6 lg:p-8 animate-fade-in">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-xl font-bold text-white">{{ t('settings.pricing.title') }}</h2>
            <span class="px-3 py-1 rounded-full text-xs font-bold bg-primary/20 text-primary border border-primary/30">
              {{ t('settings.pricing.demoBadge') }}
            </span>
          </div>
          <p class="text-text-secondary mb-6 md:mb-8">{{ t('settings.pricing.subtitle') }}</p>

          <div class="grid grid-cols-1 xl:grid-cols-3 gap-5">
            <article
              v-for="plan in demoPlans"
              :key="plan.id"
              :class="[
                'rounded-2xl p-5 transition-all duration-300',
                plan.highlight
                  ? 'bg-primary/10 border border-primary/40 shadow-[0_0_20px_rgba(56,189,248,0.12)]'
                  : 'bg-white/5 border border-white/10'
              ]"
            >
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-base font-bold text-white">{{ plan.name }}</h3>
                <span
                  v-if="plan.highlight"
                  class="px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-primary/20 text-primary"
                >
                  {{ t('settings.pricing.recommended') }}
                </span>
              </div>
              <p class="text-2xl font-extrabold text-white mb-1">{{ plan.price }}</p>
              <p class="text-sm text-text-secondary mb-4">{{ plan.description }}</p>
              <ul class="space-y-2">
                <li
                  v-for="feature in plan.features"
                  :key="feature"
                  class="text-sm text-text-primary flex items-start gap-2"
                >
                  <span class="material-symbols-outlined text-base text-primary mt-0.5">check_circle</span>
                  <span>{{ feature }}</span>
                </li>
              </ul>
            </article>
          </div>
        </div>

        <!-- Language Settings -->
        <div v-if="activeSection === 'language'" class="glass-panel rounded-2xl p-4 md:p-6 lg:p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-6 pb-4 border-b border-white/10 md:mb-8">{{ t('settings.language.title') }}</h2>
          <div class="space-y-8">
            <div>
              <label class="block text-sm font-bold text-text-secondary mb-4 uppercase tracking-wider">{{ t('settings.language.label') }}</label>
              <div class="relative max-w-lg">
                <select
                  :value="locale"
                  @change="handleLanguageChange($event.target.value)"
                  class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all appearance-none cursor-pointer"
                >
                  <option value="zh-CN">{{ t('settings.language.languages.zhCN') }}</option>
                  <option value="en">{{ t('settings.language.languages.en') }}</option>
                </select>
                <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">expand_more</span>
              </div>
              <p class="text-xs text-text-secondary mt-2 ml-1 flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">info</span>
                {{ t('settings.language.switchHint') }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useLanguage } from '../composables/useLanguage';
import { useToast } from '../composables/useToast';
import { AUTH_BASE, llmUrl } from '@/config/api';
import { readJsonResponse } from '@/services/httpResponse';

const { t, locale, setLocale } = useLanguage();
const { success, error: showError, info } = useToast();
const router = useRouter();
const authStore = useAuthStore();

// Show avatar change info (feature coming soon)
const showAvatarChangeInfo = () => {
  info(t('settings.profile.avatarComingSoon') || 'Avatar upload coming soon');
};

// Show 2FA enable info (feature coming soon)
const showEnable2FAInfo = () => {
  info(t('settings.security.2faComingSoon') || 'Two-factor authentication setup coming soon');
};

const activeSection = ref('profile');

// User profile state
const userProfile = ref({
  name: '',
  email: '',
  organization: '',
  role: 'analyst'
});
const profileLoading = ref(false);
const profileSaving = ref(false);

// Password state
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
});
const passwordSaving = ref(false);

// Notification preferences (stored in localStorage)
const notifications = ref({
  analysisComplete: true,
  agentUpdates: true,
  emailNotifications: true
});

// LLM model tier preference (Gemini Pro/Flash)
const LLM_USE_PRO_STORAGE_KEY = 'magellan_llm_use_pro_v1';
const llmUsePro = ref(true);
const llmCurrentModel = ref('gemini-3.1-pro-preview');
const llmLoading = ref(false);
const llmSaving = ref(false);
const LLM_REQUEST_TIMEOUT_MS = 8000;

const sections = computed(() => [
  { id: 'profile', name: t('settings.sections.profile'), icon: 'person' },
  { id: 'notifications', name: t('settings.sections.notifications'), icon: 'notifications' },
  { id: 'security', name: t('settings.sections.security'), icon: 'lock' },
  { id: 'api', name: t('settings.api.title'), icon: 'tune' },
  { id: 'plans', name: t('settings.sections.plans'), icon: 'workspace_premium' },
  { id: 'language', name: t('settings.sections.language'), icon: 'translate' }
]);

const demoPlans = computed(() => [
  {
    id: 'free',
    name: t('settings.pricing.plans.free.name'),
    price: t('settings.pricing.plans.free.price'),
    description: t('settings.pricing.plans.free.description'),
    features: [
      t('settings.pricing.plans.free.features.0'),
      t('settings.pricing.plans.free.features.1'),
      t('settings.pricing.plans.free.features.2')
    ],
    highlight: false
  },
  {
    id: 'pro',
    name: t('settings.pricing.plans.pro.name'),
    price: t('settings.pricing.plans.pro.price'),
    description: t('settings.pricing.plans.pro.description'),
    features: [
      t('settings.pricing.plans.pro.features.0'),
      t('settings.pricing.plans.pro.features.1'),
      t('settings.pricing.plans.pro.features.2')
    ],
    highlight: true
  },
  {
    id: 'urtal',
    name: t('settings.pricing.plans.urtal.name'),
    price: t('settings.pricing.plans.urtal.price'),
    description: t('settings.pricing.plans.urtal.description'),
    features: [
      t('settings.pricing.plans.urtal.features.0'),
      t('settings.pricing.plans.urtal.features.1'),
      t('settings.pricing.plans.urtal.features.2')
    ],
    highlight: false
  }
]);

// Get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('access_token') || '';
};

// Fetch user profile from auth service
const fetchProfile = async () => {
  const token = getAuthToken();
  if (!token) {
    console.log('[Settings] No auth token, using demo data');
    userProfile.value = {
      name: 'Zhang Wei',
      email: 'zhang.wei@example.com',
      organization: 'Investment Corp',
      role: 'analyst'
    };
    return;
  }

  profileLoading.value = true;
  try {
    const response = await fetch(`${AUTH_BASE}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    const data = await readJsonResponse(response, 'Fetch profile');
    userProfile.value = {
      name: data.name || '',
      email: data.email || '',
      organization: data.organization || '',
      role: data.role || 'analyst'
    };
  } catch (err) {
    console.error('[Settings] Error fetching profile:', err);
  } finally {
    profileLoading.value = false;
  }
};

// Save user profile
const saveProfile = async () => {
  const token = getAuthToken();
  if (!token) {
    showError('Please login to update profile');
    return;
  }

  profileSaving.value = true;
  try {
    const response = await fetch(`${AUTH_BASE}/api/auth/me`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: userProfile.value.name,
        organization: userProfile.value.organization
      })
    });
    await readJsonResponse(response, 'Update profile');
    success('Profile updated successfully');
  } catch (err) {
    console.error('[Settings] Error saving profile:', err);
    showError(err.message || 'Failed to update profile');
  } finally {
    profileSaving.value = false;
  }
};

// Change password
const changePassword = async () => {
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    showError('New passwords do not match');
    return;
  }

  const token = getAuthToken();
  if (!token) {
    showError('Please login to change password');
    return;
  }

  passwordSaving.value = true;
  try {
    const response = await fetch(`${AUTH_BASE}/api/auth/password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        current_password: passwordForm.value.currentPassword,
        new_password: passwordForm.value.newPassword
      })
    });
    await readJsonResponse(response, 'Change password');
    success('Password changed successfully');
    passwordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' };
  } catch (err) {
    console.error('[Settings] Error changing password:', err);
    showError(err.message || 'Failed to change password');
  } finally {
    passwordSaving.value = false;
  }
};

// Load notification preferences from localStorage
const loadNotificationPrefs = () => {
  const saved = localStorage.getItem('notification_prefs');
  if (saved) {
    try {
      notifications.value = JSON.parse(saved);
    } catch (e) {
      console.error('Failed to load notification prefs:', e);
    }
  }
};

// Save notification preferences to localStorage
const saveNotificationPrefs = () => {
  localStorage.setItem('notification_prefs', JSON.stringify(notifications.value));
};

const loadLlmPreference = async () => {
  const localRaw = localStorage.getItem(LLM_USE_PRO_STORAGE_KEY);
  if (localRaw === '0' || localRaw === '1') {
    llmUsePro.value = localRaw === '1';
  }

  llmLoading.value = true;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), LLM_REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(llmUrl('/gemini/model-tier'), { signal: controller.signal });
    const data = await readJsonResponse(response, 'Get Gemini model tier');

    if (typeof data?.use_pro === 'boolean') {
      llmUsePro.value = data.use_pro;
      localStorage.setItem(LLM_USE_PRO_STORAGE_KEY, llmUsePro.value ? '1' : '0');
    }
    if (data?.model) {
      llmCurrentModel.value = data.model;
    }
  } catch (err) {
    if (err?.name === 'AbortError') {
      console.warn('[Settings] Load Gemini model tier timeout');
    } else {
      console.warn('[Settings] Failed to load Gemini model tier:', err);
    }
  } finally {
    clearTimeout(timeoutId);
    llmLoading.value = false;
  }
};

const updateLlmPreference = async (nextValue, prevValue) => {
  llmSaving.value = true;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), LLM_REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(llmUrl('/gemini/model-tier'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ use_pro: nextValue }),
      signal: controller.signal
    });
    const data = await readJsonResponse(response, 'Set Gemini model tier');

    llmUsePro.value = typeof data?.use_pro === 'boolean' ? data.use_pro : nextValue;
    llmCurrentModel.value = data?.model || (llmUsePro.value ? 'gemini-3.1-pro-preview' : 'gemini-3-flash-preview');
    localStorage.setItem(LLM_USE_PRO_STORAGE_KEY, llmUsePro.value ? '1' : '0');
    success(t('settings.api.modelSwitchSuccess'));
  } catch (err) {
    console.error('[Settings] Failed to switch Gemini model tier:', err);
    llmUsePro.value = prevValue;
    localStorage.setItem(LLM_USE_PRO_STORAGE_KEY, prevValue ? '1' : '0');
    showError(t('settings.api.modelSwitchError', { error: err?.message || 'unknown error' }));
  } finally {
    clearTimeout(timeoutId);
    llmSaving.value = false;
  }
};

const toggleLlmPreference = async () => {
  if (llmSaving.value) return;
  const prevValue = llmUsePro.value;
  const nextValue = !prevValue;
  llmUsePro.value = nextValue;
  await updateLlmPreference(nextValue, prevValue);
};

const handleLanguageChange = (lang) => {
  setLocale(lang);
};

const logoutFromSettings = async () => {
  try {
    await authStore.logout();
    router.push({ name: 'Login' });
  } catch (err) {
    showError(err?.message || (t('common.logout') || 'Logout') + ' failed');
  }
};

// Fetch profile on mount
onMounted(() => {
  fetchProfile();
  loadNotificationPrefs();
  loadLlmPreference();
});
</script>
