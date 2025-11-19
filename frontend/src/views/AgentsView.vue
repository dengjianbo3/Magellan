<template>
  <div class="space-y-8">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-display font-bold text-white mb-2 tracking-tight">{{ t('agents.title') }}</h1>
        <p class="text-text-secondary text-lg">{{ t('agents.subtitle') }}</p>
      </div>
      <button class="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-bold shadow-glow-sm hover:shadow-glow transition-all duration-300 group">
        <span class="material-symbols-outlined group-hover:rotate-90 transition-transform">add</span>
        {{ t('agents.createCustomAgent') }}
      </button>
    </div>

    <!-- Agents Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
import { ref, computed } from 'vue';
import { useLanguage } from '../composables/useLanguage';

const { t } = useLanguage();

const showConfigModal = ref(false);
const configForm = ref({
  name: '',
  model: 'gpt-4',
  temperature: 0.7,
  systemPrompt: '',
  maxTokens: 2000
});

const agents = computed(() => [
  {
    id: 1,
    name: t('analysis.step2.agents.marketAnalyst.name'),
    role: t('analysis.step2.agents.marketAnalyst.role'),
    icon: 'show_chart',
    status: 'active',
    description: t('analysis.step2.agents.marketAnalyst.description'),
    analysisCount: 156,
    avgResponse: '2.3s',
    capabilities: ['Market Research', 'Competitor Analysis', 'Trend Forecasting']
  },
  {
    id: 2,
    name: t('analysis.step2.agents.financialExpert.name'),
    role: t('analysis.step2.agents.financialExpert.role'),
    icon: 'account_balance',
    status: 'active',
    description: t('analysis.step2.agents.financialExpert.description'),
    analysisCount: 142,
    avgResponse: '3.1s',
    capabilities: ['Financial Modeling', 'Ratio Analysis', 'Valuation']
  },
  {
    id: 3,
    name: t('analysis.step2.agents.teamEvaluator.name'),
    role: t('analysis.step2.agents.teamEvaluator.role'),
    icon: 'groups',
    status: 'active',
    description: t('analysis.step2.agents.teamEvaluator.description'),
    analysisCount: 98,
    avgResponse: '2.8s',
    capabilities: ['Leadership Analysis', 'Culture Assessment', 'HR Review']
  },
  {
    id: 4,
    name: t('analysis.step2.agents.riskAssessor.name'),
    role: t('analysis.step2.agents.riskAssessor.role'),
    icon: 'shield',
    status: 'active',
    description: t('analysis.step2.agents.riskAssessor.description'),
    analysisCount: 134,
    avgResponse: '2.5s',
    capabilities: ['Risk Identification', 'Impact Analysis', 'Mitigation Planning']
  },
  {
    id: 5,
    name: t('analysis.step2.agents.techSpecialist.name'),
    role: t('analysis.step2.agents.techSpecialist.role'),
    icon: 'computer',
    status: 'inactive',
    description: t('analysis.step2.agents.techSpecialist.description'),
    analysisCount: 67,
    avgResponse: '4.2s',
    capabilities: ['Tech Stack Review', 'Innovation Assessment', 'IP Analysis']
  },
  {
    id: 6,
    name: t('analysis.step2.agents.legalAdvisor.name'),
    role: t('analysis.step2.agents.legalAdvisor.role'),
    icon: 'gavel',
    status: 'inactive',
    description: t('analysis.step2.agents.legalAdvisor.description'),
    analysisCount: 45,
    avgResponse: '3.8s',
    capabilities: ['Compliance Review', 'Contract Analysis', 'Regulatory Assessment']
  }
]);

const toggleMenu = (agentId) => {
  console.log('Toggle menu for agent:', agentId);
};

const configureAgent = (agentId) => {
  const agent = agents.value.find(a => a.id === agentId);
  if (agent) {
    configForm.value = {
      name: agent.name,
      model: 'gpt-4',
      temperature: 0.7,
      systemPrompt: `You are a ${agent.role} expert. ${agent.description}`,
      maxTokens: 2000
    };
    showConfigModal.value = true;
  }
};

const toggleAgentStatus = (agentId) => {
  // In a real app, we would update the state via an API
  const agent = agents.value.find(a => a.id === agentId);
  if (agent) {
    // Since agents is computed, we can't mutate it directly in a clean way if it's purely derived.
    // For this mockup, we assume agents data structure allows mutation or we'd use a local reactive copy.
    // However, since we used 'computed' to get translations, we can't mutate it easily.
    // Better pattern: fetch raw data, then format with computed.
    // For this UI demo, we'll just log it.
    console.log(`Toggle status for agent ${agentId}`);
  }
};

const saveAgentConfig = () => {
  console.log('Saving agent config:', configForm.value);
  showConfigModal.value = false;
};
</script>