import { defineStore } from 'pinia'
import api from '../services/api'
import websocketService from '../services/websocketService'

export const useTrendStore = defineStore('trend', {
  state: () => ({
    trendingKeywords: [],
    historyData: {},
    wordCloudData: [],
    newsFeed: [],
    metadata: {},
    loading: false,
    error: null,
    
    // WebSocket 相关状态
    wsConnected: false,
    wsStatus: 'disconnected',
    lastUpdateTime: null,
    updateSource: 'http', // 'http' 或 'websocket'
    
    // WebSocket 回调注销函数
    wsUnsubscribers: []
  }),

  getters: {
    // 获取前N个热词
    topKeywords: (state) => (n = 10) => {
      return state.trendingKeywords.slice(0, n)
    },

    // 获取最新新闻
    latestNews: (state) => (n = 20) => {
      return state.newsFeed.slice(0, n)
    }
  },

  actions: {
    // 获取所有数据
    async fetchAllData() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getAllTrendData()
        if (response.success) {
          this.trendingKeywords = response.data.trending_keywords || []
          this.historyData = response.data.history_data || {}
          this.metadata = response.metadata || {}
        } else {
          this.error = response.error || 'Failed to fetch data'
        }
      } catch (error) {
        console.error('Failed to fetch all data:', error)
        this.error = error.message || 'Network error'
      } finally {
        this.loading = false
      }
    },

    // 获取热词数据
    async fetchTrendingKeywords() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getTrendingKeywords()
        if (response.success) {
          this.trendingKeywords = response.data || []
          this.metadata = response.metadata || {}
        } else {
          this.error = response.error || 'Failed to fetch keywords data'
        }
      } catch (error) {
        console.error('Failed to fetch trending keywords:', error)
        this.error = error.message || 'Network error'
      } finally {
        this.loading = false
      }
    },

    // 获取历史数据
    async fetchHistoryData() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getHistoryData()
        if (response.success) {
          this.historyData = response.data || {}
          this.metadata = response.metadata || {}
        } else {
          this.error = response.error || 'Failed to fetch history data'
        }
      } catch (error) {
        console.error('Failed to fetch history data:', error)
        this.error = error.message || 'Network error'
      } finally {
        this.loading = false
      }
    },

    // 获取词云数据
    async fetchWordCloudData() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getWordCloudData()
        if (response.success) {
          this.wordCloudData = response.data || []
          this.metadata = response.metadata || {}
        } else {
          this.error = response.error || 'Failed to fetch word cloud data'
        }
      } catch (error) {
        console.error('Failed to fetch wordcloud data:', error)
        this.error = error.message || 'Network error'
      } finally {
        this.loading = false
      }
    },

    // 获取新闻数据
    async fetchNewsFeed() {
      this.loading = true
      this.error = null
      try {
        const response = await api.getNewsFeed()
        if (response.success) {
          this.newsFeed = response.data || []
          this.metadata = response.metadata || {}
        } else {
          this.error = response.error || 'Failed to fetch news data'
        }
      } catch (error) {
        console.error('Failed to fetch news feed:', error)
        this.error = error.message || 'Network error'
      } finally {
        this.loading = false
      }
    },

    // ============ WebSocket 实时更新相关 ============
    
    /**
     * 初始化 WebSocket 连接
     */
    async initWebSocket() {
      console.log('🔗 正在初始化 WebSocket 连接...')
      
      try {
        // 连接到 WebSocket 端点
        websocketService.connect('/ws/trending')
        
        // 监听 trending 数据更新
        const unsubTrending = websocketService.onData('trending', (message) => {
          console.log('📡 收到 trending 实时更新')
          this.updateTrendingFromWebSocket(message)
        })
        this.wsUnsubscribers.push(unsubTrending)
        
        // 监听 word_cloud 数据更新
        const unsubWordCloud = websocketService.onData('word_cloud', (message) => {
          console.log('📡 收到 word_cloud 实时更新')
          this.updateWordCloudFromWebSocket(message)
        })
        this.wsUnsubscribers.push(unsubWordCloud)
        
        // 监听 news 数据更新
        const unsubNews = websocketService.onData('news', (message) => {
          console.log('📡 收到 news 实时更新')
          this.updateNewsFromWebSocket(message)
        })
        this.wsUnsubscribers.push(unsubNews)
        
        // 监听 history 数据更新
        const unsubHistory = websocketService.onData('history', (message) => {
          console.log('📡 收到 history 实时更新')
          this.updateHistoryFromWebSocket(message)
        })
        this.wsUnsubscribers.push(unsubHistory)
        
        this.wsConnected = true
        this.wsStatus = 'connected'
        console.log('✅ WebSocket 回调已注册')
        
      } catch (error) {
        console.error('❌ WebSocket 初始化失败:', error)
        this.wsConnected = false
        this.wsStatus = 'error'
      }
    },
    
    /**
     * 从 WebSocket 更新 trending 数据
     */
    updateTrendingFromWebSocket(message) {
      if (message.data) {
        this.trendingKeywords = message.data
        this.updateSource = 'websocket'
        this.lastUpdateTime = message.timestamp
        console.log('✅ Trending 数据已更新')
      }
    },
    
    /**
     * 从 WebSocket 更新 word_cloud 数据
     */
    updateWordCloudFromWebSocket(message) {
      if (message.data) {
        this.wordCloudData = message.data
        this.updateSource = 'websocket'
        this.lastUpdateTime = message.timestamp
        console.log('✅ Word Cloud 数据已更新')
      }
    },
    
    /**
     * 从 WebSocket 更新 news 数据
     */
    updateNewsFromWebSocket(message) {
      if (message.data) {
        this.newsFeed = message.data
        this.updateSource = 'websocket'
        this.lastUpdateTime = message.timestamp
        console.log('✅ News 数据已更新')
      }
    },
    
    /**
     * 从 WebSocket 更新 history 数据
     */
    updateHistoryFromWebSocket(message) {
      if (message.data) {
        this.historyData = message.data
        this.updateSource = 'websocket'
        this.lastUpdateTime = message.timestamp
        console.log('✅ History 数据已更新')
      }
    },
    
    /**
     * 断开 WebSocket 连接并清理回调
     */
    disconnectWebSocket() {
      // 注销所有回调
      this.wsUnsubscribers.forEach(unsub => unsub())
      this.wsUnsubscribers = []
      
      // 断开连接
      websocketService.disconnect()
      this.wsConnected = false
      this.wsStatus = 'disconnected'
      console.log('🔌 WebSocket 已断开')
    },

    // 清空错误
    clearError() {
      this.error = null
    },

    // 重置状态
    reset() {
      this.trendingKeywords = []
      this.historyData = {}
      this.wordCloudData = []
      this.newsFeed = []
      this.metadata = {}
      this.loading = false
      this.error = null
      this.updateSource = 'http'
      this.lastUpdateTime = null
    }
  }
})
