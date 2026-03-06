<template>
  <details class="mt-3 overflow-hidden rounded-xl border border-white/10 bg-white/6">
    <summary class="flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-xs text-text-secondary transition-colors hover:bg-white/8">
      <span class="inline-flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[14px] text-emerald-300">fact_check</span>
        <span class="font-semibold text-emerald-200">{{ titleText }}</span>
      </span>
      <span class="material-symbols-outlined text-[16px] text-text-secondary">expand_more</span>
    </summary>

    <div class="space-y-2 border-t border-white/8 p-3">
      <div v-if="taskBriefText" class="rounded-lg border border-blue-400/20 bg-blue-500/10 px-2.5 py-2 text-xs text-blue-100">
        <span class="mr-1 text-blue-200/85">{{ taskBriefLabel }}</span>{{ taskBriefText }}
      </div>

      <div v-if="packetSummary" class="rounded-lg border border-emerald-500/20 bg-emerald-500/8 px-2.5 py-2 text-xs text-emerald-100">
        {{ packetSummary }}
      </div>

      <article
        v-for="(item, idx) in normalizedChain"
        :key="`evidence_${idx}_${item.tool || 'tool'}`"
        class="rounded-lg border border-white/8 bg-white/6 p-2.5"
      >
        <div class="mb-1.5 flex flex-wrap items-center gap-1.5 text-xs">
          <span class="rounded-full bg-primary/20 px-2 py-0.5 text-[11px] text-primary-light">{{ item.tool || fallbackTool }}</span>
          <span :class="statusClass(item.status)" class="rounded-full px-2 py-0.5 text-[11px]">
            {{ statusText(item.status) }}
          </span>
          <span class="text-[11px] text-text-secondary">{{ durationLabel(item.duration_ms) }}</span>
        </div>

        <p v-if="item.purpose" class="mb-1.5 text-xs text-text-secondary">
          {{ item.purpose }}
        </p>

        <div v-if="item.summaryText" class="mb-1.5 rounded-md border border-primary/25 bg-primary/10 px-2.5 py-2 text-xs text-primary-light">
          {{ item.summaryText }}
        </div>

        <div v-if="item.keyFacts.length" class="mb-1.5 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          <div
            v-for="(fact, factIdx) in item.keyFacts"
            :key="`fact_${idx}_${factIdx}`"
            class="rounded-md border border-cyan-400/20 bg-cyan-500/8 px-2 py-1.5"
          >
            <p class="text-[10px] text-cyan-200/85">{{ fact.label }}</p>
            <p class="truncate text-xs font-semibold text-cyan-100">{{ fact.value }}</p>
          </div>
        </div>

        <div v-if="item.searchResults.length" class="mb-1.5 rounded-md border border-emerald-400/20 bg-emerald-500/8 p-2">
          <p class="mb-1 text-[10px] uppercase tracking-wider text-emerald-200/80">
            {{ searchResultLabel }}
          </p>
          <div class="space-y-1.5">
            <a
              v-for="(result, rIdx) in item.searchResults"
              :key="`result_${idx}_${rIdx}`"
              :href="result.url"
              target="_blank"
              rel="noopener noreferrer"
              class="block rounded-md border border-emerald-400/20 bg-black/10 px-2 py-1.5 text-xs text-emerald-100 hover:bg-black/20"
            >
              <p class="line-clamp-2 font-semibold">{{ result.title }}</p>
              <p class="mt-0.5 text-[10px] text-emerald-200/80">{{ sourceHost(result.url) }}</p>
            </a>
          </div>
        </div>

        <div v-if="Array.isArray(item.sources) && item.sources.length" class="flex flex-wrap gap-1">
          <a
            v-for="(url, urlIdx) in item.sources"
            :key="`src_${idx}_${urlIdx}`"
            :href="url"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex max-w-full items-center gap-1 rounded-full border border-emerald-400/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-200 hover:bg-emerald-500/16"
          >
            <span class="material-symbols-outlined text-[11px]">link</span>
            <span class="truncate">{{ sourceHost(url) }}</span>
          </a>
        </div>

        <p v-if="item.error" class="mt-1.5 rounded-md border border-rose-500/30 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200">
          {{ item.error }}
        </p>
      </article>
    </div>
  </details>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  chain: {
    type: Array,
    default: () => [],
  },
  packet: {
    type: Object,
    default: null,
  },
  taskBrief: {
    type: String,
    default: '',
  },
  localeTag: {
    type: String,
    default: 'zh-CN',
  },
});

