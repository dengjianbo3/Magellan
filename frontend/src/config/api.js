/**
 * API Configuration
 * Centralized API URL configuration with environment variable support
 */

// API Base URLs
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
export const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8000';
export const AUTH_BASE = import.meta.env.VITE_AUTH_BASE || 'http://localhost:8007';

// Helper function to build API URL
export function apiUrl(path) {
  return `${API_BASE}${path.startsWith('/') ? path : '/' + path}`;
}

// Helper function to build WebSocket URL
export function wsUrl(path) {
  return `${WS_BASE}${path.startsWith('/') ? path : '/' + path}`;
}

// Helper function to build Auth API URL
export function authUrl(path) {
  return `${AUTH_BASE}${path.startsWith('/') ? path : '/' + path}`;
}

export default {
  API_BASE,
  WS_BASE,
  AUTH_BASE,
  apiUrl,
  wsUrl,
  authUrl
};
