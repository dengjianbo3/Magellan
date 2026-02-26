/**
 * Auth Service - Handles authentication API calls
 */
import { AUTH_BASE } from '@/config/api'
import { readJsonResponse } from '@/services/httpResponse'

const AUTH_API = `${AUTH_BASE}/api/auth`
const LOCAL_AUTH_FALLBACK_API = 'http://localhost:18007/api/auth'
const AUTH_REQUEST_TIMEOUT_MS = 15000

class AuthService {
  /**
   * Get the current access token from localStorage
   */
  getAccessToken() {
    return localStorage.getItem('access_token')
  }

  /**
   * Get authorization headers
   */
  getAuthHeaders() {
    const token = this.getAccessToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  /**
   * Make authenticated API request
   */
  async request(endpoint, options = {}, requestBase = AUTH_API, allowFallback = true) {
    const url = `${requestBase}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...options.headers
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), AUTH_REQUEST_TIMEOUT_MS)

    let response
    try {
      response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      })
    } catch (error) {
      if (allowFallback && requestBase !== LOCAL_AUTH_FALLBACK_API) {
        // If the current auth base is unreachable, retry once against local auth service.
        return this.request(endpoint, options, LOCAL_AUTH_FALLBACK_API, false)
      }
      if (error?.name === 'AbortError') {
        throw new Error(`Auth ${endpoint} timeout after ${AUTH_REQUEST_TIMEOUT_MS / 1000}s`)
      }
      throw new Error(`Auth ${endpoint} network error: ${error?.message || 'request failed'}`)
    } finally {
      clearTimeout(timeoutId)
    }

    return readJsonResponse(response, `Auth ${endpoint}`)
  }

  /**
   * Register a new user
   */
  async register({ email, password, name, organization }) {
    return this.request('/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name, organization })
    })
  }

  /**
   * Login with email and password
   */
  async login(email, password) {
    return this.request('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    })
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken) {
    return this.request('/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken })
    })
  }

  /**
   * Logout (server-side)
   */
  async logout() {
    return this.request('/logout', {
      method: 'POST'
    })
  }

  /**
   * Get current user profile
   */
  async getCurrentUser() {
    return this.request('/me', {
      method: 'GET'
    })
  }

  /**
   * Update user profile
   */
  async updateProfile({ name, organization }) {
    return this.request('/me', {
      method: 'PUT',
      body: JSON.stringify({ name, organization })
    })
  }

  /**
   * Change password
   */
  async changePassword(currentPassword, newPassword) {
    return this.request('/password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword
      })
    })
  }

  /**
   * Verify if token is valid
   */
  async verifyToken() {
    return this.request('/verify', {
      method: 'GET'
    })
  }
}

export default new AuthService()
