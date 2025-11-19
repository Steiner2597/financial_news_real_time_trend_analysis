/**
 * WebSocket 实时数据服务
 * 连接后端 WebSocket，接收实时的 processed_data 更新
 */

import { ref } from 'vue'

class WebSocketService {
  constructor() {
    this.ws = null
    this.url = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.isConnecting = false
    
    // 状态
    this.isConnected = ref(false)
    this.connectionStatus = ref('disconnected') // disconnected, connecting, connected, error
    this.lastMessage = ref(null)
    this.errorMessage = ref(null)
    
    // 数据回调 - 按数据类型存储回调函数列表
    this.dataCallbacks = new Map()
  }

  /**
   * 连接到 WebSocket 服务器
   * @param {string} endpoint - WebSocket 端点 (e.g., '/ws/trending')
   */
  connect(endpoint) {
    if (this.isConnecting) {
      console.warn('⚠️ WebSocket 连接正在进行中...')
      return
    }

    if (this.ws && this.isConnected.value) {
      console.warn('⚠️ WebSocket 已连接')
      return
    }

    this.isConnecting = true
    this.connectionStatus.value = 'connecting'
    this.errorMessage.value = null

    // 构建 WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    this.url = `${protocol}//${host}/api/v1${endpoint}`

    console.log(`🔗 正在连接 WebSocket: ${this.url}`)

    try {
      this.ws = new WebSocket(this.url)

      this.ws.addEventListener('open', () => this.handleOpen())
      this.ws.addEventListener('message', (event) => this.handleMessage(event))
      this.ws.addEventListener('error', (event) => this.handleError(event))
      this.ws.addEventListener('close', () => this.handleClose())

    } catch (error) {
      console.error('❌ WebSocket 连接失败:', error)
      this.isConnecting = false
      this.connectionStatus.value = 'error'
      this.errorMessage.value = error.message
      this.attemptReconnect()
    }
  }

  /**
   * WebSocket 打开事件处理
   */
  handleOpen() {
    console.log('✅ WebSocket 已连接')
    this.isConnected.value = true
    this.isConnecting = false
    this.connectionStatus.value = 'connected'
    this.reconnectAttempts = 0
    this.errorMessage.value = null

    // 发送连接确认心跳
    this.send({
      type: 'ping',
      timestamp: new Date().toISOString()
    })
  }

  /**
   * WebSocket 消息事件处理
   */
  handleMessage(event) {
    try {
      const message = JSON.parse(event.data)
      this.lastMessage.value = message

      console.log('📨 收到 WebSocket 消息:', message.type)

      // 处理连接建立确认
      if (message.type === 'connection_established') {
        console.log('🎉 WebSocket 连接已建立，订阅类型:', message.subscribed_types)
        return
      }

      // 处理心跳响应
      if (message.type === 'pong') {
        console.debug('💓 心跳响应')
        return
      }

      // 处理实时数据更新
      if (message.type === 'data_update') {
        console.log('🔄 收到 processed_data 更新')
        this.dispatchDataUpdate(message)
        return
      }

      // 处理特定数据类型的数据
      if (message.type === 'word_cloud_data') {
        this.triggerCallback('word_cloud', message)
        return
      }

      if (message.type === 'trending_data') {
        this.triggerCallback('trending', message)
        return
      }

      if (message.type === 'news_data') {
        this.triggerCallback('news', message)
        return
      }

      // 处理错误
      if (message.type === 'error') {
        console.error('❌ WebSocket 错误:', message.message)
        this.errorMessage.value = message.message
        return
      }

    } catch (error) {
      console.error('❌ 消息处理失败:', error)
    }
  }

  /**
   * 分发数据更新事件
   */
  dispatchDataUpdate(message) {
    const { updated_data, change_info } = message

    // 根据更新的数据类型调用对应的回调
    if (updated_data.word_cloud) {
      this.triggerCallback('word_cloud', {
        type: 'word_cloud_data',
        data: updated_data.word_cloud,
        metadata: updated_data.metadata,
        timestamp: message.timestamp
      })
    }

    if (updated_data.trending_keywords) {
      this.triggerCallback('trending', {
        type: 'trending_data',
        data: updated_data.trending_keywords,
        metadata: updated_data.metadata,
        timestamp: message.timestamp
      })
    }

    if (updated_data.news_feed) {
      this.triggerCallback('news', {
        type: 'news_data',
        data: updated_data.news_feed,
        metadata: updated_data.metadata,
        timestamp: message.timestamp
      })
    }

    if (updated_data.history_data) {
      this.triggerCallback('history', {
        type: 'history_data',
        data: updated_data.history_data,
        timestamp: message.timestamp
      })
    }
  }

  /**
   * 触发数据回调
   */
  triggerCallback(dataType, data) {
    if (this.dataCallbacks.has(dataType)) {
      const callbacks = this.dataCallbacks.get(dataType)
      callbacks.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`❌ 数据回调执行失败 (${dataType}):`, error)
        }
      })
    }
  }

  /**
   * WebSocket 错误事件处理
   */
  handleError(event) {
    console.error('❌ WebSocket 错误:', event)
    this.connectionStatus.value = 'error'
    this.errorMessage.value = '连接错误'
    this.attemptReconnect()
  }

  /**
   * WebSocket 关闭事件处理
   */
  handleClose() {
    console.log('🔌 WebSocket 已关闭')
    this.isConnected.value = false
    this.isConnecting = false
    this.connectionStatus.value = 'disconnected'
    this.attemptReconnect()
  }

  /**
   * 尝试重新连接
   */
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`🔄 ${this.reconnectDelay / 1000}秒后尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      
      setTimeout(() => {
        if (this.url && !this.isConnected.value) {
          this.connect(this.url.split('/api/v1')[1])
        }
      }, this.reconnectDelay)
    } else {
      console.error('❌ 重新连接失败：已达最大尝试次数')
      this.errorMessage.value = '连接失败，请刷新页面重试'
    }
  }

  /**
   * 发送消息
   */
  send(message) {
    if (!this.isConnected.value) {
      console.warn('⚠️ WebSocket 未连接，无法发送消息')
      return false
    }

    try {
      this.ws.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('❌ 发送消息失败:', error)
      return false
    }
  }

  /**
   * 请求特定数据
   */
  requestData(dataType) {
    return this.send({
      type: 'request_data',
      data_type: dataType,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * 注册数据回调
   * @param {string} dataType - 数据类型 (word_cloud, trending, news, history)
   * @param {function} callback - 回调函数
   */
  onData(dataType, callback) {
    if (!this.dataCallbacks.has(dataType)) {
      this.dataCallbacks.set(dataType, [])
    }
    this.dataCallbacks.get(dataType).push(callback)

    console.log(`📌 已注册 ${dataType} 数据回调`)

    // 返回注销函数
    return () => {
      const callbacks = this.dataCallbacks.get(dataType)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
      console.log(`📌 已注销 ${dataType} 数据回调`)
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected.value = false
    this.isConnecting = false
    this.connectionStatus.value = 'disconnected'
    this.dataCallbacks.clear()
    console.log('🔌 WebSocket 已断开')
  }

  /**
   * 获取连接状态
   */
  getStatus() {
    return {
      isConnected: this.isConnected.value,
      connectionStatus: this.connectionStatus.value,
      reconnectAttempts: this.reconnectAttempts,
      errorMessage: this.errorMessage.value
    }
  }
}

// 创建单例
const websocketService = new WebSocketService()

export default websocketService
