<template>
  <div class="relative min-h-screen overflow-hidden bg-background-dark px-4 py-10 sm:px-6 lg:px-8">
    <div class="pointer-events-none absolute inset-0">
      <div class="absolute -left-24 top-0 h-80 w-80 rounded-full bg-primary/15 blur-3xl"></div>
      <div class="absolute right-0 top-1/4 h-72 w-72 rounded-full bg-accent-cyan/10 blur-3xl"></div>
      <div class="absolute bottom-0 left-1/2 h-80 w-[28rem] -translate-x-1/2 rounded-full bg-primary-dark/10 blur-3xl"></div>
    </div>

    <div class="relative z-10 mx-auto w-full max-w-md space-y-7">
      <div class="text-center">
        <h1 class="text-4xl font-display font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-primary">Magellan</h1>
        <h2 class="mt-4 text-2xl font-bold text-white">
          {{ t('auth.loginTitle') }}
        </h2>
        <p class="mt-2 text-sm text-text-secondary">
          {{ t('auth.loginSubtitle') }}
        </p>
      </div>

      <div class="modal-shell">
        <form class="space-y-5" @submit.prevent="handleLogin">
          <div v-if="error" class="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-rose-300">
            <p class="text-sm">{{ error }}</p>
          </div>

          <div class="space-y-4">
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
              <label for="password" class="mb-2 block text-sm font-semibold text-text-primary">
                {{ t('auth.password') }}
              </label>
              <input
                id="password"
                v-model="form.password"
                type="password"
                required
                autocomplete="current-password"
                class="control-input w-full !h-11 !bg-black/25"
                :placeholder="t('auth.passwordPlaceholder')"
              />
            </div>
          </div>

          <div class="flex items-center justify-between">
            <label for="remember-me" class="flex items-center gap-2 text-sm text-text-secondary">
              <input
                id="remember-me"
                v-model="form.rememberMe"
                type="checkbox"
                class="h-4 w-4 rounded border-white/20 bg-black/30 text-primary focus:ring-primary/50"
              />
              {{ t('auth.rememberMe') }}
            </label>

            <a href="#" class="text-sm font-semibold text-primary hover:text-white transition-colors">
              {{ t('auth.forgotPassword') }}
            </a>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="page-primary-btn h-11 w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="flex items-center">
              <svg class="-ml-1 mr-2 h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ t('auth.loggingIn') }}
            </span>
            <span v-else>{{ t('auth.login') }}</span>
          </button>

          <div class="text-center text-sm text-text-secondary">
            {{ t('auth.noAccount') }}
            <router-link to="/register" class="ml-1 font-semibold text-primary hover:text-white transition-colors">
              {{ t('auth.registerNow') }}
            </router-link>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from '@/i18n'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { t } = useI18n()

const form = reactive({
  email: '',
  password: '',
  rememberMe: false
})

const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''

  // Trim whitespace from email
  const email = form.email.trim()
  const password = form.password

  const result = await authStore.login(email, password)

  if (result.success) {
    // Redirect to original destination or dashboard
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } else {
    error.value = result.error
  }

  loading.value = false
}
</script>
