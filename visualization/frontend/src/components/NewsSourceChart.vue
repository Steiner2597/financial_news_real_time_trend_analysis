<template>
  <div class="news-source-chart">
    <div class="panel-header">
      <h3>News Sources Distribution</h3>
      <button @click="refreshChart" class="refresh-btn" :disabled="loading">
        <span v-if="!loading">🔄 Refresh</span>
        <span v-else>Loading...</span>
      </button>
    </div>

    <div v-if="loading" class="loading">
      <p>Loading news sources data...</p>
    </div>

    <div v-else-if="chartOption.series && chartOption.series.length > 0" class="chart-wrapper">
      <v-chart :option="chartOption" class="chart" autoresize />
    </div>

    <div v-else class="empty-state">
      <p>No news sources data available</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useTrendStore } from '@/stores/trendStore'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, PieChart, TitleComponent, TooltipComponent, LegendComponent])

const store = useTrendStore()
const loading = ref(false)

// 从metadata中获取新闻来源统计数据
const newsSourceData = computed(() => {
  const metadata = store.metadata || {}
  const newsSources = metadata.news_sources || {}
  
  if (!newsSources || Object.keys(newsSources).length === 0) {
    return []
  }

  // 转换为饼图数据格式并排序
  const data = Object.entries(newsSources)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  return data
})

// 图表配置
const chartOption = computed(() => {
  const data = newsSourceData.value

  if (!data || data.length === 0) {
    return {
      tooltip: {},
      legend: {},
      series: []
    }
  }

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#555',
      borderWidth: 1,
      textStyle: {
        color: '#fff',
        fontSize: 12
      },
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: {
        fontSize: 11,
        color: '#666'
      },
      formatter: function(name) {
        const item = data.find(d => d.name === name)
        return item ? `${name} (${item.value})` : name
      }
    },
    series: [
      {
        name: 'News Sources',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        labelLine: {
          show: false
        },
        data: data,
        color: [
          '#5470C6', '#91D1F7', '#FAC858', '#EE6666', '#73C0DE',
          '#9A60B4', '#EA7CCC', '#FC8452', '#3BA272', '#5B8FF9'
        ]
      }
    ]
  }
})

// 刷新图表
async function refreshChart() {
  loading.value = true
  try {
    await store.fetchAllData()
  } catch (error) {
    console.error('Failed to refresh news sources chart:', error)
  } finally {
    loading.value = false
  }
}

// 组件挂载时获取数据
onMounted(async () => {
  loading.value = true
  try {
    await store.fetchAllData()
  } catch (error) {
    console.error('Failed to fetch news sources data:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.news-source-chart {
  width: 100%;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  padding: 16px;
  box-sizing: border-box;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 10px;
  flex-shrink: 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
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

.chart-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  overflow: hidden;
  width: 100%;
}

.chart {
  width: 100%;
  height: 100%;
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
</style>
