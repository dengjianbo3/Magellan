/**
 * Error Tracking Service
 * Captures and reports frontend errors to backend for monitoring
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

class ErrorTracker {
  constructor() {
    this.initialized = false;
    this.errorQueue = [];
    this.maxQueueSize = 50;
    this.flushInterval = 30000; // 30 seconds
    this.enabled = import.meta.env.PROD || import.meta.env.VITE_ERROR_TRACKING === 'true';
    this.context = {
      appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
      environment: import.meta.env.MODE || 'development'
    };
  }

  /**
   * Initialize error tracking
   * @param {Object} app - Vue app instance
   */
  init(app) {
    if (this.initialized) return;

    // Set up Vue error handler
    app.config.errorHandler = (err, instance, info) => {
      this.captureError(err, {
        type: 'vue',
        componentName: instance?.$options?.name || 'Unknown',
        info: info
      });
    };

    // Set up global error handler
    window.onerror = (message, source, lineno, colno, error) => {
      this.captureError(error || new Error(message), {
        type: 'global',
        source,
        lineno,
        colno
      });
      return false; // Don't prevent default handling
    };

    // Set up unhandled promise rejection handler
    window.onunhandledrejection = (event) => {
      this.captureError(event.reason, {
        type: 'unhandledrejection'
      });
    };

    // Start periodic flush
    if (this.enabled) {
      setInterval(() => this.flush(), this.flushInterval);
    }

    this.initialized = true;
    console.log('[ErrorTracker] Initialized', { enabled: this.enabled });
  }

  /**
   * Set user context for error reports
   * @param {Object} user - User info
   */
  setUser(user) {
    this.context.user = user;
  }

  /**
   * Set current route for error reports
   * @param {Object} route - Route info
   */
  setRoute(route) {
    this.context.route = {
      path: route.path,
      name: route.name,
      params: route.params,
      query: route.query
    };
  }

  /**
   * Capture an error
   * @param {Error} error - The error object
   * @param {Object} extra - Additional context
   */
  captureError(error, extra = {}) {
    const errorData = {
      timestamp: new Date().toISOString(),
      message: error?.message || String(error),
      stack: error?.stack,
      name: error?.name || 'Error',
      ...extra,
      context: { ...this.context },
      url: window.location.href,
      userAgent: navigator.userAgent
    };

    // Always log to console
    console.error('[ErrorTracker] Captured error:', errorData);

    // Add to queue for batch sending
    if (this.enabled) {
      this.errorQueue.push(errorData);

      // Flush if queue is full
      if (this.errorQueue.length >= this.maxQueueSize) {
        this.flush();
      }
    }

    return errorData;
  }

  /**
   * Capture a message (non-error)
   * @param {string} message - Message to capture
   * @param {string} level - Log level (info, warning, error)
   * @param {Object} extra - Additional context
   */
  captureMessage(message, level = 'info', extra = {}) {
    const messageData = {
      timestamp: new Date().toISOString(),
      message,
      level,
      type: 'message',
      ...extra,
      context: { ...this.context },
      url: window.location.href
    };

    if (level === 'error') {
      console.error('[ErrorTracker]', message, extra);
    } else if (level === 'warning') {
      console.warn('[ErrorTracker]', message, extra);
    } else {
      console.log('[ErrorTracker]', message, extra);
    }

    if (this.enabled && level === 'error') {
      this.errorQueue.push(messageData);
    }

    return messageData;
  }

  /**
   * Flush error queue to backend
   */
  async flush() {
    if (this.errorQueue.length === 0) return;

    const errors = [...this.errorQueue];
    this.errorQueue = [];

    try {
      const response = await fetch(`${API_BASE}/api/errors/report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ errors })
      });

      if (!response.ok) {
        // Put errors back in queue if send failed
        console.warn('[ErrorTracker] Failed to send errors, re-queuing');
        this.errorQueue = [...errors, ...this.errorQueue].slice(0, this.maxQueueSize);
      } else {
        console.log(`[ErrorTracker] Sent ${errors.length} errors to backend`);
      }
    } catch (err) {
      // Network error - re-queue errors
      console.warn('[ErrorTracker] Network error, re-queuing errors');
      this.errorQueue = [...errors, ...this.errorQueue].slice(0, this.maxQueueSize);
    }
  }

  /**
   * Create a wrapped function that captures errors
   * @param {Function} fn - Function to wrap
   * @param {Object} context - Additional context for errors
   */
  wrap(fn, context = {}) {
    return (...args) => {
      try {
        const result = fn(...args);
        // Handle async functions
        if (result && typeof result.catch === 'function') {
          return result.catch((err) => {
            this.captureError(err, context);
            throw err;
          });
        }
        return result;
      } catch (err) {
        this.captureError(err, context);
        throw err;
      }
    };
  }
}

// Export singleton instance
export default new ErrorTracker();
