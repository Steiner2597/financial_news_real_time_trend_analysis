<template>
  <div class="trend-chart">
    <div class="panel-header">
      <h3>Trend Chart - Past 24 Hours</h3>
      <button @click="refreshChart" class="refresh-btn" :disabled="loading">
        <span v-if="!loading">🔄 Refresh</span>
        <span v-else>Loading...</span>
      </button>
    </div>

    <div v-if="loading" class="loading">
      <p>Loading trend data...</p>
    </div>

    <div v-else-if="chartOption.series && chartOption.series.length > 0" class="chart-wrapper">
      <v-chart :option="chartOption" class="chart" :style="{ width: chartWidth }" autoresize />
    </div>

    <div v-else class="empty-state">
      <p>No trend data available</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, nextTick } from 'vue'
import { useTrendStore } from '@/stores/trendStore'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const store = useTrendStore()
const loading = ref(false)

// 获取历史数据
const historyData = computed(() => store.historyData || {})

// 处理历史数据为图表格式
const processedData = computed(() => {
  const data = historyData.value
  
  if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
    return { dates: [], seriesData: [], allTimestamps: [] }
  }

  // 后端数据结构: { keyword: [{ timestamp, frequency }] }
  const timeMap = {}
  const keywords = new Set()

  // 兼容性解析：后端 timestamp 为 'YYYY-MM-DD HH:MM:SS'，
  // 不依赖浏览器内建 Date 字符串解析以避免跨浏览器/时区差异导致的合并问题。
  function parseTimestamp(ts) {
    const m = /^(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})$/.exec(ts)
    if (m) {
      const year = Number(m[1])
      const month = Number(m[2]) - 1
      const day = Number(m[3])
      const hour = Number(m[4])
      const minute = Number(m[5])
      const second = Number(m[6])
      return new Date(year, month, day, hour, minute, second)
    }
    const d = new Date(ts)
    return isNaN(d.getTime()) ? new Date(0) : d
  }

  // 遍历每个关键词的时间序列数据，收集所有关键词和原始数据
  Object.entries(data).forEach(([keyword, timeSeriesArray]) => {
    if (Array.isArray(timeSeriesArray)) {
      keywords.add(keyword)
      
      timeSeriesArray.forEach(item => {
        const timestamp = item.timestamp
        const value = item.frequency

        if (!timeMap[timestamp]) {
          timeMap[timestamp] = {}
        }
        timeMap[timestamp][keyword] = value
      })
    }
  })

  // 从实际数据中获取所有唯一的整点时间
  const uniqueHours = new Set()
  Object.keys(timeMap).forEach(ts => {
    try {
      const tsDate = parseTimestamp(ts)
      // 取整点
      const hourKey = new Date(tsDate.getFullYear(), tsDate.getMonth(), tsDate.getDate(), tsDate.getHours(), 0, 0, 0)
      uniqueHours.add(hourKey.getTime())
    } catch (e) {
      console.warn('Failed to parse timestamp:', ts, e)
    }
  })

  // 转换为数组并排序
  const sortedHours = Array.from(uniqueHours).sort((a, b) => a - b)
  
  // 最多保留最近24个小时
  const maxHours = 24
  const recentHours = sortedHours.slice(-maxHours)
  
  // 生成时间槽
  const timeSlots = recentHours.map(timestamp => new Date(timestamp))

  // 调试信息
  try {
    const keywordCounts = {}
    Object.entries(data).forEach(([k, arr]) => {
      if (Array.isArray(arr)) keywordCounts[k] = arr.length
    })
    console.debug('TrendChart debug — per-keyword counts:', keywordCounts)
    console.debug('TrendChart debug — unique timestamps in timeMap:', Object.keys(timeMap).length)
    console.debug('TrendChart debug — unique hours found:', sortedHours.length)
    console.debug('TrendChart debug — timeSlots count:', timeSlots.length)
    if (timeSlots.length > 0) {
      console.debug('TrendChart debug — first slot:', timeSlots[0], 'last slot:', timeSlots[timeSlots.length - 1])
    }
  } catch (e) {
    console.warn('TrendChart debug logging failed:', e)
  }

  // 获取所有关键词并按热度排序
  const allKeywords = Array.from(keywords)
    .sort((a, b) => {
      const sumA = Object.values(timeMap).reduce((sum, t) => sum + (t[a] || 0), 0)
      const sumB = Object.values(timeMap).reduce((sum, t) => sum + (t[b] || 0), 0)
      return sumB - sumA
    })

  // 为每个整点时间槽填充数据：统计该小时内所有数据
  const slotData = timeSlots.map(slotTime => {
    const slotValues = {}
    
    // 定义该小时的时间范围 [slotTime, slotTime + 1小时)
    const hourStart = slotTime.getTime()
    const hourEnd = hourStart + 60 * 60 * 1000
    
    allKeywords.forEach(keyword => {
      // 统计该小时内该关键词的总频率
      let hourTotal = 0
      
      Object.keys(timeMap).forEach(ts => {
        try {
          const tsDate = parseTimestamp(ts)
          const tsTime = tsDate.getTime()
          
          // 如果时间戳在该小时范围内
          if (tsTime >= hourStart && tsTime < hourEnd) {
            if (timeMap[ts][keyword] !== undefined) {
              hourTotal += timeMap[ts][keyword]
            }
          }
        } catch (e) {
          // 忽略解析错误
        }
      })
      
      slotValues[keyword] = hourTotal
    })
    
    return { time: slotTime, values: slotValues }
  })

  // 生成 X 轴标签（格式：HH:00 整点）
  const dates = slotData.map(slot => {
    const h = String(slot.time.getHours()).padStart(2, '0')
    return `${h}:00`
  })

  // 找到今天0点的位置索引
  const now = new Date()
  const todayZeroIndex = slotData.findIndex(slot => {
    const slotDate = slot.time
    return slotDate.getDate() === now.getDate() && 
           slotDate.getMonth() === now.getMonth() && 
           slotDate.getFullYear() === now.getFullYear() &&
           slotDate.getHours() === 0
  })
  
  // 调试信息
  console.log('Today Zero Index:', todayZeroIndex)
  console.log('Slot Data:', slotData.map(s => ({
    time: s.time.toLocaleString(),
    hour: s.time.getHours(),
    date: s.time.getDate(),
    isToday: s.time.getDate() === now.getDate() && 
             s.time.getMonth() === now.getMonth() && 
             s.time.getFullYear() === now.getFullYear()
  })))

  // 生成 ECharts Series 数据（包含所有关键词）
  const seriesData = allKeywords.map((keyword, index) => ({
    name: keyword,
    type: 'line',
    data: slotData.map(slot => slot.values[keyword] || 0),
    smooth: true,
    itemStyle: {
      color: getSeriesColor(index)
    },
    areaStyle: {
      color: getSeriesColor(index, true)
    },
    symbolSize: 5,
    lineStyle: {
      width: 2
    },
    emphasis: {
      itemStyle: {
        borderWidth: 2,
        borderColor: '#fff'
      }
    }
  }))

  return {
    dates: dates,
    keywords: allKeywords,
    seriesData,
    todayZeroIndex
  }
})

