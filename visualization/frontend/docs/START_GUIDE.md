# 🚀 完整服务启动指南

## 📋 项目服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                    浏览器 (Web Client)                        │
│              http://localhost:3000                           │
└────────────────────────┬────────────────────────────────────┘
                         │ (Vue 3 + Vite)
                         │
┌────────────────────────▼────────────────────────────────────┐
│            前端 Vite 开发服务器 (Port 3000)                   │
│           📁 frontend/src 文件监听 & 热更新                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP Requests
                         │ /api/v1/*
                         │
┌────────────────────────▼────────────────────────────────────┐
│      后端 FastAPI 服务器 (Port 8000)                         │
│    http://localhost:8000/api/v1                             │
│  - /trends/keywords                                         │
│  - /trends/history                                          │
│  - /trends/all                                              │
│  - /wordcloud                                               │
│  - /news                                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Redis 数据存储 (Port 6379)                       │
│         (应用启动时自动连接)                                  │
└─────────────────────────────────────────────────────────────┘
```

## ✅ 服务启动清单

### 1️⃣ 启动 Redis（第一步）
**必需**: 后端依赖 Redis

**方式 A: 本地 Redis 服务**
```powershell
# Windows: 使用 WSL2 或已安装的 Redis
redis-server

# 验证
redis-cli ping
# 预期输出: PONG
```

**方式 B: Docker Redis**
```powershell
docker run -d -p 6379:6379 --name redis-dev redis:latest

# 验证
curl http://localhost:6379  # 或使用 redis-cli
```

### 2️⃣ 启动后端服务（第二步）
**目录**: `backend/`

```powershell
# 进入后端目录
cd d:\SE\workspace\CS5481-visualization\backend

# 激活虚拟环境(如果需要)
venv\Scripts\activate

# 启动后端
python run.py

# 预期输出
# INFO:     Uvicorn running on http://127.0.0.1:8000
# 🚀 启动金融趋势分析后台服务
```

**验证后端**:
```powershell
# 打开新的 PowerShell 窗口
curl http://localhost:8000/api/v1/trends/keywords

# 预期: StatusCode: 200 OK
```

### 3️⃣ 启动前端服务（第三步）
**目录**: `frontend/`

```powershell
# 新建 PowerShell 窗口或标签页
cd d:\SE\workspace\CS5481-visualization\frontend

# 启动前端开发服务器
npm run dev

# 预期输出
# VITE v4.5.14 ready in XXX ms
# ➜ Local: http://localhost:3000/
```

**访问前端**:
```
在浏览器中打开: http://localhost:3000
```

---

## 🔧 VS Code 中的多终端管理

### 推荐布局
使用 VS Code 集成终端创建 3 个标签页:

**终端 1: Redis**
```powershell
redis-server
```

**终端 2: 后端**
```powershell
cd backend
python run.py
```

**终端 3: 前端**
```powershell
cd frontend
npm run dev
```

### 终端操作快捷键
- **打开新终端**: `` Ctrl + ` ``
- **新建标签页**: `Ctrl + Shift + ` (反引号)
- **切换标签页**: `Ctrl + PageUp / PageDown`
- **分割窗口**: `Ctrl + Shift + 5`

---

## 🌐 访问地址汇总

| 服务 | 地址 | 用途 | 状态 |
|------|------|------|------|
| 前端应用 | http://localhost:3000 | 📊 主应用 | 🟢 |
| 后端 API 文档 | http://localhost:8000/docs | 📖 Swagger UI | 🟢 |
| 后端 ReDoc | http://localhost:8000/redoc | 📖 ReDoc 文档 | 🟢 |
| Redis CLI | `redis-cli` | 🗄️ 数据库 | 🟢 |

---

## ✨ 前端页面预期功能

刷新后应该看到:

### 左上角
- ✅ **情感分析条** (SentimentBar)
  - 显示正面/中立/负面百分比
  - 显示总评论数

### 左下角
- ✅ **热词排行** (TrendingKeywords)
  - 前10个热门关键词
  - 排名、频率、增长率、趋势图标

### 中间
- ✅ **趋势图表** (TrendChart)
  - 24小时历史曲线
  - 前5个关键词的趋势

### 右侧
- ✅ **新闻动态** (NewsFeed)
  - 最新新闻列表
  - 时间、来源、情感标签
  - 自动滚动

### 底部
- ✅ **词云** (WordCloud)
  - 关键词云图展示

---

## 🔍 服务健康检查

### 快速验证脚本
```powershell
# 检查所有服务状态

# 1. Redis
Write-Host "🔍 检查 Redis..."
redis-cli ping | Select-Object

# 2. 后端
Write-Host "🔍 检查后端..."
$backend = Invoke-WebRequest http://localhost:8000/api/v1/trends/keywords -ErrorAction SilentlyContinue
if ($backend.StatusCode -eq 200) { Write-Host "✅ 后端正常" } else { Write-Host "❌ 后端异常" }

# 3. 前端
Write-Host "🔍 检查前端..."
$frontend = Invoke-WebRequest http://localhost:3000 -ErrorAction SilentlyContinue
if ($frontend.StatusCode -eq 200) { Write-Host "✅ 前端正常" } else { Write-Host "❌ 前端异常" }
```

---

## 🐛 常见问题排查

### ❌ 后端启动失败: Redis 连接错误
**错误**: `Error 10061 connecting to localhost:6379`

**解决方案**:
1. 启动 Redis 服务
2. 验证 Redis 运行: `redis-cli ping`
3. 重启后端

### ❌ 前端无法加载数据
**症状**: 页面空白或显示加载中

**排查步骤**:
1. 打开浏览器控制台 (F12)
2. 查看 Console 标签
3. 检查 Network 标签中的 API 请求
4. 确认后端是否返回 200 状态码

**解决方案**:
```javascript
// 在浏览器控制台运行
fetch('http://localhost:8000/api/v1/trends/keywords')
  .then(r => r.json())
  .then(d => console.log(d))
  .catch(e => console.error(e))
```

### ❌ 连接被拒绝 (ERR_CONNECTION_REFUSED)
**症状**: `net::ERR_CONNECTION_REFUSED`

**可能原因**:
- ❌ 后端未启动
- ❌ 前端未启动
- ❌ Redis 未启动
- ❌ 防火墙阻止

**检查方法**:
```powershell
# 检查端口监听
netstat -ano | findstr :3000   # 前端
netstat -ano | findstr :8000   # 后端
netstat -ano | findstr :6379   # Redis
```

---

## 📊 性能监控

### 前端性能
```javascript
// 在浏览器控制台运行
performance.getEntriesByType('navigation').forEach(e => {
  console.log('DNS:', e.domainLookupEnd - e.domainLookupStart)
  console.log('TCP:', e.connectEnd - e.connectStart)
  console.log('Request:', e.responseStart - e.requestStart)
  console.log('Response:', e.responseEnd - e.responseStart)
})
```

### 后端性能
```bash
# 后端日志中查看请求时间
tail -f backend.log | grep "GET /api/v1"
```

---

## 🛑 优雅关闭服务

**关闭顺序** (反向启动顺序):

1. **前端**: 在 VS Code 终端按 `Ctrl + C`
2. **后端**: 在 VS Code 终端按 `Ctrl + C`
3. **Redis**: 在 VS Code 终端按 `Ctrl + C`

```powershell
# 或使用命令强制关闭
taskkill /PID <PID> /F

# 或关闭所有 Node.js 进程
taskkill /F /IM node.exe
```

---

## 📝 启动脚本（可选）

**创建** `start-all.ps1`:

```powershell
# 启动所有服务的 PowerShell 脚本

Write-Host "🚀 启动所有服务..." -ForegroundColor Green

# 1. 启动 Redis (需要单独处理)
Write-Host "1. 请在单独的终端启动 Redis: redis-server"

# 2. 启动后端
Write-Host "2. 启动后端服务..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList {
    cd 'D:\SE\workspace\CS5481-visualization\backend'
    python run.py
}

# 3. 启动前端
Write-Host "3. 启动前端服务..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList {
    cd 'D:\SE\workspace\CS5481-visualization\frontend'
    npm run dev
}

Write-Host "✅ 所有服务已启动！" -ForegroundColor Green
Write-Host "📂 前端: http://localhost:3000" -ForegroundColor Yellow
Write-Host "📂 后端: http://localhost:8000/docs" -ForegroundColor Yellow
```

**运行**:
```powershell
.\start-all.ps1
```

---

## 🎯 快速启动清单

- [ ] Redis 已启动 (`redis-cli ping` 返回 PONG)
- [ ] 后端已启动 (curl 返回 200)
- [ ] 前端已启动 (页面可访问)
- [ ] 浏览器已打开 http://localhost:3000
- [ ] Console 中无红色错误
- [ ] 页面显示数据

✅ **一切就绪，开始开发！** 🚀

---

**最后更新**: 2025-10-26  
**版本**: 1.0.0
