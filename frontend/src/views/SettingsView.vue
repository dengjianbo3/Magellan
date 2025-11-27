<template>
  <div class="max-w-6xl mx-auto space-y-8">
    <!-- Page Header -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-display font-bold text-white mb-2 tracking-tight">{{ t('settings.title') }}</h1>
        <p class="text-text-secondary text-lg">{{ t('settings.subtitle') }}</p>
      </div>
    </div>

    <!-- Settings Sections -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
      <!-- Settings Navigation -->
      <div class="lg:col-span-1">
        <div class="glass-panel rounded-2xl p-4 sticky top-6">
          <nav class="space-y-2">
            <button
              v-for="section in sections"
              :key="section.id"
              @click="activeSection = section.id"
              :class="[
                'w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 text-left group',
                activeSection === section.id
                  ? 'bg-primary/10 text-primary shadow-[0_0_15px_rgba(56,189,248,0.15)]'
                  : 'text-text-secondary hover:bg-white/5 hover:text-white'
              ]"
            >
              <span class="material-symbols-outlined text-xl group-hover:scale-110 transition-transform">{{ section.icon }}</span>
              <span class="text-sm font-bold">{{ section.name }}</span>
            </button>
          </nav>
        </div>
      </div>

      <!-- Settings Content -->
      <div class="lg:col-span-3 space-y-6">
        <!-- Profile Settings -->
        <div v-if="activeSection === 'profile'" class="glass-panel rounded-2xl p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-8 pb-4 border-b border-white/10">{{ t('settings.sections.profile') }}</h2>
          <div class="space-y-8">
            <div class="flex items-center gap-8">
              <div class="relative group cursor-pointer">
                <div class="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-3xl font-bold text-white shadow-glow">
                  ZW
                </div>
                <div class="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                   <span class="material-symbols-outlined text-white">edit</span>
                </div>
              </div>
              <div>
                <h3 class="text-lg font-bold text-white">Zhang Wei</h3>
                <p class="text-text-secondary text-sm mb-3">Investment Analyst</p>
                <button class="px-4 py-2 rounded-lg border border-white/10 text-text-primary hover:bg-white/5 transition-colors text-sm font-bold">
                  {{ t('settings.profile.changeAvatar') }}
                </button>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.profile.firstName') }}</label>
                <input
                  type="text"
                  value="伟"
                  class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                />
              </div>
              <div>
                <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.profile.lastName') }}</label>
                <input
                  type="text"
                  value="张"
                  class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                />
              </div>
            </div>

            <div>
              <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.profile.email') }}</label>
              <input
                type="email"
                value="zhang.wei@example.com"
                class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
              />
            </div>

            <div class="pt-6 border-t border-white/10 flex justify-end">
              <button class="px-8 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-bold shadow-glow-sm hover:shadow-glow transition-all">
                {{ t('settings.profile.saveChanges') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Notification Settings -->
        <div v-if="activeSection === 'notifications'" class="glass-panel rounded-2xl p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-8 pb-4 border-b border-white/10">{{ t('settings.sections.notifications') }}</h2>
          <div class="space-y-4">
            <div class="flex items-center justify-between p-5 rounded-xl bg-white/5 border border-white/5">
              <div>
                <p class="font-bold text-white mb-1">{{ t('settings.notifications.analysisComplete.title') }}</p>
                <p class="text-sm text-text-secondary">{{ t('settings.notifications.analysisComplete.description') }}</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked class="sr-only peer">
                <div class="w-14 h-7 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-5 rounded-xl bg-white/5 border border-white/5">
              <div>
                <p class="font-bold text-white mb-1">{{ t('settings.notifications.agentUpdates.title') }}</p>
                <p class="text-sm text-text-secondary">{{ t('settings.notifications.agentUpdates.description') }}</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked class="sr-only peer">
                 <div class="w-14 h-7 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-5 rounded-xl bg-white/5 border border-white/5">
              <div>
                <p class="font-bold text-white mb-1">{{ t('settings.notifications.emailNotifications.title') }}</p>
                <p class="text-sm text-text-secondary">{{ t('settings.notifications.emailNotifications.description') }}</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked class="sr-only peer">
                 <div class="w-14 h-7 bg-black/40 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>
          </div>
        </div>

        <!-- Security Settings -->
        <div v-if="activeSection === 'security'" class="glass-panel rounded-2xl p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-8 pb-4 border-b border-white/10">{{ t('settings.sections.security') }}</h2>
          <div class="space-y-8">
            <div>
              <h3 class="font-bold text-primary mb-4 text-sm uppercase tracking-wider">{{ t('settings.security.changePassword') }}</h3>
              <div class="space-y-4">
                <div>
                  <label class="block text-xs font-bold text-text-secondary mb-2 uppercase">{{ t('settings.security.currentPassword') }}</label>
                  <input
                    type="password"
                    class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                  />
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-text-secondary mb-2 uppercase">{{ t('settings.security.newPassword') }}</label>
                        <input
                            type="password"
                            class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                        />
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-text-secondary mb-2 uppercase">{{ t('settings.security.confirmPassword') }}</label>
                        <input
                            type="password"
                            class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
                        />
                    </div>
                </div>
                <div class="flex justify-end pt-2">
                     <button class="px-6 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-bold transition-colors">
                        {{ t('settings.security.updatePassword') }}
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
                <button class="px-4 py-2 rounded-lg border border-primary/30 text-primary hover:bg-primary/10 transition-colors text-sm font-bold">
                  {{ t('settings.security.enable2FA.button') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- API Settings (LLM Provider) -->
        <div v-if="activeSection === 'api'" class="glass-panel rounded-2xl p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-8 pb-4 border-b border-white/10">{{ t('settings.api.title') }}</h2>
          <div class="space-y-6">
            <!-- LLM Provider Selection -->
            <div>
              <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.api.llmProvider') }}</label>
              <p class="text-sm text-text-secondary mb-4">{{ t('settings.api.llmProviderDesc') }}</p>

              <!-- Provider Cards -->
              <div class="grid grid-cols-2 gap-4">
                <!-- Gemini Provider -->
                <button
                  @click="switchProvider('gemini')"
                  :disabled="providerSwitching || !providers.gemini?.available"
                  :class="[
                    'p-5 rounded-xl border-2 transition-all text-left relative overflow-hidden group',
                    currentProvider === 'gemini'
                      ? 'border-primary bg-primary/10 shadow-glow-sm'
                      : providers.gemini?.available
                        ? 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                        : 'border-white/5 bg-white/5 opacity-50 cursor-not-allowed'
                  ]"
                >
                  <!-- Selected indicator -->
                  <div v-if="currentProvider === 'gemini'" class="absolute top-3 right-3">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>

                  <!-- Provider logo/icon -->
                  <div class="flex items-center gap-3 mb-3">
                    <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <span class="text-white font-bold text-lg">G</span>
                    </div>
                    <div>
                      <h3 class="font-bold text-white">{{ t('settings.api.providers.gemini') }}</h3>
                      <p class="text-xs text-text-secondary">{{ providers.gemini?.model || 'gemini-3-pro-preview' }}</p>
                    </div>
                  </div>

                  <!-- Status -->
                  <div class="flex items-center gap-2">
                    <span :class="['w-2 h-2 rounded-full', providers.gemini?.available ? 'bg-green-500' : 'bg-red-500']"></span>
                    <span class="text-xs text-text-secondary">
                      {{ providers.gemini?.available ? t('settings.api.available') : t('settings.api.unavailable') }}
                    </span>
                  </div>
                </button>

                <!-- Kimi Provider -->
                <button
                  @click="switchProvider('kimi')"
                  :disabled="providerSwitching || !providers.kimi?.available"
                  :class="[
                    'p-5 rounded-xl border-2 transition-all text-left relative overflow-hidden group',
                    currentProvider === 'kimi'
                      ? 'border-primary bg-primary/10 shadow-glow-sm'
                      : providers.kimi?.available
                        ? 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                        : 'border-white/5 bg-white/5 opacity-50 cursor-not-allowed'
                  ]"
                >
                  <!-- Selected indicator -->
                  <div v-if="currentProvider === 'kimi'" class="absolute top-3 right-3">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>

                  <!-- Provider logo/icon -->
                  <div class="flex items-center gap-3 mb-3">
                    <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center">
                      <span class="text-white font-bold text-lg">K</span>
                    </div>
                    <div>
                      <h3 class="font-bold text-white">{{ t('settings.api.providers.kimi') }}</h3>
                      <p class="text-xs text-text-secondary">{{ providers.kimi?.model || 'kimi-k2-0711-preview' }}</p>
                    </div>
                  </div>

                  <!-- Status -->
                  <div class="flex items-center gap-2">
                    <span :class="['w-2 h-2 rounded-full', providers.kimi?.available ? 'bg-green-500' : 'bg-red-500']"></span>
                    <span class="text-xs text-text-secondary">
                      {{ providers.kimi?.available ? t('settings.api.available') : t('settings.api.unavailable') }}
                    </span>
                  </div>
                </button>
              </div>

              <!-- Switching indicator -->
              <div v-if="providerSwitching" class="mt-4 flex items-center gap-2 text-primary">
                <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span class="text-sm">{{ t('settings.api.switching') }}</span>
              </div>

              <!-- Error message -->
              <div v-if="providerError" class="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {{ providerError }}
              </div>
            </div>

            <!-- Current Provider Info -->
            <div class="pt-6 border-t border-white/10">
              <h3 class="font-bold text-primary mb-4 text-sm uppercase tracking-wider">{{ t('settings.api.currentModel') }}</h3>
              <div class="p-5 rounded-xl bg-black/20 border border-white/5">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <div :class="['w-8 h-8 rounded-lg flex items-center justify-center',
                      currentProvider === 'gemini'
                        ? 'bg-gradient-to-br from-blue-500 to-purple-600'
                        : 'bg-gradient-to-br from-orange-500 to-red-600']">
                      <span class="text-white font-bold">{{ currentProvider === 'gemini' ? 'G' : 'K' }}</span>
                    </div>
                    <div>
                      <p class="font-bold text-white">{{ currentProvider === 'gemini' ? t('settings.api.providers.gemini') : t('settings.api.providers.kimi') }}</p>
                      <p class="text-xs text-text-secondary font-mono">{{ providers[currentProvider]?.model || '-' }}</p>
                    </div>
                  </div>
                  <span class="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-bold">Active</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Appearance Settings -->
        <div v-if="activeSection === 'appearance'" class="glass-panel rounded-2xl p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-8 pb-4 border-b border-white/10">{{ t('settings.appearance.title') }}</h2>
          <div class="space-y-8">
            <div>
              <label class="block text-sm font-bold text-text-secondary mb-4 uppercase tracking-wider">{{ t('settings.appearance.theme') }}</label>
              <div class="grid grid-cols-3 gap-4">
                <button class="p-4 rounded-xl border-2 border-white/5 bg-white/5 hover:border-white/20 transition-all group">
                  <div class="w-full h-24 rounded-lg bg-gray-200 mb-4 group-hover:scale-105 transition-transform"></div>
                  <p class="text-sm font-bold text-text-secondary group-hover:text-white">{{ t('settings.appearance.themes.light') }}</p>
                </button>
                <button class="p-4 rounded-xl border-2 border-primary bg-primary/10 shadow-glow-sm transition-all">
                  <div class="w-full h-24 rounded-lg bg-[#0b0f19] border border-white/10 mb-4 relative overflow-hidden">
                      <div class="absolute top-2 left-2 w-16 h-2 bg-white/10 rounded"></div>
                      <div class="absolute top-6 left-2 w-8 h-16 bg-primary/20 rounded"></div>
                  </div>
                  <p class="text-sm font-bold text-primary">{{ t('settings.appearance.themes.dark') }}</p>
                </button>
                <button class="p-4 rounded-xl border-2 border-white/5 bg-white/5 hover:border-white/20 transition-all group">
                  <div class="w-full h-24 rounded-lg bg-gradient-to-br from-gray-800 to-gray-200 mb-4 group-hover:scale-105 transition-transform"></div>
                  <p class="text-sm font-bold text-text-secondary group-hover:text-white">{{ t('settings.appearance.themes.auto') }}</p>
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm font-bold text-text-secondary mb-4 uppercase tracking-wider">{{ t('settings.appearance.language') }}</label>
              <div class="relative">
                <select
                    :value="locale"
                    @change="handleLanguageChange($event.target.value)"
                    class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all appearance-none cursor-pointer"
                >
                    <option value="zh-CN">{{ t('settings.appearance.languages.zhCN') }}</option>
                    <option value="en">{{ t('settings.appearance.languages.en') }}</option>
                </select>
                 <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">expand_more</span>
              </div>
              <p class="text-xs text-text-secondary mt-2 ml-1 flex items-center gap-1">
                  <span class="material-symbols-outlined text-sm">info</span>
                  {{ locale === 'zh-CN' ? '语言将立即切换' : 'Language will switch immediately' }}
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
import { useLanguage } from '../composables/useLanguage';

const { t, locale, setLocale } = useLanguage();

const activeSection = ref('appearance');

// LLM Provider state
const currentProvider = ref('gemini');
const providers = ref({
  gemini: { available: false, model: '' },
  kimi: { available: false, model: '' }
});
const providerSwitching = ref(false);
const providerError = ref('');

const sections = computed(() => [
  { id: 'profile', name: t('settings.sections.profile'), icon: 'person' },
  { id: 'notifications', name: t('settings.sections.notifications'), icon: 'notifications' },
  { id: 'security', name: t('settings.sections.security'), icon: 'lock' },
  { id: 'api', name: t('settings.sections.api'), icon: 'smart_toy' },
  { id: 'appearance', name: t('settings.sections.appearance'), icon: 'palette' }
]);

const handleLanguageChange = (lang) => {
  setLocale(lang);
};

// Fetch LLM providers info
const fetchProviders = async () => {
  try {
    console.log('[Settings] Fetching providers from http://localhost:8003/providers');
    const response = await fetch('http://localhost:8003/providers');
    console.log('[Settings] Response status:', response.status);

    if (response.ok) {
      const data = await response.json();
      console.log('[Settings] Providers data:', data);

      currentProvider.value = data.current_provider;
      // Map providers array to object
      data.providers.forEach(p => {
        providers.value[p.name] = {
          available: p.available,
          model: p.model
        };
      });

      console.log('[Settings] Updated providers:', providers.value);
      console.log('[Settings] Current provider:', currentProvider.value);
    } else {
      console.error('[Settings] Response not ok:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('[Settings] Failed to fetch providers:', error);
  }
};

// Switch LLM provider
const switchProvider = async (providerName) => {
  if (providerName === currentProvider.value) return;
  if (providerSwitching.value) return;

  providerSwitching.value = true;
  providerError.value = '';

  try {
    const response = await fetch(`http://localhost:8003/providers/${providerName}`, {
      method: 'POST'
    });

    if (response.ok) {
      const data = await response.json();
      currentProvider.value = data.current_provider;
      console.log(`[Settings] Switched to ${providerName}`);
    } else {
      const errorData = await response.json();
      providerError.value = errorData.detail || 'Switch failed';
    }
  } catch (error) {
    providerError.value = error.message;
    console.error('[Settings] Failed to switch provider:', error);
  } finally {
    providerSwitching.value = false;
  }
};

// Fetch providers on mount
onMounted(() => {
  fetchProviders();
});
</script>