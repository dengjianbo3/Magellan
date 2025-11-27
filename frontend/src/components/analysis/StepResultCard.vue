<template>
  <div class="step-result-card mt-3">
    <!-- 纯文本结果 (String) -->
    <div v-if="typeof result === 'string'" class="result-content generic group">
      <div class="markdown-content relative">
        <div 
          class="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed"
          v-html="renderMarkdown(result)"
        ></div>
      </div>
    </div>

    <!-- 市场规模结果 (如果不是Markdown分析) -->
    <div v-else-if="isMarketSizeResult" class="result-content market-size">
      <div class="grid grid-cols-2 gap-4 mb-3">
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.tam') }}</span>
          <span class="text-sm font-bold text-white">{{ result.tam || 'N/A' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.sam') }}</span>
          <span class="text-sm font-bold text-white">{{ result.sam || 'N/A' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.growthRate') }}</span>
          <span class="text-sm font-bold text-emerald-400">{{ result.growth_rate || 'N/A' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.marketMaturity') }}</span>
          <span class="text-sm font-bold text-white">{{ result.market_maturity || 'N/A' }}</span>
        </div>
      </div>
      <div v-if="result.score" class="absolute top-3 right-3 px-2.5 py-1 rounded-lg text-xs font-bold border" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 竞争格局结果 (如果不是Markdown分析) -->
    <div v-else-if="isCompetitionResult" class="result-content competition">
      <div v-if="result.top_players && result.top_players.length" class="mb-3">
        <div class="text-xs text-gray-400 uppercase tracking-wider font-medium mb-2">{{ t('analysisWizard.topPlayers') }}</div>
        <div class="flex flex-wrap gap-2">
          <div v-for="(player, idx) in result.top_players" :key="idx" class="inline-flex items-center gap-2 px-2.5 py-1 bg-white/5 border border-white/10 rounded text-xs text-white">
            <template v-if="typeof player === 'object'">
              <span class="font-medium">{{ player.name }}</span>
              <span v-if="player.market_share" class="text-gray-400 text-[10px]">{{ player.market_share }}</span>
            </template>
            <template v-else>
              <span class="font-medium">{{ player }}</span>
            </template>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 mt-3">
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.marketConcentration') }}</span>
          <span class="text-sm font-bold text-white">{{ result.market_concentration || 'N/A' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.entryBarriers') }}</span>
          <span class="text-sm font-bold text-white">{{ result.entry_barriers || 'N/A' }}</span>
        </div>
      </div>
      <div v-if="result.score" class="absolute top-3 right-3 px-2.5 py-1 rounded-lg text-xs font-bold border" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 趋势分析结果 (如果不是Markdown分析) -->
    <div v-else-if="isTrendResult" class="result-content trend">
      <div v-if="result.key_trends && result.key_trends.length" class="mb-3">
        <div class="text-xs text-gray-400 uppercase tracking-wider font-medium mb-2">{{ t('analysisWizard.keyTrends') }}</div>
        <div class="flex flex-wrap gap-2">
          <span v-for="(trend, idx) in result.key_trends" :key="idx" class="px-2.5 py-1 bg-white/5 border border-white/10 rounded text-xs text-white">
            {{ typeof trend === 'object' ? trend.trend || trend.name : trend }}
          </span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 mt-3">
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.techDirection') }}</span>
          <span class="text-sm font-bold text-white">{{ result.tech_direction || 'N/A' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-400 uppercase tracking-wider font-medium">{{ t('analysisWizard.policySupport') }}</span>
          <span class="text-sm font-bold text-white">{{ result.policy_support || 'N/A' }}</span>
        </div>
      </div>
      <div v-if="result.score" class="absolute top-3 right-3 px-2.5 py-1 rounded-lg text-xs font-bold border" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 机会扫描结果 (如果不是Markdown分析) -->
    <div v-else-if="isOpportunityResult" class="result-content opportunity">
      <div v-if="result.opportunities && result.opportunities.length" class="mb-3">
        <div class="text-xs text-gray-400 uppercase tracking-wider font-medium mb-2">{{ t('analysisWizard.investmentOpportunities') }}</div>
        <ul class="space-y-2">
          <li v-for="(opp, idx) in result.opportunities" :key="idx" class="text-xs text-white leading-relaxed pl-3 relative before:content-[''] before:absolute before:left-0 before:top-1.5 before:w-1 before:h-1 before:rounded-full before:bg-primary">
            <template v-if="typeof opp === 'object'">
              <strong class="text-primary-light">{{ opp.name }}</strong>
              <span v-if="opp.potential" class="ml-1 text-emerald-400 font-medium">({{ opp.potential }})</span>
              <div v-if="opp.description" class="mt-0.5 text-gray-400">{{ opp.description }}</div>
            </template>
            <template v-else>{{ opp }}</template>
          </li>
        </ul>
      </div>
      <div v-if="result.sub_sectors && result.sub_sectors.length" class="mt-3">
        <div class="text-xs text-gray-400 uppercase tracking-wider font-medium mb-2">{{ t('analysisWizard.subSectors') }}</div>
        <div class="flex flex-wrap gap-2">
          <span v-for="(sector, idx) in result.sub_sectors" :key="idx" class="px-2.5 py-1 bg-primary/20 border border-primary/30 rounded text-xs text-primary-light font-medium">
            {{ sector }}
          </span>
        </div>
      </div>
      <div v-if="result.score" class="absolute top-3 right-3 px-2.5 py-1 rounded-lg text-xs font-bold border" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>

    <!-- 通用结果展示 (Markdown渲染) -->
    <div v-else class="result-content generic group">
      <!-- 主要分析内容 (Markdown) -->
      <div v-if="result.analysis || result.summary" class="markdown-content relative">
        <div 
          class="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed transition-all duration-500 ease-in-out"
          :class="{ 'max-h-32 overflow-hidden mask-bottom': !isExpanded }"
          v-html="renderMarkdown(result.analysis || result.summary)"
        ></div>
        
        <!-- 展开/收起 按钮 -->
        <button 
          @click="toggleExpand" 
          class="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 bg-black/60 backdrop-blur-md border border-white/10 rounded-full px-4 py-1 text-xs font-bold text-primary hover:text-white hover:bg-primary/80 transition-all flex items-center gap-1 shadow-lg z-10"
        >
          <span>{{ isExpanded ? t('common.collapse') : t('common.expand') }}</span>
          <span class="material-symbols-outlined text-sm transition-transform duration-300" :class="{ 'rotate-180': isExpanded }">expand_more</span>
        </button>
      </div>

      <!-- 其他关键指标 (kv对) -->
      <div v-if="hasImportantFields" class="mt-6 pt-4 border-t border-white/5 grid grid-cols-2 gap-4">
        <div v-for="(value, key) in importantFields" :key="key" class="flex flex-col gap-1">
          <span class="text-xs text-gray-500 uppercase tracking-wider">{{ formatLabel(key) }}</span>
          <span class="font-bold text-white text-sm">{{ formatValue(value) }}</span>
        </div>
      </div>

      <!-- 评分 -->
      <div v-if="result.score" class="absolute top-4 right-4 px-2.5 py-1 rounded-lg text-xs font-bold border shadow-lg" :class="getScoreClass(result.score)">
        {{ (result.score * 100).toFixed(0) }}{{ t('analysisWizard.score') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import { marked } from 'marked';

const { t } = useLanguage();

const props = defineProps({
  result: {
    type: Object,
    required: true
  },
  stepType: {
    type: String,
    default: ''
  }
});

const isExpanded = ref(false);

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
}

// Markdown 渲染
function renderMarkdown(content) {
  if (!content) return '';
  try {
    return marked.parse(content);
  } catch (e) {
    console.error('Markdown parsing error:', e);
    return content;
  }
}

// 判断结果类型
const isMarketSizeResult = computed(() => {
  // 只有当没有 analysis 字段且有特定的结构化字段时，才使用旧的显示方式
  return props.stepType === 'market_size_check' && !props.result.analysis && (props.result.tam || props.result.sam);
});

const isCompetitionResult = computed(() => {
  return props.stepType === 'competition_landscape' && !props.result.analysis && (props.result.top_players || props.result.market_concentration);
});

const isTrendResult = computed(() => {
  return props.stepType === 'trend_analysis' && !props.result.analysis && (props.result.key_trends || props.result.tech_direction);
});

const isOpportunityResult = computed(() => {
  return props.stepType === 'opportunity_scan' && !props.result.analysis && (props.result.opportunities || props.result.sub_sectors);
});

// 提取重要字段 (排除已在Markdown中显示的字段和内部字段)
const importantFields = computed(() => {
  const excludeKeys = [
    'score', 'summary', 'analysis', 'raw_output', 'agent', 'recommendation', // 已处理或不需要显示的字段
    'tam', 'sam', 'growth_rate', 'market_maturity', // 市场分析字段
    'top_players', 'market_concentration', 'entry_barriers', // 竞争分析字段
    'key_trends', 'tech_direction', 'policy_support', // 趋势分析字段
    'opportunities', 'sub_sectors', 'innovations' // 机会分析字段
  ];
  const fields = {};
  for (const [key, value] of Object.entries(props.result)) {
    // 只显示基本类型的数据，不显示复杂对象
    if (!excludeKeys.includes(key) && value !== null && value !== undefined && typeof value !== 'object') {
      fields[key] = value;
    }
  }
  return fields;
});

const hasImportantFields = computed(() => {
  return Object.keys(importantFields.value).length > 0;
});

function getScoreClass(score) {
  if (score >= 0.8) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  if (score >= 0.6) return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  if (score >= 0.4) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
}

function formatLabel(key) {
  const labelMap = {
    'revenue_assessment': t('analysisWizard.revenueAssessment'),
    'cash_flow': t('analysisWizard.cashFlow'),
    'profitability': t('analysisWizard.profitability'),
    'concerns': t('analysisWizard.concernsLabel'),
    'valuation_level': t('analysisWizard.valuationLevel'),
    'pe_ratio': t('analysisWizard.peRatio'),
    'price_target': t('analysisWizard.priceTarget')
  };
  return labelMap[key] || key.replace(/_/g, ' ');
}

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  return String(value);
}
</script>

<style scoped>
.step-result-card {
  margin-top: 12px;
}

.result-content {
  position: relative;
  padding: 24px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  border-left: 3px solid var(--primary-color, #38bdf8);
  backdrop-filter: blur(12px);
  transition: all 0.3s ease;
}

.result-content:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.1);
}

.mask-bottom {
  mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
}

/* Prose Overrides for Dark Mode */
:deep(.prose) {
  color: #d1d5db;
}
:deep(.prose h1), :deep(.prose h2), :deep(.prose h3), :deep(.prose h4) {
  color: #f3f4f6;
  font-weight: 600;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}
:deep(.prose h2) {
  font-size: 1.1em;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 0.3em;
}
:deep(.prose h3) {
  font-size: 1em;
  color: #38bdf8; 
}
:deep(.prose ul), :deep(.prose ol) {
  margin-top: 0.5em;
  margin-bottom: 0.5em;
  padding-left: 1.2em;
}
:deep(.prose li) {
  margin-top: 0.2em;
  margin-bottom: 0.2em;
}
:deep(.prose strong) {
  color: #fff;
  font-weight: 600;
}
</style>