const isZh = computed(() => String(props.localeTag || '').toLowerCase().startsWith('zh'));

const normalizedChain = computed(() => {
  if (!Array.isArray(props.chain)) return [];
  return props.chain
    .filter((item) => item && typeof item === 'object')
    .map((item) => {
      const outputPreview = String(item.output_preview || '');
      const parsedPayload = parseOutputPayload(outputPreview);
      return {
        tool: String(item.tool || ''),
        status: String(item.status || ''),
        purpose: String(item.purpose || ''),
        duration_ms: Number(item.duration_ms || 0),
        sources: Array.isArray(item.sources) ? item.sources.slice(0, 8).map((url) => String(url || '').trim()).filter(Boolean) : [],
        error: String(item.error || ''),
        summaryText: pickReadableSummary(parsedPayload, outputPreview),
        keyFacts: buildKeyFacts(parsedPayload),
        searchResults: buildSearchResults(parsedPayload),
      };
    });
});

const packetSummary = computed(() => {
  if (!props.packet || typeof props.packet !== 'object') return '';
  const text = String(props.packet.summary || '').trim();
  return text.slice(0, 320);
});
const taskBriefText = computed(() => String(props.taskBrief || '').trim().slice(0, 320));

const titleText = computed(() => {
  return isZh.value ? '调用证据链' : 'Evidence Chain';
});

const taskBriefLabel = computed(() => (isZh.value ? '本次任务:' : 'Task:'));
const searchResultLabel = computed(() => (isZh.value ? '相关来源' : 'Relevant sources'));
const fallbackTool = computed(() => (isZh.value ? '工具' : 'Tool'));

function statusText(status) {
  const value = String(status || '').toLowerCase();
  if (isZh.value) {
    if (value === 'success') return '成功';
    if (value === 'error') return '失败';
    if (value === 'timeout') return '超时';
    return '未知';
  }
  if (value === 'success') return 'Success';
  if (value === 'error') return 'Error';
  if (value === 'timeout') return 'Timeout';
  return 'Unknown';
}

function statusClass(status) {
  const value = String(status || '').toLowerCase();
  if (value === 'success') return 'bg-emerald-500/20 text-emerald-200';
  if (value === 'error') return 'bg-rose-500/20 text-rose-200';
  if (value === 'timeout') return 'bg-amber-500/20 text-amber-200';
  return 'bg-white/10 text-text-secondary';
}

function durationLabel(durationMs) {
  const ms = Math.max(0, Number(durationMs || 0));
  return `${ms}ms`;
}

function hasObjectContent(value) {
  return value && typeof value === 'object' && Object.keys(value).length > 0;
}

function sourceHost(url) {
  try {
    return new URL(String(url || '')).hostname.replace(/^www\./i, '');
  } catch {
    return String(url || '');
  }
}

function parseOutputPayload(text) {
  const raw = String(text || '').trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    // Some tool outputs may contain trailing text or truncated JSON.
    const firstBrace = raw.indexOf('{');
    const lastBrace = raw.lastIndexOf('}');
    if (firstBrace >= 0 && lastBrace > firstBrace) {
      try {
        return JSON.parse(raw.slice(firstBrace, lastBrace + 1));
      } catch {
        return null;
      }
    }
    return null;
  }
}

function pickReadableSummary(parsed, rawPreview) {
  if (parsed && typeof parsed === 'object') {
    const summary = String(parsed.summary || '').trim();
    if (summary) return sanitizeSummaryText(summary, 320);
  }
  const compact = stripCodeFence(String(rawPreview || '')).replace(/\s+/g, ' ').trim();
  if (!compact) {
    return isZh.value ? '已完成该次工具调用并返回数据。' : 'Tool call completed and data returned.';
  }
  if (isJsonLikeText(compact)) {
    return isZh.value ? '已完成该次工具调用并返回结构化数据。' : 'Tool call completed and structured data returned.';
  }
  return sanitizeSummaryText(compact, 220);
}

function stripCodeFence(text) {
  return String(text || '')
    .replace(/```json/gi, '')
    .replace(/```/g, '')
    .trim();
}

