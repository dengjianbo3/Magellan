<template>
  <div class="relative min-h-screen overflow-hidden bg-background-dark px-4 py-10 sm:px-6 lg:px-8">
    <div class="pointer-events-none absolute inset-0">
      <div class="absolute -left-16 top-10 h-80 w-80 rounded-full bg-primary/15 blur-3xl"></div>
      <div class="absolute right-0 top-1/3 h-72 w-72 rounded-full bg-accent-cyan/10 blur-3xl"></div>
      <div class="absolute bottom-0 left-1/2 h-80 w-[30rem] -translate-x-1/2 rounded-full bg-primary-dark/10 blur-3xl"></div>
    </div>

    <div class="relative z-10 mx-auto w-full max-w-lg space-y-7">
      <div class="text-center">
        <h1 class="text-4xl font-display font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-primary">Magellan</h1>
        <h2 class="mt-4 text-2xl font-bold text-white">
          {{ t('auth.registerTitle') }}
        </h2>
        <p class="mt-2 text-sm text-text-secondary">
          {{ t('auth.registerSubtitle') }}
        </p>
      </div>

      <div class="modal-shell">
        <form class="space-y-5" @submit.prevent="handleRegister">
          <div v-if="error" class="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-rose-300">
            <p class="text-sm">{{ error }}</p>
          </div>

          <div class="space-y-4">
            <div>
              <label for="name" class="mb-2 block text-sm font-semibold text-text-primary">
                {{ t('auth.name') }}
              </label>
              <input
                id="name"
                v-model="form.name"
                type="text"
                required
                autocomplete="name"
                class="control-input w-full !h-11 !bg-black/25"
                :placeholder="t('auth.namePlaceholder')"
              />
            </div>

            <div>
              <label for="email" class="mb-2 block text-sm font-semibold text-text-primary">
                {{ t('auth.email') }}
              </label>
              <input
                id="email"
                v-model="form.email"
                type="email"
                required
                autocomplete="email"
                class="control-input w-full !h-11 !bg-black/25"
                :placeholder="t('auth.emailPlaceholder')"
              />
            </div>

            <div>
              <label for="organization" class="mb-2 block text-sm font-semibold text-text-primary">
                {{ t('auth.organization') }}
                <span class="ml-1 font-normal text-text-secondary">({{ t('common.optional') }})</span>
              </label>
              <input
                id="organization"
                v-model="form.organization"
                type="text"
                autocomplete="organization"
                class="control-input w-full !h-11 !bg-black/25"
                :placeholder="t('auth.organizationPlaceholder')"
              />
            </div>

            <div>
              <label for="password" class="mb-2 block text-sm font-semibold text-text-primary">
                {{ t('auth.password') }}
              </label>
              <input
                id="password"
                v-model="form.password"
                type="password"
                required
                autocomplete="new-password"
                class="control-input w-full !h-11 !bg-black/25"
                :placeholder="t('auth.newPasswordPlaceholder')"
              />
              <p class="mt-1 text-xs text-text-secondary">
                {{ t('auth.passwordRequirements') }}
              </p>
            </div>

            <div>
              <label for="confirmPassword" class="mb-2 block text-sm font-semibold text-text-primary">
                {{ t('auth.confirmPassword') }}
              </label>
              <input
                id="confirmPassword"
                v-model="form.confirmPassword"
                type="password"
                required
                autocomplete="new-password"
                class="control-input w-full !h-11 !bg-black/25"
                :placeholder="t('auth.confirmPasswordPlaceholder')"
              />
            </div>
          </div>

          <label for="terms" class="flex items-start gap-2 text-sm text-text-secondary">
            <input
              id="terms"
              v-model="form.acceptTerms"
              type="checkbox"
              required
              class="mt-0.5 h-4 w-4 rounded border-white/20 bg-black/30 text-primary focus:ring-primary/50"
            />
            <span>
              {{ t('auth.acceptTerms') }}
              <a href="#" class="mx-1 font-semibold text-primary hover:text-white transition-colors">{{ t('auth.termsOfService') }}</a>
              {{ t('auth.and') }}
              <a href="#" class="ml-1 font-semibold text-primary hover:text-white transition-colors">{{ t('auth.privacyPolicy') }}</a>
            </span>
          </label>

          <button
            type="submit"
            :disabled="loading || !form.acceptTerms"
            class="page-primary-btn h-11 w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="flex items-center">
              <svg class="-ml-1 mr-2 h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ t('auth.registering') }}
            </span>
            <span v-else>{{ t('auth.register') }}</span>
          </button>

          <div class="text-center text-sm text-text-secondary">
            {{ t('auth.hasAccount') }}
            <router-link to="/login" class="ml-1 font-semibold text-primary hover:text-white transition-colors">
              {{ t('auth.loginNow') }}
            </router-link>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from '@/i18n'

const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const form = reactive({
  name: '',
  email: '',
  organization: '',
  password: '',
  confirmPassword: '',
  acceptTerms: false
})

const loading = ref(false)
const error = ref('')

async function handleRegister() {
  // Validate passwords match
  if (form.password !== form.confirmPassword) {
    error.value = t('auth.passwordMismatch')
    return
  }

  loading.value = true
  error.value = ''

  const result = await authStore.register({
    name: form.name,
    email: form.email,
    password: form.password,
    organization: form.organization || null
  })

  if (result.success) {
    router.push('/')
  } else {
    error.value = result.error
  }

  loading.value = false
}
</script>
