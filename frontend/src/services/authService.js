/**
 * Auth Service - Handles authentication API calls
 */
import { AUTH_BASE } from '@/config/api'

const AUTH_API = `${AUTH_BASE}/api/auth`

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
  async request(endpoint, options = {}) {
    const url = `${AUTH_API}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...options.headers
    }

    const response = await fetch(url, {
      ...options,
      headers
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Request failed: ${response.status}`)
    }

    return response.json()
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
    console.log('[AuthService] Login request:', { email, passwordLength: password?.length })
    const response = await this.request('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    })
    console.log('[AuthService] Login response:', response)
    return response
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
