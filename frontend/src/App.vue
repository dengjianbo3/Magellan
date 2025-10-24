<!-- src/App.vue - shadcn/ui + Tailwind -->
<template>
  <div class="dark flex h-screen overflow-hidden bg-background">
    <!-- 侧边导航栏 -->
    <aside class="w-[280px] flex-shrink-0 border-r border-border bg-card">
      <div class="flex h-full flex-col">
        <!-- Logo 区域 -->
        <div class="flex items-center justify-between border-b border-border px-6 py-5">
          <div class="flex items-center gap-3">
            <div class="text-2xl animate-bounce">🚀</div>
            <h1 class="text-lg font-bold tracking-tight text-foreground">投研工作台</h1>
          </div>
        </div>

        <!-- 导航菜单 -->
        <nav class="flex-1 space-y-1 overflow-y-auto p-4">
          <button
            v-for="item in menuItems"
            :key="item.view"
            :class="[
              'group relative flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-all',
              activeView === item.view
                ? 'bg-[#3B82F6] text-white shadow-sm'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground'
            ]"
            @click="activeView = item.view"
          >
            <!-- 左侧蓝色指示条 -->
            <div
              v-if="activeView === item.view"
              class="absolute left-0 top-1/2 h-8 w-1 -translate-y-1/2 rounded-r-full bg-white"
            ></div>
            
            <el-icon class="text-xl transition-transform group-hover:scale-110">
              <component :is="item.icon" />
            </el-icon>
            <span class="flex-1 text-left">{{ item.label }}</span>
            <span v-if="item.badge" class="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-white/20 px-2 text-xs font-bold">
              {{ item.badge }}
            </span>
          </button>
        </nav>

        <!-- 用户资料 -->
        <div class="border-t border-border p-4">
          <div class="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-accent">
            <div class="h-10 w-10 overflow-hidden rounded-full border-2 border-border">
              <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" alt="User" class="h-full w-full object-cover" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="truncate text-sm font-semibold text-foreground">投资经理</div>
              <div class="truncate text-xs text-muted-foreground">user@example.com</div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区域 -->
    <main class="relative flex-1 overflow-hidden bg-background">
      <!-- 背景网格 -->
      <div class="pointer-events-none absolute inset-0 opacity-30" style="background-image: linear-gradient(hsl(var(--border)) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px); background-size: 50px 50px;"></div>
      
      <!-- 内容 -->
      <div class="relative h-full">
        <ChatView v-if="activeView === 'chat'" @view-report="handleViewReport" />
        <ReportView v-if="activeView === 'report'" />
        <PersonaView v-if="activeView === 'persona'" />
        <InteractiveReportView 
          v-if="activeView === 'interactive_report' && interactiveReportData" 
          :report-data="interactiveReportData.report" 
          :key-questions="interactiveReportData.questions"
          :session-id="interactiveReportData.sessionId"
        />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { ElIcon } from 'element-plus';
import { ChatDotRound, Document, DataAnalysis, User } from '@element-plus/icons-vue';
import ChatView from './views/ChatView.vue';
import ReportView from './views/ReportView.vue';
import PersonaView from './views/PersonaView.vue';
import InteractiveReportView from './views/InteractiveReportView.vue';
import type { FullReport } from './services/api';

type View = 'chat' | 'report' | 'interactive_report' | 'persona';

interface InteractiveReportPayload {
  report: FullReport;
  questions: string[];
  sessionId?: string;
}

const activeView = ref<View>('chat');
const interactiveReportData = ref<InteractiveReportPayload | null>(null);

const menuItems = computed(() => [
  {
    view: 'chat' as View,
    label: '任务驾驶舱',
    icon: ChatDotRound,
    badge: null
  },
  {
    view: 'report' as View,
    label: '报告视图',
    icon: Document,
    badge: null
  },
  {
    view: 'persona' as View,
    label: '机构画像',
    icon: User,
    badge: null
  },
  {
    view: 'interactive_report' as View,
    label: 'IM 工作台',
    icon: DataAnalysis,
    badge: interactiveReportData.value ? '1' : null  // 有数据时显示角标
  }
]);

const handleViewReport = (payload: InteractiveReportPayload) => {
  interactiveReportData.value = payload;
  activeView.value = 'interactive_report';
};
</script>

<style scoped>
/* Tailwind 类已涵盖大部分样式，这里只保留必要的自定义样式 */

/* 确保 dark 模式生效 */
:deep(.dark) {
  color-scheme: dark;
}
</style>
