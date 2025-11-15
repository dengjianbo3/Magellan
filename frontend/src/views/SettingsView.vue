<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-bold text-text-primary mb-2">{{ t('settings.title') }}</h1>
      <p class="text-text-secondary">{{ t('settings.subtitle') }}</p>
    </div>

    <!-- Settings Sections -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Settings Navigation -->
      <div class="lg:col-span-1">
        <div class="bg-surface border border-border-color rounded-lg p-4">
          <nav class="space-y-1">
            <button
              v-for="section in sections"
              :key="section.id"
              @click="activeSection = section.id"
              :class="[
                'w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-left',
                activeSection === section.id
                  ? 'bg-primary/20 text-primary'
                  : 'text-text-primary hover:bg-background-dark'
              ]"
            >
              <span class="material-symbols-outlined text-lg">{{ section.icon }}</span>
              <span class="text-sm font-semibold">{{ section.name }}</span>
            </button>
          </nav>
        </div>
      </div>

      <!-- Settings Content -->
      <div class="lg:col-span-3 space-y-6">
        <!-- Profile Settings -->
        <div v-if="activeSection === 'profile'" class="bg-surface border border-border-color rounded-lg p-6">
          <h2 class="text-lg font-bold text-text-primary mb-6">Profile Settings</h2>
          <div class="space-y-6">
            <div class="flex items-center gap-6">
              <div class="w-20 h-20 rounded-full bg-primary flex items-center justify-center text-2xl font-bold text-background-dark">
                ZW
              </div>
              <div>
                <button class="px-4 py-2 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors text-sm font-semibold">
                  Change Avatar
                </button>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-semibold text-text-primary mb-2">First Name</label>
                <input
                  type="text"
                  value="伟"
                  class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label class="block text-sm font-semibold text-text-primary mb-2">Last Name</label>
                <input
                  type="text"
                  value="张"
                  class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
                />
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-text-primary mb-2">Email</label>
              <input
                type="email"
                value="zhang.wei@example.com"
                class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-text-primary mb-2">Role</label>
              <input
                type="text"
                value="投资分析师"
                class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
              />
            </div>

            <div class="pt-4">
              <button class="px-6 py-3 rounded-lg bg-primary text-background-dark hover:bg-primary/90 transition-colors font-semibold">
                Save Changes
              </button>
            </div>
          </div>
        </div>

        <!-- Notification Settings -->
        <div v-if="activeSection === 'notifications'" class="bg-surface border border-border-color rounded-lg p-6">
          <h2 class="text-lg font-bold text-text-primary mb-6">Notification Preferences</h2>
          <div class="space-y-4">
            <div class="flex items-center justify-between p-4 rounded-lg bg-background-dark">
              <div>
                <p class="font-semibold text-text-primary">Analysis Complete</p>
                <p class="text-sm text-text-secondary">Get notified when analysis is finished</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked class="sr-only peer">
                <div class="w-11 h-6 bg-surface-light rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-4 rounded-lg bg-background-dark">
              <div>
                <p class="font-semibold text-text-primary">Agent Updates</p>
                <p class="text-sm text-text-secondary">Notifications for agent status changes</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked class="sr-only peer">
                <div class="w-11 h-6 bg-surface-light rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-4 rounded-lg bg-background-dark">
              <div>
                <p class="font-semibold text-text-primary">Weekly Reports</p>
                <p class="text-sm text-text-secondary">Receive weekly activity summary</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" class="sr-only peer">
                <div class="w-11 h-6 bg-surface-light rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-4 rounded-lg bg-background-dark">
              <div>
                <p class="font-semibold text-text-primary">Email Notifications</p>
                <p class="text-sm text-text-secondary">Send notifications to email</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked class="sr-only peer">
                <div class="w-11 h-6 bg-surface-light rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
              </label>
            </div>
          </div>
        </div>

        <!-- Security Settings -->
        <div v-if="activeSection === 'security'" class="bg-surface border border-border-color rounded-lg p-6">
          <h2 class="text-lg font-bold text-text-primary mb-6">Security Settings</h2>
          <div class="space-y-6">
            <div>
              <h3 class="font-semibold text-text-primary mb-4">Change Password</h3>
              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-semibold text-text-primary mb-2">Current Password</label>
                  <input
                    type="password"
                    class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label class="block text-sm font-semibold text-text-primary mb-2">New Password</label>
                  <input
                    type="password"
                    class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label class="block text-sm font-semibold text-text-primary mb-2">Confirm New Password</label>
                  <input
                    type="password"
                    class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
                <button class="px-6 py-3 rounded-lg bg-primary text-background-dark hover:bg-primary/90 transition-colors font-semibold">
                  Update Password
                </button>
              </div>
            </div>

            <div class="pt-6 border-t border-border-color">
              <h3 class="font-semibold text-text-primary mb-4">Two-Factor Authentication</h3>
              <div class="flex items-center justify-between p-4 rounded-lg bg-background-dark">
                <div>
                  <p class="font-semibold text-text-primary">Enable 2FA</p>
                  <p class="text-sm text-text-secondary">Add an extra layer of security</p>
                </div>
                <button class="px-4 py-2 rounded-lg border border-border-color text-text-primary hover:bg-surface transition-colors text-sm font-semibold">
                  Enable
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- API Settings -->
        <div v-if="activeSection === 'api'" class="bg-surface border border-border-color rounded-lg p-6">
          <h2 class="text-lg font-bold text-text-primary mb-6">API Configuration</h2>
          <div class="space-y-6">
            <div>
              <label class="block text-sm font-semibold text-text-primary mb-2">OpenAI API Key</label>
              <div class="flex gap-3">
                <input
                  type="password"
                  value="sk-••••••••••••••••••••••••"
                  class="flex-1 px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
                />
                <button class="px-4 py-3 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors font-semibold">
                  Update
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-text-primary mb-2">Claude API Key</label>
              <div class="flex gap-3">
                <input
                  type="password"
                  value="sk-ant-••••••••••••••••••"
                  class="flex-1 px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
                />
                <button class="px-4 py-3 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors font-semibold">
                  Update
                </button>
              </div>
            </div>

            <div class="pt-4 border-t border-border-color">
              <h3 class="font-semibold text-text-primary mb-4">API Usage</h3>
              <div class="space-y-3">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-text-secondary">This Month</span>
                  <span class="text-sm font-semibold text-text-primary">$127.50 / $500</span>
                </div>
                <div class="w-full h-2 bg-background-dark rounded-full overflow-hidden">
                  <div class="h-full bg-primary" style="width: 25.5%"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Appearance Settings -->
        <div v-if="activeSection === 'appearance'" class="bg-surface border border-border-color rounded-lg p-6">
          <h2 class="text-lg font-bold text-text-primary mb-6">{{ t('settings.appearance.title') }}</h2>
          <div class="space-y-6">
            <div>
              <label class="block text-sm font-semibold text-text-primary mb-3">{{ t('settings.appearance.theme') }}</label>
              <div class="grid grid-cols-3 gap-4">
                <button class="p-4 rounded-lg border-2 border-border-color hover:border-primary/50 transition-colors">
                  <div class="w-full h-20 rounded bg-gradient-to-br from-gray-100 to-gray-300 mb-3"></div>
                  <p class="text-sm font-semibold text-text-primary">{{ t('settings.appearance.themes.light') }}</p>
                </button>
                <button class="p-4 rounded-lg border-2 border-primary bg-primary/10 transition-colors">
                  <div class="w-full h-20 rounded bg-gradient-to-br from-gray-800 to-gray-900 mb-3"></div>
                  <p class="text-sm font-semibold text-primary">{{ t('settings.appearance.themes.dark') }}</p>
                </button>
                <button class="p-4 rounded-lg border-2 border-border-color hover:border-primary/50 transition-colors">
                  <div class="w-full h-20 rounded bg-gradient-to-br from-gray-100 via-gray-300 to-gray-900 mb-3"></div>
                  <p class="text-sm font-semibold text-text-primary">{{ t('settings.appearance.themes.auto') }}</p>
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-text-primary mb-2">{{ t('settings.appearance.language') }}</label>
              <select
                :value="locale"
                @change="handleLanguageChange($event.target.value)"
                class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
              >
                <option value="zh-CN">{{ t('settings.appearance.languages.zhCN') }}</option>
                <option value="en">{{ t('settings.appearance.languages.en') }}</option>
              </select>
              <p class="text-xs text-text-secondary mt-2">{{ locale === 'zh-CN' ? '语言将立即切换' : 'Language will switch immediately' }}</p>
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

const activeSection = ref('appearance'); // 默认显示外观设置

// 使用 computed 让 sections 响应语言变化
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
