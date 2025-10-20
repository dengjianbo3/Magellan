<!-- src/App.vue -->
<template>
  <div class="workstation-layout">
    <!-- Sidebar for Navigation -->
    <nav class="sidebar">
      <div class="sidebar-header">
        <h1>AI 投资助手</h1>
      </div>
      <ul class="nav-list">
        <li :class="{ active: activeView === 'chat' }" @click="activeView = 'chat'">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能探索</span>
        </li>
        <li :class="{ active: activeView === 'report' }" @click="activeView = 'report'">
          <el-icon><Document /></el-icon>
          <span>深度报告</span>
        </li>
      </ul>
    </nav>

    <!-- Main Content Area -->
    <main class="main-content">
      <component :is="activeView === 'chat' ? ChatView : ReportView" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef } from 'vue';
import { ElIcon } from 'element-plus';
import { ChatDotRound, Document } from '@element-plus/icons-vue';
import ChatView from './views/ChatView.vue';
import ReportView from './views/ReportView.vue';

type View = 'chat' | 'report';
const activeView = ref<View>('chat');
</script>

<style scoped>
.workstation-layout {
  display: flex;
  height: 100vh;
  background: var(--glass-bg);
  border: var(--glass-border);
  border-radius: 16px;
  box-shadow: var(--glass-shadow);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  overflow: hidden;
  max-width: 1400px;
  width: 95%;
  margin: 2.5vh auto;
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
  border-right: var(--glass-border);
  padding: 1.5rem 0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 0 1.5rem;
  text-align: center;
  margin-bottom: 2rem;
}
.sidebar-header h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.nav-list li {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  margin: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.3s ease;
  font-weight: 500;
}
.nav-list li .el-icon {
  margin-right: 12px;
  font-size: 1.2rem;
}
.nav-list li:hover {
  background: rgba(255, 255, 255, 0.1);
}
.nav-list li.active {
  background: #764ba2;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.main-content {
  flex-grow: 1;
  height: 100%;
  overflow: hidden;
}
</style>
