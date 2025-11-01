# 事件驱动清洗器架构图

## 📊 模块关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                    EventDrivenCleaner                           │
│                      (主控制器)                                   │
│                                                                 │
│  - 初始化所有组件                                                │
│  - 协调各模块工作                                                │
│  - 提供运行模式切换                                              │
└────────┬──────────┬──────────┬──────────┬─────────────────────┘
         │          │          │          │
         ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │ Redis  │ │Notifi- │ │ Cache  │ │Signal  │
    │Manager │ │cation  │ │Manager │ │Handler │
    │        │ │Handler │ │        │ │        │
    └────────┘ └────────┘ └────────┘ └────────┘
         │          │          │          │
         │          │          │          │
         ▼          ▼          ▼          ▼
    订阅/发布   消息处理   缓存管理   信号处理
```

## 🔄 数据流图

### 事件驱动模式

```
┌─────────────┐
│   Scraper   │ 爬取数据
│   (爬虫)     │
└──────┬──────┘
       │ 推送数据到 Redis DB0
       │ 发送通知到 crawler_complete
       ▼
┌─────────────────────────────────────────────────────┐
│             RedisConnectionManager                   │
│                                                      │
│  ┌──────────────┐         ┌──────────────┐         │
│  │Subscribe     │         │Publish       │         │
│  │Client (DB0)  │         │Client (DB1)  │         │
│  └──────┬───────┘         └──────▲───────┘         │
└─────────┼────────────────────────┼──────────────────┘
          │                        │
          │ 接收通知                │ 发送通知
          ▼                        │
┌─────────────────────┐            │
│NotificationHandler  │            │
│  - 解析消息          │            │
│  - 记录日志          │            │
└──────┬──────────────┘            │
       │                           │
       │ 触发清洗                   │
       ▼                           │
┌──────────────────────────────────┼──────┐
│    EventDrivenCleaner            │      │
│                                  │      │
│  ┌────────────────────┐          │      │
│  │ _run_cleaning()    │          │      │
│  │  - 调用清洗逻辑     │          │      │
│  │  - 导出文件         │          │      │
│  └──────┬─────────────┘          │      │
│         │                        │      │
│         ▼                        │      │
│  ┌────────────────────┐          │      │
│  │ CacheManager       │          │      │
│  │  - 检查缓存状态     │          │      │
│  │  - 记录统计信息     │          │      │
│  └────────────────────┘          │      │
│                                  │      │
└──────────────────────────────────┼──────┘
                                   │
                                   │ 发送 cleaner_complete
                                   ▼
                            ┌─────────────┐
                            │  Processor  │
                            │  (处理器)    │
                            └─────────────┘
```

## 🏗️ 类关系图

```
EventDrivenCleaner
│
├── has-a → RedisConnectionManager
│           ├── subscribe_client: Redis
│           ├── publish_client: Redis
│           └── pubsub: PubSub
│
├── has-a → NotificationHandler
│           ├── publish_client: Redis
│           └── methods:
│               ├── parse_message()
│               ├── log_received_message()
│               └── send_completion_notification()
│
├── has-a → CacheManager
│           ├── redis_connector: RedisConnector
│           └── methods:
│               ├── clear_cache()
│               ├── get_cache_status()
│               └── log_cache_status()
│
└── has-a → SignalHandler
            ├── stop_callback: Callable
            └── methods:
                ├── setup()
                ├── restore()
                └── _signal_handler()
```

## 🔀 状态流转图

```
┌─────────────┐
│   初始化     │ __init__()
│   状态       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  连接 Redis  │ _connect_redis()
│   状态       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   等待消息   │ run_event_driven()
│   状态       │ ◄──────────┐
└──────┬──────┘            │
       │                   │
       │ 收到通知            │
       ▼                   │
┌─────────────┐            │
│  处理消息    │            │
│   状态       │            │
└──────┬──────┘            │
       │                   │
       ▼                   │
