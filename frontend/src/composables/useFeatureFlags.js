import { ref } from 'vue';

const AUTO_TRADING_BETA_KEY = 'magellan_beta_auto_trading_v1';

function readStoredFlag() {
  try {
    if (typeof window === 'undefined') return false;
    const raw = window.localStorage.getItem(AUTO_TRADING_BETA_KEY);
    return raw === '1';
  } catch {
    return false;
  }
}

const autoTradingBetaEnabled = ref(readStoredFlag());

function persistFlag(nextValue) {
  try {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(AUTO_TRADING_BETA_KEY, nextValue ? '1' : '0');
  } catch {
    // ignore storage write errors
  }
}

function setAutoTradingBetaEnabled(nextValue) {
  const normalized = Boolean(nextValue);
  autoTradingBetaEnabled.value = normalized;
  persistFlag(normalized);
}

function isAutoTradingBetaEnabled() {
  return readStoredFlag();
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === AUTO_TRADING_BETA_KEY) {
      autoTradingBetaEnabled.value = event.newValue === '1';
    }
  });
}

export function useFeatureFlags() {
  return {
    autoTradingBetaEnabled,
    setAutoTradingBetaEnabled,
  };
}

export {
  AUTO_TRADING_BETA_KEY,
  isAutoTradingBetaEnabled,
};
