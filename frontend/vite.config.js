import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import viteCompression from 'vite-plugin-compression'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // Gzip compression for production builds
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 1024, // Only compress files > 1KB
      deleteOriginFile: false
    }),
    // Brotli compression (better compression ratio)
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 1024,
      deleteOriginFile: false
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    // Enable source maps for production debugging
    sourcemap: false,
    // Minification options
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    // Code splitting configuration
    rollupOptions: {
      output: {
        // Manual chunk splitting for better caching
        manualChunks: {
          // Vue core in separate chunk
          'vue-vendor': ['vue', 'vue-router'],
          // Chart.js in separate chunk (large library)
          'chart': ['chart.js'],
          // Markdown parser
          'markdown': ['marked']
        },
        // Asset file naming with content hash for cache busting
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.')
          const ext = info[info.length - 1]
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name)) {
            return 'assets/images/[name]-[hash][extname]'
          }
          if (/\.(css)$/i.test(assetInfo.name)) {
            return 'assets/css/[name]-[hash][extname]'
          }
          if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name)) {
            return 'assets/fonts/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        }
      }
    },
    // Chunk size warning limit (in KB)
    chunkSizeWarningLimit: 500,
    // Asset inline limit (4kb)
    assetsInlineLimit: 4096
  },
  // Server configuration
  server: {
    // Enable gzip compression in dev
    middlewareMode: false,
    // Proxy API requests to backend
    proxy: {
      // Trading API -> report_orchestrator
      '/api/trading': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true  // Enable WebSocket proxy
      },
      // Roundtable API -> report_orchestrator
      '/api/roundtable': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      // Analysis API -> report_orchestrator
      '/api/analysis': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      // Reports API -> report_orchestrator
      '/api/reports': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      // Session API -> report_orchestrator
      '/api/sessions': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      // Auth API -> auth_service
      '/api/auth': {
        target: 'http://localhost:8007',
        changeOrigin: true
      },
      // LLM Gateway API
      '/api/llm': {
        target: 'http://localhost:8003',
        changeOrigin: true
      },
      // Web Search API
      '/api/search': {
        target: 'http://localhost:8004',
        changeOrigin: true
      }
    }
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ['vue', 'vue-router', 'chart.js', 'marked']
  }
})
