import { defineStore } from 'pinia'
import api from '../services/api'

export const useTrendStore = defineStore('trend', {
  state: () => ({
    trendingKeywords: [],
    historyData: {},
    wordCloudData: [],
    newsFeed: [],
    metadata: {},
    loading: false,
    error: null
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
    }
  }
})
