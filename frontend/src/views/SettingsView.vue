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

        <!-- API Settings -->
        <div v-if="activeSection === 'api'" class="glass-panel rounded-2xl p-8 animate-fade-in">
          <h2 class="text-xl font-bold text-white mb-8 pb-4 border-b border-white/10">{{ t('settings.sections.api') }}</h2>
          <div class="space-y-6">
            <div>
              <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.api.openaiKey') }}</label>
              <div class="flex gap-3">
                <input
                  type="password"
                  value="sk-••••••••••••••••••••••••"
                  class="flex-1 px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all font-mono"
                />
                <button class="px-6 py-3 rounded-xl border border-white/10 text-white hover:bg-white/10 transition-colors font-bold">
                  {{ t('settings.api.update') }}
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">{{ t('settings.api.claudeKey') }}</label>
              <div class="flex gap-3">
                <input
                  type="password"
                  value="sk-ant-••••••••••••••••••"
                  class="flex-1 px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all font-mono"
                />
                <button class="px-6 py-3 rounded-xl border border-white/10 text-white hover:bg-white/10 transition-colors font-bold">
                  {{ t('settings.api.update') }}
                </button>
              </div>
            </div>

            <div class="pt-6 border-t border-white/10">
              <h3 class="font-bold text-primary mb-4 text-sm uppercase tracking-wider">{{ t('settings.api.usage') }}</h3>
              <div class="space-y-4 p-5 rounded-xl bg-black/20 border border-white/5">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-text-secondary font-bold">{{ t('settings.api.thisMonth') }}</span>
                  <span class="text-sm font-bold text-white font-mono">$127.50 / $500.00</span>
                </div>
                <div class="w-full h-3 bg-black/50 rounded-full overflow-hidden border border-white/5">
                  <div class="h-full bg-gradient-to-r from-primary to-accent-cyan shadow-[0_0_10px_rgba(56,189,248,0.5)]" style="width: 25.5%"></div>
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
import { ref, computed } from 'vue';
import { useLanguage } from '../composables/useLanguage';

const { t, locale, setLocale } = useLanguage();

const activeSection = ref('appearance');

const sections = computed(() => [
  { id: 'profile', name: t('settings.sections.profile'), icon: 'person' },
  { id: 'notifications', name: t('settings.sections.notifications'), icon: 'notifications' },
  { id: 'security', name: t('settings.sections.security'), icon: 'lock' },
  { id: 'api', name: t('settings.sections.api'), icon: 'key' },
  { id: 'appearance', name: t('settings.sections.appearance'), icon: 'palette' }
]);

const handleLanguageChange = (lang) => {
  setLocale(lang);
};
</script>