// src/main.ts
import { createApp } from 'vue'
import App from './App.vue'

// 导入 Tailwind CSS
import './index.css'

// 导入 shadcn/ui 主题系统
import './styles/themes/shadcn-variables.css'
import './styles/themes/shadcn-components.css'
import { initThemeOnStartup } from './composables/useTheme'

// 导入 Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

// 导入 Element Plus 覆盖样式
import './styles/base44-overrides.css'

// 导入通用样式
import './assets/main.css'

// 初始化主题
initThemeOnStartup()

const app = createApp(App)

app.use(ElementPlus)
app.mount('#app')