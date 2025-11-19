# WebSocket 实时更新系统 - 架构设计文档

## 系统架构概览

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     金融趋势分析实时系统                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐          ┌──────────────────────┐     │
│  │   后端服务           │          │   前端应用           │     │
│  │  (Python/FastAPI)    │          │  (Vue 3 + Vite)     │     │
│  └──────────────────────┘          └──────────────────────┘     │
│         ▲                                      ▲                  │
│         │                                      │                  │
│  ┌──────▼──────────────────────────────────────▼──────┐         │
│  │              WebSocket 双向通信                     │         │
│  │   ws://host:8000/api/v1/ws/trending                │         │
│  └────────────────────────────────────────────────────┘         │
│         ▲                                                         │
│         │ 数据推送                                               │
│  ┌──────┴────────┐                                              │
│  │ websocket_    │                                              │
│  │ manager       │                                              │
│  └──────┬────────┘                                              │
│         ▲ 推送触发                                              │
│  ┌──────┴────────┐                                              │
│  │ data_monitor  │                                              │
│  │ (监听器)       │                                              │
│  └──────┬────────┘                                              │
│         ▲ 变化检测                                              │
│  ┌──────┴──────────────────────────────────────┐               │
│  │         Redis (DB2)                         │               │
│  │  processed_data: {                          │               │
│  │    trending_keywords: [...],                │               │
│  │    word_cloud: [...],                       │               │
│  │    news_feed: [...],                        │               │
│  │    history_data: {...},                     │               │
│  │    metadata: {}                             │               │
│  │  }                                          │               │
│  └─────────────────────────────────────────────┘               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 后端架构详解

### 1. 数据层 (Redis DB2)

```
Redis DB2: processed_data namespace
├── processed_data:metadata
│   └── {timestamp, update_interval, data_version}
├── processed_data:trending_keywords
│   └── [{keyword, growth_rate, sentiment, frequency}, ...]
├── processed_data:word_cloud
│   └── [{text, value}, ...]
├── processed_data:news_feed
│   └── [{title, source, sentiment, url}, ...]
└── processed_data:history_data:*
    └── {keyword: [{timestamp, frequency}, ...]}
```

### 2. 监听层 (data_monitor.py)

```
┌─────────────────────────────────────────┐
│         DataMonitor (独立线程)          │
├─────────────────────────────────────────┤
│                                         │
│  每秒执行一次:                          │
│  1. 获取 Redis 当前状态快照             │
│  2. 与上次状态对比                     │
│  3. 检测新增/更新/删除的键               │
│  4. 调用已注册的回调函数                │
│                                         │
│  状态: {                               │
│    changed: bool,                      │
│    added: [],                          │
│    updated: [],                        │
│    deleted: [],                        │
│    data: {}                            │
│  }                                     │
└─────────────────────────────────────────┘
```

### 3. 推送层 (websocket_manager.py)

```
┌──────────────────────────────────────┐
│    WebSocket 连接管理器             │
├──────────────────────────────────────┤
│                                      │
│  connections: {                     │
│    WORD_CLOUD: [ws1, ws2, ...],    │
│    TRENDING: [ws3, ws4, ...],      │
│    NEWS: [ws5, ws6, ...],          │
│    ALL: [ws7, ...]                  │
│  }                                  │
│                                      │
│  接收来自 data_monitor 的回调        │
│    ↓                                │
│  调用 push_processed_data_update() │
│    ↓                                │
│  广播给所有连接                      │
│                                      │
└──────────────────────────────────────┘
```

### 4. 应用层集成

```
FastAPI Application Lifecycle:
│
├─ lifespan 事件
│  ├─ 启动时 (startup):
│  │  ├─ 初始化 Redis 客户端
│  │  ├─ 创建 data_monitor 实例
│  │  ├─ 注册 websocket_manager.push_processed_data_update 回调
│  │  └─ 启动监听线程
│  │
│  └─ 关闭时 (shutdown):
│     ├─ 停止 data_monitor
│     ├─ 关闭所有 WebSocket 连接
│     └─ 清理资源
│
├─ WebSocket 路由
│  └─ /ws/{endpoint}
│     ├─ accept 连接
│     ├─ 注册到管理器
│     ├─ 循环接收消息
│     └─ 清理断开连接
│
└─ HTTP 路由
   └─ /api/v1/{trends|news|wordcloud|websocket}
```

---

## 前端架构详解

### 1. WebSocket 客户端 (websocketService.js)

