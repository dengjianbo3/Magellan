import { ref, computed } from 'vue';
import zhCN from '../i18n/zh-CN.js';
import en from '../i18n/en.js';

// 全局语言状态 - 从 localStorage 读取或默认为中文
const currentLocale = ref(localStorage.getItem('locale') || 'zh-CN');

const translations = {
  'zh-CN': zhCN,
  'en': en
};

export function useLanguage() {
  const t = (key) => {
    const keys = key.split('.');
    let value = translations[currentLocale.value];

    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k];
      } else {
        return key; // 返回 key 如果找不到翻译
      }
    }

    return value || key;
  };

  const setLocale = (locale) => {
    if (translations[locale]) {
      currentLocale.value = locale;
      localStorage.setItem('locale', locale); // 保存到 localStorage
    }
  };

  const locale = computed(() => currentLocale.value);

  return {
    t,
    locale,
    setLocale
  };
}
