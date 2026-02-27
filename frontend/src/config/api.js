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

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '');
}

function normalizeApiBase(raw) {
  const value = trimTrailingSlash(raw.trim());
  // Allow user-provided forms like http://host or http://host/api
  return value.replace(/\/api$/i, '');
}

function normalizeAuthBase(raw) {
  const value = trimTrailingSlash(raw.trim());
  // Allow user-provided forms like http://host, http://host/api, http://host/api/auth
  return value.replace(/\/api\/auth$/i, '').replace(/\/api$/i, '');
}

function normalizeWsBase(raw) {
  return trimTrailingSlash(raw.trim());
}

function normalizeLlmBase(raw) {
  return trimTrailingSlash(raw.trim());
}

// Base URLs (prefer same-origin by default; override with VITE_* when needed)
// NOTE: Use ?? instead of || so an explicitly empty string remains meaningful.
export const API_BASE = normalizeApiBase(import.meta.env.VITE_API_BASE ?? '') || browserOrigin() || 'http://localhost';
export const AUTH_BASE = normalizeAuthBase(import.meta.env.VITE_AUTH_BASE ?? '') || browserOrigin() || 'http://localhost';
export const WS_BASE = normalizeWsBase(import.meta.env.VITE_WS_BASE ?? '') || browserWsOrigin() || 'ws://localhost';
const defaultLlmBase = browserOrigin() ? `${browserOrigin()}/api/llm` : 'http://localhost/api/llm';
export const LLM_BASE = normalizeLlmBase(import.meta.env.VITE_LLM_BASE ?? '') || defaultLlmBase;

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
