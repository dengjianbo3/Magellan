/**
 * i18n - Internationalization support
 * Provides simple translation functionality
 */
import { ref, computed, readonly } from 'vue'
import zhCN from './zh-CN'
import en from './en'

// Available locales
const locales = {
  'zh-CN': zhCN,
  'en': en
}

// Current locale (reactive)
const currentLocale = ref(localStorage.getItem('locale') || 'zh-CN')

// Get nested value from object by dot-separated path
function getNestedValue(obj, path) {
  return path.split('.').reduce((acc, key) => acc?.[key], obj)
}

// Translation function
function t(key, params = {}) {
  const messages = locales[currentLocale.value] || locales['zh-CN']
  let value = getNestedValue(messages, key)

  if (!value) {
    console.warn(`[i18n] Missing translation for key: ${key}`)
    return key
  }

  // Replace parameters like {name} with actual values
  if (typeof value === 'string' && Object.keys(params).length > 0) {
    Object.entries(params).forEach(([paramKey, paramValue]) => {
      value = value.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), paramValue)
    })
  }

  return value
}

// Set locale
function setLocale(locale) {
  if (locales[locale]) {
    currentLocale.value = locale
    localStorage.setItem('locale', locale)
  } else {
    console.warn(`[i18n] Locale not found: ${locale}`)
  }
}

// Get current locale
function getLocale() {
  return currentLocale.value
}

// Get available locales
function getAvailableLocales() {
  return Object.keys(locales)
}

// useI18n composable
export function useI18n() {
  return {
    t,
    locale: readonly(currentLocale),
    setLocale,
    getLocale,
    getAvailableLocales
  }
}

// Export for direct use
export {
  t,
  setLocale,
  getLocale,
  getAvailableLocales,
  currentLocale
}

export default {
  useI18n,
  t,
  setLocale,
  getLocale,
  getAvailableLocales
}
