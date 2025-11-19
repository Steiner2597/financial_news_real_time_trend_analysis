// 趋势数据接口

import api from './api'

export const trendService = {
  async getAllTrendData() {
    const response = await api.get('/trends/all')
    return response.data
  },

  async getTrendingKeywords() {
    const response = await api.get('/trends/keywords')
    return response.data
  },

  async getHistoryData() {
    const response = await api.get('/trends/history')
    return response.data
  },

  async getNewsFeed() {
    const response = await api.get('/news')
    return response.data
  }
}