function isJsonLikeText(text) {
  const compact = String(text || '').trim();
  if (!compact) return false;
  if (/^[\[{]/.test(compact)) return true;
  if (compact.includes('{"') || compact.includes("':") || compact.includes('":')) return true;
  if (/"[\w\-\s]+"\s*:/.test(compact)) return true;
  return false;
}

function sanitizeSummaryText(text, maxLen) {
  const cleaned = String(text || '')
    .replace(/\\n/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/^[\s"'`]+|[\s"'`]+$/g, '')
    .trim();
  return cleaned.slice(0, maxLen);
}

function buildKeyFacts(parsed) {
  if (!parsed || typeof parsed !== 'object') return [];
  const rootData = parsed.data && typeof parsed.data === 'object' ? parsed.data : {};
  const data = rootData.data && typeof rootData.data === 'object' ? rootData.data : rootData;
  if (!data || typeof data !== 'object') return [];

  const keysPriority = [
    'symbol',
    'name',
    'period',
    'current_price',
    'price',
    'previous_close',
    'change',
    'change_percent',
    'market_cap',
    'volume',
    'amount',
    'fifty_two_week_high',
    'fifty_two_week_low',
    'total_assets',
    'total_liabilities',
    'stockholders_equity',
    'net_income',
    'revenue',
    'cash',
    'free_cash_flow',
  ];

  const keyLabelZh = {
    symbol: '代码',
    name: '名称',
    period: '周期',
    current_price: '当前价格',
    price: '价格',
    previous_close: '昨收',
    change: '涨跌额',
    change_percent: '涨跌幅',
    market_cap: '市值',
    volume: '成交量',
    amount: '成交额',
    fifty_two_week_high: '52周最高',
    fifty_two_week_low: '52周最低',
    total_assets: '总资产',
    total_liabilities: '总负债',
    stockholders_equity: '股东权益',
    net_income: '净利润',
    revenue: '营收',
    cash: '现金',
    free_cash_flow: '自由现金流',
  };
  const keyLabelEn = {
    symbol: 'Symbol',
    name: 'Name',
    period: 'Period',
    current_price: 'Current Price',
    price: 'Price',
    previous_close: 'Prev Close',
    change: 'Change',
    change_percent: 'Change %',
    market_cap: 'Market Cap',
    volume: 'Volume',
    amount: 'Turnover',
    fifty_two_week_high: '52W High',
    fifty_two_week_low: '52W Low',
    total_assets: 'Total Assets',
    total_liabilities: 'Total Liabilities',
    stockholders_equity: 'Equity',
    net_income: 'Net Income',
    revenue: 'Revenue',
    cash: 'Cash',
    free_cash_flow: 'Free Cash Flow',
  };
  const labelMap = isZh.value ? keyLabelZh : keyLabelEn;

  const out = [];
  keysPriority.forEach((key) => {
    if (!(key in data)) return;
    const value = data[key];
    if (value === null || value === undefined) return;
    if (typeof value === 'object') return;
    out.push({
      label: labelMap[key] || key,
      value: formatFactValue(key, value),
    });
  });
  return out.slice(0, 8);
}

function formatFactValue(key, value) {
  const k = String(key || '').toLowerCase();
  if (typeof value === 'number' && Number.isFinite(value)) {
    if (k.includes('percent')) return `${value}%`;
    if (k.includes('market_cap') || k.includes('amount') || k.includes('assets') || k.includes('liabilities') || k.includes('equity') || k.includes('revenue') || k.includes('income') || k.includes('cash')) {
      return new Intl.NumberFormat(isZh.value ? 'zh-CN' : 'en-US', { maximumFractionDigits: 2 }).format(value);
    }
    return new Intl.NumberFormat(isZh.value ? 'zh-CN' : 'en-US', { maximumFractionDigits: 4 }).format(value);
  }
  return String(value);
}

function buildSearchResults(parsed) {
  if (!parsed || typeof parsed !== 'object') return [];
  const results = Array.isArray(parsed.results) ? parsed.results : [];
  return results
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      title: String(item.title || '').trim(),
      url: String(item.url || '').trim(),
    }))
    .filter((item) => item.title && item.url)
    .slice(0, 3);
}
</script>
