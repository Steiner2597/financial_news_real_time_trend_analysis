<!-- frontend/src/components/NewsFeed.vue -->
<template>
    <div class="news-feed-container">
      <div class="feed-header">
        <h4>📰 Recent News</h4>
        <span class="feed-count">{{ newsList.length }} items</span>
      </div>
  
      <div v-if="loading" class="feed-loading">
        <p>Loading news...</p>
      </div>
  
      <div v-else-if="newsList.length > 0" class="feed-scroller">
        <div class="scroller-track">
          <transition-group name="news-fade" tag="div">
            <div
              v-for="(news, index) in displayNewsList"
              :key="`${news.title}-${news.publish_time || news.timestamp}`"
              class="news-item"
              :class="{ 'active': index === currentIndex }"
            >
              <div class="news-icon">
                {{ getCategoryIcon(news.category) }}
              </div>
  
              <div class="news-content">
                <div class="news-title">
                  <a 
                    v-if="news.url" 
                    :href="news.url" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    class="title-link"
                    @click.stop
                  >
                    {{ news.title }}
                  </a>
                  <span v-else class="title-text">
                    {{ news.title }}
                  </span>
                </div>

                <div class="news-meta">
                  <span class="news-source">{{ news.source || 'Unknown Source' }}</span>
                  <span class="news-time">{{ formatTime(news.publish_time || news.timestamp) }}</span>
                  <span v-if="news.sentiment" class="news-sentiment" :class="`sentiment-${getSentimentType(news.sentiment)}`">
                    {{ getSentimentLabel(getSentimentType(news.sentiment)) }}
                  </span>
                </div>                <div v-if="news.keywords && news.keywords.length > 0" class="news-tags">
                  <span v-for="tag in news.keywords" :key="tag" class="tag">
                    {{ tag }}
                  </span>
                </div>
              </div>
  
              <div class="news-heat" v-if="news.heat_score !== undefined">
                <span class="heat-value">{{ news.heat_score || 0 }}</span>
                <span class="heat-label">Heat</span>
              </div>
            </div>
          </transition-group>
        </div>
      </div>
  
      <div v-else class="feed-empty">
        <p>No news data available</p>
      </div>
  
      <div class="feed-controls">
        <button 
          @click="previousNews" 
          class="control-btn"
          :disabled="!canScroll"
          title="Previous"
        >
          ▲
        </button>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <button 
          @click="nextNews" 
          class="control-btn"
          :disabled="!canScroll"
          title="Next"
        >
          ▼
        </button>
      </div>
    </div>
  </template>
  
  <script setup>
  import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
  import { useTrendStore } from '@/stores/trendStore'
  
  const store = useTrendStore()
  const loading = ref(false)
  const currentIndex = ref(0)
  let autoScrollTimer = null
  
  // 获取新闻列表
  const newsList = computed(() => {
    const news = store.newsFeed || []
    // 取前20条新闻，按时间倒序排列
    return news.slice(0, 20).sort((a, b) => {
      const timeA = new Date(a.publish_time || a.timestamp).getTime()
      const timeB = new Date(b.publish_time || b.timestamp).getTime()
      return timeB - timeA
    })
  })
  
  // 监听新闻数据变化，自动刷新
  watch(() => store.newsFeed, (newVal) => {
    if (newVal && newVal.length > 0) {
      console.log('👁️ NewsFeed 检测到数据变化，自动刷新')
      // 重置滚动位置
      currentIndex.value = 0
    }
  }, { deep: true })
  
  // 监听更新源
  watch(() => store.updateSource, (newVal) => {
    if (newVal === 'websocket') {
      console.log('🌐 NewsFeed 数据来自 WebSocket 实时推送')
    }
  })
  
  // 显示的新闻列表（循环滚动）
  const displayNewsList = computed(() => {
    if (newsList.value.length === 0) return []
    // 创建循环列表，当到达末尾时回到开头
    return [
      newsList.value[currentIndex.value % newsList.value.length]
    ]
  })
  
  // 进度百分比
  const progressPercent = computed(() => {
    if (newsList.value.length === 0) return 0
    return ((currentIndex.value + 1) / newsList.value.length) * 100
  })
  
  // 是否可以滚动
  const canScroll = computed(() => newsList.value.length > 1)
  
  // 获取分类图标
  function getCategoryIcon(category) {
    const icons = {
      'tech': '💻',
      'business': '💼',
      'entertainment': '🎬',
      'sports': '⚽',
      'health': '🏥',
      'politics': '🏛️',
      'world': '🌍',
      'science': '🔬',
      'finance': '💰',
      'default': '📰'
    }
    return icons[category?.toLowerCase()] || icons.default
  }
  
  // 获取情感类型（处理字符串或对象格式）
  function getSentimentType(sentiment) {
    if (typeof sentiment === 'string') {
      return sentiment.toLowerCase()
    } else if (sentiment && sentiment.label) {
      return sentiment.label.toLowerCase()
    }
    return 'neutral'
  }

  // 获取情感标签
  function getSentimentLabel(sentimentType) {
    const labels = {
      'positive': '👍 Positive',
      'negative': '👎 Negative',
      'neutral': '➡️ Neutral'
    }
    return labels[sentimentType] || '➡️ Neutral'
  }
  
  // 格式化时间
  function formatTime(timestamp) {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
  
    if (diff < 60000) {
      return 'Just now'
    } else if (diff < 3600000) {
      return `${Math.floor(diff / 60000)} min ago`
    } else if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)} hr ago`
    } else {
      return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    }
  }
  
  // 上一条新闻
  function previousNews() {
    if (newsList.value.length > 0) {
      currentIndex.value = (currentIndex.value - 1 + newsList.value.length) % newsList.value.length
      resetAutoScroll()
    }
  }
  
  // 下一条新闻
  function nextNews() {
    if (newsList.value.length > 0) {
      currentIndex.value = (currentIndex.value + 1) % newsList.value.length
      resetAutoScroll()
    }
  }
  
  // 自动滚动
  function startAutoScroll() {
    autoScrollTimer = setInterval(() => {
      if (newsList.value.length > 0) {
        currentIndex.value = (currentIndex.value + 1) % newsList.value.length
      }
    }, 5000) // 每5秒切换一条新闻
  }
  
  // 重置自动滚动
  function resetAutoScroll() {
    if (autoScrollTimer) {
      clearInterval(autoScrollTimer)
    }
    startAutoScroll()
  }
  
  // 监听新闻列表变化
  watch(() => newsList.value.length, (newVal) => {
    if (newVal > 0 && currentIndex.value >= newVal) {
      currentIndex.value = 0
    }
  })
  
  // 组件挂载
  onMounted(async () => {
    loading.value = true
    try {
      await store.fetchNewsFeed()
      startAutoScroll()
    } catch (error) {
      console.error('Failed to fetch news feed:', error)
    } finally {
      loading.value = false
    }
  })
  
  // 组件卸载
  onBeforeUnmount(() => {
    if (autoScrollTimer) {
      clearInterval(autoScrollTimer)
    }
  })
  </script>
  
  <style scoped>
  .news-feed-container {
    width: 100%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 8px;
    padding: 16px;
    box-sizing: border-box;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 160px;
    position: relative;
    overflow: hidden;
  }
  
  .feed-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  }
  
  .feed-header h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: white;
  }
  
  .feed-count {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 8px;
    border-radius: 12px;
  }
  
  .feed-scroller {
    flex: 1;
    min-height: 60px;
    position: relative;
    overflow: hidden; /* 隐藏溢出，不显示滚动条 */
  }
  
  .scroller-track {
    width: 100%; /* 固定宽度 */
    height: 100%;
    display: flex;
    align-items: flex-start; /* 靠左对齐 */
    position: relative; /* 相对定位，防止瞬移 */
  }
  
  .scroller-track > div {
    display: flex;
    flex-direction: row; /* 水平排列 */
    gap: 12px;
    position: absolute; /* 绝对定位，防止跳动 */
    left: 0;
    top: 0;
    width: 100%; /* 限制为容器宽度 */
    height: 100%;
    align-items: flex-start;
  }
  
  .news-item {
    width: 100%; /* 占满容器宽度 */
    max-width: 100%; /* 最大宽度为容器宽度 */
    display: flex; /* flex布局 */
    gap: 8px;
    align-items: flex-start; /* 靠上对齐 */
    padding: 10px 12px;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 6px;
    cursor: pointer;
    will-change: transform, opacity; /* 优化动画性能 */
    box-sizing: border-box; /* 包含padding在宽度内 */
  }
  
  .news-item:hover {
    background: white;
    transform: translateX(4px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  
  .news-item.active {
    background: white;
  }
  
  .news-icon {
    font-size: 20px;
    min-width: 24px;
    text-align: center;
    flex-shrink: 0;
  }
  
  .news-content {
    display: flex;
    flex-direction: column; /* 垂直布局 */
    gap: 4px; /* 行间距 */
    flex: 1; /* 占据剩余空间 */
    min-width: 0; /* 允许内容缩小 */
    overflow: hidden; /* 隐藏溢出 */
  }
  
  .news-title {
    margin: 0;
    width: 100%; /* 占满一行 */
    overflow: hidden; /* 隐藏溢出 */
  }
  
  .title-text {
    font-size: 13px;
    font-weight: 600;
    color: #333;
    line-height: 1.3;
    display: block; /* 块级显示，独占一行 */
    white-space: nowrap; /* 单行显示，不换行 */
    overflow: hidden; /* 隐藏溢出 */
    text-overflow: ellipsis; /* 超出显示省略号 */
  }
  
  .title-link {
    font-size: 13px;
    font-weight: 600;
    color: #333;
    line-height: 1.3;
    display: block; /* 块级显示，独占一行 */
    text-decoration: none;
    white-space: nowrap; /* 单行显示，不换行 */
    overflow: hidden; /* 隐藏溢出 */
    text-overflow: ellipsis; /* 超出显示省略号 */
    transition: color 0.2s ease;
  }
  
  .title-link:hover {
    color: #667eea;
    text-decoration: underline;
  }
  
  .news-item:hover .title-text {
    color: #667eea;
  }
  
  .news-meta {
    display: flex; /* flex布局，在下一行显示 */
    gap: 8px;
    align-items: center;
    font-size: 11px;
    color: #666;
    white-space: nowrap; /* 单行显示 */
    overflow: hidden; /* 隐藏溢出 */
    flex-wrap: nowrap; /* 不换行 */
  }
  
  .news-source {
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
    color: #667eea;
  }
  
  .news-time {
    color: #999;
  }
  
  .news-sentiment {
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
    font-size: 10px;
  }
  
  .sentiment-positive {
    background: #d4edda;
    color: #155724;
  }
  
  .sentiment-negative {
    background: #f8d7da;
    color: #721c24;
  }
  
  .sentiment-neutral {
    background: #e2e3e5;
    color: #383d41;
  }
  
  .news-tags {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  
  .tag {
    display: inline-block;
    background: rgba(102, 126, 234, 0.1);
    color: #667eea;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    white-space: nowrap;
    max-width: 80px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .news-heat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-width: 40px;
    flex-shrink: 0;
  }
  
  .heat-value {
    font-size: 14px;
    font-weight: 700;
    color: #ff6b6b;
  }
  
  .heat-label {
    font-size: 10px;
    color: #999;
  }
  
  .feed-loading,
  .feed-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 60px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
  }
  
  .feed-loading p,
  .feed-empty p {
    margin: 0;
  }
  
  .feed-controls {
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: center;
    padding-top: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.2);
  }
  
  .control-btn {
    background: rgba(255, 255, 255, 0.2);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.3);
    width: 24px;
    height: 24px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  
  .control-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.3);
    transform: scale(1.1);
  }
  
  .control-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .progress-bar {
    flex: 1;
    height: 3px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    overflow: hidden;
    max-width: 100px;
  }
  
  .progress-fill {
    height: 100%;
    background: white;
    transition: width 0.3s ease;
  }
  
  /* 过渡动画 */
  .news-fade-enter-active {
    transition: opacity 0.4s ease, transform 0.4s ease;
  }
  
  .news-fade-leave-active {
    transition: opacity 0.4s ease, transform 0.4s ease;
    position: absolute; /* 离开时绝对定位，不占空间 */
  }
  
  .news-fade-enter-from {
    opacity: 0;
    transform: translateX(-30px) scale(0.95); /* 从左侧缩放滑入 */
  }
  
  .news-fade-leave-to {
    opacity: 0;
    transform: translateX(30px) scale(0.95); /* 向右侧缩放滑出 */
  }
  
  .news-fade-move {
    transition: none; /* 禁用移动过渡，防止跳动 */
  }
  </style>