/**
 * API Configuration
 * Centralized API URL configuration with environment variable support
 */

function browserOrigin() {
  if (typeof window === 'undefined' || !window.location) return '';
  return window.location.origin;
}

function browserWsOrigin() {
  if (typeof window === 'undefined' || !window.location) return '';
  return `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;
}

// Base URLs (prefer same-origin by default; override with VITE_* when needed)
// NOTE: Use ?? instead of || so an explicitly empty string remains meaningful.
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').trim() || browserOrigin() || 'http://localhost:18000';
export const AUTH_BASE = (import.meta.env.VITE_AUTH_BASE ?? '').trim() || browserOrigin() || 'http://localhost:18007';
export const WS_BASE = (import.meta.env.VITE_WS_BASE ?? '').trim() || browserWsOrigin() || 'ws://localhost:18000';
const defaultLlmBase = browserOrigin() ? `${browserOrigin()}/api/llm` : 'http://localhost:18003';
export const LLM_BASE = (import.meta.env.VITE_LLM_BASE ?? '').trim() || defaultLlmBase;

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

// Helper function to build LLM Gateway URL
export function llmUrl(path) {
  return `${LLM_BASE}${path.startsWith('/') ? path : '/' + path}`;
}

export default {
  API_BASE,
  WS_BASE,
  AUTH_BASE,
  LLM_BASE,
  apiUrl,
  wsUrl,
  authUrl,
  llmUrl
};