// 图表宽度固定为100%，不需要横向滚动
const chartWidth = computed(() => {
  return '100%'
})

const chartOption = computed(() => {
  const { dates, seriesData, todayZeroIndex } = processedData.value

  if (!dates || dates.length === 0) {
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: [] },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: []
    }
  }

  return {
    title: {
      text: 'Keyword Heat Trend (Showing Top 5)',
      left: 'center',
      top: 0,
      textStyle: {
        fontSize: 14,
        fontWeight: 600,
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#555',
      borderWidth: 1,
      textStyle: {
        color: '#fff',
        fontSize: 12
      },
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: '#ddd',
          width: 1,
          type: 'dashed'
        }
      },
      formatter: function(params) {
        if (!params || params.length === 0) return ''
        const time = params[0].axisValue
        let result = `<div style="font-weight: bold; margin-bottom: 8px;">${time}</div>`
        params.forEach(item => {
          if (item.value !== '-') {
            result += `<div style="color: ${item.color}; margin: 4px 0;">● ${item.seriesName}: ${item.value}</div>`
          }
        })
        return result
      }
    },
    legend: {
      data: processedData.value.keywords,
      // 默认只显示前5个关键词
      selected: processedData.value.keywords.reduce((obj, keyword, index) => {
        obj[keyword] = index < 5
        return obj
      }, {}),
      top: 30,
      right: 20,
      textStyle: {
        fontSize: 12,
        color: '#666'
      },
      backgroundColor: 'rgba(255, 255, 255, 0.8)',
      borderRadius: 4,
      padding: 8,
      type: 'scroll', // 如果关键词太多，支持滚动
      orient: 'vertical',
      pageButtonPosition: 'end'
    },
    grid: {
      left: 60,
      right: 150, // 为右侧图例留出更多空间
      top: 50,
      bottom: 40,
      containLabel: false
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisLabel: {
        fontSize: 12,
        color: '#666',
        interval: 'auto', // 自动调整标签显示间隔
        rotate: 0,
        formatter: function(value, index) {
          // 在今天0点下方显示"Today"
          if (todayZeroIndex !== -1 && index === todayZeroIndex) {
            return value + '\nToday'
          }
          return value
        },
        rich: {
          today: {
            color: '#ff4d4f',
            fontWeight: 'bold'
          }
        }
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisLabel: {
        fontSize: 11,
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      }
    },
    series: [
      ...seriesData,
      // 添加一个专门的系列来显示今天的分界线
      ...(todayZeroIndex !== -1 ? [{
        name: 'Today Mark',
        type: 'line',
        markLine: {
          silent: true,
          symbol: 'none',
          animation: false,
          label: {
            show: false
          },
          lineStyle: {
            color: '#ff4d4f',
            width: 3,
            type: 'solid',
            opacity: 0.8
          },
          data: [{
            xAxis: todayZeroIndex,
            label: {
              show: false
            }
          }],
          emphasis: {
            disabled: true
          }
        },
        data: []
      }] : [])
    ]
  }
})

