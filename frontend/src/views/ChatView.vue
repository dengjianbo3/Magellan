<!-- src/views/ChatView.vue - shadcn/ui + Tailwind -->
<template>
  <div class="flex h-full flex-col bg-background">
    <!-- 消息区域 -->
    <div ref="messagesAreaEl" class="flex-1 space-y-4 overflow-y-auto p-6">
      <!-- 欢迎消息 -->
      <div class="flex max-w-3xl gap-3 animate-in slide-in-from-bottom duration-300">
        <div class="h-10 w-10 flex-shrink-0 overflow-hidden rounded-full border-2 border-border bg-muted flex items-center justify-center">
          <span class="text-xl">🤖</span>
        </div>
        <div class="flex-1 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-foreground">AI 尽调助手</span>
            <span class="text-xs text-muted-foreground">现在</span>
          </div>
          <div class="rounded-lg border border-border bg-card p-4 shadow-sm">
            <p class="leading-relaxed text-foreground">您好！我是您的 AI 尽职调查助手。请告诉我您要分析的早期项目或初创公司名称，我将为您执行完整的投资尽调流程。</p>
            <p class="mt-2 text-sm text-muted-foreground">例如：深圳某AI科技公司、XX智能硬件项目</p>
          </div>
        </div>
      </div>

      <!-- 会话消息 -->
      <template v-for="session in sessions" :key="session.id">
        <!-- 用户消息 -->
        <div class="flex max-w-3xl flex-row-reverse gap-3 self-end animate-in slide-in-from-bottom duration-300">
          <div class="h-10 w-10 flex-shrink-0 overflow-hidden rounded-full border-2 border-border">
            <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" alt="User" class="h-full w-full object-cover" />
          </div>
          <div class="flex-1 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-foreground">您</span>
            </div>
            <div class="rounded-lg border border-primary/20 bg-primary/10 p-4">
              <p class="leading-relaxed text-foreground">{{ session.prompt }}</p>
            </div>
          </div>
        </div>

        <!-- AI 处理步骤 -->
        <div
          v-for="step in session.steps"
          :key="step.id"
          class="max-w-3xl overflow-hidden rounded-lg border border-border bg-card shadow-sm animate-in slide-in-from-bottom duration-300"
        >
          <div 
            class="flex items-center gap-3 border-b border-border bg-muted/50 px-4 py-3 cursor-pointer hover:bg-muted/70 transition-colors"
            @click="toggleStepExpanded(step.id)"
          >
            <div
              :class="[
                'flex h-8 w-8 items-center justify-center rounded-full',
                step.status === 'running' && 'bg-primary/10 text-primary',
                step.status === 'success' && 'bg-green-500/10 text-green-500',
                step.status === 'error' && 'bg-destructive/10 text-destructive',
                step.status === 'paused' && 'bg-yellow-500/10 text-yellow-500'
              ]"
            >
              <el-icon v-if="step.status === 'running'" class="is-loading">
                <Loading />
              </el-icon>
              <el-icon v-else-if="step.status === 'success'">
                <CircleCheck />
              </el-icon>
              <el-icon v-else-if="step.status === 'error'">
                <CircleClose />
              </el-icon>
              <el-icon v-else-if="step.status === 'paused'">
                <QuestionFilled />
              </el-icon>
            </div>
            <span class="flex-1 font-semibold text-foreground">{{ step.title }}</span>
            
            <!-- 展开/收起图标 -->
            <el-icon 
              v-if="step.sub_steps && step.sub_steps.length > 0"
              class="text-muted-foreground transition-transform"
              :class="{ 'rotate-180': expandedSteps.has(step.id) }"
            >
              <ArrowDown />
            </el-icon>
            
            <span
              v-if="step.status === 'running'"
              class="inline-flex items-center rounded-full bg-primary px-2.5 py-0.5 text-xs font-semibold text-primary-foreground"
            >
              处理中
            </span>
            <span
              v-else-if="step.status === 'success'"
              class="inline-flex items-center rounded-full bg-green-500 px-2.5 py-0.5 text-xs font-semibold text-white"
            >
              完成
            </span>
            <span
              v-else-if="step.status === 'error'"
              class="inline-flex items-center rounded-full bg-destructive px-2.5 py-0.5 text-xs font-semibold text-destructive-foreground"
            >
              失败
            </span>
          </div>

          <div v-if="step.result || expandedSteps.has(step.id)" class="p-4">
            <!-- 子步骤 (可展开) -->
            <div v-if="expandedSteps.has(step.id) && step.sub_steps && step.sub_steps.length > 0" class="mb-3 space-y-2">
              <div class="text-sm font-medium text-muted-foreground">详细步骤：</div>
              <div 
                v-for="(subStep, index) in step.sub_steps" 
                :key="index"
                class="flex items-center gap-2 text-sm text-foreground"
              >
                <div class="h-1.5 w-1.5 rounded-full bg-primary"></div>
                <span>{{ subStep }}</span>
              </div>
            </div>
            
            <!-- 结果 -->
            <div v-if="step.result" :class="['whitespace-pre-wrap leading-relaxed', step.status === 'error' ? 'text-destructive' : 'text-foreground']">
              {{ step.result }}
            </div>

            <!-- HITL 选项 -->
            <div v-if="step.status === 'paused' && step.options" class="mt-4 space-y-3 border-t border-border pt-4">
              <p class="text-sm text-muted-foreground">请选择要分析的公司：</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="option in step.options"
                  :key="option.ticker"
                  class="inline-flex items-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                  @click="handleOptionSelection(session.id, option.ticker)"
                >
                  {{ option.name }} ({{ option.ticker }})
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 人工审核节点 -->
        <div
          v-if="session.followUp"
          class="max-w-3xl overflow-hidden rounded-xl border border-primary/20 bg-gradient-to-br from-primary/10 to-primary/5 p-8 text-center shadow-lg animate-in zoom-in-50 duration-300"
        >
          <div class="mb-4 text-5xl animate-bounce">✋</div>
          <h3 class="mb-2 text-2xl font-bold text-foreground">初步分析完成</h3>
          <p class="mb-6 text-base leading-relaxed text-muted-foreground">
            我们已生成投资备忘录和关键追问问题。您可以查看报告并进行深度分析。
          </p>
          <div class="flex flex-wrap justify-center gap-3">
            <button
              class="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-base font-semibold text-primary-foreground shadow-md transition-all hover:bg-primary/90 hover:shadow-lg hover:-translate-y-0.5"
              @click="emitViewReport(session.followUp)"
            >
              <span>📊</span>
              <span>查看完整报告</span>
            </button>
            <button class="inline-flex items-center gap-2 rounded-lg border border-input bg-background px-6 py-3 text-base font-medium text-foreground shadow-sm transition-colors hover:bg-accent">
              <span>💬</span>
              <span>输入回答</span>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- 输入区域 -->
    <div class="border-t border-border bg-card p-4 shadow-lg">
      <div class="mx-auto max-w-3xl space-y-3">
        <!-- BP 文件上传 -->
        <div v-if="!isThinking" class="flex items-center gap-3 rounded-lg border border-dashed border-border bg-muted/30 p-3">
          <el-icon class="text-xl text-muted-foreground"><Upload /></el-icon>
          <div class="flex-1">
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.docx,.doc"
              @change="handleFileSelect"
              class="hidden"
            />
            <button
              @click="() => fileInputRef?.click()"
              class="text-sm font-medium text-foreground hover:text-primary transition-colors"
            >
              {{ selectedFile ? selectedFile.name : '上传 BP 文件（可选）' }}
            </button>
            <p class="mt-0.5 text-xs text-muted-foreground">
              支持 PDF、Word 格式，可选
            </p>
          </div>
          <button
            v-if="selectedFile"
            @click="clearFile"
            class="rounded-full p-1 hover:bg-destructive/10 transition-colors"
          >
            <el-icon class="text-lg text-destructive"><Close /></el-icon>
          </button>
        </div>

        <!-- 消息输入 -->
        <div class="flex gap-2">
          <div class="relative flex-1">
            <el-input
              v-model="newMessage"
              placeholder="输入项目名称或初创公司名称..."
              :disabled="isThinking"
              @keyup.enter="startNewSession"
              size="large"
              class="pr-12"
            >
              <template #prefix>
                <el-icon class="text-muted-foreground"><Search /></el-icon>
              </template>
            </el-input>
          </div>
          <button
            :disabled="!newMessage.trim() || isThinking"
            @click="startNewSession"
            class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-md transition-all hover:bg-primary/90 hover:shadow-lg hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-50"
          >
            <el-icon v-if="isThinking" class="is-loading text-xl"><Loading /></el-icon>
            <el-icon v-else class="text-xl"><Position /></el-icon>
          </button>
        </div>
        <div class="text-center text-xs text-muted-foreground">
          按 Enter 发送 • {{ selectedFile ? '已选择 BP 文件' : '可上传 BP 文件或直接输入公司名称' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue';
import { ElInput, ElIcon, ElMessage } from 'element-plus';
import { Loading, CircleCheck, CircleClose, QuestionFilled, Search, Position, Upload, Close, ArrowDown } from '@element-plus/icons-vue';
import { API_WS_URL, type AnalysisStep, type FullReport } from '../services/api';

interface ExtendedWebSocketMessage {
  session_id?: string;
  status?: 'in_progress' | 'hitl_required' | 'hitl_follow_up_required' | 'error' | 'completed';
  step?: AnalysisStep;
  current_step?: AnalysisStep;
  all_steps?: AnalysisStep[];
  full_report?: FullReport;
  key_questions?: string[];
  preliminary_im?: any;
}

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
const messagesAreaEl = ref<HTMLElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const expandedSteps = ref<Set<number>>(new Set());

// Session persistence key
const SESSION_STORAGE_KEY = 'dd_sessions_v3';

// Load sessions from localStorage on mount
onMounted(() => {
  try {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Only restore sessions without active WebSocket connections
      sessions.value = parsed.map((s: Session) => ({ ...s, socket: undefined }));
      console.log('[ChatView] Restored', sessions.value.length, 'sessions from localStorage');
    }
  } catch (error) {
    console.error('[ChatView] Failed to restore sessions:', error);
  }
});

// Save sessions to localStorage whenever they change
watch(sessions, (newSessions) => {
  try {
    // Remove socket references before saving
    const toSave = newSessions.map(s => ({
      id: s.id,
      prompt: s.prompt,
      steps: s.steps,
      followUp: s.followUp
    }));
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(toSave));
    console.log('[ChatView] Saved', toSave.length, 'sessions to localStorage');
  } catch (error) {
    console.error('[ChatView] Failed to save sessions:', error);
  }
}, { deep: true });

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesAreaEl.value) {
      messagesAreaEl.value.scrollTo({
        top: messagesAreaEl.value.scrollHeight,
        behavior: 'smooth'
      });
    }
  });
};

