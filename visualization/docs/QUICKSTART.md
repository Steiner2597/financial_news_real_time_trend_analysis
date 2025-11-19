# 🚀 快速开始指南

## 5 分钟快速启动

### 前置条件

- Python 3.8+
- Node.js 14+
- Redis 服务运行 (port 6379)
- 数据已写入 Redis DB2 的 `processed_data` 命名空间

### 第 1 步: 启动后端服务

```bash
cd visualization/backend

# 安装依赖 (如果还没装)
pip install -r requirement.txt

# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**预期输出:**
```
🚀 启动金融趋势分析后台服务
✅ Redis客户端连接成功!
👁️  启动 processed_data 数据监听器...
✅ 数据监听器已启动
📡 已启用实时数据推送

Uvicorn running on http://0.0.0.0:8000
```

### 第 2 步: 启动前端应用

```bash
cd visualization/frontend

# 安装依赖 (如果还没装)
npm install

# 启动开发服务
npm run dev
```

**预期输出:**
```
VITE v4.x.x  ready in 123 ms

➜  Local:   http://localhost:5173
```

### 第 3 步: 打开浏览器

访问 `http://localhost:5173`

**预期行为:**
- 页面加载 Dashboard
- 打开 DevTools (F12 → Console)
- 看到 WebSocket 连接日志

### 第 4 步: 验证实时推送

在另一个终端运行:

```bash
redis-cli -n 2

# 更新数据
SET "processed_data:trending_keywords" '{"test": "data"}'
```

**预期结果:**
- 浏览器 Console 看到数据更新日志
- Dashboard 中的数据自动刷新 (无需手动刷新)
- 页面完全无阻塞更新

---

## 🔍 验证清单

| 项目 | 检查 | 状态 |
|------|------|------|
| 后端启动 | 看到 "✅ 数据监听器已启动" | ✅/❌ |
| 前端启动 | 看到 "Local: http://localhost:5173" | ✅/❌ |
| WebSocket 连接 | Console 看到 "✅ WebSocket 已连接" | ✅/❌ |
| 数据自动更新 | 手动更新 Redis 后，前端自动刷新 | ✅/❌ |

---

## 📊 关键日志

### 后端日志

```
📡 已推送 processed_data 更新给所有客户端
✅ 已广播数据给所有 X 个连接
```

### 前端日志

```
📺 Dashboard 组件已挂载
🔗 正在初始化 WebSocket 连接...
✅ WebSocket 已连接
🎉 WebSocket 连接已建立
📨 收到 WebSocket 消息: data_update
🔄 收到 processed_data 更新
✅ Trending 数据已更新
👁️ TrendingKeywords 检测到数据变化，自动刷新
```

---

## 🐛 常见问题

### Q1: 后端无法连接 Redis
**错误**: `Redis连接测试失败`

**解决**:
1. 确认 Redis 运行: `redis-cli ping`
2. 确认 Redis 有数据: `redis-cli -n 2 KEYS "*"`
3. 检查配置: `visualization/backend/app/config.py`

### Q2: 前端无法连接 WebSocket
**错误**: `❌ WebSocket 错误: 连接错误`

**解决**:
1. 确认后端运行: `curl http://localhost:8000/health`
2. 检查端口: `lsof -i :8000`
3. 查看浏览器网络标签 (F12 → Network → WS)

### Q3: 数据不自动更新
**症状**: 数据不会实时刷新

**排查**:
1. 检查 Redis 中是否有新数据
2. 确认 data_monitor 在运行
3. 查看浏览器 Console 错误

---

## 📚 详细文档

- **架构设计**: `ARCHITECTURE.md`
- **实现指南**: `WEBSOCKET_REALTIME_GUIDE.md`
- **验证清单**: `WEBSOCKET_VERIFICATION_CHECKLIST.md`

---

## 🎯 核心功能演示

### 1. 实时数据推送

```bash
# 终端 1: 启动后端
cd visualization/backend && python -m uvicorn app.main:app --reload

# 终端 2: 启动前端
cd visualization/frontend && npm run dev

# 终端 3: 更新数据
redis-cli -n 2
SET "processed_data:trending_keywords" '{"新数据": "已更新"}'

# 结果: 浏览器自动刷新，无需手动操作！
```

### 2. 自动重连

```bash
# 关闭后端 (Ctrl+C)
# WebSocket 自动尝试重连
# 重启后端，自动恢复连接
```

### 3. 组件自动刷新

- **TrendingKeywords** - 监听热词数据
- **WordCloud** - 监听词云数据
- **TrendChart** - 监听历史数据
- **NewsFeed** - 监听新闻数据

每个组件在接收数据更新时自动刷新！

---

## 🔧 可选配置

### 后端配置

编辑 `visualization/backend/app/config.py`:

```python
# WebSocket 配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 2  # processed_data 所在 DB

# 监听间隔 (秒)
DATA_MONITOR_INTERVAL = 1  # 每秒检查一次
```

### 前端配置

编辑 `visualization/frontend/src/services/websocketService.js`:

```javascript
// 重连配置
maxReconnectAttempts = 5      // 最多重试 5 次
reconnectDelay = 3000         // 重试延迟 3 秒
```

---

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| 连接建立 | < 500ms |
| 数据推送 | < 100ms |
| 前端刷新 | < 1s |
| 自动重连 | 3s 间隔 |

---

## 🎓 学习资源

### 了解各部分如何工作

1. **监听**: `visualization/backend/app/services/data_monitor.py`
2. **推送**: `visualization/backend/app/services/websocket_manager.py`
3. **接收**: `visualization/frontend/src/services/websocketService.js`
4. **更新**: `visualization/frontend/src/stores/trendStore.js`
5. **刷新**: `visualization/frontend/src/components/*.vue`

### 调试技巧

```javascript
// 在浏览器 Console 中运行

// 查看 WebSocket 连接状态
import websocketService from '@/services/websocketService'
console.log(websocketService.getStatus())

// 查看 Store 状态
import { useTrendStore } from '@/stores/trendStore'
const store = useTrendStore()
console.log(store.$state)

// 手动触发数据更新
store.updateTrendingFromWebSocket({
  data: [{keyword: 'test', growth_rate: 100}]
})
```

---

## 🚀 部署说明

### 生产部署

前端:
```bash
npm run build
# 输出到 dist 目录
# 使用 Nginx 或其他服务器服务静态文件
```

后端:
```bash
# 使用生产 ASGI 服务器
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## 📞 获取帮助

1. **查看日志** - 在 Console 中查看详细日志
2. **查看文档** - 阅读 `WEBSOCKET_REALTIME_GUIDE.md`
3. **运行检查** - 参考 `WEBSOCKET_VERIFICATION_CHECKLIST.md`

---

**版本**: 1.0.0  
**最后更新**: 2025-11-03