// 获取系列颜色
function getSeriesColor(index, isArea = false) {
  const colors = [
    '#5470C6', '#91D1F7', '#FAC858', '#EE6666', '#73C0DE',
    '#9A60B4', '#EA7CCC', '#FC8452', '#3BA272', '#5B8FF9',
    '#61DDAA', '#65789B', '#F6BD16', '#7262FD', '#78D3F8',
    '#9661BC', '#F6903D', '#008685', '#F08BB4', '#5D7092'
  ]
  const color = colors[index % colors.length]
  if (isArea) {
    return color + '40' // 添加透明度（40为16进制透明度）
  }
  return color
}

// 刷新图表
async function refreshChart() {
  loading.value = true
  try {
    await store.fetchHistoryData()
  } catch (error) {
    console.error('Failed to refresh chart:', error)
  } finally {
    loading.value = false
  }
}

// 组件挂载时获取数据
onMounted(async () => {
  loading.value = true
  try {
    await store.fetchHistoryData()
    // 等待DOM完全渲染后再显示图表
    await nextTick()
    // 调试：打印数据
    console.log('Raw historyData:', store.historyData)
    console.log('ProcessedData dates count:', processedData.value.dates?.length || 0)
    console.log('ProcessedData dates:', processedData.value.dates)
  } catch (error) {
    console.error('Failed to fetch history data:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.trend-chart {
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
  justify-content: flex-start;
  min-height: 0;
  overflow-x: auto;
  overflow-y: hidden;
  width: 100%;
}

.chart-wrapper::-webkit-scrollbar {
  height: 12px;
}

.chart-wrapper::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 6px;
  margin: 0 10px;
}

.chart-wrapper::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 6px;
  cursor: pointer;
}

.chart-wrapper::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.chart-wrapper::-webkit-scrollbar-thumb:active {
  background: #333;
}

.chart {
  height: 100%;
  flex-shrink: 0;
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