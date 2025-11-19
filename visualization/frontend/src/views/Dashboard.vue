<!-- frontend/src/views/Dashboard.vue -->
<template>
  <div class="dashboard">
    <!-- 顶部标题栏 -->
    <header class="dashboard-header">
      <div class="header-content">
        <div class="title-section">
          <h1>Financial News&Comments Real-time Trend Analysis</h1>
        </div>
        <div class="header-actions">
          <button @click="refreshAllData" class="refresh-btn" :disabled="loading">
            <span v-if="!loading">🔄 Refresh Data</span>
            <span v-else>⏳ Loading...</span>
          </button>
          <div class="last-update">
            <span class="update-label">Last Update:</span>
            <span class="update-time">{{ lastUpdateTime }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="dashboard-main">
      <!-- 第一行：实时热词、词云和新闻来源 -->
      <section class="first-row">
        <div class="chart-card trending-card">
          <TrendingKeywords />
        </div>
        <div class="chart-card wordcloud-card">
          <WordCloud />
        </div>
        <div class="chart-card source-card">
          <NewsSourceChart />
        </div>
      </section>

      <!-- 第二行：趋势变化曲线（宽）-->
      <section class="trend-row">
        <div class="chart-card trend-card">
          <TrendChart />
        </div>
      </section>

      <!-- 第三行：新闻滚动 -->
      <section class="news-row">
        <div class="news-card">
          <NewsFeed />
        </div>
      </section>
    </main>

    <!-- 错误提示 -->
    <div v-if="error" class="error-toast">
      <span class="error-icon">⚠️</span>
      <span class="error-message">{{ error }}</span>
      <button @click="clearError" class="error-close">✕</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useTrendStore } from '@/stores/trendStore'
import TrendingKeywords from '@/components/TrendingKeywords.vue'
import WordCloud from '@/components/WordCloud.vue'
import TrendChart from '@/components/TrendChart.vue'
import NewsFeed from '@/components/NewsFeed.vue'
import NewsSourceChart from '@/components/NewsSourceChart.vue'

const store = useTrendStore()
const loading = ref(false)
const lastUpdateTime = ref('--:--:--')
let updateTimer = null

const error = computed(() => store.error)

// 刷新所有数据
async function refreshAllData() {
  loading.value = true
  try {
    await Promise.all([
      store.fetchAllData(),
      store.fetchWordCloudData(),
      store.fetchNewsFeed()
    ])
    updateLastUpdateTime()
  } catch (err) {
    console.error('Failed to refresh data:', err)
  } finally {
    loading.value = false
  }
}

// 更新最后更新时间
function updateLastUpdateTime() {
  const now = new Date()
  lastUpdateTime.value = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
}

// 清除错误
function clearError() {
  store.clearError()
}

// 自动刷新
function startAutoRefresh() {
  updateTimer = setInterval(() => {
    refreshAllData()
  }, 300000) // 每5分钟刷新一次
}

// 组件挂载
onMounted(async () => {
  console.log('📺 Dashboard 组件已挂载')
  
  // 先加载初始数据
  await refreshAllData()
  
  // 初始化 WebSocket 实时连接
  try {
    console.log('🔗 正在初始化 WebSocket 连接...')
    await store.initWebSocket()
    console.log('✅ WebSocket 连接已初始化')
  } catch (error) {
    console.error('❌ WebSocket 初始化失败:', error)
  }
  
  // 启动定时刷新（作为备选方案）
  startAutoRefresh()
})

// 组件卸载
onBeforeUnmount(() => {
  console.log('👋 Dashboard 组件正在卸载')
  
  if (updateTimer) {
    clearInterval(updateTimer)
  }
  
  // 断开 WebSocket 连接
  store.disconnectWebSocket()
})
</script>

<style scoped>
.dashboard {
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部标题栏 */
.dashboard-header {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 20px 32px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}

.header-content {
  max-width: 1920px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.title-section h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #999;
  font-weight: 400;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.refresh-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.refresh-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.last-update {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: 12px;
}

.update-label {
  color: #999;
  font-weight: 500;
}

.update-time {
  color: #333;
  font-weight: 700;
  font-size: 14px;
  font-family: 'Courier New', monospace;
}

/* 主内容区 */
.dashboard-main {
  flex: 1;
  max-width: 1920px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 第一行：热词、词云和新闻来源 */
.first-row {
  display: grid;
  grid-template-columns: 1.3fr 0.85fr 0.85fr;
  gap: 24px;
  height: 320px;
  flex-shrink: 0;
}

.trending-card {
  min-width: 0; /* 允许内容自适应 */
}

.wordcloud-card {
  min-width: 0;
}

.source-card {
  min-width: 0;
}

/* 第二行：趋势曲线 */
.trend-row {
  width: 100%;
  height: 380px;
  flex-shrink: 0;
}

/* 第三行：新闻 */
.news-row {
  width: 100%;
  height: 160px;
  flex-shrink: 0;
}

.chart-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
  height: 100%;
  width: 100%;
}

.chart-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.news-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.news-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

/* 错误提示 */
.error-toast {
  position: fixed;
  top: 100px;
  right: 32px;
  background: white;
  border-left: 4px solid #e74c3c;
  padding: 16px 20px;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 400px;
  z-index: 1000;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.error-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.error-message {
  flex: 1;
  color: #333;
  font-size: 14px;
  line-height: 1.5;
}

.error-close {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 18px;
  flex-shrink: 0;
  transition: color 0.3s ease;
}

.error-close:hover {
  color: #333;
}

/* 响应式设计 */
@media (max-width: 1400px) {
  .first-row {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 900px) {
  .dashboard-header {
    padding: 16px 20px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .title-section h1 {
    font-size: 22px;
  }

  .subtitle {
    font-size: 12px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .dashboard-main {
    padding: 16px 20px;
  }

  .first-row {
    grid-template-columns: 1fr;
    gap: 16px;
    height: auto;
  }

  .trend-row {
    height: 350px;
  }

  .news-row {
    height: 180px;
  }

  .error-toast {
    right: 20px;
    left: 20px;
    max-width: none;
  }
}

@media (max-width: 480px) {
  .dashboard-header {
    padding: 12px 16px;
  }

  .title-section h1 {
    font-size: 18px;
  }

  .subtitle {
    font-size: 11px;
  }

  .refresh-btn {
    padding: 8px 16px;
    font-size: 12px;
  }

  .dashboard-main {
    padding: 12px 16px;
  }

  .first-row {
    gap: 12px;
    min-height: auto;
  }

  .trend-row {
    height: 250px;
  }

  .news-row {
    height: 150px;
  }
}
</style>
