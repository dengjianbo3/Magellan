<!-- src/views/ChatView.vue -->
<template>
  <div class="cockpit-container">
    <main class="task-flow-list" ref="taskFlowListEl">
      <div class="task-node ai">
        <div class="node-content">
          <p>您好！我是您的AI投资分析师。我们今天分析哪家公司？（例如，输入 'Apple'）</p>
        </div>
      </div>

      <div v-for="session in sessions" :key="session.id" class="session-group">
        <div class="task-node user">
          <div class="node-content"><p>{{ session.prompt }}</p></div>
        </div>
        <!-- Regular Steps -->
        <div v-for="step in session.steps" :key="step.id" class="task-node ai">
          <div class="node-header">
            <el-icon :class="{'is-loading': step.status === 'running'}"><component :is="getIcon(step.status)" /></el-icon>
            <span>{{ step.title }}</span>
          </div>
          <div v-if="step.result" :class="['node-content', { error: step.status === 'error' }]">
            <p>{{ step.result }}</p>
            <!-- HITL Ambiguity -->
            <div v-if="step.status === 'paused' && step.options" class="hitl-options">
              <el-button
                v-for="option in step.options"
                :key="option.ticker"
                @click="handleOptionSelection(session.id, option.ticker)"
                size="small" round >
                {{ option.name }} ({{ option.ticker }})
              </el-button>
            </div>
          </div>
        </div>
        <!-- Follow-up HITL Block -->
        <div v-if="session.followUp" class="task-node ai">
           <div class="node-header">
            <el-icon><component :is="getIcon('paused')" /></el-icon>
            <span>需要您介入 (核心功能)</span>
          </div>
          <div class="node-content">
            <p>初步分析已完成。我们已生成“关键追问问题”。您可以：</p>
            <div class="hitl-options">
               <el-button @click="emitViewReport(session.followUp)" type="primary" round>
                 立即查看报告
               </el-button>
                <el-button round>输入回答以深度分析</el-button>
            </div>
          </div>
        </div>
      </div>
    </main>
    <footer class="cockpit-input-area">
      <el-input v-model="newMessage" placeholder="请先输入一个公司名或股票代码开始分析..." @keyup.enter="startNewSession" :disabled="isThinking" />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, shallowRef } from 'vue';
import { ElInput, ElButton, ElIcon, ElMessage } from 'element-plus';
import { Loading, CircleCheck, CircleClose, QuestionFilled } from '@element-plus/icons-vue';
import { API_WS_URL, type AnalysisStep, type FullReport, type WebSocketMessage } from '../services/api';

interface FollowUpData {
  report: FullReport;
  questions: string[];
}

interface Session {
  id: string;
  prompt: string;
  steps: AnalysisStep[];
  followUp?: FollowUpData | null;
  socket?: WebSocket;
}

const emit = defineEmits(['view-report']);

const newMessage = ref('');
const isThinking = ref(false);
const sessions = ref<Session[]>([]);
const taskFlowListEl = ref<HTMLElement | null>(null);

const getIcon = (status: string) => {
  if (status === 'running') return shallowRef(Loading);
  if (status === 'success') return shallowRef(CircleCheck);
  if (status === 'error') return shallowRef(CircleClose);
  if (status === 'paused') return shallowRef(QuestionFilled);
  return shallowRef(CircleCheck);
};

const scrollToBottom = () => nextTick(() => taskFlowListEl.value?.scrollTo({ top: taskFlowListEl.value.scrollHeight, behavior: 'smooth' }));

const findOrCreateSession = (id: string, prompt: string): Session => {
  let session = sessions.value.find(s => s.id === id);
  if (!session) {
    // This might happen if the server sends a session_id before the client has created one
    const tempSession = sessions.value.find(s => s.id.startsWith('session_'));
    if (tempSession) {
      tempSession.id = id;
      session = tempSession;
    } else {
      session = { id, prompt, steps: [] };
      sessions.value.push(session);
    }
  }
  return session;
};

const userId = 'default_user'; // In a real app, this would come from an auth system

const startNewSession = () => {
  const prompt = newMessage.value.trim();
  if (prompt === '' || isThinking.value) return;

  isThinking.value = true;
  newMessage.value = '';

  const tempSessionId = `session_${Date.now()}`;
  const newSession: Session = { id: tempSessionId, prompt, steps: [] };
  sessions.value.push(newSession);
  scrollToBottom();

  const socket = new WebSocket(API_WS_URL);
  newSession.socket = socket;

  socket.onopen = () => {
    socket.send(JSON.stringify({ ticker: prompt, user_id: userId }));
  };

  socket.onmessage = (event) => {
    const message: WebSocketMessage = JSON.parse(event.data);
    const session = findOrCreateSession(message.session_id, prompt);

    if (message.step) {
      const existingStep = session.steps.find(s => s.id === message.step!.id);
      if (existingStep) {
        Object.assign(existingStep, message.step);
      } else {
        session.steps.push(message.step);
      }
    }

    if (message.status === 'hitl_follow_up_required') {
      session.followUp = {
        report: message.preliminary_report!,
        questions: message.key_questions!
      };
      isThinking.value = false;
    }
    
    if (message.status === 'error') {
        isThinking.value = false;
    }

    scrollToBottom();
  };

  socket.onerror = (error) => {
    ElMessage.error('WebSocket connection failed.');
    console.error('WebSocket Error:', error);
    isThinking.value = false;
  };

  socket.onclose = () => {
    // Clean up or notify user
    isThinking.value = false;
  };
};

const handleOptionSelection = (sessionId: string, selectedTicker: string) => {
  const session = sessions.value.find(s => s.id === sessionId);
  if (!session || !session.socket) return;

  // Visually update the step immediately
  const hitlStep = session.steps.find(s => s.status === 'paused');
  if (hitlStep) {
    hitlStep.status = 'running'; // Change status to show it's processing
    hitlStep.result = `You selected ${selectedTicker}. Continuing analysis...`;
    hitlStep.options = undefined; 
  }
  
  session.socket.send(JSON.stringify({ selected_ticker: selectedTicker }));
};

const emitViewReport = (followUpData: FollowUpData) => {
  emit('view-report', followUpData);
};
</script>
<style scoped>
.cockpit-container { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.task-flow-list { flex-grow: 1; padding: 1.5rem; overflow-y: auto; }
.session-group { margin-bottom: 2rem; }
.task-node { display: flex; margin-bottom: 1rem; animation: fadeIn 0.5s ease-in-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.task-node.user { justify-content: flex-end; }
.task-node.ai { justify-content: flex-start; flex-direction: column; }
.node-header { display: flex; align-items: center; font-size: 0.9rem; color: rgba(255,255,255,0.8); margin-bottom: 0.5rem; }
.node-header .el-icon { margin-right: 8px; }
.is-loading { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }
.node-content { max-width: 90%; padding: 0.75rem 1.25rem; border-radius: 12px; background: rgba(0, 0, 0, 0.2); white-space: pre-wrap; line-height: 1.6; }
.task-node.user .node-content { max-width: 70%; background: #764ba2; }
.cockpit-input-area { padding: 1rem 1.5rem; border-top: var(--glass-border); }
.hitl-options { margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.node-content.error { background: rgba(211, 47, 47, 0.2); border: 1px solid rgba(211, 47, 47, 0.5); }
</style>