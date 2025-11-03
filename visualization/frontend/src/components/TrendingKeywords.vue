<!-- frontend/src/components/TrendingKeywords.vue -->
<template>
  <div class="trending-keywords">
    <div class="panel-header">
      <h3>Trending Keywords</h3>
      <div class="header-actions">
        <span class="update-info">Update every {{ metadata.update_interval || 5 }} minutes</span>
        <button @click="refreshData" class="refresh-btn" :disabled="loading">
          <span v-if="!loading">🔄 Refresh</span>
          <span v-else>Loading...</span>
        </button>
      </div>
    </div>
    
    <div v-if="loading && trendingKeywords.length === 0" class="loading">
      <p>Loading keywords...</p>
    </div>
    
    <div v-else-if="trendingKeywords.length > 0" class="keywords-list">
      <transition-group name="list" tag="div">
        <div
          v-for="(item, index) in trendingKeywords"
          :key="`${item.keyword}-${index}`"
          class="keyword-item"
          :class="{ 'top-three': item.rank <= 3 }"
        >
          <div class="keyword-rank" :class="`rank-${item.rank}`">
            <span v-if="item.rank <= 3" class="rank-medal">{{ getRankMedal(item.rank) }}</span>
            <span v-else>{{ item.rank }}</span>
          </div>
          
          <div class="keyword-content">
            <div class="keyword-header">
              <span class="keyword-text">{{ item.keyword }}</span>
              <span class="growth-rate" :class="getGrowthClass(item.growth_rate)">
                {{ item.growth_rate > 0 ? '+' : '' }}{{ item.growth_rate }}%
              </span>
            </div>
            
            <div class="sentiment-section">
              <SentimentBar :sentiment="item.sentiment" />
            </div>
            
            <div class="keyword-stats">
              <div class="stat-item">
                <span class="stat-label">Comments</span>
                <span class="stat-value">{{ formatNumber(item.sentiment.total_comments) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Frequency</span>
                <span class="stat-value">{{ item.current_frequency || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Trend</span>
                <span class="stat-value" :class="getTrendClass(item.growth_rate)">
                  {{ getTrendIcon(item.growth_rate) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </transition-group>
    </div>
    
    <div v-else class="empty-state">
      <p>No trending keywords data available</p>
      <button @click="refreshData" class="retry-btn">Retry</button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useTrendStore } from '@/stores/trendStore'
import SentimentBar from './SentimentBar.vue'

const store = useTrendStore()
const loading = ref(false)
let refreshTimer = null

const trendingKeywords = computed(() => store.trendingKeywords)
const metadata = computed(() => store.metadata)

// 监听 trendingKeywords 变化，自动触发重新渲染
watch(() => store.trendingKeywords, (newVal) => {
  if (newVal && newVal.length > 0) {
    console.log('👁️ TrendingKeywords 检测到数据变化，自动刷新')
  }
}, { deep: true })

// 监听更新源，记录是否来自 WebSocket
watch(() => store.updateSource, (newVal) => {
  if (newVal === 'websocket') {
    console.log('🌐 数据来自 WebSocket 实时推送')
  }
})

// 获取排名奖牌
function getRankMedal(rank) {
  const medals = ['🥇', '🥈', '🥉']
  return medals[rank - 1] || rank
}

// 获取增长率样式
function getGrowthClass(growthRate) {
  if (growthRate > 0) return 'positive'
  if (growthRate < 0) return 'negative'
  return 'neutral'
}

// 获取趋势图标 - 根据增长率判断
function getTrendIcon(growthRate) {
  if (typeof growthRate === 'number') {
    if (growthRate > 100) return '📈'
    if (growthRate < 50) return '📉'
    return '→'
  }
  // 兼容字符串格式
  if (growthRate === 'up' || growthRate === 'rising') return '📈'
  if (growthRate === 'down' || growthRate === 'falling') return '📉'
  return '→'
}

// 获取趋势样式 - 根据增长率判断
function getTrendClass(growthRate) {
  if (typeof growthRate === 'number') {
    if (growthRate > 100) return 'trend-up'
    if (growthRate < 50) return 'trend-down'
    return 'trend-stable'
  }
  // 兼容字符串格式
  if (growthRate === 'up' || growthRate === 'rising') return 'trend-up'
  if (growthRate === 'down' || growthRate === 'falling') return 'trend-down'
  return 'trend-stable'
}

// 格式化数字
function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

// 刷新数据
async function refreshData() {
  loading.value = true
  try {
    await store.fetchTrendingKeywords()
  } catch (error) {
    console.error('Failed to refresh trending keywords:', error)
  } finally {
    loading.value = false
  }
}

// 自动刷新
function startAutoRefresh() {
  const interval = (metadata.value?.update_interval || 5) * 60 * 1000
  refreshTimer = setInterval(() => {
    refreshData()
  }, interval)
}

// 组件挂载
onMounted(async () => {
  loading.value = true
  try {
    await store.fetchTrendingKeywords()
    startAutoRefresh()
  } catch (error) {
    console.error('Failed to fetch trending keywords:', error)
  } finally {
    loading.value = false
  }
})

// 组件卸载
onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.trending-keywords {
  width: 100%;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  padding: 16px;
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 15px;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.update-info {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 4px;
}

.refresh-btn {
  background: #5470C6;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.3s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: #366092;
}

.refresh-btn:disabled {
  background: #bbb;
  cursor: not-allowed;
}

.keywords-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 200px;
  padding-right: 4px;
}

.keyword-item {
  display: flex;
  gap: 12px;
  padding: 14px 4px;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.3s ease, transform 0.3s ease;
  align-items: flex-start;
}

.keyword-item:hover {
  background-color: #fafafa;
  transform: translateX(4px);
}

.keyword-item.top-three {
  background: rgba(84, 112, 198, 0.05);
  padding: 14px 10px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.keyword-rank {
  min-width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  color: #5470C6;
  background: #f5f7ff;
  border-radius: 4px;
}

.rank-medal {
  font-size: 24px;
}

.keyword-content {
  flex: 1;
  min-width: 0;
}

.keyword-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 12px;
}

.keyword-text {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  word-wrap: break-word;
  word-break: break-word;
  line-height: 1.4;
  flex: 1;
}

.growth-rate {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

.growth-rate.positive {
  background: #f6e7e7;
  color: #e74c3c;
}

.growth-rate.negative {
  background: #e7f6e7;
  color: #27ae60;
}

.growth-rate.neutral {
  background: #f5f5f5;
  color: #999;
}

.sentiment-section {
  margin: 8px 0;
}

.keyword-stats {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
}

.stat-label {
  color: #999;
  font-weight: 500;
}

.stat-value {
  color: #333;
  font-weight: 600;
  font-size: 12px;
}

.stat-value.trend-up {
  color: #e74c3c;
}

.stat-value.trend-down {
  color: #27ae60;
}

.stat-value.trend-stable {
  color: #999;
}

.loading,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 0;
  flex: 1;
  color: #999;
  gap: 12px;
}

.loading p,
.empty-state p {
  margin: 0;
  font-size: 14px;
}

.retry-btn {
  background: #5470C6;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.3s ease;
}

.retry-btn:hover {
  background: #366092;
}

/* 列表动画 */
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

/* 滚动条美化 */
.keywords-list::-webkit-scrollbar {
  width: 6px;
}

.keywords-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.keywords-list::-webkit-scrollbar-thumb {
  background: #bbb;
  border-radius: 3px;
}

.keywords-list::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>