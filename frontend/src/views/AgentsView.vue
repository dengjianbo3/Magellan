<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-text-primary mb-2">AI Agents</h1>
        <p class="text-text-secondary">Configure and manage your AI analysis agents</p>
      </div>
      <button class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-background-dark font-semibold hover:bg-primary/90 transition-colors">
        <span class="material-symbols-outlined">add</span>
        Create Custom Agent
      </button>
    </div>

    <!-- Agents Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="bg-surface border border-border-color rounded-lg p-6 hover:border-primary/50 transition-colors"
      >
        <!-- Agent Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div
              :class="[
                'w-12 h-12 rounded-lg flex items-center justify-center',
                agent.status === 'active' ? 'bg-primary/20' : 'bg-surface-light'
              ]"
            >
              <span
                :class="[
                  'material-symbols-outlined text-2xl',
                  agent.status === 'active' ? 'text-primary' : 'text-text-secondary'
                ]"
              >
                {{ agent.icon }}
              </span>
            </div>
            <div>
              <h3 class="font-bold text-text-primary">{{ agent.name }}</h3>
              <p class="text-xs text-text-secondary">{{ agent.role }}</p>
            </div>
          </div>
          <div class="relative">
            <button
              @click="toggleMenu(agent.id)"
              class="p-1 rounded hover:bg-background-dark transition-colors"
            >
              <span class="material-symbols-outlined text-text-secondary">more_vert</span>
            </button>
          </div>
        </div>

        <!-- Agent Description -->
        <p class="text-sm text-text-secondary mb-4">{{ agent.description }}</p>

        <!-- Agent Stats -->
        <div class="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-border-color">
          <div>
            <p class="text-xs text-text-secondary mb-1">Analyses</p>
            <p class="text-lg font-bold text-text-primary">{{ agent.analysisCount }}</p>
          </div>
          <div>
            <p class="text-xs text-text-secondary mb-1">Avg Response</p>
            <p class="text-lg font-bold text-text-primary">{{ agent.avgResponse }}</p>
          </div>
        </div>

        <!-- Agent Capabilities -->
        <div class="mb-4">
          <p class="text-xs font-semibold text-text-secondary mb-2">Capabilities</p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(capability, index) in agent.capabilities"
              :key="index"
              class="text-xs px-2 py-1 rounded bg-background-dark border border-border-color text-text-primary"
            >
              {{ capability }}
            </span>
          </div>
        </div>

        <!-- Agent Actions -->
        <div class="flex items-center gap-2">
          <button
            @click="configureAgent(agent.id)"
            class="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors text-sm font-semibold"
          >
            <span class="material-symbols-outlined text-sm">settings</span>
            Configure
          </button>
          <button
            @click="toggleAgentStatus(agent.id)"
            :class="[
              'flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg text-sm font-semibold transition-colors',
              agent.status === 'active'
                ? 'bg-accent-yellow/20 text-accent-yellow hover:bg-accent-yellow/30'
                : 'bg-accent-green/20 text-accent-green hover:bg-accent-green/30'
            ]"
          >
            <span class="material-symbols-outlined text-sm">
              {{ agent.status === 'active' ? 'pause' : 'play_arrow' }}
            </span>
            {{ agent.status === 'active' ? 'Pause' : 'Activate' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Agent Configuration Modal (Simplified) -->
    <div
      v-if="showConfigModal"
      class="fixed inset-0 bg-background-dark/80 flex items-center justify-center z-50"
      @click.self="showConfigModal = false"
    >
      <div class="bg-surface border border-border-color rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-text-primary">Configure Agent</h2>
          <button
            @click="showConfigModal = false"
            class="p-1 rounded hover:bg-background-dark transition-colors"
          >
            <span class="material-symbols-outlined text-text-secondary">close</span>
          </button>
        </div>

        <div class="space-y-6">
          <!-- Agent Name -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">Agent Name</label>
            <input
              v-model="configForm.name"
              type="text"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <!-- Model Selection -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">AI Model</label>
            <select
              v-model="configForm.model"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
            >
              <option value="gpt-4">GPT-4 (Most Accurate)</option>
              <option value="gpt-3.5">GPT-3.5 (Balanced)</option>
              <option value="claude-2">Claude 2 (Long Context)</option>
            </select>
          </div>

          <!-- Temperature -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">
              Temperature: {{ configForm.temperature }}
            </label>
            <input
              v-model="configForm.temperature"
              type="range"
              min="0"
              max="1"
              step="0.1"
              class="w-full"
            />
            <div class="flex justify-between text-xs text-text-secondary mt-1">
              <span>Precise</span>
              <span>Creative</span>
            </div>
          </div>

          <!-- System Prompt -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">System Prompt</label>
            <textarea
              v-model="configForm.systemPrompt"
              rows="4"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors resize-none"
            ></textarea>
          </div>

          <!-- Max Tokens -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">Max Tokens</label>
            <input
              v-model="configForm.maxTokens"
              type="number"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-3 pt-4">
            <button
              @click="showConfigModal = false"
              class="flex-1 px-4 py-3 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors font-semibold"
            >
              Cancel
            </button>
            <button
              @click="saveAgentConfig"
              class="flex-1 px-4 py-3 rounded-lg bg-primary text-background-dark hover:bg-primary/90 transition-colors font-semibold"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const showConfigModal = ref(false);
const configForm = ref({
  name: '',
  model: 'gpt-4',
  temperature: 0.7,
  systemPrompt: '',
  maxTokens: 2000
});

const agents = ref([
  {
    id: 1,
    name: 'Market Analyst',
    role: 'Market Intelligence',
    icon: 'show_chart',
    status: 'active',
    description: 'Analyzes market trends, competition, and industry dynamics with deep market research capabilities.',
    analysisCount: 156,
    avgResponse: '2.3s',
    capabilities: ['Market Research', 'Competitor Analysis', 'Trend Forecasting']
  },
  {
    id: 2,
    name: 'Financial Expert',
    role: 'Financial Analysis',
    icon: 'account_balance',
    status: 'active',
    description: 'Reviews financial statements, calculates key ratios, and performs valuation analysis.',
    analysisCount: 142,
    avgResponse: '3.1s',
    capabilities: ['Financial Modeling', 'Ratio Analysis', 'Valuation']
  },
  {
    id: 3,
    name: 'Team Evaluator',
    role: 'Team Assessment',
    icon: 'groups',
    status: 'active',
    description: 'Evaluates management team quality, organizational structure, and company culture.',
    analysisCount: 98,
    avgResponse: '2.8s',
    capabilities: ['Leadership Analysis', 'Culture Assessment', 'HR Review']
  },
  {
    id: 4,
    name: 'Risk Assessor',
    role: 'Risk Management',
    icon: 'shield',
    status: 'active',
    description: 'Identifies potential risks, evaluates their impact, and suggests mitigation strategies.',
    analysisCount: 134,
    avgResponse: '2.5s',
    capabilities: ['Risk Identification', 'Impact Analysis', 'Mitigation Planning']
  },
  {
    id: 5,
    name: 'Tech Specialist',
    role: 'Technology Review',
    icon: 'computer',
    status: 'inactive',
    description: 'Assesses technology stack, innovation capabilities, and technical debt.',
    analysisCount: 67,
    avgResponse: '4.2s',
    capabilities: ['Tech Stack Review', 'Innovation Assessment', 'IP Analysis']
  },
  {
    id: 6,
    name: 'Legal Advisor',
    role: 'Legal Compliance',
    icon: 'gavel',
    status: 'inactive',
    description: 'Reviews legal structure, compliance status, and regulatory requirements.',
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
  const agent = agents.value.find(a => a.id === agentId);
  if (agent) {
    agent.status = agent.status === 'active' ? 'inactive' : 'active';
  }
};

const saveAgentConfig = () => {
  console.log('Saving agent config:', configForm.value);
  showConfigModal.value = false;
};
</script>
