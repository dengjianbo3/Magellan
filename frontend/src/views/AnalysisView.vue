<template>
  <div class="max-w-6xl mx-auto">
    <!-- Wizard Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-text-primary mb-2">{{ t('analysis.title') }}</h1>
      <p class="text-text-secondary">{{ t('analysis.subtitle') }}</p>
    </div>

    <!-- Progress Steps -->
    <div class="mb-8">
      <div class="flex items-center justify-between relative">
        <div class="absolute top-5 left-0 right-0 h-0.5 bg-border-color" style="z-index: 0"></div>
        <div
          class="absolute top-5 left-0 h-0.5 bg-primary transition-all duration-300"
          :style="{ width: progressWidth, zIndex: 0 }"
        ></div>

        <div
          v-for="(step, index) in steps"
          :key="step.id"
          class="flex flex-col items-center relative z-10"
          style="flex: 1"
        >
          <div
            :class="[
              'w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all duration-300 mb-2',
              currentStep > index
                ? 'bg-primary text-background-dark'
                : currentStep === index
                  ? 'bg-primary text-background-dark ring-4 ring-primary/20'
                  : 'bg-surface border-2 border-border-color text-text-secondary'
            ]"
          >
            <span v-if="currentStep > index" class="material-symbols-outlined">check</span>
            <span v-else>{{ index + 1 }}</span>
          </div>
          <div class="text-center">
            <p
              :class="[
                'text-sm font-semibold',
                currentStep >= index ? 'text-text-primary' : 'text-text-secondary'
              ]"
            >
              {{ step.title }}
            </p>
            <p class="text-xs text-text-secondary mt-1">{{ step.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Step Content -->
    <div class="bg-surface border border-border-color rounded-lg p-8 mb-6">
      <!-- Step 1: Project Information -->
      <div v-if="currentStep === 0">
        <h2 class="text-xl font-bold text-text-primary mb-6">{{ t('analysis.step1.title') }}</h2>
        <div class="space-y-6">
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">
              {{ t('analysis.step1.projectName') }} <span class="text-accent-red">*</span>
            </label>
            <input
              v-model="formData.projectName"
              type="text"
              :placeholder="t('analysis.step1.projectNamePlaceholder')"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">
              {{ t('analysis.step1.company') }} <span class="text-accent-red">*</span>
            </label>
            <input
              v-model="formData.company"
              type="text"
              :placeholder="t('analysis.step1.companyPlaceholder')"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">
              {{ t('analysis.step1.analysisType') }} <span class="text-accent-red">*</span>
            </label>
            <div class="grid grid-cols-2 gap-4">
              <button
                type="button"
                v-for="type in analysisTypes"
                :key="type.id"
                @click="formData.analysisType = type.id"
                :class="[
                  'p-4 rounded-lg border-2 transition-all text-left',
                  formData.analysisType === type.id
                    ? 'border-primary bg-primary/10'
                    : 'border-border-color hover:border-primary/50'
                ]"
              >
                <div class="flex items-start gap-3">
                  <span class="material-symbols-outlined text-primary mt-0.5">{{ type.icon }}</span>
                  <div>
                    <h4 class="font-semibold text-text-primary mb-1">{{ type.name }}</h4>
                    <p class="text-xs text-text-secondary">{{ type.description }}</p>
                  </div>
                </div>
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">
              {{ t('analysis.step1.description') }}
            </label>
            <textarea
              v-model="formData.description"
              rows="4"
              :placeholder="t('analysis.step1.descriptionPlaceholder')"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors resize-none"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Step 2: Select AI Agents -->
      <div v-if="currentStep === 1">
        <h2 class="text-xl font-bold text-text-primary mb-6">{{ t('analysis.step2.title') }}</h2>
        <p class="text-text-secondary mb-6">{{ t('analysis.step2.subtitle') }}</p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            v-for="agent in availableAgents"
            :key="agent.id"
            @click="toggleAgent(agent.id)"
            :class="[
              'p-5 rounded-lg border-2 transition-all text-left',
              formData.selectedAgents.includes(agent.id)
                ? 'border-primary bg-primary/10'
                : 'border-border-color hover:border-primary/50'
            ]"
          >
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center">
                  <span class="material-symbols-outlined text-primary">{{ agent.icon }}</span>
                </div>
                <div>
                  <h4 class="font-semibold text-text-primary">{{ agent.name }}</h4>
                  <p class="text-xs text-text-secondary">{{ agent.role }}</p>
                </div>
              </div>
              <span
                :class="[
                  'material-symbols-outlined transition-all',
                  formData.selectedAgents.includes(agent.id)
                    ? 'text-primary'
                    : 'text-text-secondary'
                ]"
              >
                {{ formData.selectedAgents.includes(agent.id) ? 'check_circle' : 'radio_button_unchecked' }}
              </span>
            </div>
            <p class="text-sm text-text-secondary">{{ agent.description }}</p>
            <div class="flex items-center gap-4 mt-3 pt-3 border-t border-border-color">
              <span class="text-xs text-text-secondary flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">speed</span>
                {{ agent.speed }}
              </span>
              <span class="text-xs text-text-secondary flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">psychology</span>
                {{ agent.expertise }}
              </span>
            </div>
          </button>
        </div>
      </div>

      <!-- Step 3: Data Sources & Configuration -->
      <div v-if="currentStep === 2">
        <h2 class="text-xl font-bold text-text-primary mb-6">{{ t('analysis.step3.title') }}</h2>

        <div class="space-y-6">
          <!-- Data Sources -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-3">
              {{ t('analysis.step3.dataSources') }}
            </label>
            <div class="space-y-3">
              <label
                v-for="source in dataSources"
                :key="source.id"
                class="flex items-center justify-between p-4 rounded-lg border border-border-color hover:border-primary/50 transition-colors cursor-pointer"
              >
                <div class="flex items-center gap-3">
                  <input
                    type="checkbox"
                    v-model="formData.dataSources"
                    :value="source.id"
                    class="w-5 h-5 rounded border-border-color text-primary focus:ring-primary focus:ring-offset-0"
                  />
                  <span class="material-symbols-outlined text-primary">{{ source.icon }}</span>
                  <div>
                    <p class="font-semibold text-text-primary">{{ source.name }}</p>
                    <p class="text-xs text-text-secondary">{{ source.description }}</p>
                  </div>
                </div>
                <span class="text-xs px-2 py-1 rounded-full bg-surface-light text-text-secondary">
                  {{ source.status }}
                </span>
              </label>
            </div>
          </div>

          <!-- Upload Documents -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-3">
              {{ t('analysis.step3.uploadDocuments') }}
            </label>
            <div
              class="border-2 border-dashed border-border-color rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
              @click="triggerFileUpload"
              @dragover.prevent
              @drop.prevent="handleFileDrop"
            >
              <span class="material-symbols-outlined text-4xl text-text-secondary mb-2">cloud_upload</span>
              <p class="text-sm text-text-primary font-semibold mb-1">
                {{ t('analysis.step3.uploadPrompt') }}
              </p>
              <p class="text-xs text-text-secondary">
                {{ t('analysis.step3.uploadHint') }}
              </p>
              <input
                ref="fileInput"
                type="file"
                multiple
                accept=".pdf,.docx,.xlsx,.csv"
                class="hidden"
                @change="handleFileSelect"
              />
            </div>

            <!-- Uploaded Files List -->
            <div v-if="formData.uploadedFiles.length > 0" class="mt-4 space-y-2">
              <div
                v-for="(file, index) in formData.uploadedFiles"
                :key="index"
                class="flex items-center justify-between p-3 rounded-lg bg-background-dark border border-border-color"
              >
                <div class="flex items-center gap-3">
                  <span class="material-symbols-outlined text-primary">description</span>
                  <div>
                    <p class="text-sm font-semibold text-text-primary">{{ file.name }}</p>
                    <p class="text-xs text-text-secondary">{{ formatFileSize(file.size) }}</p>
                  </div>
                </div>
                <button
                  @click="removeFile(index)"
                  class="text-text-secondary hover:text-accent-red transition-colors"
                >
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Analysis Priority -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-3">
              {{ t('analysis.step3.analysisPriority') }}
            </label>
            <div class="grid grid-cols-3 gap-4">
              <button
                type="button"
                v-for="priority in priorities"
                :key="priority.id"
                @click="formData.priority = priority.id"
                :class="[
                  'p-4 rounded-lg border-2 transition-all',
                  formData.priority === priority.id
                    ? 'border-primary bg-primary/10'
                    : 'border-border-color hover:border-primary/50'
                ]"
              >
                <span class="material-symbols-outlined text-2xl mb-2" :class="priority.color">
                  {{ priority.icon }}
                </span>
                <p class="font-semibold text-text-primary text-sm">{{ priority.name }}</p>
                <p class="text-xs text-text-secondary mt-1">{{ priority.time }}</p>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation Buttons -->
    <div class="flex items-center justify-between">
      <button
        type="button"
        v-if="currentStep > 0"
        @click="previousStep"
        class="flex items-center gap-2 px-6 py-3 rounded-lg border border-border-color text-text-primary hover:bg-surface transition-colors"
      >
        <span class="material-symbols-outlined">arrow_back</span>
        {{ t('analysis.buttons.previous') }}
      </button>
      <div v-else></div>

      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="cancelWizard"
          class="px-6 py-3 rounded-lg border border-border-color text-text-primary hover:bg-surface transition-colors"
        >
          {{ t('analysis.buttons.cancel') }}
        </button>
        <button
          type="button"
          v-if="currentStep < steps.length - 1"
          @click="canProceed && nextStep()"
          :class="[
            'flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-colors',
            canProceed
              ? 'bg-primary text-background-dark hover:bg-primary/90 cursor-pointer'
              : 'bg-surface text-text-secondary cursor-not-allowed pointer-events-none'
          ]"
        >
          {{ t('analysis.buttons.next') }}
          <span class="material-symbols-outlined">arrow_forward</span>
        </button>
        <button
          type="button"
          v-else
          @click="canProceed && startAnalysis()"
          :class="[
            'flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-colors',
            canProceed
              ? 'bg-primary text-background-dark hover:bg-primary/90 cursor-pointer'
              : 'bg-surface text-text-secondary cursor-not-allowed pointer-events-none'
          ]"
        >
          <span class="material-symbols-outlined">rocket_launch</span>
          {{ t('analysis.buttons.startAnalysis') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useLanguage } from '../composables/useLanguage';

const { t } = useLanguage();
const emit = defineEmits(['cancel', 'start-analysis']);

const currentStep = ref(0);
const fileInput = ref(null);

const steps = computed(() => [
  { id: 1, title: t('analysis.steps.projectInfo.title'), description: t('analysis.steps.projectInfo.description') },
  { id: 2, title: t('analysis.steps.selectAgents.title'), description: t('analysis.steps.selectAgents.description') },
  { id: 3, title: t('analysis.steps.configure.title'), description: t('analysis.steps.configure.description') }
]);

const formData = ref({
  projectName: '',
  company: '',
  analysisType: 'due-diligence',
  description: '',
  selectedAgents: ['market-analyst', 'financial-expert'],
  dataSources: ['financial-reports', 'market-data'],
  uploadedFiles: [],
  priority: 'normal'
});

const analysisTypes = computed(() => [
  {
    id: 'due-diligence',
    name: t('analysis.step1.types.dueDiligence.name'),
    description: t('analysis.step1.types.dueDiligence.description'),
    icon: 'fact_check'
  },
  {
    id: 'market-analysis',
    name: t('analysis.step1.types.marketAnalysis.name'),
    description: t('analysis.step1.types.marketAnalysis.description'),
    icon: 'trending_up'
  },
  {
    id: 'financial-review',
    name: t('analysis.step1.types.financialReview.name'),
    description: t('analysis.step1.types.financialReview.description'),
    icon: 'account_balance'
  },
  {
    id: 'competitive-analysis',
    name: t('analysis.step1.types.competitiveAnalysis.name'),
    description: t('analysis.step1.types.competitiveAnalysis.description'),
    icon: 'bar_chart'
  }
]);

const availableAgents = computed(() => [
  {
    id: 'market-analyst',
    name: t('analysis.step2.agents.marketAnalyst.name'),
    role: t('analysis.step2.agents.marketAnalyst.role'),
    description: t('analysis.step2.agents.marketAnalyst.description'),
    icon: 'show_chart',
    speed: t('analysis.step2.agents.marketAnalyst.speed'),
    expertise: t('analysis.step2.agents.marketAnalyst.expertise')
  },
  {
    id: 'financial-expert',
    name: t('analysis.step2.agents.financialExpert.name'),
    role: t('analysis.step2.agents.financialExpert.role'),
    description: t('analysis.step2.agents.financialExpert.description'),
    icon: 'account_balance',
    speed: t('analysis.step2.agents.financialExpert.speed'),
    expertise: t('analysis.step2.agents.financialExpert.expertise')
  },
  {
    id: 'team-evaluator',
    name: t('analysis.step2.agents.teamEvaluator.name'),
    role: t('analysis.step2.agents.teamEvaluator.role'),
    description: t('analysis.step2.agents.teamEvaluator.description'),
    icon: 'groups',
    speed: t('analysis.step2.agents.teamEvaluator.speed'),
    expertise: t('analysis.step2.agents.teamEvaluator.expertise')
  },
  {
    id: 'risk-assessor',
    name: t('analysis.step2.agents.riskAssessor.name'),
    role: t('analysis.step2.agents.riskAssessor.role'),
    description: t('analysis.step2.agents.riskAssessor.description'),
    icon: 'shield',
    speed: t('analysis.step2.agents.riskAssessor.speed'),
    expertise: t('analysis.step2.agents.riskAssessor.expertise')
  },
  {
    id: 'tech-specialist',
    name: t('analysis.step2.agents.techSpecialist.name'),
    role: t('analysis.step2.agents.techSpecialist.role'),
    description: t('analysis.step2.agents.techSpecialist.description'),
    icon: 'computer',
    speed: t('analysis.step2.agents.techSpecialist.speed'),
    expertise: t('analysis.step2.agents.techSpecialist.expertise')
  },
  {
    id: 'legal-advisor',
    name: t('analysis.step2.agents.legalAdvisor.name'),
    role: t('analysis.step2.agents.legalAdvisor.role'),
    description: t('analysis.step2.agents.legalAdvisor.description'),
    icon: 'gavel',
    speed: t('analysis.step2.agents.legalAdvisor.speed'),
    expertise: t('analysis.step2.agents.legalAdvisor.expertise')
  }
]);

const dataSources = computed(() => [
  {
    id: 'financial-reports',
    name: t('analysis.step3.sources.financialReports.name'),
    description: t('analysis.step3.sources.financialReports.description'),
    icon: 'description',
    status: t('analysis.step3.sources.financialReports.status')
  },
  {
    id: 'market-data',
    name: t('analysis.step3.sources.marketData.name'),
    description: t('analysis.step3.sources.marketData.description'),
    icon: 'candlestick_chart',
    status: t('analysis.step3.sources.marketData.status')
  },
  {
    id: 'news-sentiment',
    name: t('analysis.step3.sources.newsSentiment.name'),
    description: t('analysis.step3.sources.newsSentiment.description'),
    icon: 'newspaper',
    status: t('analysis.step3.sources.newsSentiment.status')
  },
  {
    id: 'company-data',
    name: t('analysis.step3.sources.companyData.name'),
    description: t('analysis.step3.sources.companyData.description'),
    icon: 'corporate_fare',
    status: t('analysis.step3.sources.companyData.status')
  }
]);

const priorities = computed(() => [
  {
    id: 'low',
    name: t('analysis.step3.priorities.low.name'),
    time: t('analysis.step3.priorities.low.time'),
    icon: 'schedule',
    color: 'text-text-secondary'
  },
  {
    id: 'normal',
    name: t('analysis.step3.priorities.normal.name'),
    time: t('analysis.step3.priorities.normal.time'),
    icon: 'timer',
    color: 'text-primary'
  },
  {
    id: 'high',
    name: t('analysis.step3.priorities.high.name'),
    time: t('analysis.step3.priorities.high.time'),
    icon: 'bolt',
    color: 'text-accent-yellow'
  }
]);

const progressWidth = computed(() => {
  return `${(currentStep.value / (steps.length - 1)) * 100}%`;
});

const canProceed = computed(() => {
  if (currentStep.value === 0) {
    const hasProjectName = !!formData.value.projectName;
    const hasCompany = !!formData.value.company;
    const hasAnalysisType = !!formData.value.analysisType;
    const result = hasProjectName && hasCompany && hasAnalysisType;

    console.log('[AnalysisView] Step 0 validation:', {
      projectName: formData.value.projectName,
      company: formData.value.company,
      analysisType: formData.value.analysisType,
      hasProjectName,
      hasCompany,
      hasAnalysisType,
      canProceed: result
    });

    return result;
  }
  if (currentStep.value === 1) {
    return formData.value.selectedAgents.length > 0;
  }
  if (currentStep.value === 2) {
    return formData.value.dataSources.length > 0;
  }
  return true;
});

// Watch for changes to debug reactivity
watch(canProceed, (newVal) => {
  console.log('[AnalysisView] canProceed changed to:', newVal);
});

watch(formData, (newVal) => {
  console.log('[AnalysisView] formData changed:', {
    projectName: newVal.projectName,
    company: newVal.company,
    analysisType: newVal.analysisType
  });
}, { deep: true });

const toggleAgent = (agentId) => {
  const index = formData.value.selectedAgents.indexOf(agentId);
  if (index > -1) {
    formData.value.selectedAgents.splice(index, 1);
  } else {
    formData.value.selectedAgents.push(agentId);
  }
};

const nextStep = () => {
  console.log('[AnalysisView] nextStep clicked! canProceed:', canProceed.value);
  if (currentStep.value < steps.value.length - 1) {
    currentStep.value++;
    console.log('[AnalysisView] Moving to step:', currentStep.value);
  }
};

const previousStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
};

const triggerFileUpload = () => {
  fileInput.value.click();
};

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  formData.value.uploadedFiles.push(...files);
};

const handleFileDrop = (event) => {
  const files = Array.from(event.dataTransfer.files);
  formData.value.uploadedFiles.push(...files);
};

const removeFile = (index) => {
  formData.value.uploadedFiles.splice(index, 1);
};

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const cancelWizard = () => {
  emit('cancel');
};

const startAnalysis = () => {
  console.log('Starting analysis with data:', formData.value);
  emit('start-analysis', formData.value);
};
</script>
