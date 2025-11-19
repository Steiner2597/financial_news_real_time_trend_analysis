# WebSocket 实时更新系统 - 实现指南

## 🎯 功能概述

完整的**实时数据推送系统**，从 Redis 数据更新 → WebSocket 推送 → 前端自动刷新的端到端解决方案。

### 数据流向

```
processed_data (Redis) 
    ↓
data_monitor (监听变化) 
    ↓
websocket_manager (推送) 
    ↓
websocketService (接收) 
    ↓
trendStore (更新状态) 
    ↓
组件 (自动刷新)
```

---

## 🔧 后端实现

### 1. `data_monitor.py` - Redis 数据监听

**位置**: `visualization/backend/app/services/data_monitor.py`

**功能**:
- 监听 `processed_data:*` 键的变化
- 检测新增、更新、删除操作
- 通过回调函数通知 WebSocket 管理器

**关键方法**:
```python
# 启动监听
monitor = get_data_monitor(host, port, db, password)
monitor.add_callback(callback_function)
monitor.start()

# 停止监听
monitor.stop()
```

### 2. `websocket_manager.py` - WebSocket 推送

**位置**: `visualization/backend/app/services/websocket_manager.py`

**新增方法**:
- `broadcast_all_types()` - 广播给所有连接
- `push_processed_data_update()` - 推送数据更新

**实时推送消息格式**:
```json
{
  "type": "data_update",
  "change_info": {
    "changed": true,
    "added": [],
    "updated": ["processed_data:trending_keywords"],
    "deleted": [],
    "timestamp": "2025-11-03T10:30:45.123Z"
  },
  "updated_data": {
    "trending_keywords": [...],
    "word_cloud": [...],
    "news_feed": [...],
    "metadata": {...}
  },
  "timestamp": "2025-11-03T10:30:45.123Z"
}
```

### 3. `main.py` - 应用启动

**关键变化**:
```python
# 启动时初始化 data_monitor
from .services.data_monitor import get_data_monitor
from .services.websocket_manager import websocket_manager

# 在启动后台服务中
data_monitor = get_data_monitor(...)
data_monitor.add_callback(websocket_manager.push_processed_data_update)
data_monitor.start()
```

---

## 🎨 前端实现

### 1. `WebSocketService.js` - WebSocket 客户端

**位置**: `visualization/frontend/src/services/websocketService.js`

**核心功能**:
- 自动连接和重连
- 注册/注销数据回调
- 消息路由和分发

**使用示例**:
```javascript
import websocketService from '@/services/websocketService'

// 连接
websocketService.connect('/ws/trending')

// 注册回调 - 返回注销函数
const unsubscribe = websocketService.onData('trending', (message) => {
  console.log('收到 trending 数据:', message.data)
})

// 注销回调
unsubscribe()

// 断开连接
websocketService.disconnect()
```

### 2. `trendStore.js` - Pinia Store

**新增状态**:
```javascript
state: {
  wsConnected: false,           // WebSocket 连接状态
  wsStatus: 'disconnected',     // 连接状态字符串
  lastUpdateTime: null,         // 最后更新时间
  updateSource: 'http',         // 更新来源 'http' 或 'websocket'
  wsUnsubscribers: []           // 回调注销函数列表
}
```

**新增 Actions**:
```javascript
// 初始化 WebSocket
await store.initWebSocket()

// 接收数据更新（自动调用）
store.updateTrendingFromWebSocket(message)
store.updateWordCloudFromWebSocket(message)
store.updateNewsFromWebSocket(message)
store.updateHistoryFromWebSocket(message)

// 断开连接
store.disconnectWebSocket()
```

### 3. 组件自动刷新

所有组件都通过 `watch()` 监听 Store 数据变化:

#### TrendingKeywords.vue
```javascript
watch(() => store.trendingKeywords, (newVal) => {
  console.log('检测到数据变化，自动刷新')
}, { deep: true })
```

#### WordCloud.vue
```javascript
watch(() => store.wordCloudData, (newVal) => {
  console.log('词云数据已更新')
}, { deep: true })
```

#### TrendChart.vue
```javascript
watch(() => store.historyData, (newVal) => {
  console.log('历史数据已更新')
}, { deep: true })
```

#### NewsFeed.vue
```javascript
watch(() => store.newsFeed, (newVal) => {
  // 重置滚动位置
  currentIndex.value = 0
}, { deep: true })
```

### 4. Dashboard.vue 启动

```javascript
onMounted(async () => {
  // 加载初始数据
  await refreshAllData()
  
  // 初始化 WebSocket
  await store.initWebSocket()
  
  // 启动定时备选刷新
  startAutoRefresh()
})

onBeforeUnmount(() => {
  // 清理 WebSocket
  store.disconnectWebSocket()
})
```

---

## 📊 数据更新流程

### 场景 1: processed_data 更新