const toggleStepExpanded = (stepId: number) => {
  if (expandedSteps.value.has(stepId)) {
    expandedSteps.value.delete(stepId);
  } else {
    expandedSteps.value.add(stepId);
  }
};

const findOrCreateSession = (id: string, prompt: string): Session => {
  let session = sessions.value.find(s => s.id === id);
  if (!session) {
    const tempSession = sessions.value.find(s => s.id.startsWith('session_'));
    if (tempSession) {
      tempSession.id = id;
      return tempSession;
    }
    session = { id, prompt, steps: [] };
    sessions.value.push(session);
  }
  return session;
};

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0];
  }
};

const clearFile = () => {
  selectedFile.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
};

const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        const parts: string[] = reader.result.split(',');
        const base64: string = parts.length > 1 && parts[1] !== undefined ? parts[1] : '';
        resolve(base64);
      } else {
        reject(new Error('Failed to read file'));
      }
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

const startNewSession = async () => {
  if (!newMessage.value.trim() || isThinking.value) return;

  const userPrompt = newMessage.value.trim();
  const bpFile = selectedFile.value;
  
  newMessage.value = '';
  isThinking.value = true;

  const tempSessionId = `session_${Date.now()}`;
  const newSession: Session = {
    id: tempSessionId,
    prompt: userPrompt + (bpFile ? ` (已上传BP: ${bpFile.name})` : ''),
    steps: []
  };
  sessions.value.push(newSession);
  scrollToBottom();

  try {
    console.log('[ChatView] Creating WebSocket connection to:', API_WS_URL);
    const ws = new WebSocket(API_WS_URL);
    newSession.socket = ws;
    
    ws.onopen = async () => {
      console.log('[ChatView] WebSocket opened');
      let bp_file_base64: string | null = null;
      let bp_filename: string | null = null;
      
      if (bpFile) {
        try {
          console.log('[ChatView] Converting file to base64...', bpFile.name, bpFile.size, 'bytes');
          bp_file_base64 = await fileToBase64(bpFile);
          bp_filename = bpFile.name;
          console.log('[ChatView] File converted, base64 length:', bp_file_base64?.length);
        } catch (error) {
          console.error('[ChatView] Failed to convert file to base64:', error);
          ElMessage.error('文件处理失败，请重试');
          ws.close();
          return;
        }
      }
      
      const payload = { 
        company_name: userPrompt,
        bp_file_base64: bp_file_base64,
        bp_filename: bp_filename || 'business_plan.pdf',
        user_id: 'test_user'
      };
      
      console.log('[ChatView] Sending payload:', {
        company_name: payload.company_name,
        bp_filename: payload.bp_filename,
        bp_file_size: bp_file_base64?.length || 0,
        user_id: payload.user_id
      });
      
      try {
        ws.send(JSON.stringify(payload));
        console.log('[ChatView] Payload sent successfully');
      } catch (sendError) {
        console.error('[ChatView] Failed to send payload:', sendError);
        ElMessage.error('发送数据失败，文件可能过大');
        ws.close();
        return;
      }
      
      // 清除已选文件
      clearFile();
    };

    ws.onmessage = (event) => {
      try {
        const data: ExtendedWebSocketMessage = JSON.parse(event.data);
        console.log('[ChatView] Received WS message:', data);
        
        if (data.session_id) {
          const session = findOrCreateSession(data.session_id, userPrompt);
          
          // V3 后端使用 all_steps，但只显示已开始的步骤（started_at 不为 null）
          if (data.all_steps && data.all_steps.length > 0) {
            session.steps = data.all_steps.filter(step => 
              step.status !== 'pending' || step.started_at !== null
            );
            scrollToBottom();
          } else if (data.current_step) {
            // 如果只有 current_step，更新或添加该步骤
            const existingStep = session.steps.find(s => s.id === data.current_step!.id);
            if (existingStep) {
              Object.assign(existingStep, data.current_step);
            } else {
              session.steps.push(data.current_step);
            }
            scrollToBottom();
          } else if (data.step) {
            // V2 兼容性
            const existingStep = session.steps.find(s => s.id === data.step!.id);
            if (existingStep) {
              Object.assign(existingStep, data.step);
            } else {
              session.steps.push(data.step);
            }
            scrollToBottom();
          }
          
          // V3: preliminary_im 和 dd_questions
          // 注意：只在有数据时设置，不会因为后续消息为 null 而清空
          if (data.preliminary_im && !session.followUp) {
            console.log('[ChatView] Setting followUp data from preliminary_im:', data.preliminary_im);
            
            // Extract questions from dd_questions array
            const questions = data.preliminary_im.dd_questions 
              ? data.preliminary_im.dd_questions.map((q: any) => q.question || q)
              : [];
            
            session.followUp = {
              report: data.preliminary_im as FullReport,
              questions: questions
            };
            console.log('[ChatView] followUp set:', session.followUp);
            scrollToBottom();
          } else if (data.full_report && data.key_questions && !session.followUp) {
            // V2 兼容性
            session.followUp = {
              report: data.full_report,
              questions: data.key_questions
            };
            scrollToBottom();
          }
          
          // 调试：即使后续消息中 preliminary_im 为 null，也保持 followUp
          if (session.followUp) {
            console.log('[ChatView] followUp preserved:', session.followUp);
          }
          
          if (data.status === 'error' || data.status === 'completed' || data.preliminary_im) {
            isThinking.value = false;
          }
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[ChatView] WebSocket error:', error);
      ElMessage.error('连接失败，请重试');
      isThinking.value = false;
    };

    ws.onclose = (event) => {
      console.log('[ChatView] WebSocket closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      isThinking.value = false;
    };
  } catch (error) {
    console.error('Failed to start session:', error);
    ElMessage.error('启动会话失败');
    isThinking.value = false;
  }
};

const handleOptionSelection = (sessionId: string, ticker: string) => {
  const session = sessions.value.find(s => s.id === sessionId);
  if (session?.socket) {
    session.socket.send(JSON.stringify({ selection: ticker }));
  }
};

const emitViewReport = (followUp: FollowUpData | null) => {
  console.log('[ChatView] emitViewReport called with:', followUp);
  if (!followUp) {
    console.warn('[ChatView] followUp is null/undefined!');
    return;
  }
  const session = sessions.value[sessions.value.length - 1];
  const payload = {
    report: followUp.report,
    questions: followUp.questions,
    sessionId: session?.id
  };
  console.log('[ChatView] Emitting view-report event:', payload);
  emit('view-report', payload);
};
</script>

<style scoped>
/* Tailwind 已涵盖大部分样式 */

/* 自定义动画 */
@keyframes slide-in-from-bottom {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes zoom-in-50 {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-in {
  animation-fill-mode: both;
}

.slide-in-from-bottom {
  animation: slide-in-from-bottom 0.3s ease-out;
}

.zoom-in-50 {
  animation: zoom-in-50 0.3s ease-out;
}

.duration-300 {
  animation-duration: 300ms;
}
</style>
