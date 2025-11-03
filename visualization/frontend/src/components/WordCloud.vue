<template>
  <div class="wordcloud-container">
    <div class="panel-header">
      <h3>Word Cloud Analysis</h3>
      <span class="update-info">Real-time Data</span>
    </div>
    <div v-if="loading" class="loading">
      <p>Loading...</p>
    </div>
    <div v-else-if="wordCloudData.length > 0" class="wordcloud-wrapper">
      <div class="words-container">
        <span
          v-for="(word, index) in processedWordCloud"
          :key="index"
          class="word-item"
          :style="{
            fontSize: word.fontSize + 'px',
            color: word.color,
            opacity: word.opacity,
            transform: `rotate(${word.rotation}deg) translateY(${word.translateY}px) skewX(${word.skewX}deg)`
          }"
          :title="`${word.text}: ${word.value}`"
        >
          {{ word.text }}
        </span>
      </div>
    </div>
    <div v-else class="empty-state">
      <p>No word cloud data available</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useTrendStore } from '@/stores/trendStore'

const store = useTrendStore()
const loading = ref(false)

const wordCloudData = computed(() => store.wordCloudData)

// 生成随机旋转角度和位移
const getRandomTransform = (seed) => {
  // 使用 seed 生成伪随机数，保证每个词语每次刷新的变化一致
  const random1 = Math.sin(seed * 12.9898) * 43758.5453
  const random2 = Math.sin((seed + 1) * 78.233) * 43758.5453
  const random3 = Math.sin((seed + 2) * 45.164) * 43758.5453
  
  const rotation = ((random1 - Math.floor(random1)) - 0.5) * 8 // -4deg 到 +4deg
  const translateY = ((random2 - Math.floor(random2)) - 0.5) * 8 // -4px 到 +4px
  const skewX = ((random3 - Math.floor(random3)) - 0.5) * 4 // -2deg 到 +2deg
  
  return { rotation, translateY, skewX }
}

// 处理词云数据 - 根据热度调整字体大小和颜色
const processedWordCloud = computed(() => {
  if (!wordCloudData.value || wordCloudData.value.length === 0) {
    return []
  }

  const maxValue = Math.max(...wordCloudData.value.map(item => item.value))
  const minValue = Math.min(...wordCloudData.value.map(item => item.value))
  const range = maxValue - minValue || 1

  // 颜色梯度 - 从蓝色到红色
  const colors = [
    '#5470C6', // 深蓝
    '#91D1F7', // 浅蓝
    '#FFC72B', // 黄色
    '#FF9E64', // 橙色
    '#FF6B6B'  // 红色
  ]

  return wordCloudData.value.map((item, index) => {
    // 规范化数值到 0-1
    const normalized = (item.value - minValue) / range
    
    // 字体大小范围：16px - 42px (更大的字体)
    const fontSize = 16 + normalized * 26
    
    // 颜色选择
    const colorIndex = Math.floor(normalized * (colors.length - 1))
    const color = colors[Math.max(0, Math.min(colorIndex, colors.length - 1))]
    
    // 透明度：0.6 - 1
    const opacity = 0.6 + normalized * 0.4
    
    // 获取随机变换
    const { rotation, translateY, skewX } = getRandomTransform(item.text.charCodeAt(0) * (index + 1))

    return {
      text: item.text,
      value: item.value,
      fontSize: Math.round(fontSize),
      color: color,
      opacity: opacity,
      rotation: rotation,
      translateY: translateY,
      skewX: skewX
    }
  }).sort(() => Math.random() - 0.5) // 随机排列
})

// 组件挂载时获取数据
onMounted(async () => {
  loading.value = true
  try {
    await store.fetchAllData()
  } catch (error) {
    console.error('Failed to fetch wordcloud data:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wordcloud-container {
  width: 100%;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  padding: 10px 8px;
  box-sizing: border-box;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 6px;
  flex-shrink: 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.update-info {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 4px;
}

.wordcloud-wrapper {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
}

.words-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  align-items: center;
  justify-content: center;
  align-content: flex-start;
  width: 100%;
  padding: 6px 8px;
  box-sizing: border-box;
  line-height: 1.4;
}

.word-item {
  cursor: pointer;
  white-space: nowrap;
  font-weight: 600;
  letter-spacing: -0.5px;
  transition: all 0.3s ease;
  user-select: none;
  display: inline-flex;
  align-items: center;
  padding: 3px 6px;
  border-radius: 4px;
  margin: 0;
}

.word-item:hover {
  transform: scale(1.15);
  opacity: 1 !important;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.loading,
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
  min-height: 0;
}

.loading p,
.empty-state p {
  margin: 0;
}

/* 滚动条美化 */
.wordcloud-wrapper::-webkit-scrollbar {
  width: 6px;
}

.wordcloud-wrapper::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.wordcloud-wrapper::-webkit-scrollbar-thumb {
  background: #bbb;
  border-radius: 3px;
}

.wordcloud-wrapper::-webkit-scrollbar-thumb:hover {
  background: #888;
}
</style>