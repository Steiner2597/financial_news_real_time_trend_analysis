# WebSocket 实时更新系统 - 快速验证清单

## ✅ 实现验证

### 后端验证

#### 1. data_monitor.py 是否存在
```bash
# 检查文件
ls -la visualization/backend/app/services/data_monitor.py

# 应该看到：data_monitor.py 存在
```

#### 2. websocket_manager.py 是否有新增方法
```bash
# 检查 broadcast_all_types 方法
grep -n "broadcast_all_types" visualization/backend/app/services/websocket_manager.py

# 检查 push_processed_data_update 方法
grep -n "push_processed_data_update" visualization/backend/app/services/websocket_manager.py
```

#### 3. main.py 是否正确集成
```bash
# 检查是否导入 data_monitor
grep -n "from .services.data_monitor" visualization/backend/app/main.py

# 检查是否导入 websocket_manager
grep -n "from .services.websocket_manager" visualization/backend/app/main.py

# 检查是否启动 data_monitor
grep -n "data_monitor.add_callback" visualization/backend/app/main.py
grep -n "data_monitor.start()" visualization/backend/app/main.py
```

---

### 前端验证

#### 1. WebSocketService.js 是否存在
```bash
# 检查文件
ls -la visualization/frontend/src/services/websocketService.js

# 应该看到：websocketService.js 存在
```

#### 2. trendStore.js 是否有 WebSocket 方法
```bash
# 检查导入 websocketService
grep -n "import websocketService" visualization/frontend/src/stores/trendStore.js

# 检查 initWebSocket 方法
grep -n "initWebSocket" visualization/frontend/src/stores/trendStore.js

# 检查 disconnectWebSocket 方法
grep -n "disconnectWebSocket" visualization/frontend/src/stores/trendStore.js

# 检查数据更新方法
grep -n "updateTrendingFromWebSocket" visualization/frontend/src/stores/trendStore.js
```

#### 3. Dashboard.vue 是否初始化 WebSocket
```bash
# 检查是否调用 initWebSocket
grep -n "initWebSocket" visualization/frontend/src/views/Dashboard.vue

# 检查是否调用 disconnectWebSocket
grep -n "disconnectWebSocket" visualization/frontend/src/views/Dashboard.vue
```

#### 4. 组件是否添加了监听器
```bash
# TrendingKeywords
grep -n "watch.*trendingKeywords" visualization/frontend/src/components/TrendingKeywords.vue

# WordCloud
grep -n "watch.*wordCloudData" visualization/frontend/src/components/WordCloud.vue

# TrendChart
grep -n "watch.*historyData" visualization/frontend/src/components/TrendChart.vue

# NewsFeed
grep -n "watch.*newsFeed" visualization/frontend/src/components/NewsFeed.vue
```

---

## 🧪 运行时验证

### 后端启动检查

```bash
# 启动后端服务
cd visualization/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 应该看到日志：
# 🚀 启动金融趋势分析后台服务
# 🔧 初始化Redis连接...
# ✅ Redis客户端连接成功!
# 👁️  启动 processed_data 数据监听器...
# ✅ 数据监听器已启动
# 📡 已启用实时数据推送
```

### 前端启动检查

```bash
# 启动前端开发服务
cd visualization/frontend
npm run dev

# 应该看到：
# VITE v4.x.x ready in 123 ms
# ➜  Local: http://localhost:5173
```

### 浏览器控制台验证

1. **打开浏览器开发者工具** (F12)
2. **切换到 Console 标签**
3. **刷新页面**

应该看到的日志：
```
📺 Dashboard 组件已挂载
🔗 正在初始化 WebSocket 连接...
🔗 正在连接 WebSocket: ws://localhost:8000/api/v1/ws/trending
✅ WebSocket 已连接
🎉 WebSocket 连接已建立，订阅类型: ['trending']
📌 已注册 trending 数据回调
📌 已注册 word_cloud 数据回调
📌 已注册 news 数据回调
📌 已注册 history 数据回调
✅ WebSocket 连接已初始化
```

### 手动触发数据更新测试

#### 方法 1: Redis CLI 直接更新

```bash
# 连接 Redis
redis-cli -n 2

# 更新 processed_data 中的某个键
SET "processed_data:trending_keywords" '{"test": "data"}'

# 返回前端，应该看到：
# 📨 收到 WebSocket 消息: data_update
# 🔄 收到 processed_data 更新
# 📡 收到 trending 实时更新
# ✅ Trending 数据已更新
# 👁️ TrendingKeywords 检测到数据变化，自动刷新
```