```
┌──────────────────────────────────────────┐
│     WebSocketService (单例)             │
├──────────────────────────────────────────┤
│                                          │
│  属性:                                   │
│  ├─ ws: WebSocket 实例                  │
│  ├─ url: 连接 URL                        │
│  ├─ isConnected: 连接状态                │
│  ├─ dataCallbacks: Map<type, [callbacks]>│
│  └─ reconnectAttempts: 重连次数          │
│                                          │
│  方法:                                   │
│  ├─ connect(endpoint)                   │
│  ├─ send(message)                       │
│  ├─ onData(type, callback) → unsubscribe│
│  ├─ disconnect()                        │
│  └─ getStatus()                         │
│                                          │
│  事件处理:                                │
│  ├─ handleOpen() → 连接成功              │
│  ├─ handleMessage() → 消息路由           │
│  ├─ handleError() → 错误处理             │
│  ├─ handleClose() → 断开处理             │
│  └─ attemptReconnect() → 重连            │
│                                          │
└──────────────────────────────────────────┘
```

### 2. 状态管理 (trendStore.js - Pinia)

```
┌──────────────────────────────────────────┐
│         Pinia Store (trendStore)        │
├──────────────────────────────────────────┤
│                                          │
│  状态 (State):                           │
│  ├─ trendingKeywords: []                │
│  ├─ wordCloudData: []                   │
│  ├─ newsFeed: []                        │
│  ├─ historyData: {}                     │
│  ├─ metadata: {}                        │
│  │                                      │
│  ├─ wsConnected: false                  │
│  ├─ wsStatus: 'disconnected'            │
│  ├─ lastUpdateTime: null                │
│  ├─ updateSource: 'http'                │
│  └─ wsUnsubscribers: []                 │
│                                          │
│  Actions:                                │
│  ├─ 数据获取 (HTTP):                    │
│  │  ├─ fetchAllData()                   │
│  │  ├─ fetchTrendingKeywords()          │
│  │  ├─ fetchWordCloudData()             │
│  │  └─ fetchNewsFeed()                  │
│  │                                      │
│  ├─ WebSocket 初始化:                   │
│  │  └─ initWebSocket()                  │
│  │     ├─ connect() 连接                │
│  │     └─ onData() 注册回调             │
│  │                                      │
│  ├─ 数据更新 (WebSocket):               │
│  │  ├─ updateTrendingFromWebSocket()   │
│  │  ├─ updateWordCloudFromWebSocket()  │
│  │  ├─ updateNewsFromWebSocket()       │
│  │  └─ updateHistoryFromWebSocket()    │
│  │                                      │
│  └─ 清理:                                │
│     └─ disconnectWebSocket()            │
│                                          │
└──────────────────────────────────────────┘
```

### 3. 组件响应式更新

```
┌─────────────────────────────────────────┐
│        Dashboard 组件                   │
├─────────────────────────────────────────┤
│  onMounted():                           │
│  ├─ 加载初始数据 (HTTP)                 │
│  ├─ 初始化 WebSocket                    │
│  └─ 启动定时备选刷新                    │
│                                         │
│  各个子组件:                            │
│  ├─ TrendingKeywords                    │
│  │  └─ watch(store.trendingKeywords)   │
│  │     → 自动刷新                       │
│  │                                     │
│  ├─ WordCloud                          │
│  │  └─ watch(store.wordCloudData)      │
│  │     → 自动刷新                       │
│  │                                     │
│  ├─ TrendChart                         │
│  │  └─ watch(store.historyData)        │
│  │     → 自动刷新                       │
│  │                                     │
│  └─ NewsFeed                           │
│     └─ watch(store.newsFeed)           │
│        → 自动刷新                       │
│                                         │
│  onBeforeUnmount():                     │
│  └─ 断开 WebSocket 连接                │
│                                         │
└─────────────────────────────────────────┘
```

---

## 完整数据流

### 场景：Redis 数据更新 → 前端自动刷新