┌─────────────┐            │
│  执行清洗    │            │
│   状态       │            │
└──────┬──────┘            │
       │                   │
       ▼                   │
┌─────────────┐            │
│  发送通知    │            │
│   状态       │            │
└──────┬──────┘            │
       │                   │
       └───────────────────┘
       │
       │ 收到退出信号
       ▼
┌─────────────┐
│  清理资源    │ _cleanup()
│   状态       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   退出       │
└─────────────┘
```

## 📦 模块职责分配

| 模块 | 职责 | 依赖 |
|-----|------|------|
| **cleaner.py** | 主控制流程、协调各模块 | 所有其他模块 |
| **redis_manager.py** | Redis 连接生命周期管理 | redis |
| **notification_handler.py** | 消息解析、发送、日志 | redis, json |
| **cache_manager.py** | 缓存状态查询、清理 | redis, time |
| **signal_handler.py** | 信号捕获、回调触发 | signal |

## 🔧 配置驱动架构

```
config_processing.yaml
        │
        ▼
┌──────────────────┐
│  CONFIG (dict)   │
│                  │
│  ├─ redis        │
│  │  ├─ notification_listen
│  │  └─ notification_send
│  │                │
│  └─ deduplication │
│     ├─ mode       │
│     ├─ window_hours
│     └─ clear_on_start
└─────────┬────────┘
          │
          ▼
    EventDrivenCleaner
          │
          ├─> RedisConnectionManager (使用 redis 配置)
          ├─> NotificationHandler (使用 notification 配置)
          └─> CacheManager (使用 deduplication 配置)
```

## 🎯 单一职责原则应用

### 原文件 (460 行)
```
data_cleaner_event_driven.py
├── 连接管理 (30 行)
├── 消息处理 (100 行)
├── 缓存管理 (60 行)
├── 信号处理 (20 行)
├── 清洗逻辑 (150 行)
└── 工具方法 (100 行)
```

### 新架构 (5 个文件)
```
event_driven/
├── cleaner.py (250 行)
│   └── 主控制流程
├── redis_manager.py (130 行)
│   └── 连接管理
├── notification_handler.py (150 行)
│   └── 消息处理
├── cache_manager.py (120 行)
│   └── 缓存管理
└── signal_handler.py (50 行)
    └── 信号处理
```

## 💡 优势对比

| 方面 | 原架构 | 新架构 |
|-----|--------|--------|
| **可读性** | ⭐⭐⭐ (460 行单文件) | ⭐⭐⭐⭐⭐ (5 个清晰模块) |
| **可测试性** | ⭐⭐ (难以隔离测试) | ⭐⭐⭐⭐⭐ (每个模块独立测试) |
| **可维护性** | ⭐⭐⭐ (修改影响范围大) | ⭐⭐⭐⭐⭐ (修改局部化) |
| **可扩展性** | ⭐⭐ (添加功能复杂) | ⭐⭐⭐⭐⭐ (插件式扩展) |
| **关闭速度** | ⭐⭐ (可能阻塞) | ⭐⭐⭐⭐⭐ (< 2 秒) |

## 🚀 性能优化

### 快速关闭机制
```python
# 原方式（可能阻塞）
pubsub.unsubscribe(channel)
pubsub.close()  # 等待响应

# 新方式（立即断开）
pubsub.unsubscribe()  # 不等待
pubsub.connection_pool = None
pubsub.connection = None
```

### 连接池管理
```python
# 直接关闭连接池
if client.connection_pool:
    client.connection_pool.disconnect()
```

## 📈 未来扩展方向

1. **插件系统**
   - 自定义消息处理器
   - 自定义缓存策略
   - 自定义通知格式

2. **监控和指标**
   - 添加 metrics 收集
   - 性能监控
   - 错误追踪

3. **配置热重载**
   - 监听配置文件变化
   - 动态更新运行参数

4. **分布式支持**
   - 多实例协调
   - 负载均衡
   - 故障转移
