import axios from 'axios'

// 直接指向后端 API（无需通过代理）
// 后端运行在 localhost:8000，路由前缀为 /api/v1
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    console.log(`[API Request] ${config.method.toUpperCase()} ${config.baseURL}${config.url}`)
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log(`[API Response] Status: ${response.status}`, response.data)
    return response.data
  },
  error => {
    console.error('Response error:', error.message)
    if (error.response) {
      console.error(`Status: ${error.response.status}`)
      console.error(`Data:`, error.response.data)
    }
    return Promise.reject(error)
  }
)

// API 接口
export default {
  // 获取所有趋势数据
  getAllTrendData() {
    return api.get('/trends/all')
  },

  // 获取热词数据
  getTrendingKeywords() {
    return api.get('/trends/keywords')
  },

  // 获取历史趋势数据
  getHistoryData() {
    return api.get('/trends/history')
  },

  // 获取词云数据
  getWordCloudData() {
    return api.get('/wordcloud')
  },

  // 获取新闻数据
  getNewsFeed() {
    return api.get('/news')
  },

  // 趋势服务健康检查
  checkTrendsHealth() {
    return api.get('/trends/health')
  },

  // 词云服务健康检查
  checkWordCloudHealth() {
    return api.get('/wordcloud/health')
  },

  // 新闻服务健康检查
  checkNewsHealth() {
    return api.get('/news/health')
  }
}