```
时间 | 操作                      | 组件           | 备注
-----|---------------------------|---------------|----------
T0   | Processor 写入数据        | Processor     |
     | SET processed_data:*      | Redis (DB2)   |
     |                           |               |
T1   | 监听检测到变化            | data_monitor  | 每秒检查一次
     | {updated: [...]}          | (后端线程)    |
     |                           |               |
T2   | 调用推送回调              | data_monitor  |
     | push_processed_data_*     | → websocket_  |
     |                           | manager       |
     |                           |               |
T3   | 构建推送消息              | websocket_    |
     | {type: 'data_update',     | manager       |
     |  updated_data: {...}}     |               |
     |                           |               |
T4   | 广播给所有 WebSocket 连接 | websocket_    |
     | connection.send_text()    | manager       |
     |                           |               |
T5   | 浏览器接收消息            | WebSocket     |
     | ws.addEventListener('msg')| (前端)        |
     |                           |               |
T6   | WebSocket 服务路由消息    | websocket     |
     | dispatchDataUpdate()      | Service       |
     |                           |               |
T7   | 触发回调函数              | websocket     |
     | triggerCallback()         | Service       |
     |                           |               |
T8   | Store action 更新状态     | trendStore    |
     | updateTrendingFromWS()    | (Pinia)       |
     | trendingKeywords = data   |               |
     |                           |               |
T9   | 组件 watch 检测到变化     | 各个组件      |
     | watch(trendingKeywords)   | (Vue)         |
     |                           |               |
T10  | 组件自动重新渲染          | 组件          | ✨ 用户看到更新
     |                           |               |

总耗时: ~500-1000ms (T0 → T10)
```

---

## 消息格式规范

### WebSocket 推送消息

```json
{
  "type": "data_update",
  "change_info": {
    "changed": true,
    "added": [],
    "updated": ["processed_data:trending_keywords"],
    "deleted": [],
    "timestamp": "2025-11-03T10:30:45.123456Z"
  },
  "updated_data": {
    "trending_keywords": [
      {
        "keyword": "AI",
        "growth_rate": 150,
        "sentiment": {
          "positive_count": 45,
          "neutral_count": 20,
          "negative_count": 5,
          "total_comments": 70,
          "label": "positive"
        },
        "current_frequency": 123
      }
    ],
    "word_cloud": [
      {
        "text": "AI",
        "value": 123
      }
    ],
    "news_feed": [
      {
        "title": "AI 新动向",
        "source": "新浪",
        "url": "https://...",
        "sentiment": {"label": "positive"},
        "keywords": ["AI", "科技"]
      }
    ],
    "metadata": {
      "timestamp": "2025-11-03T10:30:45.123Z",
      "update_interval": 30,
      "data_version": "1.0"
    }
  },
  "timestamp": "2025-11-03T10:30:45.123456Z"
}
```

---

## 错误处理流程

```
┌─ WebSocket 错误
│  ├─ 连接失败
│  │  └─ attemptReconnect()
│  │     └─ 等待 3s 后重连 (最多 5 次)
│  │
│  ├─ 接收消息错误
│  │  └─ handleError()
│  │     └─ 自动重连
│  │
│  └─ 连接意外关闭
│     └─ handleClose()
│        └─ 尝试重连
│
└─ 应用层处理
   ├─ 消息解析失败
   │  └─ 记录错误，继续监听
   │
   └─ 回调执行异常
      └─ try-catch 捕获，不影响其他回调
```

---

## 性能考虑

### 1. 内存使用

- **WebSocket 连接**: ~100KB per connection
- **回调列表**: ~1KB per callback
- **消息缓存**: ~10MB max (可配置)

### 2. CPU 使用

- **监听线程**: < 1% (每秒检查一次)
- **推送操作**: < 5% (取决于连接数)
- **前端更新**: < 10% (组件 diff 算法)

### 3. 网络流量

- **消息大小**: ~1-5KB per update
- **频率**: 变化依赖 (1-60 updates/min)
- **带宽**: ~10-50 KB/s (低频场景)

---

## 扩展性

### 1. 多客户端

支持无限数量客户端连接，通过广播推送。

### 2. 数据分片

可以为不同数据类型使用不同的 WebSocket 端点。

### 3. 消息优先级

可以为高优先级消息添加专用队列。

### 4. 消息压缩

大消息可使用 gzip 压缩。

---

## 安全考虑

### 1. 连接验证

- WebSocket 握手阶段验证令牌
- 限制单 IP 连接数

### 2. 消息验证

- 验证消息完整性
- 限制消息大小

### 3. 速率限制

- 限制每秒推送数量
- 防止 DDoS 攻击

---

## 监控指标

```
实时监控指标:
├─ 连接数
│  ├─ 当前活跃连接
│  └─ 总累计连接数
│
├─ 消息流量
│  ├─ 每秒消息数
│  └─ 平均消息大小
│
├─ 性能指标
│  ├─ 平均推送延迟
│  ├─ 消息丢失率
│  └─ 连接失败率
│
└─ 错误追踪
   ├─ 连接错误
   ├─ 消息解析错误
   └─ 回调执行错误
```

---

**文档版本**: 1.0.0  
**最后更新**: 2025-11-03