#### 方法 2: Python 脚本更新

```python
# test_websocket_update.py
import redis
import json
import time

client = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)

# 更新数据
test_data = {
    "test_keyword": {
        "frequency": 100,
        "growth_rate": 50
    }
}

client.set("processed_data:trending_keywords", json.dumps(test_data))
print("✅ 数据已更新")
```

运行：
```bash
python test_websocket_update.py
```

---

## 📊 完整流程验证

| 步骤 | 检查项 | 预期结果 | 实际结果 |
|------|--------|--------|---------|
| 1 | 后端启动 | 显示监听器启动日志 | ✅/❌ |
| 2 | 前端启动 | 显示 Dashboard 挂载 | ✅/❌ |
| 3 | WebSocket 连接 | 显示连接成功 | ✅/❌ |
| 4 | 回调注册 | 显示 4 个回调已注册 | ✅/❌ |
| 5 | 数据更新 | Redis 中数据变化 | ✅/❌ |
| 6 | 消息接收 | 前端收到 data_update | ✅/❌ |
| 7 | 状态更新 | Store 状态改变 | ✅/❌ |
| 8 | 组件刷新 | 组件显示新数据 | ✅/❌ |

---

## 🔧 调试命令

### 查看所有 processed_data 键

```bash
redis-cli -n 2 KEYS "processed_data:*"
```

### 实时监控 Redis 数据变化

```bash
redis-cli -n 2 MONITOR
```

### 查看 Redis 中的具体数据

```bash
redis-cli -n 2 GET "processed_data:trending_keywords"
```

### 检查前端 Store 状态

在浏览器控制台执行：
```javascript
// 导入 store
import { useTrendStore } from '@/stores/trendStore'
const store = useTrendStore()

// 查看状态
console.log('连接状态:', store.wsConnected)
console.log('连接状态字符串:', store.wsStatus)
console.log('最后更新时间:', store.lastUpdateTime)
console.log('更新来源:', store.updateSource)
console.log('Trending 数据:', store.trendingKeywords)
```

### 检查 WebSocket 服务状态

```javascript
import websocketService from '@/services/websocketService'

// 查看连接状态
console.log(websocketService.getStatus())

// 查看最后收到的消息
console.log(websocketService.lastMessage.value)

// 查看注册的回调
console.log(websocketService.dataCallbacks)
```

---

## ✨ 预期行为

### 正常工作时

1. ✅ 打开浏览器，看到 Dashboard 加载
2. ✅ 控制台显示 WebSocket 已连接
3. ✅ 更新 Redis 数据
4. ✅ **前端数据自动更新**（无需手动刷新）
5. ✅ 组件显示更新动画

### 异常情况

| 异常 | 处理 |
|------|------|
| WebSocket 连接失败 | 自动重连，最多 5 次 |
| 网络中断 | 显示连接错误，恢复后自动重连 |
| 收到错误消息 | 控制台显示错误，不影响其他功能 |
| 浏览器标签关闭 | 断开连接，清理资源 |

---

## 📋 快速诊断

如果数据不自动更新，按顺序检查：

1. **后端正在运行？**
   ```bash
   curl http://localhost:8000/health
   ```

2. **WebSocket 连接成功？**
   - 浏览器 DevTools → Network → WS
   - 应该看到一个 `ws://localhost:8000/api/v1/ws/trending` 连接

3. **Redis 中有数据？**
   ```bash
   redis-cli -n 2 KEYS "processed_data:*"
   ```

4. **Console 中有错误？**
   - 打开浏览器 DevTools → Console
   - 查看是否有红色错误

5. **Store 状态正确？**
   - Console 中执行 `store.wsConnected`
   - 应该返回 `true`

---

## 🎓 关键日志位置

### 后端日志
```
📡 已推送 processed_data 更新给所有客户端
✅ 已广播数据给所有 X 个连接
```

### 前端日志
```
📨 收到 WebSocket 消息: data_update
🔄 收到 processed_data 更新
✅ Trending 数据已更新
👁️ TrendingKeywords 检测到数据变化，自动刷新
```

---

**完成此清单后，WebSocket 实时更新系统应该完全工作！** 🎉

