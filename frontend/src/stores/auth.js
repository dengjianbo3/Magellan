/**
 * Auth Store - Manages authentication state using Pinia
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import authService from '@/services/authService'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const userRole = computed(() => user.value?.role || 'guest')
  const userName = computed(() => user.value?.name || '')
  const userEmail = computed(() => user.value?.email || '')

  const isAdmin = computed(() => userRole.value === 'admin')
  const isInstitution = computed(() => userRole.value === 'institution')
  const isAnalyst = computed(() => userRole.value === 'analyst')

  // Actions
  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function setUser(userData) {
    user.value = userData
  }

  function clearUser() {
    user.value = null
  }

  async function login(email, password) {
    loading.value = true
    error.value = null

    try {
      const response = await authService.login(email, password)
      setTokens(response.access_token, response.refresh_token)
      setUser(response.user)
      return { success: true }
    } catch (err) {
      error.value = err.message || 'Login failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  async function register(userData) {
    loading.value = true
    error.value = null

    try {
      const response = await authService.register(userData)
      setTokens(response.access_token, response.refresh_token)
      setUser(response.user)
      return { success: true }
    } catch (err) {
      error.value = err.message || 'Registration failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true

    try {
      await authService.logout()
    } catch (err) {
      // Ignore logout errors
      console.warn('Logout error:', err)
    } finally {
      clearTokens()
      clearUser()
      loading.value = false
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      return false
    }

    try {
      const response = await authService.refreshToken(refreshToken.value)
      setTokens(response.access_token, response.refresh_token)
      setUser(response.user)
      return true
    } catch (err) {
      console.error('Token refresh failed:', err)
      clearTokens()
      clearUser()
      return false
    }
  }

  async function fetchCurrentUser() {
    if (!accessToken.value) {
      return false
    }

    loading.value = true

    try {
      const userData = await authService.getCurrentUser()
      setUser(userData)
      return true
    } catch (err) {
      console.error('Failed to fetch current user:', err)
      // Token might be expired, try to refresh
      const refreshed = await refreshAccessToken()
      if (!refreshed) {
        clearTokens()
        clearUser()
      }
      return refreshed
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(data) {
    loading.value = true
    error.value = null

    try {
      const updatedUser = await authService.updateProfile(data)
      setUser(updatedUser)
      return { success: true }
    } catch (err) {
      error.value = err.message || 'Update failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  async function changePassword(currentPassword, newPassword) {
    loading.value = true
    error.value = null

    try {
      await authService.changePassword(currentPassword, newPassword)
      return { success: true }
    } catch (err) {
      error.value = err.message || 'Password change failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  // Initialize - check if user is already logged in
  async function initialize() {
    if (accessToken.value) {
      await fetchCurrentUser()
    }
  }

  // Check if user has specific role
  function hasRole(roles) {
    if (!Array.isArray(roles)) {
      roles = [roles]
    }
    return roles.includes(userRole.value)
  }

  return {
    // State
    user,
    accessToken,
    refreshToken,
    loading,
    error,

    // Getters
    isAuthenticated,
    userRole,
    userName,
    userEmail,
    isAdmin,
    isInstitution,
    isAnalyst,

    // Actions
    login,
    register,
    logout,
    refreshAccessToken,
    fetchCurrentUser,
    updateProfile,
    changePassword,
    initialize,
    hasRole,
    setTokens,
    clearTokens
  }
})
