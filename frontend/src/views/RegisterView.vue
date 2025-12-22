<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <!-- Logo and Title -->
      <div class="text-center">
        <h1 class="text-4xl font-bold text-indigo-600">Magellan</h1>
        <h2 class="mt-4 text-2xl font-semibold text-gray-900">
          {{ t('auth.registerTitle') }}
        </h2>
        <p class="mt-2 text-sm text-gray-600">
          {{ t('auth.registerSubtitle') }}
        </p>
      </div>

      <!-- Register Form -->
      <form class="mt-8 space-y-6" @submit.prevent="handleRegister">
        <!-- Error Alert -->
        <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p class="text-sm">{{ error }}</p>
        </div>

        <div class="space-y-4">
          <!-- Name Input -->
          <div>
            <label for="name" class="block text-sm font-medium text-gray-700">
              {{ t('auth.name') }}
            </label>
            <input
              id="name"
              v-model="form.name"
              type="text"
              required
              autocomplete="name"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm
                     placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              :placeholder="t('auth.namePlaceholder')"
            />
          </div>

          <!-- Email Input -->
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">
              {{ t('auth.email') }}
            </label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              autocomplete="email"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm
                     placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              :placeholder="t('auth.emailPlaceholder')"
            />
          </div>

          <!-- Organization Input (Optional) -->
          <div>
            <label for="organization" class="block text-sm font-medium text-gray-700">
              {{ t('auth.organization') }}
              <span class="text-gray-400 font-normal">({{ t('common.optional') }})</span>
            </label>
            <input
              id="organization"
              v-model="form.organization"
              type="text"
              autocomplete="organization"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm
                     placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              :placeholder="t('auth.organizationPlaceholder')"
            />
          </div>

          <!-- Password Input -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">
              {{ t('auth.password') }}
            </label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              autocomplete="new-password"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm
                     placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              :placeholder="t('auth.newPasswordPlaceholder')"
            />
            <p class="mt-1 text-xs text-gray-500">
              {{ t('auth.passwordRequirements') }}
            </p>
          </div>

          <!-- Confirm Password Input -->
          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700">
              {{ t('auth.confirmPassword') }}
            </label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              required
              autocomplete="new-password"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm
                     placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              :placeholder="t('auth.confirmPasswordPlaceholder')"
            />
          </div>
        </div>

        <!-- Terms Checkbox -->
        <div class="flex items-start">
          <input
            id="terms"
            v-model="form.acceptTerms"
            type="checkbox"
            required
            class="h-4 w-4 mt-0.5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
          />
          <label for="terms" class="ml-2 block text-sm text-gray-700">
            {{ t('auth.acceptTerms') }}
            <a href="#" class="text-indigo-600 hover:text-indigo-500">{{ t('auth.termsOfService') }}</a>
            {{ t('auth.and') }}
            <a href="#" class="text-indigo-600 hover:text-indigo-500">{{ t('auth.privacyPolicy') }}</a>
          </label>
        </div>

        <!-- Submit Button -->
        <div>
          <button
            type="submit"
            :disabled="loading || !form.acceptTerms"
            class="group relative w-full flex justify-center py-3 px-4 border border-transparent
                   text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700
                   focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span v-if="loading" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ t('auth.registering') }}
            </span>
            <span v-else>{{ t('auth.register') }}</span>
          </button>
        </div>

        <!-- Login Link -->
        <div class="text-center">
          <p class="text-sm text-gray-600">
            {{ t('auth.hasAccount') }}
            <router-link to="/login" class="font-medium text-indigo-600 hover:text-indigo-500">
              {{ t('auth.loginNow') }}
            </router-link>
          </p>
        </div>
      </form>
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