```
1. Processor 写入新数据到 processed_data:trending_keywords
2. data_monitor 检测到变化
3. data_monitor 调用回调 → push_processed_data_update()
4. websocket_manager 推送消息到所有连接
5. websocketService 接收消息
6. trendStore action 更新状态
7. 组件 watch 检测状态变化
8. 组件自动重新渲染
```

### 时间轴

- **T0**: 后端数据更新
- **T0+100ms**: 监听检测到变化
- **T0+150ms**: WebSocket 推送
- **T0+160ms**: 前端接收
- **T0+165ms**: Store 状态更新
- **T0+170ms**: 组件重新渲染

---

## 🚀 性能优化

### 1. 背压处理
- WebSocket 发送失败时自动断开并重连
- 限制连接重试次数

### 2. 数据去重
- 相同数据不重复推送
- 只推送实际改变的字段

### 3. 连接管理
- 自动重连机制（最多 5 次）
- 心跳保活（ping/pong）

### 4. 内存管理
- 及时清理断开的连接
- 卸载组件时注销回调

---

## 🐛 调试方法

### 后端日志
```python
# 检查监听状态
data_monitor.is_monitoring  # True/False

# 查看最后状态
data_monitor.last_state

# 手动检查数据
redis_client.keys("processed_data:*")
```

### 前端日志
```javascript
// 检查连接状态
websocketService.getStatus()

// 查看接收的消息
websocketService.lastMessage

// 查看所有注册的回调
websocketService.dataCallbacks
```

### 浏览器控制台
```javascript
// 连接状态
store.wsConnected
store.wsStatus

// 最后更新时间
store.lastUpdateTime

// 更新来源
store.updateSource  // 'http' or 'websocket'
```

---

## 📝 测试检查表

- [ ] ✅ 后端 data_monitor 启动时输出日志
- [ ] ✅ WebSocket 连接建立时前端有日志
- [ ] ✅ 手动更新 processed_data 后，前端数据自动更新
- [ ] ✅ 刷新页面后重新连接成功
- [ ] ✅ 关闭浏览器标签后断开连接
- [ ] ✅ 数据错误时有错误提示
- [ ] ✅ 网络中断后自动重连

---

## 🔍 常见问题排查

### 问题 1: WebSocket 无法连接
**症状**: 前端控制台显示 "连接错误"

**排查**:
1. 确认后端服务运行: `http://localhost:8000/health`
2. 检查 WebSocket 路由是否注册
3. 查看浏览器网络标签 WebSocket 连接状态

### 问题 2: 数据不更新
**症状**: 前端收不到实时数据

**排查**:
1. 检查 `data_monitor` 是否启动
2. 验证 Redis 中有数据：`redis-cli KEYS "processed_data:*"`
3. 检查回调函数是否被调用
4. 查看浏览器控制台是否有错误

### 问题 3: 连接频繁断开
**症状**: WebSocket 经常重连

**排查**:
1. 检查后端日志是否有异常
2. 查看网络延迟是否过高
3. 确认 Redis 连接是否稳定

---

## 📚 相关文件清单

### 后端
- ✅ `app/services/data_monitor.py` - 监听服务
- ✅ `app/services/websocket_manager.py` - 推送管理
- ✅ `app/main.py` - 启动集成

### 前端
- ✅ `services/websocketService.js` - WebSocket 客户端
- ✅ `stores/trendStore.js` - 状态管理
- ✅ `views/Dashboard.vue` - 主页面
- ✅ `components/TrendingKeywords.vue` - 组件
- ✅ `components/WordCloud.vue` - 组件
- ✅ `components/TrendChart.vue` - 组件
- ✅ `components/NewsFeed.vue` - 组件

---

## 🎓 架构总结

```
┌─────────────────────────────────────────────────────────┐
│                    系统架构图                             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  【后端】                          【前端】               │
│  ┌──────────────┐                ┌──────────────┐      │
│  │ processed_   │                │  Dashboard   │      │
│  │   data       │                │     vue      │      │
│  └──────┬───────┘                └───────┬──────┘      │
│         │                                │              │
│  ┌──────▼───────┐                ┌───────▼──────┐      │
│  │ data_monitor ◄─────────────────► websocket   │      │
│  │  (Redis)     │   WebSocket      Service      │      │
│  └──────┬───────┘                └───────┬──────┘      │
│         │                                │              │
│  ┌──────▼───────┐                ┌───────▼──────┐      │
│  │ websocket_   │                │ trendStore   │      │
│  │  manager     │                │   (Pinia)    │      │
│  └──────────────┘                └───────┬──────┘      │
│                                          │              │
│                                  ┌───────▼──────┐      │
│                                  │  Components  │      │
│                                  │  (自动刷新)  │      │
│                                  └──────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ 关键特性

1. **实时推送** - 数据秒级更新
2. **自动重连** - 网络中断自动恢复
3. **智能去重** - 相同数据不重复推送
4. **自动刷新** - 组件监听状态变化自动渲染
5. **心跳保活** - 定期发送 ping 保持连接
6. **错误恢复** - 异常自动处理

---

**最后更新**: 2025-11-03
**版本**: 1.0.0
