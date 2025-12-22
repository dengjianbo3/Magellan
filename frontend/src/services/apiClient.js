/**
 * API Client with authentication interceptors
 * Handles automatic token injection and refresh
 */
import { API_BASE, AUTH_BASE } from '@/config/api'

class ApiClient {
  constructor() {
    this.isRefreshing = false
    this.refreshSubscribers = []
  }

  /**
   * Get access token from localStorage
   */
  getAccessToken() {
    return localStorage.getItem('access_token')
  }

  /**
   * Get refresh token from localStorage
   */
  getRefreshToken() {
    return localStorage.getItem('refresh_token')
  }

  /**
   * Subscribe to token refresh
   */
  subscribeTokenRefresh(callback) {
    this.refreshSubscribers.push(callback)
  }

  /**
   * Notify all subscribers that token has been refreshed
   */
  onTokenRefreshed(token) {
    this.refreshSubscribers.forEach(callback => callback(token))
    this.refreshSubscribers = []
  }

  /**
   * Refresh the access token
   */
  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await fetch(`${AUTH_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    })

    if (!response.ok) {
      // Clear tokens on refresh failure
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      throw new Error('Token refresh failed')
    }

    const data = await response.json()
    localStorage.setItem('access_token', data.access_token)
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }

    return data.access_token
  }

  /**
   * Make an authenticated request
   */
  async request(url, options = {}) {
    const token = this.getAccessToken()

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    let response = await fetch(url, {
      ...options,
      headers
    })

    // Handle 401 Unauthorized - try to refresh token
    if (response.status === 401 && token) {
      if (!this.isRefreshing) {
        this.isRefreshing = true

        try {
          const newToken = await this.refreshAccessToken()
          this.isRefreshing = false
          this.onTokenRefreshed(newToken)

          // Retry the original request with new token
          headers['Authorization'] = `Bearer ${newToken}`
          response = await fetch(url, {
            ...options,
            headers
          })
        } catch (error) {
          this.isRefreshing = false
          // Redirect to login on refresh failure
          window.location.href = '/login'
          throw error
        }
      } else {
        // Wait for token refresh to complete
        return new Promise((resolve, reject) => {
          this.subscribeTokenRefresh(async (newToken) => {
            try {
              headers['Authorization'] = `Bearer ${newToken}`
              const retryResponse = await fetch(url, {
                ...options,
                headers
              })
              resolve(this.handleResponse(retryResponse))
            } catch (error) {
              reject(error)
            }
          })
        })
      }
    }

    return this.handleResponse(response)
  }

  /**
   * Handle response and parse JSON
   */
  async handleResponse(response) {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const error = new Error(errorData.detail || `Request failed: ${response.status}`)
      error.status = response.status
      error.data = errorData
      throw error
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      return response.json()
    }
    return null
  }

  /**
   * GET request
   */
  get(url, options = {}) {
    return this.request(url, { ...options, method: 'GET' })
  }

  /**
   * POST request
   */
  post(url, data, options = {}) {
    return this.request(url, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  /**
   * PUT request
   */
  put(url, data, options = {}) {
    return this.request(url, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  /**
   * DELETE request
   */
  delete(url, options = {}) {
    return this.request(url, { ...options, method: 'DELETE' })
  }

  /**
   * Build API URL
   */
  apiUrl(path) {
    return `${API_BASE}${path.startsWith('/') ? path : '/' + path}`
  }

  /**
   * Build Auth URL
   */
  authUrl(path) {
    return `${AUTH_BASE}${path.startsWith('/') ? path : '/' + path}`
  }
}

export default new ApiClient()
