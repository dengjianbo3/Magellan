<!-- src/views/ChatView.vue -->
<template>
  <div class="cockpit-container">
    <main class="task-flow-list" ref="taskFlowListEl">
      <div class="task-node ai">
        <div class="node-content">
          <p>您好！我是您的AI投资分析师。我们今天分析哪家公司？（例如，输入股票代码 'AAPL'）</p>
        </div>
      </div>
      <div v-for="session in sessions" :key="session.id" class="session-group">
        <div class="task-node user">
          <div class="node-content">
            <p>{{ session.prompt }}</p>
          </div>
        </div>
        <div v-for="step in session.steps" :key="step.id" class="task-node ai">
          <div class="node-header">
            <el-icon :class="{'is-loading': step.status === 'running'}">
              <component :is="step.icon" />
            </el-icon>
            <span>{{ step.title }}</span>
          </div>
          <div v-if="step.status === 'success' && step.result" class="node-content">
            <p>{{ step.result }}</p>
          </div>
        </div>
      </div>
    </main>
    <footer class="cockpit-input-area">
      <el-input
        v-model="newMessage"
        placeholder="请先输入一个股票代码开始分析..."
        class="input-field"
        size="large"
        @keyup.enter="startNewSession"
        :disabled="isThinking"
      >
        <template #append>
          <el-button :icon="Promotion" @click="startNewSession" :disabled="isThinking" />
        </template>
      </el-input>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, shallowRef } from 'vue';
import { ElInput, ElButton, ElIcon } from 'element-plus';
import { Promotion, Loading, CircleCheck, Cpu, Document } from '@element-plus/icons-vue';

interface Step {
  id: number;
  title: string;
  status: 'running' | 'success' | 'error';
  icon: any;
  result?: string;
}
interface Session {
  id: number;
  prompt: string;
  steps: Step[];
}

const newMessage = ref('');
const isThinking = ref(false);
const sessions = ref<Session[]>([]);
const taskFlowListEl = ref<HTMLElement | null>(null);

const scrollToBottom = () => {
  nextTick(() => {
    taskFlowListEl.value?.scrollTo({ top: taskFlowListEl.value.scrollHeight, behavior: 'smooth' });
  });
};

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const startNewSession = async () => {
  const prompt = newMessage.value.trim();
  if (prompt === '' || isThinking.value) return;
  isThinking.value = true;
  newMessage.value = '';
  const newSession: Session = { id: Date.now(), prompt, steps: [] };
  sessions.value.push(newSession);
  scrollToBottom();

  await sleep(500);
  const step1: Step = { id: 1, title: `正在获取 ${prompt.toUpperCase()} 的公开数据...`, status: 'running', icon: shallowRef(Loading) };
  newSession.steps.push(step1);
  scrollToBottom();
  
  await sleep(2000); 
  step1.status = 'success';
  step1.icon = shallowRef(CircleCheck);
  step1.result = `成功获取 ${prompt.toUpperCase()} 的公开数据。苹果公司是全球科技领导者... (此处将显示由后端生成的摘要)`;
  scrollToBottom();

  await sleep(500);
  const step2: Step = { id: 2, title: '正在分析您上传的文档...', status: 'running', icon: shallowRef(Loading) };
  newSession.steps.push(step2);
  scrollToBottom();

  await sleep(2500);
  step2.status = 'success';
  step2.icon = shallowRef(Document);
  step2.result = '财务报表和战略文档分析完毕。已识别出关键收入驱动因素和潜在风险。';
  scrollToBottom();

  await sleep(500);
  const step3: Step = { id: 3, title: '正在使用 Gemini 生成核心洞察...', status: 'running', icon: shallowRef(Loading) };
  newSession.steps.push(step3);
  scrollToBottom();

  await sleep(3000);
  step3.status = 'success';
  step3.icon = shallowRef(Cpu);
  step3.result = '已生成初步投资论点，并识别出3个值得考虑的追问问题。';
  scrollToBottom();

  isThinking.value = false;
};
</script>

<style scoped>
.cockpit-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.task-flow-list {
  flex-grow: 1;
  padding: 1.5rem;
  overflow-y: auto;
}
.session-group { margin-bottom: 2rem; }
.task-node {
  display: flex;
  margin-bottom: 1rem;
  animation: fadeIn 0.5s ease-in-out;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.task-node.user { justify-content: flex-end; }
.task-node.ai { justify-content: flex-start; flex-direction: column; }
.node-header {
  display: flex;
  align-items-center;
  font-size: 0.9rem;
  color: rgba(255,255,255,0.8);
  margin-bottom: 0.5rem;
}
.node-header .el-icon { margin-right: 8px; }
.is-loading { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }
.node-content {
  max-width: 90%;
  padding: 0.75rem 1.25rem;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.2);
  white-space: pre-wrap;
  line-height: 1.6;
}
.task-node.user .node-content {
  max-width: 70%;
  background: #764ba2;
}
.cockpit-input-area {
  padding: 1rem 1.5rem;
  border-top: var(--glass-border);
}
.input-field {
  --el-input-bg-color: rgba(0, 0, 0, 0.2);
  --el-input-text-color: white;
  --el-border-color: transparent;
}
</style>