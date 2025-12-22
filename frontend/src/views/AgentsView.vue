<template>
  <div class="space-y-8">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-display font-bold text-white mb-2 tracking-tight">{{ t('agents.title') }}</h1>
        <p class="text-text-secondary text-lg">{{ t('agents.subtitle') }}</p>
      </div>
      <button @click="showCreateAgentInfo" class="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-bold shadow-glow-sm hover:shadow-glow transition-all duration-300 group">
        <span class="material-symbols-outlined group-hover:rotate-90 transition-transform">add</span>
        {{ t('agents.createCustomAgent') }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="flex flex-col items-center gap-4">
        <span class="material-symbols-outlined text-4xl text-primary animate-spin">progress_activity</span>
        <p class="text-text-secondary">Loading agents...</p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="agents.length === 0" class="flex flex-col items-center justify-center py-20">
      <span class="material-symbols-outlined text-6xl text-text-secondary mb-4">smart_toy</span>
      <h3 class="text-xl font-bold text-white mb-2">No Agents Found</h3>
      <p class="text-text-secondary">No AI agents are currently configured.</p>
    </div>

    <!-- Agents Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="glass-card rounded-2xl p-6 group relative overflow-hidden hover:-translate-y-1 transition-transform duration-300"
      >
        <!-- Background Glow -->
        <div class="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

        <!-- Agent Header -->
        <div class="relative z-10 flex items-start justify-between mb-6">
          <div class="flex items-center gap-4">
            <div
              :class="[
                'w-14 h-14 rounded-xl flex items-center justify-center border transition-all duration-300 shadow-lg',
                agent.status === 'active' 
                  ? 'bg-primary/10 border-primary/30 text-primary shadow-[0_0_15px_rgba(56,189,248,0.2)]' 
                  : 'bg-white/5 border-white/10 text-text-secondary'
              ]"
            >
              <span class="material-symbols-outlined text-3xl">{{ agent.icon }}</span>
            </div>
            <div>
              <h3 class="font-bold text-white text-lg">{{ agent.name }}</h3>
              <p class="text-xs font-medium text-primary uppercase tracking-wider">{{ agent.role }}</p>
            </div>
          </div>
          <div class="relative">
            <button
              @click="toggleMenu(agent.id)"
              class="p-2 rounded-lg hover:bg-white/10 text-text-secondary hover:text-white transition-colors"
            >
              <span class="material-symbols-outlined">more_vert</span>
            </button>
          </div>
        </div>

        <!-- Agent Description -->
        <p class="relative z-10 text-sm text-text-secondary mb-6 leading-relaxed h-12 line-clamp-2">{{ agent.description }}</p>

        <!-- Agent Stats -->
        <div class="relative z-10 grid grid-cols-2 gap-4 mb-6 pb-6 border-b border-white/10">
          <div class="bg-white/5 rounded-lg p-3 border border-white/5">
            <p class="text-xs text-text-secondary mb-1 uppercase tracking-wide">{{ t('agents.card.analyses') }}</p>
            <p class="text-lg font-bold text-white font-mono">{{ agent.analysisCount }}</p>
          </div>
          <div class="bg-white/5 rounded-lg p-3 border border-white/5">
            <p class="text-xs text-text-secondary mb-1 uppercase tracking-wide">{{ t('agents.card.avgResponse') }}</p>
            <p class="text-lg font-bold text-white font-mono">{{ agent.avgResponse }}</p>
          </div>
        </div>

        <!-- Agent Capabilities -->
        <div class="relative z-10 mb-6 h-16 overflow-hidden">
          <p class="text-xs font-bold text-text-secondary mb-3 uppercase tracking-wider flex items-center gap-2">
             <span class="material-symbols-outlined text-sm">bolt</span> {{ t('agents.card.capabilities') }}
          </p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(capability, index) in agent.capabilities"
              :key="index"
              class="text-[10px] font-bold px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-text-primary"
            >
              {{ capability }}
            </span>
          </div>
        </div>

        <!-- Agent Actions -->
        <div class="relative z-10 flex items-center gap-3">
          <button
            @click="configureAgent(agent.id)"
            class="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 text-text-primary hover:bg-white/10 transition-colors text-sm font-bold group/btn"
          >
            <span class="material-symbols-outlined text-lg group-hover/btn:rotate-45 transition-transform">settings</span>
            {{ t('agents.card.configure') }}
          </button>
          <button
            @click="toggleAgentStatus(agent.id)"
            :class="[
              'flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-bold transition-all border',
              agent.status === 'active'
                ? 'bg-amber-500/10 border-amber-500/20 text-amber-400 hover:bg-amber-500/20'
                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
            ]"
          >
            <span class="material-symbols-outlined text-lg">
              {{ agent.status === 'active' ? 'pause' : 'play_arrow' }}
            </span>
            {{ agent.status === 'active' ? t('agents.card.pause') : t('agents.card.activate') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Agent Configuration Modal -->
    <div
      v-if="showConfigModal"
      class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in"
      @click.self="showConfigModal = false"
    >
      <div class="glass-panel rounded-2xl p-8 max-w-2xl w-full mx-4 max-h-[85vh] overflow-y-auto border border-white/10 shadow-2xl">
        <div class="flex items-center justify-between mb-8 pb-6 border-b border-white/10">
          <div class="flex items-center gap-4">
             <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined">tune</span>
             </div>
             <h2 class="text-2xl font-bold text-white">{{ t('agents.configModal.title') }}</h2>
          </div>
          <button
            @click="showConfigModal = false"
            class="p-2 rounded-lg hover:bg-white/10 text-text-secondary hover:text-white transition-colors"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="space-y-6">
          <!-- Agent Name -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-2 uppercase tracking-wider">{{ t('agents.configModal.agentName') }}</label>
            <input
              v-model="configForm.name"
              type="text"
              class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
            />
          </div>

          <!-- Model Selection -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-2 uppercase tracking-wider">{{ t('agents.configModal.aiModel') }}</label>
            <div class="relative">
                <select
                v-model="configForm.model"
                class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all appearance-none cursor-pointer"
                >
                <option value="gpt-4">{{ t('agents.configModal.models.gpt4') }}</option>
                <option value="gpt-3.5">{{ t('agents.configModal.models.gpt35') }}</option>
                <option value="claude-2">{{ t('agents.configModal.models.claude2') }}</option>
                </select>
                <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">expand_more</span>
            </div>
          </div>

          <!-- Temperature -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-4 uppercase tracking-wider">
              {{ t('agents.configModal.temperature') }}: <span class="text-primary">{{ configForm.temperature }}</span>
            </label>
            <input
              v-model="configForm.temperature"
              type="range"
              min="0"
              max="1"
              step="0.1"
              class="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-primary"
            />
            <div class="flex justify-between text-xs font-bold text-text-secondary mt-2 uppercase">
              <span>{{ t('agents.configModal.temperatureHint.precise') }}</span>
              <span>{{ t('agents.configModal.temperatureHint.creative') }}</span>
            </div>
          </div>

          <!-- System Prompt -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-2 uppercase tracking-wider">{{ t('agents.configModal.systemPrompt') }}</label>
            <textarea
              v-model="configForm.systemPrompt"
              rows="5"
              class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all resize-none font-mono text-sm leading-relaxed"
            ></textarea>
          </div>

          <!-- Max Tokens -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-2 uppercase tracking-wider">{{ t('agents.configModal.maxTokens') }}</label>
            <input
              v-model="configForm.maxTokens"
              type="number"
              class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
            />
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-4 pt-6 border-t border-white/10">
            <button
              @click="showConfigModal = false"
              class="flex-1 px-6 py-3 rounded-xl border border-white/10 text-text-primary hover:bg-white/5 transition-colors font-bold"
            >
              {{ t('agents.configModal.cancel') }}
            </button>
            <button
              @click="saveAgentConfig"
              class="flex-1 px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white hover:shadow-glow transition-all font-bold"
            >
              {{ t('agents.configModal.saveChanges') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useLanguage } from '../composables/useLanguage';
import { useToast } from '../composables/useToast';
import { API_BASE } from '@/config/api';

const { t, locale } = useLanguage();
const { success, error: showError, info } = useToast();

// Show create custom agent modal (coming soon)
const showCreateAgentInfo = () => {
  info(t('agents.createComingSoon') || 'Custom agent creation coming soon. Use the configuration options for now.');
};

const showConfigModal = ref(false);
const loading = ref(true);
const agentsData = ref([]);
const selectedAgentId = ref(null);

const configForm = ref({
  name: '',
  model: 'gpt-4',
  temperature: 0.7,
  systemPrompt: '',
  maxTokens: 2000
});

// Agent icon mapping
const agentIcons = {
  team_evaluator: 'groups',
  market_analyst: 'show_chart',
  financial_expert: 'account_balance',
  risk_assessor: 'shield',
  tech_specialist: 'computer',
  legal_advisor: 'gavel',
  technical_analyst: 'candlestick_chart',
  leader: 'supervisor_account',
  report_synthesizer: 'summarize',
  // Phase 2 新增 Agent
  macro_economist: 'trending_up',
  esg_analyst: 'eco',
  sentiment_analyst: 'mood',
  quant_strategist: 'analytics',
  deal_structurer: 'handshake',
  ma_advisor: 'merge'
};

// Fetch agents from API
const fetchAgents = async () => {
  loading.value = true;
  try {
    const response = await fetch(`${API_BASE}/api/agents`);
    if (response.ok) {
      const data = await response.json();
      agentsData.value = data.agents || [];
    } else {
      console.error('[Agents] Failed to fetch agents');
    }
  } catch (err) {
    console.error('[Agents] Error fetching agents:', err);
  } finally {
    loading.value = false;
  }
};

// Transform API data to display format
const agents = computed(() => {
  const lang = locale.value === 'zh-CN' ? 'zh' : 'en';

  return agentsData.value.map(agent => ({
    id: agent.agent_id,
    name: agent.name?.[lang] || agent.name?.zh || agent.agent_id,
    role: agent.type === 'special' ? 'Special Agent' : 'Atomic Agent',
    icon: agentIcons[agent.agent_id] || 'smart_toy',
    status: agent.enabled ? 'active' : 'inactive',
    description: agent.description?.[lang] || agent.description?.zh || '',
    analysisCount: agent.usage_count || 0,
    avgResponse: agent.estimated_duration?.quick ? `${agent.estimated_duration.quick}s` : 'N/A',
    capabilities: agent.capabilities?.slice(0, 3) || [],
    tags: agent.tags || [],
    successRate: agent.success_rate || 100
  }));
});

const toggleMenu = (agentId) => {
  console.log('Toggle menu for agent:', agentId);
};

const configureAgent = (agentId) => {
  const agent = agents.value.find(a => a.id === agentId);
  if (agent) {
    selectedAgentId.value = agentId;
    configForm.value = {
      name: agent.name,
      model: 'gpt-4',
      temperature: 0.7,
      systemPrompt: `You are a ${agent.role}. ${agent.description}`,
      maxTokens: 2000
    };
    showConfigModal.value = true;
  }
};

const toggleAgentStatus = async (agentId) => {
  const agent = agents.value.find(a => a.id === agentId);
  if (!agent) return;

  const newStatus = agent.status !== 'active';

  try {
    const response = await fetch(`${API_BASE}/api/agents/${agentId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: newStatus })
    });

    if (response.ok) {
      success(`Agent ${newStatus ? 'activated' : 'paused'} successfully`);
      await fetchAgents(); // Refresh the list
    } else {
      showError('Failed to update agent status');
    }
  } catch (err) {
    console.error('[Agents] Error toggling status:', err);
    showError('Failed to update agent status');
  }
};

const saveAgentConfig = async () => {
  if (!selectedAgentId.value) return;

  try {
    const response = await fetch(`${API_BASE}/api/agents/${selectedAgentId.value}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        temperature: configForm.value.temperature,
        max_tokens: configForm.value.maxTokens,
        custom_prompt: configForm.value.systemPrompt
      })
    });

    if (response.ok) {
      success('Agent configuration saved');
      showConfigModal.value = false;
      await fetchAgents();
    } else {
      showError('Failed to save configuration');
    }
  } catch (err) {
    console.error('[Agents] Error saving config:', err);
    showError('Failed to save configuration');
  }
};

onMounted(() => {
  fetchAgents();
});
</script>